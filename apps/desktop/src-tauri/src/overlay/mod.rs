pub mod dismiss;
use serde::{Deserialize, Serialize};
use std::sync::Mutex;
use tauri::{AppHandle, Manager, PhysicalPosition, PhysicalSize, WebviewUrl, WebviewWindowBuilder};

use crate::capture::{CaptureMetadata, Rectangle};
pub mod input;

// Keep preferred width in sync with --popup-width; all dimensions here are
// converted once into the target monitor's physical pixels.
const POPUP_LOGICAL_WIDTH: f64 = 420.0;
const INITIAL_POPUP_LOGICAL_HEIGHT: f64 = 320.0;
const POPUP_SCREEN_INSET: f64 = 12.0;
const POPUP_HEIGHT_FRACTION: f64 = 0.7;
const POPUP_ANCHOR_GAP: f64 = 8.0;

fn overlay_navigation_url(
    mut capture_url: tauri::Url,
    session_id: u64,
) -> Result<tauri::Url, String> {
    // Use the already loaded selector's app entry point. A new WebView2's
    // current URL can still be about:blank while its first navigation is pending.
    if capture_url.cannot_be_a_base() {
        return Err("The capture app page has not loaded".into());
    }
    capture_url.set_query(Some(&format!("mode=overlay&session={session_id}")));
    capture_url.set_fragment(None);
    Ok(capture_url)
}

#[derive(Default)]
pub struct OverlayStore(Mutex<Option<serde_json::Value>>);

impl OverlayStore {
    fn set(&self, value: serde_json::Value) -> Result<(), String> {
        *self.0.lock().map_err(|error| error.to_string())? = Some(value);
        Ok(())
    }

    pub fn get(&self) -> Result<serde_json::Value, String> {
        self.0
            .lock()
            .map_err(|error| error.to_string())?
            .clone()
            .ok_or_else(|| "OCR overlay data is unavailable".into())
    }

    pub fn clear(&self) -> Result<(), String> {
        *self.0.lock().map_err(|error| error.to_string())? = None;
        Ok(())
    }
}

#[derive(Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
struct OverlayLayout {
    window_x: i32,
    window_y: i32,
    window_width: u32,
    window_height: u32,
    content_left: f64,
    content_top: f64,
    content_width: f64,
    content_height: f64,
    toolbar_top: f64,
    toolbar_height: f64,
}

fn measured_layout(
    metadata: &CaptureMetadata,
    mut layout: OverlayLayout,
    position: PhysicalPosition<i32>,
    size: PhysicalSize<u32>,
) -> OverlayLayout {
    let scale = metadata.scale_factor;
    let toolbar_screen_top = f64::from(layout.window_y) + layout.toolbar_top * scale;
    layout.window_x = position.x;
    layout.window_y = position.y;
    layout.window_width = size.width;
    layout.window_height = size.height;
    layout.content_left = (metadata.selection_physical_bounds.x - f64::from(position.x)) / scale;
    layout.content_top = (metadata.selection_physical_bounds.y - f64::from(position.y)) / scale;
    layout.toolbar_top = ((toolbar_screen_top - f64::from(position.y)) / scale).clamp(
        0.0,
        (f64::from(size.height) / scale - layout.toolbar_height).max(0.0),
    );
    layout
}

pub fn reveal_overlay(app: &AppHandle, store: &OverlayStore) -> Result<serde_json::Value, String> {
    let window = app
        .get_webview_window("ocr-overlay")
        .ok_or("OCR overlay is unavailable")?;
    window
        .set_ignore_cursor_events(true)
        .map_err(|e| e.to_string())?;
    window.show().map_err(|e| e.to_string())?;
    let mut state = store.get()?;
    let metadata: CaptureMetadata =
        serde_json::from_value(state["metadata"].clone()).map_err(|e| e.to_string())?;
    let planned: OverlayLayout =
        serde_json::from_value(state["layout"].clone()).map_err(|e| e.to_string())?;
    // Measure after showing: macOS may shift a borderless window below its
    // menu bar. Keep image pixels at their physical origin, even when that
    // requires a negative content offset inside the visible native window.
    let actual = measured_layout(
        &metadata,
        planned,
        window.inner_position().map_err(|e| e.to_string())?,
        window.inner_size().map_err(|e| e.to_string())?,
    );
    app.state::<crate::AppState>()
        .overlay_input
        .install(app, &state, &actual)?;
    let actual = serde_json::to_value(actual).map_err(|e| e.to_string())?;
    #[cfg(debug_assertions)]
    if std::env::var_os("YOMIMADO_OVERLAY_GEOMETRY_DEBUG").is_some() {
        let polygons: Vec<_> = state["regions"]
            .as_array()
            .into_iter()
            .flatten()
            .map(|region| region["polygon"].clone())
            .collect();
        eprintln!(
            "YomiMado geometry: {}",
            serde_json::json!({
                "metadata": state["metadata"], "layout": actual, "polygons": polygons,
            })
        );
    }
    state["layout"] = actual.clone();
    store.set(state)?;
    Ok(actual)
}

