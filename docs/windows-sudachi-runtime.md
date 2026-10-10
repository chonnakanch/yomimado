# Locked Windows Sudachi binding

The private ONNX preparation builds only SudachiPy 0.6.10's small Rust binding,
using the original `sudachi.rs` source at
`7e2f287bbfffc036421cf960802e41a696727747`, Python 3.11.17 and Rust 1.98.1.
It preserves the original wheel's Python wrapper and dictionaries. There is no
Torch source build and no macOS change.

The old wheel's embedded paths identify PyO3 0.23.3, while its published tag's
lock records 0.22.6. A deliberately resolved lock avoids claiming that incomplete
upstream graph as exact binary evidence. The new lock pins PyO3 0.23.3 and retains
the other original compatible versions. Two recorded build-manifest edits select
the `sudachi` and `python` workspace members and remove the library's test-only
dependencies. Runtime Rust/Python source files are unchanged.

[The input manifest](windows-sudachi-build-inputs.json) binds the original source,
each original and updated build manifest, [the complete lock](windows-sudachi-Cargo.lock),
62 original crate checksums and their original notice hashes. The preparation
extracts verified originals into a task-owned vendor directory and Cargo home;
compilation uses `--offline --locked --release` for `x86_64-pc-windows-msvc`.
It does not change global Cargo configuration or use credential storage.

The binding compile has a ten-minute limit. The build record preserves compiler
and SDK identity, actual compiler-artifact package IDs, command/log hashes,
the original wheel extension hash and the replacement extension's SHA-256,
architecture and imports. The replacement must pass the existing service and
exact frozen/installed tokenization, dictionary and persistence tests.

Source delivery retains the original project/crate archives, manifest changes,
lock, recipe and build record; installed notices retain the original licence
texts and matching record. Some locked target support crates are not selected
for x64 compilation; supplying their original archives does not claim ARM64 app
coverage. Compiler-artifact records identify what actually compiled.

Local preparation verifies all original source/notice bytes and resolves the
Windows graph offline: 54 registry packages selected, 128 original notice files.
The new native Windows build and installed tests remain required. This record
does not approve the full source delivery or human installer gate.

Rebuild from the complete source checkout on Windows after preparing the pinned
Python runtime and installing the original Sudachi wheel:

```powershell
services/ocr/build/windows/venv/Scripts/python.exe scripts/windows_sudachi_runtime.py build
```

The normal private candidate entrypoint performs this before service tests and
freezing, then retains its delivery record before inventory and packaging.
