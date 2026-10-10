"""Source delivery preserves original legal bytes and rejects changed source inputs."""

import gzip
import hashlib
import io
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))
import windows_native_sources as sources


class NativeSourceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.original = self.root / "original.tar.gz"
        with tarfile.open(self.original, "w:gz") as archive:
            for name, content in {
                "root/LICENSE": b"original notice\r\n",
                "root/source.cpp": b"value = 1\n",
                "root/test.onnx": b"excluded test model",
                "root/example.jpg": b"excluded artwork",
            }.items():
                member = tarfile.TarInfo(name)
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))
        canonical = self.root / "expected.tar"
        sources.source_tree(self.original, canonical)
        import hashlib

        self.entry = {
            "name": "synthetic",
            "sha256": sources.digest(self.original),
            "preferredSourceSha256": sources.digest(canonical),
            "noticeHashes": {
                "root/LICENSE": hashlib.sha256(b"original notice\r\n").hexdigest()
            },
        }

    def test_filtered_delivery_and_notices_keep_exact_original_bytes(self):
        records = []
        for destination in (self.root / "one", self.root / "two"):
            records.append(
                sources.retain_archive(
                    self.entry, self.original, destination, self.root / "notices"
                )
            )
        self.assertEqual(records[0], records[1])
        self.assertEqual(
            {x["path"] for x in records[0]["excluded"]},
            {"root/test.onnx", "root/example.jpg"},
        )
        delivered = self.root / "one/synthetic.tar.gz"
        with tarfile.open(delivered) as archive:
            self.assertEqual(archive.getnames(), ["root/LICENSE", "root/source.cpp"])
            self.assertEqual(
                archive.extractfile("root/source.cpp").read(), b"value = 1\n"
            )
        self.assertEqual(
            (self.root / "notices/synthetic/root/LICENSE").read_bytes(),
            b"original notice\r\n",
        )
        self.assertEqual(sources.digest(delivered), records[0]["deliverySha256"])
        self.assertEqual(delivered.read_bytes()[4:8], b"\0" * 4)
        self.assertTrue(gzip.decompress(delivered.read_bytes()))

    def test_changed_source_or_notice_hashes_cannot_be_delivered(self):
        for field in ("sha256", "preferredSourceSha256", "noticeHashes"):
            entry = dict(self.entry)
            entry[field] = (
                {"root/LICENSE": "0" * 64} if field == "noticeHashes" else "0" * 64
            )
            with self.subTest(field=field), self.assertRaises(ValueError):
                sources.retain_archive(
                    entry, self.original, self.root / "delivery", self.root / "notices"
                )

    def test_notice_member_cannot_escape_delivery(self):
        self.entry["noticeHashes"] = {"../escape": "0" * 64}
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            sources.retain_archive(
                self.entry, self.original, self.root / "delivery", self.root / "notices"
            )

    def test_delivery_name_cannot_escape_source_directory(self):
        for name in ("../escape", "C:\\escape", "a/b", ""):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "Unsafe"):
                sources.retain_archive(
                    dict(self.entry, name=name),
                    self.original,
                    self.root / "delivery",
                    self.root / "notices",
                )

    def test_missing_original_license_cannot_be_silently_delivered(self):
        with self.assertRaisesRegex(ValueError, "no pinned original notices"):
            sources.retain_archive(
                dict(self.entry, noticeHashes={}),
                self.original,
                self.root / "delivery",
                self.root / "notices",
            )

    def test_python_wheel_code_matches_exact_preferred_source(self):
        wheel = self.root / "synthetic.whl"
        with zipfile.ZipFile(wheel, "w") as archive:
            archive.writestr("module.py", b"value = 1\n")
        original = self.root / "python.tar.gz"
        with tarfile.open(original, "w:gz") as archive:
            member = tarfile.TarInfo("root/module.py")
            member.size = len(b"value = 1\n")
            archive.addfile(member, io.BytesIO(b"value = 1\n"))
        package = {
            "package": "synthetic",
            "sha256": sources.digest(wheel),
            "source": {
                "sha256": sources.digest(original),
                "wheelSourcePrefix": "root/",
            },
        }
        result = sources.verify_python_source(package, wheel, original)
        self.assertEqual(set(result["pythonHashes"]), {"module.py"})
        for code in (b"changed code", None):
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr("module.py", code or b"value = 1\n")
                if code is None:
                    archive.writestr("missing.py", b"missing preferred source")
            package["sha256"] = sources.digest(wheel)
            with self.subTest(code=code), self.assertRaisesRegex(ValueError, "differs"):
                sources.verify_python_source(package, wheel, original)

    def test_numpy_vendor_binding_rejects_changed_blas_and_recipe(self):
        numpy = self.root / "numpy.whl"
        supplier = self.root / "supplier.whl"
        for path in (numpy, supplier):
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("blas.dll", b"original BLAS")
                archive.writestr("LICENSE", b"original notice\r\n")
        entry = {
            "numpyWheel": {
                "sha256": sources.digest(numpy),
                "nativeMember": "blas.dll",
                "nativeSha256": hashlib.sha256(b"original BLAS").hexdigest(),
            },
            "supplierWheel": {
                "sha256": sources.digest(supplier),
                "nativeMember": "blas.dll",
                "nativeSha256": hashlib.sha256(b"original BLAS").hexdigest(),
            },
            "supplierNoticeHashes": self.entry["noticeHashes"].copy(),
            "recipeFileHashes": {
                "source.cpp": hashlib.sha256(b"value = 1\n").hexdigest()
            },
            "recipePrefix": "root/",
            "supplierRevision": "supplier revision",
            "openblasRevision": "source revision",
        }
        entry["supplierNoticeHashes"] = {
            "LICENSE": hashlib.sha256(b"original notice\r\n").hexdigest()
        }
        result = sources.verify_numpy_vendor(entry, numpy, supplier, self.original)
        self.assertEqual(result["noticeBytes"], {"LICENSE": b"original notice\r\n"})
        entry["recipeFileHashes"]["source.cpp"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "recipe differs"):
            sources.verify_numpy_vendor(entry, numpy, supplier, self.original)
        entry["recipeFileHashes"]["source.cpp"] = hashlib.sha256(
            b"value = 1\n"
        ).hexdigest()
        with zipfile.ZipFile(supplier, "w") as archive:
            archive.writestr("blas.dll", b"different BLAS")
            archive.writestr("LICENSE", b"original notice\r\n")
        with self.assertRaisesRegex(ValueError, "wheel differs"):
            sources.verify_numpy_vendor(entry, numpy, supplier, self.original)
        entry["supplierWheel"].update(
            sha256=sources.digest(supplier),
            nativeSha256=hashlib.sha256(b"different BLAS").hexdigest(),
        )
        with self.assertRaisesRegex(ValueError, "differs from its original supplier"):
            sources.verify_numpy_vendor(entry, numpy, supplier, self.original)


if __name__ == "__main__":
    unittest.main()
