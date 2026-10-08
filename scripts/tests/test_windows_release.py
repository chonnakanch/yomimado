"""Reject altered Windows inputs, leaked models, and changed installed binaries."""

import importlib.util
import json
import shutil
import subprocess
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

smoke_spec = importlib.util.spec_from_file_location(
    "windows_smoke", Path(__file__).parents[1] / "smoke-windows-install.py"
)
smoke = importlib.util.module_from_spec(smoke_spec)
smoke_spec.loader.exec_module(smoke)


class WindowsReleaseTests(unittest.TestCase):
    def test_desktop_rejects_console_subsystem_and_accepts_x64_gui(self):
        path = Path("yomimado.exe")
        with (
            patch.object(
                release, "pe_info", return_value={"machine": "0x8664", "subsystem": 3}
            ),
            self.assertRaisesRegex(ValueError, "opens a console"),
        ):
            release.verify_desktop_gui(path)
        with patch.object(
            release, "pe_info", return_value={"machine": "0x8664", "subsystem": 2}
        ):
            release.verify_desktop_gui(path)
        with (
            patch.object(
                release, "pe_info", return_value={"machine": "0x14c", "subsystem": 2}
            ),
            self.assertRaisesRegex(ValueError, "not x64"),
        ):
            release.verify_desktop_gui(path)

    def test_windows_powershell_diagnostics_do_not_inherit_ps7_modules(self):
        with (
            patch.dict(
                "os.environ",
                {"SystemRoot": str(self.root), "PSModulePath": "incompatible-PS7"},
            ),
            patch.object(smoke.subprocess, "check_output", return_value="[]") as query,
        ):
            self.assertEqual(smoke.loaded_modules(42, self.root / "runtime"), [])
            environment = {
                k.upper(): v for k, v in query.call_args.kwargs["env"].items()
            }
            self.assertNotIn("PSMODULEPATH", environment)
            self.assertEqual(environment["SYSTEMROOT"], str(self.root))

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

    def generated_repository(self):
        generated = self.root / "services/ocr/yomimado_ocr.egg-info/SOURCES.txt"
        generated.parent.mkdir(parents=True)
        generated.write_text("original\n")
        (self.root / "app.py").write_text("source\n")
        (self.root / ".gitignore").write_text("evidence/\n")
        for args in (
            ["init", "-q"],
            ["add", "."],
            [
                "-c",
                "user.name=Release tests",
                "-c",
                "user.email=tests@example.invalid",
                "commit",
                "-qm",
                "initial",
            ],
        ):
            subprocess.run(
                ["git", *args], cwd=self.root, check=True, capture_output=True
            )
        revision = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=self.root, encoding="utf-8"
        ).strip()
        return generated, revision

    def test_restores_only_known_generated_outputs(self):
        generated, revision = self.generated_repository()
        generated.write_text("regenerated\n")
        schema = self.root / "apps/desktop/src-tauri/gen/schemas/windows-schema.json"
        schema.parent.mkdir(parents=True)
        schema.write_text("{}")
        with (
            patch.object(release, "ROOT", self.root),
            patch.object(release, "BUILD", self.root / "evidence"),
        ):
            release.restore_generated_outputs(revision)
        self.assertEqual(generated.read_text(), "original\n")
        self.assertFalse(schema.exists())
        self.assertEqual(
            subprocess.check_output(["git", "status", "--porcelain"], cwd=self.root),
            b"",
        )

    def test_unexpected_source_change_prevents_any_restoration(self):
        generated, revision = self.generated_repository()
        generated.write_text("regenerated\n")
        (self.root / "app.py").write_text("changed source\n")
        with (
            patch.object(release, "ROOT", self.root),
            patch.object(release, "BUILD", self.root / "evidence"),
            self.assertRaisesRegex(ValueError, "Unexpected source changes"),
        ):
            release.restore_generated_outputs(revision)
        self.assertEqual(generated.read_text(), "regenerated\n")
        self.assertEqual((self.root / "app.py").read_text(), "changed source\n")

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
            if url.endswith("/releases?per_page=100"):
                return []
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

    def test_loaded_inference_modules_reject_developer_and_system_vc_runtime(self):
        runtime = self.root / "runtime"
        system = self.root / "Windows"
        for path, error in (
            (self.root / "developer/torch_cpu.dll", "external"),
            (system / "System32/msvcp140.dll", "app-local"),
            (system / "Temp/msvcp_win.dll", "app-local"),
            (runtime / "cudart64.dll", "CUDA"),
        ):
            modules = json.dumps(
                [{"name": path.name, "path": str(path), "sha256": "test"}]
            )
            with (
                patch.dict("os.environ", {"SystemRoot": str(system)}),
                patch.object(smoke.subprocess, "check_output", return_value=modules),
                self.assertRaisesRegex(RuntimeError, error),
            ):
                smoke.loaded_modules(42, runtime)

    def test_loaded_inference_modules_allow_bundled_and_os_libraries(self):
        runtime = self.root / "runtime"
        system = self.root / "Windows"
        modules = [
            {"name": p.name, "path": str(p), "sha256": "test"}
            for p in (
                runtime / "torch_cpu.dll",
                runtime / "msvcp140.dll",
                system / "System32/kernel32.dll",
                system / "System32/msvcp_win.dll",
            )
        ]
        with (
            patch.dict("os.environ", {"SystemRoot": str(system)}),
            patch.object(
                smoke.subprocess, "check_output", return_value=json.dumps(modules)
            ),
        ):
            self.assertEqual(smoke.loaded_modules(42, runtime), modules)

    def test_codec_exclusion_preserves_transitive_native_dependencies(self):
        runtime = self.root / "runtime"
        vision = runtime / "torchvision"
        vision.mkdir(parents=True)
        imports = {
            "_C.pyd": [],
            "image.pyd": ["jpeg8.dll"],
            "pillow.pyd": ["libpng16.dll"],
            "libpng16.dll": ["zlib.dll"],
            "zlib.dll": [],
            "jpeg8.dll": [],
        }
        for name in imports:
            path = (vision if name in ("_C.pyd", "image.pyd") else runtime) / name
            path.write_bytes(b"MZsynthetic-" + name.encode())
        with (
            patch.object(release, "RESOURCES", self.root),
            patch.object(
                release, "pe_info", side_effect=lambda p: {"imports": imports[p.name]}
            ),
        ):
            release.prune_unused_native()
        self.assertTrue((vision / "_C.pyd").exists())
        self.assertTrue((runtime / "libpng16.dll").exists())
        self.assertTrue((runtime / "zlib.dll").exists())
        self.assertFalse((vision / "image.pyd").exists())
        self.assertFalse((runtime / "jpeg8.dll").exists())
        self.assertEqual(
            len(release.read_json(self.root / "notices/windows-excluded-native.json")),
            2,
        )

    def test_os_exclusion_retains_app_local_vc_and_requires_system_dependencies(self):
        runtime = self.root / "runtime"
        system_root = self.root / "Windows"
        system = system_root / "System32"
        runtime.mkdir()
        system.mkdir(parents=True)
        for name in (
            "dbghelp.dll",
            "wintrust.dll",
            "ucrtbase.dll",
            "api-ms-win-crt-runtime-l1-1-0.dll",
            "vcruntime140.dll",
            "msvcp140.dll",
        ):
            (runtime / name).write_bytes(b"MZsynthetic")
        with (
            patch.object(release, "RESOURCES", self.root),
            patch.dict("os.environ", {"SystemRoot": str(system_root)}),
            patch.object(
                release, "pe_info", return_value={"machine": "0x8664", "imports": []}
            ),
        ):
            with self.assertRaisesRegex(ValueError, "OS dependency"):
                release.prune_unused_native()
            self.assertTrue((runtime / "dbghelp.dll").exists())
            for name in ("dbghelp.dll", "wintrust.dll", "ucrtbase.dll"):
                (system / name).write_bytes(b"MZsynthetic")
            release.prune_unused_native()
        self.assertEqual(
            {p.name for p in runtime.iterdir()}, {"vcruntime140.dll", "msvcp140.dll"}
        )
        removed = release.read_json(self.root / "notices/windows-excluded-native.json")
        self.assertEqual(len(removed), 4)
        self.assertTrue(all("OS component" in p["reason"] for p in removed))

    def test_changed_cpu_wheel_url_is_rejected(self):
        manifest = release.read_json(release.SERVICE / "windows-inputs.json")
        next(e for e in manifest["packages"] if e["name"] == "torch")["url"] = (
            "https://pypi.org/torch.whl"
        )
        with self.assertRaisesRegex(ValueError, "CPU Torch"):
            release.validate_lock(manifest)

    def test_incompatible_python_abi_and_arm_wheels_are_rejected(self):
        for filename in (
            "hf_xet-1.6.0-cp314-cp314t-win_amd64.whl",
            "hf_xet-1.6.0-cp38-abi3-win_arm64.whl",
        ):
            manifest = release.read_json(release.SERVICE / "windows-inputs.json")
            next(e for e in manifest["packages"] if e["name"] == "hf-xet")[
                "filename"
            ] = filename
            with self.assertRaisesRegex(ValueError, "not compatible"):
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
