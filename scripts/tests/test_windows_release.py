"""Reject altered Windows inputs, leaked models, and changed installed binaries."""

import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
spec = importlib.util.spec_from_file_location(
    "windows_release", Path(__file__).parents[1] / "windows_release.py"
)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)
import windows_private_draft as draft


class WindowsReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def private_candidate(self):
        setup = self.root / "test-setup.exe"
        setup.write_bytes(b"private installer")
        record = {
            "mode": "private-test",
            "sourceRevision": "a" * 40,
            "installedAppVerified": False,
            "publicDistributionApproved": False,
            "assets": {setup.name: release.digest(setup)},
        }
        release.write_json(self.root / "windows-candidate.json", record)
        sums = {
            **record["assets"],
            "windows-candidate.json": release.digest(
                self.root / "windows-candidate.json"
            ),
        }
        (self.root / "SHA256SUMS.txt").write_text(
            "".join(f"{sha}  {name}\n" for name, sha in sums.items())
        )

    def test_private_draft_rejects_changed_candidate_and_gate_claim(self):
        self.private_candidate()
        self.assertEqual(len(draft.candidate_files(self.root, "a" * 40)), 3)
        (self.root / "test-setup.exe").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "changed"):
            draft.candidate_files(self.root, "a" * 40)
        self.private_candidate()
        record = release.read_json(self.root / "windows-candidate.json")
        record["installedAppVerified"] = True
        release.write_json(self.root / "windows-candidate.json", record)
        with self.assertRaisesRegex(ValueError, "gates differ"):
            draft.candidate_files(self.root, "a" * 40)

    def test_private_staging_never_publishes_or_creates_a_tag(self):
        self.private_candidate()
        calls = []

        def api(url, method="GET", data=None, content_type=None):
            calls.append((url, method, data))
            if url.endswith("/releases"):
                self.assertTrue(data["draft"])
                self.assertTrue(data["prerelease"])
                return {
                    "id": 1,
                    "draft": True,
                    "upload_url": "https://uploads.github.com/private{?name}",
                }
            if url.endswith("/releases/1"):
                return {
                    "draft": True,
                    "target_commitish": "a" * 40,
                    "tag_name": "windows-private-test-" + "a" * 40,
                    "html_url": "https://github.com/private-draft",
                    "assets": [
                        {
                            "name": p.name,
                            "digest": "sha256:" + release.digest(p),
                            "state": "uploaded",
                        }
                        for p in self.root.iterdir()
                        if p.name != "summary"
                    ],
                }
            return {}

        env = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_REPOSITORY": draft.REPOSITORY,
            "GITHUB_REF": "refs/heads/develop",
            "GITHUB_SHA": "a" * 40,
            "GITHUB_STEP_SUMMARY": str(self.root / "summary"),
        }
        with (
            patch.dict("os.environ", env),
            patch.object(draft, "request", side_effect=api),
            patch.object(draft, "tag_absent") as tags,
        ):
            draft.stage(self.root)
        self.assertEqual(tags.call_count, 2)
        self.assertEqual(sum(method == "POST" for _, method, _ in calls), 4)
        self.assertFalse(
            any(
                method in ("PATCH", "PUT") or "/git/refs" in url
                for url, method, _ in calls
            )
        )

    def test_actual_lock_matches_and_only_cpu_torch_is_selected(self):
        manifest = release.read_json(release.SERVICE / "windows-inputs.json")
        release.validate_lock(manifest)
        manifest["packages"][0]["version"] = "unreviewed"
        with self.assertRaisesRegex(ValueError, "manifest differ"):
            release.validate_lock(manifest)

    def test_changed_cpu_wheel_url_is_rejected(self):
        manifest = release.read_json(release.SERVICE / "windows-inputs.json")
        next(e for e in manifest["packages"] if e["name"] == "torch")["url"] = (
            "https://pypi.org/torch.whl"
        )
        with self.assertRaisesRegex(ValueError, "CPU Torch"):
            release.validate_lock(manifest)

    def test_detector_and_unapproved_weights_are_rejected_at_any_depth(self):
        for suffix in release.FORBIDDEN:
            path = self.root / ("model" + suffix)
            path.write_bytes(b"weights")
            with self.assertRaisesRegex(ValueError, "weights"):
                release.assert_no_detector(self.root)
            path.unlink()
        alias = self.root / "comictextdetector.pt.renamed"
        alias.write_bytes(b"weights")
        with self.assertRaisesRegex(ValueError, "weights"):
            release.assert_no_detector(self.root)

    def test_source_symlinks_are_rejected(self):
        (self.root / "alias").symlink_to(self.root / "missing")
        with self.assertRaisesRegex(ValueError, "symlink"):
            release.assert_no_detector(self.root)

    def test_changed_download_is_not_promoted_to_a_new_pin(self):
        source = self.root / "source"
        source.write_bytes(b"changed bytes")
        target = self.root / "target"
        with self.assertRaisesRegex(ValueError, "checksum changed"):
            release.fetch({"url": source.as_uri(), "sha256": "0" * 64}, target)
        self.assertFalse(target.exists())
        self.assertFalse(target.with_name("target.download").exists())

    def resources(self):
        notices = self.root / "notices"
        notices.mkdir()
        for name in [
            "LICENSE",
            "MODEL_CREDITS.md",
            "ASSET_NOTICES.md",
            "project-revision.txt",
            "windows-inputs.json",
            "windows-assets.json",
            "distribution.json",
        ]:
            (notices / name).write_text("test")
        runtime = self.root / "runtime"
        runtime.mkdir()
        exe = runtime / "yomimado-ocr.exe"
        exe.write_bytes(b"MZsynthetic")
        release.write_json(
            notices / "windows-inventory.json",
            {
                "binaries": [
                    {
                        "path": "runtime/yomimado-ocr.exe",
                        "sha256": release.digest(exe),
                        "imports": [],
                    }
                ]
            },
        )
        for name in ("windows-inputs.json", "windows-assets.json"):
            shutil.copy2(release.SERVICE / name, notices / name)
        release.seal_resources(self.root)
        return exe

    def verify(self, machine="0x8664"):
        with (
            patch.object(
                release,
                "read_json",
                side_effect=lambda p: (
                    [] if p.name == "windows-assets.json" else json.loads(p.read_text())
                ),
            ),
            patch.object(
                release, "pe_info", return_value={"machine": machine, "imports": []}
            ),
        ):
            return release.verify_resources(self.root)

    def test_installed_native_hash_is_bound_to_inventory(self):
        exe = self.resources()
        self.verify()
        exe.write_bytes(b"MZchanged")
        with self.assertRaisesRegex(ValueError, "resource hashes differ"):
            self.verify()

    def test_frozen_python_archive_tampering_is_rejected(self):
        self.resources()
        archive = self.root / "runtime/PYZ.pyz"
        archive.write_bytes(b"original frozen Python")
        release.seal_resources(self.root)
        self.verify()
        archive.write_bytes(b"changed Python")
        with self.assertRaisesRegex(ValueError, "resource hashes differ"):
            self.verify()

    def test_mixed_pe_architecture_is_rejected(self):
        self.resources()
        with self.assertRaisesRegex(ValueError, "architecture"):
            self.verify("0x14c")

    def test_extra_dll_is_rejected_even_if_x64(self):
        self.resources()
        (self.root / "runtime/extra.dll").write_bytes(b"MZextra")
        with self.assertRaisesRegex(ValueError, "resource hashes differ"):
            self.verify()

    def test_native_names_with_non_pe_content_are_rejected(self):
        (self.root / "invalid.pyd").write_bytes(b"not a PE")
        with self.assertRaisesRegex(ValueError, "not a PE"):
            list(release.native_files(self.root))


if __name__ == "__main__":
    unittest.main()
