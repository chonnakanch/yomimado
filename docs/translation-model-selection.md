# Choosing a translation model

In **Settings → Reading → Translation model**, choose a **Model source**.
The available sources are **Import local model** and **Ollama**. Local translation
starts unconfigured; install and select a model before using it. Browsing a source
does not activate it. **Using** names the current selection;
selecting another provider takes effect on the next translation without restarting.
OCR, tokenization and dictionary lookup remain independent of this choice.

## Import a local model

Choose **Import local model**, browse to the model folder and choose **Import
and use model**.

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
terms.

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

YomiMado uses Ollama on this computer at `http://127.0.0.1:11434`. Choose local
text-generation models; cloud/remote aliases and unknown capabilities are rejected.
Custom server or registry endpoints are not supported.

Translation sends only the selected Japanese text and a Japanese-to-English
translation instruction to the local Ollama process. It sends no screenshot,
reading history or saved vocabulary. The translation instruction and source text
share one user message so translation-focused models receive the task alongside
the passage, rather than a bare question to answer. Hunyuan templates also receive explicit
turn-boundary stops so a generated follow-up conversation is not included.

## Saved selection and cache

Your model choice persists across restarts. Imported model copies are checked
again when the service restarts. Switching providers keeps separate translation
caches; switching back can reuse that provider's previous results. Changing the
model does not delete original files, Ollama models or saved learning data.

Ollama cache identities include the installed model digest and translation prompt
revision. Updating the prompt can therefore recompute results without reusing
older conversational answers; existing cache rows and saved sentences remain.

The prompt follows the translation-in-user-turn pattern in the
[HY-MT guidance](https://github.com/Tencent-Hunyuan/Hy-MT#prompts) and
[HY-MT2 examples](https://huggingface.co/tencent/Hy-MT2-7B/blob/main/README.md#hy-mt2-translation-task-instruction-examples-chinese-english-comparison).
Other Ollama templates retain their own stop settings. Translation quality still
depends on the selected model and source text; isolated bubbles lack page context.
