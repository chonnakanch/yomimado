# Clean Apple Silicon Mac release test

Status: **pending**. Run this after native source clearance and signed/notarized
candidate verification. A new account on the development Mac alone does not
prove a clean machine: global runtimes, permissions and caches can persist.
Use a separate Apple Silicon Mac or fresh macOS installation/VM with working
screen capture, macOS 14+, no YomiMado, no development Python/Node/Rust, no local
models/dictionaries, and no existing app Screen Recording permission.

Supply the tester with the exact verified candidate privately, its SHA-256,
source commit and the original publisher's detector link. Do not attach an
unsigned installer or redistribute detector weights. Preserve browser download
quarantine to exercise Gatekeeper. Do not reset the developer Mac's permissions.

## Record before testing

| Field | Result |
| --- | --- |
| Tester / test date | Pending |
| Mac model / Apple chip | Pending |
| macOS version/build (`sw_vers`) | Pending |
| DMG filename / SHA-256 | Pending |
| Source commit / release version | Pending |
| Expected Developer ID team | Pending |
| App/DMG Accepted submission IDs | Pending |
| JMdict/KANJIDIC2 header refresh dates | Pending |
| Fresh installation and quarantine confirmed | Pending |

## Execute in order

- [ ] Download the signed candidate in a browser; verify its hash and retain
  quarantine. Open the DMG; drag YomiMado to `/Applications`, eject it and
  launch the installed app in Finder.
- [ ] Gatekeeper allows first launch without a damaged/unidentified-developer
  error or manual security override. UI and bundled service start without a
  development runtime. Quit/relaunch once.
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
  signed app and capture works afterward.
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
Failures block release until fixed and retested on the new candidate hash.
Return the completed record to this chat; no external tester message is sent
automatically.

## Release notes

Include macOS 14+/Apple Silicon requirements and DMG install steps; Screen
Recording grant/restart instructions; local-only screenshot OCR; separate
detector import with publisher credit/link/hash; actual dictionary refresh
dates and EDRDG/CC BY-SA attribution; known OCR/geometry/reading-order limits
and Windows unverified status; exact source commit and DMG/source/notices
download links with SHA-256 values. Resolve every placeholder before publishing.
