# Windows Microsoft runtime review

Reviewed 2026-10-11. Status: conditional redistribution evidence remains open.
This records actual inputs and the remaining decisions; it does not accept a
Microsoft agreement for the maintainer or approve an installer.

The successful provenance run `38071435853` at `4badc93` is independently
verified: artifact `11676279560` has SHA-256
`d2aec89a9b6c75e0249cac835c257a9055131faccde93eecddab93f9a127b7df`.
None of the six historical files matches the runner's canonical REDIST copies.
The private recipe now selects [exact VC143 originals](windows-vc-runtime-inputs.json),
version **14.44.35211.0**, from `14.44.35112/x64/Microsoft.VC143.CRT`.
It replaces existing standard/renamed runtime inputs without altering any PE
bytes, follows normal/delay-loaded VC dependencies, and retains every original
and replacement hash. Inventory binds the replacements to canonical originals.
The next Windows installed test must verify this replacement; provenance is
separate from contractual redistribution permission.

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

The forthcoming NumPy/Sudachi candidate needs its own installed inventory.
The historical comparison does not silently approve new files.

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

1. Verify the new candidate's actual VC DLLs against unchanged canonical
   distributable inputs, with exact versions and notices. The prepared recipe
   replaces the old Shapely copy and tool-directory inputs; its installed
   execution remains pending.
2. Establish the maintainer's applicable redistribution grant and satisfy its
   distribution/end-user requirements specifically for Microsoft components.
   Do not impose proprietary restrictions on YomiMado's GPL code. An alternative
   is a separately installed official Microsoft prerequisite, with proper clean-PC
   detection and installed tests; that packaging path is not implemented here.
3. Finish the WebView2 SDK loader assessment separately. Its exact BSD licence,
   NOTICE and wrapper sources are retained, but SDK-loader source/System Library
   scope is not established by VC-runtime provenance.
4. Verify the exact resulting setup and its source/notices delivery, then obtain
   fresh maintainer installed-app confirmation and protected release approval.

These gates are concrete distribution checks. No long Torch build, paid code
signing requirement or self-approved installer gate is introduced.
