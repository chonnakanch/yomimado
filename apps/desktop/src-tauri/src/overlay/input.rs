//! Native input routing. Geometry is in physical client pixels, exactly as drawn.
//! Windows uses a native window region; AppKit exposes whole-window mouse ignore,
//! so macOS samples the native cursor without listening to or replaying events.
use serde::Deserialize;
use std::sync::{
    atomic::{AtomicBool, Ordering},
    Arc, Mutex,
};
use tauri::{AppHandle, Manager};

use super::OverlayLayout;
use crate::capture::{CaptureMetadata, Rectangle};

#[derive(Clone, Copy, Debug, Deserialize, PartialEq)]
pub struct Point {
    pub x: f64,
    pub y: f64,
}

#[derive(Clone, Default)]
struct Route {
    session_id: u64,
    epoch: u64,
    active: bool,
    origin: Point,
    scale: f64,
    width: u32,
    height: u32,
    polygons: Vec<Vec<Point>>,
    controls: Vec<Vec<Point>>,
    control_revision: u64,
    popup_return: Option<String>,
}

impl Default for Point {
    fn default() -> Self {
        Self { x: 0.0, y: 0.0 }
    }
}

#[derive(Default)]
pub struct InputRouter {
    route: Arc<Mutex<Route>>,
    stopped: Arc<AtomicBool>,
}

// Inclusive edges match the visible polygon boundary; concave regions must not
// turn the empty corners of their bounding box into native hit targets.
fn contains(polygon: &[Point], p: Point) -> bool {
    let mut inside = false;
    for (a, b) in polygon
        .iter()
        .zip(polygon.iter().cycle().skip(1))
        .take(polygon.len())
    {
        let cross = (p.x - a.x) * (b.y - a.y) - (p.y - a.y) * (b.x - a.x);
        if cross.abs() <= 0.001
            && p.x >= a.x.min(b.x)
            && p.x <= a.x.max(b.x)
            && p.y >= a.y.min(b.y)
            && p.y <= a.y.max(b.y)
        {
            return true;
        }
        if (a.y > p.y) != (b.y > p.y) && p.x < (b.x - a.x) * (p.y - a.y) / (b.y - a.y) + a.x {
            inside = !inside;
        }
    }
    inside
}

fn physical_polygons(
    state: &serde_json::Value,
    layout: &OverlayLayout,
) -> Result<Vec<Vec<Point>>, String> {
    let metadata: CaptureMetadata =
        serde_json::from_value(state["metadata"].clone()).map_err(|e| e.to_string())?;
    if metadata.image_width == 0 || metadata.image_height == 0 {
        return Err("Invalid OCR image size".into());
    }
    let area = metadata.selection_physical_bounds;
    let mut polygons = Vec::new();
    for region in state["regions"].as_array().ok_or("Missing OCR polygons")? {
        let points: Vec<Point> =
            serde_json::from_value(region["polygon"].clone()).map_err(|e| e.to_string())?;
        if points.len() < 3 || points.iter().any(|p| !p.x.is_finite() || !p.y.is_finite()) {
            return Err("Invalid OCR polygon".into());
        }
        polygons.push(
            points
                .into_iter()
                .map(|p| Point {
                    x: area.x - f64::from(layout.window_x)
                        + p.x * area.width / f64::from(metadata.image_width),
                    y: area.y - f64::from(layout.window_y)
                        + p.y * area.height / f64::from(metadata.image_height),
                })
                .collect(),
        );
    }
    Ok(polygons)
}

impl InputRouter {
    pub(super) fn install(
        &self,
        app: &AppHandle,
        state: &serde_json::Value,
        layout: &OverlayLayout,
    ) -> Result<(), String> {
        let polygons = physical_polygons(state, layout)?;
        let scale = state["metadata"]["scaleFactor"]
            .as_f64()
            .filter(|s| s.is_finite() && *s > 0.0)
            .ok_or("Invalid overlay display scale")?;
        let route = Route {
            epoch: self.route.lock().map_err(|e| e.to_string())?.epoch + 1,
            session_id: state["sessionId"]
                .as_u64()
                .ok_or("Missing overlay generation")?,
            active: true,
            origin: Point {
                x: layout.window_x.into(),
                y: layout.window_y.into(),
            },
            scale,
            width: layout.window_width,
            height: layout.window_height,
            polygons,
            ..Route::default()
        };
        // Fail open to the reader while configuring/replacing hit targets.
        let window = app
            .get_webview_window("ocr-overlay")
            .ok_or("OCR overlay is unavailable")?;
        window
            .set_ignore_cursor_events(true)
            .map_err(|e| e.to_string())?;
        #[cfg(target_os = "windows")]
        windows::apply(app, &route)?;
        *self.route.lock().map_err(|e| e.to_string())? = route;
        #[cfg(target_os = "windows")]
        window
            .set_ignore_cursor_events(false)
            .map_err(|e| e.to_string())?;
        Ok(())
    }

