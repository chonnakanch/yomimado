"""Exercise shared release rules and macOS reviewed-runtime/artifact gates."""

import copy
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))

spec = importlib.util.spec_from_file_location(
    "ci", Path(__file__).parents[1] / "macos-ci-release.py"
)
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)


class VersionTests(unittest.TestCase):
    def test_runtime_preflight_cli_propagates_stale_seed_rejection(self):
        with (
            patch("sys.argv", ["macos-ci-release.py", "verify-reuse"]),
            patch.object(ci, "git", return_value="services/ocr/app/pipeline.py"),
            self.assertRaisesRegex(ValueError, "new seed"),
        ):
            ci.main()

    @staticmethod
    def bumped(path, text, version):
        if path.endswith(".json"):
            data = json.loads(text)
            data["version"] = version
            if path.endswith("package-lock.json"):
                data["packages"][""]["version"] = version
            return json.dumps(data)
        return re.sub(
            r'(name = "yomimado"\nversion = )"[^"\n]+"',
            lambda match: match[1] + f'"{version}"',
            text,
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
        self.assertEqual(ci.version(self.root), ci.version(ci.ROOT))
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
        value = json.loads(path.read_text())
        value["version"] = "9.9.8" if value["version"] == "9.9.9" else "9.9.9"
        path.write_text(json.dumps(value))
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

    def test_release_notes_tooling_is_independent_of_frozen_runtime(self):
        paths = ("scripts/release_notes.py",)
        with patch.object(ci, "git", return_value="\n".join(paths)):
            ci.verify_reuse()
        for path in (
            "scripts/unreviewed-runtime.py",
            "THIRD_PARTY_LICENSES/release-tools/unreviewed-input.json",
            "services/ocr/app/pipeline.py",
        ):
            with (
                self.subTest(path=path),
                patch.object(ci, "git", return_value=path),
                self.assertRaisesRegex(ValueError, "new seed"),
            ):
                ci.verify_reuse()

    def test_tray_feature_alone_preserves_reviewed_runtime_dependencies(self):
        path = "apps/desktop/src-tauri/Cargo.toml"
        after = (ci.ROOT / path).read_text()
        before = after.replace(', "tray-icon"', "")
        self.assertNotEqual(ci.normalized(path, before), ci.normalized(path, after))
        with patch.object(ci, "git", side_effect=[path, before, after]):
            ci.verify_reuse()
        for changed in (
            after.replace('"tray-icon"', '"tray-icon", "image-png"'),
            after.replace('"tray-icon"', '"tray-icon", "tray-icon"'),
            after.replace('version = "2.11"', 'version = "2.12"'),
            after.replace('base64 = "0.22"', 'base64 = "0.23"'),
            after.replace('"macos-private-api", ', ""),
        ):
            with (
                self.subTest(config=changed),
                patch.object(ci, "git", side_effect=[path, before, changed]),
                self.assertRaisesRegex(ValueError, "new seed"),
            ):
                ci.verify_reuse()

    def test_tray_source_file_scope_does_not_allow_unreviewed_build_inputs(self):
        for path in (
            "apps/desktop/src-tauri/build.rs",
            "apps/desktop/src-tauri/windows-app-manifest.xml",
            "apps/desktop/src-tauri/icons/tray-template.png",
            "apps/desktop/src-tauri/icons/tray-windows.png",
            "scripts/generate_tray_icons.py",
            "THIRD_PARTY_LICENSES/system-tray-review.md",
        ):
            with self.subTest(path=path), patch.object(ci, "git", return_value=path):
                ci.verify_reuse()
        for path in (
            "apps/desktop/src-tauri/icons/unreviewed.png",
            "apps/desktop/src-tauri/tauri.release.conf.json",
            "scripts/build-macos-prerelease.sh",
            "services/ocr/app/pipeline.py",
            "services/ocr/requirements-macos-release.txt",
        ):
            with (
                self.subTest(path=path),
                patch.object(ci, "git", return_value=path),
                self.assertRaisesRegex(ValueError, "new seed"),
            ):
                ci.verify_reuse()

    def test_windows_only_preparation_does_not_change_macos_runtime_scope(self):
        for path in (
            "services/ocr/windows-inputs.json",
            "services/ocr/windows_packaged_main.py",
            "scripts/windows_python.py",
            "scripts/release_dictionaries.py",
            "scripts/verify-windows-ui.ps1",
            "scripts/windows-ui-driver.ps1",
            ".github/workflows/windows-onnx-prototype.yml",
            "scripts/onnx-probe-inputs.json",
            "scripts/onnx_generation.py",
            "scripts/onnx_detector.py",
            "scripts/onnx_runtime.py",
            "scripts/export_onnx_models.py",
            "scripts/verify_onnx_models.py",
            "scripts/prepare_windows_onnx.py",
            "THIRD_PARTY_LICENSES/windows-onnx-probe/coloredlogs/LICENSE.txt",
            "THIRD_PARTY_LICENSES/windows-onnx-probe/flatbuffers/LICENSE",
            "THIRD_PARTY_LICENSES/windows-onnx-probe/humanfriendly/LICENSE.txt",
            "THIRD_PARTY_LICENSES/windows-onnx-probe/pyreadline3/LICENSE.md",
            "THIRD_PARTY_LICENSES/windows-onnx-probe/ml_dtypes/LICENSE",
            "THIRD_PARTY_LICENSES/windows-onnx-probe/ml_dtypes/LICENSE.eigen",
            "THIRD_PARTY_LICENSES/windows-onnx-probe/onnx/LICENSE",
            "THIRD_PARTY_LICENSES/windows-onnx-probe/onnxruntime/LICENSE",
            "THIRD_PARTY_LICENSES/windows-onnx-probe/onnxruntime/ThirdPartyNotices.txt",
            ".github/workflows/windows-geos-audit.yml",
            "scripts/build-geos-windows.py",
            "scripts/geos-windows-probe.py",
            ".github/workflows/windows-opencv-audit.yml",
            "scripts/build-opencv-windows.py",
            "scripts/opencv-windows-probe.py",
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

    def test_repository_instructions_and_ignore_rules_are_source_only(self):
        for path in ("AGENTS.md", ".gitignore"):
            with self.subTest(path=path), patch.object(ci, "git", return_value=path):
                ci.verify_reuse()

    def test_cleanup_allows_only_deletion_of_generated_files_and_unused_icons(self):
        paths = (
            "services/ocr/yomimado_ocr.egg-info/SOURCES.txt",
            "apps/desktop/src-tauri/gen/schemas/desktop-schema.json",
            "apps/desktop/src-tauri/icons/android/mipmap-hdpi/ic_launcher.png",
            "apps/desktop/src-tauri/icons/placeholder.svg",
        )
        changes = "\n".join(paths)
        with patch.object(ci, "git", side_effect=[changes, changes]):
            ci.verify_reuse()
        for path in paths:
            with (
                self.subTest(path=path),
                patch.object(ci, "git", side_effect=[path, ""]),
                self.assertRaisesRegex(ValueError, "new seed"),
            ):
                ci.verify_reuse()
        with (
            patch.object(
                ci, "git", return_value="apps/desktop/src-tauri/icons/icon.icns"
            ),
            self.assertRaisesRegex(ValueError, "new seed"),
        ):
            ci.verify_reuse()


class FrontendDataReuseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.command("init", "-q")
        self.command("config", "user.name", "Test")
        self.command("config", "user.email", "test@example.invalid")
        runtime = self.root / "services/ocr/app/pipeline.py"
        runtime.parent.mkdir(parents=True)
        runtime.write_text("# original frozen service\n")
        self.commit()
        seed = ci.git("rev-parse", "HEAD", root=self.root)
        seed_patch = patch.object(ci, "SEED_REVISION", seed)
        seed_patch.start()
        self.addCleanup(seed_patch.stop)
        self.originals = {}
        for path in ci.FRONTEND_DATA_HASHES:
            content = ci.committed_bytes(path)
            self.originals[path] = content
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        self.commit()

    def command(self, *args):
        subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True)

    def commit(self):
        self.command("add", ".")
        self.command("commit", "-qm", "test source")

    def test_exact_frontend_data_and_changelog_preserve_frozen_runtime(self):
        (self.root / "CHANGELOG.md").write_text("# Release notes\n")
        self.commit()
        ci.verify_reuse(self.root)

    def test_every_data_notice_and_generator_pin_is_enforced(self):
        for path, content in self.originals.items():
            with self.subTest(path=path):
                target = self.root / path
                target.write_bytes(content + b"\n")
                self.commit()
                with self.assertRaisesRegex(ValueError, "review hash changed"):
                    ci.verify_reuse(self.root)
                target.write_bytes(content)
                self.commit()

    def test_guard_uses_committed_data_not_dirty_worktree(self):
        path = "THIRD_PARTY_LICENSES/jlpt/LICENSE.txt"
        (self.root / path).write_text("licence removed")
        ci.verify_reuse(self.root)
        self.commit()
        with self.assertRaisesRegex(ValueError, "review hash changed"):
            ci.verify_reuse(self.root)

    def test_additional_third_party_data_is_not_allowlisted(self):
        (self.root / "THIRD_PARTY_LICENSES/jlpt/unreviewed.json").write_text("{}")
        self.commit()
        with self.assertRaisesRegex(ValueError, "new seed"):
            ci.verify_reuse(self.root)

    def test_valid_frontend_data_cannot_hide_changed_frozen_code(self):
        (self.root / "services/ocr/app/pipeline.py").write_text("# changed runtime\n")
        self.commit()
        with self.assertRaisesRegex(ValueError, "new seed"):
            ci.verify_reuse(self.root)

    def test_pr_checks_keep_version_validation_without_blocking_on_old_seed(self):
        text = (ci.ROOT / ".github/workflows/checks.yml").read_text()
        job = text.split("  release-tools:\n", 1)[1].split("  native:\n", 1)[0]
        self.assertIn("          fetch-depth: 0\n", job)
        self.assertIn("          python scripts/macos-ci-release.py plan\n", job)
        self.assertNotIn("python scripts/macos-ci-release.py verify-reuse", job)
        self.assertIn("test_macos_seed.py", job)
        step = job.split(
            "      - name: Check release version consistency\n",
            1,
        )[1].split("      - name:", 1)[0]
        self.assertNotIn("if:", step)
        self.assertNotIn("continue-on-error", step)
        self.assertIn("needs: [frontend, service, release-tools, native]", text)


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

    def package_fixture(self, root, seed_version=None, backend="torch"):
        sources, notices, output = (root / n for n in ("sources", "notices", "output"))
        for path in (sources, notices, output):
            path.mkdir()
        (sources / "README.md").write_text("synthetic source delivery")
        (output / "YomiMado_0.4.0_aarch64.dmg").write_bytes(b"synthetic installer")
        archive = None
        if seed_version is not None:
            cache = root / "services/ocr/build/translation-components"
            cache.mkdir(parents=True)
            archive = cache / f"YomiMado_{seed_version}_translation_{backend}.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("model/config.json", b"{}")
            files = {
                "model/config.json": {
                    "bytes": 2,
                    "sha256": hashlib.sha256(b"{}").hexdigest(),
                }
            }
            ci.write_json(
                notices / "translation-component.json",
                {
                    "schemaVersion": 1,
                    "backend": backend,
                    "id": hashlib.sha256(
                        json.dumps(files, sort_keys=True).encode()
                    ).hexdigest(),
                    "files": files,
                    "archive": {
                        "url": f"https://github.com/chonnakanch/yomimado/releases/download/v{seed_version}/{archive.name}",
                        "sha256": ci.digest(archive),
                        "bytes": archive.stat().st_size,
                    },
                },
            )
        return sources, notices, output, archive

    def run_package(self, root, sources, notices, output):
        with (
            patch.object(ci, "ROOT", root),
            patch.object(ci, "version", return_value="0.4.0"),
            patch.object(ci, "git", return_value="a" * 40),
            patch.object(sys, "path", [str(Path(__file__).parents[1]), *sys.path]),
        ):
            return ci.package(output, sources, notices)

    def test_package_and_verify_reused_and_same_version_optional_components(self):
        for seed_version in ("0.3.0", "0.4.0"):
            with self.subTest(seed=seed_version), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                sources, notices, output, archive = self.package_fixture(
                    root, seed_version
                )
                original_manifest = (
                    notices / "translation-component.json"
                ).read_bytes()
                record = self.run_package(root, sources, notices, output)
                name = "YomiMado_0.4.0_translation_torch.zip"
                self.assertEqual(record["assets"][name], ci.digest(archive))
                self.assertEqual((output / name).read_bytes(), archive.read_bytes())
                self.assertEqual(
                    (notices / "translation-component.json").read_bytes(),
                    original_manifest,
                )
                self.assertIs(record["optionalTranslation"], True)
                ci.verify_artifact(output, record)
                with tarfile.open(output / "YomiMado_0.4.0_notices.tar.gz") as bundle:
                    self.assertEqual(
                        bundle.extractfile(
                            "YomiMado-notices/translation-component.json"
                        ).read(),
                        original_manifest,
                    )
                with (
                    patch(
                        "sys.argv",
                        [
                            "macos-ci-release.py",
                            "verify-artifact",
                            "--directory",
                            str(output),
                            "--expected",
                            json.dumps(record),
                        ],
                    ),
                    patch.dict("os.environ", {"GITHUB_SHA": "a" * 40}),
                ):
                    ci.main()

    def test_package_without_optional_component_still_verifies(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sources, notices, output, _ = self.package_fixture(root)
            record = self.run_package(root, sources, notices, output)
            self.assertNotIn("optionalTranslation", record)
            ci.verify_artifact(output, record)

    def test_reused_component_tampering_cannot_be_hidden_by_current_filename(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sources, notices, output, archive = self.package_fixture(root, "0.3.0")
            content = archive.read_bytes()
            archive.write_bytes(b"x" + content[1:])
            with self.assertRaisesRegex(ValueError, "archive differs"):
                self.run_package(root, sources, notices, output)

    def test_macos_package_rejects_an_onnx_component(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sources, notices, output, _ = self.package_fixture(root, "0.3.0", "onnx")
            with self.assertRaisesRegex(ValueError, "Torch"):
                self.run_package(root, sources, notices, output)

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
                "name": "desktop-release",
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
            {"name": "desktop-release", "protection_rules": []},
            {
                "name": "desktop-release",
                "protection_rules": [{"type": "required_reviewers", "reviewers": []}],
            },
        ):
            with self.assertRaisesRegex(ValueError, "required reviewer"):
                ci.verify_environment(data, policies)

    def test_environment_rejects_bypass_and_broad_branch_rules(self):
        data = {
            "name": "desktop-release",
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
        for name in ("macos-release", "unprotected-release"):
            with (
                self.subTest(environment=name),
                self.assertRaisesRegex(ValueError, "desktop-release"),
            ):
                ci.verify_environment({**data, "name": name}, policies)
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
            for path in ci.FRONTEND_DATA_HASHES:
                target = checkout / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(ci.committed_bytes(path))
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
            followup = result["ciFollowup"]
            self.assertIn("not extended", followup["scope"])
            self.assertEqual(followup["frontendData"]["license"], "CC-BY-SA-4.0")
            self.assertEqual(followup["frontendData"]["files"], ci.FRONTEND_DATA_HASHES)
            self.assertEqual(
                ci.read_json(output / "source-delivery.worksheet.json")["components"][
                    0
                ],
                result["components"][0],
            )
            self.assertIn(
                "frontend-jlpt/THIRD_PARTY_LICENSES/jlpt/LICENSE.txt",
                result["components"][0]["noticeFiles"],
            )
            for path, checksum in ci.FRONTEND_DATA_HASHES.items():
                self.assertEqual(ci.digest(notices / "frontend-jlpt" / path), checksum)
                self.assertEqual(
                    ci.digest(output / "notices/frontend-jlpt" / path), checksum
                )
            self.assertEqual(
                ci.read_json(notices / "frontend-data.json"), followup["frontendData"]
            )
            self.assertEqual(
                (notices / "project-revision.txt").read_text().strip(), revision
            )
            self.assertFalse((output / "old.tar.gz").exists())
            with tarfile.open(output / result["components"][0]["archive"]) as archive:
                self.assertEqual(
                    archive.extractfile("yomimado/feature.txt").read(),
                    b"merged feature",
                )
                for path in ci.FRONTEND_DATA_HASHES:
                    self.assertEqual(
                        archive.extractfile("yomimado/" + path).read(),
                        ci.committed_bytes(path),
                    )

            # A dynamically selected seed follows its own source, not the
            # migration fallback; retain that selection inside shipped sources.
            original.update(
                projectRevision=revision,
                reviewer="chonnakanch",
                reviewedAt="2020-01-01",
            )
            ci.write_json(seed / "source-delivery.json", original)
            ci.write_json(notices / "source-delivery.json", original)
            chosen = {
                "sourceRevision": revision,
                "seed": {
                    "sourceRevision": revision,
                    "approvedBy": "chonnakanch",
                    "reviewedAt": "2020-01-01",
                    "sourceDeliverySha256": ci.digest(seed / "source-delivery.json"),
                },
            }
            dynamic = root / "dynamic"
            ci.prepare_sources(seed, notices, dynamic, root=checkout, selection=chosen)
            self.assertEqual(
                ci.read_json(dynamic / "ci-followup.json")["seedRevision"], revision
            )
            self.assertEqual(
                ci.read_json(dynamic / "runtime-seed-selection.json"), chosen
            )
            self.assertEqual(
                ci.read_json(notices / "runtime-seed-selection.json"), chosen
            )
            (notices / "source-delivery.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "approval/delivery differs"):
                ci.prepare_sources(
                    seed, notices, root / "bad", root=checkout, selection=chosen
                )


if __name__ == "__main__":
    unittest.main()