#[derive(Clone, Copy, Deserialize)]
pub struct OcrPoint {
    x: f64,
    y: f64,
}

#[derive(Debug, PartialEq)]
struct PopupPosition {
    x: i32,
    y: i32,
    width: u32,
    height: u32,
}

#[derive(Clone, Copy, Deserialize, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct PopupPlacement {
    screen: Rectangle,
    anchor_left: f64,
    anchor_right: f64,
    anchor_top: f64,
    scale_factor: f64,
}

fn popup_placement(
    metadata: &CaptureMetadata,
    polygon: &[OcrPoint],
    screen: Rectangle,
) -> Result<PopupPlacement, String> {
    if polygon.len() < 3 || metadata.image_width == 0 || metadata.image_height == 0 {
        return Err("The selected OCR region has no usable geometry".into());
    }
    let scale = metadata.scale_factor;
    if !scale.is_finite() || scale <= 0.0 {
        return Err("Invalid display scale".into());
    }
    let min_x = polygon
        .iter()
        .map(|point| point.x)
        .fold(f64::INFINITY, f64::min);
    let max_x = polygon
        .iter()
        .map(|point| point.x)
        .fold(f64::NEG_INFINITY, f64::max);
    let min_y = polygon
        .iter()
        .map(|point| point.y)
        .fold(f64::INFINITY, f64::min);
    if !min_x.is_finite() || !max_x.is_finite() || !min_y.is_finite() {
        return Err("Invalid OCR region coordinates".into());
    }
    let selection = metadata.selection_physical_bounds;
    let anchor_left = selection.x + min_x * selection.width / f64::from(metadata.image_width);
    let anchor_right = selection.x + max_x * selection.width / f64::from(metadata.image_width);
    let anchor_top = selection.y + min_y * selection.height / f64::from(metadata.image_height);
    Ok(PopupPlacement {
        screen,
        anchor_left,
        anchor_right,
        anchor_top,
        scale_factor: scale,
    })
}

fn popup_position(placement: PopupPlacement, logical_height: f64) -> Result<PopupPosition, String> {
    let screen = placement.screen;
    let scale = placement.scale_factor;
    if !logical_height.is_finite()
        || logical_height <= 0.0
        || !scale.is_finite()
        || scale <= 0.0
        || !screen.width.is_finite()
        || !screen.height.is_finite()
        || screen.width <= 0.0
        || screen.height <= 0.0
    {
        return Err("Invalid popup size or display bounds".into());
    }
    let inset = (POPUP_SCREEN_INSET * scale)
        .round()
        .min((screen.width.min(screen.height) / 4.0).floor());
    let available_width = (screen.width - 2.0 * inset).max(1.0);
    let available_height = (screen.height - 2.0 * inset).max(1.0);
    let width = (POPUP_LOGICAL_WIDTH * scale).round().min(available_width);
    let height = (logical_height * scale)
        .round()
        .min((available_height * POPUP_HEIGHT_FRACTION).round())
        .max(1.0);
    let gap = (POPUP_ANCHOR_GAP * scale).round();
    let screen_left = screen.x + inset;
    let screen_top = screen.y + inset;
    let screen_right = screen.x + screen.width - inset;
    let screen_bottom = screen.y + screen.height - inset;
    let x = if placement.anchor_right + gap + width <= screen_right {
        placement.anchor_right + gap
    } else if placement.anchor_left - gap - width >= screen_left {
        placement.anchor_left - gap - width
    } else {
        (placement.anchor_right + gap).clamp(screen_left, screen_right - width)
    };
    let y = placement
        .anchor_top
        .clamp(screen_top, screen_bottom - height);
    Ok(PopupPosition {
        x: x.round() as i32,
        y: y.round() as i32,
        width: width as u32,
        height: height as u32,
    })
}

