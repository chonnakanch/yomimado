"""Exercise release version, reviewed-input and artifact rejection gates."""

import copy
import importlib.util
import json
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "ci", Path(__file__).parents[1] / "macos-ci-release.py"
)
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)


class VersionTests(unittest.TestCase):
    @staticmethod
    def bumped(path, text, version):
        if path.endswith(".json"):
            data = json.loads(text)
            data["version"] = version
            if path.endswith("package-lock.json"):
                data["packages"][""]["version"] = version
            return json.dumps(data)
        return text.replace(
            'name = "yomimado"\nversion = "0.1.0"',
            f'name = "yomimado"\nversion = "{version}"',
        )

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in (
            "package.json",
            "package-lock.json",
            "src-tauri/Cargo.toml",
            "src-tauri/Cargo.lock",
            "src-tauri/tauri.conf.json",
        ):
            target = self.root / "apps/desktop" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ci.ROOT / "apps/desktop" / name, target)

    def test_matching_release_and_prerelease_versions(self):
        self.assertEqual(ci.version(self.root), "0.1.0")
        originals = {p: p.read_text() for p in self.root.rglob("*") if p.is_file()}
        for app_version in ("0.1.0-alpha.1", "1.0.0", "1.0.0-beta.2", "2.1.3"):
            with self.subTest(version=app_version):
                for path, text in originals.items():
                    path.write_text(self.bumped(str(path), text, app_version))
                self.assertEqual(ci.version(self.root), app_version)

    def test_release_classification(self):
        for app_version, expected in (
            ("0.1.0", True),
            ("0.99.10", True),
            ("1.0.0-alpha.1", True),
            ("1.0.0-beta.2", True),
            ("2.0.0-rc.1", True),
            ("1.0.0", False),
            ("1.0.1", False),
            ("2.1.3", False),
            ("10.0.0", False),
        ):
            with self.subTest(version=app_version):
                self.assertIs(ci.is_prerelease(app_version), expected)

    def test_invalid_versions_cannot_select_a_release_classification(self):
        for app_version in (
            "1.0",
            "01.0.0",
            "1.0.0-beta.x",
            "1.0.0-beta.01",
            "1.0.0-foo.1",
        ):
            with (
                self.subTest(version=app_version),
                self.assertRaisesRegex(ValueError, "version"),
            ):
                ci.is_prerelease(app_version)

    def test_mismatched_version_is_rejected(self):
        path = self.root / "apps/desktop/package.json"
        path.write_text(path.read_text().replace('"0.1.0"', '"0.2.0"'))
        with self.assertRaisesRegex(ValueError, "must agree"):
            ci.version(self.root)

    def test_version_only_change_preserves_dependency_scope(self):
        for name in (
            "package.json",
            "package-lock.json",
            "src-tauri/Cargo.toml",
            "src-tauri/Cargo.lock",
            "src-tauri/tauri.conf.json",
        ):
            text = (self.root / "apps/desktop" / name).read_text()
            path = "apps/desktop/" + name
            self.assertEqual(
                ci.normalized(path, text),
                ci.normalized(path, self.bumped(path, text, "0.2.0")),
            )

    def test_dependency_change_and_ocr_change_require_new_review(self):
        path = "apps/desktop/package.json"
        before = (ci.ROOT / path).read_text()
        after = before.replace('"react": "^19.1.0"', '"react": "^20.0.0"')
        with (
            patch.object(ci, "git", side_effect=[path, before, after]),
            self.assertRaisesRegex(ValueError, "new seed"),
        ):
            ci.verify_reuse()
        with (
            patch.object(ci, "git", return_value="services/ocr/app/pipeline.py"),
            self.assertRaisesRegex(ValueError, "new seed"),
        ):
            ci.verify_reuse()

    def test_windows_only_preparation_does_not_change_macos_runtime_scope(self):
        for path in (
            "services/ocr/windows-inputs.json",
            "services/ocr/windows_packaged_main.py",
            "scripts/windows_python.py",
            "apps/desktop/src-tauri/tauri.windows-release.conf.json",
        ):
            with self.subTest(path=path), patch.object(ci, "git", return_value=path):
                ci.verify_reuse()
        for path in (
            "services/ocr/app/main.py",
            "services/ocr/packaged_main.py",
            "services/ocr/requirements-macos-release.txt",
        ):
            with (
                self.subTest(path=path),
                patch.object(ci, "git", return_value=path),
                self.assertRaisesRegex(ValueError, "new seed"),
            ):
                ci.verify_reuse()

    def test_detector_weights_rejected_even_in_desktop_sources(self):
        with (
            patch.object(ci, "git", return_value="apps/desktop/src/detector.onnx"),
            self.assertRaisesRegex(ValueError, "Model weights"),
        ):
            ci.verify_reuse()


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.record = {
            "sourceRevision": "a" * 40,
            "version": "0.1.0",
            "tag": "v0.1.0",
            "prerelease": True,
            "mode": "unnotarized-hobby",
            "installedAppVerified": False,
            "assets": {},
        }
        for suffix in ("_aarch64.dmg", "_sources.tar.gz", "_notices.tar.gz"):
            path = self.root / ("YomiMado_0.1.0" + suffix)
            path.write_bytes(b"verified input " + suffix.encode())
            checksum = ci.digest(path)
            self.record["assets"][path.name] = checksum
            (self.root / (path.name + ".sha256")).write_text(
                f"{checksum}  {path.name}\n"
            )
        ci.write_json(self.root / "release-candidate.json", self.record)

    def test_exact_artifacts_accepted(self):
        ci.verify_artifact(self.root, self.record)

    def test_release_classification_tampering_rejected(self):
        for value in (False, "true", 1, None):
            changed = copy.deepcopy(self.record)
            changed["prerelease"] = value
            ci.write_json(self.root / "release-candidate.json", changed)
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(ValueError, "provenance"),
            ):
                ci.verify_artifact(self.root, changed)

    def test_stable_artifacts_accepted_and_wrong_classification_rejected(self):
        record = copy.deepcopy(self.record)
        record.update(version="1.0.0", tag="v1.0.0", prerelease=False)
        record["assets"] = {}
        for path in list(self.root.iterdir()):
            if path.name.startswith("YomiMado_0.1.0"):
                new_name = path.name.replace("0.1.0", "1.0.0")
                path.rename(self.root / new_name)
                if not new_name.endswith(".sha256"):
                    checksum = ci.digest(self.root / new_name)
                    record["assets"][new_name] = checksum
        for name, checksum in record["assets"].items():
            (self.root / (name + ".sha256")).write_text(f"{checksum}  {name}\n")
        ci.write_json(self.root / "release-candidate.json", record)
        ci.verify_artifact(self.root, record)
        record["prerelease"] = True
        ci.write_json(self.root / "release-candidate.json", record)
        with self.assertRaisesRegex(ValueError, "provenance"):
            ci.verify_artifact(self.root, record)

    def test_added_model_rejected(self):
        (self.root / "comictextdetector.pt.onnx").write_bytes(b"model")
        with self.assertRaisesRegex(ValueError, "Unexpected"):
            ci.verify_artifact(self.root, self.record)

    def test_changed_dmg_rejected(self):
        (self.root / "YomiMado_0.1.0_aarch64.dmg").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            ci.verify_artifact(self.root, self.record)

    def test_false_installer_approval_rejected(self):
        false_record = copy.deepcopy(self.record)
        false_record["installedAppVerified"] = True
        ci.write_json(self.root / "release-candidate.json", false_record)
        with self.assertRaisesRegex(ValueError, "provenance changed"):
            ci.verify_artifact(self.root, self.record)

    def test_changed_sidecar_and_symlink_rejected(self):
        sidecar = self.root / "YomiMado_0.1.0_aarch64.dmg.sha256"
        sidecar.write_text("incorrect")
        with self.assertRaisesRegex(ValueError, "sidecar"):
            ci.verify_artifact(self.root, self.record)
        sidecar.unlink()
        sidecar.symlink_to(self.root / "release-candidate.json")
        with self.assertRaisesRegex(ValueError, "regular files"):
            ci.verify_artifact(self.root, self.record)

    def test_environment_requires_an_actual_reviewer(self):
        policies = {"branch_policies": [{"name": "main", "type": "branch"}]}
        ci.verify_environment(
            {
                "name": "macos-release",
                "can_admins_bypass": False,
                "deployment_branch_policy": {
                    "protected_branches": False,
                    "custom_branch_policies": True,
                },
                "protection_rules": [
                    {"type": "required_reviewers", "reviewers": [{"type": "User"}]}
                ],
            },
            policies,
        )
        for data in (
            {},
            {"name": "macos-release", "protection_rules": []},
            {
                "name": "macos-release",
                "protection_rules": [{"type": "required_reviewers", "reviewers": []}],
            },
        ):
            with self.assertRaisesRegex(ValueError, "required reviewer"):
                ci.verify_environment(data, policies)

    def test_environment_rejects_bypass_and_broad_branch_rules(self):
        data = {
            "name": "macos-release",
            "can_admins_bypass": False,
            "deployment_branch_policy": {
                "protected_branches": False,
                "custom_branch_policies": True,
            },
            "protection_rules": [
                {"type": "required_reviewers", "reviewers": [{"type": "User"}]}
            ],
        }
        policies = {"branch_policies": [{"name": "main", "type": "branch"}]}
        ci.verify_environment(data, policies)
        data["can_admins_bypass"] = True
        with self.assertRaisesRegex(ValueError, "no administrator bypass"):
            ci.verify_environment(data, policies)
        data["can_admins_bypass"] = False
        for rule in ({"name": "*", "type": "branch"}, {"name": "main", "type": "tag"}):
            with self.assertRaisesRegex(ValueError, "main-only"):
                ci.verify_environment(data, {"branch_policies": [rule]})


