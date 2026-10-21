use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::Mutex;

use serde::{Deserialize, Serialize};
use tauri::{AppHandle, Emitter, Manager, WebviewWindow};
use tauri_plugin_global_shortcut::{GlobalShortcutExt, Modifiers, Shortcut, ShortcutState};

const RECORDED_EVENT: &str = "capture-shortcut-recorded";

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize)]
#[serde(rename_all = "camelCase", deny_unknown_fields)]
pub struct Bindings {
    selected_area: String,
    whole_screen: String,
}

impl Default for Bindings {
    fn default() -> Self {
        Self {
            selected_area: "CmdOrControl+Shift+KeyO".into(),
            whole_screen: "CmdOrControl+Shift+KeyS".into(),
        }
    }
}

impl Bindings {
    fn parse(&self) -> Result<[Shortcut; 2], String> {
        let parse = |text: &str| -> Result<Shortcut, String> {
            let shortcut = Shortcut::try_from(text).map_err(|_| "Invalid shortcut.".to_string())?;
            let key = shortcut.key.to_string();
            let supported = (key.starts_with("Key") && key.len() == 4)
                || (key.starts_with("Digit") && key.len() == 6)
                || key
                    .strip_prefix('F')
                    .is_some_and(|n| n.parse::<u8>().is_ok_and(|n| (1..=24).contains(&n)));
            if !supported
                || !shortcut
                    .mods
                    .intersects(Modifiers::CONTROL | Modifiers::SUPER | Modifiers::ALT)
            {
                return Err("Use Ctrl, Command/Windows or Alt with a letter, number or F1–F24. Shift is optional.".into());
            }
            Ok(shortcut)
        };
        let keys = [parse(&self.selected_area)?, parse(&self.whole_screen)?];
        if keys[0] == keys[1] {
            return Err("Selected Area and Whole Screen need different shortcuts.".into());
        }
        Ok(keys)
    }

    fn normalized(&self) -> Result<Self, String> {
        let keys = self.parse()?;
        Ok(Self {
            selected_area: keys[0].to_string(),
            whole_screen: keys[1].to_string(),
        })
    }
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Snapshot {
    bindings: Bindings,
    defaults: Bindings,
    available: [bool; 2],
    warnings: Vec<String>,
}

struct Settings {
    bindings: Bindings,
    registered: Vec<Shortcut>,
    warnings: Vec<String>,
}

trait Registry {
    fn register(&self, key: Shortcut) -> Result<(), String>;
    fn unregister(&self, key: Shortcut) -> Result<(), String>;
}

struct NativeRegistry<'a>(&'a AppHandle);

impl Registry for NativeRegistry<'_> {
    fn register(&self, key: Shortcut) -> Result<(), String> {
        self.0.global_shortcut().register(key).map_err(|_| {
            "Shortcut unavailable. It may be reserved by the system or another app. Choose another combination.".into()
        })
    }

    fn unregister(&self, key: Shortcut) -> Result<(), String> {
        self.0
            .global_shortcut()
            .unregister(key)
            .map_err(|e| e.to_string())
    }
}

impl Settings {
    fn snapshot(&self) -> Snapshot {
        let keys = self.bindings.parse().expect("validated capture shortcuts");
        Snapshot {
            bindings: self.bindings.clone(),
            defaults: Bindings::default().normalized().expect("valid defaults"),
            available: keys.map(|key| self.registered.contains(&key)),
            warnings: self.warnings.clone(),
        }
    }

    fn release(&mut self, keys: &[Shortcut], registry: &impl Registry) {
        for key in keys {
            match registry.unregister(*key) {
                Ok(()) => self.registered.retain(|registered| registered != key),
                Err(_) => self.warnings.push(
                    "An old shortcut could not be released. Restart YomiMado to release it.".into(),
                ),
            }
        }
    }

