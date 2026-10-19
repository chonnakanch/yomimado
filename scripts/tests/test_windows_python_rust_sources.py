"""Require complete hash-locked registry inputs and safe original members."""

import hashlib
import io
import json
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

    def source_comparison_fixture(
        self, directory, *, code=b"pub fn sample() {}", vcs=None
    ):
        root = Path(directory)
        key = "example-1.0.0"
        original = root / "original.crate"
        upstream = root / "supplements/source-match" / (key + ".tar.gz")
        upstream.parent.mkdir(parents=True)
        package = b'[package]\nname="example"\nversion="1.0.0"\n'
        for path, prefix, contents in (
            (original, key, b"pub fn sample() {}"),
            (upstream, "source", code),
        ):
            with tarfile.open(path, "w:gz") as output:
                files = {"Cargo.toml": package, "src/lib.rs": contents}
                if path == original and vcs:
                    files[".cargo_vcs_info.json"] = json.dumps(
                        {"git": {"sha1": vcs}}
                    ).encode()
                for name, data in files.items():
                    item = tarfile.TarInfo(prefix + "/" + name)
                    item.size = len(data)
                    output.addfile(item, io.BytesIO(data))
        manifest = {
            "name": "example",
            "version": "1.0.0",
            "repository": "https://github.com/example/original",
        }
        pin = {
            "crateSha256": hashlib.sha256(original.read_bytes()).hexdigest(),
            "repository": manifest["repository"],
            "revision": "a" * 40,
            "sourceComparison": {
                "url": "https://codeload.github.com/example/original/tar.gz/"
                + "a" * 40,
                "sha256": hashlib.sha256(upstream.read_bytes()).hexdigest(),
                "prefix": "source",
            },
        }
        return root, key, original, manifest, pin

    def test_older_crate_without_vcs_requires_identical_pinned_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root, key, path, manifest, pin = self.source_comparison_fixture(directory)
            with tarfile.open(path) as source:
                sources.verify_supplement(
                    path,
                    source,
                    list(sources.regular_members(source)),
                    key,
                    manifest,
                    pin,
                    root,
                )
                pin.pop("sourceComparison")
                with self.assertRaisesRegex(ValueError, "needs VCS metadata"):
                    sources.verify_supplement(
                        path,
                        source,
                        list(sources.regular_members(source)),
                        key,
                        manifest,
                        pin,
                        root,
                    )

    def test_source_comparison_rejects_different_code_and_original_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root, key, path, manifest, pin = self.source_comparison_fixture(
                directory, code=b"pub fn changed() {}"
            )
            with tarfile.open(path) as source:
                members = list(sources.regular_members(source))
                with self.assertRaisesRegex(ValueError, "code differs"):
                    sources.verify_supplement(
                        path, source, members, key, manifest, pin, root
                    )
                pin["crateSha256"] = "0" * 64
                with self.assertRaisesRegex(ValueError, "identity differs"):
                    sources.verify_supplement(
                        path, source, members, key, manifest, pin, root
                    )

    def test_vcs_mismatch_cannot_fall_back_to_matching_code(self):
        with tempfile.TemporaryDirectory() as directory:
            root, key, path, manifest, pin = self.source_comparison_fixture(
                directory, vcs="b" * 40
            )
            with (
                tarfile.open(path) as source,
                self.assertRaisesRegex(ValueError, "original revision differs"),
            ):
                sources.verify_supplement(
                    path,
                    source,
                    list(sources.regular_members(source)),
                    key,
                    manifest,
                    pin,
                    root,
                )

    def test_source_comparison_rejects_unbound_revision_and_unsafe_prefix(self):
        with tempfile.TemporaryDirectory() as directory:
            root, key, path, manifest, pin = self.source_comparison_fixture(directory)
            with tarfile.open(path) as source:
                members = list(sources.regular_members(source))
                pin["revision"] = "c" * 40
                with self.assertRaisesRegex(ValueError, "repository/revision differs"):
                    sources.verify_supplement(
                        path, source, members, key, manifest, pin, root
                    )
                pin["revision"] = "a" * 40
                pin["sourceComparison"]["prefix"] = "../source"
                with self.assertRaisesRegex(ValueError, "Unsafe"):
                    sources.verify_supplement(
                        path, source, members, key, manifest, pin, root
                    )


if __name__ == "__main__":
    unittest.main()
