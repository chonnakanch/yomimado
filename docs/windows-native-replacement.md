# Windows native library replacement

These instructions accompany the private source preparation. They describe
replacement of LGPL libraries without modifying the desktop EXE or Python PYDs.
They are not a claim that every replacement has been tested with the latest
installer. Keep the setup, source archive and SHA256SUMS from the same candidate.

## Before replacing a library

1. Quit YomiMado and confirm its OCR service has exited. Back up the installed
   DLLs and their names before changing them; preserve user models and SQLite data.
2. Extract `windows-source-preparation.tar.gz`. The `windows-native` source
   directory includes `source-preparation.json`, the pinned original-input
   manifest, filtered preferred-source archives and collection recipes. The
   original licence texts are also installed under `notices/windows-native-sources`.
   Verify delivered archive hashes against that preparation record before use.
3. Use Windows x64 tools and the same public API/ABI expected by the existing
   native callers. Rebuilding an unrelated upstream version is not automatically
   a compatible replacement. Keep your source changes and resulting build log.

## GEOS 3.11.4

The original GEOS preferred source and LGPL text are provided. Build its shared
libraries with an x64 MSVC environment and CMake/Ninja. The exact project recipe
is `scripts/build-geos-windows.py`; its selected configuration includes:

```powershell
cmake -S <geos-source> -B <build> -G Ninja -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON -DBUILD_TESTING=ON -DBUILD_BENCHMARKS=OFF -DBUILD_WEBSITE=OFF -DCMAKE_POLICY_DEFAULT_CMP0091=NEW -DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDLL
cmake --build <build>
ctest --test-dir <build> --output-on-failure
```

Locate `runtime/_internal/shapely.libs` beneath the installed OCR resources.
The unchanged Shapely PYDs import a hashed `geos_c-…dll` name. Copy your rebuilt
`geos_c.dll` using that exact imported name, and copy the rebuilt C++ library as
`geos.dll`, the name imported by the rebuilt C wrapper. Move the old GEOS pair
to your backup outside the runtime directory. Do not change the Shapely PYDs.
The `replacement_plan` function in the recipe derives these names from actual
PE imports and rejects non-x64 inputs.

The historical exact-installed replacement test `38021809403` passed both OCR
orientations, dictionary/translation/persistence and loaded replacement DLL hash
checks, then restored every original installed file. Its setup identity and
limitations are recorded in `windows-native-rebuild.md`. It does not approve a
different setup. The historical installed-test script has fixed old setup hashes;
do not run it against a new setup without deliberately updating those bindings.

## NumPy's OpenBLAS and compiler libraries

NumPy 1.26.4 uses the Windows ILP64 OpenBLAS source commit `c2f4bdbb…` and GCC
10.3.0. Their sources, full compiler-runtime licence/exception texts and the
historical `openblas-libs` build helper are included. That helper's pinned
Windows recipe selects the same OpenBLAS commit and records the ILP64 symbol
suffix and architecture options. Rebuild with that ABI, including any modified
LGPL libquadmath implementation, and retain required runtime dependencies.

Replace the OpenBLAS DLL at the exact name imported by NumPy's native extension,
under its installed `.libs` directory. Preserve all other DLLs and PYDs. The
current review still lacks the original vendor ZIP and complete downstream
compiler-patch evidence; source collection does not establish an exact rebuild.
Do not interpret these instructions as closing that public-distribution gate.

## Check and restore

Launch the app and test capture/OCR, dictionary lookup, a previously untranslated
sentence and persistence. Confirm the replacement DLL paths and hashes in a
diagnostic process inventory. The app has no native-DLL hash enforcement;
candidate sealing and installed verification checks identify the shipped bytes
and will deliberately report a locally modified installation. ONNX learning
graph integrity checks are separate from native-library replacement.

If the ABI or dependency check fails, quit the app and restore your backed-up
original DLLs. Never disable Defender, SmartScreen or certificate verification
to make a replacement load. Distributing a modified build requires its own
source, notice and installer review.
