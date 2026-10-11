# Windows Microsoft runtime review

Reviewed 2026-10-11. Status: conditional redistribution evidence remains open.
This records actual inputs and the remaining decisions; it does not accept a
Microsoft agreement for the maintainer or approve an installer.

Component-terms verification — 2026-10-11: [run `38142782743`, attempt 4](https://github.com/chonnakanch/yomimado/actions/runs/38142782743)
at `f8396cc` passes all hosted gates. Setup SHA-256:
`756b7dc6003af202e4df95e946edcbc7fe409c41cfd0d2fc3be4062f758b4a1b`.
All four missing/wrong silent/passive acceptance cases exit with code 2 without
installation; interactive decline starts unchecked with Next disabled and writes
no app files. Successful exact installation records the pinned terms hash.
Canonical VC originals, static installer runtime, embedded plugin and WebView
loader bindings pass. Downloaded evidence and delivered terms/source/notices
digests verify in [the source review](windows-source-review.md).
The remaining owner step is fresh local confirmation of this changed installer
and protected publication review, rather than another licensed-copy request.

Final technical verification — 2026-10-11: [run `38133593809`, attempt 2](https://github.com/chonnakanch/yomimado/actions/runs/38133593809)
at `8c46366d04e96d5356c250605e7ea936db209eb3` passes all installed startup, UI,
learning and persistence gates. The exact setup SHA-256 is
`7ff298c597de9c33d23bb598bf16d6f41761219e51fc0b61951ed6c54174c6d9`.
Its ten desktop VC DLLs and standard/renamed frozen-service copies match the
canonical unchanged VC143 **14.44.35211.0** originals. The source-only MIT
WebView loader's recipe/static-library binding passes for all Cargo outputs
and the installed desktop EXE. Its BSD SDK headers/notices remain retained.
The short source-built NSIS plugin passes upstream tests and exact embedded
DLL verification, with static compiler runtime linkage and no dynamic VC imports.
Downloaded diagnostic artifact `11701215883` matches GitHub's SHA-256
`4b2267a29f12e16f8ad07d258542b4afb150e505ac1e1230b974bc78774fb6f8`.
These results resolve technical identity/integration gates, independently of
contractual permission.

Owner response — 2026-10-11: after initially only accepting linked terms,
the maintainer directly confirms downloading Visual Studio Community 2022 and
accepting its terms. [The manifest](windows-microsoft-terms.json) records this
owner attestation without an independently verified installed version or account
details. The licensed-copy confirmation is complete. Public redistribution still
requires fresh exact-installer confirmation and protected human review.
[The Microsoft-only terms](../THIRD_PARTY_LICENSES/windows-microsoft-components.txt)
are now selected by the Windows-only configuration, retained in source/notices
and hash-bound in the NSIS build record. Interactive setup requires affirmative
checkbox acceptance; silent/passive setup requires the exact terms hash in
`/ACCEPTMSRUNTIME=` and otherwise exits with code 2. Successful installation
records the hash in its per-user uninstall key; uninstall removes that key.
Windows Actions checks rejection/cancel and the exact installed acceptance hash.
The changed package passes hosted execution and awaits new exact-installer review.
The maintainer confirms the previous `7ff298c5…` setup hash and all listed local tests,
including corrected alignment at 100%/125%/150%. The local test checklist is
complete; [untested hardware cases](windows-installed-test.md) remain explicit.
Protected publication approval remains open.

Owner acquisition route — checked 2026-10-11: Microsoft's
[2022 release history](https://learn.microsoft.com/en-us/visualstudio/releases/2022/release-history#evergreen-bootstrappers)
still lists the Community bootstrapper on Current 17.14. The maintainer can
obtain this edition and review/accept its terms on their Windows PC. The
[Community terms](https://visualstudio.microsoft.com/license-terms/vs2022-ga-community/)
allow individual developers to develop their own applications; the edition is
free. The owner's obtained-copy/acceptance confirmation above completes that
step; no paid licence or Windows OS licence proof is requested. Do not substitute the newer default download without
reviewing its applicable terms. Record only edition, version and acceptance
date/confirmation; no account information or key is needed.

The dated input history below does not supersede these current results.

The successful provenance run `38071435853` at `4badc93` is independently
verified: artifact `11676279560` has SHA-256
`d2aec89a9b6c75e0249cac835c257a9055131faccde93eecddab93f9a127b7df`.
None of the six historical files matches the runner's canonical REDIST copies.
The private recipe now selects [exact VC143 originals](windows-vc-runtime-inputs.json),
version **14.44.35211.0**, from `14.44.35112/x64/Microsoft.VC143.CRT`.
It replaces existing standard/renamed runtime inputs without altering any PE
bytes, follows normal/delay-loaded VC dependencies, and retains every original
and replacement hash. Inventory binds the replacements to canonical originals.
Run `38104876515` now verifies the installed canonical replacements, including
the ten desktop copies and standard/renamed service inputs. Its downloaded
evidence `11689928315` matches SHA-256
`cd0698778aff9f54d252ce85fbc339616fa8b8ae0279b4404b472a806fcf4626`.
Startup, cleanup and frozen ONNX learning pass, while page-scan cancellation
fails its UI gate. Provenance is separate from contractual redistribution
permission; that diagnostic setup is not approved for release.

## Actual files and canonical inputs

The verified historical ONNX inventory from run `38066505590` contains six
Microsoft VC runtime DLLs. [The reference record](windows-vc-reference.json)
preserves every installed path and SHA-256, bound to diagnostic artifact
`11675597657`. The freezer obtained several from Visual Studio tool/IDE
directories and others from hosted Python. Shapely supplies a renamed
`msvcp140` DLL. Its original PE version information identifies **14.29.30158.0**;
its name alone does not establish that it is an unchanged redistributable.

**Windows VC runtime provenance** performs a short, read-only inspection of
the hosted image's canonical `VC/Redist/MSVC/*/x64/Microsoft.VC*.CRT/` files.
It records SHA-256, original filename, file version and AMD64 headers, then
compares these bytes with the reference inventory. It executes no DLL, changes
no runtime and uses no private-input credential. A match establishes canonical
input identity, not the maintainer's contractual entitlement. Missing matches
must be resolved from an exact original distribution or a tested replacement;
a matching product/version string is insufficient.

The final run above supplies its own NumPy 2.4.6/Sudachi installed inventory
and exact archive verification. Historical comparison alone does not approve
new files or confer redistribution rights.

## Separate redistribution and GPL questions

Microsoft's [2022 redistribution list](https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution)
permits licensed Visual Studio users to distribute specified, unmodified VC
runtime files, subject to that edition's terms. Debug/non-redistributable files
are excluded. This is conditional permission; copying a DLL from the runner is
not itself proof that all conditions have been met.

The [Community 2022 agreement](https://visualstudio.microsoft.com/license-terms/vs2022-ga-community/)
allows individual application development and OSI open-source development. Its
distribution provisions require application functionality and appropriate
protection for the Microsoft Distributable Code. They prohibit subjecting its
source code to an Excluded License. The downloaded original English DOCX has
SHA-256 `41a207b10c8ab91d0d2f10a854715f73dca54509581692d2fe179aa3ffcb8540`.
No purchase of a Windows app publishing licence follows from these provisions;
the distributor still needs an applicable grant and compliance with its terms.

GPLv3 section 1 excludes qualifying System Libraries from Corresponding Source.
Its definition includes libraries normally packaged with the compiler, serving
the specified compiler or standard-interface role. The [FSF's GPLv3 guide](https://www.gnu.org/licenses/quick-guide-gplv3.html)
expressly describes distributing a GPL program together with incompatible
System Libraries. Its [Windows runtime FAQ](https://www.gnu.org/licenses/gpl-faq.en.html#WindowsRuntimeAndGPL)
also recognizes VC runtimes as System Libraries, but then states a broader
restriction on bundled DLLs. That paragraph conflicts with the guide and does
not justify a blanket claim that every GPLv3 installer must provide Microsoft
runtime source. Apply the actual GPLv3 text and identify each component's role;
this does not make application libraries such as Intel MKL/IPP System Libraries.

## Remaining public gates

1. Verify the changed installer in Windows Actions: unchecked interactive
   acceptance, cancellation before writes, missing/wrong silent/passive assent,
   installed acceptance hash, canonical VC inputs, source-only WebView loader,
   embedded plugin, source/notices and existing installed runtime checks.
2. Review the exact component terms and new installer, retaining the distributor
   obligations and separate GPL rights. No blanket legal approval or upstream
   agreement acceptance on anyone's behalf is claimed.
3. Obtain fresh hash-bound maintainer installed-app confirmation and protected
   release approval before joint publication. Setup `7ff298c5…` retains its passing
   report; it does not cover the new component-terms installer.

No long Torch build, paid code signing requirement or self-approved installer
approval is introduced.
