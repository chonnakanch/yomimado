mod capture;
mod detector_model;
mod overlay;
mod toolbar;
#[cfg(all(target_os = "windows", any(not(debug_assertions), test)))]
mod windows_service;

use std::process::Child;
use std::sync::{Arc, Mutex};

use capture::{
    cleanup_legacy_captures, crop_detected_page, CaptureMetadata, CapturedImage, DisplayInfo,
    Rectangle, ScreenCapture, ViewportSize, XcapScreenCapture,
};
use serde::{Deserialize, Serialize};
use tauri::{
    AppHandle, Emitter, Manager, PhysicalPosition, PhysicalSize, WebviewUrl, WebviewWindowBuilder,
};
use tauri_plugin_global_shortcut::{
    Builder as GlobalShortcutBuilder, GlobalShortcutExt, Shortcut, ShortcutState,
};

const MANUAL_CAPTURE_SHORTCUT: &str = "CMDORCONTROL+SHIFT+O";
const WHOLE_SCREEN_SHORTCUT: &str = "CMDORCONTROL+SHIFT+S";

struct AppState {
    capture: Arc<dyn ScreenCapture>,
    overlay: overlay::OverlayStore,
    overlay_input: overlay::input::InputRouter,
    scans: toolbar::ScanStore,
    toolbar_layout: Mutex<toolbar::ToolbarLayout>,
    toolbar_menu: toolbar::ToolbarMenuStore,
    service: Mutex<Option<Child>>,
    #[cfg(all(not(debug_assertions), target_os = "windows"))]
    windows_service: Mutex<Option<windows_service::Service>>,
}

#[cfg(all(not(debug_assertions), target_os = "macos"))]
fn start_bundled_service(app: &tauri::App) -> Result<Child, Box<dyn std::error::Error>> {
    use std::process::Command;

    let resources = app.path().resource_dir()?.join("ocr");
    let assets = resources.join("assets");
    let data = app.path().app_data_dir()?;
    std::fs::create_dir_all(&data)?;
    let child = Command::new(resources.join("runtime/yomimado-ocr"))
        .env("YOMIMADO_OCR_PORT", "8766")
        .env("YOMIMADO_DETECTOR_REPO", assets.join("comic-text-detector"))
        .env(
            "YOMIMADO_DETECTOR_MODEL",
            detector_model::installed_path(app.handle())?,
        )
        .env("YOMIMADO_MANGA_OCR_MODEL", assets.join("manga-ocr-base"))
        .env("YOMIMADO_TRANSLATION_MODEL", assets.join("opus-mt-ja-en"))
        .env("YOMIMADO_JMDICT", assets.join("JMdict_e.gz"))
        .env("YOMIMADO_KANJIDIC2", assets.join("kanjidic2.xml.gz"))
        .env("YOMIMADO_JMDICT_INDEX", data.join("jmdict-index.sqlite3"))
        .env("YOMIMADO_VOCAB_DB", data.join("vocabulary.sqlite3"))
        .env(
            "YOMIMADO_TRANSLATION_CACHE",
            data.join("translation.sqlite3"),
        )
        .env("HF_HUB_OFFLINE", "1")
        .env("TRANSFORMERS_OFFLINE", "1")
        .spawn()?;
    Ok(child)
}

fn current_display(app: &AppHandle, window_label: &str) -> Result<DisplayInfo, String> {
    let window = app
        .get_webview_window(window_label)
        .ok_or_else(|| format!("{window_label} window is unavailable"))?;
    let monitor = window
        .current_monitor()
        .map_err(|error| error.to_string())?
        .ok_or("No active monitor")?;
    Ok(toolbar::display_from_monitor(&monitor))
}

// WebView2 creation deadlocks inside Windows synchronous IPC/event handlers.
// Both platforms also keep session coordination off the UI thread.
#[tauri::command(async)]
fn show_capture_selector(app: AppHandle) -> Result<(), String> {
    show_capture_window(app, "")
}

#[tauri::command(async)]
fn show_auto_scanner(app: AppHandle) -> Result<(), String> {
    show_capture_window(app, "scan=auto")
}

#[tauri::command(async)]
fn show_scan_area_selector(app: AppHandle) -> Result<(), String> {
    show_capture_window(app, "scan=configure")
}

