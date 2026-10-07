# Windows candidate test record

Status: waiting for a verified candidate and the separate PC. Never approve this
record from automated CI alone. Each rebuilt setup needs its own confirmation.
The candidate workflow stages an owner-only GitHub draft with `SHA256SUMS.txt`
and `windows-candidate.json`. It creates no tag and has no publication operation.
Installer/source archives are never uploaded as public Actions artifacts.
GitHub blocks Actions tokens from creating a draft targeting workflow changes
relative to main. Before staging, create an **empty draft** in the owner UI with
`windows-private-test-<full candidate SHA>` and the exact candidate commit as
target; save as draft, never publish/create a tag. The workflow can upload and
verify that empty draft. No credentials belong in git, logs or test reports.

Reported hardware (2026-10-07): Intel Core i5-14500, RTX 4070 Super, Windows
version described as “25h”, one 2K display. The PC is not currently available.
This is reported hardware, not installed Windows x64 coverage. Confirm the
System type, full version/OS build, resolution and scaling when the PC is ready.
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
