# Image/ONNX-only OpenCV for macOS

The macOS release uses `opencv-python==4.11.0.86+yomimado.1`, built locally
from the official 4.11.0.86 source distribution. Do not install the public
precompiled wheel into the release environment. A headless wheel alone is not
proof that FFmpeg is absent.

## Build and install

On Apple Silicon with source-built Python 3.11.17 and Xcode command-line tools:

```sh
rtk services/ocr/build/release-venv/bin/python scripts/build-opencv-macos.py
rtk services/ocr/build/release-venv/bin/python -m pip install --no-deps --force-reinstall services/ocr/build/opencv-source/opencv_python-4.11.0.86+yomimado.1-cp311-cp311-macosx_14_0_arm64.whl
rtk services/ocr/build/release-venv/bin/python scripts/opencv_release.py services/ocr/build/opencv-source/build-record.json
rtk services/ocr/build/release-venv/bin/python scripts/verify-python-release-lock.py
```

For a new environment, use `build-macos-prerelease.sh --prepare-runtime`
from [the release checklist](macos-release.md); it builds and installs the
interpreter and OpenCV together. It installs the packages from
`services/ocr/requirements-macos-release.txt` and the OCR project with
`--no-deps`. Build tools are installed separately in the ignored
`services/ocr/build/opencv-venv-py311`; they are not added to the frozen OCR runtime.
The build log is `services/ocr/build/opencv-source/build.log`.

The script pins the source archive SHA-256 and tool versions, rebuilds from
fresh extracted sources, targets arm64/macOS 14, and uses static OpenCV modules:
core, imgproc, imgcodecs, calib3d, features2d, flann, dnn, highgui and Python bindings.
These cover ONNX detection, image operations, contours and geometry. Video I/O,
FFmpeg, GStreamer, AVFoundation and optional acceleration dependencies
are disabled. JPEG, PNG, zlib and protobuf are built from the same archive;
OpenCV links only system dylibs. No OpenCV algorithm code is changed.

Highgui is retained because the detector imports `imshow` at module load time,
although YomiMado never calls it. It uses system Cocoa; Qt/GTK are disabled.
Keeping this compatibility module preserves the clean detector checkout.

Two source files are modified: `cv2/version.py` identifies the custom wheel,
and `LICENSE-3RD-PARTY.txt` describes this build and retains the Apache, JPEG,
PNG, zlib, protobuf, SoftFloat, MSCR and module-level author/licence notices.
The build retains the exact diff and modified files. The wrapper's MIT licence
is also preserved. This software is based in part on the work of the
Independent JPEG Group.

## Provenance and release gates

`build-record.json` records source, wheel and original binary hashes, build
tools, compiler/SDK, CMake options, notice sources and `getBuildInformation()`.
The verifier checks the installed custom version, binary and notice hashes,
module list, absent video APIs and system-only dynamic links. The DMG
verifier requires that same record and matching frozen-input hash, and rejects
FFmpeg/x264/x265/GnuTLS libraries anywhere in the runtime. Signing/relocation
changes the frozen binary's bytes, so comparison uses the native inventory's
original input hash.

`opencv-source-delivery.tar.gz` contains the original source archive, exact
modifications/diff, recipe copies, record and rebuild instructions. Preserve
it outside git and include it in the eventual corresponding-source delivery;
the full project source remains a separate required release asset. This
archive does not clear sources/notices for other frozen libraries. Compiler,
SDK and build location can change output hashes; the build is source-pinned,
not claimed to produce byte-identical wheels across machines.

Public release still requires the complete native/source review, Developer ID
signing, notarization and the remaining installed-app evidence in
[the release checklist](macos-release.md), which records the fresh-macOS test waiver.

References: [OpenCV build options](https://docs.opencv.org/4.x/db/d05/tutorial_config_reference.html),
[opencv-python source build](https://github.com/opencv/opencv-python/tree/4.11.0.86).
