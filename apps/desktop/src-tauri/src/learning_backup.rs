use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::path::Path;

use serde::Serialize;
use tauri::AppHandle;
use tauri_plugin_dialog::DialogExt;

const MAX_BACKUP_BYTES: u64 = 16 * 1024 * 1024;

fn require_saved_window(label: &str) -> Result<(), String> {
    if label == "saved" {
        Ok(())
    } else {
        Err("Open backup and restore from Saved.".into())
    }
}

fn validate_backup(contents: &str) -> Result<(), String> {
    if contents.len() as u64 > MAX_BACKUP_BYTES {
        return Err("The backup exceeds the 16 MiB size limit.".into());
    }
    let value: serde_json::Value = serde_json::from_str(contents)
        .map_err(|_| "This is not a supported YomiMado saved-data backup.")?;
    if value.get("format").and_then(|v| v.as_str()) != Some("yomimado-saved")
        || value.get("version").and_then(|v| v.as_u64()) != Some(1)
        || !value.get("words").is_some_and(|v| v.is_array())
        || !value.get("sentences").is_some_and(|v| v.is_array())
        || !value.get("createdAt").is_some_and(|v| v.is_string())
    {
        return Err("This is not a supported YomiMado saved-data backup.".into());
    }
    Ok(())
}

fn read_backup(path: &Path) -> Result<String, String> {
    let file = File::open(path).map_err(|error| error.to_string())?;
    let metadata = file.metadata().map_err(|error| error.to_string())?;
    if !metadata.is_file() || metadata.len() > MAX_BACKUP_BYTES {
        return Err("Select a JSON backup of at most 16 MiB.".into());
    }
    let mut contents = String::new();
    file.take(MAX_BACKUP_BYTES + 1)
        .read_to_string(&mut contents)
        .map_err(|_| "Could not read the backup as UTF-8 text.")?;
    validate_backup(&contents)?;
    Ok(contents)
}

fn write_backup(path: &Path, contents: &str) -> Result<(), String> {
    validate_backup(contents)?;
    let parent = path
        .parent()
        .ok_or("Backup destination has no directory.")?;
    let nonce = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_err(|error| error.to_string())?
        .as_nanos();
    let staging = parent.join(format!(
        ".yomimado-backup-{}-{nonce}.tmp",
        std::process::id()
    ));
    let mut options = OpenOptions::new();
    options.write(true).create_new(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.mode(0o600);
    }
    let mut file = options.open(&staging).map_err(|error| error.to_string())?;
    let result = (|| {
        file.write_all(contents.as_bytes())?;
        file.sync_all()?;
        drop(file);
        // Same-directory rename publishes only a complete file, preserving any
        // existing backup if writing fails. The native dialog owns the path.
        fs::rename(&staging, path)
    })();
    if let Err(error) = result {
        let _ = fs::remove_file(&staging);
        return Err(error.to_string());
    }
    Ok(())
}

#[derive(Serialize)]
pub struct BackupFile {
    name: String,
    contents: String,
}

#[tauri::command]
pub async fn choose_learning_backup(
    app: AppHandle,
    window: tauri::WebviewWindow,
) -> Result<Option<BackupFile>, String> {
    require_saved_window(window.label())?;
    tauri::async_runtime::spawn_blocking(move || {
        let selected = app
            .dialog()
            .file()
            .set_parent(&window)
            .add_filter("YomiMado saved-data backup", &["json"])
            .blocking_pick_file();
        let Some(selected) = selected else {
            return Ok(None);
        };
        let path = selected.into_path().map_err(|error| error.to_string())?;
        Ok(Some(BackupFile {
            name: path
                .file_name()
                .ok_or("Backup has no file name.")?
                .to_string_lossy()
                .into_owned(),
            contents: read_backup(&path)?,
        }))
    })
    .await
    .map_err(|error| error.to_string())?
}

#[tauri::command]
pub async fn save_learning_backup(
    app: AppHandle,
    window: tauri::WebviewWindow,
    contents: String,
) -> Result<bool, String> {
    require_saved_window(window.label())?;
    tauri::async_runtime::spawn_blocking(move || {
        validate_backup(&contents)?;
        let selected = app
            .dialog()
            .file()
            .set_parent(&window)
            .add_filter("YomiMado saved-data backup", &["json"])
            .set_file_name("yomimado-saved-backup.json")
            .blocking_save_file();
        let Some(selected) = selected else {
            return Ok(false);
        };
        let path = selected.into_path().map_err(|error| error.to_string())?;
        write_backup(&path, &contents)?;
        Ok(true)
    })
    .await
    .map_err(|error| error.to_string())?
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixture() -> String {
        serde_json::json!({"format":"yomimado-saved", "version":1,
            "createdAt":"2026-10-23T00:00:00+00:00", "words":[], "sentences":[]})
        .to_string()
    }

    #[test]
    fn backup_commands_are_limited_to_saved() {
        assert!(require_saved_window("saved").is_ok());
        for label in ["main", "translation-popup", "ocr-overlay", "toolbar"] {
            assert!(require_saved_window(label).is_err());
        }
    }

    #[test]
    fn backup_files_round_trip_and_failed_writes_preserve_the_old_file() {
        let directory = std::env::temp_dir().join(format!(
            "yomimado-backup-test-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        fs::create_dir(&directory).unwrap();
        let path = directory.join("saved.json");
        let original = fixture();
        write_backup(&path, &original).unwrap();
        assert_eq!(read_backup(&path).unwrap(), original);
        assert!(write_backup(&path, "not JSON").is_err());
        assert_eq!(fs::read_to_string(&path).unwrap(), original);
        let revised = original.replace("2026-10-23", "2026-10-24");
        write_backup(&path, &revised).unwrap();
        assert_eq!(read_backup(&path).unwrap(), revised);
        let target_directory = directory.join("directory.json");
        fs::create_dir(&target_directory).unwrap();
        assert!(write_backup(&target_directory, &original).is_err());
        assert_eq!(fs::read_dir(&directory).unwrap().count(), 2);
        fs::write(&path, [0xff, 0xfe]).unwrap();
        assert!(read_backup(&path).is_err());
        fs::write(&path, vec![b' '; MAX_BACKUP_BYTES as usize + 1]).unwrap();
        assert!(read_backup(&path).is_err());
        fs::remove_dir_all(&directory).unwrap();
    }

    #[test]
    fn rejects_other_files_and_future_versions() {
        assert!(validate_backup("{}").is_err());
        assert!(validate_backup(&fixture().replace("\"version\":1", "\"version\":2")).is_err());
        assert!(validate_backup(&" ".repeat(MAX_BACKUP_BYTES as usize + 1)).is_err());
    }
}
