use std::sync::{
    atomic::{AtomicU64, Ordering},
    Mutex, MutexGuard,
};

use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter, LogicalSize, Manager, PhysicalPosition, PhysicalSize};

use crate::capture::{CaptureMetadata, DisplayInfo, Rectangle};

pub const TOOLBAR_EVENT: &str = "toolbar-state-changed";
const SCREEN_INSET: f64 = 12.0;

#[derive(Clone, Copy, Debug, Deserialize, Serialize, PartialEq)]
#[serde(rename_all = "camelCase")]
pub enum ScanMode {
    SelectedArea,
    WholeScreen,
}

#[derive(Clone, Debug)]
pub struct ScanSpec {
    pub mode: ScanMode,
    pub display: DisplayInfo,
    pub area: Rectangle,
    pub estimated_reading_order: bool,
}

#[derive(Clone)]
pub struct ActiveScan {
    pub id: u64,
    pub mode: ScanMode,
    pub display: DisplayInfo,
    pub repeat: Option<ScanSpec>,
    pub restore: Vec<String>,
    pub captured: Option<CaptureMetadata>,
}

#[derive(Clone, Default)]
pub struct Session {
    pub revision: u64,
    pub active: Option<ActiveScan>,
    pub last_scan: Option<ScanSpec>,
    pub completed_id: Option<u64>,
    pub overlay_visible: bool,
    pub phase: &'static str,
    pub message: String,
}

impl Session {
    pub fn begin(
        &mut self,
        mode: ScanMode,
        display: DisplayInfo,
        repeat: Option<ScanSpec>,
        restore: Vec<String>,
    ) -> Result<u64, String> {
        if self.active.is_some() {
            return Err("A scan is already running. Cancel it before starting another.".into());
        }
        self.revision += 1;
        let id = self.revision;
        self.active = Some(ActiveScan {
            id,
            mode,
            display,
            repeat,
            restore,
            captured: None,
        });
        self.phase = "selecting";
        self.message = "Drag to select Japanese text. Escape cancels.".into();
        Ok(id)
    }

    pub fn active(&self, id: Option<u64>) -> Result<&ActiveScan, String> {
        self.active
            .as_ref()
            .filter(|scan| id.is_none_or(|id| id == scan.id))
            .ok_or_else(|| "This scan was cancelled or replaced.".into())
    }

    pub fn captured(&mut self, id: u64, metadata: CaptureMetadata) -> Result<(), String> {
        self.active(Some(id))?;
        self.active.as_mut().unwrap().captured = Some(metadata);
        self.revision += 1;
        self.phase = "recognizing";
        self.message = "Recognizing Japanese text locally…".into();
        Ok(())
    }

    pub fn complete(
        &mut self,
        id: u64,
        estimated_reading_order: bool,
    ) -> Result<ActiveScan, String> {
        let scan = self.active(Some(id))?;
        let metadata = scan.captured.as_ref().ok_or("No capture is available")?;
        self.last_scan = Some(ScanSpec {
            mode: scan.mode,
            display: scan.display.clone(),
            area: metadata.selection_physical_bounds,
            estimated_reading_order,
        });
        self.revision += 1;
        self.phase = "ready";
        self.message = "Click a text region to learn.".into();
        self.overlay_visible = true;
        self.completed_id = Some(id);
        Ok(self.active.take().unwrap())
    }

    pub fn stop(
        &mut self,
        id: Option<u64>,
        message: &str,
        no_text: bool,
    ) -> Result<ActiveScan, String> {
        self.active(id)?;
        self.revision += 1;
        self.phase = if message.is_empty() {
            "idle"
        } else if no_text {
            "noText"
        } else {
            "error"
        };
        self.message = if message.is_empty() {
            "Scan cancelled. Ready when you are.".into()
        } else {
            message.into()
        };
        Ok(self.active.take().unwrap())
    }
}

#[derive(Default)]
pub struct ScanStore {
    session: Mutex<Session>,
    selector_id: AtomicU64,
}

impl ScanStore {
    pub fn lock(&self) -> Result<MutexGuard<'_, Session>, String> {
        self.session.lock().map_err(|error| error.to_string())
    }

    pub fn set_selector_id(&self, id: u64) {
        self.selector_id.store(id, Ordering::Release);
    }

    pub fn selector_id(&self) -> Option<u64> {
        let id = self.selector_id.load(Ordering::Acquire);
        (id != 0).then_some(id)
    }
}

