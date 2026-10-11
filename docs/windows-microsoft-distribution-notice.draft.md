# Microsoft runtime component notice — review draft

Prepared 2026-10-11. **Not an accepted agreement, redistribution grant or active
installer licence page.** The maintainer reports no/unsure Visual Studio licence.
This document identifies the components and prepares the remaining review; a
notice alone does not satisfy Microsoft's end-user agreement requirement.

## Component identification

YomiMado's Windows candidate includes unchanged Microsoft Visual C++ VC143
runtime files, version **14.44.35211.0**. Their canonical origin is Visual
Studio's `VC/Redist/MSVC/14.44.35112/x64/Microsoft.VC143.CRT` directory.
[The exact manifest](windows-vc-runtime-inputs.json) records each original
SHA-256; installed verification binds desktop and standard/renamed service
copies to those originals.

The ten originals are `concrt140.dll`, `msvcp140.dll`, `msvcp140_1.dll`,
`msvcp140_2.dll`, `msvcp140_atomic_wait.dll`, `msvcp140_codecvt_ids.dll`,
`vccorlib140.dll`, `vcruntime140.dll`, `vcruntime140_1.dll` and
`vcruntime140_threads.dll`. The source-built NSIS plugin also uses static
compiler runtime linkage, as recorded in [the installer review](windows-nsis-runtime.md).

These Microsoft components remain separately licensed Microsoft software.
YomiMado's GPL licence does not grant additional rights to them. Any approved
Microsoft-specific terms must apply only to the Microsoft components, without
restricting rights granted for YomiMado or its other open-source components.

## Applicable originals and owner completion

Microsoft's [Visual Studio 2022 redistribution list](https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution)
conditions distribution of these unchanged runtime files on a valid Visual
Studio licence and its terms. The [Community 2022 terms](https://visualstudio.microsoft.com/license-terms/vs2022-ga-community/)
permit individual application development. Their original English agreement is
[available from Microsoft](https://visualstudio.microsoft.com/wp-content/uploads/2021/11/Visual-Studio-2022-Community-License-EN.docx),
SHA-256 `41a207b10c8ab91d0d2f10a854715f73dca54509581692d2fe179aa3ffcb8540`.
Distribution provisions include protective agreements with external end users
and distributors. An attribution page or link is not evidence of their assent.

Before public distribution:

1. The maintainer must establish an applicable Visual Studio licence, reviewing
   and accepting its agreement themselves if necessary. Record the edition and
   applicable terms; do not publish account details or licence keys.
2. Review the complete distribution conditions, including the compiler runtime
   role and Microsoft-only end-user/distributor terms. Prepare an appropriate
   acceptance mechanism and retain evidence. This draft supplies neither that
   agreement nor a legal conclusion that the conditions have been met.
3. Include the reviewed component notice and any required accepted terms in
   the Windows package. Rebuild if installer content changes, verify the exact
   files, source/notices and hashes, and obtain the new exact-installer PC result.
4. Only then request protected human release approval and integrate joint
   publication. The current private setup remains unapproved for publication.

A separately installed official runtime prerequisite is a possible alternative,
but requires revised packaging, clean-machine detection and installed testing.
It is not implemented by this notice. No Microsoft agreement is accepted on
the maintainer's behalf, and no paid Windows application-publishing licence or
paid code-signing requirement is introduced.