    pub fn disable(&self, app: &AppHandle) -> Result<(), String> {
        let mut route = self.route.lock().map_err(|e| e.to_string())?;
        route.active = false;
        route.popup_return = None;
        if let Some(window) = app.get_webview_window("ocr-overlay") {
            window
                .set_ignore_cursor_events(true)
                .map_err(|e| e.to_string())?;
        }
        Ok(())
    }

    pub fn controls(
        &self,
        app: &AppHandle,
        session_id: u64,
        revision: u64,
        rectangles: Vec<Rectangle>,
        viewport_width: f64,
        viewport_height: f64,
    ) -> Result<(), String> {
        if !viewport_width.is_finite()
            || !viewport_height.is_finite()
            || viewport_width <= 0.0
            || viewport_height <= 0.0
            || rectangles.len() > 2
        {
            return Err("Invalid region navigator bounds".into());
        }
        let mut route = self.route.lock().map_err(|e| e.to_string())?;
        if !route.active || route.session_id != session_id || revision <= route.control_revision {
            return Ok(());
        }
        let mut controls = Vec::new();
        for rect in rectangles {
            if [rect.x, rect.y, rect.width, rect.height]
                .iter()
                .any(|v| !v.is_finite())
                || rect.width <= 0.0
                || rect.height <= 0.0
            {
                return Err("Invalid navigator rectangle".into());
            }
            let sx = f64::from(route.width) / viewport_width;
            let sy = f64::from(route.height) / viewport_height;
            let l = (rect.x * sx).clamp(0.0, route.width.into());
            let t = (rect.y * sy).clamp(0.0, route.height.into());
            let r = ((rect.x + rect.width) * sx).clamp(0.0, route.width.into());
            let b = ((rect.y + rect.height) * sy).clamp(0.0, route.height.into());
            controls.push(vec![
                Point { x: l, y: t },
                Point { x: r, y: t },
                Point { x: r, y: b },
                Point { x: l, y: b },
            ]);
        }
        route.controls = controls;
        route.control_revision = revision;
        #[cfg(target_os = "windows")]
        windows::apply(app, &route)?;
        #[cfg(not(target_os = "windows"))]
        let _ = app;
        Ok(())
    }

    pub fn remember_popup(&self, region: Option<String>) {
        if let Ok(mut route) = self.route.lock() {
            route.popup_return = region;
        }
    }
    pub fn is_active(&self) -> bool {
        self.route.lock().is_ok_and(|route| route.active)
    }
    pub fn take_popup_return(&self) -> Option<String> {
        let mut route = self.route.lock().ok()?;
        let region = route.popup_return.take();
        if route.active {
            region
        } else {
            None
        }
    }
    pub fn stop(&self) {
        self.stopped.store(true, Ordering::Relaxed);
    }

