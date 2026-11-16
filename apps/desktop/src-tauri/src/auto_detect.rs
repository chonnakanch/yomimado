//! Opt-in page-change monitoring. Pixels stay in memory; OCR uses the existing
//! clean Rescan path. All lifecycle decisions share the scan-session lock.
use crate::overlay::input::{contains, Point};
use crate::{
    capture::{CapturedImage, Rectangle},
    toolbar,
};
use image::RgbImage;
use std::{
    sync::atomic::{AtomicBool, Ordering},
    time::Duration,
};
use tauri::{AppHandle, Manager};

/// Paint in screen-physical coordinates, using the native input route's geometry.
/// Opaque panels hide page content; OCR fills are translucent and must not hide
/// an entire text region from page-change detection.
pub enum CaptureMask {
    Opaque(Rectangle),
    Highlight(Vec<Point>),
}

impl CaptureMask {
    fn bounds(&self) -> Rectangle {
        match self {
            Self::Opaque(bounds) => *bounds,
            Self::Highlight(points) => {
                let left = points.iter().map(|p| p.x).fold(f64::INFINITY, f64::min);
                let top = points.iter().map(|p| p.y).fold(f64::INFINITY, f64::min);
                let right = points.iter().map(|p| p.x).fold(f64::NEG_INFINITY, f64::max);
                let bottom = points.iter().map(|p| p.y).fold(f64::NEG_INFINITY, f64::max);
                Rectangle {
                    x: left,
                    y: top,
                    width: right - left,
                    height: bottom - top,
                }
            }
        }
    }
}

// Keep these in sync with --color-region-fill in styles/tokens.css. Hover and
// selection use the same fill. Stroke pixels are excluded geometrically below.
const HIGHLIGHT_RGB: [f64; 3] = [0.0, 128.0, 255.0];
const HIGHLIGHT_ALPHA: f64 = 0.14;
const PAINT_MARGIN: f64 = 8.0;

fn near_outline(points: &[Point], p: Point, padding: f64) -> bool {
    points
        .iter()
        .zip(points.iter().cycle().skip(1))
        .take(points.len())
        .any(|(a, b)| {
            let dx = b.x - a.x;
            let dy = b.y - a.y;
            let length = dx * dx + dy * dy;
            let t = if length > 0.0 {
                ((p.x - a.x) * dx + (p.y - a.y) * dy) / length
            } else {
                0.0
            }
            .clamp(0.0, 1.0);
            (p.x - a.x - t * dx).powi(2) + (p.y - a.y - t * dy).powi(2) <= padding * padding
        })
}

fn pixel_changed(a: [u8; 3], b: [u8; 3], tint_layers: u8) -> bool {
    let distance = |a: [f64; 3], b: [f64; 3]| {
        a.iter()
            .zip(b)
            .map(|(a, b)| (a - b).abs())
            .fold(0.0, f64::max)
    };
    let a = a.map(f64::from);
    let b = b.map(f64::from);
    let mut difference = distance(a, b);
    let mut painted_a = a;
    let mut painted_b = b;
    for _ in 0..tint_layers {
        for channel in 0..3 {
            painted_a[channel] = painted_a[channel] * (1.0 - HIGHLIGHT_ALPHA)
                + HIGHLIGHT_RGB[channel] * HIGHLIGHT_ALPHA;
            painted_b[channel] = painted_b[channel] * (1.0 - HIGHLIGHT_ALPHA)
                + HIGHLIGHT_RGB[channel] * HIGHLIGHT_ALPHA;
        }
        difference = difference
            .min(distance(painted_a, b))
            .min(distance(a, painted_b));
    }
    difference > 24.0
}

#[derive(Clone, Debug)]
pub struct Frame {
    pixels: RgbImage,
    masked: Vec<bool>,
    tint_layers: Vec<u8>,
}

impl Frame {
    pub fn captured(image: &CapturedImage) -> Result<Self, String> {
        use base64::prelude::*;
        let bytes = BASE64_STANDARD
            .decode(
                image
                    .image_data_url
                    .strip_prefix("data:image/png;base64,")
                    .ok_or("Invalid capture image")?,
            )
            .map_err(|e| e.to_string())?;
        let image = image::load_from_memory(&bytes)
            .map_err(|e| e.to_string())?
            .to_rgba8();
        Ok(Self {
            pixels: crate::capture::thumbnail(&image),
            masked: vec![false; 128 * 128],
            tint_layers: vec![0; 128 * 128],
        })
    }