    fn apply(
        &mut self,
        bindings: Bindings,
        registry: &impl Registry,
        save: impl FnOnce(&Bindings) -> Result<(), String>,
    ) -> Result<(), String> {
        let bindings = bindings.normalized()?;
        let keys = bindings.parse()?;
        let mut added = Vec::new();
        for key in keys {
            if self.registered.contains(&key) {
                continue;
            }
            if let Err(error) = registry.register(key) {
                self.release(&added, registry);
                return Err(error);
            }
            self.registered.push(key);
            added.push(key);
        }
        if let Err(error) = save(&bindings) {
            self.release(&added, registry);
            return Err(error);
        }
        self.bindings = bindings;
        self.warnings.clear();
        let obsolete: Vec<_> = self
            .registered
            .iter()
            .copied()
            .filter(|k| !keys.contains(k))
            .collect();
        self.release(&obsolete, registry);
        Ok(())
    }
}

pub struct Store {
    settings: Mutex<Settings>,
    path: Option<PathBuf>,
    // The handler never locks settings: the plugin calls it while holding its
    // registry lock. Registration runs on the UI thread from async commands.
    active: AtomicU64,
    updating: AtomicBool,
    recording: AtomicBool,
}

fn load(path: Option<&Path>) -> (Bindings, Vec<String>) {
    let result = path.ok_or("Shortcut storage is unavailable.".to_string()).and_then(|path| {
        match std::fs::read(path) {
            Ok(bytes) => serde_json::from_slice::<Bindings>(&bytes)
                .map_err(|_| "Saved shortcuts could not be read; defaults are active. Save shortcuts to replace the damaged file.".to_string())?
                .normalized(),
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(Bindings::default()),
            Err(_) => Err("Saved shortcuts could not be read; defaults are active.".into()),
        }
    });
    match result {
        Ok(bindings) => (
            bindings.normalized().expect("validated capture shortcuts"),
            Vec::new(),
        ),
        Err(error) => (
            Bindings::default().normalized().expect("valid defaults"),
            vec![error],
        ),
    }
}

fn save(path: &Path, bindings: &Bindings) -> Result<(), String> {
    let temporary = path.with_extension("json.tmp");
    let write = || -> Result<(), Box<dyn std::error::Error>> {
        std::fs::create_dir_all(path.parent().ok_or("Missing settings directory")?)?;
        let file = std::fs::File::create(&temporary)?;
        serde_json::to_writer_pretty(&file, bindings)?;
        file.sync_all()?;
        std::fs::rename(&temporary, path)?;
        Ok(())
    };
    write().map_err(|_| {
        let _ = std::fs::remove_file(&temporary);
        "Could not save shortcuts. Your previous shortcuts are unchanged.".into()
    })
}

impl Store {
    pub fn new(app: &AppHandle) -> Self {
        let path = app
            .path()
            .app_config_dir()
            .ok()
            .map(|p| p.join("capture-shortcuts.json"));
        let (bindings, warnings) = load(path.as_deref());
        Self {
            settings: Mutex::new(Settings {
                bindings,
                registered: Vec::new(),
                warnings,
            }),
            path,
            active: AtomicU64::new(0),
            updating: AtomicBool::new(false),
            recording: AtomicBool::new(false),
        }
    }

    fn activate(&self, bindings: &Bindings) {
        let keys = bindings.parse().expect("validated capture shortcuts");
        self.active.store(
            u64::from(keys[0].id()) | (u64::from(keys[1].id()) << 32),
            Ordering::SeqCst,
        );
    }

    pub fn stop_recording(&self) {
        self.recording.store(false, Ordering::SeqCst);
    }
}

pub fn initialize(app: &AppHandle) {
    let state = app.state::<Store>();
    let mut settings = state.settings.lock().expect("shortcut settings lock");
    for key in settings
        .bindings
        .parse()
        .expect("validated capture shortcuts")
    {
        match NativeRegistry(app).register(key) {
            Ok(()) => settings.registered.push(key),
            Err(error) => settings.warnings.push(format!("{key}: {error}")),
        }
    }
    state.activate(&settings.bindings);
    for warning in &settings.warnings {
        eprintln!("YomiMado: {warning}");
    }
}

