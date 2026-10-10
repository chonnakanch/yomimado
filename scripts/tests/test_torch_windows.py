"""Reject unsafe source extraction, Intel backends and incorrect PE evidence."""

import importlib.util
import io
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))


def load(name, filename):
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).parents[1] / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


audit = load("torch_windows_build", "build-torch-windows.py")
probe = load("torch_windows_probe", "torch-windows-probe.py")


class TorchWindowsTests(unittest.TestCase):
    def test_windows_resources_are_distinct_from_cpp_guard_checks(self):
        cpp = {
            "file": "kernel.cpp",
            "command": "cl -DEIGEN_MPL2_ONLY /DWIN32 /D_WINDOWS -MD -c kernel.cpp",
        }
        resource = {
            "file": r"build\version.rc",
            "command": "rc /fo version.res version.rc",
        }
        self.assertEqual(
            audit.verify_commands([cpp, resource]),
            {"cppCommands": 1, "resourceCommands": 1},
        )
        for wrong in (
            [resource],
            [{**cpp, "file": "unknown.s"}],
            [{**cpp, "command": cpp["command"].replace("-MD", "-MT")}],
            [{**cpp, "command": cpp["command"].replace("-MD", "/MDd")}],
            [{**cpp, "command": cpp["command"].replace("-DEIGEN_MPL2_ONLY", "")}],
            [{**cpp, "command": cpp["command"].replace("/DWIN32", "")}],
            [{**cpp, "command": cpp["command"].replace("/D_WINDOWS", "")}],
            [cpp, {**cpp, "command": "cl /MD kernel.cpp"}],
        ):
            with self.subTest(commands=wrong), self.assertRaises(ValueError):
                audit.verify_commands(wrong)

    def test_actual_cache_must_disable_intel_and_gpu_backends(self):
        cache = "\n".join(
            [
                *[k + ":BOOL=OFF" for k in audit.OFF],
                *[k + ":BOOL=ON" for k in audit.ON],
                "BLAS:STRING=Eigen",
                "CMAKE_BUILD_TYPE:STRING=Release",
            ]
        )
        audit.verify_cache(cache)
        for wrong in (
            cache.replace("BLAS:STRING=Eigen", "BLAS:STRING=MKL"),
            cache.replace("USE_OPENMP:BOOL=OFF", "USE_OPENMP:BOOL=ON"),
            cache.replace("USE_CUDA:BOOL=OFF", ""),
            cache.replace("BUILD_PYTHON:BOOL=ON", "BUILD_PYTHON:BOOL=OFF"),
        ):
            with self.subTest(cache=wrong), self.assertRaises(ValueError):
                audit.verify_cache(wrong)

    def test_all_torch_native_inputs_must_be_amd64_without_forbidden_imports(self):
        record = {
            "path": "torch_cpu.dll",
            "machine": "0x8664",
            "imports": ["kernel32.dll"],
        }
        probe.verify_inventory([record])
        for wrong in (
            [],
            [{**record, "machine": "0xaa64"}],
            [{**record, "imports": ["libiomp5md.dll"]}],
            [{**record, "path": "mkl_rt.dll"}],
            [{**record, "imports": ["cudart64.dll"]}],
        ):
            with self.subTest(records=wrong), self.assertRaises(ValueError):
                probe.verify_inventory(wrong)

    def test_eigen_archive_rejects_traversal_and_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, kind in (
                ("../outside", tarfile.REGTYPE),
                ("eigen/link", tarfile.SYMTYPE),
            ):
                archive = root / "source.tar"
                with tarfile.open(archive, "w") as tar:
                    member = tarfile.TarInfo(name)
                    member.type = kind
                    member.linkname = "/tmp/outside"
                    tar.addfile(member, io.BytesIO())
                with self.subTest(name=name), self.assertRaises(ValueError):
                    audit.extract_eigen(archive, {"licenseFiles": {}}, root / "extract")
            self.assertFalse((root / "outside").exists())


if __name__ == "__main__":
    unittest.main()
