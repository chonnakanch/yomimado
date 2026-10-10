"""Verify source archive integrity and exact supplemental notice coverage."""

import base64
import hashlib
import io
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
import windows_notices as notices
import windows_release as release


class WindowsNoticeTests(unittest.TestCase):
    def test_gitiles_metadata_can_vary_but_source_bytes_cannot(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)

            def archive(name, timestamp, content):
                path = root / name
                with tarfile.open(path, "w:gz") as source:
                    member = tarfile.TarInfo("src/library.c")
                    member.mode = 0o100644
                    member.mtime = timestamp
                    member.size = len(content)
                    source.addfile(member, io.BytesIO(content))
                return path

            original = archive("original.tar.gz", 123, b"original source\n")
            refreshed = archive("refreshed.tar.gz", 456, b"original source\n")
            changed = archive("changed.tar.gz", 456, b"changed source\n")
            expected = root / "expected.tar"
            notices.canonical_source_tar(original, expected)
            entry = {
                "archiveNormalization": "gitiles-tar-v1",
                "url": "https://chromium.googlesource.com/project/+archive/"
                + "a" * 40
                + ".tar.gz",
                "revision": "a" * 40,
                "sha256": notices.digest(expected),
            }
            output = root / "accepted.tar"
            with patch.object(
                notices, "urlopen", return_value=io.BytesIO(refreshed.read_bytes())
            ):
                notices.native_notice_source(entry, output)
            self.assertEqual(output.read_bytes(), expected.read_bytes())
            with tarfile.open(output) as source:
                member = source.getmember("src/library.c")
                self.assertEqual(member.mode, 0o644)
                self.assertEqual(member.mtime, 0)
                self.assertEqual(
                    source.extractfile(member).read(), b"original source\n"
                )
            with (
                patch.object(
                    notices, "urlopen", return_value=io.BytesIO(changed.read_bytes())
                ),
                self.assertRaisesRegex(ValueError, "tree checksum changed"),
            ):
                notices.native_notice_source(entry, root / "rejected.tar")
            self.assertFalse((root / "rejected.tar").exists())
            self.assertFalse((root / "rejected.tar.download").exists())
            self.assertFalse((root / "rejected.tar.canonical").exists())

    def test_canonical_source_rejects_links_escaping_and_duplicate_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for names in (("../source",), ("/source",), ("source", "source")):
                archive = root / "unsafe.tar"
                with tarfile.open(archive, "w") as source:
                    for name in names:
                        source.addfile(tarfile.TarInfo(name))
                with self.assertRaisesRegex(ValueError, "Unsafe or duplicate"):
                    notices.canonical_source_tar(archive, root / "canonical.tar")
            with tarfile.open(archive, "w") as source:
                link = tarfile.TarInfo("link")
                link.type = tarfile.SYMTYPE
                link.linkname = "elsewhere"
                source.addfile(link)
            with self.assertRaisesRegex(ValueError, "Unsafe or duplicate"):
                notices.canonical_source_tar(archive, root / "canonical.tar")

    def test_normalized_source_requires_exact_commit_on_original_host(self):
        entry = {
            "archiveNormalization": "gitiles-tar-v1",
            "revision": "a" * 40,
            "sha256": "unused",
        }
        for url in (
            "https://example.com/+archive/" + "a" * 40 + ".tar.gz",
            "https://chromium.googlesource.com/project/+archive/main.tar.gz",
            "https://user:secret@chromium.googlesource.com/project/+archive/"
            + "a" * 40
            + ".tar.gz",
        ):
            with (
                patch.object(notices, "urlopen") as network,
                self.assertRaisesRegex(ValueError, "Unpinned Gitiles"),
            ):
                notices.native_notice_source({**entry, "url": url}, Path("unused"))
            network.assert_not_called()

    def test_native_notices_preserve_bytes_and_reject_changed_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "original.tar.gz"
            content = b"Original vendor notice\r\n"
            with tarfile.open(archive, "w:gz") as source:
                member = tarfile.TarInfo("vendor/licenses/PATENTS")
                member.size = len(content)
                source.addfile(member, io.BytesIO(content))
            entry = {
                "sha256": notices.digest(archive),
                "licenseFiles": {
                    member.name: hashlib.sha256(content).hexdigest(),
                },
            }
            result = notices.tar_notices(entry, archive, root / "notices")
            self.assertEqual(len(result), 1)
            self.assertEqual(Path(result[0]).read_bytes(), content)
            entry["licenseFiles"][member.name] = "changed"
            with self.assertRaisesRegex(ValueError, "notice hash differs"):
                notices.tar_notices(entry, archive, root / "wrong-notice")
            self.assertFalse((root / "wrong-notice").exists())
            entry["sha256"] = "changed"
            with self.assertRaisesRegex(ValueError, "archive hash differs"):
                notices.tar_notices(entry, archive, root / "wrong-source")

    def test_native_notice_cannot_escape_or_follow_archive_link(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "original.tar.gz"
            with tarfile.open(archive, "w:gz") as source:
                link = tarfile.TarInfo("LICENSE")
                link.type = tarfile.SYMTYPE
                link.linkname = "elsewhere"
                source.addfile(link)
            entry = {"sha256": notices.digest(archive), "licenseFiles": {}}
            for name in ("../LICENSE", "/LICENSE", "C:/LICENSE", "a\\LICENSE"):
                entry["licenseFiles"] = {name: "unused"}
                with self.assertRaisesRegex(ValueError, "Unsafe"):
                    notices.tar_notices(entry, archive, root / "notices")
            entry["licenseFiles"] = {"LICENSE": "unused"}
            with self.assertRaisesRegex(ValueError, "regular source"):
                notices.tar_notices(entry, archive, root / "notices")
            self.assertFalse((root / "notices").exists())

    def test_desktop_cannot_use_developer_vc_runtime_from_system32(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            installed = root / "installed"
            cache = root / "tauri/NSIS"
            system = root / "System32"
            for path in (installed, cache, system):
                path.mkdir(parents=True)
            exe = installed / "yomimado.exe"
            exe.write_bytes(b"MZsynthetic")
            (system / "msvcp140.dll").write_bytes(b"MZsystem-developer-runtime")
            (system / "msvcp_win.dll").write_bytes(b"MZwindows-os-library")
            with (
                patch.dict(
                    "os.environ", {"LOCALAPPDATA": str(root), "SystemRoot": str(root)}
                ),
                patch.object(notices, "BUILD", root / "evidence"),
                patch.object(
                    release,
                    "pe_info",
                    return_value={
                        "machine": "0x8664",
                        "subsystem": 2,
                        "imports": ["msvcp140.dll", "msvcp_win.dll"],
                    },
                ),
            ):
                with self.assertRaisesRegex(ValueError, "desktop app-local"):
                    notices.installer_inputs(installed, exe)
                self.assertTrue(
                    (root / "evidence/windows-installer-inputs.json").exists()
                )
                (installed / "msvcp140.dll").write_bytes(b"MZapp-local-runtime")
                notices.installer_inputs(installed, exe)

    def test_existing_npm_archive_must_match_locked_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "package.tgz"
            path.write_bytes(b"original archive")
            entry = {
                "resolved": "https://registry.npmjs.org/package/-/package.tgz",
                "integrity": "sha512-"
                + base64.b64encode(hashlib.sha512(path.read_bytes()).digest()).decode(),
            }
            self.assertEqual(notices.npm_source(entry, path), notices.digest(path))
            path.write_bytes(b"changed archive")
            with self.assertRaisesRegex(ValueError, "integrity differs"):
                notices.npm_source(entry, path)

    def test_unpinned_registry_source_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unpinned"):
            notices.npm_source(
                {"resolved": "https://example.com/source", "integrity": "sha256-eA=="},
                Path("unused"),
            )

    def test_supplement_text_is_verified_before_copying(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            copied = notices.supplement("lgpl-2.1", target / "ok")
            self.assertTrue(copied)
            with (
                patch.object(notices, "digest", return_value="changed"),
                self.assertRaisesRegex(ValueError, "hash differs"),
            ):
                notices.supplement("lgpl-2.1", target / "bad")
            self.assertFalse((target / "bad").exists())


if __name__ == "__main__":
    unittest.main()
