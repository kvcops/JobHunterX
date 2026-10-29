# JobHunterX desktop app

JobHunterX as a normal app you install: double-click, it opens in its own window, and everything runs on your computer.
No terminal, no Python, no browser tab.

## Install

Download the installer for your system from the latest **[desktop release](https://github.com/kvcops/JobHunterX/releases/latest)**:

| System | File | Notes |
|:--|:--|:--|
| Windows 10 / 11 | `JobHunterX_…_x64-setup.exe` (or `.msi`) | Installs for your user only, no admin needed. Windows may show "Windows protected your PC" because the app isn't code-signed yet: **More info → Run anyway**. |
| macOS 11+ (Apple Silicon) | `JobHunterX_…_aarch64.dmg` | Open the `.dmg`, drag JobHunterX to Applications. First launch: right-click → **Open** (the app isn't notarized by Apple yet). |
| Linux | `.AppImage` (any distro), `.deb` (Ubuntu / Debian), `.rpm` (Fedora) | AppImage: `chmod +x` and run. |

Your settings, API keys and data live in your own app folder, not next to the app, so updates and reinstalls keep them:

* Windows: `%APPDATA%\JobHunterX`
* macOS: `~/Library/Application Support/JobHunterX`
* Linux: `~/.local/share/JobHunterX`

Auto-apply uses the Chrome or Edge already on your computer.

**Updates:** when a new version is out, the app asks once ("Install and restart"); your data stays.

## How it works

```
JobHunterX (Tauri window, system webview)
 ├─ splash page (desktop/ui) while starting
 ├─ starts backend/jobhunterx-backend  ← the Python app frozen with PyInstaller (desktop/backend)
 │     listens on 127.0.0.1 only, data in the app folder, prints "JHX_READY <url>"
 └─ shows that local page; links to other sites open in your browser, downloads go to Downloads
```

* **Why Tauri and not Electron:** the UI is plain HTML/JS served by the Python app, so it doesn't need Node or a bundled
  Chromium. Tauri uses the webview your system already has (WebView2 on Windows, WebKit on macOS / Linux): the window
  part is ~10 MB instead of ~150 MB, it has a signed auto-updater, and it makes real installers for every system.
* **Safety:** the page gets no access to the app's own system APIs (`src-tauri/capabilities/default.json` covers only
  the splash page). In desktop mode the server answers only requests addressed to `127.0.0.1` / `localhost`, so a web
  page that points its own domain at your computer (DNS rebinding) can't reach it. One copy of the app runs at a time.
* **Quitting** stops the backend; it also stops by itself if the window crashes (its stdin closes).

## Build it yourself

Needs Python 3.11, Node 22 and Rust (plus on Linux: `libwebkit2gtk-4.1-dev libgtk-3-dev libayatana-appindicator3-dev librsvg2-dev patchelf`). On Linux the AppImage step needs `LD_LIBRARY_PATH` set to the `*.libs` folders inside `src-tauri/backend` (the workflow does this).

```bash
pip install -r jobhunterx/requirements.txt pyinstaller==6.22.3
```

```bash
python desktop/scripts/build_backend.py
```

The second command freezes the backend into `desktop/src-tauri/backend/` and runs its self-test (it starts the app,
renders a resume PDF and imports the AI, browser and search parts). Then:

```bash
cd desktop && npm ci && npx tauri build
```

Installers land in `desktop/src-tauri/target/release/bundle/`. For a quick run without installers: `npx tauri dev`.

Run only the backend the way the app does (handy for debugging): `python desktop/backend/launcher.py`, or
`python desktop/backend/launcher.py --self-test`.

## Staying up to date with main (CI/CD)

`.github/workflows/desktop.yml` does this on every push to `main`:

1. merges `main` into `jobhunterx-desktop` on a staging branch (`desktop-sync`) — a conflict stops here;
2. runs the tests, freezes and self-tests the backend, and builds the installers on Windows, macOS and Linux;
3. only if **all** of that passes: moves `jobhunterx-desktop` forward and publishes a new version (`desktop-v2.0.<run>`);
4. installed apps see the new version and offer to update.

If anything fails, the desktop branch and the published app stay as they were and an issue is opened with a link to
the run. Pushes to `jobhunterx-desktop` itself are built and checked too (add `[release]` to the commit message, or
use **Run workflow → publish**, to release one).

The workflow file must also be on `main`: GitHub only runs a "push to main" workflow from main's own copy.

### One-time setup for auto-update

Updates are signed, and the app only installs updates signed with your key.

1. Make a key pair (keep the private key secret; anyone with it can ship updates to your users):

   ```bash
   cd desktop && npx tauri signer generate -w ~/.tauri/jobhunterx.key
   ```

2. In GitHub → repository **Settings → Secrets and variables → Actions**:
   * **Secret** `TAURI_SIGNING_PRIVATE_KEY`: the contents of `~/.tauri/jobhunterx.key`
   * **Secret** `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`: the password you chose (skip if none)
   * **Variable** `TAURI_UPDATER_PUBKEY`: the contents of `~/.tauri/jobhunterx.key.pub`

Without these, releases are still built and published, but apps won't update themselves (a warning shows in the run).

### Not done yet

* Code signing (Windows certificate, Apple Developer ID + notarization) — paid accounts. Until then Windows SmartScreen
  and macOS Gatekeeper ask once before the first launch.
* Intel Macs: only Apple Silicon is built (GitHub's Intel macOS runners are being retired).
* Installer size: ~120–150 MB, mostly the Python libraries (PDF engine, AI router, browser automation).
