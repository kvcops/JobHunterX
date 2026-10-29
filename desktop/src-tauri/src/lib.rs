//! JobHunterX desktop shell.
//!
//! Shows a splash page, starts the bundled Python backend (`resources/backend/jobhunterx-backend`), waits for it to
//! print `JHX_READY <url>`, then points the window at that local address. The page served on 127.0.0.1 gets no access
//! to the app's own APIs; links to other sites open in the normal browser and downloads go to the Downloads folder.
//! Quitting the window stops the backend (it also stops by itself when its stdin closes).

use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::Duration;

use tauri::webview::{DownloadEvent, NewWindowResponse};
use tauri::{AppHandle, Manager, RunEvent, Url, WebviewUrl, WebviewWindow, WebviewWindowBuilder};
use tauri_plugin_opener::OpenerExt;

const READY: &str = "JHX_READY ";
const START_TIMEOUT: Duration = Duration::from_secs(120);

/// The running backend, so it can be stopped on quit (and before an update replaces its files).
struct Backend(Mutex<Option<Child>>);

fn backend_exe(app: &AppHandle) -> Result<PathBuf, String> {
    let name = if cfg!(windows) { "jobhunterx-backend.exe" } else { "jobhunterx-backend" };
    let dir = app.path().resource_dir().map_err(|e| e.to_string())?;
    let exe = dir.join("backend").join(name);
    if exe.exists() {
        Ok(exe)
    } else {
        Err(format!("The app's backend is missing ({}). Reinstall JobHunterX.", exe.display()))
    }
}

fn log_file(app: &AppHandle) -> PathBuf {
    let dir = app.path().app_log_dir().unwrap_or_else(|_| std::env::temp_dir());
    let _ = std::fs::create_dir_all(&dir);
    dir.join("backend.log")
}

fn is_local(url: &Url) -> bool {
    matches!(url.scheme(), "tauri" | "asset")
        || matches!(url.host_str(), Some("127.0.0.1") | Some("localhost") | Some("tauri.localhost"))
}

fn open_outside(app: &AppHandle, url: &Url) {
    if matches!(url.scheme(), "http" | "https" | "mailto") {
        let _ = app.opener().open_url(url.as_str(), None::<&str>);
    }
}

/// A free path in the Downloads folder for this file name ("Resume.pdf", "Resume (1).pdf", …).
fn download_target(app: &AppHandle, suggested: &Path, url: &Url) -> PathBuf {
    let dir = app.path().download_dir().unwrap_or_else(|_| std::env::temp_dir());
    let name = suggested
        .file_name()
        .map(|n| n.to_string_lossy().to_string())
        .filter(|n| !n.is_empty())
        .or_else(|| url.path_segments().and_then(|s| s.last().map(str::to_string)).filter(|n| !n.is_empty()))
        .unwrap_or_else(|| "download".to_string());
    let (stem, ext) = match name.rsplit_once('.') {
        Some((s, e)) if !s.is_empty() => (s.to_string(), format!(".{e}")),
        _ => (name.clone(), String::new()),
    };
    let mut path = dir.join(&name);
    let mut n = 1;
    while path.exists() {
        path = dir.join(format!("{stem} ({n}){ext}"));
        n += 1;
    }
    path
}

fn show_error(window: &WebviewWindow, message: &str, log: &Path) {
    let js = format!(
        "window.jhxError && window.jhxError({}, {})",
        serde_json::to_string(message).unwrap_or_default(),
        serde_json::to_string(&log.display().to_string()).unwrap_or_default()
    );
    // the splash page may still be loading (e.g. the backend is missing and this runs at once): repeat for a few seconds
    let window = window.clone();
    std::thread::spawn(move || {
        for _ in 0..12 {
            let _ = window.eval(&js);
            std::thread::sleep(Duration::from_millis(500));
        }
    });
}

fn main_window(app: &AppHandle) -> tauri::Result<WebviewWindow> {
    let nav_app = app.clone();
    let new_app = app.clone();
    let dl_app = app.clone();
    WebviewWindowBuilder::new(app, "main", WebviewUrl::App("index.html".into()))
        .title("JobHunterX")
        .inner_size(1360.0, 880.0)
        .min_inner_size(900.0, 600.0)
        .center()
        .on_navigation(move |url| {
            if is_local(url) {
                return true;
            }
            open_outside(&nav_app, url);
            false
        })
        .on_new_window(move |url, _features| {
            // target="_blank" links (job postings, company sites): the user's own browser
            open_outside(&new_app, &url);
            NewWindowResponse::Deny
        })
        .on_download(move |_webview, event| {
            match event {
                DownloadEvent::Requested { url, destination } => {
                    *destination = download_target(&dl_app, destination, &url);
                }
                DownloadEvent::Finished { path, success, .. } => {
                    if let (true, Some(p)) = (success, path) {
                        let _ = dl_app.opener().reveal_item_in_dir(p);
                    }
                }
                _ => {}
            }
            true
        })
        .build()
}