    pub fn start(&self, app: &AppHandle) {
        #[cfg(target_os = "macos")]
        {
            let app = app.clone();
            let route = self.route.clone();
            let stopped = self.stopped.clone();
            std::thread::spawn(move || {
                let mut ignored = true;
                let mut generation = 0;
                while !stopped.load(Ordering::Relaxed) {
                    let current = match route.lock() {
                        Ok(r) => r.clone(),
                        Err(_) => break,
                    };
                    if !current.active {
                        ignored = true;
                        std::thread::sleep(std::time::Duration::from_millis(80));
                        continue;
                    }
                    if generation != current.epoch {
                        ignored = true;
                        generation = current.epoch;
                    }
                    let (point, down) = macos::pointer(current.scale);
                    let local = Point {
                        x: point.x - current.origin.x,
                        y: point.y - current.origin.y,
                    };
                    let hit = current
                        .polygons
                        .iter()
                        .chain(&current.controls)
                        .any(|p| contains(p, local));
                    // Keep drags with the app that received mouse-down. Entering a
                    // region during a browser drag must not steal mouse-up.
                    let next = ignore_after_pointer(ignored, hit, down);
                    if next != ignored {
                        if let Ok(latest) = route.lock() {
                            if latest.active && latest.epoch == generation {
                                if let Some(window) = app.get_webview_window("ocr-overlay") {
                                    if window.set_ignore_cursor_events(next).is_ok() {
                                        ignored = next;
                                    }
                                }
                            }
                        }
                    }
                    std::thread::sleep(std::time::Duration::from_millis(8));
                }
            });
        }
        #[cfg(not(target_os = "macos"))]
        let _ = app;
    }
}

#[cfg(any(target_os = "macos", test))]
fn ignore_after_pointer(ignored: bool, hit: bool, down: bool) -> bool {
    if down {
        ignored
    } else {
        !hit
    }
}

#[cfg(target_os = "macos")]
pub fn logical_cursor_point() -> Point {
    macos::pointer(1.0).0
}

#[cfg(target_os = "macos")]
mod macos {
    use super::Point;
    // Read-only native state: no event tap, Accessibility grant, screenshots,
    // synthesized events, or input replay. Quartz uses top-left logical points.
    #[link(name = "CoreGraphics", kind = "framework")]
    extern "C" {
        fn CGEventCreate(source: *const std::ffi::c_void) -> *const std::ffi::c_void;
        fn CGEventGetLocation(event: *const std::ffi::c_void) -> core_graphics::geometry::CGPoint;
        fn CGEventSourceButtonState(state: i32, button: u32) -> bool;
    }
    #[link(name = "CoreFoundation", kind = "framework")]
    extern "C" {
        fn CFRelease(value: *const std::ffi::c_void);
    }
    pub fn pointer(scale: f64) -> (Point, bool) {
        unsafe {
            let event = CGEventCreate(std::ptr::null());
            if event.is_null() {
                return (
                    Point {
                        x: f64::NAN,
                        y: f64::NAN,
                    },
                    false,
                );
            }
            let p = CGEventGetLocation(event);
            CFRelease(event);
            (
                Point {
                    x: p.x * scale,
                    y: p.y * scale,
                },
                (0..3).any(|b| CGEventSourceButtonState(1, b)),
            )
        }
    }
}

