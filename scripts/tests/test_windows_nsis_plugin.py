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


if __name__ == "__main__":
    unittest.main()
