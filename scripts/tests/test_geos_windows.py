"""Reject unsafe source extraction and misleading Windows replacement evidence."""

import importlib.util
import io
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

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


class GeosWindowsTests(unittest.TestCase):
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
