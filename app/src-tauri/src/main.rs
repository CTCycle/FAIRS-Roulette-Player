#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{
    fs,
    net::{TcpListener, TcpStream},
    path::PathBuf,
    process::{Child, Command, Stdio},
    sync::{Arc, Mutex},
    thread,
    time::Duration,
};
use tauri::{Manager, RunEvent};

#[cfg(target_os = "windows")]
const CREATE_NO_WINDOW: u32 = 0x08000000;

fn runtime_root(app: &tauri::AppHandle) -> Result<PathBuf, String> {
    let resource = app.path().resource_dir().map_err(|e| e.to_string())?;
    let root = resource.join("runtime");
    if !root.join("python").join("python.exe").is_file() {
        return Err(format!("Missing packaged runtime: {}", root.display()));
    }
    Ok(root)
}

fn choose_port() -> Result<u16, String> {
    let listener = TcpListener::bind(("127.0.0.1", 0)).map_err(|e| e.to_string())?;
    Ok(listener.local_addr().map_err(|e| e.to_string())?.port())
}

fn wait_for_health(port: u16) -> bool {
    for _ in 0..120 {
        if let Ok(mut stream) = TcpStream::connect(("127.0.0.1", port)) {
            use std::io::{Read, Write};
            let _ = stream.write_all(
                b"GET /api/health HTTP/1.1\r\nHost: localhost\r\nConnection: close\r\n\r\n",
            );
            let mut response = String::new();
            let _ = stream.read_to_string(&mut response);
            if response.contains("\"application\":\"FAIRS\"") {
                return true;
            }
        }
        thread::sleep(Duration::from_millis(500));
    }
    false
}

fn stop_backend(child: &Arc<Mutex<Option<Child>>>) {
    if let Ok(mut child) = child.lock() {
        if let Some(process) = child.take() {
            #[cfg(target_os = "windows")]
            {
                let _ = Command::new("taskkill")
                    .args(["/PID", &process.id().to_string(), "/T", "/F"])
                    .status();
            }
            #[cfg(not(target_os = "windows"))]
            {
                let _ = process.kill();
            }
        }
    }
}

fn main() {
    let backend = Arc::new(Mutex::new(None));
    let setup_backend = backend.clone();
    let app = tauri::Builder::default()
        .setup(move |app| {
            #[cfg(not(target_os = "windows"))]
            {
                return Err("FAIRS desktop packaging supports Windows only.".into());
            }
            let root = runtime_root(app.handle())?;
            let package_root = root.parent().ok_or("Packaged runtime has no parent")?;
            let data_dir = if package_root.join("portable.flag").is_file() {
                package_root.join("data")
            } else {
                app.path().app_local_data_dir().map_err(|e| e.to_string())?
            };
            fs::create_dir_all(&data_dir).map_err(|e| e.to_string())?;
            let port = choose_port()?;
            let python = root.join("python").join("python.exe");
            let app_dir = root.join("app");
            let mut command = Command::new(python);
            command.args([
                "-m",
                "uvicorn",
                "server.app:app",
                "--app-dir",
                app_dir.to_string_lossy().as_ref(),
                "--host",
                "127.0.0.1",
                "--port",
                &port.to_string(),
            ]);
            command
                .current_dir(&root)
                .env("FAIRS_TAURI_MODE", "true")
                .env("FAIRS_USER_DATA_DIR", &data_dir)
                .env("EMBEDDED_DATABASE", "true")
                .env("ENABLE_API_DOCS", "false")
                .env("RELOAD", "false")
                .stdin(Stdio::null())
                .stdout(Stdio::null())
                .stderr(Stdio::null());
            #[cfg(target_os = "windows")]
            {
                use std::os::windows::process::CommandExt;
                command.creation_flags(CREATE_NO_WINDOW);
            }
            *setup_backend
                .lock()
                .map_err(|_| "Backend state lock poisoned")? =
                Some(command.spawn().map_err(|e| e.to_string())?);
            if !wait_for_health(port) {
                return Err("FAIRS backend failed health check.".into());
            }
            app.get_webview_window("main")
                .ok_or("Missing main window")?
                .eval(&format!(
                    "window.location.replace('http://127.0.0.1:{port}/')"
                ))
                .map_err(|e| e.to_string())?;
            Ok(())
        })
        .build(tauri::generate_context!())
        .map_err(|e| e.to_string())
        .expect("failed to build FAIRS desktop");
    app.run(move |_handle, event| {
        if matches!(event, RunEvent::Exit | RunEvent::ExitRequested { .. }) {
            stop_backend(&backend);
        }
    });
}
