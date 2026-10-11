# Windows installer source record

Current component-terms setup — 2026-10-11: [run `38142782743`, attempt 4](https://github.com/chonnakanch/yomimado/actions/runs/38142782743)
at `f8396cc` passes the complete hosted installer suite. Setup SHA-256:
`756b7dc6003af202e4df95e946edcbc7fe409c41cfd0d2fc3be4062f758b4a1b`.
Its one extracted plugin copy matches the source-built i686 DLL SHA-256
`310896e3d00baf083744388d8fcaaad41b513f25c4b445fbdcca2eef19b03a62`;
recipe, lock, original/rendered template and terms manifest bindings pass.
The five unattended rejection/interactive cancellation cases and the installed
terms hash pass. Downloaded source/notices retain the exact new terms bytes,
unchanged original plugin/archive dependencies and their notices.
The maintainer confirms this exact setup hash and all six Windows 11 local
checks pass. Protected publication review remains open.

Verified 2026-10-11 in [run `38133593809`, attempt 2](https://github.com/chonnakanch/yomimado/actions/runs/38133593809),
source `8c46366d04e96d5356c250605e7ea936db209eb3`. Native workspace tests and
production compilation pass; the production build takes **4.05 seconds**.
The exact setup with SHA-256
`7ff298c597de9c33d23bb598bf16d6f41761219e51fc0b61951ed6c54174c6d9`
contains one extracted plugin copy, matching the source-built DLL SHA-256
`d0d8e0d5dea12cfedda350a4492803fc3bf758e2daf72752e6793a8a8537ccd7`.
Its machine is i686 (`0x14c`); imports are only advapi32, kernel32, shell32 and
user32, with no dynamic VC runtime dependency. The installed desktop/service
remain AMD64. Rendered template, dependency lock, recipe and original input
hashes also verify. The downloaded source/notices bundles preserve the original
plugin archive, all seven registry archives and their 15 notices, plus the two
upstream plugin licence texts. This changes the Windows private recipe only;
macOS and the public publisher are unchanged. The maintainer reports upgrade/uninstall/reinstall pass on this exact setup.
Microsoft redistribution requirements and protected publication approval remain open.

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
toolchain. It runs all upstream workspace tests with its `test` feature and
`--test-threads=1`, then
builds the production DLL with the original `DllMain` entrypoint. The NSIS host
is **i686**, while YomiMado and the frozen service remain **x64**. A target-only
linker script supplies x86 libraries without changing the host compiler's x64
environment. The plugin selects static compiler runtime linkage and rejects
unexpected dynamic VC imports; the compiler-runtime redistribution assessment
remains in the [Microsoft component review](windows-microsoft-runtime.md).

The exact official Tauri CLI 2.11.5 installer template is checksum-pinned.
The private component-terms replacement at `f8396cc` changes its
`ADDITIONALPLUGINSPATH` definition to select the newly built DLL, requires the
Microsoft-only terms page with an initially unchecked checkbox, rejects missing
or mismatched silent/passive assent, and records the accepted terms hash in the
per-user uninstall entry. The transformation requires the exact upstream anchors;
unexpected template changes fail preparation. The owner confirms obtaining
Community 2022 and accepting its terms; hosted verification now passes and fresh
local review of this changed setup now passes with its exact hash confirmed. See [the terms record](windows-microsoft-terms.json).
Tauri may still
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
i686-pc-windows-msvc --workspace --features test -- --test-threads=1` and the analogous
`cargo build --package nsis-tauri-utils` without the test feature under the
task-owned Cargo environment.
The producer records the complete commands and logs. The verified execution
does not claim a byte-identical independent rebuild, a Windows 11 manual result
or public approval.
