#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
dmg="${1:?Pass a DMG path}"
python_bin="${2:-$repo_root/services/ocr/.venv/bin/python}"

if [[ ! -f "$dmg" ]]; then
  echo "Missing macOS disk image: $dmg" >&2
  exit 1
fi
hdiutil verify "$dmg"
mount_dir="$(mktemp -d /private/tmp/yomimado-dmg.XXXXXX)"
cleanup() {
  hdiutil detach "$mount_dir" >/dev/null 2>&1 || true
  rmdir "$mount_dir" >/dev/null 2>&1 || true
}
trap cleanup EXIT
hdiutil attach -readonly -nobrowse -mountpoint "$mount_dir" "$dmg"
"$python_bin" "$repo_root/scripts/verify-macos-bundle.py" \
  "$mount_dir/YomiMado.app"
