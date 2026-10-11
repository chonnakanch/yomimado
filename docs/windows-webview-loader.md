# Source-only Windows WebView2 loader investigation

Prepared 2026-10-11. The private recipe now stages the source-built loader into
the exact locked Windows Cargo input. Full installed-app verification remains
pending. This does not accept Microsoft terms, approve source delivery or publish.

The exact `webview2-com-sys` 0.38.2 binding statically links
`WebView2LoaderStatic.lib` on MSVC. The SDK's original BSD licence and NOTICE
are retained, but a public source tree for that loader has not been established.
Sources of the Rust wrappers and Microsoft's third-party browser components do
not establish preferred source for that statically linked loader.

The [webview project](https://github.com/webview/webview/blob/cbbdee44afff22867de9fd88a9fc8350d9bdd399/core/include/webview/detail/platform/windows/webview2/loader.hh)
provides a small MIT implementation of installed Evergreen runtime discovery
and environment creation. The isolated probe pins original revision
`cbbdee44afff22867de9fd88a9fc8350d9bdd399` and archive SHA-256
`10e972a2327b5681474f4aa4499e505eaa4ff659aa995380386f08fd6fc1b763`.
It uses only the exact Microsoft 1.0.3650.58 public header, LICENSE and NOTICE
from the already pinned NuGet package; it extracts no Microsoft loader object.

The recipe retains four explicit source corrections as a patch: include the
terminating NUL when allocating/copying the version string, size the file-version
buffer, return a failure when the internal environment symbol is absent, and
disable fallback loading of `WebView2Loader.dll`. Original sources/notices remain
unchanged in the retained archive. The compiled probe must discover an installed
Evergreen version, prove the Microsoft SDK loader is not loaded, create an actual
environment and controller through the open implementation, and finish within
one minute.

The initial direct-class probe passes run `38073007641` at `841c14a`. Its
downloaded evidence ZIP matches SHA-256
`6853bce4a07723f482f0e9f48298ab41ff4806037ce802bf3db5f632872c3ca8`;
installed Evergreen `131.0.2903.86` discovery, environment and controller pass.
The ABI probe passes run `38073342458` at `aa801cc`. Downloaded evidence
`11677482049` matches SHA-256
`1f413e83c00bc35a1d8df3bbbfc562172cafe3431911839387e1ca35e0c7ac6b`.
It compiles the two exact C ABI entrypoints used by locked wry
0.55.1 into a static library, then links and calls that library with non-null
environment options. The adapter catches C++ exceptions before the Rust ABI
boundary. Unused SDK loader entrypoints are not implemented or claimed.

**Windows source-only WebView loader probe** is an independent, five-minute,
read-only Actions workflow on `develop`. It has no private credential and does
not rebuild an installer or Torch. Its artifact retains original sources, the
SDK/header notices, exact patch, compiler command and native result. A passing
probe establishes feasibility only. The integration checks the original locked
crate against its archive before replacing only its x64 static-library input.
It retains original MIT source, patches, public SDK headers/notices and the ABI
adapter/build recipes. Installed verification requires the adapter marker in the
desktop EXE and exact source-library hashes in every Cargo build output. The
adapter's dynamic CRT dependencies are packaged as unchanged, pinned canonical
VC143 REDIST copies; their conditional redistribution review remains separate.
Full installed UI tests must pass. Fixed-version runtimes and alternative browser
channels remain untested. The native probe covers non-null environment options.

The OS-provided Evergreen runtime remains a separate component. Microsoft's
[distribution guidance](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution)
states it is included with Windows 11 and describes its independent servicing.
This does not clear the original SDK loader or make Microsoft's runtime open
source. Preserve the distinction when completing the release review.