    fn sampled(pixels: RgbImage, area: Rectangle, masks: &[CaptureMask]) -> Self {
        let mut masked = vec![false; 128 * 128];
        let mut tint_layers = vec![0u8; 128 * 128];
        let cell_width = area.width / 128.0;
        let cell_height = area.height / 128.0;
        let edge_padding = PAINT_MARGIN + cell_width.hypot(cell_height) / 2.0;
        let bounds: Vec<_> = masks.iter().map(CaptureMask::bounds).collect();
        for (i, mask) in masked.iter_mut().enumerate() {
            // Include a thumbnail cell's full footprint, not just its centre.
            let x = area.x + (i % 128) as f64 * area.width / 128.0;
            let y = area.y + (i / 128) as f64 * area.height / 128.0;
            let centre = Point {
                x: x + cell_width / 2.0,
                y: y + cell_height / 2.0,
            };
            for (paint, bounds) in masks.iter().zip(&bounds) {
                if centre.x < bounds.x - edge_padding
                    || centre.y < bounds.y - edge_padding
                    || centre.x > bounds.x + bounds.width + edge_padding
                    || centre.y > bounds.y + bounds.height + edge_padding
                {
                    continue;
                }
                match paint {
                    CaptureMask::Opaque(m) => {
                        *mask |= x <= m.x + m.width
                            && y <= m.y + m.height
                            && x + cell_width >= m.x
                            && y + cell_height >= m.y;
                    }
                    CaptureMask::Highlight(points) => {
                        *mask |= near_outline(points, centre, edge_padding);
                        if contains(points, centre) {
                            tint_layers[i] = tint_layers[i].saturating_add(1);
                        }
                    }
                }
            }
        }
        Self {
            pixels,
            masked,
            tint_layers,
        }
    }

    fn difference(&self, other: &Self) -> Option<f64> {
        let mut usable = 0;
        let mut changed = 0;
        for (i, (a, b)) in self.pixels.pixels().zip(other.pixels.pixels()).enumerate() {
            if self.masked[i] || other.masked[i] {
                continue;
            }
            usable += 1;
            // Small compositor/antialiasing changes should not count as a page turn.
            if pixel_changed(a.0, b.0, self.tint_layers[i].max(other.tint_layers[i])) {
                changed += 1;
            }
        }
        // Do not infer a page change from a tiny exposed corner behind panels.
        (usable >= 128 * 128 * 3 / 10).then_some(changed as f64 / usable.max(1) as f64)
    }
}

#[derive(Clone)]
pub struct AutoDetect {
    pub enabled: bool,
    pub epoch: u64,
    pub status: &'static str,
    baseline: Option<Frame>,
    previous: Option<Frame>,
}

impl Default for AutoDetect {
    fn default() -> Self {
        Self {
            enabled: false,
            epoch: 0,
            status: "off",
            baseline: None,
            previous: None,
        }
    }
}

impl AutoDetect {
    pub fn stop(&mut self) {
        self.enabled = false;
        self.epoch += 1;
        self.status = "off";
        self.baseline = None;
        self.previous = None;
    }
    pub fn enable(&mut self, frame: Frame) {
        self.epoch += 1;
        self.enabled = true;
        self.reset(frame);
    }
    pub fn reset(&mut self, frame: Frame) {
        self.baseline = Some(frame);
        self.previous = None;
        self.status = "watching";
    }
    fn pause(&mut self) {
        self.previous = None;
        self.status = "paused";
    }
    fn observe(&mut self, frame: Frame) -> bool {
        let changed = self.baseline.as_ref().and_then(|b| b.difference(&frame));
        let stable = self.previous.as_ref().and_then(|p| p.difference(&frame));
        self.previous = Some(frame);
        match changed {
            None => {
                self.previous = None;
                self.status = "covered";
                false
            }
            Some(change) if change < 0.04 => {
                self.status = "watching";
                false
            }
            Some(_) => {
                self.status = "settling";
                // Two samples 750 ms apart must agree before starting one OCR job.
                stable.is_some_and(|change| change < 0.005)
            }
        }
    }
}

#[derive(Default)]
pub struct Worker {
    stopped: AtomicBool,
}