class SourceFollowupTests(unittest.TestCase):
    def test_export_matches_current_commit_and_preserves_original_approval(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            checkout, seed, notices, output = (
                root / n for n in ("checkout", "seed", "notices", "output")
            )
            checkout.mkdir()
            for args in (
                ["init", "-q"],
                ["config", "user.name", "Test"],
                ["config", "user.email", "test@example.invalid"],
            ):
                subprocess.run(["git", *args], cwd=checkout, check=True)
            (checkout / "feature.txt").write_text("merged feature")
            subprocess.run(["git", "add", "."], cwd=checkout, check=True)
            subprocess.run(
                ["git", "commit", "-qm", "feature"], cwd=checkout, check=True
            )
            revision = ci.git("rev-parse", "HEAD", root=checkout)
            seed.mkdir()
            notices.mkdir()
            (seed / "old.tar.gz").write_bytes(b"old project")
            (seed / "dependency.tar.gz").write_bytes(b"approved dependency")
            project = {"id": "project:yomimado", "archive": "old.tar.gz"}
            original = {
                "projectRevision": ci.SEED_REVISION,
                "reviewer": "Original reviewer",
                "approvalProjectRevision": "b" * 40,
                "components": [
                    project,
                    {
                        "id": "dependency",
                        "archive": "dependency.tar.gz",
                        "sha256": ci.digest(seed / "dependency.tar.gz"),
                    },
                ],
            }
            ci.write_json(seed / "source-delivery.json", original)
            ci.write_json(seed / "source-delivery.worksheet.json", original)
            ci.write_json(
                seed / "source-asset-omissions.json", {"archives": {"old.tar.gz": {}}}
            )
            for name in ("BUILD.md", "REVIEW.md"):
                (seed / name).write_text("original review instructions")
            with patch.object(ci, "verify_reuse"):
                ci.prepare_sources(seed, notices, output, root=checkout)
            result = ci.read_json(output / "source-delivery.json")
            self.assertEqual(result["projectRevision"], revision)
            self.assertEqual(result["reviewer"], original["reviewer"])
            self.assertEqual(
                result["approvalProjectRevision"], original["approvalProjectRevision"]
            )
            self.assertEqual(result["components"][1], original["components"][1])
            self.assertEqual(ci.read_json(seed / "source-delivery.json"), original)
            self.assertEqual(
                (notices / "project-revision.txt").read_text().strip(), revision
            )
            self.assertFalse((output / "old.tar.gz").exists())
            with tarfile.open(output / result["components"][0]["archive"]) as archive:
                self.assertEqual(
                    archive.extractfile("yomimado/feature.txt").read(),
                    b"merged feature",
                )


if __name__ == "__main__":
    unittest.main()