fn dispatch_capture_shortcut(app: AppHandle, scan_query: &'static str) {
    let capture = move || {
        let result = toolbar::pointer_display(&app).and_then(|display| {
            let mode = if scan_query == "scan=whole" {
                toolbar::ScanMode::WholeScreen
            } else {
                toolbar::ScanMode::SelectedArea
            };
            show_capture_window_on(app.clone(), scan_query, display, mode, None)
        });
        if let Err(error) = result {
            let state = app.state::<AppState>();
            if let Ok(mut session) = state.scans.lock() {
                // A repeated hotkey must not reveal app chrome while an earlier
                // capture is still waiting for the compositor/screenshot.
                if session.active.is_some() {
                    return;
                }
                session.revision += 1;
                session.phase = "error";
                session.message = error.clone();
                if let Some(window) = app.get_webview_window("toolbar") {
                    let _ = window.show();
                }
            }
            toolbar::emit_state(&app);
            eprintln!("YomiMado: {error}");
        }
    };
    // Keep native window work and session locks off the UI thread on both
    // platforms. Windows also requires this to avoid WebView2 creation deadlocks.
    tauri::async_runtime::spawn_blocking(capture);
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct CaptureSurface {
    display_id: String,
    screen_physical_bounds: Rectangle,
    selector_physical_bounds: Rectangle,
    scale_factor: f64,
}

#[tauri::command(async)]
fn get_capture_surface(app: AppHandle, session_id: Option<u64>) -> Result<CaptureSurface, String> {
    let display = active_scan(&app, session_id)?.display;
    let selector = app
        .get_webview_window("capture-selector")
        .ok_or("Capture selector is unavailable")?;
    let position = selector
        .inner_position()
        .map_err(|error| error.to_string())?;
    let size = selector.inner_size().map_err(|error| error.to_string())?;
    Ok(CaptureSurface {
        display_id: display.id,
        screen_physical_bounds: display.physical_bounds,
        selector_physical_bounds: Rectangle {
            x: f64::from(position.x),
            y: f64::from(position.y),
            width: f64::from(size.width),
            height: f64::from(size.height),
        },
        scale_factor: display.scale_factor,
    })
}

fn show_capture_window(app: AppHandle, scan_query: &str) -> Result<(), String> {
    let display = current_display(&app, "main")?;
    show_capture_window_on(
        app,
        scan_query,
        display,
        toolbar::ScanMode::SelectedArea,
        None,
    )
}

fn show_capture_window_on(
    app: AppHandle,
    scan_query: &str,
    display: DisplayInfo,
    mode: toolbar::ScanMode,
    repeat: Option<toolbar::ScanSpec>,
) -> Result<(), String> {
    detector_model::ensure_available(&app)?;
    #[cfg(target_os = "macos")]
    {
        let access = core_graphics::access::ScreenCaptureAccess;
        if !access.preflight() {
            access.request();
            return Err("Screen Recording access is required. Enable YomiMado (or your terminal when running `tauri dev`) in System Settings > Privacy & Security > Screen & System Audio Recording, then restart the app.".into());
        }
    }
    toolbar::close_toolbar_menu(app.clone(), None)?;
    let restore = toolbar::CAPTURE_WINDOW_LABELS
        .iter()
        .filter(|label| {
            app.get_webview_window(label)
                .is_some_and(|window| window.is_visible().unwrap_or(false))
        })
        .map(|label| (*label).to_string())
        .collect();
    let id = app
        .state::<AppState>()
        .scans
        .lock()?
        .begin(mode, display.clone(), repeat, restore)?;
    app.state::<AppState>().scans.set_selector_id(id);
    let result: Result<(), String> = (|| {
        app.state::<AppState>().overlay_input.disable(&app)?;
        for label in std::iter::once("toolbar-menu").chain(toolbar::CAPTURE_WINDOW_LABELS) {
            if let Some(window) = app.get_webview_window(label) {
                window.hide().map_err(|e| e.to_string())?;
            }
        }
        let query = format!(
            "mode=capture&session={id}{}",
            if scan_query.is_empty() {
                String::new()
            } else {
                format!("&{scan_query}")
            }
        );
        let window = if let Some(window) = app.get_webview_window("capture-selector") {
            let mut url = window.url().map_err(|e| e.to_string())?;
            url.set_query(Some(&query));
            window.navigate(url).map_err(|e| e.to_string())?;
            window
        } else {
            WebviewWindowBuilder::new(
                &app,
                "capture-selector",
                WebviewUrl::App(format!("index.html?{query}").into()),
            )
            // Whole Screen/Rescan may never show this webview. On macOS 14+
            // WKWebView's inactive policy can suspend IPC/fetch continuations
            // until a manual selection makes it visible for the first time.
            .background_throttling(tauri::utils::config::BackgroundThrottlingPolicy::Disabled)
            .transparent(true)
            .decorations(false)
            .always_on_top(true)
            .skip_taskbar(true)
            .visible(false)
            .build()
            .map_err(|e| e.to_string())?
        };
        window
            .set_position(PhysicalPosition::new(
                display.physical_bounds.x as i32,
                display.physical_bounds.y as i32,
            ))
            .map_err(|e| e.to_string())?;
        window
            .set_size(PhysicalSize::new(
                display.physical_bounds.width as u32,
                display.physical_bounds.height as u32,
            ))
            .map_err(|e| e.to_string())?;
        // Automatic/repeat requests can run in a hidden webview. Only selecting
        // an area deliberately takes focus and blocks interaction with the reader.
        if !scan_query.starts_with("scan=whole") && !scan_query.starts_with("scan=repeat") {
            window.show().map_err(|e| e.to_string())?;
            window.set_focus().map_err(|e| e.to_string())?;
        }
        toolbar::emit_state(&app);
        Ok(())
    })();
    if let Err(ref error) = result {
        let _ = toolbar::stop_scan(&app, Some(id), error, false);
    }
    result
}

fn active_scan(app: &AppHandle, id: Option<u64>) -> Result<toolbar::ActiveScan, String> {
    let scan = app.state::<AppState>().scans.lock()?.active(id)?.clone();
    toolbar::live_display(app, &scan.display)?;
    Ok(scan)
}

async fn perform_capture(
    app: AppHandle,
    capture: Arc<dyn ScreenCapture>,
    display: DisplayInfo,
    selection: Rectangle,
    id: u64,
) -> Result<CapturedImage, String> {
    {
        let state = app.state::<AppState>();
        let mut session = state.scans.lock()?;
        session.active(Some(id))?;
        session.revision += 1;
        session.phase = "capturing";
        session.message = "Capturing screen pixels…".into();
        // Hiding the native selector, not just its DOM, keeps processing from
        // trapping browser input and keeps all app chrome out of the screenshot.
        for label in ["capture-selector", "toolbar-menu"]
            .into_iter()
            .chain(toolbar::CAPTURE_WINDOW_LABELS)
        {
            if let Some(window) = app.get_webview_window(label) {
                window.hide().map_err(|e| e.to_string())?;
            }
        }
    }
    toolbar::emit_state(&app);
    let captured = tauri::async_runtime::spawn_blocking(move || {
        std::thread::sleep(std::time::Duration::from_millis(180));
        capture.capture(&display, selection)
    })
    .await
    .map_err(|e| e.to_string())?
    .map_err(|e| e.to_string())?;
    {
        let state = app.state::<AppState>();
        let mut session = state.scans.lock()?;
        session.captured(id, captured.metadata.clone())?;
        let scan = session.active(Some(id))?.clone();
        toolbar::restore_windows(&app, &scan, false)?;
    }
    toolbar::emit_state(&app);
    eprintln!(
        "YomiMado: capture physical={:?} image={}x{}",
        captured.metadata.selection_physical_bounds,
        captured.metadata.image_width,
        captured.metadata.image_height
    );
    Ok(captured)
}

fn full_display_selection(display: &mut DisplayInfo, area: Rectangle) -> Result<Rectangle, String> {
    toolbar::validate_area(area, display)?;
    if !display.scale_factor.is_finite() || display.scale_factor <= 0.0 {
        return Err("Invalid display scale".into());
    }
    display.selector_physical_bounds = display.physical_bounds;
    display.viewport_width = display.physical_bounds.width / display.scale_factor;
    display.viewport_height = display.physical_bounds.height / display.scale_factor;
    Ok(Rectangle {
        x: (area.x - display.physical_bounds.x) / display.scale_factor,
        y: (area.y - display.physical_bounds.y) / display.scale_factor,
        width: area.width / display.scale_factor,
        height: area.height / display.scale_factor,
    })
}

#[tauri::command]
async fn capture_whole_screen(
    app: AppHandle,
    state: tauri::State<'_, AppState>,
    session_id: u64,
) -> Result<Option<CapturedImage>, String> {
    let scan = active_scan(&app, Some(session_id))?;
    let mut display = scan.display;
    let area = display.physical_bounds;
    let selection = full_display_selection(&mut display, area)?;
    let captured = perform_capture(
        app.clone(),
        Arc::clone(&state.capture),
        display,
        selection,
        scan.id,
    )
    .await?;
    crop_captured_page(app, captured, scan.id).await
}

#[tauri::command]
async fn capture_repeat_scan(
    app: AppHandle,
    state: tauri::State<'_, AppState>,
    session_id: u64,
) -> Result<CapturedImage, String> {
    let scan = active_scan(&app, Some(session_id))?;
    let spec = scan.repeat.ok_or("No repeat scan is available")?;
    let mut display = scan.display;
    let selection = full_display_selection(&mut display, spec.area)?;
    perform_capture(app, Arc::clone(&state.capture), display, selection, scan.id).await
}

#[tauri::command]
async fn capture_display(
    app: AppHandle,
    state: tauri::State<'_, AppState>,
    session_id: Option<u64>,
) -> Result<CapturedImage, String> {
    let scan = active_scan(&app, session_id)?;
    let mut display = scan.display;
    let selector = app
        .get_webview_window("capture-selector")
        .ok_or("Capture selector is unavailable")?;
    let position = selector
        .inner_position()
        .map_err(|error| error.to_string())?;
    let size = selector.inner_size().map_err(|error| error.to_string())?;
    display.selector_physical_bounds = Rectangle {
        x: f64::from(position.x),
        y: f64::from(position.y),
        width: f64::from(size.width),
        height: f64::from(size.height),
    };
    // The compositor may shift the full-height borderless window below the
    // macOS menu bar without reducing its height. Clip it to the monitor so
    // capture and overlay share the same visible physical rectangle.
    let selection = display_capture_selection(&mut display)?;
    eprintln!(
        "YomiMado: display scan selector={:?} visible={:?} monitor={:?}",
        Rectangle {
            x: f64::from(position.x),
            y: f64::from(position.y),
            width: f64::from(size.width),
            height: f64::from(size.height),
        },
        display.selector_physical_bounds,
        display.physical_bounds,
    );
    perform_capture(app, Arc::clone(&state.capture), display, selection, scan.id).await
}

#[tauri::command]
async fn capture_auto_page(
    app: AppHandle,
    state: tauri::State<'_, AppState>,
    session_id: Option<u64>,
) -> Result<Option<CapturedImage>, String> {
    let id = active_scan(&app, session_id)?.id;
    let captured = capture_display(app.clone(), state, session_id).await?;
    crop_captured_page(app, captured, id).await
}

// Both entry points inspect pixels locally and publish only the detected page
// to OCR. None deliberately requests the saved/drawn area fallback in the UI.
async fn crop_captured_page(
    app: AppHandle,
    captured: CapturedImage,
    id: u64,
) -> Result<Option<CapturedImage>, String> {
    let result = tauri::async_runtime::spawn_blocking(move || crop_detected_page(captured))
        .await
        .map_err(|error| error.to_string())?
        .map_err(|error| error.to_string())?;
    if let Some(ref page) = result {
        app.state::<AppState>()
            .scans
            .lock()?
            .captured(id, page.metadata.clone())?;
        eprintln!(
            "YomiMado: automatic manga page physical={:?} image={}x{}",
            page.metadata.selection_physical_bounds,
            page.metadata.image_width,
            page.metadata.image_height,
        );
    } else {
        eprintln!("YomiMado: manga page uncertain; use saved area fallback");
    }
    Ok(result)
}

fn display_capture_selection(display: &mut DisplayInfo) -> Result<Rectangle, String> {
    let bounds = visible_capture_bounds(display.physical_bounds, display.selector_physical_bounds)?;
    if !display.scale_factor.is_finite() || display.scale_factor <= 0.0 {
        return Err("Invalid display dimensions or scale".into());
    }
    display.selector_physical_bounds = bounds;
    let selection = Rectangle {
        x: 0.0,
        y: 0.0,
        width: bounds.width / display.scale_factor,
        height: bounds.height / display.scale_factor,
    };
    display.viewport_width = selection.width;
    display.viewport_height = selection.height;
    Ok(selection)
}

fn visible_capture_bounds(screen: Rectangle, selector: Rectangle) -> Result<Rectangle, String> {
    if ![
        screen.x,
        screen.y,
        screen.width,
        screen.height,
        selector.x,
        selector.y,
        selector.width,
        selector.height,
    ]
    .iter()
    .all(|value| value.is_finite())
        || screen.width <= 0.0
        || screen.height <= 0.0
        || selector.width <= 0.0
        || selector.height <= 0.0
    {
        return Err("Invalid display dimensions".into());
    }
    let left = selector.x.max(screen.x);
    let top = selector.y.max(screen.y);
    let right = (selector.x + selector.width).min(screen.x + screen.width);
    let bottom = (selector.y + selector.height).min(screen.y + screen.height);
    if right <= left || bottom <= top {
        return Err("Capture window does not overlap the active display".into());
    }
    Ok(Rectangle {
        x: left,
        y: top,
        width: right - left,
        height: bottom - top,
    })
}

#[tauri::command(async)]
fn cancel_capture_selector(app: AppHandle, session_id: Option<u64>) -> Result<(), String> {
    toolbar::stop_scan(&app, session_id, "", false)
}

#[tauri::command]
async fn capture_selection(
    app: AppHandle,
    state: tauri::State<'_, AppState>,
    selection: Rectangle,
    viewport: ViewportSize,
    session_id: Option<u64>,
) -> Result<CapturedImage, String> {
    let scan = active_scan(&app, session_id)?;
    let mut display = scan.display;
    let selector = app
        .get_webview_window("capture-selector")
        .ok_or("Capture selector is unavailable")?;
    let position = selector
        .inner_position()
        .map_err(|error| error.to_string())?;
    let size = selector.inner_size().map_err(|error| error.to_string())?;
    display.selector_physical_bounds = Rectangle {
        x: f64::from(position.x),
        y: f64::from(position.y),
        width: f64::from(size.width),
        height: f64::from(size.height),
    };
    display.viewport_width = viewport.width;
    display.viewport_height = viewport.height;
    eprintln!(
        "YomiMado: selector actual={:?} monitor={:?}",
        display.selector_physical_bounds, display.physical_bounds
    );
    perform_capture(app, Arc::clone(&state.capture), display, selection, scan.id).await
}

#[derive(Debug, Deserialize)]
#[serde(rename_all = "camelCase")]
enum OcrStage {
    Requesting,
    Recognized,
    Publishing,
}

#[tauri::command(async)]
fn report_ocr_stage(
    window: tauri::WebviewWindow,
    state: tauri::State<'_, AppState>,
    session_id: u64,
    stage: OcrStage,
) -> Result<(), String> {
    // Only log stage metadata for the current selector; never image/text data.
    if window.label() == "capture-selector" && state.scans.lock()?.active(Some(session_id)).is_ok()
    {
        eprintln!("YomiMado: scan={session_id} OCR stage={stage:?}");
    }
    Ok(())
}

#[tauri::command(async)]
fn show_ocr_overlay(
    app: AppHandle,
    state: tauri::State<'_, AppState>,
    metadata: CaptureMetadata,
    regions: serde_json::Value,
    engine: String,
    estimated_reading_order: bool,
    session_id: Option<u64>,
) -> Result<(), String> {
    let mut session = state.scans.lock()?;
    let id = session.active(session_id)?.id;
    toolbar::live_display(&app, &session.active(Some(id))?.display)?;
    if session.active(Some(id))?.captured.is_none() {
        return Err("No capture is available".into());
    }
    // Keep publication and cancellation mutually exclusive; old OCR replies
    // cannot replace a later result after cancellation or a new scan.
    overlay::show_overlay(
        &app,
        &state.overlay,
        &metadata,
        regions,
        &engine,
        estimated_reading_order,
        id,
    )?;
    let scan = session.complete(id, estimated_reading_order)?;
    toolbar::restore_windows(&app, &scan, false)?;
    drop(session);
    toolbar::emit_state(&app);
    eprintln!("YomiMado: OCR overlay displayed ({engine})");
    Ok(())
}

#[tauri::command]
fn get_overlay_state(state: tauri::State<'_, AppState>) -> Result<serde_json::Value, String> {
    state.overlay.get()
}

#[tauri::command(async)]
fn update_overlay_controls(
    window: tauri::WebviewWindow,
    session_id: u64,
    revision: u64,
    rectangles: Vec<Rectangle>,
    viewport_width: f64,
    viewport_height: f64,
    view_query: String,
) -> Result<(), String> {
    if window.label() != "ocr-overlay"
        || window.url().map_err(|e| e.to_string())?.query() != Some(view_query.as_str())
    {
        return Ok(());
    }
    #[cfg(debug_assertions)]
    if std::env::var_os("YOMIMADO_OVERLAY_GEOMETRY_DEBUG").is_some() {
        eprintln!(
            "YomiMado viewport: {}",
            serde_json::json!({
                "sessionId": session_id, "width": viewport_width, "height": viewport_height,
                "windowWidth": window.inner_size().map(|size| size.width).ok(),
                "windowHeight": window.inner_size().map(|size| size.height).ok(),
            })
        );
    }
    let app = window.app_handle().clone();
    let state = app.state::<AppState>();
    let result = state.overlay_input.controls(
        &app,
        session_id,
        revision,
        rectangles,
        viewport_width,
        viewport_height,
    );
    if let Err(error) = &result {
        let mut session = state.scans.lock()?;
        if session.active.is_none() && session.completed_id == Some(session_id) {
            state.overlay_input.disable(&app)?;
            window.hide().map_err(|e| e.to_string())?;
            session.overlay_visible = false;
            session.phase = "error";
            session.message = format!("Could not configure region navigation: {error}");
            session.revision += 1;
            drop(session);
            toolbar::emit_state(&app);
        }
    }
    result
}

#[tauri::command(async)]
fn focus_ocr_regions(app: AppHandle) -> Result<(), String> {
    let state = app.state::<AppState>();
    let session = state.scans.lock()?;
    if session.active.is_some() || !session.overlay_visible || !state.overlay_input.is_active() {
        return Err("Show an OCR result before focusing its regions.".into());
    }
    let window = app
        .get_webview_window("ocr-overlay")
        .ok_or("OCR overlay is unavailable")?;
    window.set_focus().map_err(|e| e.to_string())?;
    window
        .emit("focus-ocr-region", serde_json::json!({"regionId":null}))
        .map_err(|e| e.to_string())
}

#[tauri::command(async)]
fn hide_focused_overlay(app: AppHandle) -> Result<(), String> {
    toolbar::set_overlay_visibility(app.clone(), false)?;
    if let Some(window) = app.get_webview_window("toolbar") {
        window.set_focus().map_err(|e| e.to_string())?;
    }
    Ok(())
}

#[tauri::command(async)]
fn close_translation_popup(
    app: AppHandle,
    window: tauri::WebviewWindow,
    view_query: String,
    return_focus: bool,
) -> Result<(), String> {
    if window.label() != "translation-popup"
        || window.url().map_err(|e| e.to_string())?.query() != Some(view_query.as_str())
    {
        return Ok(());
    }
    let state = app.state::<AppState>();
    let return_region = state.overlay_input.take_popup_return();
    let was_focused = window.is_visible().map_err(|e| e.to_string())?
        && window.is_focused().map_err(|e| e.to_string())?;
    window.hide().map_err(|e| e.to_string())?;
    // Only explicit keyboard dismissal returns to the navigator that opened it.
    // Blur dismissal never activates the overlay or steals focus from the reader.
    if return_focus && was_focused {
        let session = state.scans.lock()?;
        if session.active.is_none() && session.overlay_visible {
            if let (Some(region_id), Some(window)) =
                (return_region, app.get_webview_window("ocr-overlay"))
            {
                window.set_focus().map_err(|e| e.to_string())?;
                window
                    .emit(
                        "focus-ocr-region",
                        serde_json::json!({"regionId":region_id}),
                    )
                    .map_err(|e| e.to_string())?;
            }
        }
    }
    Ok(())
}

#[tauri::command(async)]
fn show_translation_popup(
    app: AppHandle,
    metadata: CaptureMetadata,
    text: String,
    polygon: Vec<overlay::OcrPoint>,
    region_id: Option<String>,
    session_id: Option<u64>,
    keyboard: Option<bool>,
) -> Result<(), String> {
    let state = app.state::<AppState>();
    let session = state.scans.lock()?;
    if session.active.is_some()
        || !session.overlay_visible
        || (session_id.is_some() && session_id != session.completed_id)
    {
        return Err("This OCR result is no longer visible. Show it or rescan first.".into());
    }
    let overlay = state.overlay.get()?;
    // The stored OCR result owns its engine; the frontend need not repeat it.
    let demo = overlay["engine"].as_str() == Some("demo");
    let region = overlay["regions"].as_array().and_then(|regions| {
        regions
            .iter()
            .find(|region| region["id"].as_str() == region_id.as_deref())
    });
    let review = region
        .filter(|region| region["needsReview"].as_bool().unwrap_or(false))
        .map(|region| {
            region["reviewReason"]
                .as_str()
                .unwrap_or("Check the OCR text against the page.")
        });
    let approximate = region.is_some_and(|region| region["geometrySource"].as_str().is_some());
    let result = overlay::show_translation_popup(
        &app,
        &metadata,
        &text,
        &polygon,
        demo,
        review,
        approximate,
    );
    if result.is_ok() {
        state
            .overlay_input
            .remember_popup(if keyboard.unwrap_or(false) {
                region_id
            } else {
                None
            });
    }
    result
}

#[tauri::command]
fn resize_translation_popup(
    app: AppHandle,
    placement: overlay::PopupPlacement,
    logical_height: f64,
    view_query: String,
) -> Result<(), String> {
    overlay::resize_translation_popup(&app, placement, logical_height, &view_query)
}

#[tauri::command(async)]
fn close_ocr_overlay(app: AppHandle, state: tauri::State<'_, AppState>) -> Result<(), String> {
    let mut session = state.scans.lock()?;
    if session.active.is_some() {
        return Err("Finish or cancel the scan before closing its overlay.".into());
    }
    state.overlay_input.disable(&app)?;
    if let Some(window) = app.get_webview_window("translation-popup") {
        window.close().map_err(|error| error.to_string())?;
    }
    if let Some(window) = app.get_webview_window("ocr-overlay") {
        window.close().map_err(|error| error.to_string())?;
    }
    state.overlay.clear()?;
    session.overlay_visible = false;
    session.revision += 1;
    drop(session);
    toolbar::emit_state(&app);
    Ok(())
}

pub fn run() {
    tauri::Builder::default()
        .on_window_event(|window, event| {
            if window.label() == "ocr-overlay"
                && matches!(
                    event,
                    tauri::WindowEvent::Moved(_)
                        | tauri::WindowEvent::Resized(_)
                        | tauri::WindowEvent::ScaleFactorChanged { .. }
                )
            {
                let app = window.app_handle().clone();
                tauri::async_runtime::spawn_blocking(move || {
                    if let Err(error) = overlay::check_frame(&app) {
                        eprintln!("YomiMado: could not validate OCR window geometry: {error}");
                    }
                });
            }
            if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                if window.label() == "toolbar" {
                    api.prevent_close();
                    return;
                }
                if toolbar::SECONDARY_WINDOW_LABELS.contains(&window.label())
                    || window.label() == "capture-selector"
                {
                    api.prevent_close();
                    if let Err(error) = window.hide() {
                        eprintln!("YomiMado: could not hide window: {error}");
                    }
                    if window.label() == "capture-selector" {
                        let app = window.app_handle().clone();
                        let id = app.state::<AppState>().scans.selector_id();
                        tauri::async_runtime::spawn_blocking(move || {
                            if let Some(id) = id {
                                if let Err(error) = toolbar::stop_scan(&app, Some(id), "", false) {
                                    eprintln!("YomiMado: could not cancel scan: {error}");
                                }
                            }
                        });
                    }
                }
            }
            if window.label() == "toolbar"
                && matches!(
                    event,
                    tauri::WindowEvent::Moved(_) | tauri::WindowEvent::ScaleFactorChanged { .. }
                )
            {
                let app = window.app_handle().clone();
                tauri::async_runtime::spawn_blocking(move || toolbar::emit_state(&app));
            }
            if window.label() == "translation-popup"
                && matches!(event, tauri::WindowEvent::Focused(false))
            {
                // Hiding instead of closing keeps the label reusable when an
                // OCR-region click immediately opens the next popup.
                if let Err(error) = window.hide() {
                    eprintln!("YomiMado: failed to hide translation popup: {error}");
                }
            }
            if matches!(window.label(), "toolbar" | "toolbar-menu")
                && matches!(event, tauri::WindowEvent::Focused(false))
            {
                let app = window.app_handle().clone();
                tauri::async_runtime::spawn(async move {
                    // Query after the focus transition: clicking the toolbar
                    // must leave the menu alive long enough for its toggle action.
                    tauri::async_runtime::spawn_blocking(move || {
                        let toolbar_focused = app
                            .get_webview_window("toolbar")
                            .is_some_and(|toolbar| toolbar.is_focused().unwrap_or(false));
                        let menu_visible = app
                            .get_webview_window("toolbar-menu")
                            .is_some_and(|menu| menu.is_visible().unwrap_or(false));
                        let menu_focused = app
                            .get_webview_window("toolbar-menu")
                            .is_some_and(|menu| menu.is_focused().unwrap_or(false));
                        if !toolbar_focused && !menu_focused && menu_visible {
                            let _ = toolbar::close_toolbar_menu(app, None);
                        }
                    });
                });
            }
        })
        .plugin(GlobalShortcutBuilder::new().build())
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            let capture_dir = app.path().app_cache_dir()?.join("captures");
            if let Err(error) = cleanup_legacy_captures(&capture_dir) {
                eprintln!("YomiMado: could not clear legacy capture cache: {error}");
            }
            #[cfg(all(not(debug_assertions), target_os = "macos"))]
            let service = Some(start_bundled_service(app)?);
            #[cfg(any(debug_assertions, not(target_os = "macos")))]
            let service = None;
            #[cfg(all(not(debug_assertions), target_os = "windows"))]
            let (windows_service, startup_error) = match windows_service::start(app) {
                Ok(service) => (Some(service), None),
                Err(error) => (None, Some(error.to_string())),
            };
            app.manage(AppState {
                capture: Arc::new(XcapScreenCapture::new()),
                overlay: overlay::OverlayStore::default(),
                overlay_input: overlay::input::InputRouter::default(),
                scans: toolbar::ScanStore::default(),
                toolbar_layout: Mutex::new(toolbar::ToolbarLayout::default()),
                toolbar_menu: toolbar::ToolbarMenuStore::default(),
                service: Mutex::new(service),
                #[cfg(all(not(debug_assertions), target_os = "windows"))]
                windows_service: Mutex::new(windows_service),
            });
            #[cfg(all(not(debug_assertions), target_os = "windows"))]
            if let Some(error) = startup_error {
                use tauri_plugin_dialog::DialogExt;
                // Keep the event loop running for the native dialog. Blocking
                // here deadlocks it; returning a setup error destroys it early.
                if let Some(main) = app.get_webview_window("main") {
                    main.hide()?;
                }
                if let Some(toolbar) = app.get_webview_window("toolbar") {
                    toolbar.hide()?;
                }
                let handle = app.handle().clone();
                app.dialog()
                    .message(format!("Local OCR service could not start: {error}"))
                    .title("YomiMado startup failed")
                    .show(move |_| handle.exit(1));
                return Ok(());
            }
            let manual =
                Shortcut::try_from(MANUAL_CAPTURE_SHORTCUT).map_err(|error| error.to_string())?;
            app.global_shortcut().on_shortcut(manual, |app, _, event| {
                if event.state() == ShortcutState::Pressed {
                    dispatch_capture_shortcut(app.clone(), "");
                }
            })?;
            let whole_screen =
                Shortcut::try_from(WHOLE_SCREEN_SHORTCUT).map_err(|error| error.to_string())?;
            app.global_shortcut()
                .on_shortcut(whole_screen, |app, _, event| {
                    if event.state() == ShortcutState::Pressed {
                        dispatch_capture_shortcut(app.clone(), "scan=whole");
                    }
                })?;
            toolbar::setup(app.handle())?;
            app.state::<AppState>().overlay_input.start(app.handle());
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            toolbar::get_toolbar_state,
            toolbar::start_toolbar_scan,
            toolbar::rescan,
            toolbar::set_overlay_visibility,
            toolbar::show_secondary_window,
            toolbar::show_toolbar_menu,
            toolbar::close_toolbar_menu,
            toolbar::position_toolbar_menu,
            toolbar::resize_toolbar,
            toolbar::move_toolbar,
            toolbar::drag_toolbar,
            toolbar::quit_app,
            toolbar::finish_scan,
            toolbar::hide_finished_selector,
            toolbar::reveal_ocr_overlay,
            toolbar::resume_capture_selection,
            capture_whole_screen,
            capture_repeat_scan,
            detector_model::detector_model_status,
            detector_model::install_detector_model,
            show_capture_selector,
            show_auto_scanner,
            show_scan_area_selector,
            get_capture_surface,
            cancel_capture_selector,
            capture_selection,
            capture_display,
            capture_auto_page,
            report_ocr_stage,
            show_ocr_overlay,
            get_overlay_state,
            update_overlay_controls,
            focus_ocr_regions,
            hide_focused_overlay,
            close_translation_popup,
            show_translation_popup,
            resize_translation_popup,
            close_ocr_overlay
        ])
        .build(tauri::generate_context!())
        .expect("error while building YomiMado")
        .run(|app, event| {
            if matches!(event, tauri::RunEvent::Exit) {
                app.state::<AppState>().overlay_input.stop();
                #[cfg(all(not(debug_assertions), target_os = "windows"))]
                if let Ok(mut service) = app.state::<AppState>().windows_service.lock() {
                    // Drop closes the job and terminates its entire service tree.
                    service.take();
                }
                if let Ok(mut service) = app.state::<AppState>().service.lock() {
                    if let Some(mut child) = service.take() {
                        let _ = child.kill();
                        let _ = child.wait();
                    }
                }
            }
        });
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn manual_and_whole_screen_shortcuts_are_distinct() {
        let manual = Shortcut::try_from(MANUAL_CAPTURE_SHORTCUT).unwrap();
        let whole_screen = Shortcut::try_from(WHOLE_SCREEN_SHORTCUT).unwrap();
        assert_ne!(manual, whole_screen);
    }

    #[test]
    fn whole_screen_keeps_every_pixel_despite_a_retina_selector_menu_bar_inset() {
        let bounds = Rectangle {
            x: 0.0,
            y: 0.0,
            width: 2940.0,
            height: 1912.0,
        };
        let mut display = DisplayInfo {
            id: "retina".into(),
            name: "Retina".into(),
            physical_bounds: bounds,
            selector_physical_bounds: Rectangle { y: 66.0, ..bounds },
            scale_factor: 2.0,
            viewport_width: 1470.0,
            viewport_height: 956.0,
        };
        let selection = full_display_selection(&mut display, bounds).unwrap();
        let physical = XcapScreenCapture::physical_selection(&display, selection).unwrap();
        assert_eq!(
            (physical.x, physical.y, physical.width, physical.height),
            (0.0, 0.0, 2940.0, 1912.0)
        );
    }

    #[test]
    fn repeating_a_physical_area_on_a_left_monitor_preserves_fractional_scaling() {
        for scale in [1.0, 1.25, 1.5, 2.0] {
            let bounds = Rectangle {
                x: -2560.0,
                y: -1440.0,
                width: 2560.0,
                height: 1440.0,
            };
            let area = Rectangle {
                x: -2300.0,
                y: -1200.0,
                width: 640.0,
                height: 800.0,
            };
            let mut display = DisplayInfo {
                id: "left".into(),
                name: "Left".into(),
                physical_bounds: bounds,
                selector_physical_bounds: Rectangle {
                    y: -1400.0,
                    ..bounds
                },
                scale_factor: scale,
                viewport_width: 1.0,
                viewport_height: 1.0,
            };
            let selection = full_display_selection(&mut display, area).unwrap();
            let physical = XcapScreenCapture::physical_selection(&display, selection).unwrap();
            assert_eq!(
                (physical.x, physical.y, physical.width, physical.height),
                (area.x, area.y, area.width, area.height)
            );
        }
    }

    #[test]
    fn display_scan_uses_actual_selector_bounds_on_retina() {
        let mut display = DisplayInfo {
            id: "retina".into(),
            name: "Retina".into(),
            physical_bounds: Rectangle {
                x: 0.0,
                y: 0.0,
                width: 2940.0,
                height: 1912.0,
            },
            selector_physical_bounds: Rectangle {
                x: 0.0,
                y: 66.0,
                width: 2940.0,
                height: 1912.0,
            },
            scale_factor: 2.0,
            viewport_width: 1470.0,
            viewport_height: 956.0,
        };
        let selection = display_capture_selection(&mut display).unwrap();
        assert_eq!((selection.width, selection.height), (1470.0, 923.0));
        assert_eq!(display.selector_physical_bounds.height, 1846.0);
        let physical = XcapScreenCapture::physical_selection(&display, selection).unwrap();
        assert_eq!((physical.x, physical.y), (0.0, 66.0));
        assert_eq!((physical.width, physical.height), (2940.0, 1846.0));
    }

    #[test]
    fn display_scan_handles_negative_monitor_origin() {
        let mut display = DisplayInfo {
            id: "left".into(),
            name: "Left".into(),
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
            scale_factor: 1.0,
            viewport_width: 1920.0,
            viewport_height: 1080.0,
        };
        let selection = display_capture_selection(&mut display).unwrap();
        let physical = XcapScreenCapture::physical_selection(&display, selection).unwrap();
        assert_eq!((physical.x, physical.y), (-1920.0, 0.0));
        assert_eq!((physical.width, physical.height), (1920.0, 1080.0));
    }

    #[test]
    fn display_scan_clips_window_on_left_monitor() {
        let screen = Rectangle {
            x: -1920.0,
            y: 0.0,
            width: 1920.0,
            height: 1080.0,
        };
        let selector = Rectangle {
            x: -1930.0,
            y: 20.0,
            width: 1920.0,
            height: 1080.0,
        };
        let visible = visible_capture_bounds(screen, selector).unwrap();
        assert_eq!((visible.x, visible.y), (-1920.0, 20.0));
        assert_eq!((visible.width, visible.height), (1910.0, 1060.0));
    }

    #[test]
    fn display_scan_rejects_window_outside_monitor() {
        let screen = Rectangle {
            x: 0.0,
            y: 0.0,
            width: 1920.0,
            height: 1080.0,
        };
        let selector = Rectangle {
            x: 2000.0,
            y: 0.0,
            width: 100.0,
            height: 100.0,
        };
        assert!(visible_capture_bounds(screen, selector).is_err());
    }
}