pub fn blocked(app: &AppHandle) -> bool {
    [
        "translation-popup",
        "main",
        "saved",
        "sources",
        "toolbar-menu",
    ]
    .iter()
    .any(|label| {
        app.get_webview_window(label)
            .is_some_and(|w| w.is_visible().unwrap_or(true))
    })
}

#[tauri::command(async)]
pub fn set_auto_detect(
    app: AppHandle,
    window: tauri::WebviewWindow,
    enabled: bool,
) -> Result<(), String> {
    if window.label() != "toolbar" {
        return Err("Use Auto detect in the reading toolbar.".into());
    }
    let state = app.state::<crate::AppState>();
    let mut session = state.scans.lock()?;
    if enabled {
        toolbar::require_idle(&session)?;
        if !session.last_manga || !session.overlay_visible {
            return Err(
                "Scan Japanese text and show its overlays before enabling Auto detect.".into(),
            );
        }
        let spec = session
            .last_scan
            .as_ref()
            .ok_or("Select a manga area first.")?;
        toolbar::live_display(&app, &spec.display)?;
        let frame = session
            .last_frame
            .clone()
            .ok_or("Rescan the manga area first.")?;
        session.auto_detect.enable(frame);
        session.phase = "ready";
        session.message = "Auto detect on. Turn the page within the same area.".into();
    } else {
        session.auto_detect.stop();
        if session.active.is_none() {
            session.phase = if session.overlay_visible {
                "ready"
            } else {
                "idle"
            };
        }
        session.message = "Auto detect stopped.".into();
    }
    session.revision += 1;
    if !enabled {
        if let Some(id) = session
            .active
            .as_ref()
            .filter(|scan| scan.auto_epoch.is_some())
            .map(|scan| scan.id)
        {
            toolbar::stop_scan_in_session(&app, &mut session, Some(id), "", false)?;
        }
    }
    drop(session);
    toolbar::emit_state(&app);
    Ok(())
}

impl Worker {
    pub fn stop(&self) {
        self.stopped.store(true, Ordering::Relaxed);
    }
    pub fn start(app: &AppHandle) {
        let app = app.clone();
        std::thread::spawn(move || {
            while !app
                .state::<crate::AppState>()
                .auto_worker
                .stopped
                .load(Ordering::Relaxed)
            {
                std::thread::sleep(Duration::from_millis(750));
                if let Err(error) = tick(&app) {
                    eprintln!("YomiMado: auto detection state unavailable: {error}");
                }
            }
        });
    }
}

fn tick(app: &AppHandle) -> Result<(), String> {
    let state = app.state::<crate::AppState>();
    let (epoch, spec) = {
        let session = state.scans.lock()?;
        if !session.auto_detect.enabled || session.active.is_some() {
            return Ok(());
        }
        (
            session.auto_detect.epoch,
            session.last_scan.clone().ok_or("Choose a new scan area.")?,
        )
    };
    if let Err(error) = sample_session(app, epoch, spec) {
        let mut session = state.scans.lock()?;
        // A failure from a stopped generation cannot stop a newly enabled one.
        if session.auto_detect.enabled && session.auto_detect.epoch == epoch {
            session.auto_detect.stop();
            session.revision += 1;
            session.phase = "error";
            session.message = format!("Auto detect stopped: {error}");
            drop(session);
            toolbar::emit_state(app);
        }
    }
    Ok(())
}

