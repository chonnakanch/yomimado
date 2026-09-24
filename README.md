# YomiMado (読み窓)

YomiMado is a local-first desktop assistant for reading Japanese manga already
visible on screen. It preserves the original image and adds an interactive OCR
overlay rather than replacing text.

## Current milestone

The initial capture-to-overlay slice is implemented:

1. Press `Cmd+Shift+O` on macOS or `Ctrl+Shift+O` on Windows (or use **Select
   screen region** in the main window).
2. Drag a rectangular selection on the current display.
3. The Rust capture layer saves a PNG crop locally and returns scaling metadata.
4. The app calls the local OCR service and shows its geometry in a transparent
   overlay. Without local models, the service shows a dashed **demo boundary**
   around the selected area. This is a coordinate check, not recognized text.
5. Click a recognized region to open a Japanese → English popup. Edit the OCR
   text if needed, then press **Translate locally**. Translation never starts
   merely because OCR detected a region. In demo mode, enter Japanese text
   manually; the demo boundary contains no recognized text.

## Development

Start the OCR service in one terminal (Python 3.9+):

```sh
cd services/ocr
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --reload --port 8765
```

Start the desktop app in another terminal:

```sh
cd apps/desktop
npm install
npm run tauri dev
```

macOS requires Screen Recording permission. If macOS prompts during the first
capture, enable YomiMado in **System Settings → Privacy & Security → Screen &
System Audio Recording**, then restart the app. When running `tauri dev`, macOS
may list the terminal application instead. Without this permission, macOS can
return a screenshot containing only the desktop background instead of the
visible windows. The placeholder OCR endpoint does not download models or send
images over the network.

## Local OCR models (optional)

The service supports a user-local checkout of
[comic-text-detector](https://github.com/dmMaze/comic-text-detector) and a local
[Manga OCR](https://github.com/kha-white/manga-ocr) model directory. These are
not bundled or downloaded by YomiMado. Install the detector checkout's own
requirements and then install `manga-ocr==0.1.16` with
`pip install -e '.[ocr]'` from `services/ocr`. Set these paths before starting
Uvicorn:

```sh
export YOMIMADO_DETECTOR_REPO=/absolute/path/to/comic-text-detector
export YOMIMADO_DETECTOR_MODEL=/absolute/path/to/comictextdetector.pt.onnx
export YOMIMADO_MANGA_OCR_MODEL=/absolute/path/to/manga-ocr-base
```

The first request loads both models and may take time. The detector supplies
geometry and orientation; Manga OCR recognizes each detected crop. The model
API does not provide a calibrated recognition confidence, so the response uses
`0` to indicate that confidence is unknown. Keep the checkout and weights
outside this repository until their distribution terms are reviewed.

## Local translation model (optional)

The on-demand popup can translate Japanese text to English with the free,
user-installed [Helsinki-NLP/opus-mt-ja-en](https://huggingface.co/Helsinki-NLP/opus-mt-ja-en)
model. This is a baseline model, not a manga-specific or contextual translator.
Neither model weights nor Japanese text are sent to a cloud translation service
at runtime. No model is downloaded by YomiMado itself.

Install the optional Python dependencies in the OCR service environment and
download the model to the git-ignored local model directory:

```sh
cd services/ocr
pip install -e '.[dev,translation]'
hf download Helsinki-NLP/opus-mt-ja-en --local-dir ./local-models/opus-mt-ja-en
export YOMIMADO_TRANSLATION_MODEL="$PWD/local-models/opus-mt-ja-en"
uvicorn app.main:app --reload --port 8765
```

The popup reports a setup error until the model and optional dependencies are
available. Successful translations are cached locally in
`~/.cache/yomimado/translation.sqlite3` (override with
`YOMIMADO_TRANSLATION_CACHE`). Only the selected Japanese text is sent from
the desktop window to this loopback service; screenshots are not submitted for
translation. The service accepts browser requests only from the Tauri app and
the development frontend origins.
