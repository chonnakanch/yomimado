"""Reject unsafe source extraction and misleading Windows replacement evidence."""

import copy
import importlib.util
import io
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request

sys.path.insert(0, str(Path(__file__).parents[1]))
spec = importlib.util.spec_from_file_location(
    "geos_windows", Path(__file__).parents[1] / "build-geos-windows.py"
)
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
probe_spec = importlib.util.spec_from_file_location(
    "geos_probe", Path(__file__).parents[1] / "geos-windows-probe.py"
)
probe = importlib.util.module_from_spec(probe_spec)
probe_spec.loader.exec_module(probe)
installed_spec = importlib.util.spec_from_file_location(
    "geos_installed", Path(__file__).parents[1] / "geos-installed-windows.py"
)
installed = importlib.util.module_from_spec(installed_spec)
installed_spec.loader.exec_module(installed)


class GeosWindowsTests(unittest.TestCase):
    def test_private_input_requires_real_reviewer_without_bypass_or_other_branch(self):
        environment = {
            "name": installed.INPUT_ENVIRONMENT,
            "can_admins_bypass": False,
            "deployment_branch_policy": {
                "protected_branches": False,
                "custom_branch_policies": True,
            },
            "protection_rules": [
                {"type": "required_reviewers", "reviewers": [{"id": 1}]}
            ],
        }
        policies = {"branch_policies": [{"name": "develop", "type": "branch"}]}
        installed.verify_input_protection(environment, policies)
        for key, value in (
            ("can_admins_bypass", True),
            ("protection_rules", []),
            ("name", "macos-release"),
        ):
            with self.subTest(key=key), self.assertRaises(ValueError):
                installed.verify_input_protection({**environment, key: value}, policies)
        with self.assertRaises(ValueError):
            installed.verify_input_protection(
                environment, {"branch_policies": [{"name": "*", "type": "branch"}]}
            )

    def test_draft_access_uses_fixed_identity_and_rejects_missing_or_published(self):
        release = {
            "draft": True,
            "target_commitish": installed.REVISION,
            "tag_name": "windows-private-test-" + installed.REVISION,
        }
        with patch.object(installed, "request", return_value=release) as request:
            self.assertEqual(installed.private_release(), release)
            request.assert_called_once_with(
                installed.API + "/releases/tags/" + release["tag_name"]
            )
        for key, value in (("draft", False), ("target_commitish", "a" * 40)):
            with (
                self.subTest(key=key),
                patch.object(
                    installed, "request", return_value={**release, key: value}
                ),
                self.assertRaises(ValueError),
            ):
                installed.private_release()
        for status in (403, 404):
            with (
                self.subTest(status=status),
                patch.object(
                    installed,
                    "request",
                    side_effect=HTTPError(
                        "https://api.github.com", status, "", {}, None
                    ),
                ),
                self.assertRaisesRegex(RuntimeError, "provide protected access"),
            ):
                installed.private_release()

    def test_asset_redirect_does_not_forward_token_or_accept_other_hosts(self):
        req = Request(
            "https://api.github.com/repos/example/releases/assets/1",
            headers={"Authorization": "Bearer synthetic-test"},
        )
        handler = installed.AssetRedirect()
        redirected = handler.redirect_request(
            req,
            None,
            302,
            "",
            {},
            "https://release-assets.githubusercontent.com/example",
        )
        self.assertIsNone(redirected.get_header("Authorization"))
        for url in (
            "http://release-assets.githubusercontent.com/example",
            "https://example.com/asset",
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                handler.redirect_request(req, None, 302, "", {}, url)

    def test_installed_probe_requires_exact_candidate_and_private_gates(self):
        release = {
            "draft": True,
            "target_commitish": installed.REVISION,
            "tag_name": "windows-private-test-" + installed.REVISION,
        }
        provenance = {
            "sourceRevision": installed.REVISION,
            "mode": "private-test",
            "installedAppVerified": False,
            "publicDistributionApproved": False,
            "assets": {installed.SETUP: installed.SETUP_SHA256},
        }
        installed.verify_candidate(release, provenance)
        for target, key, value in (
            ("release", "draft", False),
            ("release", "target_commitish", "a" * 40),
            ("provenance", "installedAppVerified", True),
            ("provenance", "publicDistributionApproved", True),
            ("provenance", "assets", {installed.SETUP: "b" * 64}),
        ):
            r, p = copy.deepcopy(release), copy.deepcopy(provenance)
            (r if target == "release" else p)[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                installed.verify_candidate(r, p)

    def test_installed_replacement_rejects_changed_application_or_missing_learning(
        self,
    ):
        before = {"app.exe": "a", "old.dll": "b", "wrapper.dll": "c"}
        after = {"app.exe": "a", "new.dll": "d", "wrapper.dll": "e"}
        installed.verify_changes(
            before,
            after,
            ["old.dll", "wrapper.dll"],
            {"new.dll": "d", "wrapper.dll": "e"},
        )
        with self.assertRaises(ValueError):
            installed.verify_changes(
                before,
                {**after, "app.exe": "tampered"},
                ["old.dll", "wrapper.dll"],
                {"new.dll": "d", "wrapper.dll": "e"},
            )
        expected = {"/tmp/geos.dll": "a", "/tmp/geos_c.dll": "b"}
        report = {
            "runtimeSha256": installed.RUNTIME_SHA256,
            "geometry": ["vertical", "horizontal"],
            "loadedModules": [{"path": p, "sha256": h} for p, h in expected.items()],
            **{
                k: True
                for k in (
                    "tokenization",
                    "dictionaries",
                    "kanji",
                    "uncachedTranslation",
                    "savedDataAndTranslationCacheSurvivedRestart",
                )
            },
        }
        installed.verify_smoke(report, expected)
        for key, value in (
            ("kanji", False),
            ("loadedModules", []),
            ("runtimeSha256", "c" * 64),
            ("geometry", ["horizontal"]),
        ):
            wrong = {**report, key: value}
            with self.subTest(key=key), self.assertRaises(ValueError):
                installed.verify_smoke(wrong, expected)

    def test_module_collector_excludes_its_own_executable(self):
        for name in ("geos.dll", "geos_c-hash.dll", "GEOS.DLL"):
            self.assertTrue(probe.is_geos_dll(Path(name)))
        for name in ("geos-probe.exe", "geos-helper.pyd", "msvcp140.dll"):
            self.assertFalse(probe.is_geos_dll(Path(name)))

    def report(self, paths):
        return {
            "passed": True,
            "frozen": True,
            "machine": "AMD64",
            "python": "3.11.17",
            "shapely": "2.0.7",
            "geos": "3.11.4",
            "loadedGeos": [{"path": str(p), "sha256": h} for p, h in paths.items()],
        }

    def test_actual_loaded_paths_and_hashes_are_required(self):
        expected = {
            str(Path("/tmp/geos.dll")): "a" * 64,
            str(Path("/tmp/geos_c.dll")): "b" * 64,
        }
        audit.verify_probe(self.report(expected), expected)
        for wrong in (
            {"/tmp/old/geos.dll": "a" * 64, "/tmp/geos_c.dll": "b" * 64},
            {"/tmp/geos.dll": "c" * 64, "/tmp/geos_c.dll": "b" * 64},
            {"/tmp/geos.dll": "a" * 64},
        ):
            with (
                self.subTest(wrong=wrong),
                self.assertRaisesRegex(ValueError, "paths/hashes"),
            ):
                audit.verify_probe(self.report(wrong), expected)

    def test_non_frozen_or_wrong_architecture_version_evidence_is_rejected(self):
        expected = {"/tmp/geos.dll": "a" * 64, "/tmp/geos_c.dll": "b" * 64}
        for key, value in (
            ("passed", False),
            ("frozen", False),
            ("machine", "ARM64"),
            ("python", "3.11.9"),
            ("geos", "3.12.0"),
        ):
            report = self.report(expected)
            report[key] = value
            with (
                self.subTest(key=key),
                self.assertRaisesRegex(ValueError, "pinned versions"),
            ):
                audit.verify_probe(report, expected)

    def test_replacement_uses_actual_extension_import_and_wrapper_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime, rebuilt = Path(tmp) / "runtime", Path(tmp) / "rebuilt"
            (runtime / "shapely").mkdir(parents=True)
            (runtime / "shapely.libs").mkdir()
            rebuilt.mkdir()
            for name in ("lib.pyd", "_geos.pyd", "_geometry_helpers.pyd"):
                (runtime / "shapely" / name).touch()
            for name in ("geos_c-hash.dll", "geos-oldhash.dll"):
                (runtime / "shapely.libs" / name).touch()
            for name in ("geos_c.dll", "geos.dll"):
                (rebuilt / name).touch()

            def inspect(path):
                return {
                    "machine": "0x8664",
                    "imports": ["geos_c-hash.dll"]
                    if path.suffix == ".pyd"
                    else ["geos.dll"],
                }

            plan = audit.replacement_plan(runtime, rebuilt, inspect)
            self.assertEqual(
                [dst.name for src, dst in plan["copy"]], ["geos_c-hash.dll", "geos.dll"]
            )
            with self.assertRaisesRegex(ValueError, "Non-AMD64"):
                audit.replacement_plan(
                    runtime, rebuilt, lambda p: {"machine": "0xaa64", "imports": []}
                )

            def wrong_wrapper(path):
                info = inspect(path)
                if path == rebuilt / "geos_c.dll":
                    info["imports"] = ["geos-oldhash.dll"]
                return info

            with self.assertRaisesRegex(ValueError, "rebuilt geos.dll"):
                audit.replacement_plan(runtime, rebuilt, wrong_wrapper)

    def test_parent_escape_and_symlinks_are_rejected_before_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, kind in (
                ("../outside.txt", tarfile.REGTYPE),
                ("geos-3.11.4/link", tarfile.SYMTYPE),
            ):
                archive = root / "source.tar"
                with tarfile.open(archive, "w") as tar:
                    member = tarfile.TarInfo(name)
                    member.type = kind
                    member.linkname = "/tmp/outside"
                    tar.addfile(member, io.BytesIO())
                with (
                    self.subTest(name=name),
                    self.assertRaisesRegex(ValueError, "Unsafe"),
                ):
                    audit.extract_source(archive, root / "extract")
            self.assertFalse((root / "outside.txt").exists())


if __name__ == "__main__":
    unittest.main()
