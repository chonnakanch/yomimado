use serde::Deserialize;
use tauri::{AppHandle, Manager};

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub enum WindowAction {
    Hide,
    Minimize,
    ToggleMaximize,
    Drag,
}

/// In-app controls target only the Saved/Settings window. Hide never requests
/// window destruction or application exit, and does not touch OCR/session state.
#[tauri::command(async)]
pub fn control_secondary_window(app: AppHandle, action: WindowAction) -> Result<(), String> {
    let window = app
        .get_webview_window("main")
        .ok_or("Saved/Settings window is unavailable")?;
    match action {
        WindowAction::Hide => window.hide(),
        WindowAction::Minimize => window.minimize(),
        WindowAction::Drag => window.start_dragging(),
        WindowAction::ToggleMaximize => {
            if window.is_maximized().map_err(|error| error.to_string())? {
                window.unmaximize()
            } else {
                window.maximize()
            }
        }
    }
    .map_err(|error| error.to_string())
}
