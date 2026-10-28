//! Opt-in page-change monitoring. Pixels stay in memory; OCR uses the existing
//! clean Rescan path. All lifecycle decisions share the scan-session lock.
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

#[derive(Clone, Debug)]
pub struct Frame {
    pixels: RgbImage,
    masked: Vec<bool>,
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
        })
    }

    fn sampled(pixels: RgbImage, area: Rectangle, masks: &[Rectangle]) -> Self {
        let mut masked = vec![false; 128 * 128];
        for (i, mask) in masked.iter_mut().enumerate() {
            // Include a thumbnail cell's full footprint, not just its centre.
            let x = area.x + (i % 128) as f64 * area.width / 128.0;
            let y = area.y + (i / 128) as f64 * area.height / 128.0;
            *mask = masks.iter().any(|m| {
                x <= m.x + m.width
                    && y <= m.y + m.height
                    && x + area.width / 128.0 >= m.x
                    && y + area.height / 128.0 >= m.y
            });
        }
        Self { pixels, masked }
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
            if a.0.iter().zip(b.0).any(|(a, b)| a.abs_diff(b) > 24) {
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
                masks.push(Rectangle {
                    x: position.x as f64 - 8.0,
                    y: position.y as f64 - 8.0,
                    width: size.width as f64 + 16.0,
                    height: size.height as f64 + 16.0,
                });
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
        let painted = Frame::sampled(painted, a, &[mask]);
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
            Frame::sampled(frame(0).pixels, a, &[Rectangle { x: 0.0, ..a }])
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
            &[Rectangle {
                width: a.width * 0.8,
                ..a
            }],
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
