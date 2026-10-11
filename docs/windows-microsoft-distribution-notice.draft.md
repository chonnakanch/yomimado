# Microsoft runtime component notice — review draft

Prepared 2026-10-11. **Not an accepted agreement, redistribution grant or active
installer licence page.** The maintainer now confirms obtaining Community 2022
and accepting its terms. This notice worksheet is supplemented by the
[actual Windows installer terms](../THIRD_PARTY_LICENSES/windows-microsoft-components.txt)
and [hash-bound owner record](windows-microsoft-terms.json); hosted verification
and protected exact-installer review remain pending.
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

1. The maintainer confirms obtaining Community 2022 and accepting its terms on
   2026-10-11. No key or account details are recorded.
2. Review the complete distribution conditions, including the compiler runtime
   role and Microsoft-only end-user/distributor terms. Prepare an appropriate
   acceptance mechanism and retain evidence. The
   [component-only text](../THIRD_PARTY_LICENSES/windows-microsoft-components.txt)
   is now included in private Windows setup with affirmative interactive and
   explicit exact-hash unattended acceptance. No conclusion that the protective standard has been
   satisfied is claimed.
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

## Owner acquisition instructions

Microsoft's [2022 release history](https://learn.microsoft.com/en-us/visualstudio/releases/2022/release-history#evergreen-bootstrappers)
lists Community under Current 17.14. On the Windows PC, obtain that edition,
review the offered licence and accept it yourself if you agree. Community is
free for individual developers; a Professional/Enterprise purchase is not
required for this personal project. Record edition, version and your acceptance
confirmation/date. Do not send a key or account information. Installing only
the Visual C++ Redistributable as an end user does not establish the distributor
grant. The current public download landing page may offer a newer edition;
using another edition needs its own applicable-terms review.

## Prepared acceptance implementation review

The [exact pinned Tauri CLI 2.11.5 NSIS template](https://github.com/tauri-apps/tauri/blob/tauri-cli-v2.11.5/crates/tauri-bundler/src/bundle/windows/nsis/installer.nsi)
includes an optional licence page,
but its `SkipIfPassive` callback skips that page in passive mode, and silent
installation does not display interactive pages. Merely setting `bundle.licenseFile`
would therefore not establish assent in every installation path.

After the owner grant and component-only agreement have been reviewed:

1. Retain the final Microsoft-component terms in the installer, installed notice
   directory and delivered notices, and bind their exact hash in provenance.
   Explicitly preserve YomiMado's GPL rights and each other component's licence.
2. Present the reviewed text with affirmative acceptance in interactive setup;
   cancellation/declining must exit before installing files. Treat update setup
   consistently; do not assume that an earlier install accepted changed text.
3. Either reject silent/passive installation when assent is required or require
   an explicit documented acceptance argument bound to the exact terms hash.
   Do not silently treat `/S`, passive mode or a previous install as consent.
4. Verify decline/cancel, interactive acceptance and silent/passive behavior in
   Windows Actions and the exact installed candidate. Preserve the retained
   NSIS plugin/template source bindings, per-user installation and macOS path.
5. Distributors need the reviewed obligations and their own agreement evidence;
   an installer page for end users alone does not establish downstream compliance.

The acceptance mechanics above are now implemented for a new private candidate;
Windows Actions verification is pending. This worksheet does not claim blanket
legal approval. The protected human review includes the exact terms and installer.
Current setup `7ff298c5…` has a passing technical/local test record but includes
no accepted component-specific terms page. A changed package requires a new
hash and exact-installer confirmation before protected publication approval.
