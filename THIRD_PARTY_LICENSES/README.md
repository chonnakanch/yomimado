# Third-party notices

This initial prototype uses the following direct runtime dependencies:

- Tauri 2.11.6 and `tauri-plugin-global-shortcut` 2.3.2 — Apache-2.0 OR MIT
- xcap 0.8.3 — Apache-2.0
- React 19.3.0 — MIT

Development tooling also includes Vite 7.3.6 (MIT) and the Tauri CLI
(Apache-2.0 OR MIT). Before shipping a bundled application, this directory must
be expanded with the resolved dependency notices and full required license text.
OCR models, OCR datasets, and Japanese dictionary data are deliberately not
included in this milestone and require separate license review before addition.

Optional, user-installed OCR components: comic-text-detector's source repository
is GPL-3.0; Manga OCR 0.1.16 software and the `kha-white/manga-ocr-base`
model card state Apache-2.0. The detector model weights are not bundled here;
review their terms separately before distributing them.
