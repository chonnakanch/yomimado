# Apple Silicon installed-app release test

Fresh-macOS installation test: **skipped at the maintainer's request on
2026-10-05** because no clean Mac is available. This waiver is not evidence of
successful clean-machine installation. Keep that limitation in the pre-release
notes; it does not block this first pre-release on its own.

Installed-app result: **passed for candidate `5120506`** with the fresh-macOS
waiver and untested cases below retained. Native
source/licence approval is complete. The replacement at clean commit `5120506`
passes exact mounted bundle/signature/source and frozen-service checks.
Installation, per-app Gatekeeper approval, model-import UI and permission
recovery were exercised with the maintainer's explicit authorization.

The original `042360e` DMG passed browser hash/quarantine and Finder copy, but
first launch reported **“YomiMado is damaged and can't be opened”**. Its
linker-only signature lacked `_CodeSignature/CodeResources`. That candidate
was rejected. Packaging now seals the app locally before creating the DMG;
the verifier rejects both a missing seal and altered sealed resources.

## Test record — 2026-10-06

| Field                   | Result                                                                                                       |
| ----------------------- | ------------------------------------------------------------------------------------------------------------ |
| Tester                  | Codex, with maintainer local authentication                                                                  |
| Environment             | Maintainer's existing Mac; fresh-macOS test waived                                                           |
| Mac / chip              | Mac17,3 / Apple M5                                                                                           |
| macOS version/build     | 26.6.2 / 25G83                                                                                               |
| Source commit / version | 5120506bdf5cf5fa93e2780484985473038f2195 / 0.1.0                                                             |
| Distribution            | Unnotarized hobby DMG, locally ad-hoc sealed                                                                 |
| JMdict/KANJIDIC2 dates  | 2026-09-27                                                                                                   |
| Installed location      | /Applications/YomiMado.app                                                                                   |
| Existing state          | No installed app initially; model, dictionary index, learning DBs and development permission already existed |

Candidate: `YomiMado_0.1.0_aarch64.dmg`; SHA-256:
`fbe1d788d2f80b442b2abf9c53c5439af81ea78c2bc73c584907b4791f3c1cff`.
Private path:
`apps/desktop/src-tauri/target/release/bundle/releasable/YomiMado_0.1.0_aarch64.dmg`.
Matching source: `YomiMado_0.1.0_sources_5120506.tar.gz`; SHA-256:
`0ca10a4cc5084d4778aa636e07c504db56dcf9baec87af2d37b00859803a2744`.

- **Pass:** Helium browser download has the exact candidate hash and quarantine.
  Finder Copy/Paste into Applications (Replace for the rejected test install)
  preserves quarantine. Installed strict outer/native signature verification
  passes. The DMG was ejected; installed launch/relaunch succeeds.
- **Pass:** initial launch shows Apple's expected cannot-verify warning.
  System Settings per-app Open Anyway and the final Open Anyway confirmation
  start the installed UI and bundled service. No damaged/malware warning on
  the replacement. Gatekeeper remains enabled; quarantine was not removed.
- **Pass:** detector-picker cancellation leaves the app usable. A synthetic,
  unrelated `.onnx` is rejected without replacing the existing valid model.
  Importing the original publisher's supported file succeeds; restart retains
  installed status. Both original and installed copies retain expected SHA-256
  `1a86ace74961413cbd650002e7bb4dcec4980ffa21b2f19b86933372071d718f`.
- **Not tested manually:** first-run model-absent setup, because the maintainer
  already had the detector installed. Existing model and learning data were
  preserved. Automated setup/validation tests cover absent and invalid models.
- **Pass:** capture without a matching Screen Recording grant shows a usable
  permission error; no crash or black image is claimed as an OCR result.
- **Pass with recovery:** the old development grant showed enabled but did
  not match the replacement signature. The maintainer authenticated locally;
  adding the exact installed app and Quit & Reopen alone initially retained
  the stale requirement. Narrow macOS TCC diagnostics confirmed the code
  mismatch. The YomiMado entry was subsequently refreshed in System Settings;
  the installed app opens the capture selector and returns real OCR regions.
  Other applications' grants are unchanged. No global TCC reset was performed.
- **Pass (maintainer confirmation):** Cmd+Shift+O over the synthetic Japanese
  page produces an aligned, clickable vertical `学校へ` OCR region. Desktop
  automation independently exercised selector/capture, but did not establish
  the intended synthetic crop; the precise alignment result is attributed to
  the maintainer's manual test.
- **Pass (maintainer screenshots):** the synthetic vertical `学校へ` region
  aligns with the text, and the page also has a horizontal OCR region.
  Selecting `学校` shows `がっこう` / “school” and JMdict attribution.
  Selecting `学` shows meanings, on/kun readings, example compounds and
  KANJIDIC2 attribution. The original Japanese remains visible alongside a
  cached local translation, “Go to school.” Saved words and saved sentences
  show the test word and sentence with the expected reading/meaning/translation.
  The supplied screenshots were inspected in chat; no desktop screenshot or
  unrelated personal screen contents were copied into the repository.
