#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
service_dir="$repo_root/services/ocr"
desktop_dir="$repo_root/apps/desktop"
resource_parent="$desktop_dir/src-tauri/resources"
resource_dir="$resource_parent/ocr"
python_bin="${YOMIMADO_BUILD_PYTHON:-$service_dir/build/release-venv/bin/python}"
detector_repo="$service_dir/local-models/comic-text-detector"
translation_model="$service_dir/local-models/opus-mt-ja-en"
dictionary_dir="$service_dir/local-dictionaries"
model_revision="aa6573bd10b0d446cbf622e29c3e084914df9741"
release=false
signed_release=false
prepare_runtime=false
prepare_numpy=false
case "${1:-}" in
  "") ;;
  --release) release=true ;;
  --developer-id-release) release=true; signed_release=true ;;
  --prepare-runtime) prepare_runtime=true ;;
  --prepare-numpy) prepare_numpy=true ;;
  *) echo "Usage: $0 [--release|--developer-id-release|--prepare-runtime|--prepare-numpy]" >&2; exit 1 ;;
esac
if [[ $# -gt 1 ]]; then
  echo "Usage: $0 [--release|--developer-id-release|--prepare-runtime|--prepare-numpy]" >&2
  exit 1
fi

if [[ "$(uname -s)" != "Darwin" || "$(uname -m)" != "arm64" ]]; then
  echo "This first pre-release build requires an Apple Silicon Mac." >&2
  exit 1
fi
if $prepare_numpy; then
  "$python_bin" - "$repo_root" <<'PYNUMPY'
import base64, csv, hashlib, io, json, os, re, shutil, subprocess, sys, tarfile, zipfile
from pathlib import Path
root = Path(sys.argv[1]).resolve()
output = root / "services/ocr/build/numpy-source"
output.mkdir(parents=True, exist_ok=True)
original = root / "services/ocr/build/source-delivery/python/numpy-1.26.4.tar.gz"
archive = output / original.name
expected = "2a02aba9ed12e4ac4eb3ea9421c420301a0c6460d9830d74a9df87efa4912010"
if not archive.exists():
    if original.exists():
        shutil.copyfile(original, archive)
    else:
        import urllib.request
        with urllib.request.urlopen("https://pypi.org/pypi/numpy/1.26.4/json", timeout=60) as response:
            metadata = json.load(response)
        entry = next(item for item in metadata["urls"] if item["filename"] == archive.name)
        if entry["digests"]["sha256"] != expected or not entry["url"].startswith("https://files.pythonhosted.org/"):
            raise ValueError("Unexpected NumPy source registry record")
        urllib.request.urlretrieve(entry["url"], archive)
hashfile = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
if hashfile(archive) != expected:
    raise ValueError("NumPy source archive checksum mismatch")
source = output / "numpy-1.26.4"
if source.exists():
    shutil.rmtree(source)
with tarfile.open(archive) as bundle:
    for member in bundle.getmembers():
        if member.issym() or member.islnk() or not (output / member.name).resolve().is_relative_to(output):
            raise ValueError("Unsafe NumPy source archive")
    bundle.extractall(output)
# Keep build tools outside the inventoried/frozen release environment.
build_env = root / "services/ocr/build/numpy-build-venv"
subprocess.run([sys.executable, "-m", "venv", str(build_env)], check=True)
build_python = str(build_env / "bin/python")
tools = ["Cython==3.0.8", "meson-python==0.15.0", "meson==1.3.2", "ninja==1.11.1.1", "packaging==26.3", "pyproject-metadata==0.7.1"]
subprocess.run([build_python, "-m", "pip", "install", "--no-deps", *tools], check=True)
env = os.environ.copy()
env.update(MACOSX_DEPLOYMENT_TARGET="14.0", CC=subprocess.check_output(["xcrun", "--find", "clang"], text=True).strip(), CXX=subprocess.check_output(["xcrun", "--find", "clang++"], text=True).strip(), SDKROOT=subprocess.check_output(["xcrun", "--show-sdk-path"], text=True).strip())
env["PATH"] = str(build_env / "bin") + os.pathsep + env["PATH"]
args = ["-Dblas=accelerate", "-Dlapack=accelerate", "-Duse-ilp64=true", "-Dallow-noblas=false"]
wheels = output / "wheels"
wheels.mkdir(exist_ok=True)
subprocess.run([build_python, "-m", "pip", "wheel", "--no-build-isolation", "--no-deps", str(source), "--wheel-dir", str(wheels), *["--config-settings=setup-args=" + arg for arg in args], "--config-settings=compile-args=-j4"], env=env, check=True)
wheel = next(wheels.glob("numpy-1.26.4-*.whl"))
# Preserve embedded licences rather than the public wheel's unused GCC notice.
texts = [source / "LICENSES_bundled.txt"]
texts.extend(p for p in source.rglob("*") if p.is_file() and p.name.lower().startswith(("license", "copying")) and (p.is_relative_to(source / "numpy") or p.is_relative_to(source / "tools/npy_tempita")))
notice = (source / "LICENSE.txt").read_text()
for path in sorted(set(texts)):
    notice += "\n\n--- " + path.relative_to(source).as_posix() + " ---\n" + path.read_text()
for relative in ["numpy/core/src/multiarray/dragon4.c", "numpy/fft/_pocketfft.c"]:
    comments = re.findall(r"/\*.*?\*/", (source / relative).read_text(), re.S)
    notice += "\n\n--- " + relative + " ---\n" + "\n".join(c for c in comments if "Copyright" in c or "copyright" in c)
with zipfile.ZipFile(wheel) as bundle:
    contents = {name: bundle.read(name) for name in bundle.namelist() if not name.endswith("/")}
license_name = next(name for name in contents if name.endswith(".dist-info/LICENSE.txt"))
contents[license_name] = notice.encode()
record_name = next(name for name in contents if name.endswith(".dist-info/RECORD"))
record_csv = io.StringIO()
writer = csv.writer(record_csv, lineterminator="\n")
for name, data in contents.items():
    writer.writerow([name, "" if name == record_name else "sha256=" + base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode(), "" if name == record_name else len(data)])
contents[record_name] = record_csv.getvalue().encode()
with zipfile.ZipFile(wheel, "w", zipfile.ZIP_DEFLATED) as bundle:
    for name, data in contents.items():
        bundle.writestr(name, data)
subprocess.run([sys.executable, "-m", "pip", "install", "--no-deps", "--force-reinstall", str(wheel)], check=True)
import numpy
site = Path(numpy.__file__).parent
recipe = (root / "scripts/build-macos-prerelease.sh").read_text().split("if $prepare_numpy; then\n", 1)[1].split("\nif $prepare_runtime; then", 1)[0]
record = {"version": "1.26.4", "sourceSha256": expected, "recipeSha256": hashlib.sha256(recipe.encode()).hexdigest(), "buildTools": tools, "mesonArgs": args, "compiler": subprocess.check_output([env["CC"], "--version"], text=True).strip(), "sdk": subprocess.check_output(["xcrun", "--show-sdk-version"], text=True).strip(), "wheel": wheel.name, "wheelSha256": hashfile(wheel), "binaries": {p.relative_to(site).as_posix(): hashfile(p) for p in sorted(site.rglob("*.so"))}, "noticeSha256": hashlib.sha256(notice.encode()).hexdigest(), "configuration": numpy.__config__.CONFIG}
(output / "build-record.json").write_text(json.dumps(record, indent=2) + "\n")
(output / "NOTICE.txt").write_text(notice)
with tarfile.open(output / "numpy-source-delivery.tar.gz", "w:gz") as bundle:
    for path in [archive, output / "build-record.json", output / "NOTICE.txt", root / "scripts/build-macos-prerelease.sh"]:
        bundle.add(path, arcname="numpy-source-delivery/" + path.name)
print("NumPy built against system Accelerate; original source, recipe, notices and binary hashes retained.")
PYNUMPY
  "$python_bin" "$repo_root/scripts/verify-python-release-lock.py" --numpy-only
  exit 0
fi
if $prepare_runtime; then
  python_bin="$service_dir/build/release-venv/bin/python"
  bootstrap="${YOMIMADO_BOOTSTRAP_PYTHON:-/usr/bin/python3}"
  python_source_root="$service_dir/build/python-source"
  python_runtime_prefix="$service_dir/build/python-runtime"
  openssl_runtime_prefix="$python_runtime_prefix/openssl"
  lzma_runtime_prefix="$python_runtime_prefix/lzma"
  mkdir -p "$python_source_root"
  "$bootstrap" - "$python_source_root" <<'PY'
import hashlib, json, shutil, sys, tarfile, urllib.request
from pathlib import Path
root = Path(sys.argv[1]).resolve()
sources = [
    ("Python-3.11.17.tgz", "https://www.python.org/ftp/python/3.11.17/Python-3.11.17.tgz", "53cdee63ac4bf12387b7b33a53d3b1f8f4941cad73807a7b4fe91bb001ef004a", "Python-3.11.17"),
    ("openssl-3.5.9.tar.gz", "https://github.com/openssl/openssl/releases/download/openssl-3.5.9/openssl-3.5.9.tar.gz", "603f5602e2eef00d77fbd429d34dcd5822bb301757a1bc9cdb24c670f1eb859a", "openssl-3.5.9"),
    ("xz-5.8.4.tar.gz", "https://github.com/tukaani-project/xz/releases/download/v5.8.4/xz-5.8.4.tar.gz", "0014c7886930454fe8bd4228665b51af55eeae560ea135c9c4cd33f55b2591d9", "xz-5.8.4"),
]
for name, url, expected, directory in sources:
    path = root / name
    if not path.exists():
        temporary = path.with_suffix(".part")
        urllib.request.urlretrieve(url, temporary)
        if hashlib.sha256(temporary.read_bytes()).hexdigest() != expected:
            raise ValueError("Runtime source download checksum mismatch")
        temporary.replace(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError("Runtime source checksum mismatch")
    if (root / directory).exists():
        shutil.rmtree(root / directory)
    with tarfile.open(path) as bundle:
        for member in bundle.getmembers():
            if member.issym() or member.islnk() or not (root / member.name).resolve().is_relative_to(root):
                raise ValueError("Unsafe runtime source archive")
        bundle.extractall(root)
(root / "sources.json").write_text(json.dumps([
    {"filename": name, "url": url, "sha256": digest}
    for name, url, digest, _ in sources
], indent=2) + "\n")
PY
  export MACOSX_DEPLOYMENT_TARGET=14.0
  export SDKROOT="$(xcrun --sdk macosx --show-sdk-path)"
  export CC="$(xcrun --sdk macosx --find clang)"
  export CXX="$(xcrun --sdk macosx --find clang++)"
  export CFLAGS="-O2 -mmacosx-version-min=14.0 -arch arm64"
  export LDFLAGS="-mmacosx-version-min=14.0 -arch arm64"
  (
    cd "$python_source_root/openssl-3.5.9"
    ./Configure darwin64-arm64-cc no-shared no-tests no-module no-legacy \
      --prefix="$openssl_runtime_prefix" --openssldir="$openssl_runtime_prefix/ssl"
    make -j4
    make install_sw
    cd "$python_source_root/xz-5.8.4"
    ./configure --prefix="$lzma_runtime_prefix" --disable-shared --enable-static \
      --disable-xz --disable-xzdec --disable-lzmadec --disable-lzmainfo \
      --disable-scripts --disable-doc --disable-nls
    make -j4
    make check
    make install
    cd "$python_source_root/Python-3.11.17"
    LIBLZMA_CFLAGS="-I$lzma_runtime_prefix/include" LIBLZMA_LIBS="$lzma_runtime_prefix/lib/liblzma.a" \
      ./configure --prefix="$python_runtime_prefix" --enable-shared \
      --without-static-libpython --with-openssl="$openssl_runtime_prefix" \
      --with-openssl-rpath=no --without-readline --with-ensurepip=install
    make -j4
    make install
  ) > "$python_source_root/build.log" 2>&1
  "$python_runtime_prefix/bin/python3.11" - "$repo_root" <<'PY'
import hashlib, json, re, shutil, subprocess, sys, sysconfig, tarfile
from pathlib import Path
root = Path(sys.argv[1]).resolve()
source = root / "services/ocr/build/python-source"
base = Path(sys.base_prefix)
hashfile = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
notices = source / "notices"
notices.mkdir(exist_ok=True)
for name, path in {
    "CPython-LICENSE.txt": source / "Python-3.11.17/LICENSE",
    "Expat-COPYING.txt": source / "Python-3.11.17/Modules/expat/COPYING",
    "SHA3-LICENSE.txt": source / "Python-3.11.17/Modules/_sha3/LICENSE",
    "OpenSSL-LICENSE.txt": source / "openssl-3.5.9/LICENSE.txt",
    "liblzma-LICENSE.txt": source / "xz-5.8.4/COPYING.0BSD",
    "XZ-COPYING.txt": source / "xz-5.8.4/COPYING",
}.items():
    shutil.copy2(path, notices / name)
for name, relative in {
    "libmpdec-COPYRIGHT.txt": "Modules/_decimal/libmpdec/mpdecimal.c",
    "Mersenne-Twister-NOTICE.txt": "Modules/_randommodule.c",
    "BLAKE2-NOTICE.txt": "Modules/_blake2/impl/blake2.h",
    "dtoa-NOTICE.txt": "Python/dtoa.c",
    "SipHash-NOTICE.txt": "Python/pyhash.c",
}.items():
    text = (source / "Python-3.11.17" / relative).read_text()
    comments = re.findall(r"/\*.*?\*/", text, re.S)
    matches = [comment for comment in comments if "Copyright" in comment or "public domain" in comment]
    if not matches:
        raise ValueError("Missing embedded runtime notice: " + relative)
    (notices / name).write_text("\n\n".join(matches) + "\n")
record = {
    "pythonVersion": "3.11.17", "opensslVersion": "3.5.9", "lzmaVersion": "5.8.4",
    "sources": json.loads((source / "sources.json").read_text()),
    "recipeScope": "prepare-runtime",
    "recipeSha256": hashlib.sha256((root / "scripts/build-macos-prerelease.sh").read_text().split("if $prepare_runtime; then\n", 1)[1].split("\nif $release; then", 1)[0].encode()).hexdigest(),
    "configureArgs": sysconfig.get_config_var("CONFIG_ARGS").replace(str(root), "$PROJECT_ROOT"),
    "compiler": subprocess.check_output(["clang", "--version"], text=True).strip(),
    "sdk": subprocess.check_output(["xcrun", "--show-sdk-version"], text=True).strip(),
    "binaries": {str(p.relative_to(base)): hashfile(p) for p in [
        base / "bin/python3.11", base / "lib/libpython3.11.dylib",
        *sorted(base.glob("lib/python3.11/lib-dynload/*.so"))]},
    "noticeHashes": {p.name: hashfile(p) for p in sorted(notices.iterdir())},
}
(source / "build-record.json").write_text(json.dumps(record, indent=2) + "\n")
with tarfile.open(source / "python-source-delivery.tar.gz", "w:gz") as bundle:
    for p in [*(source / item["filename"] for item in record["sources"]),
              source / "build-record.json", root / "scripts/build-macos-prerelease.sh", notices]:
        bundle.add(p, arcname="python-source-delivery/" + p.name)
print("Source-controlled Python/OpenSSL built; original sources, recipe, hashes and notices recorded.")
PY
  "$python_runtime_prefix/bin/python3.11" -c 'import ssl, lzma, sqlite3, ctypes; assert lzma.decompress(lzma.compress(b"runtime check")) == b"runtime check"'
  "$python_runtime_prefix/bin/python3.11" -m venv "$service_dir/build/release-venv"
  sed '/^opencv-python==/d' "$service_dir/requirements-macos-release.txt" > "$python_source_root/requirements-without-opencv.txt"
  "$python_bin" -m pip install --no-deps -r "$python_source_root/requirements-without-opencv.txt"
  export SSL_CERT_FILE="$("$python_bin" -c 'import certifi; print(certifi.where())')"
  "$python_bin" "$repo_root/scripts/build-opencv-macos.py" --jobs 4
  wheel="$("$python_bin" -c 'import json,sys; print(json.load(open(sys.argv[1]))["wheel"])' "$service_dir/build/opencv-source/build-record.json")"
  "$python_bin" -m pip install --no-deps --force-reinstall "$service_dir/build/opencv-source/$wheel"
  "$python_bin" -m pip install --no-build-isolation --no-deps "$service_dir"
  "$python_bin" -m pip check
  bash "$repo_root/scripts/build-macos-prerelease.sh" --prepare-numpy
  "$python_bin" "$repo_root/scripts/verify-python-release-lock.py"
  echo "Release runtime prepared. Build a private DMG before attempting --release."
  exit 0
fi
if $release; then
  if $signed_release; then
    "$python_bin" "$repo_root/scripts/macos-release.py" preflight
  fi
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
cp "$service_dir/build/numpy-source/build-record.json" "$staging/notices/numpy-build.json"
cp "$service_dir/build/python-source/build-record.json" "$staging/notices/python-build.json"
cp "$service_dir/build/opencv-source/source-changes.diff" "$staging/notices/opencv-source-changes.diff"
(
  cd "$staging/assets"
  shasum -a 256 manga-ocr-base/pytorch_model.bin \
    opus-mt-ja-en/pytorch_model.bin JMdict_e.gz kanjidic2.xml.gz
) > "$staging/notices/asset-checksums.txt"
"$python_bin" "$repo_root/scripts/generate-macos-notices.py" \
  "$staging/notices" --strict
"$python_bin" - "$staging/notices/distribution.json" "$release" "$signed_release" <<'PY'
import json, sys
from pathlib import Path
signed = sys.argv[3] == "true"
mode = "developer-id" if signed else ("unnotarized-hobby" if sys.argv[2] == "true" else "private-test")
Path(sys.argv[1]).write_text(json.dumps({
    "mode": mode, "developerIdSigned": signed, "appleNotarized": signed,
    "manualGatekeeperApproval": not signed,
}, indent=2) + "\n")
PY
git -C "$repo_root" rev-parse HEAD > "$staging/notices/project-revision.txt"
if $release; then
  if [[ -d "$YOMIMADO_SOURCE_DIR/native-notices" ]]; then
    cp -R "$YOMIMADO_SOURCE_DIR/native-notices" "$staging/notices/"
  fi
  "$python_bin" "$repo_root/scripts/macos-release.py" verify-sources \
    "$staging/notices" --source-dir "$YOMIMADO_SOURCE_DIR" \
    --revision "$(cat "$staging/notices/project-revision.txt")"
  cp "$YOMIMADO_SOURCE_DIR/source-delivery.json" "$staging/notices/"
  if $signed_release; then
    "$python_bin" "$repo_root/scripts/macos-release.py" sign-runtime "$staging/runtime"
  fi
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
if $signed_release; then
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
# Private and unnotarized hobby builds do not use signing/notary credentials.
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
  if $release; then
    bash "$repo_root/scripts/verify-macos-dmg.sh" "$dmg" "$python_bin" --hobby-release
    if [[ -n "$(git -C "$repo_root" status --porcelain)" || \
          "$(git -C "$repo_root" rev-parse HEAD)" != "$(cat "$resource_dir/notices/project-revision.txt")" ]]; then
      echo "The source tree changed during the release build; rebuild from a clean commit." >&2
      exit 1
    fi
    final_output="$desktop_dir/src-tauri/target/release/bundle/releasable"
    mkdir -p "$final_output"
    cp "$dmg" "$final_output/"
    (cd "$final_output"; shasum -a 256 "$(basename "$dmg")") > "$final_output/$(basename "$dmg").sha256"
    echo "Verified unnotarized candidate (installed-app manual checks still required): $final_output/$(basename "$dmg")"
  else
    bash "$repo_root/scripts/verify-macos-dmg.sh" "$dmg" "$python_bin"
    echo "Local macOS test installer: $dmg"
  fi
done
echo "Detector ONNX weights are not bundled; select your own copy in YomiMado."
if ! $release; then
  echo "Private test only until source clearance and remaining installed-app release gates are resolved."
fi
