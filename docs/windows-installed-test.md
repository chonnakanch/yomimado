# Windows candidate test record

Status — 2026-10-08: the maintainer reports that setup completes, but launching
opens a blank terminal, scan buttons do nothing and a capture shortcut freezes
the app. The supplied screenshot shows no detector-import panel. The human
installer gate is **FAILED / open**. The installed setup hash has not yet been
confirmed on the PC. The maintainer confirms an x64 OS/processor and full Windows
build below. Other checklist cases remain
untested. Never
approve this record from automated CI alone. Each rebuilt setup needs its own confirmation.

Candidate: `79065df7ba34a3aaa4ddb3a1ebb30e164405742a`, successful
[Windows run `37721943728`](https://github.com/chonnakanch/yomimado/actions/runs/37721943728).
Download from the [owner-only draft](https://github.com/chonnakanch/yomimado/releases/tag/untagged-e4524b4cbafe468fe44d)
while signed in with repository release access. Setup:
`YomiMado_0.1.0_x64-setup.exe` (893 MB), SHA-256:
`01a28c0f4964b2df1733814670b3024d8aa18c525b544965a50189ec25ecab0a`.
`SHA256SUMS.txt` in the same draft covers all seven other assets; its own
GitHub digest is `ac6a442053f710ee3ca146f5627dea7aaed62c0348613c5c79f059133ccfb72a`.
This candidate is retained for diagnosis and must not be approved or published.
Its source omits the Windows GUI subsystem, enables model setup only for macOS,
and creates capture windows synchronously from IPC/shortcut handlers. A
replacement fixes those paths and adds installed Windows UI regression checks;
its new installer hash needs fresh human confirmation.
It also replaces the blocking startup-error dialog with an asynchronous dialog;
CI checks occupied-port acknowledgement and the original app's responsiveness.
The installed desktop reports `NotSigned`. Earlier CI passed installed startup/quit,
CPU/native loading without Python/CUDA on PATH, OCR geometry, tokenization,
dictionary/kanji, uncached translation and persistence after restart.
Those Windows Server 2022 checks do not pass any Windows 11 hardware,
browser/SmartScreen, capture/scaling or human installer case below.

The candidate workflow stages an owner-only GitHub draft with `SHA256SUMS.txt`
and `windows-candidate.json`. It creates no tag and has no publication operation.
Installer/source archives are never uploaded as public Actions artifacts.
GitHub blocks Actions tokens from creating a draft targeting workflow changes
relative to main. Before staging, create an **empty draft** in the owner UI with
`windows-private-test-<full candidate SHA>` and the exact candidate commit as
target; save as draft, never publish/create a tag. The workflow can upload and
verify that empty draft. No credentials belong in git, logs or test reports.

Confirmed by the maintainer's System/About report (2026-10-08): **64-bit operating
system, x64-based processor**, Windows 11 Home **25H2**, OS build **26200.9457**,
Intel Core i5-14500 and 32 GB RAM. Previously reported: RTX 4070 Super and one
2K display; exact resolution and scaling remain unconfirmed. Device/product
identifiers are intentionally omitted. The PC architecture is confirmed, while
the replacement installer's functional tests remain open and the prior UI test
failed. Record resolution and scaling during retesting.
GPU acceleration is not used; a CUDA installation is not required.

Fill in: candidate commit, setup filename/SHA-256, browser, System type,
Windows version/build, CPU, display resolution/scaling/layout, existing machine
or new profile/VM. For each step, report **pass / fail / untested** and brief
observations. Use only synthetic text/images and disposable study entries.

1. Browser-download the exact candidate. In PowerShell run
   `Get-FileHash .\YomiMado_0.1.0_x64-setup.exe -Algorithm SHA256` and compare with
   its checksum file. Record SmartScreen/Defender behavior and unsigned status.
   Install per-user and launch from Start. Do not disable security protections.
   Investigate damaged/malware warnings. Record WebView2 presence and test
   missing-runtime installation only in a disposable profile/VM if available;
   missing WebView2 needs internet with the bootstrapper configuration.
2. Quit/relaunch twice. Confirm no console flashes or leftover OCR process.
   Attempt a second instance: it must show an occupied-port/startup error, not
   reuse another process. The bundled runtime must work without developer
   Python, Python PATH entries or CUDA. Record actual data folder
   `%APPDATA%\com.yomimado.desktop`; notices are in `<install>\ocr\notices`.
3. Before importing a model, verify the missing-model message. Cancel import,
   reject a wrong file, then import the original publisher's detector. Expected
   SHA-256: `1a86ace74961413cbd650002e7bb4dcec4980ffa21b2f19b86933372071d718f`.
   Relaunch and verify the imported model persists. The setup must not contain
   detector weights; importing copies your file into the writable data folder.
4. Use Ctrl+Shift+O on synthetic vertical and horizontal `学校へ` text. Check
   aligned regions, click/hover and popup placement. Verify 学校 reading/word
   meanings, 学 kanji meanings/readings and attribution. Request a new local
   sentence translation explicitly; a cached result alone is insufficient.
5. Try page scan, a saved scan area and Ctrl+Shift+S. Verify overlay visibility,
   focus, cancellation, and no leftover full-screen input-blocking selector.
6. Repeat alignment and hit-testing at 100%, 125% and 150% display scaling.
   Relaunch after changing scaling. If available test two monitors with different
   scaling, a monitor left of primary and layout changes. Otherwise mark those
   hardware cases untested; one 2K monitor does not cover them.
7. Disconnect internet after WebView2/model setup. Repeat capture, lookup and an
   **uncached** translation. Save a synthetic word/sentence; relaunch, verify
   those entries and cached translation. Reboot, then test shortcuts/capture.
8. Remove only test entries. Upgrade/reinstall using disposable test data and
   verify imported model and intended learning data survive. Uninstall and
   record whether data is retained; do not delete unrelated user data. Test
   offline setup with WebView2 already present. Report any case not exercised.

Public distribution remains blocked by the separate Windows native/source
review and this exact-installer confirmation. No macOS testing waiver transfers
to Windows. Joint publication must wait for both platforms' installer gates.
