"""Reject unbound installer plugin sources and changed template behavior."""

import copy
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import windows_nsis_plugin as plugin


class NsisPluginTests(unittest.TestCase):
    def test_spawn_tests_are_serial_without_changing_production_build(self):
        inputs = plugin.read_json(plugin.MANIFEST)
        terms = plugin.component_terms()
        commands = []

        def run(command, **_kwargs):
            commands.append(command)
            if command[:2] == ["cargo", "build"]:
                raise RuntimeError("captured build command")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "bin/HostX64/x86").mkdir(parents=True)
            (root / "bin/HostX64/x86/link.exe").touch()
            for lib in (
                "lib/x86",
                "Lib/10.0.26100.0/ucrt/x86",
                "Lib/10.0.26100.0/um/x86",
            ):
                (root / lib).mkdir(parents=True)
            with (
                patch.object(plugin.sys, "platform", "win32"),
                patch.object(plugin, "AUDIT", root),
                patch.object(plugin, "prepare", return_value=(inputs, root, root)),
                patch.object(plugin, "component_terms", return_value=terms),
                patch.object(
                    plugin, "read_json", return_value={"version": inputs["cliVersion"]}
                ),
                patch.object(
                    plugin.subprocess,
                    "check_output",
                    return_value=f"release: {inputs['rustVersion']}\n",
                ),
                patch.object(plugin.subprocess, "run", side_effect=run),
                patch.dict(
                    os.environ,
                    {
                        "VCToolsInstallDir": directory,
                        "WindowsSdkDir": directory,
                        "WindowsSDKVersion": "10.0.26100.0\\",
                    },
                ),
                self.assertRaisesRegex(RuntimeError, "captured build command"),
            ):
                plugin.stage()
        self.assertEqual(
            commands[1],
            [
                "cargo",
                "test",
                "--offline",
                "--locked",
                "--release",
                "--target",
                inputs["target"],
                "--manifest-path",
                str(root / "Cargo.toml"),
                "--workspace",
                "--features",
                "test",
                "--",
                "--test-threads=1",
            ],
        )
        self.assertEqual(
            commands[2],
            [
                "cargo",
                "build",
                "--offline",
                "--locked",
                "--release",
                "--target",
                inputs["target"],
                "--manifest-path",
                str(root / "Cargo.toml"),
                "--package",
                "nsis-tauri-utils",
            ],
        )

    def test_exact_lock_requires_all_original_sources_and_notices(self):
        original = plugin.read_json(plugin.MANIFEST)
        plugin.validate(original)
        for mutation in ("missing", "duplicate", "checksum", "notice", "target"):
            inputs = copy.deepcopy(original)
            if mutation == "missing":
                inputs["crates"].pop()
            elif mutation == "duplicate":
                inputs["crates"].append(inputs["crates"][0])
            elif mutation == "checksum":
                inputs["crates"][0]["sha256"] = "0" * 64
            elif mutation == "notice":
                inputs["crates"][0]["noticeHashes"] = {}
            else:
                inputs["target"] = "x86_64-pc-windows-msvc"
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                plugin.validate(inputs)

    def test_lock_bytes_cannot_change(self):
        with tempfile.TemporaryDirectory() as directory:
            altered = Path(directory) / "Cargo.lock"
            altered.write_bytes(plugin.LOCK.read_bytes() + b"\n")
            with (
                patch.object(plugin, "LOCK", altered),
                self.assertRaisesRegex(ValueError, "lock differs"),
            ):
                plugin.validate(plugin.read_json(plugin.MANIFEST))

    def test_template_preserves_every_other_installation_line(self):
        original = "before\n" + plugin.TEMPLATE_LINE + "\nafter\n"
        directory = Path("/private/tmp/nsis-source-plugin")
        generated = plugin.template(original, directory)
        self.assertEqual(generated.splitlines()[0], "before")
        self.assertEqual(generated.splitlines()[2], "after")
        self.assertIn(directory.resolve().as_posix(), generated)
        for changed in ("unrecognized", original + plugin.TEMPLATE_LINE):
            with self.assertRaises(ValueError):
                plugin.template(changed, directory)
        for unsafe in ("/private/tmp/$PLUGIN", '/private/tmp/"quoted'):
            with self.assertRaises(ValueError):
                plugin.template(original, Path(unsafe))

    def test_component_terms_page_and_unattended_gate_are_both_required(self):
        original = (
            f"{plugin.TEMPLATE_LINE}\n{plugin.LICENSE_PAGE}\n{plugin.PASSIVE_INIT}\n"
            "FunctionEnd\nFunction .onInstSuccess\nFunctionEnd\n"
        )
        sha = "a" * 64
        result = plugin.template(original, Path("/private/tmp/source-plugin"), sha)
        self.assertIn("!define MUI_LICENSEPAGE_CHECKBOX", result)
        self.assertIn(f'!define YOMIMADO_MICROSOFT_TERMS_SHA256 "{sha}"', result)
        self.assertIn('!error "Microsoft component terms file is required"', result)
        self.assertIn(plugin.TERMS_GATE, result)
        self.assertIn('"MicrosoftRuntimeTermsSHA256"', result)
        for changed in (
            original.replace(plugin.LICENSE_PAGE, ""),
            original.replace(plugin.PASSIVE_INIT, "Function .onInit"),
            original + "Function .onInstSuccess\n",
        ):
            with self.assertRaisesRegex(ValueError, "component-terms template"):
                plugin.template(changed, Path("/private/tmp/source-plugin"), sha)
        with self.assertRaises(ValueError):
            plugin.template(original, Path("/private/tmp/source-plugin"), '"unsafe')

    def test_changed_terms_owner_attestation_and_configuration_fail_closed(self):
        original = plugin.read_json(plugin.TERMS_MANIFEST)
        configuration = plugin.read_json(
            plugin.ROOT / "apps/desktop/src-tauri/tauri.windows-release.conf.json"
        )
        plugin.component_terms()
        for field in ("sha", "path", "owner", "approval", "configuration"):
            record = copy.deepcopy(original)
            config = copy.deepcopy(configuration)
            if field == "sha":
                record["termsSha256"] = "0" * 64
            elif field == "path":
                record["termsFile"] = "../other.txt"
            elif field == "owner":
                record["ownerLicense"]["obtainedCopyAndAcceptedTerms"] = False
            elif field == "approval":
                record["publicDistributionApproved"] = True
            else:
                config["bundle"].pop("licenseFile")
            with (
                self.subTest(field=field),
                patch.object(plugin, "read_json", side_effect=[record, config]),
                self.assertRaisesRegex(ValueError, "component terms"),
            ):
                plugin.component_terms()


if __name__ == "__main__":
    unittest.main()
