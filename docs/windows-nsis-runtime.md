# Windows installer source record

Prepared 2026-10-11. Native execution and embedded-plugin verification remain
pending. This changes the Windows private recipe only; macOS and the public
publisher are unchanged.

The observed installer input `nsis_tauri_utils.dll` is version 0.5.3 from
[upstream commit `13d9edd27b69310e108d6fbd49f90992f8a05390`](https://github.com/tauri-apps/nsis-tauri-utils/tree/13d9edd27b69310e108d6fbd49f90992f8a05390).
Its original release source contains the MIT/Apache-2.0 licences and build
recipe, but no Cargo.lock. The old prebuilt DLL's exact dependency resolution
is therefore not established merely by collecting that source.

The private recipe now builds that unchanged plugin source with a deliberately
resolved [dependency lock](windows-nsis-plugin-Cargo.lock). The
[input manifest](windows-nsis-plugin-inputs.json) pins all seven original
registry archives and 15 full notice files. Preparation resolves the graph
offline and preserves those original archives, notices, the new lock and the
recipe. This is a short installer-plugin build, separate from Torch.

`scripts/windows_nsis_plugin.py` uses Rust 1.98.1 and the pinned Windows MSVC/SDK
toolchain. It runs the upstream workspace tests with its `test` feature, then
builds the production DLL with the original `DllMain` entrypoint. The NSIS host
is **i686**, while YomiMado and the frozen service remain **x64**. A target-only
linker script supplies x86 libraries without changing the host compiler's x64
environment. The plugin selects static compiler runtime linkage and rejects
unexpected dynamic VC imports; the compiler-runtime redistribution assessment
remains in the [Microsoft component review](windows-microsoft-runtime.md).

The exact official Tauri CLI 2.11.5 installer template is checksum-pinned.
Only its `ADDITIONALPLUGINSPATH` definition changes to select the newly built
DLL. Every other upstream installation line is preserved. Tauri may still
download its stock plugin into the tool cache; that file is outside the selected
additional-plugin directory and is not treated as the embedded input.

After installing the exact resulting setup, verification binds its rendered
installer script to that directory and extracts all matching embedded plugin
copies with the runner's 7-Zip. Every copy must match the source-built DLL's
SHA-256. Missing copies, changed templates, locks, recipes or DLLs fail the gate.
The result enters `windows-installer-inputs.json`; installed startup/UI/learning
tests and a fresh maintainer upgrade/uninstall test remain separate gates.

The retained NSIS 3.11 original source includes its stubs, built-in plugins,
compression sources, SCons recipe and full COPYING file. Its zlib/libpng licence
and separate bzip2/CPL-1.0 LZMA terms (including the linking exception) are
preserved rather than inferred from the
Tauri plugin's licence. The installer input inventory distinguishes the full
tool cache from the exact additional plugin actually embedded in the setup.
The selected setup uses zlib compression; retaining other upstream compressor
sources/notices does not claim that their code is embedded.

For a rebuild, use the project source at the recorded revision, the retained
original archives and lock, and the pinned Windows toolchain. Run the preparation
recipe, then `cargo test --offline --locked --release --target
i686-pc-windows-msvc --workspace --features test` and the analogous
`cargo build --package nsis-tauri-utils` without the test feature under the
task-owned Cargo environment.
The producer records the complete commands and logs. No byte-identical rebuild,
Windows 11 manual result or public approval is claimed before execution.
