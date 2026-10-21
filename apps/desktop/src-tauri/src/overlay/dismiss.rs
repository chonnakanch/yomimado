//! Escape belongs to a visible, completed OCR result only. It is released while
//! another YomiMado window owns keyboard input, preserving popup/menu/IME Escape.
use std::sync::{
    atomic::{AtomicU64, Ordering},
    Mutex,
};
use tauri::{AppHandle, Emitter, Manager};
use tauri_plugin_global_shortcut::{Code, GlobalShortcutExt, Shortcut, ShortcutState};

#[derive(Default)]
pub struct DismissShortcut {
    registration: Mutex<bool>,
    session: AtomicU64,
}

fn shortcut() -> Shortcut {
    Shortcut::new(None, Code::Escape)
}

fn update_registration(
    registered: &mut bool,
    needed: bool,
    change: impl FnOnce(bool) -> Result<(), String>,
) -> Result<(), String> {
    if *registered != needed {
        change(needed)?;
        *registered = needed;
    }
    Ok(())
}

fn protected_focus(app: &AppHandle) -> bool {
    app.webview_windows()
        .iter()
        .any(|(label, window)| label != "ocr-overlay" && window.is_focused().unwrap_or(true))
}

fn eligible(
    active_scan: bool,
    visible: bool,
    interactive: bool,
    protected: bool,
    completed: Option<u64>,
) -> Option<u64> {
    if active_scan || !visible || !interactive || protected {
        None
    } else {
        completed
    }
}

pub fn queue_sync(app: &AppHandle) {
    let app = app.clone();
    tauri::async_runtime::spawn_blocking(move || {
        if let Err(error) = sync(&app) {
            eprintln!("YomiMado: {error}");
            let _ = app.emit_to("toolbar", "toolbar-action-error", error);
        }
    });
}

fn sync(app: &AppHandle) -> Result<(), String> {
    let Some(binding) = app.try_state::<DismissShortcut>() else {
        return Ok(());
    };
    let mut registered = binding.registration.lock().map_err(|e| e.to_string())?;
    let state = app.state::<crate::AppState>();
    let (active, visible, completed) = {
        let session = state.scans.lock()?;
        (
            session.active.is_some(),
            session.overlay_visible,
            session.completed_id,
        )
    };
    let target = eligible(
        active,
        visible,
        state.overlay_input.is_active(),
        protected_focus(app),
        completed,
    );
    // The shortcut handler reads only this atomic while the plugin holds its
    // registry lock. Never acquire scan/registration locks in that handler.
    binding.session.store(target.unwrap_or(0), Ordering::SeqCst);
    let result = update_registration(&mut registered, target.is_some(), |needed| {
        if needed {
            app.global_shortcut().register(shortcut()).map_err(|_| {
                "Escape to hide OCR is unavailable. Use the hide icon or toolbar toggle."
                    .to_string()
            })
        } else {
            app.global_shortcut().unregister(shortcut()).map_err(|_| {
                "Could not release the OCR Escape shortcut. Restart YomiMado to release it."
                    .to_string()
            })
        }
    });
    if result.is_err() {
        binding.session.store(0, Ordering::SeqCst);
    }
    result
}

pub fn handle(app: &AppHandle, key: &Shortcut, state: ShortcutState) -> bool {
    if *key != shortcut() {
        return false;
    }
    if state == ShortcutState::Pressed {
        if let Some(binding) = app.try_state::<DismissShortcut>() {
            let id = binding.session.load(Ordering::SeqCst);
            if id != 0 {
                let app = app.clone();
                tauri::async_runtime::spawn_blocking(move || {
                    // Focus and generation may have changed since the key event.
                    if protected_focus(&app) {
                        return;
                    }
                    let focused = app
                        .get_webview_window("ocr-overlay")
                        .is_some_and(|w| w.is_focused().unwrap_or(false));
                    match crate::toolbar::hide_completed_overlay(&app, id) {
                        Ok(true) if focused => {
                            if let Some(toolbar) = app.get_webview_window("toolbar") {
                                let _ = toolbar.set_focus();
                            }
                        }
                        Ok(_) => {}
                        Err(error) => {
                            let _ = app.emit_to("toolbar", "toolbar-action-error", error);
                        }
                    }
                });
            }
        }
    }
    true
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn escape_is_scoped_to_interactive_completed_results_outside_other_app_windows() {
        assert_eq!(eligible(false, true, true, false, Some(12)), Some(12));
        for (active, visible, interactive, protected, id) in [
            (true, true, true, false, Some(12)),
            (false, false, true, false, Some(12)),
            (false, true, false, false, Some(12)),
            (false, true, true, true, Some(12)),
            (false, true, true, false, None),
        ] {
            assert_eq!(eligible(active, visible, interactive, protected, id), None);
        }
    }

    #[test]
    fn temporary_escape_is_distinct_from_modified_capture_shortcuts() {
        assert_eq!(shortcut(), Shortcut::try_from("Escape").unwrap());
        assert_ne!(shortcut(), Shortcut::try_from("Control+Escape").unwrap());
    }
    #[test]
    fn temporary_registration_releases_once_and_preserves_failed_operations_for_retry() {
        let mut registered = false;
        assert!(update_registration(&mut registered, true, |_| Err("conflict".into())).is_err());
        assert!(!registered);
        update_registration(&mut registered, true, |_| Ok(())).unwrap();
        update_registration(&mut registered, true, |_| panic!("must not register twice")).unwrap();
        assert!(
            update_registration(&mut registered, false, |_| Err("release failed".into())).is_err()
        );
        assert!(registered);
        update_registration(&mut registered, false, |_| Ok(())).unwrap();
        assert!(!registered);
    }
}
