//! Windows-only frozen service lifecycle. No changes to the reviewed macOS runtime.
use std::ffi::c_void;
use std::io;
use std::net::TcpListener;
use std::os::windows::{io::AsRawHandle, process::CommandExt};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};
use tauri::Manager;

// Windows SDK winnt.h layouts. Keep the small kernel32 boundary local instead
// of changing the reviewed cross-platform Cargo dependency lock.
#[repr(C)]
#[derive(Default)]
struct BasicLimits {
    process_time: i64,
    job_time: i64,
    flags: u32,
    minimum_working_set: usize,
    maximum_working_set: usize,
    active_processes: u32,
    affinity: usize,
    priority: u32,
    scheduling: u32,
}
#[repr(C)]
#[derive(Default)]
struct ExtendedLimits {
    basic: BasicLimits,
    io: [u64; 6],
    process_memory: usize,
    job_memory: usize,
    peak_process_memory: usize,
    peak_job_memory: usize,
}
#[repr(C)]
#[derive(Default)]
struct ThreadEntry {
    size: u32,
    usage: u32,
    thread_id: u32,
    process_id: u32,
    base_priority: i32,
    delta_priority: i32,
    flags: u32,
}
#[link(name = "kernel32")]
extern "system" {
    fn CreateJobObjectW(attributes: *const c_void, name: *const u16) -> *mut c_void;
    fn SetInformationJobObject(job: *mut c_void, class: i32, info: *const c_void, size: u32)
        -> i32;
    fn AssignProcessToJobObject(job: *mut c_void, process: *mut c_void) -> i32;
    fn CloseHandle(handle: *mut c_void) -> i32;
    fn CreateToolhelp32Snapshot(flags: u32, process: u32) -> *mut c_void;
    fn Thread32First(snapshot: *mut c_void, entry: *mut ThreadEntry) -> i32;
    fn Thread32Next(snapshot: *mut c_void, entry: *mut ThreadEntry) -> i32;
    fn OpenThread(access: u32, inherit: i32, thread: u32) -> *mut c_void;
    fn ResumeThread(thread: *mut c_void) -> u32;
}
struct Job(*mut c_void);
// The handle is exclusively owned; kernel32 job operations are thread safe.
unsafe impl Send for Job {}
impl Job {
    fn new() -> io::Result<Self> {
        // Null security attributes create a non-inheritable handle.
        let job = Self(unsafe { CreateJobObjectW(std::ptr::null(), std::ptr::null()) });
        if job.0.is_null() {
            return Err(io::Error::last_os_error());
        }
        let mut limits = ExtendedLimits::default();
        limits.basic.flags = 0x2000; // JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        let ok = unsafe {
            SetInformationJobObject(
                job.0,
                9, // JobObjectExtendedLimitInformation
                &limits as *const _ as *const c_void,
                std::mem::size_of::<ExtendedLimits>() as u32,
            )
        };
        if ok == 0 {
            return Err(io::Error::last_os_error());
        }
        Ok(job)
    }
    fn assign(&self, child: &Child) -> io::Result<()> {
        if unsafe { AssignProcessToJobObject(self.0, child.as_raw_handle()) } == 0 {
            return Err(io::Error::last_os_error());
        }
        Ok(())
    }
}
impl Drop for Job {
    fn drop(&mut self) {
        if !self.0.is_null() {
            unsafe { CloseHandle(self.0) };
        }
    }
}

fn resume_primary_thread(pid: u32) -> io::Result<()> {
    // std::process closes CreateProcess's thread handle. Find the single
    // initial thread while CREATE_SUSPENDED prevents application code running.
    let snapshot = unsafe { CreateToolhelp32Snapshot(0x4, 0) }; // TH32CS_SNAPTHREAD
    if snapshot as isize == -1 {
        return Err(io::Error::last_os_error());
    }
    let mut entry = ThreadEntry {
        size: std::mem::size_of::<ThreadEntry>() as u32,
        ..Default::default()
    };
    let mut threads = Vec::new();
    let mut found = unsafe { Thread32First(snapshot, &mut entry) } != 0;
    while found {
        if entry.process_id == pid {
            threads.push(entry.thread_id);
        }
        entry.size = std::mem::size_of::<ThreadEntry>() as u32;
        found = unsafe { Thread32Next(snapshot, &mut entry) } != 0;
    }
    unsafe { CloseHandle(snapshot) };
    if threads.len() != 1 {
        return Err(io::Error::other(
            "Cannot identify the suspended OCR primary thread",
        ));
    }
    let thread = unsafe { OpenThread(0x2, 0, threads[0]) }; // THREAD_SUSPEND_RESUME
    if thread.is_null() {
        return Err(io::Error::last_os_error());
    }
    let count = unsafe { ResumeThread(thread) };
    let error = io::Error::last_os_error();
    unsafe { CloseHandle(thread) };
    if count == u32::MAX {
        return Err(error);
    }
    if count != 1 {
        return Err(io::Error::other("Unexpected OCR thread suspension count"));
    }
    Ok(())
}

