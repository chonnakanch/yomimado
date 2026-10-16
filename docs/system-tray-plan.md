# System tray / menu bar plan

Status: **Planned, 2026-10-17. Implementation has not started.**

Add a native macOS menu bar icon and Windows notification-area icon so the
running app is easy to find, the floating toolbar can be hidden and recovered,
and Quit remains accessible. This is a future source feature on `develop`;
it does not alter the existing 0.2.1 candidate or its acceptance evidence.

## Existing integration points

- `src-tauri/src/lib.rs` creates application state, registers shortcuts, starts
  the toolbar and owns exit cleanup. Secondary windows hide on close; toolbar
  close requests are currently prevented.
- `src-tauri/src/toolbar.rs` owns scan state, window positioning and
  `show_secondary_window`. Its `quit_app` calls `app.exit(0)`; the exit callback
  stops overlay input and the bundled OCR process, including the Windows job.
- `src-tauri/tauri.conf.json` starts the settings window hidden. The toolbar is
  shown by native setup and skips the Windows taskbar.
- Cargo.lock currently resolves Tauri 2.11.6, tray-icon 0.24.2 and muda 0.19.3.
  Presence in the lockfile alone does not establish enabled features or complete
  license/source coverage for a new build.

Paths above are relative to `apps/desktop/`.

## Proposed behavior

Keep the toolbar visible on ordinary startup. Create one application-owned tray
icon per running process, independent of React window mounts. Hiding the toolbar
is an explicit action and lasts only for the current run.

| Menu item                   | Behavior                                                                                                                                                                                                  |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Show Toolbar / Hide Toolbar | Label reflects actual toolbar visibility. Show restores, clamps to a connected display's work area, unminimizes and focuses the existing toolbar. Hide dismisses its overflow menu and hides the toolbar. |
| Saved                       | Opens the existing Saved window.                                                                                                                                                                          |
| Settings                    | Opens the existing settings view.                                                                                                                                                                         |
| Sources & licenses          | Opens the existing attribution window.                                                                                                                                                                    |
| Quit YomiMado               | Uses the existing application exit and OCR cleanup path.                                                                                                                                                  |

Use native separators between toolbar visibility, secondary windows and Quit.
The tooltip is `YomiMado`. Keep this first menu small; scan modes, rescan and
overlay controls remain in the toolbar.

Platform interaction:

- macOS: clicking the icon opens the native menu. Use a dedicated transparent
  monochrome template icon derived from the app mark, checked in light and dark
  menu bars and on Retina displays. Keep the current Dock behavior.
- Windows: left-click release shows/focuses the toolbar; right-click opens the
  native menu. Use a small transparent app icon that remains legible in light
  and dark taskbars at 100%, 125%, 150% and 200% scaling. The notification-area
  overflow may contain the icon; users can pin it through Windows.

Hiding the toolbar leaves existing OCR overlays as they are. It does not clear
results, trigger OCR, suspend the local service or unregister shortcuts. Document
this beside the toolbar visibility control. Existing keyboard shortcuts remain
available while the toolbar is hidden.

During an active selection/capture/OCR session, disable toolbar visibility and
secondary-window tray actions. Keep Quit available. Recheck the scan guard when
an action executes, because state can change after a menu opens. A Windows
left-click during capture must not reveal the toolbar into a screenshot or steal
selector focus. Refresh menu state whenever scans or toolbar visibility change.

Closing Settings, Saved or Sources keeps its existing hide-on-close behavior.
Do not introduce automatic hiding on toolbar close or intercept every app exit.
Quit from the tray, toolbar and normal OS app-quit routes must share cleanup.

## Implementation sequence

1. **Enable native tray support and prepare assets.** Enable Tauri's `tray-icon`
   feature alongside `macos-private-api`, preserving locked versions where
   possible. Add the small macOS template and Windows icon assets with a
   reproducible source. Review the actual enabled crate graph, exact licenses,
   corresponding sources and generated notices for both targets; update
   `THIRD_PARTY_LICENSES/` coverage where needed.
