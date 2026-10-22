use std::sync::{Mutex, OnceLock};

use tauri::{
    menu::{Menu, MenuItem, PredefinedMenuItem},
    tray::{MouseButton, MouseButtonState, TrayIcon, TrayIconBuilder, TrayIconEvent},
    AppHandle, Manager,
};

use crate::toolbar::{self, SecondaryView};

const VISIBILITY: &str = "yomimado.tray.visibility";
const SHOW_OCR_RESULTS: &str = "yomimado.tray.show-ocr-results";
const SAVED: &str = "yomimado.tray.saved";
const SETTINGS: &str = "yomimado.tray.settings";
const SOURCES: &str = "yomimado.tray.sources";
const QUIT: &str = "yomimado.tray.quit";

struct TrayMenu {
    _icon: TrayIcon,
    visibility: MenuItem<tauri::Wry>,
    show_ocr_results: MenuItem<tauri::Wry>,
    secondary: [MenuItem<tauri::Wry>; 3],
}

#[derive(Default)]
pub struct TrayState {
    menu: OnceLock<TrayMenu>,
    error: Mutex<Option<String>>,
}

impl TrayState {
    pub fn available(&self) -> bool {
        self.menu.get().is_some()
    }

    pub fn error(&self) -> Option<String> {
        self.error.lock().ok().and_then(|error| error.clone())
    }
}

enum Action {
    ToggleToolbar,
    ShowToolbar,
    ShowOcrResults,
    Secondary(SecondaryView),
    Quit,
}

fn menu_action(id: &str) -> Option<Action> {
    // Tauri menu listeners also receive events from application/window menus.
    match id {
        VISIBILITY => Some(Action::ToggleToolbar),
        SHOW_OCR_RESULTS => Some(Action::ShowOcrResults),
        SAVED => Some(Action::Secondary(SecondaryView::Saved)),
        SETTINGS => Some(Action::Secondary(SecondaryView::Settings)),
        SOURCES => Some(Action::Secondary(SecondaryView::Sources)),
        QUIT => Some(Action::Quit),
        _ => None,
    }
}

fn visibility_label(visible: bool) -> &'static str {
    if visible {
        "Hide Toolbar"
    } else {
        "Show Toolbar"
    }
}

fn show_on_click(button: MouseButton, state: MouseButtonState) -> bool {
    button == MouseButton::Left && state == MouseButtonState::Up
}

pub fn setup(app: &AppHandle) -> Result<(), String> {
    let visibility = MenuItem::with_id(app, VISIBILITY, "Hide Toolbar", true, None::<&str>)
        .map_err(|e| e.to_string())?;
    let show_ocr_results = MenuItem::with_id(
        app,
        SHOW_OCR_RESULTS,
        "Show OCR results",
        false,
        None::<&str>,
    )
    .map_err(|e| e.to_string())?;
    let saved =
        MenuItem::with_id(app, SAVED, "Saved", true, None::<&str>).map_err(|e| e.to_string())?;
    let settings = MenuItem::with_id(app, SETTINGS, "Settings", true, None::<&str>)
        .map_err(|e| e.to_string())?;
    let sources = MenuItem::with_id(app, SOURCES, "Sources & licenses", true, None::<&str>)
        .map_err(|e| e.to_string())?;
    let quit = MenuItem::with_id(app, QUIT, "Quit YomiMado", true, None::<&str>)
        .map_err(|e| e.to_string())?;
    let separator = PredefinedMenuItem::separator(app).map_err(|e| e.to_string())?;
    let quit_separator = PredefinedMenuItem::separator(app).map_err(|e| e.to_string())?;
    let menu = Menu::with_items(
        app,
        &[
            &visibility,
            &show_ocr_results,
            &separator,
            &saved,
            &settings,
            &sources,
            &quit_separator,
            &quit,
        ],
    )
    .map_err(|e| e.to_string())?;
    #[cfg(target_os = "macos")]
    let bytes = include_bytes!("../icons/tray-template.png").as_slice();
    #[cfg(not(target_os = "macos"))]
    let bytes = include_bytes!("../icons/tray-windows.png").as_slice();
    let rgba = image::load_from_memory(bytes)
        .map_err(|e| e.to_string())?
        .into_rgba8();
    let icon = tauri::image::Image::new_owned(rgba.to_vec(), rgba.width(), rgba.height());
    let icon = TrayIconBuilder::with_id("yomimado.tray")
        .icon(icon)
        .icon_as_template(cfg!(target_os = "macos"))
        .tooltip("YomiMado")
        .menu(&menu)
        .show_menu_on_left_click(!cfg!(target_os = "windows"))
        .on_menu_event(|app, event| {
            if let Some(action) = menu_action(event.id().as_ref()) {
                dispatch(app.clone(), action);
            }
        })
        .on_tray_icon_event(|tray, event| {
            if cfg!(target_os = "windows") {
                if let TrayIconEvent::Click {
                    button,
                    button_state,
                    ..
                } = event
                {
                    if show_on_click(button, button_state) {
                        dispatch(tray.app_handle().clone(), Action::ShowToolbar);
                    }
                }
            }
        })
        .build(app)
        .map_err(|e| e.to_string())?;
    app.state::<crate::AppState>()
        .tray
        .menu
        .set(TrayMenu {
            _icon: icon,
            visibility,
            show_ocr_results,
            secondary: [saved, settings, sources],
        })
        .map_err(|_| "Tray icon is already initialized".to_string())?;
    let handle = app.clone();
    tauri::async_runtime::spawn_blocking(move || refresh(&handle));
    Ok(())
}

