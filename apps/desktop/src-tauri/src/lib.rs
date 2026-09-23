mod capture;
mod overlay;

use std::sync::Arc;

use capture::{
    CaptureMetadata, CapturedImage, DisplayInfo, Rectangle, ScreenCapture, ViewportSize,
    XcapScreenCapture,
};
use tauri::{AppHandle, Manager, PhysicalPosition, PhysicalSize, WebviewUrl, WebviewWindowBuilder};
use tauri_plugin_global_shortcut::{
    Builder as GlobalShortcutBuilder, GlobalShortcutExt, Shortcut, ShortcutState,
};

struct AppState {
    capture: Arc<dyn ScreenCapture>,
}

fn current_display(app: &AppHandle, window_label: &str) -> Result<DisplayInfo, String> {
    let window = app
        .get_webview_window(window_label)
        .ok_or_else(|| format!("{window_label} window is unavailable"))?;
    let monitor = window
        .current_monitor()
        .map_err(|error| error.to_string())?
        .ok_or("No active monitor")?;
    let position = monitor.position();
    let size = monitor.size();
    let name = monitor.name().cloned();
    Ok(DisplayInfo {
        id: name
            .clone()
            .unwrap_or_else(|| format!("{},{}", position.x, position.y)),
        name: name.unwrap_or_else(|| "Unnamed display".into()),
        physical_bounds: Rectangle {
            x: position.x as f64,
            y: position.y as f64,
            width: size.width as f64,
            height: size.height as f64,
        },
        scale_factor: monitor.scale_factor(),
        viewport_width: size.width as f64 / monitor.scale_factor(),
        viewport_height: size.height as f64 / monitor.scale_factor(),
    })
}

#[tauri::command]
fn show_capture_selector(app: AppHandle) -> Result<(), String> {
    let display = current_display(&app, "main")?;
    let main = app
        .get_webview_window("main")
        .ok_or("Main window is unavailable")?;
    if let Some(window) = app.get_webview_window("ocr-overlay") {
        window.close().map_err(|error| error.to_string())?;
    }
    if let Some(window) = app.get_webview_window("capture-selector") {
        main.minimize().map_err(|error| error.to_string())?;
        window.show().map_err(|error| error.to_string())?;
        window.set_focus().map_err(|error| error.to_string())?;
        return Ok(());
    }
    let window = WebviewWindowBuilder::new(
        &app,
        "capture-selector",
        WebviewUrl::App("index.html?mode=capture".into()),
    )
    .transparent(true)
    .decorations(false)
    .always_on_top(true)
    .skip_taskbar(true)
    .visible(false)
    .build()
    .map_err(|error| error.to_string())?;
    window
        .set_position(PhysicalPosition::new(
            display.physical_bounds.x as i32,
            display.physical_bounds.y as i32,
        ))
        .map_err(|error| error.to_string())?;
    window
        .set_size(PhysicalSize::new(
            display.physical_bounds.width as u32,
            display.physical_bounds.height as u32,
        ))
        .map_err(|error| error.to_string())?;
    window.show().map_err(|error| error.to_string())?;
    main.minimize().map_err(|error| error.to_string())?;
    window.set_focus().map_err(|error| error.to_string())?;
    Ok(())
}

#[tauri::command]
fn cancel_capture_selector(app: AppHandle) -> Result<(), String> {
    if let Some(selector) = app.get_webview_window("capture-selector") {
        selector.close().map_err(|error| error.to_string())?;
    }
    let main = app
        .get_webview_window("main")
        .ok_or("Main window is unavailable")?;
    main.unminimize().map_err(|error| error.to_string())?;
    main.set_focus().map_err(|error| error.to_string())
}

#[tauri::command]
async fn capture_selection(
    app: AppHandle,
    state: tauri::State<'_, AppState>,
    selection: Rectangle,
    viewport: ViewportSize,
) -> Result<CapturedImage, String> {
    let mut display = current_display(&app, "capture-selector")?;
    display.viewport_width = viewport.width;
    display.viewport_height = viewport.height;
    app.get_webview_window("capture-selector")
        .ok_or("Capture selector is unavailable")?;
    let capture = Arc::clone(&state.capture);
    // Give the window compositor time to remove the selection UI before xcap
    // snapshots the monitor. The blocking work stays off the Tauri UI thread.
    let result = tauri::async_runtime::spawn_blocking(move || {
        std::thread::sleep(std::time::Duration::from_millis(180));
        capture.capture(&display, selection)
    })
    .await;
    let captured = match result {
        Ok(Ok(captured)) => captured,
        Ok(Err(error)) => return Err(error.to_string()),
        Err(error) => return Err(error.to_string()),
    };
    let bounds = &captured.metadata.selection_physical_bounds;
    eprintln!(
        "YomiMado: capture viewport={:.0}x{:.0} selection=({:.0},{:.0},{:.0},{:.0}) physical=({:.0},{:.0},{:.0},{:.0}) image={}x{}",
        viewport.width,
        viewport.height,
        selection.x,
        selection.y,
        selection.width,
        selection.height,
        bounds.x,
        bounds.y,
        bounds.width,
        bounds.height,
        captured.metadata.image_width,
        captured.metadata.image_height,
    );
    Ok(captured)
}

#[tauri::command]
fn show_ocr_overlay(
    app: AppHandle,
    metadata: CaptureMetadata,
    regions: serde_json::Value,
    engine: String,
) -> Result<(), String> {
    overlay::show_overlay(&app, &metadata, regions, &engine)?;
    eprintln!("YomiMado: OCR overlay displayed ({engine})");
    Ok(())
}

#[tauri::command]
fn region_clicked(region_id: String) {
    let _ = region_id;
}

pub fn run() {
    tauri::Builder::default()
        .plugin(
            GlobalShortcutBuilder::new()
                .with_handler(|app, _shortcut, event| {
                    if event.state() == ShortcutState::Pressed {
                        let _ = show_capture_selector(app.clone());
                    }
                })
                .build(),
        )
        .setup(|app| {
            let capture_dir = app.path().app_cache_dir()?.join("captures");
            app.manage(AppState {
                capture: Arc::new(XcapScreenCapture::new(capture_dir)),
            });
            let shortcut =
                Shortcut::try_from("CMDORCONTROL+SHIFT+O").map_err(|error| error.to_string())?;
            app.global_shortcut().register(shortcut)?;
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            show_capture_selector,
            cancel_capture_selector,
            capture_selection,
            show_ocr_overlay,
            region_clicked
        ])
        .run(tauri::generate_context!())
        .expect("error while running YomiMado");
}
