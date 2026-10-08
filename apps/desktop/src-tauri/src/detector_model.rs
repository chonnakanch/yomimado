use std::fs;
use std::io::{BufReader, Read};
use std::path::{Path, PathBuf};

use serde::Serialize;
use sha2::{Digest, Sha256};
use tauri::{AppHandle, Manager};
use tauri_plugin_dialog::DialogExt;

const MODEL_NAME: &str = "comictextdetector.pt.onnx";
const MODEL_SHA256: &str = "1a86ace74961413cbd650002e7bb4dcec4980ffa21b2f19b86933372071d718f";
const MAX_MODEL_BYTES: u64 = 256 * 1024 * 1024;

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DetectorModelStatus {
    required: bool,
    installed: bool,
}

pub fn installed_path(app: &AppHandle) -> Result<PathBuf, String> {
    app.path()
        .app_data_dir()
        .map(|path| path.join("models").join(MODEL_NAME))
        .map_err(|error| error.to_string())
}

fn status(app: &AppHandle) -> Result<DetectorModelStatus, String> {
    Ok(DetectorModelStatus {
        required: cfg!(all(
            not(debug_assertions),
            any(target_os = "macos", target_os = "windows")
        )),
        installed: installed_path(app)?.is_file(),
    })
}

pub fn ensure_available(app: &AppHandle) -> Result<(), String> {
    let model = status(app)?;
    if model.required && !model.installed {
        return Err("Install the detector model in YomiMado before scanning.".into());
    }
    Ok(())
}

#[tauri::command]
pub fn detector_model_status(app: AppHandle) -> Result<DetectorModelStatus, String> {
    status(&app)
}

fn verify_model(path: &Path) -> Result<(), String> {
    let file = fs::File::open(path).map_err(|error| error.to_string())?;
    let size = file.metadata().map_err(|error| error.to_string())?.len();
    if size == 0 || size > MAX_MODEL_BYTES {
        return Err("This is not the expected detector model file.".into());
    }
    let mut reader = BufReader::new(file);
    let mut hasher = Sha256::new();
    let mut buffer = [0_u8; 64 * 1024];
    loop {
        let count = reader
            .read(&mut buffer)
            .map_err(|error| error.to_string())?;
        if count == 0 {
            break;
        }
        hasher.update(&buffer[..count]);
    }
    if format!("{:x}", hasher.finalize()) != MODEL_SHA256 {
        return Err("The selected file does not match the supported detector model.".into());
    }
    Ok(())
}

fn copy_verified_model(source: &Path, destination: &Path) -> Result<(), String> {
    if source == destination {
        return verify_model(source);
    }
    let parent = destination
        .parent()
        .ok_or("Model destination has no directory")?;
    fs::create_dir_all(parent).map_err(|error| error.to_string())?;
    let staging = parent.join(format!(".{MODEL_NAME}.partial"));
    if let Err(error) = fs::copy(source, &staging) {
        let _ = fs::remove_file(&staging);
        return Err(error.to_string());
    }
    if let Err(error) = verify_model(&staging) {
        let _ = fs::remove_file(&staging);
        return Err(error);
    }
    if let Err(error) = fs::rename(&staging, destination) {
        let _ = fs::remove_file(&staging);
        return Err(error.to_string());
    }
    Ok(())
}

#[tauri::command]
pub async fn install_detector_model(app: AppHandle) -> Result<Option<DetectorModelStatus>, String> {
    tauri::async_runtime::spawn_blocking(move || {
        let selected = app
            .dialog()
            .file()
            .add_filter("ONNX detector model", &["onnx"])
            .blocking_pick_file();
        let Some(selected) = selected else {
            return Ok(None);
        };
        let source = selected.into_path().map_err(|error| error.to_string())?;
        let destination = installed_path(&app)?;
        copy_verified_model(&source, &destination)?;
        Ok(Some(status(&app)?))
    })
    .await
    .map_err(|error| error.to_string())?
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_an_unrelated_file() {
        let path = std::env::temp_dir().join(format!(
            "yomimado-wrong-detector-{}.onnx",
            std::process::id()
        ));
        fs::write(&path, b"not a detector model").unwrap();
        assert!(verify_model(&path).is_err());
        fs::remove_file(path).unwrap();
    }

    #[test]
    fn invalid_import_does_not_install_a_model() {
        let directory = std::env::temp_dir().join(format!(
            "yomimado-detector-import-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        fs::create_dir(&directory).unwrap();
        let source = directory.join("invalid.onnx");
        let destination = directory.join("models").join(MODEL_NAME);
        fs::write(&source, b"not a detector model").unwrap();

        assert!(copy_verified_model(&source, &destination).is_err());
        assert!(!destination.exists());
        assert!(!destination
            .with_file_name(format!(".{MODEL_NAME}.partial"))
            .exists());

        fs::remove_file(source).unwrap();
        fs::remove_dir(destination.parent().unwrap()).unwrap();
        fs::remove_dir(directory).unwrap();
    }
}