2. **Add `src-tauri/src/tray.rs`.** Create the icon and native menu in setup
   after application state and toolbar setup succeed. Use stable menu IDs and
   Rust callbacks. Reuse `SecondaryView` and `show_secondary_window`, and call
   the existing quit function. Dispatch asynchronous window actions without
   blocking the native event loop. Keep ownership for the application lifetime;
   create no frontend tray permissions or extra webview.
3. **Add toolbar visibility and recovery helpers.** Implement explicit show/hide
   operations in `toolbar.rs`, using live scan guards and the existing geometry
   helpers. Preserve compact/expanded layout and position on a connected display;
   use the primary display if the previous monitor is gone. Convert physical
   bounds and logical dimensions through the existing scale path. Update the
   native menu after every visibility/scan transition. Windows click-to-show
   uses the same idempotent helper as the menu.
4. **Expose Hide Toolbar from the toolbar overflow menu.** Offer this only once
   tray creation succeeds, with accessible feedback that the tray/menu bar icon
   restores it. Report action failures visibly as well as in diagnostics. If
   tray creation fails, keep the toolbar visible and usable with its existing
   Quit action; disable hiding and report the tray error. Tray failure must not
   strand an invisible running app or bypass startup-service errors.
5. **Verify and document the feature.** Add focused regression tests, run both
   native build jobs, update usage documentation and record platform evidence.
   Commit and push the focused implementation after verification. Choose the
   next version separately through the existing version/release workflow.

## Verification and acceptance

Automated checks should cover menu ID routing, visibility labels, active-scan
guards, idempotent show, tray-failure fallback and disconnected-display recovery.
Extend meaningful existing geometry tests for mixed scales and negative monitor
origins. Test the frontend Hide Toolbar action and error feedback. Avoid tests
that only repeat the menu declarations.

Run native tests, Cargo formatting and strict Clippy on the changed native code;
run relevant frontend tests, typecheck, Prettier and production build after the
overflow-menu change. Require macOS and Windows native CI builds. Native menu
appearance, OS input and actual process cleanup also need installed-app checks:

| Check      | macOS Apple Silicon                                                  | Windows 11 x64                                                      |
| ---------- | -------------------------------------------------------------------- | ------------------------------------------------------------------- |
| Launch     | One legible menu bar icon; toolbar visible                           | One legible notification-area icon; toolbar visible                 |
| Input      | Native menu opens and keyboard navigation works                      | Left-click restores; right-click menu and keyboard navigation work  |
| Recovery   | Hide/show preserves toolbar layout; recover after display disconnect | Same, including overflow area and scaled/secondary displays         |
| Busy state | Tray cannot interrupt capture; actions recover after cancel/error    | Same; no toolbar/menu captured in scan output                       |
| Windows    | Saved/settings/sources reopen correctly after close                  | Same                                                                |
| Quit       | Tray/toolbar/OS Quit exit and stop bundled OCR                       | Tray/toolbar/OS quit routes exit and terminate the service job/tree |
| Appearance | Light/dark menu bar and Retina                                       | Light/dark taskbar and 100%/125%/150%/200% scaling                  |

Verify hotkeys with the toolbar hidden, overlays remaining interactive, repeated
hide/show cycles, and quitting while OCR is active. Check for duplicate icons
after those operations and after a clean relaunch. Exercise Windows Explorer
restart recovery; if the pinned tray stack fails to restore its icon, resolve
that before calling the Windows feature complete.

Source checks establish implementation readiness only. Any future release needs
fresh installer hashes and the applicable exact-installer checks in
[desktop-release.md](desktop-release.md). Installer approval and publication
remain separate owner actions; retain all existing candidate evidence.

## Deferred scope

Login autostart, tray-only startup, hiding the macOS Dock icon, notifications,
animated/status icons, direct tray capture actions, single-instance enforcement
and persisted toolbar visibility are separate enhancements. This slice adds no
OCR, translation, dictionary or continuous-capture behavior.

## API references

Reviewed on 2026-10-17; implementation must check the locked Tauri API:

- [Tauri system tray guide](https://v2.tauri.app/learn/system-tray/): Rust feature
  setup, native menus and click callbacks.
- [Tauri 2.11.6 TrayIconBuilder](https://docs.rs/tauri/2.11.6/tauri/tray/struct.TrayIconBuilder.html):
  `icon_as_template`, `show_menu_on_left_click` and event handlers.