fn same_rectangle(a: Rectangle, b: Rectangle) -> bool {
    a.x == b.x && a.y == b.y && a.width == b.width && a.height == b.height
}

pub fn validate_display(expected: &DisplayInfo, current: &DisplayInfo) -> Result<(), String> {
    if expected.id != current.id
        || !same_rectangle(expected.physical_bounds, current.physical_bounds)
        || expected.scale_factor != current.scale_factor
    {
        return Err(
            "The display layout changed. Choose Selected Area or Whole Screen again.".into(),
        );
    }
    Ok(())
}

pub fn validate_area(area: Rectangle, display: &DisplayInfo) -> Result<(), String> {
    let bounds = display.physical_bounds;
    if ![area.x, area.y, area.width, area.height]
        .iter()
        .all(|v| v.is_finite())
        || area.width <= 0.0
        || area.height <= 0.0
        || area.x < bounds.x
        || area.y < bounds.y
        || area.x + area.width > bounds.x + bounds.width
        || area.y + area.height > bounds.y + bounds.height
    {
        return Err("The saved area no longer fits this display. Select a new area.".into());
    }
    Ok(())
}

pub fn display_from_monitor(monitor: &tauri::Monitor) -> DisplayInfo {
    let position = monitor.position();
    let size = monitor.size();
    let name = monitor.name().cloned();
    let bounds = Rectangle {
        x: f64::from(position.x),
        y: f64::from(position.y),
        width: f64::from(size.width),
        height: f64::from(size.height),
    };
    DisplayInfo {
        id: name
            .clone()
            .unwrap_or_else(|| format!("{},{}", position.x, position.y)),
        name: name.unwrap_or_else(|| "Unnamed display".into()),
        physical_bounds: bounds,
        selector_physical_bounds: bounds,
        scale_factor: monitor.scale_factor(),
        viewport_width: bounds.width / monitor.scale_factor(),
        viewport_height: bounds.height / monitor.scale_factor(),
    }
}

pub fn live_display(app: &AppHandle, expected: &DisplayInfo) -> Result<DisplayInfo, String> {
    let display = app
        .available_monitors()
        .map_err(|error| error.to_string())?
        .iter()
        .map(display_from_monitor)
        .find(|display| {
            display.id == expected.id
                && same_rectangle(display.physical_bounds, expected.physical_bounds)
        })
        .ok_or("The scan's display is no longer available. Choose a new scan area.")?;
    validate_display(expected, &display)?;
    Ok(display)
}

