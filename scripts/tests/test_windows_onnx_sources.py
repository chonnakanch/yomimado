"""Source delivery keeps code and licences while rejecting unsafe archives."""

import io
import tarfile
import tempfile
import unittest
from pathlib import Path

from windows_onnx_sources import source_tree
from windows_release import digest


class PreferredSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def archive(self, name, files, *, timestamp=0, link=None):
        archive = self.root / name
        with tarfile.open(archive, "w") as out:
            for path, data in files.items():
                member = tarfile.TarInfo(path)
                member.size = len(data)
                member.mode = 0o755 if path.endswith(".sh") else 0o644
                member.mtime = timestamp
                out.addfile(member, io.BytesIO(data))
            if link:
                member = tarfile.TarInfo(link[0])
                member.type = tarfile.SYMTYPE
                member.linkname = link[1]
                out.addfile(member)
        return archive

    def test_test_models_media_and_native_binaries_cannot_enter_source_delivery(self):
        source = self.archive(
            "input.tar",
            {
                "root/source.cc": b"original source",
                "root/LICENSE": b"original terms",
                "root/build.sh": b"build recipe",
                "root/test.onnx": b"test weights",
                "root/test.png": b"test media",
                "root/vendor.dll": b"prebuilt",
            },
        )
        target = self.root / "preferred.tar"
        excluded = source_tree(source, target)
        self.assertEqual(
            {x["path"] for x in excluded},
            {"root/test.onnx", "root/test.png", "root/vendor.dll"},
        )
        with tarfile.open(target) as out:
            self.assertEqual(
                set(out.getnames()), {"root/source.cc", "root/LICENSE", "root/build.sh"}
            )
            self.assertEqual(
                out.extractfile("root/source.cc").read(), b"original source"
            )
            self.assertEqual(out.getmember("root/build.sh").mode, 0o755)

    def test_metadata_changes_preserve_hash_but_source_changes_do_not(self):
        first = self.archive("first.tar", {"root/code.cc": b"source"}, timestamp=1)
        second = self.archive(
            "second.tar", {"root/code.cc": b"source"}, timestamp=12345
        )
        third = self.archive("third.tar", {"root/code.cc": b"changed"})
        outputs = [self.root / (str(i) + ".tar") for i in range(3)]
        for source, target in zip((first, second, third), outputs):
            source_tree(source, target)
        self.assertEqual(digest(outputs[0]), digest(outputs[1]))
        self.assertNotEqual(digest(outputs[0]), digest(outputs[2]))

    def test_escaping_paths_and_symlinks_are_rejected(self):
        for path in ("../escape", "/absolute", "root/C:escape", "root/back\\slash"):
            source = self.archive("unsafe.tar", {path: b"data"})
            with self.assertRaisesRegex(ValueError, "Unsafe"):
                source_tree(source, self.root / "target.tar")
        source = self.archive(
            "link.tar", {"root/LICENSE": b"terms"}, link=("root/alias", "../escape")
        )
        with self.assertRaisesRegex(ValueError, "Escaping"):
            source_tree(source, self.root / "target.tar")

    def test_original_internal_license_symlink_is_retained(self):
        source = self.archive(
            "link.tar",
            {"root/LICENSE": b"terms"},
            link=("root/python/LICENSE", "../LICENSE"),
        )
        target = self.root / "target.tar"
        source_tree(source, target)
        with tarfile.open(target) as out:
            self.assertTrue(out.getmember("root/python/LICENSE").issym())
            self.assertEqual(out.extractfile("root/python/LICENSE").read(), b"terms")


if __name__ == "__main__":
    unittest.main()