- **Pass (maintainer confirmation):** after disconnecting the network,
  capture/lookup works. After reboot, the installed app's shortcut works, and
  both saved test entries remain after relaunch. This confirmation supplements
  the screenshots; those images alone do not establish the OS conditions.
- **Pass (maintainer confirmation):** Scan manga page, fresh uncached
  translation and removal of the two synthetic saved test entries all work.
  Unrelated saved items were excluded from the removal test. This supplements
  the screenshots, which show the cached translation and entries before removal.
  The mounted frozen-service smoke independently verifies fresh offline
  translation and saved-item persistence.
- **Pass (files):** embedded revision/source-delivery, EDRDG/model and native
  notices match the verified candidate. Expanding Sources and licenses shows
  EDRDG/CC BY-SA, OCR/translation model credits, detector source, separate
  user-installed weights and the bundled notices location.

The approved base source revision remains `042360e`. The `5120506` source
manifest records the packaging correction and retains that approval scope;
no new human source review is claimed. Full rebuild using only the filtered
source package remains unverified.

## Execute in order

- [x] Download the source-cleared hobby candidate in a browser; verify its hash and retain
      quarantine. Open the DMG; drag YomiMado to `/Applications`, eject it and
      launch the installed app in Finder.
- [x] Record the expected Gatekeeper block for an unnotarized app. Use the
      per-app **Open Anyway** flow in System Settings → Privacy & Security, then
      launch in Finder. Do not clear quarantine or disable Gatekeeper globally.
      Investigate damaged/malware warnings. UI and bundled service start without
      a development runtime. Quit/relaunch once.
- [ ] Before detector import, capture/page scan is blocked with the setup
      instruction. Cancel the file dialog; the app stays usable. An unrelated
      `.onnx` file is rejected and remains uninstalled.
- [x] Obtain `comictextdetector.pt.onnx` from the original publisher:
      [beta-0.2.1](https://github.com/zyddnys/manga-image-translator/releases/tag/beta-0.2.1).
      Import through the app; expected SHA-256 is
      `1a86ace74961413cbd650002e7bb4dcec4980ffa21b2f19b86933372071d718f`.
      Restart; setup remains installed. Original file stays intact.
- [ ] Trigger Cmd+Shift+O without Screen Recording access. Record prompt and
      denial behavior. Denial yields a usable error, without a crash, black-image
      claimed result, or screenshot uploaded anywhere.
- [x] Grant YomiMado Screen Recording in System Settings → Privacy & Security
      → Screen Recording (wording may include system audio on newer macOS).
      Follow the requested quit/reopen flow. Permission attaches to the installed
      app and capture works afterward.
- [x] Show synthetic/user-local Japanese text; select a crop and confirm real
      vertical OCR with clickable regions aligned on Retina. Dismiss/repeat and
      try page scan. If available, also test a monitor left of the primary display.
- [x] Click `学校`, inspect reading/meaning, select `学` and inspect kanji
      readings/meanings. Dictionary attribution is visible.
- [x] Request sentence translation; Japanese remains visible. Save a word and
      sentence, quit/relaunch, verify both persist and can be removed.
- [ ] Disconnect the network after import. Relaunch and repeat OCR,
      tokenization, dictionaries and explicit translation. No model download is
      needed. Translation starts only on request.
- [x] Reboot; launch from `/Applications`, repeat shortcut/capture. Permissions
      and model setup persist. Remove/eject the DMG; the installed app works
      independently of the DMG and repository.
- [x] Inspect `/Applications/YomiMado.app/Contents/Resources/ocr/notices`;
      revision, source-delivery and EDRDG/model notices match the candidate.

Untested manual subcases: missing-model first launch (existing detector retained),
denial specifically through the shortcut (the shared capture command's button
error was observed), a left-of-primary display, and fresh uncached translation
while physically disconnected (fresh translation passes the isolated offline
frozen smoke). These are not claimed as passed. The maintainer's confirmations
clear the installed-app gate for this exact candidate; any CI rebuild with a
different DMG hash needs its own installer confirmation before publication.

Record pass/fail, errors and recovery for every step. Use synthetic text for
screenshots; never put copyrighted manga or private screen content in git.
Failures in the remaining tests block release until fixed and retested on the
new candidate hash. Retain any untested cases explicitly in the record.
Return the completed record to this chat; no external tester message is sent
automatically.

## Release notes

Include explicit unnotarized status and Apple
[Open Anyway instructions](https://support.apple.com/en-us/102445);
macOS 14+/Apple Silicon requirements and DMG install steps; Screen
Recording grant/restart instructions; local-only screenshot OCR; separate
detector import with publisher credit/link/hash; actual dictionary refresh
dates and EDRDG/CC BY-SA attribution; known OCR/geometry/reading-order limits
and Windows unverified status; exact source commit and DMG/source/notices
download links with SHA-256 values. State that installation on a fresh Mac was
not tested, and disclose any additional untested manual cases. Resolve every
placeholder before publishing.