#[cfg(target_os = "windows")]
mod windows {
    use super::*;
    type Handle = *mut std::ffi::c_void;
    #[repr(C)]
    struct WinPoint {
        x: i32,
        y: i32,
    }
    #[link(name = "gdi32")]
    extern "system" {
        fn CreateRectRgn(l: i32, t: i32, r: i32, b: i32) -> Handle;
        fn CreatePolygonRgn(points: *const WinPoint, count: i32, mode: i32) -> Handle;
        fn CombineRgn(dest: Handle, a: Handle, b: Handle, mode: i32) -> i32;
        fn DeleteObject(object: Handle) -> i32;
    }
    #[link(name = "user32")]
    extern "system" {
        fn SetWindowRgn(window: Handle, region: Handle, redraw: i32) -> i32;
    }
    pub fn apply(app: &AppHandle, route: &Route) -> Result<(), String> {
        let window = app
            .get_webview_window("ocr-overlay")
            .ok_or("OCR overlay is unavailable")?;
        let hwnd = window.hwnd().map_err(|e| e.to_string())?.0 as usize;
        // SetWindowRgn is relative to the outer HWND, not its webview client.
        let inner = window.inner_position().map_err(|e| e.to_string())?;
        let outer = window.outer_position().map_err(|e| e.to_string())?;
        let offset_x = inner.x - outer.x;
        let offset_y = inner.y - outer.y;
        let polygons: Vec<_> = route
            .polygons
            .iter()
            .chain(&route.controls)
            .cloned()
            .collect();
        let (send, recv) = std::sync::mpsc::channel();
        app.run_on_main_thread(move || {
            let result = unsafe {
                let region = CreateRectRgn(0, 0, 0, 0);
                if region.is_null() {
                    Err("Could not create native OCR hit region".to_string())
                } else {
                    let mut failed = false;
                    for p in polygons {
                        let points: Vec<_> = p
                            .iter()
                            .map(|p| WinPoint {
                                x: p.x.round() as i32 + offset_x,
                                y: p.y.round() as i32 + offset_y,
                            })
                            .collect();
                        let piece = CreatePolygonRgn(points.as_ptr(), points.len() as i32, 1);
                        if piece.is_null() {
                            failed = true;
                            break;
                        }
                        if CombineRgn(region, region, piece, 2) == 0 {
                            failed = true;
                        }
                        DeleteObject(piece);
                    }
                    // Windows owns the final HRGN only after a successful call.
                    if failed || SetWindowRgn(hwnd as Handle, region, 1) == 0 {
                        DeleteObject(region);
                        Err("Could not install native OCR hit region".to_string())
                    } else {
                        Ok(())
                    }
                }
            };
            let _ = send.send(result);
        })
        .map_err(|e| e.to_string())?;
        recv.recv().map_err(|e| e.to_string())?
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn browser_drags_keep_their_mouse_up_when_crossing_a_region() {
        assert!(ignore_after_pointer(true, false, true));
        assert!(ignore_after_pointer(true, true, true));
        assert!(!ignore_after_pointer(true, true, false));
        assert!(!ignore_after_pointer(false, true, true));
        assert!(!ignore_after_pointer(false, false, true));
        assert!(ignore_after_pointer(false, false, false));
    }
    #[test]
    fn concave_regions_leave_empty_corners_click_through_and_include_edges() {
        let p = vec![
            Point { x: 0., y: 0. },
            Point { x: 40., y: 0. },
            Point { x: 40., y: 10. },
            Point { x: 10., y: 10. },
            Point { x: 10., y: 40. },
            Point { x: 0., y: 40. },
        ];
        assert!(contains(&p, Point { x: 5., y: 35. }));
        assert!(contains(&p, Point { x: 10., y: 30. }));
        assert!(!contains(&p, Point { x: 30., y: 30. }));
        assert!(!contains(&p, Point { x: -1., y: 5. }));
    }
    #[test]
    fn native_hits_follow_image_geometry_on_negative_and_fractional_scale_monitors() {
        for scale in [1., 1.25, 1.5, 2.] {
            let metadata = CaptureMetadata {
                display_id: "left".into(),
                display_name: "Left".into(),
                screen_physical_bounds: Rectangle {
                    x: -2560.,
                    y: -1440.,
                    width: 2560.,
                    height: 1440.,
                },
                selection_physical_bounds: Rectangle {
                    x: -2300.,
                    y: -1000.,
                    width: 640.,
                    height: 800.,
                },
                selection_logical_bounds: Rectangle {
                    x: 0.,
                    y: 0.,
                    width: 640. / scale,
                    height: 800. / scale,
                },
                image_width: 320,
                image_height: 400,
                scale_factor: scale,
            };
            let mut layout = super::super::layout(&metadata);
            layout.window_y += 66; // OS-adjusted client origin, not the requested origin.
            let state = serde_json::json!({"metadata":metadata,"regions":[{"polygon":[{"x":10.,"y":20.},{"x":40.,"y":20.},{"x":40.,"y":80.}]}]});
            let polygons = physical_polygons(&state, &layout).unwrap();
            assert_eq!(polygons[0][0].x + f64::from(layout.window_x), -2280.);
            assert_eq!(polygons[0][0].y + f64::from(layout.window_y), -960.);
        }
    }
    #[test]
    fn malformed_geometry_does_not_make_a_full_window_hit_target() {
        let state = serde_json::json!({"metadata":{"displayId":"x","displayName":"x","screenPhysicalBounds":{"x":0,"y":0,"width":100,"height":100},"selectionPhysicalBounds":{"x":0,"y":0,"width":100,"height":100},"selectionLogicalBounds":{"x":0,"y":0,"width":100,"height":100},"imageWidth":100,"imageHeight":100,"scaleFactor":1},"regions":[{"polygon":[{"x":0,"y":0}]}]});
        let metadata = serde_json::from_value(state["metadata"].clone()).unwrap();
        assert!(physical_polygons(&state, &super::super::layout(&metadata)).is_err());
    }
}