fn translation_popup_query(
    text: &str,
    demo: bool,
    placement: PopupPlacement,
    review_reason: Option<&str>,
    approximate: bool,
) -> String {
    let mut state = serde_json::json!({ "text": text, "demo": demo, "placement": placement });
    if let Some(reason) = review_reason {
        state["reviewReason"] = reason.into();
    }
    if approximate {
        state["approximate"] = true.into();
    }
    let serialized = state.to_string();
    let encoded = urlencoding::encode(&serialized);
    format!("mode=translation&state={encoded}")
}

fn layout(metadata: &CaptureMetadata) -> OverlayLayout {
    let selection = &metadata.selection_physical_bounds;
    let screen = &metadata.screen_physical_bounds;
    let scale = if metadata.scale_factor > 0.0 {
        metadata.scale_factor
    } else {
        1.0
    };
    let toolbar = (32.0 * scale).round() as i32;
    let minimum_width = (148.0 * scale).round() as i32;
    let screen_right = (screen.x + screen.width).round() as i32;
    let screen_bottom = (screen.y + screen.height).round() as i32;
    let screen_left = screen.x.round() as i32;
    let screen_top = screen.y.round() as i32;
    let selection_x = selection.x.round() as i32;
    let selection_y = selection.y.round() as i32;
    let selection_width = selection.width.round() as i32;
    let selection_height = selection.height.round() as i32;
    let window_width = selection_width
        .max(minimum_width)
        .min(screen_right - screen_left);
    let window_x = selection_x
        .min(screen_right - window_width)
        .max(screen_left);
    let fills_visible_display = selection_width >= screen_right - screen_left - 1
        && selection_y + selection_height >= screen_bottom - 1;
    let (window_y, content_top, toolbar_top, window_height) = if fills_visible_display {
        // A macOS selector can start below the menu bar. Placing the toolbar
        // above it would make the OS shift the overlay window down and drift
        // every OCR polygon away from the captured image.
        (selection_y, 0, 0, selection_height)
    } else if selection_y - toolbar >= screen_top {
        (
            selection_y - toolbar,
            toolbar,
            0,
            selection_height + toolbar,
        )
    } else if selection_y + selection_height + toolbar <= screen_bottom {
        (selection_y, 0, selection_height, selection_height + toolbar)
    } else {
        // A selection filling the display has no outside gutter.
        (selection_y, 0, 0, selection_height)
    };

    OverlayLayout {
        window_x,
        window_y,
        window_width: window_width as u32,
        window_height: window_height as u32,
        content_left: f64::from(selection_x - window_x) / scale,
        content_top: f64::from(content_top) / scale,
        content_width: f64::from(selection_width) / scale,
        content_height: f64::from(selection_height) / scale,
        toolbar_top: f64::from(toolbar_top) / scale,
        toolbar_height: f64::from(toolbar) / scale,
    }
}

