use std::io::{BufRead, BufReader};
use std::path::PathBuf;
use std::process::{Child, Command, Stdio};
use std::sync::{Arc, Mutex};
use std::thread;
use tauri::{AppHandle, Manager, RunEvent};

fn kill_child(child_lock: &Arc<Mutex<Option<Child>>>) {
    if let Ok(mut lock) = child_lock.lock() {
        if let Some(mut child) = lock.take() {
            log::info!("[Tauri] Terminating backend child process (PID: {})...", child.id());
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

fn resolve_backend_command(app: &AppHandle) -> Option<Command> {
    // 0. Explicit override via environment variable
    if let Ok(custom_bin) = std::env::var("SATELLITE_BACKEND_BIN") {
        let p = PathBuf::from(custom_bin);
        if p.exists() {
            log::info!("[Tauri] Using backend binary from SATELLITE_BACKEND_BIN: {:?}", p);
            return Some(Command::new(p));
        }
    }

    // 1. Linux AppImage environment
    if let Ok(appdir) = std::env::var("APPDIR") {
        let p = PathBuf::from(appdir).join("usr/bin/sattrack-backend");
        if p.exists() {
            log::info!("[Tauri] Found backend in AppImage: {:?}", p);
            return Some(Command::new(p));
        }
    }

    // 2. Check bundled binary in resource directory or current exe directory
    if let Ok(current_exe) = std::env::current_exe() {
        if let Some(parent) = current_exe.parent() {
            let candidates = [
                parent.join("sattrack-backend"),
                parent.join("sattrack-backend.exe"),
                parent.join("binaries").join("sattrack-backend"),
                parent.join("binaries").join("sattrack-backend.exe"),
            ];
            for candidate in &candidates {
                if candidate.exists() {
                    log::info!("[Tauri] Found backend relative to current exe: {:?}", candidate);
                    return Some(Command::new(candidate));
                }
            }
        }
    }

    if let Ok(resource_dir) = app.path().resource_dir() {
        let candidates = [
            resource_dir.join("binaries").join("sattrack-backend"),
            resource_dir.join("binaries").join("sattrack-backend.exe"),
            resource_dir.join("sattrack-backend"),
            resource_dir.join("sattrack-backend.exe"),
        ];
        for candidate in &candidates {
            if candidate.exists() {
                log::info!("[Tauri] Found backend in resource_dir: {:?}", candidate);
                return Some(Command::new(candidate));
            }
        }
    }

    // 3. Check dist/ directory from workspace root
    let dist_candidates = [
        PathBuf::from("dist/sattrack-backend"),
        PathBuf::from("dist/sattrack-backend.exe"),
        PathBuf::from("../dist/sattrack-backend"),
        PathBuf::from("../dist/sattrack-backend.exe"),
    ];
    for candidate in &dist_candidates {
        if candidate.exists() {
            log::info!("[Tauri] Found backend in dist: {:?}", candidate);
            return Some(Command::new(candidate));
        }
    }

    // 4. Check src-tauri/binaries/
    let binary_dirs = [
        PathBuf::from("src-tauri/binaries"),
        PathBuf::from("binaries"),
        PathBuf::from("../src-tauri/binaries"),
    ];
    for binary_dir in &binary_dirs {
        if binary_dir.exists() {
            if let Ok(entries) = std::fs::read_dir(binary_dir) {
                for entry in entries.flatten() {
                    let path = entry.path();
                    if let Some(name) = path.file_name().and_then(|n| n.to_str()) {
                        if name.starts_with("sattrack-backend") && !name.ends_with(".log") {
                            log::info!("[Tauri] Found backend in binaries dir: {:?}", path);
                            return Some(Command::new(path));
                        }
                    }
                }
            }
        }
    }

    // 5. Development environment: run python desktop_entry.py if present
    for dev_dir in &[PathBuf::from("."), PathBuf::from("..")] {
        let dev_script = dev_dir.join("desktop_entry.py");
        if dev_script.exists() {
            let venv_python = dev_dir.join("venv/bin/python3");
            let venv_python_win = dev_dir.join("venv/Scripts/python.exe");
            let python_cmd = if venv_python.exists() {
                venv_python
            } else if venv_python_win.exists() {
                venv_python_win
            } else {
                PathBuf::from("python3")
            };
            log::info!("[Tauri] Running development script: {:?} via {:?}", dev_script, python_cmd);
            let mut cmd = Command::new(python_cmd);
            cmd.arg(&dev_script);
            return Some(cmd);
        }
    }

    None
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let child_arc: Arc<Mutex<Option<Child>>> = Arc::new(Mutex::new(None));
    let child_clone_for_setup = child_arc.clone();
    let child_clone_for_exit = child_arc.clone();

    tauri::Builder::default()
        .setup(move |app| {
            if cfg!(debug_assertions) {
                let _ = app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                );
            }

            #[cfg(not(mobile))]
            {
                let app_handle = app.handle().clone();
                let child_storage = child_clone_for_setup.clone();

                thread::spawn(move || {
                    let mut cmd = match resolve_backend_command(&app_handle) {
                        Some(c) => c,
                        None => {
                            log::error!("[Tauri] Could not locate backend executable or desktop_entry.py!");
                            return;
                        }
                    };

                    cmd.stdout(Stdio::piped());
                    cmd.stderr(Stdio::inherit());

                    match cmd.spawn() {
                        Ok(mut child) => {
                            let stdout = child.stdout.take();
                            if let Ok(mut lock) = child_storage.lock() {
                                *lock = Some(child);
                            }

                            if let Some(out) = stdout {
                                let reader = BufReader::new(out);
                                for line in reader.lines().flatten() {
                                    log::info!("[Backend Out] {}", line);
                                    if line.starts_with("READY:") {
                                        if let Some(port_str) = line.strip_prefix("READY:") {
                                            if let Ok(port) = port_str.trim().parse::<u16>() {
                                                log::info!("[Tauri] Backend ready on port {}. Navigating main window...", port);
                                                let url_str = format!("http://127.0.0.1:{}/", port);
                                                if let Ok(url) = url_str.parse::<tauri::Url>() {
                                                    // Try navigating the window, with retry loop if window is initializing
                                                    for _ in 0..20 {
                                                        if let Some(window) = app_handle.get_webview_window("main") {
                                                            let _ = window.navigate(url);
                                                            break;
                                                        }
                                                        thread::sleep(std::time::Duration::from_millis(100));
                                                    }
                                                }
                                                break;
                                            }
                                        }
                                    }
                                }
                            }
                        }
                        Err(e) => {
                            log::error!("[Tauri] Failed to spawn backend process: {}", e);
                        }
                    }
                });
            }

            #[cfg(mobile)]
            {
                log::info!("[Tauri Mobile] Running mobile application with local SGP4 orbit engine and optional remote AI.");
            }

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(move |_app_handle, event| {
            if let RunEvent::ExitRequested { .. } = event {
                kill_child(&child_clone_for_exit);
            }
        });
}
