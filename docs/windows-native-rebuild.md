# Windows native source work remaining

This is an execution worksheet for the public-distribution gate, not an
approved source delivery or a claim that these Windows rebuilds have run.
Use the exact candidate's `windows-inventory.json`,
`windows-native-configuration.json` and `windows-installer-inputs.json`.
Preserve originals, patches, build commands, compiler versions, full vendor
notices and resulting hashes together. A replacement changes the installer
hash and requires the installed-runtime checks and maintainer tests again.

## Replace the Intel binary components

The inspected Windows Torch wheel reports source commit
`a1cb3cc05d46d198467bebbb6e8fba50a325d4e7`, MKL 2025.2 and Intel OpenMP.
Its original `torch/version.py` independently matches that commit. Preserve the
recursive preferred-source tree at that revision, including the recorded
submodule commits; a GitHub source tarball alone lacks those submodules.
The existing local PyTorch source collection can be checked against this
Windows revision, but its macOS approval does not cover the Windows binaries.

Prepare a separate Windows CPU Torch build using `BLAS=Eigen`,
`USE_OPENMP=0`, `USE_MKLDNN=0`, `USE_CUDA=0`, `USE_XPU=0`,
`USE_DISTRIBUTED=0`, `USE_FBGEMM=0` and `BUILD_TEST=0`. These are proposed
build settings: the pinned source supports Eigen in
`cmake/Dependencies.cmake`, but the complete Windows build and inference are
unverified. Pin the build tools and retain the actual CMake cache rather than
assuming an environment variable was accepted. Rebuild the matching
torchvision extension against this Torch; the original wheel's `_C.pyd`
must not be presumed ABI compatible. Preserve its preferred sources and
vendor graph independently.

Build OpenCV from the pinned `opencv-python-4.11.0.86.tar.gz` input
(`03d60ccae62304860d232272e4a4fda93c39d595780cb40b161b310244b736a4`)
with IPP/IPP IW and FFmpeg disabled. Limit modules to those required by the
existing detector: inspect its actual imports and the macOS minimal recipe
before deciding the Windows highgui stub/module handling. Disable unused
codecs and network-fetched vendor inputs deliberately, preserve selected
static sources/notices, and record `cv2.getBuildInformation()` from the built
wheel. The Windows wheel currently links IPP statically; deleting its optional
FFmpeg DLL does not remove IPP.

For both replacements, require x64 PE inventory, no Intel MKL/OpenMP/IPP or
CUDA imports/loaded modules, and installed synthetic horizontal/vertical OCR,
tokenization, dictionaries, kanji, uncached translation and restart persistence.
Do not substitute these builds into the macOS seed or shared development lock.

## GEOS source and library replacement

The Windows Shapely wheel reports GEOS **3.11.4**. Its original source is
`https://download.osgeo.org/geos/geos-3.11.4.tar.bz2`, SHA-256
`364c88ccfc38aa50cf65c700e7b2ae4706ed103326128493dbf750c78d136d2c`.
The retained original archive was hash checked locally. Preserve the GEOS
LGPL text and embedded vendor notices as well as Shapely's BSD text.

The pinned Shapely 2.0.7 source archive contains `ci/install_geos.cmd`:
it builds GEOS with CMake/Ninja, `CMAKE_BUILD_TYPE=Release` and
`BUILD_SHARED_LIBS=ON`, runs CTest and installs it. Adapt its original HTTP
download to the HTTPS URL above, verify the hash before extraction, and pin
CMake/Ninja rather than copying its unpinned `pip install` command. Record
these changes. This Windows recipe and replacement test remain unrun.

In the inspected frozen runtime, the three Shapely PYDs import
`geos_c-2ec21252057a9a4d4390485e0e576a5a.dll`; that DLL imports
`geos-601667c569b99092781bd4af7fecde0b.dll`. Merely copying a rebuilt
`geos_c.dll` beside them does not replace the library they load. In a disposable
copy, supply compatible replacement libraries under the imported names and
account for the rebuilt C wrapper's own imports, or rebuild Shapely against
the replacement. Verify actual loaded paths and geometry through frozen OCR.
Retain a user-facing replacement/relinking recipe with the corresponding
sources; the macOS GEOS replacement test is not Windows evidence.

## Finish remaining binary bindings

- NumPy's OpenBLAS DLL reports `0.3.23-293-gc2f4bdbb`, GCC 10.3.0.
  Preserve that exact OpenBLAS revision, LAPACK/compiler runtime sources,
  original wheel build recipe and applicable LGPL replacement instructions.
  The NumPy sdist and full licence texts alone do not supply these vendors.
- Pillow's actual codec versions are recorded in the configuration report.
  Resolve its Windows build script's downloaded vendor sources and notices;
  do not use the different macOS codec inventory.
- Bind Fugashi's hashed MeCab DLL, SudachiPy/tokenizer Rust vendor graphs,
  PyInstaller's bootloader and modified frozen executable, and CPython's
  pinned OpenSSL/libffi binary externals to their exact sources/recipes.
- Identify each app-local VC runtime's origin and exact redistribution terms.
  Windows OS libraries are excluded from delivery; this does not clear VC
  redistributables or SDK loader binaries.
- Bind the actual NSIS stub/plugins to NSIS 3.11 and
  `nsis_tauri_utils` commit `13d9edd27b69310e108d6fbd49f90992f8a05390`.
  Retain recursive build inputs and the exact WebView2 SDK loader scope.

Finish with a per-native-input review bound to the new installer hash, complete
source/notices archives and verified archive hashes. Keep public publication
disabled while any of these entries or the separate-PC installer gate is open.