fn start_backend(app: AppHandle, window: WebviewWindow) {
    let log = log_file(&app);
    let exe = match backend_exe(&app) {
        Ok(exe) => exe,
        Err(msg) => return show_error(&window, &msg, &log),
    };
    let err_file = std::fs::File::create(&log).ok();
    let mut cmd = Command::new(&exe);
    cmd.stdin(Stdio::piped()).stdout(Stdio::piped());
    match err_file.as_ref().and_then(|f| f.try_clone().ok()) {
        Some(f) => cmd.stderr(Stdio::from(f)),
        None => cmd.stderr(Stdio::null()),
    };
    if let Some(dir) = exe.parent() {
        cmd.current_dir(dir);
    }
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x0800_0000); // CREATE_NO_WINDOW: no console window next to the app
    }
    let mut child = match cmd.spawn() {
        Ok(child) => child,
        Err(e) => return show_error(&window, &format!("Couldn't start the backend: {e}"), &log),
    };
    let stdout = child.stdout.take();
    app.state::<Backend>().0.lock().unwrap().replace(child);

    let (tx, rx) = std::sync::mpsc::channel::<Result<Url, String>>();
    let mut out_log = err_file;
    std::thread::spawn(move || {
        let Some(stdout) = stdout else { return };
        let mut sent = false;
        for line in BufReader::new(stdout).lines().map_while(Result::ok) {
            if let Some(f) = out_log.as_mut() {
                let _ = writeln!(f, "{line}");
            }
            if !sent {
                if let Some(rest) = line.strip_prefix(READY) {
                    sent = true;
                    let _ = tx.send(Url::parse(rest.trim()).map_err(|e| e.to_string()));
                }
            }
        }
        if !sent {
            let _ = tx.send(Err("The backend stopped while starting.".into()));
        }
    });

    std::thread::spawn(move || match rx.recv_timeout(START_TIMEOUT) {
        Ok(Ok(url)) if is_local(&url) => {
            let _ = window.navigate(url);
            #[cfg(feature = "updater")]
            updates::check_later(app.clone());
        }
        Ok(Ok(url)) => show_error(&window, &format!("Unexpected backend address: {url}"), &log),
        Ok(Err(msg)) => show_error(&window, &msg, &log),
        Err(_) => show_error(&window, "The backend took too long to start.", &log),
    });
}

pub fn stop_backend(app: &AppHandle) {
    if let Some(mut child) = app.state::<Backend>().0.lock().unwrap().take() {
        drop(child.stdin.take()); // the backend exits when its stdin closes …
        for _ in 0..30 {
            if matches!(child.try_wait(), Ok(Some(_))) {
                return;
            }
            std::thread::sleep(Duration::from_millis(100));
        }
        let _ = child.kill(); // … or is stopped after 3 seconds
        let _ = child.wait();
    }
}

#[cfg(feature = "updater")]
mod updates {
    //! New versions come from the project's GitHub releases (signed; the public key is set at build time).
    use tauri::AppHandle;
    use tauri_plugin_dialog::{DialogExt, MessageDialogButtons};
    use tauri_plugin_updater::UpdaterExt;

    pub fn check_later(app: AppHandle) {
        tauri::async_runtime::spawn(async move {
            tokio_sleep(20).await; // let the app settle first
            let Ok(updater) = app.updater() else { return };
            let Ok(Some(update)) = updater.check().await else { return };
            let notes = update.body.clone().unwrap_or_default();
            let ask = format!(
                "JobHunterX {} is available (you have {}).\n\n{}\n\nInstall it now? The app restarts; your data stays.",
                update.version,
                update.current_version,
                notes.chars().take(600).collect::<String>()
            );
            let handle = app.clone();
            let yes = tauri::async_runtime::spawn_blocking(move || {
                handle
                    .dialog()
                    .message(ask)
                    .title("Update available")
                    .buttons(MessageDialogButtons::OkCancelCustom("Install and restart".into(), "Later".into()))
                    .blocking_show()
            })
            .await
            .unwrap_or(false);
            if !yes {
                return;
            }
            let Ok(bytes) = update.download(|_, _| {}, || {}).await else { return };
            super::stop_backend(&app); // its files are replaced by the installer
            if update.install(bytes).is_ok() {
                app.restart();
            }
        });
    }

    async fn tokio_sleep(secs: u64) {
        let (tx, rx) = std::sync::mpsc::channel::<()>();
        std::thread::spawn(move || {
            std::thread::sleep(std::time::Duration::from_secs(secs));
            let _ = tx.send(());
        });
        let _ = tauri::async_runtime::spawn_blocking(move || rx.recv()).await;
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    #[cfg_attr(not(feature = "updater"), allow(unused_mut))]
    let mut builder = tauri::Builder::default()
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            // a second launch just brings this window forward (two backends must not share one database)
            if let Some(w) = app.get_webview_window("main") {
                let _ = w.unminimize();
                let _ = w.show();
                let _ = w.set_focus();
            }
        }))
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init());
    #[cfg(feature = "updater")]
    {
        builder = builder.plugin(tauri_plugin_updater::Builder::new().build());
    }
    builder
        .manage(Backend(Mutex::new(None)))
        .setup(|app| {
            let window = main_window(app.handle())?;
            start_backend(app.handle().clone(), window);
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building JobHunterX")
        .run(|app, event| {
            if let RunEvent::Exit = event {
                stop_backend(app);
            }
        });
}
