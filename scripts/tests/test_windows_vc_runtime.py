"""Verify unchanged canonical bytes replace every actual app-local VC input."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import windows_vc_runtime as vc


class VcRuntimeTests(unittest.TestCase):
    def test_standard_and_renamed_inputs_and_dependency_are_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "vs/VC/Redist/MSVC/test/x64/Microsoft.VC143.CRT"
            original.mkdir(parents=True)
            resources = root / "resources"
            internal = resources / "runtime/_internal"
            internal.mkdir(parents=True)
            (original / "msvcp140.dll").write_bytes(b"MZcanonical-cpp")
            (original / "vcruntime140.dll").write_bytes(b"MZcanonical-runtime")
            alias = internal / ("msvcp140-" + "a" * 32 + ".dll")
            alias.write_bytes(b"MZold-renamed")
            manifest = root / "inputs.json"
            manifest.write_text(
                json.dumps(
                    {
                        "version": "test",
                        "redistDirectory": "test/x64/Microsoft.VC143.CRT",
                        "files": {p.name: vc.digest(p) for p in original.iterdir()},
                    }
                )
            )

            def info(path):
                imports = ["vcruntime140.dll"] if path.name == "msvcp140.dll" else []
                return {"machine": "0x8664", "imports": imports}

            with (
                patch.object(vc, "MANIFEST", manifest),
                patch.object(vc, "BUILD", root / "build"),
                patch.dict(vc.os.environ, {"VSINSTALLDIR": str(root / "vs")}),
                patch.object(vc, "pe_info", side_effect=info),
            ):
                vc.stage(resources)
                self.assertEqual(alias.read_bytes(), b"MZcanonical-cpp")
                self.assertEqual(
                    (internal / "vcruntime140.dll").read_bytes(), b"MZcanonical-runtime"
                )
                self.assertEqual(len(vc.bound_inputs(resources, check_sources=True)), 2)
                alias.write_bytes(b"MZtampered")
                with self.assertRaisesRegex(ValueError, "unbound"):
                    vc.bound_inputs(resources)

    def test_unknown_runtime_names_fail_closed(self):
        allowed = {"msvcp140.dll": "sha"}
        self.assertIsNone(vc.vc_name("python311.dll", allowed))
        self.assertEqual(
            vc.vc_name("MSVCP140-" + "a" * 32 + ".dll", allowed), "msvcp140.dll"
        )
        for name in ("msvcp140-debug.dll", "vcruntime140_1.dll"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                vc.vc_name(name, allowed)


if __name__ == "__main__":
    unittest.main()
