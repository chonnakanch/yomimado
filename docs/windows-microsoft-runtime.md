# Windows Microsoft runtime review

Reviewed 2026-10-11. Status: conditional redistribution evidence remains open.
This records actual inputs and the remaining decisions; it does not accept a
Microsoft agreement for the maintainer or approve an installer.

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

Owner response — 2026-10-11: the maintainer first answered **No, or unsure**,
then confirmed acceptance of the linked Community 2022 terms. On clarification
they report **Only accepted the linked terms so far**; no obtained copy or
installed edition/version is claimed. The applicable licensed-copy requirement
therefore remains open. Public redistribution remains blocked. The
[component notice draft](windows-microsoft-distribution-notice.draft.md) identifies
the exact files and owner completion steps; it is not an agreement and is not
enabled as an installer licence page. The maintainer must establish their grant
and review/satisfy the Microsoft-specific end-user/distributor requirements.
The maintainer confirms this exact setup hash and all listed local tests,
including corrected alignment at 100%/125%/150%. The local test checklist is
complete; [untested hardware cases](windows-installed-test.md) remain explicit.
Protected publication approval remains open.

Owner acquisition route — checked 2026-10-11: Microsoft's
[2022 release history](https://learn.microsoft.com/en-us/visualstudio/releases/2022/release-history#evergreen-bootstrappers)
still lists the Community bootstrapper on Current 17.14. The maintainer can
obtain this edition and review/accept its terms on their Windows PC. The
[Community terms](https://visualstudio.microsoft.com/license-terms/vs2022-ga-community/)
allow individual developers to develop their own applications; the edition is
free. Obtaining a validly licensed copy, not paying for a licence or holding a
Windows OS licence, is the remaining owner step. Do not substitute the newer default download without
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

1. Obtain the applicable licensed copy and satisfy its
   distribution/end-user requirements specifically for Microsoft components.
   Do not impose proprietary restrictions on YomiMado's GPL code. An alternative
   is a separately installed official Microsoft prerequisite, with proper clean-PC
   detection and installed tests; that packaging path is not implemented here.
2. Review [the concrete component terms draft](windows-microsoft-component-terms.draft.txt),
   resolve its explicit review items, then include approved component-specific
   terms/acceptance and notices;
   any changed installer must repeat the passing canonical VC, source-only
   WebView loader, embedded plugin and source/notices delivery checks.
3. Obtain fresh maintainer installed-app confirmation if terms or packaging
   change the setup, then protected release approval. The current exact setup's
   automated and listed local checks pass. Keep it private while the owner
   entitlement and component terms are unresolved.

These gates are concrete distribution checks. No long Torch build, paid code
signing requirement or self-approved installer gate is introduced.