pub fn pointer_display(app: &AppHandle) -> Result<DisplayInfo, String> {
    let pointer = app.cursor_position().map_err(|error| error.to_string())?;
    app.monitor_from_point(pointer.x, pointer.y)
        .map_err(|error| error.to_string())?
        .as_ref()
        .map(display_from_monitor)
        .ok_or_else(|| "No monitor under the pointer".into())
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ToolbarState {
    revision: u64,
    session_id: Option<u64>,
    phase: &'static str,
    message: String,
    can_rescan: bool,
    has_overlay: bool,
    overlay_visible: bool,
    display_name: String,
    available_width: f64,
    detector_model: crate::detector_model::DetectorModelStatus,
}

#[tauri::command(async)]
pub fn get_toolbar_state(app: AppHandle) -> Result<ToolbarState, String> {
    let state = app.state::<crate::AppState>();
    let session = state.scans.lock()?.clone();
    let monitor = app
        .get_webview_window("toolbar")
        .and_then(|window| window.current_monitor().ok().flatten());
    let available_width = monitor
        .as_ref()
        .map(|monitor| {
            (f64::from(monitor.work_area().size.width) / monitor.scale_factor()
                - 2.0 * SCREEN_INSET)
                .max(112.0)
        })
        .unwrap_or(520.0);
    let display_name = session
        .active
        .as_ref()
        .map(|scan| scan.display.name.clone())
        .or_else(|| {
            crate::current_display(&app, "toolbar")
                .ok()
                .map(|display| display.name)
        })
        .unwrap_or_else(|| "Current monitor".into());
    Ok(ToolbarState {
        revision: session.revision,
        session_id: session.active.as_ref().map(|scan| scan.id),
        phase: if session.phase.is_empty() {
            "idle"
        } else {
            session.phase
        },
        message: if session.message.is_empty() {
            "Ready to scan Japanese text.".into()
        } else {
            session.message.clone()
        },
        can_rescan: session.last_scan.is_some(),
        has_overlay: state.overlay.get().is_ok(),
        overlay_visible: session.overlay_visible,
        display_name,
        available_width,
        detector_model: crate::detector_model::detector_model_status(app.clone())?,
    })
}

pub fn emit_state(app: &AppHandle) {
    match get_toolbar_state(app.clone()).and_then(|snapshot| {
        app.emit_to("toolbar", TOOLBAR_EVENT, snapshot)
            .map_err(|e| e.to_string())
    }) {
        Ok(()) => {}
        Err(error) => eprintln!("YomiMado: could not publish toolbar status: {error}"),
    }
}

pub fn restore_windows(app: &AppHandle, scan: &ActiveScan, results: bool) -> Result<(), String> {
    let previous = if results {
        app.state::<crate::AppState>().overlay.get().ok()
    } else {
        None
    };
    let restore_generation = previous
        .as_ref()
        .and_then(|result| result["sessionId"].as_u64());
    let restore_results = results
        && previous
            .as_ref()
            .and_then(|result| result.get("metadata").cloned())
            .and_then(|metadata| serde_json::from_value::<CaptureMetadata>(metadata).ok())
            .is_some_and(|metadata| {
                let expected = DisplayInfo {
                    id: metadata.display_id,
                    name: metadata.display_name,
                    physical_bounds: metadata.screen_physical_bounds,
                    scale_factor: metadata.scale_factor,
                    ..scan.display.clone()
                };
                live_display(app, &expected).is_ok()
            });
    for label in &scan.restore {
        if !restore_results && (label == "ocr-overlay" || label == "translation-popup") {
            continue;
        }
        if let Some(window) = app.get_webview_window(label) {
            if label == "ocr-overlay" {
                if let Some(generation) = restore_generation {
                    let mut url = window.url().map_err(|e| e.to_string())?;
                    url.set_query(Some(&format!(
                        "mode=overlay&session={generation}&restore={}",
                        scan.id
                    )));
                    window.navigate(url).map_err(|e| e.to_string())?;
                }
            }
            window.show().map_err(|error| error.to_string())?;
        }
    }
    Ok(())
}

pub fn stop_scan(
    app: &AppHandle,
    id: Option<u64>,
    message: &str,
    no_text: bool,
) -> Result<(), String> {
    let state = app.state::<crate::AppState>();
    let restored = {
        let mut session = state.scans.lock()?;
        if session.active(id).is_err() {
            return Ok(());
        }
        let stopped = session.stop(id, message, no_text)?;
        if let Some(selector) = app.get_webview_window("capture-selector") {
            selector.hide().map_err(|error| error.to_string())?;
        }
        // Keep restoration in the same transaction as cancellation so a new
        // scan cannot start between clearing state and restoring old windows.
        let restored = restore_windows(app, &stopped, true);
        session.overlay_visible = app
            .get_webview_window("ocr-overlay")
            .is_some_and(|window| window.is_visible().unwrap_or(false));
        restored
    };
    emit_state(app);
    restored
}

#[tauri::command(async)]
pub fn hide_finished_selector(app: AppHandle, session_id: u64) -> Result<(), String> {
    let state = app.state::<crate::AppState>();
    let session = state.scans.lock()?;
    if session.active.is_none() && session.completed_id == Some(session_id) {
        if let Some(selector) = app.get_webview_window("capture-selector") {
            selector.hide().map_err(|e| e.to_string())?;
        }
    }
    Ok(())
}

#[tauri::command(async)]
pub fn reveal_ocr_overlay(
    app: AppHandle,
    session_id: u64,
) -> Result<Option<serde_json::Value>, String> {
    let state = app.state::<crate::AppState>();
    let session = state.scans.lock()?;
    if session.active.is_none()
        && session.completed_id == Some(session_id)
        && session.overlay_visible
    {
        return crate::overlay::reveal_overlay(&app, &state.overlay).map(Some);
    }
    Ok(None)
}

#[tauri::command(async)]
pub fn finish_scan(
    app: AppHandle,
    session_id: u64,
    message: String,
    no_text: Option<bool>,
) -> Result<(), String> {
    stop_scan(&app, Some(session_id), &message, no_text.unwrap_or(false))
}

#[tauri::command(async)]
pub fn start_toolbar_scan(app: AppHandle, mode: ScanMode) -> Result<(), String> {
    let display = crate::current_display(&app, "toolbar")?;
    let query = if mode == ScanMode::WholeScreen {
        "scan=whole"
    } else {
        ""
    };
    crate::show_capture_window_on(app, query, display, mode, None)
}

#[tauri::command(async)]
pub fn rescan(app: AppHandle) -> Result<(), String> {
    let spec = app
        .state::<crate::AppState>()
        .scans
        .lock()?
        .last_scan
        .clone()
        .ok_or("Scan an area or screen first.")?;
    let display = live_display(&app, &spec.display)?;
    validate_area(spec.area, &display)?;
    let query = if spec.estimated_reading_order {
        "scan=repeat&order=1"
    } else {
        "scan=repeat"
    };
    crate::show_capture_window_on(app, query, display, spec.mode, Some(spec))
}

#[tauri::command(async)]
pub fn set_overlay_visibility(app: AppHandle, visible: bool) -> Result<(), String> {
    let state = app.state::<crate::AppState>();
    let mut session = state.scans.lock()?;
    if session.active.is_some() {
        return Err("Wait for the scan to finish.".into());
    }
    state.overlay.get()?;
    let window = app
        .get_webview_window("ocr-overlay")
        .ok_or("No OCR overlay is available")?;
    if visible {
        if let Some(spec) = &session.last_scan {
            live_display(&app, &spec.display)?;
        }
        let generation = session
            .completed_id
            .ok_or("No completed OCR result is available")?;
        let mut url = window.url().map_err(|e| e.to_string())?;
        url.set_query(Some(&format!(
            "mode=overlay&session={generation}&restore={}",
            session.revision + 1
        )));
        window.navigate(url).map_err(|e| e.to_string())?;
    } else {
        window.hide().map_err(|error| error.to_string())?;
        if let Some(popup) = app.get_webview_window("translation-popup") {
            popup.hide().map_err(|e| e.to_string())?;
        }
    }
    session.overlay_visible = visible;
    session.revision += 1;
    session.message = if visible {
        "Overlay restored. Rescan if the page has changed."
    } else {
        "OCR overlays hidden. Results are kept locally for this session."
    }
    .into();
    drop(session);
    emit_state(&app);
    Ok(())
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub enum SecondaryView {
    Words,
    Sentences,
    Settings,
    Sources,
}

#[tauri::command(async)]
pub fn show_secondary_window(app: AppHandle, view: SecondaryView) -> Result<(), String> {
    if app
        .state::<crate::AppState>()
        .scans
        .lock()?
        .active
        .is_some()
    {
        return Err("Finish or cancel the scan before opening settings.".into());
    }
    let name = match view {
        SecondaryView::Words => "words",
        SecondaryView::Sentences => "sentences",
        SecondaryView::Settings => "settings",
        SecondaryView::Sources => "sources",
    };
    let window = app
        .get_webview_window("main")
        .ok_or("Settings window is unavailable")?;
    let mut url = window.url().map_err(|e| e.to_string())?;
    url.set_query(Some(&format!("view={name}")));
    window.navigate(url).map_err(|e| e.to_string())?;
    window.unminimize().map_err(|e| e.to_string())?;
    window.show().map_err(|e| e.to_string())?;
    window.set_focus().map_err(|e| e.to_string())
}

fn clamped_position(
    x: f64,
    y: f64,
    width: f64,
    height: f64,
    area: Rectangle,
    scale: f64,
) -> (i32, i32) {
    let inset = SCREEN_INSET * scale;
    let max_x = (area.x + area.width - width - inset).max(area.x);
    let max_y = (area.y + area.height - height - inset).max(area.y);
    (
        x.clamp((area.x + inset).min(max_x), max_x).round() as i32,
        y.clamp((area.y + inset).min(max_y), max_y).round() as i32,
    )
}

#[tauri::command(async)]
pub fn resize_toolbar(
    app: AppHandle,
    logical_width: f64,
    logical_height: f64,
) -> Result<(), String> {
    if !logical_width.is_finite()
        || !logical_height.is_finite()
        || !(80.0..=900.0).contains(&logical_width)
        || !(40.0..=700.0).contains(&logical_height)
    {
        return Err("Invalid toolbar dimensions".into());
    }
    let window = app
        .get_webview_window("toolbar")
        .ok_or("Toolbar is unavailable")?;
    let monitor = window
        .current_monitor()
        .map_err(|e| e.to_string())?
        .ok_or("No active monitor")?;
    let scale = monitor.scale_factor();
    let work = monitor.work_area();
    let area = Rectangle {
        x: f64::from(work.position.x),
        y: f64::from(work.position.y),
        width: f64::from(work.size.width),
        height: f64::from(work.size.height),
    };
    let width = (logical_width * scale).ceil().min(area.width);
    let height = (logical_height * scale).ceil().min(area.height);
    let position = window.outer_position().map_err(|e| e.to_string())?;
    let (x, y) = clamped_position(
        f64::from(position.x),
        f64::from(position.y),
        width,
        height,
        area,
        scale,
    );
    window
        .set_size(PhysicalSize::new(width as u32, height as u32))
        .map_err(|e| e.to_string())?;
    window
        .set_position(PhysicalPosition::new(x, y))
        .map_err(|e| e.to_string())
}

#[tauri::command(async)]
pub fn move_toolbar(app: AppHandle, dx: f64, dy: f64) -> Result<(), String> {
    if !dx.is_finite() || !dy.is_finite() || dx.abs() > 32.0 || dy.abs() > 32.0 {
        return Err("Invalid toolbar movement".into());
    }
    let window = app
        .get_webview_window("toolbar")
        .ok_or("Toolbar is unavailable")?;
    let p = window.outer_position().map_err(|e| e.to_string())?;
    let scale = window.scale_factor().map_err(|e| e.to_string())?;
    window
        .set_position(PhysicalPosition::new(
            (f64::from(p.x) + dx * scale).round() as i32,
            (f64::from(p.y) + dy * scale).round() as i32,
        ))
        .map_err(|e| e.to_string())?;
    let size = window
        .inner_size()
        .map_err(|e| e.to_string())?
        .to_logical::<f64>(scale);
    resize_toolbar(app, size.width, size.height)
}

#[tauri::command(async)]
pub fn drag_toolbar(app: AppHandle) -> Result<(), String> {
    app.get_webview_window("toolbar")
        .ok_or("Toolbar is unavailable")?
        .start_dragging()
        .map_err(|e| e.to_string())
}

#[tauri::command(async)]
pub fn resume_capture_selection(
    app: AppHandle,
    session_id: u64,
    debug: bool,
) -> Result<(), String> {
    {
        let state = app.state::<crate::AppState>();
        let mut session = state.scans.lock()?;
        session.active(Some(session_id))?;
        session.revision += 1;
        session.phase = if debug { "reviewing" } else { "selecting" };
        session.message = if debug {
            "Reviewing the local capture."
        } else {
            "Drag a reading area to continue."
        }
        .into();
    }
    for label in ["toolbar", "main"] {
        if let Some(window) = app.get_webview_window(label) {
            window.hide().map_err(|e| e.to_string())?;
        }
    }
    let selector = app
        .get_webview_window("capture-selector")
        .ok_or("Capture selector is unavailable")?;
    selector.show().map_err(|e| e.to_string())?;
    selector.set_focus().map_err(|e| e.to_string())?;
    emit_state(&app);
    Ok(())
}

#[tauri::command(async)]
pub fn quit_app(app: AppHandle) {
    app.exit(0);
}

pub fn setup(app: &AppHandle) -> Result<(), String> {
    let window = app
        .get_webview_window("toolbar")
        .ok_or("Toolbar is unavailable")?;
    #[cfg(target_os = "windows")]
    window.set_shadow(false).map_err(|e| e.to_string())?;
    // Start within the work area; later resizing also clamps restored dimensions.
    window
        .set_size(LogicalSize::new(560.0, 56.0))
        .map_err(|e| e.to_string())?;
    resize_toolbar(app.clone(), 560.0, 56.0)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn display() -> DisplayInfo {
        DisplayInfo {
            id: "left".into(),
            name: "Left monitor".into(),
            physical_bounds: Rectangle {
                x: -1920.0,
                y: 0.0,
                width: 1920.0,
                height: 1080.0,
            },
            selector_physical_bounds: Rectangle {
                x: -1920.0,
                y: 0.0,
                width: 1920.0,
                height: 1080.0,
            },
            scale_factor: 1.5,
            viewport_width: 1280.0,
            viewport_height: 720.0,
        }
    }
    fn metadata() -> CaptureMetadata {
        CaptureMetadata {
            display_id: "left".into(),
            display_name: "Left monitor".into(),
            screen_physical_bounds: display().physical_bounds,
            selection_physical_bounds: Rectangle {
                x: -1800.0,
                y: 80.0,
                width: 300.0,
                height: 200.0,
            },
            selection_logical_bounds: Rectangle {
                x: 80.0,
                y: 80.0 / 1.5,
                width: 200.0,
                height: 200.0 / 1.5,
            },
            image_width: 300,
            image_height: 200,
            scale_factor: 1.5,
        }
    }
    #[test]
    fn cancelled_scan_cannot_publish_or_replace_last_success() {
        let mut state = Session::default();
        let id = state
            .begin(
                ScanMode::SelectedArea,
                display(),
                None,
                vec!["toolbar".into()],
            )
            .unwrap();
        state.captured(id, metadata()).unwrap();
        state.complete(id, true).unwrap();
        let next = state
            .begin(ScanMode::WholeScreen, display(), None, vec![])
            .unwrap();
        state.stop(Some(next), "", false).unwrap();
        assert!(state.captured(next, metadata()).is_err());
        assert!(state.complete(next, false).is_err());
        assert_eq!(state.last_scan.unwrap().mode, ScanMode::SelectedArea);
    }
    #[test]
    fn single_scan_admission_and_old_failure_cannot_cancel_new_scan() {
        let mut state = Session::default();
        let id = state
            .begin(ScanMode::SelectedArea, display(), None, vec![])
            .unwrap();
        assert!(state
            .begin(ScanMode::WholeScreen, display(), None, vec![])
            .is_err());
        state.stop(Some(id), "OCR unavailable", false).unwrap();
        let next = state
            .begin(ScanMode::WholeScreen, display(), None, vec![])
            .unwrap();
        assert!(state.stop(Some(id), "late error", false).is_err());
        assert_eq!(state.active.unwrap().id, next);
    }

    #[test]
    fn no_text_does_not_make_an_unsuccessful_area_rescannable() {
        let mut state = Session::default();
        let id = state
            .begin(ScanMode::SelectedArea, display(), None, vec![])
            .unwrap();
        state.captured(id, metadata()).unwrap();
        state.stop(Some(id), "No text detected", true).unwrap();
        assert_eq!(state.phase, "noText");
        assert!(state.last_scan.is_none());
        assert!(state.completed_id.is_none());
    }
    #[test]
    fn rescan_rejects_scale_layout_and_monitor_changes() {
        for change in 0..3 {
            let expected = display();
            let mut actual = expected.clone();
            match change {
                0 => actual.scale_factor = 2.0,
                1 => actual.physical_bounds.x = 0.0,
                _ => actual.id = "other".into(),
            };
            assert!(validate_display(&expected, &actual).is_err());
        }
        assert!(validate_display(&display(), &display()).is_ok());
        assert!(validate_area(metadata().selection_physical_bounds, &display()).is_ok());
        assert!(validate_area(
            Rectangle {
                x: 0.0,
                y: 0.0,
                width: 100.0,
                height: 100.0
            },
            &display()
        )
        .is_err());
    }
    #[test]
    fn toolbar_resize_clamps_negative_work_area_at_fractional_scale() {
        let area = Rectangle {
            x: -1920.0,
            y: 30.0,
            width: 1920.0,
            height: 1000.0,
        };
        assert_eq!(
            clamped_position(-100.0, 1000.0, 840.0, 84.0, area, 1.5),
            (-858, 928)
        );
        assert_eq!(
            clamped_position(-3000.0, -100.0, 168.0, 72.0, area, 1.5),
            (-1902, 48)
        );
    }
}
