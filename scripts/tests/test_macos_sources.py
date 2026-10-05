"""Test source provenance rejection without downloading or executing packages."""

import importlib.util
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "macos_sources", Path(__file__).parents[1] / "prepare-macos-sources.py"
)
sources = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sources)


class SourceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.vendor = self.root / "vendor"
        self.crate = self.vendor / "test-crate"
        self.crate.mkdir(parents=True)
        (self.crate / "Cargo.toml").write_text(
            '[package]\nname="test-crate"\nversion="1.0.0"\n'
        )
        (self.crate / "LICENSE").write_text("MPL-2.0 test fixture")
        cache = self.root / "cache/registry"
        cache.mkdir(parents=True)
        archive = cache / "test-crate-1.0.0.crate"
        with tarfile.open(archive, "w:gz") as bundle:
            bundle.add(self.crate, arcname="test-crate-1.0.0")
        checksum = sources.digest(archive)
        cache_patch = patch.object(sources, "CARGO_CACHE", cache.parent)
        cache_patch.start()
        self.addCleanup(cache_patch.stop)
        self.lock = self.root / "Cargo.lock"
        self.lock.write_text(
            '[[package]]\nname="test-crate"\nversion="1.0.0"\n'
            'source="registry+https://github.com/rust-lang/crates.io-index"\n'
            f'checksum="{checksum}"\n'
        )
        self.checksums = {
            "package": checksum,
            "files": {path.name: sources.digest(path) for path in self.crate.iterdir()},
        }
        self.write_checksums()

    def write_checksums(self):
        (self.crate / ".cargo-checksum.json").write_text(json.dumps(self.checksums))

    def native_review_fixture(self):
        archive = self.root / "native.tar.gz"
        archive.write_bytes(b"original sources and build recipe")
        notices = self.root / "notices"
        notices.mkdir()
        notice = notices / "LICENSE"
        notice.write_text("MIT licence and original attribution")
        group = {
            "archive": archive.name,
            "sha256": sources.digest(archive),
            "licenseEvidence": "Inspected original source and retained MIT notice",
            "noticeFiles": {"LICENSE": sources.digest(notice)},
            "nativeInputs": [{"id": "native:test", "buildInputSha256": "input"}],
        }
        review = self.root / "review.json"
        review.write_text(json.dumps({"groups": [group]}))
        binaries = [{"id": "native:test", "buildInputSha256": "input"}]
        return archive, notices, group, review, binaries

    def test_native_review_is_hash_bound_and_does_not_approve_release(self):
        _, notices, _, review, binaries = self.native_review_fixture()
        report = {"status": "unreviewed", "candidates": []}
        result = sources.apply_native_reviews(
            notices, self.root, binaries, report, review
        )
        self.assertEqual(result, {"native:test"})
        self.assertEqual(report["nativeEvidenceVerified"], 1)
        self.assertEqual(report["status"], "unreviewed")
        self.assertNotIn("reviewer", report)

    def test_native_review_rejects_changed_source_notice_and_input(self):
        archive, notices, _, review, binaries = self.native_review_fixture()
        archive.write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "source archive"):
            sources.apply_native_reviews(
                notices, self.root, binaries, {"candidates": []}, review
            )
        archive.write_bytes(b"original sources and build recipe")
        (notices / "LICENSE").write_text("changed")
        with self.assertRaisesRegex(ValueError, "native notice"):
            sources.apply_native_reviews(
                notices, self.root, binaries, {"candidates": []}, review
            )
        (notices / "LICENSE").write_text("MIT licence and original attribution")
        binaries[0]["buildInputSha256"] = "changed"
        with self.assertRaisesRegex(ValueError, "native input"):
            sources.apply_native_reviews(
                notices, self.root, binaries, {"candidates": []}, review
            )

    def test_native_review_requires_licence_and_notice_evidence(self):
        _, notices, group, review, binaries = self.native_review_fixture()
        for field in ("licenseEvidence", "noticeFiles"):
            altered = {**group, field: None}
            review.write_text(json.dumps({"groups": [altered]}))
            with self.assertRaisesRegex(ValueError, "licence/notice evidence"):
                sources.apply_native_reviews(
                    notices, self.root, binaries, {"candidates": []}, review
                )

    def test_native_review_rejects_duplicate_inputs_and_path_escape(self):
        _, notices, group, review, binaries = self.native_review_fixture()
        group["nativeInputs"] *= 2
        review.write_text(json.dumps({"groups": [group]}))
        with self.assertRaisesRegex(ValueError, "native input"):
            sources.apply_native_reviews(
                notices, self.root, binaries, {"candidates": []}, review
            )
        group["archive"] = "../outside.tar.gz"
        review.write_text(json.dumps({"groups": [group]}))
        with self.assertRaisesRegex(ValueError, "source archive"):
            sources.apply_native_reviews(
                notices, self.root, binaries, {"candidates": []}, review
            )

    def test_complete_vendor_matches_lock(self):
        result = sources.validate_vendor(self.vendor, self.lock)
        self.assertEqual(result, {("test-crate", "1.0.0"): self.crate})

    def test_modified_crate_source_rejected(self):
        (self.crate / "LICENSE").write_text("altered")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            sources.validate_vendor(self.vendor, self.lock)

    def test_extra_unchecked_file_rejected(self):
        (self.crate / "injected.rs").write_text("unchecked")
        with self.assertRaisesRegex(ValueError, "coverage mismatch"):
            sources.validate_vendor(self.vendor, self.lock)

    def test_wrong_locked_package_rejected(self):
        self.checksums["package"] = "another-package"
        self.write_checksums()
        with self.assertRaisesRegex(ValueError, "does not match lockfile"):
            sources.validate_vendor(self.vendor, self.lock)

    def test_forged_vendor_checksum_map_rejected(self):
        path = self.crate / "LICENSE"
        path.write_text("changed source with forged per-file hash")
        self.checksums["files"]["LICENSE"] = sources.digest(path)
        self.write_checksums()
        with self.assertRaisesRegex(ValueError, "differs from original source"):
            sources.validate_vendor(self.vendor, self.lock)

    def test_missing_locked_crate_rejected(self):
        with self.lock.open("a") as stream:
            stream.write(
                '[[package]]\nname="missing"\nversion="1"\n'
                'source="registry+https://github.com/rust-lang/crates.io-index"\n'
                'checksum="missing-checksum"\n'
            )
        with self.assertRaisesRegex(ValueError, "full lockfile"):
            sources.validate_vendor(self.vendor, self.lock)

    def test_symlink_source_rejected(self):
        (self.crate / "escape").symlink_to(self.root)
        with self.assertRaisesRegex(ValueError, "Symlink"):
            sources.validate_vendor(self.vendor, self.lock)

    def test_registry_url_rejects_host_and_credentials(self):
        for url in [
            "http://files.pythonhosted.org/source.tar.gz",
            "https://files.pythonhosted.org.evil.example/source.tar.gz",
            "https://user:password@files.pythonhosted.org/source.tar.gz",
        ]:
            with self.assertRaises(ValueError):
                sources.checked_url(url, {"files.pythonhosted.org"})

    def test_source_filename_rejects_escape(self):
        for name in ["../source.tar.gz", "/source.tar.gz", ".."]:
            with self.assertRaises(ValueError):
                sources.filename(name)

    def test_detector_source_filter_omits_weights_artwork_and_fonts(self):
        for path in [
            "models/model.onnx",
            "data/examples/fonts/msgothic.ttc",
            "data/doc/model.jpg",
            "examples.ipynb",
        ]:
            self.assertTrue(sources.excluded_detector_path(path))
        for path in [
            "inference.py",
            "models/yolov5/yolo.py",
            "LICENSE",
            "requirements.txt",
        ]:
            self.assertFalse(sources.excluded_detector_path(path))

    def test_cached_archive_tampering_rejected_without_network(self):
        target = self.root / "source.tar.gz"
        target.write_bytes(b"original")
        expected = sources.digest(target)
        target.write_bytes(b"changed")
        with patch.object(sources.urllib.request, "urlopen") as network:
            with self.assertRaisesRegex(ValueError, "Cached source checksum"):
                sources.download(
                    "https://files.pythonhosted.org/source.tar.gz",
                    target,
                    expected,
                    "sha256",
                    {"files.pythonhosted.org"},
                )
            network.assert_not_called()

    def test_candidates_do_not_claim_review_or_native_coverage(self):
        result = sources.candidate(
            {"ecosystem": "python", "name": "test", "version": "1"},
            self.root / "test.tar.gz",
            self.root,
            "digest",
            "registry",
        )
        self.assertEqual(result["status"], "source-candidate-review-pending")
        self.assertNotIn("reviewer", result)
        self.assertNotIn("licenseEvidence", result)


if __name__ == "__main__":
    unittest.main()
