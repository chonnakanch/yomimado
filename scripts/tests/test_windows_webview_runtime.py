"""Reject loader cache substitution and unbound installed native copies."""

import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import windows_webview_runtime as loader


class WebviewRuntimeTests(unittest.TestCase):
    def test_original_crate_cache_must_match_locked_archive(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            crate = root / "webview2-com-sys-0.38.2"
            crate.mkdir()
            (crate / "build.rs").write_bytes(b"original source")
            archive = root / "original.crate"
            with tarfile.open(archive, "w:gz") as output:
                item = tarfile.TarInfo(crate.name + "/build.rs")
                item.size = len(b"original source")
                output.addfile(item, io.BytesIO(b"original source"))
            loader.check_original_crate(crate, archive, loader.digest(archive))
            (crate / "build.rs").write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "cache differs"):
                loader.check_original_crate(crate, archive, loader.digest(archive))

    def test_installed_loader_and_crt_are_bound_to_cargo_input(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            desktop = root / "installed/yomimado.exe"
            notices = desktop.parent / "ocr/notices/source-webview-loader"
            notices.mkdir(parents=True)
            desktop.write_bytes(b"MZ" + loader.MARKER)
            adapter = root / "scripts/source-webview-loader.cpp"
            adapter.parent.mkdir()
            adapter.write_bytes(b"adapter")
            (notices / adapter.name).write_bytes(adapter.read_bytes())
            patch_file = notices / "loader.patch"
            patch_file.write_bytes(b"patch")
            crt = desktop.parent / "vcruntime140.dll"
            crt.write_bytes(b"canonical")
            manifest = root / "docs/windows-vc-runtime-inputs.json"
            manifest.parent.mkdir()
            manifest.write_text(json.dumps({"files": {crt.name: loader.digest(crt)}}))
            library = (
                root
                / "apps/desktop/src-tauri/target/release/build/webview2-com-sys-test/out/x64/WebView2LoaderStatic.lib"
            )
            library.parent.mkdir(parents=True)
            library.write_bytes(b"source library")
            record = {
                "passed": True,
                "adapterSha256": loader.digest(adapter),
                "patchSha256": loader.digest(patch_file),
                "librarySha256": loader.digest(library),
                "desktopCrtInputs": [{"name": crt.name, "sha256": loader.digest(crt)}],
            }
            (notices / loader.RECORD).write_text(json.dumps(record))
            with patch.object(loader, "ROOT", root):
                result = loader.verify(desktop)
                self.assertEqual(
                    result["installedDesktopSha256"], loader.digest(desktop)
                )
                library.write_bytes(b"SDK library")
                with self.assertRaisesRegex(ValueError, "unbound"):
                    loader.verify(desktop)
                library.write_bytes(b"source library")
                crt.write_bytes(b"changed")
                with self.assertRaisesRegex(ValueError, "CRT copies differ"):
                    loader.verify(desktop)


if __name__ == "__main__":
    unittest.main()
