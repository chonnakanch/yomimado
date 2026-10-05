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
release=false
case "${1:-}" in
  "") ;;
  --release) release=true ;;
  *) echo "Usage: $0 [--release]" >&2; exit 1 ;;
esac
if [[ $# -gt 1 ]]; then
  echo "Usage: $0 [--release]" >&2
  exit 1
fi

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "This first pre-release build requires an Apple Silicon Mac." >&2
  exit 1
fi
if $release; then
  "$python_bin" "$repo_root/scripts/macos-release.py" preflight
  if [[ -z "${YOMIMADO_SOURCE_DIR:-}" || ! -d "$YOMIMADO_SOURCE_DIR" ]]; then
    echo "Set YOMIMADO_SOURCE_DIR to the reviewed corresponding-source delivery." >&2
    exit 1
  fi
  if [[ -z "${YOMIMADO_SMOKE_DETECTOR_MODEL:-}" || ! -f "$YOMIMADO_SMOKE_DETECTOR_MODEL" ]]; then
    echo "Set YOMIMADO_SMOKE_DETECTOR_MODEL to your separately installed ONNX file." >&2
    exit 1
  fi
  if [[ -n "$(git -C "$repo_root" status --porcelain)" ]]; then
    echo "Commit all release changes before building; the release tree must be clean." >&2
    exit 1
  fi
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
"$python_bin" "$repo_root/scripts/verify-python-release-lock.py"
opencv_record="$service_dir/build/opencv-source/build-record.json"
"$python_bin" "$repo_root/scripts/opencv_release.py" "$opencv_record"
# The detector imports imshow even for ONNX-only inference. Check its source
# imports before freezing so an incompatible minimal OpenCV fails early.
"$python_bin" -c 'import sys; sys.path.insert(0, sys.argv[1]); from inference import TextDetector; print("Detector source imports with release OpenCV.")' "$detector_repo"
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
trap '[[ ! -d "$staging" ]] || rm -rf "$staging"' EXIT
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
cp "$repo_root/docs/macos-source-review.md" "$staging/notices/"
cp "$opencv_record" "$staging/notices/opencv-build.json"
cp "$service_dir/build/opencv-source/source-changes.diff" "$staging/notices/opencv-source-changes.diff"
(
  cd "$staging/assets"
  shasum -a 256 manga-ocr-base/pytorch_model.bin \
    opus-mt-ja-en/pytorch_model.bin JMdict_e.gz kanjidic2.xml.gz
) > "$staging/notices/asset-checksums.txt"
"$python_bin" "$repo_root/scripts/generate-macos-notices.py" \
  "$staging/notices" --strict
git -C "$repo_root" rev-parse HEAD > "$staging/notices/project-revision.txt"
if $release; then
  if [[ -d "$YOMIMADO_SOURCE_DIR/native-notices" ]]; then
    cp -R "$YOMIMADO_SOURCE_DIR/native-notices" "$staging/notices/"
  fi
  "$python_bin" "$repo_root/scripts/macos-release.py" verify-sources \
    "$staging/notices" --source-dir "$YOMIMADO_SOURCE_DIR" \
    --revision "$(cat "$staging/notices/project-revision.txt")"
  cp "$YOMIMADO_SOURCE_DIR/source-delivery.json" "$staging/notices/"
  "$python_bin" "$repo_root/scripts/macos-release.py" sign-runtime "$staging/runtime"
fi

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
if $release; then
  # Use the Keychain profile below for explicit notarization. Tauri's default
  # path may merely warn when notarization variables are missing. Do not mix
  # environment-based certificate import with an already installed identity.
  env -u APPLE_API_ISSUER -u APPLE_API_KEY -u APPLE_API_KEY_PATH \
    -u APPLE_ID -u APPLE_PASSWORD -u APPLE_TEAM_ID \
    -u APPLE_CERTIFICATE -u APPLE_CERTIFICATE_PASSWORD \
    VITE_OCR_URL=http://127.0.0.1:8766 npm run tauri build -- \
    --config src-tauri/tauri.release.conf.json --bundles app
  app="$desktop_dir/src-tauri/target/release/bundle/macos/YomiMado.app"
  final_output="$desktop_dir/src-tauri/target/release/bundle/releasable"
  mkdir -p "$final_output"
  output="$(mktemp -d "$desktop_dir/src-tauri/target/release/bundle/.release-stage.XXXXXX")"
  trap '[[ ! -d "$staging" ]] || rm -rf "$staging"; [[ ! -d "$output" ]] || rm -rf "$output"' EXIT
  "$python_bin" "$repo_root/scripts/verify-macos-bundle.py" "$app"
  # Sign any native resources the Tauri bundler doesn't traverse, then seal
  # the outer app. No --deep signing and no library-validation exemption.
  "$python_bin" "$repo_root/scripts/macos-release.py" sign-runtime "$app/Contents"
  codesign --force --timestamp --options runtime --sign "$APPLE_SIGNING_IDENTITY" "$app"
  archive="$output/YomiMado-notary.zip"
  ditto -c -k --keepParent "$app" "$archive"
  "$python_bin" "$repo_root/scripts/macos-release.py" notarize "$archive"
  xcrun stapler staple "$app"
  "$python_bin" "$repo_root/scripts/macos-release.py" verify-app "$app"
  image_stage="$(mktemp -d "$resource_parent/.dmg-stage.XXXXXX")"
  trap '[[ ! -d "$staging" ]] || rm -rf "$staging"; [[ ! -d "$image_stage" ]] || rm -rf "$image_stage"; [[ ! -d "$output" ]] || rm -rf "$output"' EXIT
  ditto "$app" "$image_stage/YomiMado.app"
  ln -s /Applications "$image_stage/Applications"
  dmg="$output/YomiMado_$("$python_bin" -c 'import json; print(json.load(open("src-tauri/tauri.conf.json"))["version"])')_aarch64.dmg"
  hdiutil create -ov -format UDZO -volname YomiMado -srcfolder "$image_stage" "$dmg"
  codesign --force --timestamp --sign "$APPLE_SIGNING_IDENTITY" "$dmg"
  "$python_bin" "$repo_root/scripts/macos-release.py" notarize "$dmg"
  xcrun stapler staple "$dmg"
  bash "$repo_root/scripts/verify-macos-dmg.sh" "$dmg" "$python_bin" --release
  (cd "$output"; shasum -a 256 "$(basename "$dmg")") > "$dmg.sha256"
  if [[ -n "$(git -C "$repo_root" status --porcelain)" || \
        "$(git -C "$repo_root" rev-parse HEAD)" != "$(cat "$resource_dir/notices/project-revision.txt")" ]]; then
    echo "The source tree changed during the release build; rebuild from a clean commit." >&2
    exit 1
  fi
  # Expose candidate files only after every verification and smoke succeeds.
  # Keep notarization reports; the temporary ZIP is not a release asset.
  for artifact in "$dmg" "$dmg.sha256" "$dmg.notarization.json" "$archive.notarization.json"; do
    mv "$artifact" "$final_output/"
  done
  dmg="$final_output/$(basename "$dmg")"
  echo "Verified signed/notarized candidate (installed-app manual checks still required): $dmg"
  exit 0
fi
# Private builds should not pick up signing/notary credentials accidentally.
env -u APPLE_SIGNING_IDENTITY -u APPLE_CERTIFICATE -u APPLE_CERTIFICATE_PASSWORD \
  -u APPLE_API_ISSUER -u APPLE_API_KEY -u APPLE_API_KEY_PATH \
  -u APPLE_ID -u APPLE_PASSWORD -u APPLE_TEAM_ID \
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
