# OCR resource reduction and optional translation — 2026-10-18

The source app now decodes OCR output without UniDic/Fugashi and installs the
local translation model only when the user requests its download. Lindera,
JMdict, KANJIDIC2, OCR model weights and screen-coordinate behavior stay intact.
This implements priorities 1 and 2 after the [Lindera migration](lindera-migration.md).

## OCR decode-only adapter

[`load_ocr_tokenizer`](../services/ocr/app/pipeline/ocr_tokenizer.py) preserves the
model vocabulary, special tokens and output cleanup, using the pinned Japanese
tokenizer with `do_word_tokenize=False` and `word_tokenizer_type="basic"`.
The second setting also preserves serialization behavior. It applies only to
generated OCR IDs; the Marian translation tokenizer still encodes Japanese text
normally. Original model files are not edited.

Manga OCR constructs its tokenizer internally. Its constructor reference is
overridden only during recognizer construction and restored in `finally`.
Transformers' global loader and translation construction are untouched. The
Windows ONNX recognizer uses the same helper directly. Both freezer recipes
exclude UniDic, Fugashi and MeCab, strip unused dictionary metadata copied by
third-party hooks, and reject retained dictionaries/bindings in resource checks.

macOS's upstream Manga OCR package still declares those packages as installation
dependencies, so they remain in its build/development environment and locked
source/notice collection. They are excluded from the frozen inference runtime.
The Windows ONNX environment also omits them from its selected runtime packages.
The earlier [decode-parity experiment](tokenizer-resource-investigation.md)
records 12,804 matching cases and ten synthetic recognitions.

## Optional local translation

In **Settings → Reading → Local translation**, the user chooses **Download local
translation**. Opening settings, scanning, selecting text and asking for a missing
model never start a download. The UI shows the pinned download size, progress,
ready state and retry guidance. Translation remains a separate explicit action
and runs offline after installation. Screenshots and Japanese text are never
included in download requests.

If the local service cannot be reached, setup stops checking and offers **Try
again** with guidance to quit and reopen the installed app. A lost connection
during progress polling also permits reconnecting; setup never starts a second
download merely to retry a status check. Once ready, the card explains the next
step: scan text, click a detected region, then choose **Translate locally**.

The local API adds:

| Endpoint                                 | Behavior                                                              |
| ---------------------------------------- | --------------------------------------------------------------------- |
| `GET /api/v1/translation-model`          | Read status; no network or model inference                            |
| `POST /api/v1/translation-model/install` | Start one background download; repeated requests share the active job |

These routes use the existing loopback Host, origin, desktop-header and request
size guards. Download URLs and hashes come from the packaged descriptor, with
HTTPS restricted to this project's GitHub release and its asset redirects. The
client cannot supply an arbitrary URL or destination.

Archives and individual files have SHA-256 and size pins. Unexpected members,
duplicates, links, traversal, oversized responses and changed bytes fail
verification. Files are staged privately before the model directory is renamed
into place. Failed or interrupted downloads are not live installations. An
explicit retry can repair corrupt managed model data after verifying the new
download; saved words, sentences and translation-cache databases are separate.
An OS-released download lock permits cleanup of abandoned model staging files
after interruption, without deleting an active download from another service.

Native launchers supply `YOMIMADO_TRANSLATION_MANIFEST` and
`YOMIMADO_TRANSLATION_RESOURCES`. Models live under the app's writable data
directory, `models/translation/<content-id>/model`, with ONNX graphs alongside
under `onnx/`. Verified data survives app restarts and is reused while the content
identity matches. The source-service `YOMIMADO_TRANSLATION_MODEL` override still
works for an existing local model. No app restart is required after installation.

## Packaging and release delivery

[`translation_component.py`](../scripts/translation_component.py) checks original
model pins, creates a versioned archive outside installer resources, retains the
model card/Apache-2.0 licence and embeds `notices/translation-component.json` in
the installer. macOS downloads the original Torch model; Windows downloads the
existing exported CPU ONNX translation graphs and tokenizer data, keeping Torch
out of its inference runtime. OCR graph verification does not require optional
translation graphs. Export provenance and model pins remain enforced even when
the optional files are absent.

Future releases using this layout publish eight files: the previous six plus
`YomiMado_<version>_translation_torch.zip` and
`YomiMado_<version>_translation_onnx.zip`. Both platform candidates, combined
candidate and checksums bind the exact ZIP bytes. Components remain separate
downloads, outside source/notices wrapper archives. Historical six-file and
original legacy records remain readable with their original layout rules.
The published component names must match the embedded descriptors before users
can download them; an unpublished private candidate can test the same archives
offline via `YOMIMADO_SMOKE_TRANSLATION_ARCHIVE`.

Both exact-candidate smoke scripts first check that translation is absent while
OCR/learning work, then verify and install the local component, translate, and
check persistence/cache after restarting the service. Component downloads do not
bypass source/notice review, exact-installer acceptance or publication approval.
The macOS seed predates these changes and its reuse guard remains enforced.

## Local verification

- 127 service tests, 180 frontend tests, 259 packaging/release-tool tests and
  70 Rust tests pass; frontend build, release-mode native compilation and lint
  checks pass.
- A private frozen macOS service has no UniDic/Fugashi modules or dictionary
  resources. All nine synthetic scans match the previous complete text, polygon,
  orientation and review metadata, including the blank fixture. Lindera spans,
  100 concurrent analysis requests, JMdict and KANJIDIC2 pass.
- The frozen service returns a setup error before optional translation is
  installed, becomes ready after verifying the component, and translates locally.
- A separate ONNX CPU source process on macOS passes horizontal/vertical OCR and
  three translations with actual Torch, Manga OCR, UniDic and Fugashi imports
  blocked and their package metadata absent. Recognition runs with translation
  graphs absent; translation then loads only from the installed component.

Private evidence is under ignored
`services/ocr/build/resource-reduction-20261018/`: frozen service, manifests,
component archives, model export records, smoke reports and logs. No third-party
manga images or detector weights are committed or included in components.
Native Windows freezing/installed acceptance and real public-release downloads
remain untested. No installer, model component or release has been published.

## Measured size

The private macOS frozen runtime falls from **714.50 MiB to 465.39 MiB**, a
**249.11 MiB** reduction versus the preceding Lindera build. The optional Torch
translation component is **292.20 MiB**; excluding its model from the default
installation brings the combined opportunity to approximately **541 MiB** of
regular-file content. New API/UI/descriptor bytes and final installer compression
still need exact-candidate measurement. Downloading translation restores its
model size in user data while the UniDic saving remains.

The locally exported ONNX translation component is **529.55 MiB**, reflecting
separate encoder/decoder graphs. This is macOS export/source-test evidence, not
a native Windows installer-size measurement. ONNX components and complete
installer downloads may have different final sizes; no speed or memory saving
is claimed here.
