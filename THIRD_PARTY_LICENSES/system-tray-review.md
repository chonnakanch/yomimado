# System tray source review — 2026-10-17

The tray implementation enables Tauri's `tray-icon` feature. It adds no package
version or Cargo.lock change. Offline, locked Cargo metadata was compared with
the same manifest minus that feature for `aarch64-apple-darwin` and
`x86_64-pc-windows-msvc`: the resolved registry package sets and versions are
unchanged (280 and 286 third-party packages respectively). The only changed
feature list is Tauri's addition of `tray-icon`.

The exact local registry sources declare:

| Crate     | Version | Declared license  |
| --------- | ------- | ----------------- |
| tauri     | 2.11.6  | Apache-2.0 OR MIT |
| tray-icon | 0.24.2  | MIT OR Apache-2.0 |
| muda      | 0.19.3  | Apache-2.0 OR MIT |

Both tray-icon and muda ship full `LICENSE-MIT` and `LICENSE-APACHE` texts.
Their respective file SHA-256 digests are
`2ab5537b8c0cb1d475e2145b6a7994b04e7c71e6e5bd836f7f9c47c221a5ad9a`
and `a60eea817514531668d7e00765731449fe14d059d3249e0bc93b36de45f759f2`.
Tauri's license texts use the existing upstream supplement under `upstream/tauri`.

The existing macOS Rust notice collector was run against the changed manifest:
280 third-party components have declared licenses and copied notice files, with
no missing entries. It includes tray-icon and muda's full license texts and
Tauri's supplement. The Windows collector reads the Windows-target locked Cargo
graph and retains matching registry archives/checksums and notice files. Its
full packaged-source inventory remains a future Windows release check; it was
not regenerated as an installer in this change. Keep the existing notice/source
gates on both release builders.

For 0.2.2 preparation, the local approved `fae4d28` source delivery and its Rust
notice inventory were compared with the current macOS Cargo metadata. All 280
registry package names/versions match, including tray-icon, muda and Tauri; no
package was added or removed. The approved delivery already contains their
notices and checksum-verified sources in `cargo-sources.tar.gz` (delivery SHA-256
`41f91e3ba3d29a5600e260bbaf3a02b57f77805e69377e461009736424f5cd9b`).
The release preflight permits only the tray feature addition and the named native
tray inputs; other dependency, build-input and shared OCR changes still fail.

The two tray images are original geometric application assets generated from
`scripts/generate_tray_icons.py`, using only the Python standard library. No
third-party logo, font, manga, screenshot or model input is bundled. Their
SHA-256 digests are:

| File              | SHA-256                                                            |
| ----------------- | ------------------------------------------------------------------ |
| tray-template.png | `641a7becd5f793e570b6f3a5d96fed6521824ecc3f83707114031d7f954ffcd7` |
| tray-windows.png  | `89536e719926aec8c1a2feb9cdde4adb409f0a1978853883332fa3d587a53f20` |

This records source/license coverage for the feature. Existing installer hashes,
owner acceptance and publication gates are unchanged.