fn sample_session(app: &AppHandle, epoch: u64, spec: toolbar::ScanSpec) -> Result<(), String> {
    let state = app.state::<crate::AppState>();
    let mut display = toolbar::live_display(app, &spec.display)?;
    let selection = crate::full_display_selection(&mut display, spec.area)?;
    let paused = blocked(app)
        || app
            .get_webview_window("ocr-overlay")
            .is_some_and(|w| w.is_visible().unwrap_or(false) && !state.overlay_input.is_active());
    let frame = if paused {
        None
    } else {
        let mut masks = Vec::new();
        if let Some(window) = app.get_webview_window("toolbar") {
            if window.is_visible().map_err(|e| e.to_string())? {
                let position = window.inner_position().map_err(|e| e.to_string())?;
                let size = window.inner_size().map_err(|e| e.to_string())?;
                masks.push(CaptureMask::Opaque(Rectangle {
                    x: position.x as f64 - 8.0,
                    y: position.y as f64 - 8.0,
                    width: size.width as f64 + 16.0,
                    height: size.height as f64 + 16.0,
                }));
            }
        }
        if let Some(window) = app.get_webview_window("ocr-overlay") {
            if window.is_visible().map_err(|e| e.to_string())? {
                let position = window.inner_position().map_err(|e| e.to_string())?;
                masks.extend(
                    state
                        .overlay_input
                        .capture_masks(position.x as f64, position.y as f64)?,
                );
            }
        }
        Some(Frame::sampled(
            state
                .capture
                .sample(&display, selection)
                .map_err(|e| e.to_string())?,
            spec.area,
            &masks,
        ))
    };
    let mut session = state.scans.lock()?;
    // Stop/restart, manual scans and popup opening can overtake capture work.
    if !session.auto_detect.enabled
        || session.auto_detect.epoch != epoch
        || session.active.is_some()
    {
        return Ok(());
    }
    let previous_status = session.auto_detect.status;
    let ready = match frame {
        Some(frame) if !blocked(app) => session.auto_detect.observe(frame),
        _ => {
            session.auto_detect.pause();
            false
        }
    };
    let changed = previous_status != session.auto_detect.status;
    if changed {
        session.revision += 1;
        session.message = match session.auto_detect.status {
            "covered" => "Auto detect paused: too little of the page is visible. Hide translated panels or choose a larger reading area.",
            "paused" => "Auto detect paused while a learning popup or app window is open.",
            "settling" => "Auto detect is waiting for the page to settle.",
            _ => "Auto detect on. Turn the page within the same area.",
        }.into();
    }
    drop(session);
    if changed {
        toolbar::emit_state(app);
    }
    if ready {
        // begin() rechecks epoch, idle state and popup visibility under the same
        // lock used to open popups. Only one scan can own a session.
        crate::show_capture_window_on(
            app.clone(),
            if spec.estimated_reading_order {
                "scan=repeat&order=1"
            } else {
                "scan=repeat"
            },
            display,
            spec.mode,
            Some(spec),
            Some(epoch),
        )?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use image::Rgb;

    fn area() -> Rectangle {
        Rectangle {
            x: -1600.0,
            y: 100.0,
            width: 800.0,
            height: 1200.0,
        }
    }
    fn frame(value: u8) -> Frame {
        Frame::sampled(RgbImage::from_pixel(128, 128, Rgb([value; 3])), area(), &[])
    }
    fn watcher() -> AutoDetect {
        let mut detector = AutoDetect::default();
        detector.enable(frame(255));
        detector
    }

    fn highlight() -> Vec<Point> {
        let a = area();
        [(16.0, 16.0), (112.0, 16.0), (112.0, 112.0), (16.0, 112.0)]
            .into_iter()
            .map(|(x, y)| Point {
                x: a.x + x * a.width / 128.0,
                y: a.y + y * a.height / 128.0,
            })
            .collect()
    }

    fn highlighted(pixels: RgbImage, layers: usize) -> Frame {
        let points = highlight();
        let mut painted = pixels;
        // Synthetic compositor output, with the actual 14% fill and no input
        // events. Both frames keep the same pointer, polygon and control state.
        for y in 16..112 {
            for x in 16..112 {
                let mut color = painted.get_pixel(x, y).0.map(f64::from);
                for _ in 0..layers {
                    for (channel, tint) in [0.0, 128.0, 255.0].into_iter().enumerate() {
                        color[channel] = 0.86 * color[channel] + 0.14 * tint;
                    }
                }
                painted.put_pixel(x, y, Rgb(color.map(|v| v.round() as u8)));
            }
        }
        let masks: Vec<_> = (0..layers)
            .map(|_| CaptureMask::Highlight(points.clone()))
            .collect();
        Frame::sampled(painted, area(), &masks)
    }

    #[test]
    fn text_only_page_turn_is_detected_without_pointer_or_mask_changes() {
        let mut old = frame(255);
        let mut new = frame(255);
        for x in 32..96 {
            for y in 40..50 {
                old.pixels.put_pixel(x, y, Rgb([0; 3]));
            }
            for y in 72..82 {
                new.pixels.put_pixel(x, y, Rgb([0; 3]));
            }
        }
        let sample = highlighted(new.pixels.clone(), 1);
        let mut detector = AutoDetect::default();
        detector.enable(old.clone());
        // The former full-region masks discard every changed pixel and leave
        // the detector watching forever, even though a new page is visible.
        let bounds = CaptureMask::Highlight(highlight()).bounds();
        let former = Frame::sampled(
            sample.pixels.clone(),
            area(),
            &[CaptureMask::Opaque(bounds)],
        );
        assert_eq!(old.difference(&former), Some(0.0));
        assert!(!detector.observe(sample.clone()));
        assert!(detector.observe(sample.clone()));
        // A clean capture of this page followed by overlay repaint is not a
        // further page turn. This protects against repeating OCR on one page.
        detector.reset(new);
        for _ in 0..4 {
            assert!(!detector.observe(sample.clone()));
        }
    }

    #[test]
    fn highlight_render_hover_and_overlapping_regions_do_not_rescan() {
        for value in [0, 120, 255] {
            let mut detector = AutoDetect::default();
            detector.enable(frame(value));
            for layers in [1, 2, 1, 2] {
                assert!(!detector.observe(highlighted(frame(value).pixels, layers)));
                assert_eq!(detector.status, "watching");
            }
        }
    }

    #[test]
    fn highlight_compensation_preserves_visible_changes_in_every_color_channel() {
        for color in [[220, 120, 120], [120, 220, 120], [120, 120, 220]] {
            assert!(pixel_changed([120; 3], color, 1));
            assert!(pixel_changed(color, [120; 3], 1));
        }
    }

    #[test]
    fn polygon_interior_remains_visible_while_strokes_are_excluded() {
        let sampled = highlighted(frame(255).pixels, 1);
        assert!(!sampled.masked[64 * 128 + 64]);
        assert_eq!(sampled.tint_layers[64 * 128 + 64], 1);
        assert!(sampled.masked[16 * 128 + 64]);
        assert!(!sampled.masked[4 * 128 + 4]);
        // Real polygon geometry, rather than its rectangle, also handles a
        // slanted/concave result without hiding unrelated page corners.
        let a = area();
        let points = [(64.0, 16.0), (112.0, 64.0), (64.0, 112.0), (16.0, 64.0)]
            .into_iter()
            .map(|(x, y)| Point {
                x: a.x + x * a.width / 128.0,
                y: a.y + y * a.height / 128.0,
            })
            .collect();
        let slanted = Frame::sampled(frame(255).pixels, a, &[CaptureMask::Highlight(points)]);
        assert!(!slanted.masked[20 * 128 + 20]);
        assert_eq!(slanted.tint_layers[20 * 128 + 20], 0);
        assert_eq!(slanted.tint_layers[64 * 128 + 64], 1);
    }

    #[test]
    fn highlight_comparison_matches_the_shipped_rendering_contract() {
        let tokens = include_str!("../../src/styles/tokens.css");
        assert!(tokens.contains(&format!(
            "--color-region-fill: rgb({} {} {} / {});",
            HIGHLIGHT_RGB[0], HIGHLIGHT_RGB[1], HIGHLIGHT_RGB[2], HIGHLIGHT_ALPHA
        )));
        for state in ["hover", "selected"] {
            assert!(tokens.contains(&format!(
                "--color-region-{state}-fill: var(--color-region-fill);"
            )));
        }
    }

    #[test]
    fn unchanged_pages_and_cursor_sized_changes_do_not_scan() {
        let mut detector = watcher();
        for _ in 0..5 {
            assert!(!detector.observe(frame(255)));
        }
        let mut cursor = frame(255);
        for y in 40..44 {
            for x in 40..44 {
                cursor.pixels.put_pixel(x, y, Rgb([0; 3]));
            }
        }
        for _ in 0..5 {
            assert!(!detector.observe(cursor.clone()));
        }
        assert_eq!(detector.status, "watching");
    }

    #[test]
    fn a_changed_page_must_settle_and_completion_prevents_a_rescan_loop() {
        let mut detector = watcher();
        assert!(!detector.observe(frame(0)));
        assert_eq!(detector.status, "settling");
        assert!(detector.observe(frame(0)));
        detector.reset(frame(0));
        for _ in 0..5 {
            assert!(!detector.observe(frame(0)));
        }
        assert!(!detector.observe(frame(255)));
        assert!(detector.observe(frame(255)));
    }

    #[test]
    fn scrolling_and_page_animation_wait_until_motion_stops() {
        let mut detector = watcher();
        for value in [0, 80, 160, 0, 80] {
            assert!(!detector.observe(frame(value)));
        }
        assert!(detector.observe(frame(80)));
    }

    #[test]
    fn pause_preserves_page_change_but_requires_fresh_stable_samples() {
        let mut detector = watcher();
        assert!(!detector.observe(frame(0)));
        detector.pause();
        assert_eq!(detector.status, "paused");
        assert!(!detector.observe(frame(0)));
        assert!(detector.observe(frame(0)));
    }

    #[test]
    fn stop_and_restart_invalidate_old_generations_and_clear_motion_history() {
        let mut detector = watcher();
        let old = detector.epoch;
        detector.observe(frame(0));
        detector.stop();
        assert!(!detector.enabled);
        assert_eq!(detector.status, "off");
        assert!(detector.baseline.is_none());
        assert!(detector.previous.is_none());
        detector.enable(frame(255));
        assert_ne!(detector.epoch, old);
        assert!(!detector.observe(frame(0)));
    }

    #[test]
    fn painted_overlay_changes_are_ignored_using_physical_masks() {
        // Negative monitor origin and fractional-scale dimensions are already
        // in screen physical pixels, not multiplied by scale a second time.
        let mut painted = frame(255).pixels;
        for y in 16..48 {
            for x in 16..48 {
                painted.put_pixel(x, y, Rgb([0; 3]));
            }
        }
        let a = area();
        let mask = Rectangle {
            x: a.x + a.width / 8.0,
            y: a.y + a.height / 8.0,
            width: a.width / 4.0,
            height: a.height / 4.0,
        };
        let painted = Frame::sampled(painted, a, &[CaptureMask::Opaque(mask)]);
        let mut detector = watcher();
        for _ in 0..5 {
            assert!(!detector.observe(painted.clone()));
        }
        assert_eq!(detector.status, "watching");
    }

    #[test]
    fn moving_controls_are_masked_in_both_samples() {
        let a = area();
        let mut old = frame(0);
        let mut new = frame(0);
        old.masked[0..2000].fill(true);
        new.masked[2000..4000].fill(true);
        for i in 0..4000 {
            new.pixels.put_pixel(i % 128, i / 128, Rgb([255; 3]));
        }
        assert_eq!(old.difference(&new), Some(0.0));
        assert_eq!(
            Frame::sampled(
                frame(0).pixels,
                a,
                &[CaptureMask::Opaque(Rectangle { x: 0.0, ..a })]
            )
            .masked
            .iter()
            .filter(|m| **m)
            .count(),
            0
        );
    }

    #[test]
    fn heavily_obscured_pages_pause_instead_of_guessing_from_a_corner() {
        let mut detector = watcher();
        let a = area();
        let obscured = Frame::sampled(
            frame(0).pixels,
            a,
            &[CaptureMask::Opaque(Rectangle {
                width: a.width * 0.8,
                ..a
            })],
        );
        for _ in 0..5 {
            assert!(!detector.observe(obscured.clone()));
        }
        assert_eq!(detector.status, "covered");
        assert!(!detector.observe(frame(0)));
        assert!(detector.observe(frame(0)));
    }

    #[test]
    fn minor_pixel_noise_does_not_make_a_page_change() {
        let mut detector = watcher();
        for value in [250, 240, 250, 240] {
            assert!(!detector.observe(frame(value)));
        }
    }

    #[test]
    fn png_capture_baseline_matches_raw_sampling_and_rejects_bad_data() {
        use base64::prelude::*;
        use image::ImageEncoder;
        let image = image::RgbaImage::from_pixel(320, 640, image::Rgba([120, 80, 40, 255]));
        let mut bytes = Vec::new();
        image::codecs::png::PngEncoder::new(&mut bytes)
            .write_image(image.as_raw(), 320, 640, image::ExtendedColorType::Rgba8)
            .unwrap();
        let mut captured = CapturedImage {
            image_data_url: format!("data:image/png;base64,{}", BASE64_STANDARD.encode(bytes)),
            metadata: crate::capture::CaptureMetadata {
                display_id: "test".into(),
                display_name: "test".into(),
                screen_physical_bounds: area(),
                selection_physical_bounds: area(),
                selection_logical_bounds: area(),
                image_width: 320,
                image_height: 640,
                scale_factor: 1.25,
            },
        };
        let sample = Frame::sampled(crate::capture::thumbnail(&image), area(), &[]);
        assert_eq!(
            Frame::captured(&captured).unwrap().difference(&sample),
            Some(0.0)
        );
        captured.image_data_url = "bad".into();
        assert!(Frame::captured(&captured).is_err());
    }
}

#[cfg(test)]
mod session_tests {
    use super::*;
    use crate::{
        capture::DisplayInfo,
        toolbar::{ScanMode, ScanSpec, Session},
    };
    fn image() -> Frame {
        Frame {
            pixels: RgbImage::new(128, 128),
            masked: vec![false; 128 * 128],
            tint_layers: vec![0; 128 * 128],
        }
    }
    fn metadata() -> crate::capture::CaptureMetadata {
        let bounds = Rectangle {
            x: -2000.0,
            y: 100.0,
            width: 800.0,
            height: 1200.0,
        };
        crate::capture::CaptureMetadata {
            display_id: "left".into(),
            display_name: "Left".into(),
            screen_physical_bounds: bounds,
            selection_physical_bounds: bounds,
            selection_logical_bounds: bounds,
            image_width: 800,
            image_height: 1200,
            scale_factor: 1.25,
        }
    }
    fn session() -> (Session, u64) {
        let m = metadata();
        let d = DisplayInfo {
            id: m.display_id.clone(),
            name: m.display_name.clone(),
            physical_bounds: m.screen_physical_bounds,
            selector_physical_bounds: m.screen_physical_bounds,
            scale_factor: 1.25,
            viewport_width: 640.0,
            viewport_height: 960.0,
        };
        let mut session = Session {
            last_scan: Some(ScanSpec {
                mode: ScanMode::SelectedArea,
                display: d.clone(),
                area: m.selection_physical_bounds,
                estimated_reading_order: true,
            }),
            ..Session::default()
        };
        session.auto_detect.enable(image());
        let epoch = session.auto_detect.epoch;
        let id = session
            .begin(ScanMode::SelectedArea, d, None, vec![])
            .unwrap();
        session.active.as_mut().unwrap().auto_epoch = Some(epoch);
        session.captured(id, m).unwrap();
        session.active.as_mut().unwrap().frame = Some(image());
        (session, id)
    }
    #[test]
    fn a_blank_page_keeps_watching_and_keeps_the_original_area() {
        let (mut s, id) = session();
        let epoch = s.auto_detect.epoch;
        s.stop(Some(id), "No text", true).unwrap();
        assert!(s.auto_detect.enabled);
        assert_eq!(s.auto_detect.epoch, epoch);
        assert_eq!(s.auto_detect.status, "watching");
        assert!(s.last_frame.is_some());
        assert_eq!(s.last_scan.as_ref().unwrap().area.x, -2000.0);
        assert!(s.active.is_none());
        assert!(s.complete(id, true).is_err());
    }
    #[test]
    fn stopping_or_failing_an_automatic_scan_invalidates_late_publication() {
        for error in ["", "OCR failed"] {
            let (mut s, id) = session();
            let epoch = s.auto_detect.epoch;
            s.stop(Some(id), error, false).unwrap();
            assert!(!s.auto_detect.enabled);
            assert_ne!(s.auto_detect.epoch, epoch);
            assert!(s.complete(id, true).is_err());
        }
    }
    #[test]
    fn completion_preserves_reading_order_and_rebaselines_the_new_page() {
        let (mut s, id) = session();
        let epoch = s.auto_detect.epoch;
        s.complete(id, true).unwrap();
        assert!(s.auto_detect.enabled);
        assert_eq!(s.auto_detect.epoch, epoch);
        assert!(s.last_scan.as_ref().unwrap().estimated_reading_order);
        assert!(!s.auto_detect.observe(image()));
        assert!(!s.auto_detect.observe(image()));
        assert!(s
            .begin(
                ScanMode::SelectedArea,
                s.last_scan.as_ref().unwrap().display.clone(),
                None,
                vec![]
            )
            .is_ok());
        assert!(s.complete(id, true).is_err());
    }
}
