# Installation guide

This guide takes you from a downloaded installer to your first working scan.
The app starts its local OCR service automatically and includes its recognition
model and word/kanji dictionaries. The detector model is a separate required
download; translation is optional.

- [Install and set up](#install-and-set-up)
- [Make your first scan](#make-your-first-scan)
- [Optional translation setup](#optional-translation-setup)
- [Setup troubleshooting](#setup-troubleshooting)
- [Continue reading](usage.md)

## Install and set up

### 1. Download the app

Open [YomiMado Releases](https://github.com/chonnakanch/yomimado/releases), choose
the version you want, and expand **Assets**. Download the installer for your
computer:

| Computer   | Requirement                                 | Installer                          |
| ---------- | ------------------------------------------- | ---------------------------------- |
| Mac        | macOS 14 or later, Apple Silicon (M-series) | `YomiMado_<version>_aarch64.dmg`   |
| Windows PC | Windows 11, x64                             | `YomiMado_<version>_x64-setup.exe` |

The source archives, notices and translation ZIPs are separate release files;
only the installer is needed for this step. The detector download in step 3 is
also required before scanning. This guide uses the toolbar interface available
in v0.4.0; older releases may have different controls.

### 2. Install and launch

#### macOS

1. Open the downloaded `.dmg` in Finder.
2. Drag **YomiMado.app** into **Applications**. Wait for the copy to finish.
3. Eject the disk image and open **Applications → YomiMado**.
4. This hobby release is ad-hoc signed and unnotarized. If macOS says the developer
   cannot be verified or Apple cannot check the app, first confirm it came from
   the project's release page. To approve that app, open **System Settings →
   Privacy & Security**, find YomiMado's blocked-app notice and choose **Open
   Anyway**, then confirm **Open**. See [Apple's opening guidance](https://support.apple.com/en-us/102445).

A damaged-file or malware alert needs investigation. Keep macOS security
protections enabled; this setup uses the per-app approval flow.

**Expected result:** a small floating YomiMado toolbar appears. Continue with
step 3. Screen Recording permission is handled when you make your first scan.

#### Windows

1. Open the downloaded `_x64-setup.exe` in File Explorer.
2. The installer is unsigned. If SmartScreen shows **Windows protected your PC**,
   check that the file came from the project's release page. For a file you trust,
   use **More info → Run anyway** if offered. Managed PCs can prevent continuation;
   see [Microsoft's SmartScreen guidance](https://learn.microsoft.com/windows/apps/package-and-deploy/smartscreen-reputation).
   Keep Defender and SmartScreen enabled.
3. Follow setup for your current Windows user. Read and accept the Microsoft
   runtime-component terms if you agree; these apply to those components, while
   YomiMado and its other open-source components keep their own licences.
4. Let setup install WebView2 if it is missing. That step needs internet access;
   the bundled OCR runtime runs on the CPU.
5. Finish setup and open **YomiMado** from the Start menu.

**Expected result:** a small floating YomiMado toolbar appears. Continue with
step 3. There is no macOS-style Screen Recording permission step on Windows.

### 3. Install the required detector model

The app includes text recognition and learning dictionaries, but excludes detector
weights. The detector finds the text regions that recognition will read.

1. Open the [original detector release](https://github.com/zyddnys/manga-image-translator/releases/tag/beta-0.2.1).
2. Expand **Assets** and download **`comictextdetector.pt.onnx`**. Choose that exact
   file, rather than `comictextdetector.pt`, a source archive or another ONNX model.
   The other models listed on that upstream page are not needed for YomiMado.
3. In the YomiMado toolbar, open **More actions → Settings → Scan & OCR**.
4. Choose **Select detector model file**, then select the downloaded `.onnx` file.
5. Wait for **Installed on this computer.** The app checks the file's checksum and
   copies it into its own data directory. A rejected file leaves setup unchanged;
   download the exact supported file from the link above and try again.

YomiMado does not download this model automatically. Its import is shared by both
platforms. Restart YomiMado if you replaced a detector that was already in use.
Word and kanji dictionaries require no separate download in the packaged app.

## Make your first scan

1. Open a page with clear Japanese text in your usual manga reader or browser.
   Keep the text visible on screen.
2. Click **Selected Area** on the YomiMado toolbar and drag around one text bubble.
   The shortcut is `Cmd+Shift+O` on macOS or `Ctrl+Shift+O` on Windows.
3. **On macOS, grant capture permission if requested.** Open **System Settings →
   Privacy & Security → Screen Recording** (called **Screen & System Audio
   Recording** on newer macOS versions), enable **YomiMado**, then fully quit and
   reopen the app and repeat step 2. If the app is not listed, try the capture
   once to request access. See [Apple's screen-access instructions](https://support.apple.com/guide/mac-help/control-access-screen-system-audio-recording-mchld6aa7d23/mac).
4. Wait for recognition. The first scan can take longer while local models load;
   an OCR request has a three-minute deadline. Orange text-region outlines should
   appear over the page.
5. Click an outline, then select a Japanese word in the learning popup. Confirm
   that its reading and possible dictionary meanings appear. Dashed outlines or
   **Check OCR** indicate text to review; use **Edit OCR text** to correct it.
6. Choose **Save this word**, then open **More actions → Saved → Words** and check
   that the entry appears. Saving and translation happen only when requested.

You are ready to read when capture produces aligned text regions and selecting a
word opens its local learning information. A translation model is not required.
For a full page, choose **Whole Screen** or `Cmd/Ctrl+Shift+S`; draw a fallback
area if asked. Use **Rescan** after turning a page when the reading area stays in
place. Run a new scan if you move the page or change display scaling/layout.

## Optional translation setup

After OCR and dictionary lookup work, open **More actions → Settings → Reading**.
Choose one local translation source:

- **Ollama:** [install and run Ollama](https://ollama.com/download) on the same
  computer, return to YomiMado and select **Ollama → Refresh Ollama models**.
  Choose an installed local text model and press **Use this model**. If you use
  **Download in Ollama** first, wait for it to finish, then explicitly select the
  downloaded model and press **Use this model**.
- **Import local model:** choose a compatible Japanese-to-English Marian folder,
  then **Import and use model**. macOS accepts the supported Torch/Safetensors
  folder; Windows needs YomiMado's Marian ONNX export layout. See
  [supported files and model setup](translation-model-selection.md#import-a-local-model)
  before downloading a model. GGUF files use Ollama rather than this importer.

The **Using** line confirms the active model. Return to a recognized region and
choose **Translate locally**. There is no built-in model selection or automatic
translation. Downloads can require several GB; model availability does not guarantee
translation quality or suitability for your hardware. The
[translation guide](translation-model-selection.md) covers the supported formats,
provider switching and troubleshooting in more detail.

## Setup troubleshooting

| What you see                                        | What to do                                                                                                                                                                                          |
| --------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Detector required before scanning                   | Finish step 3 and confirm **Installed on this computer.**                                                                                                                                           |
| Selected file does not match the supported detector | Download `comictextdetector.pt.onnx` from the exact release linked in step 3; renaming a different model will not work.                                                                             |
| macOS capture permission error                      | Enable YomiMado's screen-recording access, fully quit/reopen it and scan again.                                                                                                                     |
| Toolbar disappeared                                 | Restore it from YomiMado's macOS menu bar icon or Windows notification-area icon; check Windows' icon overflow.                                                                                     |
| No translation model installed                      | OCR and dictionary lookup still work. Complete the optional translation setup to translate sentences.                                                                                               |
| Ollama unavailable                                  | Open Ollama on this computer, then choose **Refresh Ollama models** in Reading settings.                                                                                                            |
| OCR service/startup error                           | Quit YomiMado through **More actions → Quit YomiMado**, reopen it and retry. For a packaged app, the service should start automatically. Report the app version, OS and exact error if it persists. |
| OCR text is wrong or no region appears              | Try a tight selection around larger, clearly visible text; check detector setup. Correct detected text with **Edit OCR text**. OCR accuracy varies with the page.                                   |

After setup, use the [reading guide](usage.md) for toolbar controls, keyboard
reading, word/kanji lookup and Saved collections.
