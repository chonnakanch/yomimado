mod capture;
mod overlay;

use std::sync::Arc;

use capture::{
    cleanup_legacy_captures, CaptureMetadata, CapturedImage, DisplayInfo, Rectangle, ScreenCapture,
    ViewportSize, XcapScreenCapture,
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
        selector_physical_bounds: Rectangle {
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
    show_capture_window(app, false)
}

#[tauri::command]
fn show_display_scanner(app: AppHandle) -> Result<(), String> {
    show_capture_window(app, true)
}

fn show_capture_window(app: AppHandle, scan_display: bool) -> Result<(), String> {
    #[cfg(target_os = "macos")]
    {
        let access = core_graphics::access::ScreenCaptureAccess;
        if !access.preflight() {
            access.request();
            return Err("Screen Recording access is required. Enable YomiMado (or your terminal when running `tauri dev`) in System Settings > Privacy & Security > Screen & System Audio Recording, then restart the app.".into());
        }
    }
    let display = current_display(&app, "main")?;
    let main = app
        .get_webview_window("main")
        .ok_or("Main window is unavailable")?;
    if let Some(window) = app.get_webview_window("ocr-overlay") {
        window.close().map_err(|error| error.to_string())?;
    }
    if let Some(window) = app.get_webview_window("translation-popup") {
        window.close().map_err(|error| error.to_string())?;
    }
    let query = if scan_display {
        "mode=capture&scan=display"
    } else {
        "mode=capture"
    };
    if let Some(window) = app.get_webview_window("capture-selector") {
        let mut url = window.url().map_err(|error| error.to_string())?;
        url.set_query(Some(query));
        window.navigate(url).map_err(|error| error.to_string())?;
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
        main.minimize().map_err(|error| error.to_string())?;
        window.show().map_err(|error| error.to_string())?;
        window.set_focus().map_err(|error| error.to_string())?;
        return Ok(());
    }
    let window = WebviewWindowBuilder::new(
        &app,
        "capture-selector",
        WebviewUrl::App(format!("index.html?{query}").into()),
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
async fn capture_display(
    app: AppHandle,
    state: tauri::State<'_, AppState>,
) -> Result<CapturedImage, String> {
    let mut display = current_display(&app, "capture-selector")?;
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
    let capture = Arc::clone(&state.capture);
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
    eprintln!(
        "YomiMado: display capture physical={:?} image={}x{}",
        captured.metadata.selection_physical_bounds,
        captured.metadata.image_width,
        captured.metadata.image_height,
    );
    Ok(captured)
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
fn show_translation_popup(
    app: AppHandle,
    metadata: CaptureMetadata,
    text: String,
    polygon: Vec<overlay::OcrPoint>,
    demo: bool,
) -> Result<(), String> {
    overlay::show_translation_popup(&app, &metadata, &text, &polygon, demo)
}

#[tauri::command]
fn resize_translation_popup(
    app: AppHandle,
    placement: overlay::PopupPlacement,
    logical_height: f64,
) -> Result<(), String> {
    overlay::resize_translation_popup(&app, placement, logical_height)
}

#[tauri::command]
fn close_ocr_overlay(app: AppHandle) -> Result<(), String> {
    if let Some(window) = app.get_webview_window("translation-popup") {
        window.close().map_err(|error| error.to_string())?;
    }
    if let Some(window) = app.get_webview_window("ocr-overlay") {
        window.close().map_err(|error| error.to_string())?;
    }
    Ok(())
}

pub fn run() {
    tauri::Builder::default()
        .on_window_event(|window, event| {
            if window.label() == "translation-popup"
                && matches!(event, tauri::WindowEvent::Focused(false))
            {
                // Hiding instead of closing keeps the label reusable when an
                // OCR-region click immediately opens the next popup.
                if let Err(error) = window.hide() {
                    eprintln!("YomiMado: failed to hide translation popup: {error}");
                }
            }
        })
        .plugin(
            GlobalShortcutBuilder::new()
                .with_handler(|app, _shortcut, event| {
                    if event.state() == ShortcutState::Pressed {
                        if let Err(error) = show_capture_selector(app.clone()) {
                            eprintln!("YomiMado: {error}");
                        }
                    }
                })
                .build(),
        )
        .setup(|app| {
            let capture_dir = app.path().app_cache_dir()?.join("captures");
            if let Err(error) = cleanup_legacy_captures(&capture_dir) {
                eprintln!("YomiMado: could not clear legacy capture cache: {error}");
            }
            app.manage(AppState {
                capture: Arc::new(XcapScreenCapture::new()),
            });
            let shortcut =
                Shortcut::try_from("CMDORCONTROL+SHIFT+O").map_err(|error| error.to_string())?;
            app.global_shortcut().register(shortcut)?;
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            show_capture_selector,
            show_display_scanner,
            cancel_capture_selector,
            capture_selection,
            capture_display,
            show_ocr_overlay,
            show_translation_popup,
            resize_translation_popup,
            close_ocr_overlay
        ])
        .run(tauri::generate_context!())
        .expect("error while running YomiMado");
}

#[cfg(test)]
mod tests {
    use super::*;

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
