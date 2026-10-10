# Windows native source work remaining

This is an execution worksheet for the public-distribution gate, not an
approved source delivery. Individual results below distinguish passing
isolated checks from unrun full-runtime builds and replacement tests.
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

Prepared on 2026-10-09: **Windows Torch source audit**
(`.github/workflows/windows-torch-audit.yml`) performs an independent native
CPU build with the pinned Windows CPython/MSVC/SDK and CMake/Ninja tools.
[Its input record](windows-torch-build-inputs.json) binds the original PyTorch
commit and fourteen selected CPU/header source repositories to the parent's exact gitlinks,
with hashes for 31 original tracked licence/notice files. Source checkouts do not
use floating branches or initialize unused GPU/mobile dependencies. The build
checks the accepted Eigen/CPU CMake cache and generated compiler commands before
compilation; Windows upstream mimalloc remains a recorded source dependency.

The previously missing Eigen input is upstream's pinned **3.4.0**, exact commit
`3147391d946bb4b6c68edd901f2add6ac1f31f8c`. Its original GitLab archive is
downloaded and verified locally, SHA-256
`0c8c490764f9c2a793133491adca0cd073b73e0bde965c68cbe58d91b5ed4261`.
The record preserves eight full original licence files, including MPL, BSD,
Apache, LGPL and GPL texts. Upstream describes MPL-only header selection through
`EIGEN_MPL2_ONLY`; the recipe requires that guard in actual compiler commands.
This does not approve every Eigen file for binary inclusion or remove notice
requirements. The native build uses unchanged preferred sources and upstream
packaging after CMake installation, with separately pinned build tools.