pub struct Service {
    child: Child,
    job: Option<Job>,
    ready: PathBuf,
}
impl Drop for Service {
    fn drop(&mut self) {
        self.job.take();
        let _ = self.child.kill();
        let _ = self.child.wait();
        let _ = std::fs::remove_file(&self.ready);
    }
}

fn ready_matches(path: &Path, pid: u32, instance: &str) -> bool {
    std::fs::read(path)
        .ok()
        .and_then(|bytes| serde_json::from_slice::<serde_json::Value>(&bytes).ok())
        .is_some_and(|value| {
            value["pid"].as_u64() == Some(u64::from(pid))
                && value["instanceId"].as_str() == Some(instance)
                && value["port"].as_u64() == Some(8766)
        })
}

pub fn start(app: &tauri::App) -> Result<Service, Box<dyn std::error::Error>> {
    // Never adopt another app's service or a previous developer process.
    let probe = TcpListener::bind(("127.0.0.1", 8766))
        .map_err(|e| format!("Port 8766 is occupied. Quit the other YomiMado/OCR process: {e}"))?;
    let resources = app.path().resource_dir()?.join("ocr");
    let assets = resources.join("assets");
    let data = app.path().app_data_dir()?;
    std::fs::create_dir_all(&data)?;
    let instance = format!(
        "{}-{}",
        std::process::id(),
        SystemTime::now().duration_since(UNIX_EPOCH)?.as_nanos()
    );
    let ready = data.join(format!("service-ready-{instance}.json"));
    let job = Job::new()?;
    let mut command = Command::new(resources.join("runtime/yomimado-ocr.exe"));
    command
        .creation_flags(0x08000004) // CREATE_NO_WINDOW | CREATE_SUSPENDED
        .current_dir(&data)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .env_remove("PYTHONPATH")
        .env_remove("PYTHONHOME")
        .env("YOMIMADO_OCR_PORT", "8766")
        .env("YOMIMADO_READY_FILE", &ready)
        .env("YOMIMADO_SERVICE_INSTANCE", &instance)
        .env("YOMIMADO_DETECTOR_REPO", assets.join("comic-text-detector"))
        .env(
            "YOMIMADO_DETECTOR_MODEL",
            crate::detector_model::installed_path(app.handle())?,
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
        .env("HF_HOME", data.join("hf-cache"))
        .env("HF_HUB_OFFLINE", "1")
        .env("TRANSFORMERS_OFFLINE", "1")
        .env("CUDA_VISIBLE_DEVICES", "");
    drop(probe);
    let child = command
        .spawn()
        .map_err(|e| format!("Cannot launch bundled OCR executable: {e}"))?;
    let mut service = Service {
        child,
        job: None,
        ready,
    };
    job.assign(&service.child)?;
    service.job = Some(job);
    // Assign before Python/bootloader can spawn descendants, so every child
    // inherits the kill-on-close job, including if desktop startup later fails.
    resume_primary_thread(service.child.id())?;
    let deadline = Instant::now() + Duration::from_secs(60);
    loop {
        if let Some(status) = service.child.try_wait()? {
            return Err(format!(
                "Bundled OCR exited during startup ({status}); check runtime DLLs and port 8766"
            )
            .into());
        }
        // The entrypoint writes this only after its own loopback socket binds.
        // A racing, unrelated HTTP responder cannot satisfy this check.
        if ready_matches(&service.ready, service.child.id(), &instance) {
            return Ok(service);
        }
        if Instant::now() >= deadline {
            return Err("Bundled OCR did not become ready within 60 seconds".into());
        }
        std::thread::sleep(Duration::from_millis(100));
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn sdk_x64_layout_and_job_cleanup() {
        assert_eq!(std::mem::size_of::<ExtendedLimits>(), 144);
        assert_eq!(std::mem::size_of::<ThreadEntry>(), 28);
        let job = Job::new().unwrap();
        let mut child = Command::new("cmd.exe")
            .args(["/C", "ping -n 60 127.0.0.1 > nul"])
            .creation_flags(0x08000004)
            .spawn()
            .unwrap();
        job.assign(&child).unwrap();
        resume_primary_thread(child.id()).unwrap();
        std::thread::sleep(Duration::from_millis(200));
        assert!(child.try_wait().unwrap().is_none());
        drop(job);
        // Closing a kill-on-close job can report exit code zero. Verify that
        // the long-running process terminates promptly, independent of code.
        let deadline = Instant::now() + Duration::from_secs(5);
        while child.try_wait().unwrap().is_none() {
            if Instant::now() >= deadline {
                let _ = child.kill();
                let _ = child.wait();
                panic!("OCR job did not terminate its child within five seconds");
            }
            std::thread::sleep(Duration::from_millis(20));
        }
    }
    #[test]
    fn readiness_rejects_other_process_and_stale_instance() {
        let path =
            std::env::temp_dir().join(format!("yomimado-ready-test-{}.json", std::process::id()));
        std::fs::write(&path, r#"{"pid":42,"instanceId":"fresh","port":8766}"#).unwrap();
        assert!(ready_matches(&path, 42, "fresh"));
        assert!(!ready_matches(&path, 41, "fresh"));
        assert!(!ready_matches(&path, 42, "old"));
        std::fs::remove_file(path).unwrap();
    }
}