pub fn show_overlay(
    app: &AppHandle,
    store: &OverlayStore,
    metadata: &CaptureMetadata,
    regions: serde_json::Value,
    engine: &str,
    estimated_reading_order: bool,
    session_id: u64,
) -> Result<(), String> {
    app.state::<crate::AppState>().overlay_input.disable(app)?;
    let previous = store.get().ok();
    let layout = layout(metadata);
    let state = serde_json::json!({
        "metadata": metadata, "regions": regions, "engine": engine,
        "layout": layout, "estimatedReadingOrder": estimated_reading_order,
        "sessionId": session_id,
    });
    if let Some(popup) = app.get_webview_window("translation-popup") {
        popup.hide().map_err(|e| e.to_string())?;
    }
    let target_url = overlay_navigation_url(
        app.get_webview_window("capture-selector")
            .ok_or("Capture selector is unavailable")?
            .url()
            .map_err(|e| e.to_string())?,
        session_id,
    )?;
    // Reuse the overlay just like the learning popup: closing and immediately
    // rebuilding the same label races asynchronous native destruction on Rescan.
    let existing = app.get_webview_window("ocr-overlay");
    let previous_frame = existing.as_ref().and_then(|window| {
        Some((
            window.inner_position().ok()?,
            window.inner_size().ok()?,
            window.url().ok()?,
        ))
    });
    let result: Result<(), String> = (|| {
        // Publish the data before the new React root can request it.
        store.set(state)?;
        let reused = existing.is_some();
        let window = if let Some(window) = existing {
            window.hide().map_err(|e| e.to_string())?;
            window
        } else {
            let builder = WebviewWindowBuilder::new(
                app,
                "ocr-overlay",
                WebviewUrl::External(target_url.clone()),
            )
            .transparent(true)
            .decorations(false)
            .resizable(false)
            .always_on_top(true)
            .focused(false)
            .accept_first_mouse(true)
            .skip_taskbar(true)
            .visible(false);
            // Windows shadows add client-area insets and shift image polygons.
            #[cfg(target_os = "windows")]
            let builder = builder.shadow(false);
            builder.build().map_err(|e| e.to_string())?
        };
        // Establish the target monitor before converting the physical size;
        // a new hidden window can still have the default monitor's scale.
        window
            .set_position(PhysicalPosition::new(layout.window_x, layout.window_y))
            .map_err(|e| e.to_string())?;
        // macOS resizing preserves the bottom edge and shifts the top. Apply the
        // position again after resizing so smaller selections are not clipped.
        window
            .set_size(PhysicalSize::new(layout.window_width, layout.window_height))
            .map_err(|e| e.to_string())?;
        window
            .set_position(PhysicalPosition::new(layout.window_x, layout.window_y))
            .map_err(|e| e.to_string())?;
        if reused {
            // Never derive this from the overlay's current URL: it can still
            // be blank if a new scan overtook the initial page load.
            window.navigate(target_url).map_err(|e| e.to_string())?;
        }
        // The React root reveals this generation after mounting its polygons.
        // Repositioning a visible old DOM would briefly show incorrect geometry.
        Ok(())
    })();
    if result.is_err() {
        if let Some(previous) = previous {
            let _ = store.set(previous);
        } else {
            let _ = store.clear();
        }
        if let Some(window) = app.get_webview_window("ocr-overlay") {
            if let Some((position, size, url)) = previous_frame {
                let _ = window.set_position(position);
                let _ = window.set_size(size);
                let _ = window.set_position(position);
                let _ = window.navigate(url);
            } else {
                let _ = window.hide();
            }
        }
    }
    result
}

pub fn show_translation_popup(
    app: &AppHandle,
    metadata: &CaptureMetadata,
    text: &str,
    polygon: &[OcrPoint],
    demo: bool,
    review_reason: Option<&str>,
    approximate: bool,
) -> Result<(), String> {
    let screen = app
        .get_webview_window("ocr-overlay")
        .and_then(|window| window.current_monitor().ok().flatten())
        .map(|monitor| {
            let area = monitor.work_area();
            Rectangle {
                x: f64::from(area.position.x),
                y: f64::from(area.position.y),
                width: f64::from(area.size.width),
                height: f64::from(area.size.height),
            }
        })
        .unwrap_or(metadata.screen_physical_bounds);
    let placement = popup_placement(metadata, polygon, screen)?;
    let position = popup_position(placement, INITIAL_POPUP_LOGICAL_HEIGHT)?;
    let query = translation_popup_query(text, demo, placement, review_reason, approximate);
    if let Some(window) = app.get_webview_window("translation-popup") {
        // Reuse the existing webview: close() can return before its label is
        // removed, so immediately rebuilding with the same label can fail.
        let mut url = window.url().map_err(|error| error.to_string())?;
        url.set_query(Some(&query));
        window.navigate(url).map_err(|error| error.to_string())?;
        window
            .set_position(PhysicalPosition::new(position.x, position.y))
            .map_err(|error| error.to_string())?;
        window
            .set_size(PhysicalSize::new(position.width, position.height))
            .map_err(|error| error.to_string())?;
        window
            .set_position(PhysicalPosition::new(position.x, position.y))
            .map_err(|error| error.to_string())?;
        window.show().map_err(|error| error.to_string())?;
        window.set_focus().map_err(|error| error.to_string())?;
        return Ok(());
    }
    let window = WebviewWindowBuilder::new(
        app,
        "translation-popup",
        WebviewUrl::App(format!("index.html?{query}").into()),
    )
    .transparent(true)
    .decorations(false)
    .always_on_top(true)
    .accept_first_mouse(true)
    .skip_taskbar(true)
    .visible(false)
    .build()
    .map_err(|error| error.to_string())?;
    window
        .set_position(PhysicalPosition::new(position.x, position.y))
        .map_err(|error| error.to_string())?;
    window
        .set_size(PhysicalSize::new(position.width, position.height))
        .map_err(|error| error.to_string())?;
    window
        .set_position(PhysicalPosition::new(position.x, position.y))
        .map_err(|error| error.to_string())?;
    window.show().map_err(|error| error.to_string())?;
    window.set_focus().map_err(|error| error.to_string())?;
    Ok(())
}