The proposed probe verifies CPU matrix multiplication, convolution and attention,
all Torch PE architecture/imports, disabled MKL/OpenMP/oneDNN/CUDA, and the actual
loaded paths/hashes of `torch_cpu.dll`, `torch_python.dll` and `c10.dll` from the
source-built wheel. Only textual inputs/commands/logs/notices/results leave the
runner. This build is unverified until hosted execution succeeds; model inference,
frozen service and exact installed OCR replacement
remain separate gates. No tested installer or macOS runtime is changed.
First [run `37939801320`](https://github.com/chonnakanch/yomimado/actions/runs/37939801320)
at `61143751c5c79238acfcb57df15c37f9cc8492bc` builds pinned CPython,
verifies all selected source commits/notices, downloads the pinned Eigen/tool
inputs and reaches Eigen CPU configuration. CMake FindPython then cannot read
`Include/pyconfig.h`; Windows CPython retains that original file under `PC`.
The recipe now stages unchanged original Python headers with `pyconfig.h`,
records their hashes and the CPython build-record hash, and uses that staged
include directory. Optional SLEEF SSL/MPFR/FFTW testing and host OpenMP/OpenSSL
discovery are explicitly disabled. The downloaded first-run textual evidence
ZIP (ID `11620263065`, 171,654 bytes) matches GitHub SHA-256
`9652640a457a714e9f0dd5af1224cd512666d9a4f042b1d62c530ad52ab0b9cf`.
No Torch compilation or inference pass is claimed from that run; a complete
rerun is required.
Run `37941035678` at `9e08202bc782114227612c13ccf14f1996271f37`
resolves Python header discovery and reaches CMake generation, then fails because
the unconditional OpenTelemetry API include target lacks its preferred source.
The source selection now also pins OpenTelemetry, cpp-httplib, nlohmann-json and
FlatBuffers to the exact parent gitlinks and preserves their original notices.
These existing upstream header dependencies are retained without adding product
telemetry or a new feature. Upstream wheel-stub compilation now also preserves
the selected MSVC/SDK and receives the original Python headers/import-library
paths. Compilation and CPU probe results remain unverified until a full run passes.

Run `37941928033` at `64ab5de2d18f77c27e324c95ac9c7a5ef84d593f`
stops at OpenTelemetry notice verification before configuration. Its `text`
attributes let Windows' native line ending alter the checkout despite
`core.autocrlf=false`. Checkout now also selects `core.eol=lf`; strict original
notice hashes remain required. Downloaded textual evidence (ID `11623090010`,
63,583 bytes) matches GitHub SHA-256
`a8eeb9259e6a8aa996035a06b4368e5a4336aace77eeddaf52ce23b2f7e8327e`.

The same isolated audit now prepares matched **torchvision 0.23.0+cpu** from
preferred commit `824e8c8726b65fd9d5abdc9702f81c2b0c4c0dc8`.
[Its input record](windows-torchvision-build-inputs.json) binds original setup and
BSD licence bytes. A recorded minimal patch removes unused image/video extension
builders while retaining CPU `_C` operators and Pillow-backed Python transforms.
The runner preserves that exact patch, original full licence, pinned Pillow
notices and wheel hash. The probe requires the expected Torch/vision source
identities, CPU NMS selection, synthetic resize/tensor/normalization output,
AMD64 imports and the actual loaded `_C.pyd` hash. Existing binary wheels are
not assumed compatible with the new Torch. These source-built probes and the
full frozen OCR/installer remain unverified until hosted execution succeeds.

Run `37943467439` at `bba93e491f1d6198285917a3cec9bacf3840cd1c`
verifies all selected sources/notices and generates the Eigen CPU build. Its
compiler guard incorrectly treats four protobuf Windows `.rc` resource commands
as C/C++ compilation. The corrected guard explicitly separates resources, while
requiring the MPL-only Eigen define and release DLL runtime on every C/C++
command and rejecting unexpected source types. Local inspection of the retained
cache and commands passes for 1,726 C/C++ and four resource commands. No native
compilation or Torch/vision inference pass is claimed. The downloaded textual
evidence (ID `11622408001`, 309,825 bytes) matches GitHub SHA-256
`bb87076217c46562b72b6acb766516b1a3ddf82757c5a41ebcab7598b4fdeaa5`.
The matched torchvision recipe's Pillow notice pins are stored explicitly in
its own input record: the general Windows package manifest does not have a
`licenseFiles` field. Original Windows Pillow wheel and aggregate notice hashes
are verified locally; changed or absent notice pins fail closed. This corrects
the preparation recipe before its first successful torchvision execution.

Run `38015437061` at `3f2866d8dac6d82cb08f59cc6f8dde8735616ece`
verifies the preferred sources, notices and compiler guards, then fails native
compilation at `caffe2/core/common.cc` (build command 1015 of 1805). The retained
`CMAKE_CXX_FLAGS` contains a quoted `/I` path; upstream substitutes it unchanged
into the `CXX_FLAGS` entry of `CAFFE2_BUILD_STRINGS`, breaking the generated C++
string. The source-built Python headers already include original `pyconfig.h`
and are supplied through `Python_INCLUDE_DIR` and `INCLUDE`. The recipe removes
the redundant flag, preserves the MPL guard and compiles the original
build-options consumer before starting the long complete build.
A local C++ check using the exact pinned upstream template reproduces the old
syntax failure and passes with corrected flags; this does not establish MSVC
execution, a completed Torch wheel or inference. The rerun remains required.

Downloaded textual evidence (ID `11658066026`, 326,496 bytes) matches GitHub
SHA-256 `4ea1ffa0d388dfa0d0265a2c4947d41d3c9898abc175d01a207fdc4e95c1a6e5`.
The input record, all fifteen repository revisions, 31 original repository
notices, eight Eigen notices, accepted CMake cache and 1,726 C/C++ plus four
resource commands verify locally. No completed Torch/vision probe or installed
replacement pass is claimed. Reports remain private under
`services/ocr/build/windows-torch-run-38015437061/`.

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

### Independent Windows OpenCV execution

Prepared on 2026-10-09: **Windows OpenCV source audit**
(`.github/workflows/windows-opencv-audit.yml`) builds the exact original
`opencv-python-4.11.0.86` source's OpenCV tree with source-built CPython 3.11.17,
MSVC 14.44.35207, SDK 10.0.26100.0, CMake 3.31.6 and Ninja 1.11.1.4.
[The input record](windows-opencv-build-inputs.json) binds the original source
and full selected vendor licence hashes. No macOS binary approval is reused.

The static x64 PYD retains core/image/geometry/DNN and the detector's `imshow`
import; GUI backends, videoio, FFmpeg, IPP/IPP IW, OpenMP, OpenCL and CUDA are
disabled. The accepted CMake cache and actual build information must verify
those settings and the exact four static vendors (protobuf, JPEG, PNG, zlib).
Unrecorded vendor downloads are rejected. Source code is unchanged; the recipe
retains full selected vendor texts and module-level source notices separately.

The audit executes original synthetic horizontal/vertical shape geometry,
homography and PNG/JPEG checks. It also loads the hash-pinned detector as a
temporary external input and runs CPU ONNX inference on both original synthetic
text fixtures. It repeats those checks in a disposable PyInstaller build,
verifies the unchanged source-built PYD bytes and actual loaded paths/hashes,
and rejects Intel/CUDA/video dependencies. This is a native/frozen detector
probe, not full OCR recognition, installed-app replacement or source clearance.
Only JSON/log/cache/notices text is uploaded; no binaries, weights, installer,
tag, publication or approval is produced. The maintainer-tested setup is unchanged.
First [audit run `37933246289`](https://github.com/chonnakanch/yomimado/actions/runs/37933246289)
at `81988bb07121e9bb08c2cdaee4b8ee649a8dc685` builds CPython and verifies
source/tool inputs, then fails OpenCV configuration: OpenCV expands the native
Python library path through a CMake expression, interpreting `D:\\a` as an
invalid escape. The recipe now normalizes all CMake path values to forward
slashes, with a regression check for Windows paths containing spaces. No
OpenCV compilation or inference pass is claimed; the complete rerun is required.
Torch replacement and full installed OCR remain separate.
Corrected [run `37934320710`](https://github.com/chonnakanch/yomimado/actions/runs/37934320710)
at `3be03080dc59cbd16868da35e51a65b3697a9eb6` passes compilation, native
and frozen geometry/image checks and CPU detector inference on both fixtures.
The textual artifact (ID `11618091892`, 115,832 bytes) is downloaded and verified
against GitHub SHA-256
`94cfa98529913d471e886d94b89661483f94073d22a3f5c76ad7049b7e71d07d`.
Recipe/probe/cache/full-notice hashes match; native and frozen detector/geometry
results match, and both load the same AMD64 PYD bytes
`b10865944723640e72b482613894730f376d71ba65cb51d0652efd1cccbc8f37`.
Its imports are only `kernel32.dll` and `python311.dll`; IPP removal passes.
However, archive inspection reveals **`BUILD_WITH_STATIC_CRT=ON`** despite the
requested `CMAKE_MSVC_RUNTIME_LIBRARY`. This run does not validate the proposed
DLL compiler-runtime linkage. The recipe now explicitly disables static CRT,
retains and checks all generated C/C++ compile commands for Release `/MD`
(rejecting `/MT` and debug runtime flags), and requires a VC runtime PE import.
Run `37936508507` at `1ea0b33b932b5ef1f8beb7c8e13758cb9b3f699b`
reaches the corrected configuration but rejects CMake's actual `-MD` spelling
before compilation. Its evidence ZIP (ID `11618732565`, 58,320 bytes) matches
GitHub SHA-256 `9d9401647e1de2a59d8ed3f1798748ac6884134194fa3c300dc0644019f5d0c0`.
All 648 retained C/C++ commands use Release DLL runtime. The verifier now accepts
both MSVC flag prefixes and still rejects static/debug forms with either prefix;
compilation, PE imports and frozen inference still require the corrected rerun.
Reports stay private under
`services/ocr/build/windows-opencv-run-37934320710/`. No installer is modified.

Corrected [run `37938195277`](https://github.com/chonnakanch/yomimado/actions/runs/37938195277)
at `23ad7f119cf99881aa634855f4394e6b45deac02` passes the complete audit.
Its evidence ZIP (ID `11621171125`, 141,038 bytes) is downloaded and independently
verified against GitHub SHA-256
`8880f575652c84d5200719ef4b65c60cf9651b051efeafb9fcdab39fd8145fbf`.
Recipe/probe/cache/compile-command hashes and all ten retained full notice texts
match. All **648** actual C/C++ commands select Release DLL runtime, the cache
disables static CRT, and the AMD64 PYD imports `vcruntime140.dll`,
`vcruntime140_1.dll`, `msvcp140.dll`, `concrt140.dll` and Windows UCRT APIs.
Native and frozen probes load the unchanged PYD SHA-256
`f2ac973b04cd0c2b5f4708f247eb1004bc2562ffe6bfa53aa5caaea5d6781f93`
from their expected locations; both fixtures' geometry and CPU detector outputs
match. IPP-free OpenCV with DLL compiler-runtime linkage now passes this isolated
audit. Full installed OCR, final compiler/source/notice clearance and delivery
remain open. Reports stay private under
`services/ocr/build/windows-opencv-run-37938195277/`.

Local verification: 135 release-script tests pass, including rejection of unsafe
source extraction, enabled IPP/backends, wrong loaded PYD paths/hashes and wrong
probe architecture/version. Synthetic image geometry runs on the development
Mac; that does not claim Windows execution. Python lint/format, workflow lint
and YAML/JSON/document formatting pass.

## GEOS source and library replacement

Independent execution prepared on 2026-10-09: **Windows GEOS source audit**
(`.github/workflows/windows-geos-audit.yml`) builds the pinned GEOS source with
source-built CPython 3.11.17, MSVC 14.44.35207, SDK 10.0.26100.0,
CMake 3.31.6 and Ninja 1.11.1.4. Original source/tool checksums and build-tool
licence hashes are in [the input record](windows-geos-build-inputs.json).
It runs upstream CTest, freezes a disposable Shapely 2.0.7 geometry probe,
then replaces both GEOS libraries using the unchanged extensions' actual
import names. Synthetic intersection/union, validity repair, rotated bounds,
prepared geometry and vectorized operations must match the baseline;
loaded DLL paths/hashes must identify only the replacement libraries.
The C wrapper retains the imported hashed name and loads the new `geos.dll`.
Only textual build/source/replacement diagnostics are exported. Neither
installer resources nor the current candidate are modified; no binary,
weights, tag, publication or approval is produced.
Even a passing isolated probe does not establish replacement in the full
installed OCR service or final corresponding-source/licence clearance.

First [audit run `37876379469`](https://github.com/chonnakanch/yomimado/actions/runs/37876379469)
at `ac10c48f41a8546d0dfe1c09a83bfd875ff81ffa` builds CPython and GEOS,
passes upstream CTest and freezes the probe. It fails the baseline loaded-module
assertion: the collector also selects its own `geos-probe.exe`, whose name starts
with `geos`. The collector is corrected to accept DLLs only, with a regression
test. Actual rebuilt-library replacement is still unverified; the complete
rerun must pass before recording that result. Original source and Ryu licence
hashes are additionally pinned and checked without changing the GEOS source.

Corrected [audit run `37877467511`](https://github.com/chonnakanch/yomimado/actions/runs/37877467511)
at `a10db77ec91d5e1e0f96f444b0a98376c641774a` **passes** source/tool/notice
checks, CPython and GEOS builds, upstream CTest, original-wheel byte binding,
baseline and replacement synthetic geometry, unchanged EXE/PYD hashes, and
actual loaded replacement DLL paths/hashes. This is Windows Server 2022 x64
execution of an isolated frozen probe; it does not cover the full installed
OCR service, Windows 11 hardware, source-delivery approval or the installer gate.
The current `c69eff996f7e` private installer is unchanged.

Its textual `windows-geos-source-evidence` artifact (ID `11593186615`, 45,079 bytes)
has GitHub SHA-256
`63d92c5663d0f77f9a57386297d02cd0fff92487237d827a953f6d6d8fcc0291`.
It retains the CMake cache, commands, upstream test/build logs, original notice
hashes and `replacement-verification.json`, including both DLL digests and
actual loaded paths. This is an evidence ZIP hash, not an installer or DLL hash.
The evidence ZIP is downloaded and hash-verified locally on 2026-10-09.
Its reports bind the recipe/probe hashes to the exact source revision and the
CMake cache hash to its retained bytes. CTest records **431 of 431 tests passed**.
Both reports contain matching geometry fingerprints; the replacement report's
actual loaded DLL hashes match both AMD64 PE records. The C wrapper imports
`geos.dll` under its recorded replacement name. Reports are retained privately
under `services/ocr/build/windows-geos-run-37877467511/`. Final source delivery
must retain those reports, original sources and full notice texts together;
archive inspection does not approve the full installed-service replacement.

Prepared follow-up on 2026-10-09: the audit is configured to download the exact unchanged
`c69eff996f7e` private setup through a read-only Actions token, verifies the draft,
provenance and setup hashes, and installs it on a disposable runner. Signed
asset redirects strip authentication headers. All installed resource hashes and
AMD64 payloads must verify before replacement. The baseline and replacement
each run real horizontal/vertical OCR, tokenization, dictionary/kanji, uncached
translation and saved-data/cache restart without developer Python/CUDA on the
service PATH. Actual loaded GEOS paths/hashes must identify the expected pair.
An exhaustive installed-file comparison permits only the exact two-library plan;
EXE/PYDs/assets remain unchanged, and the original libraries are restored even
after a smoke failure. Original GEOS/vendor notice texts now accompany textual
evidence. No installer is rebuilt, uploaded or published. Hosted installed-service
replacement execution remains pending. Run `37935912253` at
`082b241d6b24f127bbfd632b8b37f969e951b039` passes the source build, upstream
tests and isolated replacement, then cannot find the draft in its read-only
token's release listing. No installer is downloaded or replaced in that run.
GitHub's [release API documentation](https://docs.github.com/en/rest/releases/releases#list-releases)
requires push access to include drafts in listings. Earlier direct tag preflights
(including `37938465690` and the approved run `38016752910` at `485c672`)
used the wrong lookup: GitHub documents
[Get a release by tag name](https://docs.github.com/en/rest/releases/releases#get-a-release-by-tag-name)
for published releases. Those failures do not establish that the configured owner
token lacks draft access. The corrected preflight resolves the exact unpublished
identity through the authenticated release listing, rejects missing/duplicate or
incomplete listings, and validates the declared setup/provenance digests before
building. It retains a fixed, credential-free diagnostic JSON and error annotation
even on early failure; no response bodies, headers or exception text are exported.
The existing protected environment check and maintainer approval passed in
`38016752910`; corrected draft access and installed replacement still require a
passing hosted run. Keep token permissions unchanged while testing this correction.
The correction is commit `220bd0bf2d9e4fce616cb8f70b7059e107451a01`;
[run `38017337839`](https://github.com/chonnakanch/yomimado/actions/runs/38017337839)
passed the protected environment check and received the maintainer's approval.
Attempt 1 stopped because the environment secret was missing or empty; the owner
corrected its placement from environment variables to environment secrets.
Attempt 2 now reaches the authenticated release listing but cannot see exactly
one matching private draft. This exposed an external input-access blocker:
confirm the token selects this repository and that the exact draft above still
exists before proposing any permission change. GitHub requires push access for
draft listings; token presence and successful public listing alone do not prove
draft access. No GEOS source rebuild, installer download or installed replacement
had executed in attempt 2. All 148 release-script tests,
Python lint/format, documentation formatting and workflow syntax pass locally;
the reviewed macOS release-seed reuse check still passes.
On 2026-10-10 the owner confirms the exact old draft opens while signed in and
explicitly authorizes a replacement token with **Contents: read and write**,
restricted to this repository, with **Workflows disabled**. This credential has
repository/release write capability; the reviewed GEOS consumer still performs
only GET requests. The owner updated the environment secret and reran the
unchanged audit. This permission approval does not approve source delivery,
publication or the final installer.

Attempt 3 (job `114117016340`) passes protected draft access, the GEOS source
build, all **431** upstream tests and isolated frozen replacement. The exact
installed-service step fails before producing baseline/replacement evidence.
Its downloaded textual artifact (ID `11657354146`, 61,130 bytes) matches GitHub
SHA-256 `fdc55cef0f8163c317591e75b2c810b686cfaea9688e8cc9b919f5f5d142279f`.
Recipe/probe/cache hashes, retained full notices, matching geometry fingerprints
and both actual AMD64 replacement DLL paths/hashes verify locally. The artifact
has no exception log for the installed step; no installed pass is claimed.

Local inspection identifies a definite historical-input mismatch: the verifier
compares the old setup with today's changed `windows-inputs.json`. The original
`c69eff996f7e` source bytes and retained tested inventory agree on manifest
SHA-256 `1e75e22fa08eec1589cc517b6dbf9a88af6f043e6a3a74733a36f814103141cc`;
the unchanged original asset manifest is
`c5f745cfcfdd0f30fb11eeb52467c373bea9386b34a24ecd8fefe753e76e5878`.
The historical audit now explicitly requires those two hashes. New candidate
verification still requires current inputs; file sealing, exact assets, AMD64
native inventory and import checks remain enforced in both cases. The installed
audit now retains fixed phase/error-type/HTTP-status diagnostics without response
bodies or signed URLs, and writes its passing verification only after exact
original-file restoration. These fixes require a reviewed Windows rerun.
All 151 local release-script tests pass, including rejection of changed/partial
historical manifests, asset tampering and mixed architecture. Reports stay private
under `services/ocr/build/windows-geos-run-38017337839/`.

Reviewed rerun `38020734338` at `d2b52dde989c91cbbbf548a198e7be3d03ec2102`
passes private input access, all 431 CTest cases, isolated replacement and the
exact original installed-service OCR/learning/persistence smoke. It then fails
with `KeyError` during the replacement file comparison; original installation
restoration verifies exactly. Downloaded artifact `11658466939` (69,883 bytes)
matches GitHub SHA-256
`df5bc169f2e520604e7985d6d260fe3ee7246ecdc3246a534540937b23103269`.
Recipe/probe/cache and all five retained full-notice hashes verify locally.
The failure is in the audit's path keys: the snapshot preserves `Shapely.libs`
while the replacement plan addresses `shapely.libs`. Windows accepts both paths,
but the Python dictionary rejects the differently cased removal key. The audit
now normalizes all installed relative keys consistently, rejects case collisions
and still compares every file hash. Regression tests reproduce the casing mismatch
and retain rejection of unrelated application changes. Installed replacement
remains unverified until the corrected reviewed rerun passes. Reports stay private
under `services/ocr/build/windows-geos-run-38020734338/`.

The workflow now prepares a dedicated protected input consumer. Its read-only
plan validates the existing environment before a Windows deployment can be
created; an absent, unprotected, bypassable or wrong-branch environment fails
closed. The Windows job keeps `contents: read` and uses the environment's
separate owner token only for private draft GET requests. The exact
setup/source/provenance checks above remain required. This is private input
access approval, not publication, source clearance or the human installer gate.

Owner setup required in GitHub Settings (no credential in chat or git):

1. Create environment **`windows-native-input`**, add the maintainer as a
   required reviewer, disable administrator bypass and permit only the branch
   **`develop`** through selected branch rules. No tag rules or wildcard branches.
2. Create a short-lived fine-grained owner token restricted to this repository
   with the explicitly owner-authorized **Contents: read and write** scope;
   leave **Workflows disabled**. Store it only as the environment secret
   **`WINDOWS_PRIVATE_INPUT_TOKEN`**. Its owner identity must have existing push
   access for draft visibility. The initial Contents-read token did not expose
   the draft; this broader scope was approved separately as recorded above.
   Verify the exact name under this environment's **Environment secrets**,
   not its variables; an empty or missing value fails before any private API call.
3. A focused push to the audit's `develop` paths starts the workflow. Review the
   resulting run's exact source revision and the private setup hash above, then
   manually approve **only this private-input deployment**.
   The agent must not approve it. The preflight must see the unchanged draft;
   then the build and installed OCR replacement checks can execute.
   For environment-only changes, use **Re-run all jobs** on the latest existing
   audit run (which retains its recorded source revision), or request a verified
   `develop` push. GitHub's **Run workflow** UI button requires the workflow on
   the default branch; it is currently absent because this audit is only on
   `develop`. Do not merge to `main` or change the default branch for this button.
4. Remove/revoke the input token after testing. The protected publication
   environment and final exact-installer approval remain separate.
   Local guard tests reject changed
   application files, wrong candidate/gates, missing learning/native evidence and
   credential-bearing or unexpected asset redirects. Preflight tests also reject
   hidden/duplicate drafts, incorrect declared assets and leaked failure credentials.

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
these changes. The isolated Windows source build/replacement audit now passes
as recorded above; full installed OCR replacement and final delivery remain open.

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
  The Windows notice recipe now preserves seventeen original supplemental
  licence/patent texts from pinned AOM, dav1d, libyuv and libwebp sources; all
  copies verify locally. This resolves missing-text preparation, not exact
  static linkage or installed notice delivery. See the source review.
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