pub fn handle(app: &AppHandle, key: &Shortcut, event: tauri_plugin_global_shortcut::ShortcutEvent) {
    let Some(state) = app.try_state::<Store>() else {
        return;
    };
    if state.updating.load(Ordering::SeqCst) {
        return;
    }
    if state.recording.load(Ordering::SeqCst)
        && app
            .get_webview_window("main")
            .is_some_and(|w| w.is_focused().unwrap_or(false))
    {
        // Registered chords can be consumed by the OS before the webview sees
        // keydown. Forward them to the recorder instead of starting a capture.
        if event.state() == ShortcutState::Released {
            let _ = app.emit_to("main", RECORDED_EVENT, key.to_string());
        }
        return;
    }
    if event.state() != ShortcutState::Pressed {
        return;
    }
    let active = state.active.load(Ordering::SeqCst);
    if key.id() == active as u32 {
        super::dispatch_capture_shortcut(app.clone(), "");
    } else if key.id() == (active >> 32) as u32 {
        super::dispatch_capture_shortcut(app.clone(), "scan=whole");
    }
}

fn settings_window(window: &WebviewWindow) -> Result<(), String> {
    if window.label() != "main" {
        return Err("Change capture shortcuts from Settings.".into());
    }
    Ok(())
}

#[tauri::command(async)]
pub fn capture_shortcuts(app: AppHandle, window: WebviewWindow) -> Result<Snapshot, String> {
    settings_window(&window)?;
    let state = app.state::<Store>();
    let settings = state
        .settings
        .lock()
        .map_err(|_| "Shortcut settings are busy.")?;
    Ok(settings.snapshot())
}

#[tauri::command]
pub fn record_capture_shortcut(
    app: AppHandle,
    window: WebviewWindow,
    recording: bool,
) -> Result<(), String> {
    settings_window(&window)?;
    if recording && !window.is_focused().map_err(|e| e.to_string())? {
        return Err("Focus Settings before recording a shortcut.".into());
    }
    app.state::<Store>()
        .recording
        .store(recording, Ordering::SeqCst);
    Ok(())
}

