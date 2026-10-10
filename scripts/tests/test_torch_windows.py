"""Reject unsafe source extraction, Intel backends and incorrect PE evidence."""

import contextlib
import hashlib
import importlib.util
import io
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
    def test_required_header_is_checked_before_compilation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            header = root / "include/ActivityType.h"
            header.parent.mkdir()
            data = b"enum class ActivityType { CPU_OP };\n"
            sha = hashlib.sha256(data).hexdigest()
            repo = {"requiredFiles": {"include/ActivityType.h": sha}}
            with self.assertRaisesRegex(ValueError, "missing or changed"):
                audit.verify_required_files(root, repo)
            header.write_bytes(data)
            self.assertEqual(
                audit.verify_required_files(root, repo), repo["requiredFiles"]
            )
            header.write_bytes(data + b"// changed\n")
            with self.assertRaisesRegex(ValueError, "missing or changed"):
                audit.verify_required_files(root, repo)

    def test_long_command_reports_progress_and_keeps_complete_log(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with (
                patch.object(audit, "BUILD", Path(tmp)),
                patch.object(audit, "PROGRESS_INTERVAL", 0.02),
                contextlib.redirect_stdout(output),
            ):
                audit.run(
                    [
                        sys.executable,
                        "-c",
                        "import time; print('[1/3] compile', flush=True); time.sleep(0.15); print('done')",
                    ],
                    "compile-test",
                )
            text = output.getvalue()
            self.assertIn("compile-test: running", text)
            self.assertIn("last output: [1/3] compile", text)
            self.assertIn("exited 0", text)
            self.assertEqual(
                (Path(tmp) / "compile-test.log").read_text(), "[1/3] compile\ndone\n"
            )

    def test_failed_command_preserves_error_and_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = io.StringIO()
            with (
                patch.object(audit, "BUILD", Path(tmp)),
                contextlib.redirect_stdout(output),
                self.assertRaisesRegex(RuntimeError, "compile-test failed"),
            ):
                audit.run(
                    [
                        sys.executable,
                        "-c",
                        "import sys; print('fatal error: missing header', file=sys.stderr); sys.exit(7)",
                    ],
                    "compile-test",
                )
            self.assertIn("exited 7", output.getvalue())
            self.assertIn("fatal error: missing header", output.getvalue())
            self.assertIn(
                "fatal error: missing header",
                (Path(tmp) / "compile-test.log").read_text(),
            )

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