pub fn resize_translation_popup(
    app: &AppHandle,
    placement: PopupPlacement,
    logical_height: f64,
    view_query: &str,
) -> Result<(), String> {
    let window = app
        .get_webview_window("translation-popup")
        .ok_or("Translation popup is unavailable")?;
    // A reused webview can still deliver a resize from its previous sentence.
    if !window.is_visible().map_err(|error| error.to_string())?
        || window.url().map_err(|error| error.to_string())?.query() != Some(view_query)
    {
        return Ok(());
    }
    let position = popup_position(placement, logical_height)?;
    window
        .set_position(PhysicalPosition::new(position.x, position.y))
        .map_err(|error| error.to_string())?;
    window
        .set_size(PhysicalSize::new(position.width, position.height))
        .map_err(|error| error.to_string())?;
    window
        .set_position(PhysicalPosition::new(position.x, position.y))
        .map_err(|error| error.to_string())
}

fn frame_matches_capture(
    planned: &OverlayLayout,
    position: PhysicalPosition<i32>,
    size: PhysicalSize<u32>,
    captured_scale: Option<f64>,
    current_scale: f64,
) -> bool {
    position.x == planned.window_x
        && position.y == planned.window_y
        && size.width == planned.window_width
        && size.height == planned.window_height
        && captured_scale == Some(current_scale)
}

