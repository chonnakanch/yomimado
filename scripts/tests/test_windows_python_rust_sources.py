"""Require complete hash-locked registry inputs and safe original members."""

import io
import tarfile
import tempfile
import unittest
from pathlib import Path

import windows_python_rust_sources as sources


class PythonRustSourcesTests(unittest.TestCase):
    def archive(self, directory, name, contents):
        path = Path(directory) / "original.tar.gz"
        with tarfile.open(path, "w:gz") as output:
            item = tarfile.TarInfo(name)
            item.size = len(contents)
            output.addfile(item, io.BytesIO(contents))
        return path

    def test_original_lock_checksums_and_nonregistry_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            content = (
                'version = 3\n[[package]]\nname = "binding"\nversion = "1.0.0"\n'
                '[[package]]\nname = "dep"\nversion = "2.0.0"\n'
                'source = "registry+https://github.com/rust-lang/crates.io-index"\n'
                'checksum = "' + "a" * 64 + '"\n'
            ).encode()
            path = self.archive(directory, "binding/Cargo.lock", content)
            lock, entries = sources.locked_sources(path)
            self.assertEqual(lock["path"], "binding/Cargo.lock")
            self.assertEqual(
                entries, [{"name": "dep", "version": "2.0.0", "sha256": "a" * 64}]
            )
            self.archive(
                directory,
                "binding/Cargo.lock",
                content.replace(
                    b"registry+https://github.com/rust-lang/crates.io-index",
                    b"git+https://example.invalid/repo",
                ),
            )
            with self.assertRaisesRegex(ValueError, "non-registry"):
                sources.locked_sources(path)

    def test_unsafe_original_members_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.archive(directory, "../Cargo.lock", b"bad")
            with self.assertRaisesRegex(ValueError, "Unsafe"):
                sources.locked_sources(path)


if __name__ == "__main__":
    unittest.main()
