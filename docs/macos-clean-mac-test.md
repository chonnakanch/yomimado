# Apple Silicon installed-app release test

Fresh-macOS installation test: **skipped at the maintainer's request on
2026-10-05** because no clean Mac is available. This waiver is not evidence of
successful clean-machine installation. Keep that limitation in the pre-release
notes; it does not block this first pre-release on its own.

Remaining installed-app tests: **pending**. Run these on the existing Apple
Silicon Mac after native source clearance and unnotarized hobby candidate
verification. Record existing app data, model setup and Screen Recording
permission before testing. Preserve existing learning data. A separate local
test account can isolate app data if practical, but does not prove a clean
machine: global runtimes, permissions and caches can persist. Mark any step
that cannot be exercised as not tested, with its reason; never infer a pass
from an existing model or permission grant.

Supply the tester with the exact verified candidate privately, its SHA-256,
source commit and the original publisher's detector link. Do not substitute a private build or redistribute detector weights. Preserve browser download
quarantine to exercise Gatekeeper. Do not reset the developer Mac's permissions.

## Record before testing

| Field                                 | Result                                              |
| ------------------------------------- | --------------------------------------------------- |
| Tester / test date                    | Pending                                             |
| Mac model / Apple chip                | Pending                                             |
| macOS version/build (`sw_vers`)       | Pending                                             |
| DMG filename / SHA-256                | Pending                                             |
| Source commit / release version       | Pending                                             |
| Distribution                          | Unnotarized hobby DMG; no Developer ID/notarization |
| JMdict/KANJIDIC2 header refresh dates | Pending                                             |
| Fresh macOS installation              | Skipped by maintainer, 2026-10-05; unavailable      |
| Download quarantine confirmed         | Pending                                             |
| Existing app/model/permission state   | Pending                                             |

## Execute in order

- [ ] Download the source-cleared hobby candidate in a browser; verify its hash and retain
      quarantine. Open the DMG; drag YomiMado to `/Applications`, eject it and
      launch the installed app in Finder.
- [ ] Record the expected Gatekeeper block for an unnotarized app. Use the
      per-app **Open Anyway** flow in System Settings → Privacy & Security, then
      launch in Finder. Do not clear quarantine or disable Gatekeeper globally.
      Investigate damaged/malware warnings. UI and bundled service start without
      a development runtime. Quit/relaunch once.
- [ ] Before detector import, capture/page scan is blocked with the setup
      instruction. Cancel the file dialog; the app stays usable. An unrelated
      `.onnx` file is rejected and remains uninstalled.
- [ ] Obtain `comictextdetector.pt.onnx` from the original publisher:
      [beta-0.2.1](https://github.com/zyddnys/manga-image-translator/releases/tag/beta-0.2.1).
      Import through the app; expected SHA-256 is
      `1a86ace74961413cbd650002e7bb4dcec4980ffa21b2f19b86933372071d718f`.
      Restart; setup remains installed. Original file stays intact.
- [ ] Trigger Cmd+Shift+O without Screen Recording access. Record prompt and
      denial behavior. Denial yields a usable error, without a crash, black-image
      claimed result, or screenshot uploaded anywhere.
- [ ] Grant YomiMado Screen Recording in System Settings → Privacy & Security
      → Screen Recording (wording may include system audio on newer macOS).
      Follow the requested quit/reopen flow. Permission attaches to the installed
      app and capture works afterward.
- [ ] Show synthetic/user-local Japanese text; select a crop and confirm real
      vertical OCR with clickable regions aligned on Retina. Dismiss/repeat and
      try page scan. If available, also test a monitor left of the primary display.
- [ ] Click `学校`, inspect reading/meaning, select `学` and inspect kanji
      readings/meanings. Dictionary attribution is visible.
- [ ] Request sentence translation; Japanese remains visible. Save a word and
      sentence, quit/relaunch, verify both persist and can be removed.
- [ ] Disconnect the network after import. Relaunch and repeat OCR,
      tokenization, dictionaries and explicit translation. No model download is
      needed. Translation starts only on request.
- [ ] Reboot; launch from `/Applications`, repeat shortcut/capture. Permissions
      and model setup persist. Remove/eject the DMG; the installed app works
      independently of the DMG and repository.
- [ ] Inspect `/Applications/YomiMado.app/Contents/Resources/ocr/notices`;
      revision, source-delivery and EDRDG/model notices match the candidate.

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