pub fn check_frame(app: &AppHandle) -> Result<(), String> {
    let state = app.state::<crate::AppState>();
    let mut session = state.scans.lock()?;
    if session.active.is_some() || !session.overlay_visible || !state.overlay_input.is_active() {
        return Ok(());
    }
    let window = app
        .get_webview_window("ocr-overlay")
        .ok_or("OCR overlay is unavailable")?;
    let data = state.overlay.get()?;
    let planned: OverlayLayout =
        serde_json::from_value(data["layout"].clone()).map_err(|e| e.to_string())?;
    let position = window.inner_position().map_err(|e| e.to_string())?;
    let size = window.inner_size().map_err(|e| e.to_string())?;
    let scale = window.scale_factor().map_err(|e| e.to_string())?;
    if !frame_matches_capture(
        &planned,
        position,
        size,
        data["metadata"]["scaleFactor"].as_f64(),
        scale,
    ) {
        state.overlay_input.disable(app)?;
        window.hide().map_err(|e| e.to_string())?;
        if let Some(popup) = app.get_webview_window("translation-popup") {
            popup.hide().map_err(|e| e.to_string())?;
        }
        session.overlay_visible = false;
        session.phase = "error";
        session.message = "Display layout changed. Rescan before using these OCR regions.".into();
        session.revision += 1;
        drop(session);
        crate::toolbar::emit_state(app);
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::capture::Rectangle;

    #[test]
    fn frame_guard_rejects_mixed_dpi_transitions_and_shifted_or_clipped_windows() {
        let scales = [1.0, 1.25, 1.5, 2.0];
        let planned = OverlayLayout {
            window_x: -3840,
            window_y: -2160,
            window_width: 1600,
            window_height: 900,
            content_left: 0.0,
            content_top: 0.0,
            content_width: 1600.0,
            content_height: 900.0,
            toolbar_top: 0.0,
            toolbar_height: 0.0,
        };
        let position = PhysicalPosition::new(planned.window_x, planned.window_y);
        let size = PhysicalSize::new(planned.window_width, planned.window_height);
        for captured_scale in scales {
            for current_scale in scales {
                // A DPI transition invalidates old hits even if the physical
                // frame happens to be unchanged on the destination monitor.
                assert_eq!(
                    frame_matches_capture(
                        &planned,
                        position,
                        size,
                        Some(captured_scale),
                        current_scale,
                    ),
                    captured_scale == current_scale
                );
            }
            for moved in [
                PhysicalPosition::new(position.x + 1, position.y),
                PhysicalPosition::new(position.x, position.y + 1),
            ] {
                assert!(!frame_matches_capture(
                    &planned,
                    moved,
                    size,
                    Some(captured_scale),
                    captured_scale,
                ));
            }
            for resized in [
                PhysicalSize::new(size.width - 1, size.height),
                PhysicalSize::new(size.width, size.height - 1),
            ] {
                assert!(!frame_matches_capture(
                    &planned,
                    position,
                    resized,
                    Some(captured_scale),
                    captured_scale,
                ));
            }
        }
        assert!(!frame_matches_capture(&planned, position, size, None, 1.0));
    }

    #[test]
    fn measured_window_origin_keeps_whole_screen_pixels_aligned_below_menu_bar() {
        let bounds = Rectangle {
            x: 0.0,
            y: 0.0,
            width: 2940.0,
            height: 1912.0,
        };
        let metadata = CaptureMetadata {
            display_id: "retina".into(),
            display_name: "Retina".into(),
            screen_physical_bounds: bounds,
            selection_physical_bounds: bounds,
            selection_logical_bounds: Rectangle {
                x: 0.0,
                y: 0.0,
                width: 1470.0,
                height: 956.0,
            },
            image_width: 2940,
            image_height: 1912,
            scale_factor: 2.0,
        };
        let measured = measured_layout(
            &metadata,
            layout(&metadata),
            PhysicalPosition::new(0, 66),
            PhysicalSize::new(2940, 1912),
        );
        assert_eq!(measured.content_top, -33.0);
        assert_eq!(measured.content_height, 956.0);
        assert_eq!(
            f64::from(measured.window_y) + measured.content_top * 2.0,
            0.0
        );
        // An image-space point at physical y=666 lands at screen y=666.
        assert_eq!(
            f64::from(measured.window_y) + (measured.content_top + 333.0) * 2.0,
            666.0
        );
    }

    #[test]
    fn large_ocr_state_is_kept_out_of_the_webview_url() {
        let store = OverlayStore::default();
        let regions: Vec<_> = (0..300)
            .map(|id| serde_json::json!({ "id": id, "text": "日本語".repeat(100) }))
            .collect();
        store
            .set(serde_json::json!({ "regions": regions }))
            .unwrap();

        let url = overlay_navigation_url(
            tauri::Url::parse("http://tauri.localhost/index.html?mode=capture&session=42").unwrap(),
            42,
        )
        .unwrap();
        assert_eq!(url.query(), Some("mode=overlay&session=42"));
        assert_eq!(
            store.get().unwrap()["regions"].as_array().unwrap().len(),
            300
        );
        store.clear().unwrap();
        assert!(store.get().is_err());
    }

    #[test]
    fn overlay_navigation_uses_the_loaded_app_origin_and_replaces_capture_options() {
        for base in [
            "http://localhost:1420/index.html",
            "http://tauri.localhost/index.html",
            "tauri://localhost/index.html",
        ] {
            let source = tauri::Url::parse(&format!(
                "{base}?mode=capture&session=6&scan=whole#selection"
            ))
            .unwrap();
            let target = overlay_navigation_url(source.clone(), 7).unwrap();
            assert_eq!(target.as_str(), format!("{base}?mode=overlay&session=7"));
            assert_eq!(target.query(), Some("mode=overlay&session=7"));
            assert_eq!(target.fragment(), None);
        }
    }

    #[test]
    fn an_initial_blank_webview_cannot_be_used_as_an_app_navigation_base() {
        for source in ["about:blank", "about:blank?mode=overlay&session=1"] {
            assert!(overlay_navigation_url(tauri::Url::parse(source).unwrap(), 2).is_err());
        }
    }

    #[test]
    fn translation_popup_navigation_preserves_new_ocr_text() {
        let placement = PopupPlacement {
            screen: Rectangle {
                x: 0.0,
                y: 0.0,
                width: 1920.0,
                height: 1080.0,
            },
            anchor_left: 100.0,
            anchor_right: 200.0,
            anchor_top: 100.0,
            scale_factor: 1.0,
        };
        let mut url = tauri::Url::parse("http://localhost:1420/index.html?mode=translation")
            .expect("valid app URL");
        url.set_query(Some(&translation_popup_query(
            "たまにはいいでしょ",
            false,
            placement,
            Some("Check short text"),
            true,
        )));

        let state = url
            .query_pairs()
            .find(|(key, _)| key == "state")
            .map(|(_, value)| value.into_owned())
            .expect("popup state");
        let state: serde_json::Value = serde_json::from_str(&state).expect("JSON popup state");
        assert_eq!(state["text"], "たまにはいいでしょ");
        assert_eq!(state["demo"], false);
        assert_eq!(state["reviewReason"], "Check short text");
        assert_eq!(state["approximate"], true);
        assert_eq!(state["placement"]["anchorLeft"], 100.0);
    }

    #[test]
    fn small_selection_gets_toolbar_outside_image() {
        let metadata = CaptureMetadata {
            display_id: "test".into(),
            display_name: "test".into(),
            screen_physical_bounds: Rectangle {
                x: 0.0,
                y: 0.0,
                width: 1920.0,
                height: 1080.0,
            },
            selection_physical_bounds: Rectangle {
                x: 1800.0,
                y: 300.0,
                width: 40.0,
                height: 70.0,
            },
            selection_logical_bounds: Rectangle {
                x: 900.0,
                y: 150.0,
                width: 20.0,
                height: 35.0,
            },
            image_width: 40,
            image_height: 70,
            scale_factor: 2.0,
        };
        let result = layout(&metadata);
        assert_eq!(result.window_x, 1624);
        assert_eq!(result.content_left, 88.0);
        assert_eq!(result.content_top, 32.0);
        assert_eq!(result.toolbar_top, 0.0);
        assert_eq!(result.content_width, 20.0);
    }

    #[test]
    fn content_stays_on_the_selected_screen_rectangle() {
        let metadata = CaptureMetadata {
            display_id: "retina".into(),
            display_name: "Retina".into(),
            screen_physical_bounds: Rectangle {
                x: 0.0,
                y: 0.0,
                width: 2940.0,
                height: 1912.0,
            },
            selection_physical_bounds: Rectangle {
                x: 1200.0,
                y: 666.0,
                width: 200.0,
                height: 300.0,
            },
            selection_logical_bounds: Rectangle {
                x: 600.0,
                y: 300.0,
                width: 100.0,
                height: 150.0,
            },
            image_width: 200,
            image_height: 300,
            scale_factor: 2.0,
        };
        let result = layout(&metadata);
        assert_eq!(
            f64::from(result.window_x) + result.content_left * 2.0,
            1200.0
        );
        assert_eq!(f64::from(result.window_y) + result.content_top * 2.0, 666.0);
        assert_eq!(result.content_width * 2.0, 200.0);
        assert_eq!(result.content_height * 2.0, 300.0);
    }

    #[test]
    fn display_scan_keeps_overlay_below_mac_menu_bar() {
        let metadata = CaptureMetadata {
            display_id: "retina".into(),
            display_name: "Retina".into(),
            screen_physical_bounds: Rectangle {
                x: 0.0,
                y: 0.0,
                width: 2940.0,
                height: 1912.0,
            },
            selection_physical_bounds: Rectangle {
                x: 0.0,
                y: 66.0,
                width: 2940.0,
                height: 1846.0,
            },
            selection_logical_bounds: Rectangle {
                x: 0.0,
                y: 0.0,
                width: 1470.0,
                height: 923.0,
            },
            image_width: 2940,
            image_height: 1846,
            scale_factor: 2.0,
        };
        let result = layout(&metadata);
        assert_eq!(result.window_y, 66);
        assert_eq!(result.content_top, 0.0);
        assert_eq!(result.window_height, 1846);
    }

    #[test]
    fn translation_popup_is_anchored_beside_ocr_region() {
        let metadata = CaptureMetadata {
            display_id: "retina".into(),
            display_name: "Retina".into(),
            screen_physical_bounds: Rectangle {
                x: 0.0,
                y: 0.0,
                width: 2940.0,
                height: 1912.0,
            },
            selection_physical_bounds: Rectangle {
                x: 1200.0,
                y: 666.0,
                width: 200.0,
                height: 300.0,
            },
            selection_logical_bounds: Rectangle {
                x: 600.0,
                y: 300.0,
                width: 100.0,
                height: 150.0,
            },
            image_width: 200,
            image_height: 300,
            scale_factor: 2.0,
        };
        let polygon = [
            OcrPoint { x: 0.0, y: 0.0 },
            OcrPoint { x: 200.0, y: 0.0 },
            OcrPoint { x: 200.0, y: 300.0 },
        ];
        let placement = popup_placement(&metadata, &polygon, metadata.screen_physical_bounds)
            .expect("valid popup placement");
        assert_eq!(
            popup_position(placement, INITIAL_POPUP_LOGICAL_HEIGHT).unwrap(),
            PopupPosition {
                x: 1416,
                y: 666,
                width: 840,
                height: 640
            }
        );
    }

    #[test]
    fn tall_popup_fits_work_area_and_keeps_retina_scale() {
        let placement = PopupPlacement {
            screen: Rectangle {
                x: -1600.0,
                y: 30.0,
                width: 1600.0,
                height: 900.0,
            },
            anchor_left: -200.0,
            anchor_right: -100.0,
            anchor_top: 700.0,
            scale_factor: 2.0,
        };
        let position = popup_position(placement, 800.0).unwrap();
        assert_eq!(position.width, 840);
        assert_eq!(position.height, 596);
        assert!(position.x >= -1576);
        assert!(position.x + position.width as i32 <= -24);
        assert!(position.y >= 54);
        assert!(position.y + position.height as i32 <= 906);
    }

    #[test]
    fn popup_grows_to_content_height_when_screen_has_room() {
        let placement = PopupPlacement {
            screen: Rectangle {
                x: 0.0,
                y: 0.0,
                width: 1920.0,
                height: 1080.0,
            },
            anchor_left: 100.0,
            anchor_right: 200.0,
            anchor_top: 120.0,
            scale_factor: 1.0,
        };
        let position = popup_position(placement, 680.0).unwrap();
        assert_eq!((position.width, position.height), (420, 680));
        assert_eq!((position.x, position.y), (208, 120));
    }

    #[test]
    fn small_screen_clamps_popup_width_and_height() {
        let placement = PopupPlacement {
            screen: Rectangle {
                x: 0.0,
                y: 0.0,
                width: 360.0,
                height: 500.0,
            },
            anchor_left: 200.0,
            anchor_right: 250.0,
            anchor_top: 200.0,
            scale_factor: 1.0,
        };
        let position = popup_position(placement, 900.0).unwrap();
        assert_eq!((position.width, position.height), (336, 333));
        assert_eq!((position.x, position.y), (12, 155));
    }

    #[test]
    fn compact_popup_scales_once_and_caps_height_on_fractional_displays() {
        for scale in [1.0, 1.25, 1.5, 2.0] {
            let placement = PopupPlacement {
                screen: Rectangle {
                    x: -2400.0,
                    y: -300.0,
                    width: 1920.0,
                    height: 1080.0,
                },
                anchor_left: -600.0,
                anchor_right: -500.0,
                anchor_top: 700.0,
                scale_factor: scale,
            };
            let position = popup_position(placement, 2000.0).unwrap();
            let inset = (12.0 * scale).round();
            assert_eq!(position.width, (420.0 * scale).round() as u32);
            assert_eq!(
                position.height,
                ((1080.0 - 2.0 * inset) * 0.7).round() as u32
            );
            assert!(f64::from(position.x) >= -2400.0 + inset);
            assert!(f64::from(position.x) + f64::from(position.width) <= -480.0 - inset);
            assert!(f64::from(position.y) >= -300.0 + inset);
            assert!(f64::from(position.y) + f64::from(position.height) <= 780.0 - inset);
            let collapsed = popup_position(placement, 180.0).unwrap();
            assert_eq!(collapsed.height, (180.0 * scale).round() as u32);
        }
    }
}