#[tauri::command(async)]
pub fn set_capture_shortcuts(
    app: AppHandle,
    window: WebviewWindow,
    bindings: Bindings,
) -> Result<Snapshot, String> {
    settings_window(&window)?;
    let state = app.state::<Store>();
    let mut settings = state
        .settings
        .lock()
        .map_err(|_| "Shortcut settings are busy.")?;
    let path = state
        .path
        .as_deref()
        .ok_or("Shortcut storage is unavailable.")?;
    state.updating.store(true, Ordering::SeqCst);
    let result = settings.apply(bindings, &NativeRegistry(&app), |b| save(path, b));
    state.activate(&settings.bindings);
    state.updating.store(false, Ordering::SeqCst);
    state.stop_recording();
    result?;
    Ok(settings.snapshot())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::cell::RefCell;

    #[derive(Default)]
    struct FakeRegistry {
        keys: RefCell<Vec<Shortcut>>,
        conflict: Option<Shortcut>,
    }

    impl Registry for FakeRegistry {
        fn register(&self, key: Shortcut) -> Result<(), String> {
            if self.conflict == Some(key) {
                return Err("Shortcut unavailable".into());
            }
            self.keys.borrow_mut().push(key);
            Ok(())
        }
        fn unregister(&self, key: Shortcut) -> Result<(), String> {
            self.keys.borrow_mut().retain(|k| *k != key);
            Ok(())
        }
    }

    fn initial() -> (Settings, FakeRegistry) {
        let bindings = Bindings::default().normalized().unwrap();
        let keys = bindings.parse().unwrap().to_vec();
        (
            Settings {
                bindings,
                registered: keys.clone(),
                warnings: Vec::new(),
            },
            FakeRegistry {
                keys: RefCell::new(keys),
                conflict: None,
            },
        )
    }

    fn custom() -> Bindings {
        Bindings {
            selected_area: "Ctrl+Alt+KeyK".into(),
            whole_screen: "Ctrl+Alt+Digit9".into(),
        }
    }

    #[test]
    fn validates_modifiers_keys_and_canonical_duplicates() {
        assert!(Bindings::default().parse().is_ok());
        for key in [
            "KeyK",
            "Shift+KeyK",
            "Ctrl+Escape",
            "Alt+Space",
            "Ctrl+F25",
            "Ctrl+KeyK+KeyS",
        ] {
            let mut bindings = custom();
            bindings.selected_area = key.into();
            assert!(bindings.parse().is_err(), "{key}");
        }
        let mut bindings = custom();
        bindings.whole_screen = "alt+control+k".into();
        assert!(bindings.parse().unwrap_err().contains("different"));
        bindings.whole_screen = "Ctrl+Shift+F24".into();
        assert!(bindings.parse().is_ok());
    }

    #[test]
    fn failed_second_registration_releases_first_and_preserves_old_bindings() {
        let (mut settings, mut registry) = initial();
        let old = settings.bindings.clone();
        let original = registry.keys.borrow().clone();
        registry.conflict = Some(custom().parse().unwrap()[1]);
        let result = settings.apply(custom(), &registry, |_| {
            panic!("must not save a conflicting pair")
        });
        assert!(result.is_err());
        assert_eq!(settings.bindings, old);
        assert_eq!(*registry.keys.borrow(), original);
        assert_eq!(settings.registered, original);
    }

    #[test]
    fn failed_save_rolls_back_new_registrations() {
        let (mut settings, registry) = initial();
        let old = settings.bindings.clone();
        let original = registry.keys.borrow().clone();
        assert!(settings
            .apply(custom(), &registry, |_| Err("disk full".into()))
            .is_err());
        assert_eq!(settings.bindings, old);
        assert_eq!(*registry.keys.borrow(), original);
    }

    #[test]
    fn successful_update_releases_old_keys_and_can_restore_or_swap() {
        let (mut settings, registry) = initial();
        let defaults = settings.bindings.clone();
        settings.apply(custom(), &registry, |_| Ok(())).unwrap();
        assert_eq!(settings.bindings, custom().normalized().unwrap());
        assert_eq!(*registry.keys.borrow(), custom().parse().unwrap());
        assert_eq!(settings.snapshot().available, [true, true]);
        settings
            .apply(defaults.clone(), &registry, |_| Ok(()))
            .unwrap();
        let swapped = Bindings {
            selected_area: defaults.whole_screen,
            whole_screen: defaults.selected_area,
        };
        settings
            .apply(swapped.clone(), &registry, |_| Ok(()))
            .unwrap();
        assert_eq!(settings.bindings, swapped);
        assert_eq!(registry.keys.borrow().len(), 2);
    }

    #[test]
    fn settings_round_trip_and_corrupt_file_preservation() {
        let directory = std::env::temp_dir().join(format!(
            "yomimado-shortcuts-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        let path = directory.join("capture-shortcuts.json");
        assert!(load(Some(&path)).1.is_empty());
        assert_eq!(
            load(Some(&path)).0,
            Bindings::default().normalized().unwrap()
        );
        save(&path, &custom()).unwrap();
        assert_eq!(load(Some(&path)).0, custom().normalized().unwrap());
        assert!(!path.with_extension("json.tmp").exists());
        std::fs::write(&path, b"broken json").unwrap();
        let (bindings, warnings) = load(Some(&path));
        assert_eq!(bindings, Bindings::default().normalized().unwrap());
        assert!(!warnings.is_empty());
        assert_eq!(std::fs::read(&path).unwrap(), b"broken json");
        std::fs::remove_dir_all(directory).unwrap();
    }

    #[test]
    fn startup_registration_failure_is_reported_without_claiming_availability() {
        let (mut settings, registry) = initial();
        registry.keys.borrow_mut().remove(0);
        settings.registered.remove(0);
        assert_eq!(settings.snapshot().available, [false, true]);
        settings
            .apply(settings.bindings.clone(), &registry, |_| Ok(()))
            .unwrap();
        assert_eq!(settings.snapshot().available, [true, true]);
    }
}
