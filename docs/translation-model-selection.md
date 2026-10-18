# Choosing a translation model

In **Settings → Reading → Translation model**, choose a **Model source**.
The available sources are **Import local model** and **Ollama**. Local translation
starts unconfigured; install and select a model before using it. Browsing a source
does not activate it. **Using** names the current selection;
selecting another provider takes effect on the next translation without restarting.
OCR, tokenization and dictionary lookup remain independent of this choice.

An earlier development build offered a built-in model. That choice is removed;
its saved selection now becomes unconfigured. Existing model files are preserved
and can be imported explicitly. A source-service environment path alone does not
activate a translator. Historical component archives/APIs remain available to
release verification tools; the settings UI does not offer their download.

## Import a local model

Choose **Import local model**, browse to the model folder and choose **Import
and use model**. In the browser development preview, enter its full path instead
of using the native folder picker.

Imports currently support Japanese-to-English **Marian** models:

- macOS: a Hugging Face style folder with `config.json`,
  `tokenizer_config.json`, `vocab.json`, `source.spm`, `target.spm` and either
  `model.safetensors` or `pytorch_model.bin`. Single-file weights are supported;
  sharded weights and arbitrary Transformers model families are not.
- Windows: a parent folder containing `model/` tokenizer/config files and
  `onnx/` with `translation-encoder.onnx`, `translation-decoder.onnx`,
  `policies.json` and `export.json` in YomiMado's existing Marian export format.
  A normal Torch model folder alone does not work in the Torch-free runtime.

The model must fit within 2 GiB. Models requiring custom Python code and files
resolving outside the selected folder are rejected. The app copies recognized
files into its writable model directory, hashes them, verifies that the runtime
can load the copy, then atomically saves the selection. A failed import preserves
the previous selection. Imported content is checked again after a service restart.
Original model files and saved learning data are not deleted. Model cards and
recognized license files are retained when present; users must follow the model's
terms. No new model weights are bundled or redistributed by this feature.

For GGUF and other text model families, use Ollama with an already imported or
downloaded model. This folder importer does not create Ollama models from GGUF.

## Ollama

Install and open [Ollama](https://ollama.com/download) on the same computer. Select
**Ollama**, then **Refresh Ollama models**. Choose an installed local text model
and press **Use this model**. Choose one with Japanese language support; a model
being installed does not establish its translation quality or hardware fitness.

To download a model, enter its Ollama library name, such as `model:tag`, and press
**Download in Ollama**. Downloads may use several GB. The page shows progress and
errors; retrying resumes through Ollama. A successful download does not change the
active translator: choose the downloaded model and press **Use this model**.
Ollama manages its files; switching providers does not delete them.

The adapter connects only to `http://127.0.0.1:11434`, with system proxies disabled
and redirects rejected. It uses Ollama's [model listing](https://docs.ollama.com/api/tags),
[download](https://docs.ollama.com/api/pull) and
[chat](https://docs.ollama.com/api/chat) APIs. Cloud model names, remote aliases
reported by Ollama and models without text-generation capability are rejected.
The app checks local model metadata before sending Japanese text. This requires
a compatible Ollama version that reports model capabilities and remote aliases;
unknown capabilities are rejected. Custom registry endpoints are not supported.

Translation sends only the selected Japanese text and a Japanese-to-English
translation instruction to the local Ollama process. It sends no screenshot,
reading history or saved vocabulary. No cloud OCR or cloud translator is added.

## Persistence and cache

The service stores `preferences.json` under `YOMIMADO_TRANSLATION_RESOURCES`
(the app's `models/translation` directory in packaged builds). Managed imports
use `custom/<content-hash>/model` with sibling ONNX files where applicable.
Each request snapshots its provider before choosing its cache key. Imported
content hashes and Ollama model names/digests separate cached translations;
switching back can reuse the correct previous results.

The existing `TranslationProvider` boundary remains intact. A settings adapter
chooses an imported Marian provider or the local Ollama adapter. Without a
selection it returns setup guidance instead of falling back to a default model.
Model installation is separate from OCR and translation requests.
New setup routes retain the service's loopback/origin/desktop-header guards.

## Verification scope

Source checks cover import validation, persistence, failed-import recovery,
provider snapshots/cache separation, explicit downloads, Ollama progress/retry,
local-only requests and rejection of cloud aliases. The UI checks cover folder
selection/cancellation, import failure, saved selections and explicit Ollama
download/activation. A macOS source smoke imports the existing real Marian model,
translates a synthetic sentence and verifies cache reuse after switching away and
back. The ONNX CPU import/inference/cache path also passes on macOS; this is not
native Windows acceptance. Evidence is kept privately in
`services/ocr/build/resource-reduction-20261018/model-choice-smoke.json` and
`model-choice-smoke-onnx.json`.

Ollama is not running on the development machine: API behavior uses controlled
test responses, and the UI's missing-service guidance is checked live. Actual
Ollama model inference/download and native Windows installed acceptance remain
unverified. These are source changes; no installer or model component is published.
