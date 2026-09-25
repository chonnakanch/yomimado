use std::{fs, io, path::Path};

fn is_legacy_capture(name: &str) -> bool {
    name.strip_prefix("capture-")
        .and_then(|rest| rest.strip_suffix(".png"))
        .is_some_and(|timestamp| {
            !timestamp.is_empty() && timestamp.bytes().all(|byte| byte.is_ascii_digit())
        })
}

/// Remove only PNG captures written by older YomiMado builds. New captures
/// stay in memory, so this is a one-time migration on the next app launch.
pub fn cleanup_legacy_captures(directory: &Path) -> io::Result<usize> {
    let entries = match fs::read_dir(directory) {
        Ok(entries) => entries,
        Err(error) if error.kind() == io::ErrorKind::NotFound => return Ok(0),
        Err(error) => return Err(error),
    };

    let mut removed = 0;
    for entry in entries {
        let entry = entry?;
        if !entry.file_type()?.is_file() {
            continue;
        }
        if !entry.file_name().to_str().is_some_and(is_legacy_capture) {
            continue;
        }
        match fs::remove_file(entry.path()) {
            Ok(()) => removed += 1,
            Err(error) if error.kind() == io::ErrorKind::NotFound => {}
            Err(error) => return Err(error),
        }
    }
    Ok(removed)
}

#[cfg(test)]
mod tests {
    use std::time::{SystemTime, UNIX_EPOCH};

    use super::*;

    #[test]
    fn only_matches_legacy_capture_names() {
        assert!(is_legacy_capture("capture-1790333857278.png"));
        assert!(!is_legacy_capture("capture-.png"));
        assert!(!is_legacy_capture("capture-debug.png"));
        assert!(!is_legacy_capture("capture-1790333857278.jpg"));
        assert!(!is_legacy_capture("other-1790333857278.png"));
    }

    #[test]
    fn removes_only_legacy_capture_files_from_its_directory() {
        let nonce = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let directory = std::env::temp_dir().join(format!(
            "yomimado-cache-test-{}-{nonce}",
            std::process::id()
        ));
        fs::create_dir(&directory).unwrap();
        let capture = directory.join("capture-123.png");
        let unrelated = directory.join("notes.txt");
        let similarly_named = directory.join("capture-debug.png");
        let matching_directory = directory.join("capture-456.png");
        fs::write(&capture, b"capture").unwrap();
        fs::write(&unrelated, b"note").unwrap();
        fs::write(&similarly_named, b"debug").unwrap();
        fs::create_dir(&matching_directory).unwrap();

        assert_eq!(cleanup_legacy_captures(&directory).unwrap(), 1);
        assert!(!capture.exists());
        assert!(unrelated.exists());
        assert!(similarly_named.exists());
        assert!(matching_directory.exists());
        fs::remove_dir_all(&directory).unwrap();
    }
}
