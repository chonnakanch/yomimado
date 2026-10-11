# Windows NumPy prebuilt runtime

The Windows preparation selects NumPy **2.4.6**, with its official CPython 3.11
x64 wheel and original sdist pinned in `services/ocr/windows-inputs.json`.
The macOS NumPy runtime and approved seed are unchanged. Windows parity and
exact-installed tests must pass before this change is considered usable.

This replaces the older Windows NumPy 1.26.4/OpenBLAS input, whose static
libquadmath source/relinking coverage remained unresolved. It requires no NumPy
or Torch source build. The focused OpenCV build uses the selected NumPy headers;
it must be rebuilt for the new ABI rather than reusing the previous PYD.

## Exact binary and source binding

- NumPy wheel SHA-256:
  `1e254a00cdf42b1e4d5b3d68d33af63268d41340d8885df2ab6470f2e1500147`.
- Its BLAS DLL, `libscipy_openblas64_-63c857e738469261263c764a36be9436.dll`,
  has SHA-256
  `63c857e738469261263c764a36be9436ebdeaa272e340a828f42047a97131080`.
  This exactly matches `libscipy_openblas64_.dll` in the official
  **scipy-openblas64 0.3.31.188.0** Windows x64 wheel, SHA-256
  `4958b7fb8dcc5b8312652764acc762f42e7f1cc7269fe5a561b0635ffd1a8601`.
- NumPy's original `requirements/ci_requirements.txt` selects that exact supplier
  version. Its Windows repair recipe copies that supplier library into the wheel.
- The supplier's published tag selects recipe revision
  `2387cb313f653b694d864f2d1d6888a26d7b2ba1`, whose OpenBLAS gitlink is
  `4956446ca26d365f209bf729123349f19dd820b6`. Both preferred source archives,
  full original notices, Windows patch and build recipes are retained.
- `scripts/windows_native_sources.py` verifies the original wheels, matching DLL
  hashes, unchanged original supplier notices and selected recipe files before
  recording this binding in the delivered source preparation.

These bindings identify the binary supplier and tagged build recipe. They do not
claim a byte-for-byte rebuild or a signed build attestation from its publisher.

## Licence scope

The NumPy wheel retains its full original software and vendor licences. Its
Windows BLAS notice names OpenBLAS/LAPACK under BSD terms and the GCC runtime
under GPL-3.0-or-later with GCC Runtime Library Exception 3.1. The retained GCC
10.3.0 sources supply the original full licence/exception texts as well.

The tagged Windows recipe applies `patches-windows/openblas-make-libs.patch`,
remaps the unused quadmath formatting reference to UCRT `snprintf`, and checks
the actual linker map for any `libquadmath.a(...)` contribution. A contribution
fails the supplier build. NumPy's own original licence declaration excludes
Windows from libquadmath's scope, and the exact Windows wheel contains no
libquadmath notice or separate DLL. This resolves the old static-libquadmath
delivery concern through the documented replacement input, subject to verifying
that the exact new installed DLL is the pinned supplier binary.

Original notices remain unmodified. The supplier notice is additionally copied
into installed notices. The recipes and source inputs are available from
[NumPy 2.4.6](https://github.com/numpy/numpy/tree/v2.4.6) and the
[tagged supplier](https://github.com/MacPython/openblas-libs/tree/2387cb313f653b694d864f2d1d6888a26d7b2ba1).
This review does not approve unrelated Microsoft runtime inputs, the complete
Windows source gate, or the human installer gate.

The delivery manifest now also retains the actual NumPy 2.4.6 sdist, rather
than treating the export-only NumPy 1.26.4 source as runtime coverage. The original
archive has SHA-256 `f3a3570c4a2a16746ac2c31a7c7c7b0c186b95ce902e33db6f28094ed7387dda`;
the canonical preferred tree is
`3b5105c1dcec720e6ccd5ee2a5ac938cfa1d214aee1f30b3c57e92034580e4a1`.
All 25 original notice files are pinned and preserved. Metadata from the exact
wheel and original sdist must agree on NumPy 2.4.6. The 116 omitted inputs are
test/media/prebuilt files, retained by path/hash in the preparation record;
preferred code and recipes are unchanged. These bytes and checks pass locally;
final installed notice/source-archive verification remains required.
