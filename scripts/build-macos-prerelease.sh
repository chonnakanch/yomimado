#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
service_dir="$repo_root/services/ocr"
desktop_dir="$repo_root/apps/desktop"
resource_parent="$desktop_dir/src-tauri/resources"
resource_dir="$resource_parent/ocr"
python_bin="${YOMIMADO_BUILD_PYTHON:-$service_dir/.venv/bin/python}"
detector_repo="$service_dir/local-models/comic-text-detector"
translation_model="$service_dir/local-models/opus-mt-ja-en"
dictionary_dir="$service_dir/local-dictionaries"
model_revision="aa6573bd10b0d446cbf622e29c3e084914df9741"

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "This first pre-release build requires an Apple Silicon Mac." >&2
  exit 1
fi
for required in "$python_bin" "$detector_repo/inference.py" \
  "$translation_model/pytorch_model.bin" "$dictionary_dir/JMdict_e.gz" \
  "$dictionary_dir/kanjidic2.xml.gz"; do
  if [[ ! -e "$required" ]]; then
    echo "Missing local release input: $required" >&2
    exit 1
  fi
done
if ! "$python_bin" -m PyInstaller --version >/dev/null 2>&1; then
  echo "Install PyInstaller 6.16.0 into $python_bin before building." >&2
  exit 1
fi
export PYINSTALLER_CONFIG_DIR="$service_dir/build/pyinstaller-cache"
mkdir -p "$PYINSTALLER_CONFIG_DIR"

manga_model="${YOMIMADO_MANGA_OCR_SOURCE:-}"
if [[ -z "$manga_model" ]]; then
  manga_model="$($python_bin -c 'from huggingface_hub import snapshot_download; print(snapshot_download("kha-white/manga-ocr-base", revision="aa6573bd10b0d446cbf622e29c3e084914df9741", local_files_only=True))')"
fi
if [[ ! -f "$manga_model/config.json" || ! -f "$manga_model/pytorch_model.bin" ]]; then
  echo "Manga OCR model revision $model_revision is not available locally." >&2
  exit 1
fi
require_sha256() {
  local source="$1" expected="$2" actual
  actual="$(shasum -a 256 "$source" | cut -d ' ' -f1)"
  if [[ "$actual" != "$expected" ]]; then
    echo "Unexpected model checksum: $source ($actual)" >&2
    exit 1
  fi
}
require_sha256 "$manga_model/pytorch_model.bin" \
  c63e0bb5b3ff798c5991de18a8e0956c7ee6d1563aca6729029815eda6f5c2eb
require_sha256 "$translation_model/pytorch_model.bin" \
  ed649116c143fc2d7aea690246f4b2b7caa814e9e00a8d5bbe047822b18de022

"$python_bin" -m PyInstaller --noconfirm --clean --onedir \
  --name yomimado-ocr \
  --distpath "$service_dir/dist" \
  --workpath "$service_dir/build/pyinstaller" \
  --specpath "$service_dir/build/pyinstaller" \
  --paths "$service_dir" --paths "$detector_repo" \
  --hidden-import inference \
  --hidden-import backports.tarfile \
  --collect-all manga_ocr \
  --collect-all unidic_lite \
  --collect-all sudachidict_core \
  --collect-all wandb \
  --collect-submodules transformers.models.bert \
  --collect-submodules transformers.models.vit \
  --collect-submodules transformers.models.vision_encoder_decoder \
  --collect-submodules transformers.models.marian \
  --exclude-module pytest \
  --exclude-module tensorflow \
  "$service_dir/packaged_main.py"

mkdir -p "$resource_parent"
staging="$(mktemp -d "$resource_parent/.ocr-stage.XXXXXX")"
mkdir -p "$staging/runtime" "$staging/assets/comic-text-detector" \
  "$staging/assets/manga-ocr-base" "$staging/assets/opus-mt-ja-en" \
  "$staging/notices"
cp -R "$service_dir/dist/yomimado-ocr/." "$staging/runtime/"
# Manga OCR warms up by reading this path. Replace its sample artwork with
# an original, generated blank image so no third-party example is distributed.
"$python_bin" "$repo_root/scripts/create-manga-ocr-warmup.py" \
  "$staging/runtime/_internal/manga_ocr/assets/example.jpg"
rsync -a --exclude .git --exclude __pycache__ --exclude '*.pyc' \
  --exclude '*.onnx' --exclude '*.pt' --exclude '*.pth' \
  --exclude '/data/doc/' --exclude '/data/examples/' \
  --exclude '*.ipynb' \
  "$detector_repo/" "$staging/assets/comic-text-detector/"
cp -RL "$manga_model/." "$staging/assets/manga-ocr-base/"
for name in README.md config.json generation_config.json pytorch_model.bin \
  source.spm target.spm tokenizer_config.json vocab.json; do
  cp "$translation_model/$name" "$staging/assets/opus-mt-ja-en/"
done
cp "$dictionary_dir/JMdict_e.gz" "$dictionary_dir/kanjidic2.xml.gz" \
  "$staging/assets/"
cp "$repo_root/LICENSE" "$repo_root/THIRD_PARTY_LICENSES/README.md" \
  "$repo_root/THIRD_PARTY_LICENSES/MODEL_CREDITS.md" \
  "$repo_root/THIRD_PARTY_LICENSES/ASSET_NOTICES.md" \
  "$staging/notices/"
cp "$repo_root/docs/dictionary-updates.md" "$staging/notices/"
(
  cd "$staging/assets"
  shasum -a 256 manga-ocr-base/pytorch_model.bin \
    opus-mt-ja-en/pytorch_model.bin JMdict_e.gz kanjidic2.xml.gz
) > "$staging/notices/asset-checksums.txt"
"$python_bin" "$repo_root/scripts/generate-macos-notices.py" \
  "$staging/notices" --strict

# Replace only the ignored, generated bundle input; never touch user models.
if [[ "$resource_dir" != "$repo_root/apps/desktop/src-tauri/resources/ocr" ]]; then
  echo "Unexpected resource target: $resource_dir" >&2
  exit 1
fi
if [[ -d "$resource_dir" ]]; then
  rm -rf "$resource_dir"
fi
mv "$staging" "$resource_dir"

cd "$desktop_dir"
VITE_OCR_URL=http://127.0.0.1:8766 npm run tauri build -- \
  --config src-tauri/tauri.release.conf.json --bundles dmg

for dmg in "$desktop_dir"/src-tauri/target/release/bundle/dmg/YomiMado_*.dmg; do
  if [[ ! -f "$dmg" ]]; then
    echo "Missing macOS disk image installer." >&2
    exit 1
  fi
  bash "$repo_root/scripts/verify-macos-dmg.sh" "$dmg" "$python_bin"
  echo "Local macOS test installer: $dmg"
done
echo "Detector ONNX weights are not bundled; select your own copy in YomiMado."
echo "Private test only until signing, notarization, and remaining release gates are resolved."
