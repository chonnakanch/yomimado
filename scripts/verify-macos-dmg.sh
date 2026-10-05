#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
dmg="${1:?Pass a DMG path}"
python_bin="${2:-$repo_root/services/ocr/build/release-venv/bin/python}"
mode="${3:---private}"
case "$mode" in
  --private|--private-smoke|--hobby-release|--release) ;;
  *) echo "Expected --private, --private-smoke, --hobby-release or --release" >&2; exit 1 ;;
esac

if [[ ! -f "$dmg" ]]; then
  echo "Missing macOS disk image: $dmg" >&2
  exit 1
fi
hdiutil verify "$dmg"
if [[ "$mode" == --release ]]; then
  "$python_bin" "$repo_root/scripts/macos-release.py" verify-dmg "$dmg"
fi
mount_dir="$(mktemp -d /private/tmp/yomimado-dmg.XXXXXX)"
cleanup() {
  for attempt in 1 2 3; do
    if hdiutil detach "$mount_dir" >/dev/null 2>&1; then
      rmdir "$mount_dir"
      return
    fi
    sleep 2
  done
  echo "Failed to detach test volume: $mount_dir" >&2
  exit 1
}
trap cleanup EXIT
hdiutil attach -readonly -nobrowse -mountpoint "$mount_dir" "$dmg"
"$python_bin" "$repo_root/scripts/verify-macos-bundle.py" \
  "$mount_dir/YomiMado.app"
"$python_bin" "$repo_root/scripts/macos-release.py" verify-platform "$mount_dir/YomiMado.app"
if [[ "$mode" == --release ]]; then
  "$python_bin" "$repo_root/scripts/macos-release.py" verify-app "$mount_dir/YomiMado.app"
fi
if [[ "$mode" == --release || "$mode" == --hobby-release ]]; then
  : "${YOMIMADO_SOURCE_DIR:?Set the corresponding-source delivery directory}"
  notices="$mount_dir/YomiMado.app/Contents/Resources/ocr/notices"
  if [[ "$mode" == --hobby-release ]]; then
    "$python_bin" "$repo_root/scripts/macos-release.py" verify-hobby "$notices"
  fi
  cmp "$notices/source-delivery.json" "$YOMIMADO_SOURCE_DIR/source-delivery.json"
  "$python_bin" "$repo_root/scripts/macos-release.py" verify-sources "$notices" \
    --source-dir "$YOMIMADO_SOURCE_DIR" --revision "$(cat "$notices/project-revision.txt")"
fi
if [[ "$mode" != --private ]]; then
  : "${YOMIMADO_SMOKE_DETECTOR_MODEL:?Set the user-installed ONNX file for the frozen smoke}"
  "$python_bin" "$repo_root/scripts/smoke-macos-bundle.py" "$mount_dir/YomiMado.app" \
    --detector-model "$YOMIMADO_SMOKE_DETECTOR_MODEL"
fi