pub fn refresh(app: &AppHandle) {
    let Some(state) = app.try_state::<crate::AppState>() else {
        return;
    };
    let Some(menu) = state.tray.menu.get() else {
        return;
    };
    let result = (|| {
        // Serialize presentation with scan/visibility transactions so an older
        // snapshot cannot re-enable actions after a capture starts.
        let session = state.scans.lock()?;
        let visible = app
            .get_webview_window("toolbar")
            .ok_or("Toolbar is unavailable")?
            .is_visible()
            .map_err(|e| e.to_string())?;
        menu.visibility
            .set_text(visibility_label(visible))
            .map_err(|e| e.to_string())?;
        let enabled = session.active.is_none();
        menu.visibility
            .set_enabled(enabled)
            .map_err(|e| e.to_string())?;
        menu.show_ocr_results
            .set_enabled(session.can_show_ocr_results(state.overlay.get().is_ok()))
            .map_err(|e| e.to_string())?;
        for item in &menu.secondary {
            item.set_enabled(enabled).map_err(|e| e.to_string())?;
        }
        Ok::<(), String>(())
    })();
    if let Err(error) = result {
        eprintln!("YomiMado: could not refresh tray menu: {error}");
    }
}

fn dispatch(app: AppHandle, action: Action) {
    // Callbacks run on the UI thread. Window commands and session locks must
    // run elsewhere, including WebView2 window creation on Windows.
    tauri::async_runtime::spawn_blocking(move || {
        let result = match action {
            Action::Quit => {
                toolbar::quit_app(app);
                return;
            }
            Action::ShowToolbar => toolbar::set_toolbar_visible(&app, true),
            Action::ShowOcrResults => toolbar::set_overlay_visibility(app.clone(), true),
            Action::ToggleToolbar => app
                .get_webview_window("toolbar")
                .ok_or("Toolbar is unavailable".to_string())
                .and_then(|window| window.is_visible().map_err(|e| e.to_string()))
                .and_then(|visible| toolbar::set_toolbar_visible(&app, !visible)),
            Action::Secondary(view) => toolbar::show_secondary_window(app.clone(), view),
        };
        if let Err(error) = result {
            report_error(&app, format!("Tray action failed: {error}"));
        } else {
            let state = app.state::<crate::AppState>();
            if let Ok(mut error) = state.tray.error.lock() {
                *error = None;
            }
            toolbar::emit_state(&app);
        }
        refresh(&app);
    });
}

pub fn report_error(app: &AppHandle, message: String) {
    eprintln!("YomiMado: {message}");
    if let Ok(mut error) = app.state::<crate::AppState>().tray.error.lock() {
        *error = Some(message);
    }
    // The shared guard prevents error recovery from revealing chrome during a
    // concurrent capture. The diagnostic remains in the toolbar state afterward.
    if toolbar::set_toolbar_visible(app, true).is_err() {
        toolbar::emit_state(app);
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn foreign_application_menu_events_do_not_quit_or_toggle_the_toolbar() {
        for id in [
            "quit",
            "close",
            "settings",
            "show-ocr-results",
            "",
            "yomimado.tray.unknown",
        ] {
            assert!(menu_action(id).is_none());
        }
        assert!(matches!(menu_action(QUIT), Some(Action::Quit)));
        assert!(matches!(
            menu_action(SAVED),
            Some(Action::Secondary(SecondaryView::Saved))
        ));
        assert!(matches!(
            menu_action(SETTINGS),
            Some(Action::Secondary(SecondaryView::Settings))
        ));
        assert!(matches!(
            menu_action(SOURCES),
            Some(Action::Secondary(SecondaryView::Sources))
        ));
        assert!(matches!(
            menu_action(VISIBILITY),
            Some(Action::ToggleToolbar)
        ));
        assert!(matches!(
            menu_action(SHOW_OCR_RESULTS),
            Some(Action::ShowOcrResults)
        ));
    }

    #[test]
    fn only_left_release_restores_the_windows_toolbar() {
        for button in [MouseButton::Left, MouseButton::Right, MouseButton::Middle] {
            assert!(!show_on_click(button, MouseButtonState::Down));
            assert_eq!(
                show_on_click(button, MouseButtonState::Up),
                button == MouseButton::Left
            );
        }
    }

    #[test]
    fn visibility_label_offers_the_inverse_action() {
        assert_eq!(visibility_label(true), "Hide Toolbar");
        assert_eq!(visibility_label(false), "Show Toolbar");
        assert!(!TrayState::default().available());
    }
}
