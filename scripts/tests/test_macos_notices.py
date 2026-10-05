"""Verify native license supplements survive generated package notices."""

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "macos_notices", Path(__file__).parents[1] / "generate-macos-notices.py"
)
notices = importlib.util.module_from_spec(spec)
spec.loader.exec_module(notices)
sys.path.insert(0, str(Path(__file__).parents[1]))
runtime_spec = importlib.util.spec_from_file_location(
    "runtime_lock", Path(__file__).parents[1] / "verify-python-release-lock.py"
)
runtime = importlib.util.module_from_spec(runtime_spec)
runtime_spec.loader.exec_module(runtime)
bundle_spec = importlib.util.spec_from_file_location(
    "bundle_check", Path(__file__).parents[1] / "verify-macos-bundle.py"
)
bundle = importlib.util.module_from_spec(bundle_spec)
bundle_spec.loader.exec_module(bundle)


class NoticeSupplementTests(unittest.TestCase):
    def test_numpy_preserves_wheel_notice_and_adds_full_lgpl(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            original = "licenses/python/numpy-1.26.4/LICENSE.txt"
            component = {
                "name": "numpy",
                "version": "1.26.4",
                "noticeFiles": [original],
            }
            notices.supplement_python_notices(output, component)
            self.assertEqual(component["noticeFiles"][0], original)
            self.assertEqual(len(component["noticeFiles"]), 2)
            full = (output / component["noticeFiles"][1]).read_text()
            self.assertIn("Version 2.1, February 1999", full)
            self.assertIn("END OF TERMS AND CONDITIONS", full)

    def test_tampered_supplement_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "fake.txt").write_text("tampered license")
            (root / "sources.json").write_text(
                json.dumps(
                    {"lgpl-2.1": {"files": [{"path": "fake.txt", "sha256": "wrong"}]}}
                )
            )
            with (
                patch.object(notices, "UPSTREAM", root),
                self.assertRaisesRegex(ValueError, "checksum mismatch"),
            ):
                notices.supplement_python_notices(
                    root, {"name": "numpy", "version": "1.26.4", "noticeFiles": []}
                )


class RuntimeProvenanceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.base = self.root / "runtime"
        self.source = self.root / "source"
        self.source.mkdir()
        self.record = {
            "pythonVersion": "3.11.17",
            "opensslVersion": "3.5.9",
            "lzmaVersion": "5.8.4",
            "sources": [],
            "recipeScope": "prepare-runtime",
            "recipeSha256": runtime.runtime_recipe_digest(
                runtime.LOCK.parents[2] / "scripts/build-macos-prerelease.sh"
            ),
            "binaries": {},
            "noticeHashes": {},
        }
        pins = {}
        for name in runtime.SOURCES:
            path = self.source / name
            path.write_bytes(b"original source archive")
            pins[name] = hashlib.sha256(path.read_bytes()).hexdigest()
            self.record["sources"].append({"filename": name, "sha256": pins[name]})
        patched = patch.object(runtime, "SOURCES", pins)
        patched.start()
        self.addCleanup(patched.stop)
        for name in (
            "bin/python3.11",
            "lib/libpython3.11.dylib",
            "lib/python3.11/lib-dynload/_ssl.cpython-311-darwin.so",
        ):
            path = self.base / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"original native input")
            self.record["binaries"][name] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
        for name in runtime.NOTICES:
            path = self.source / "notices" / name
            path.parent.mkdir(exist_ok=True)
            path.write_text("original license notice")
            self.record["noticeHashes"][name] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            component = "CPython-3.11.17"
            if name == "OpenSSL-LICENSE.txt":
                component = "OpenSSL-3.5.9"
            elif name in {"liblzma-LICENSE.txt", "XZ-COPYING.txt"}:
                component = "liblzma-5.8.4"
            target = self.root / "bundled/licenses/source" / component / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
        self.write_record()
        self.frozen = [
            {
                "buildInput": "interpreter/" + Path(name).name,
                "buildInputSha256": digest,
            }
            for name, digest in self.record["binaries"].items()
        ]

    def write_record(self):
        (self.source / "build-record.json").write_text(json.dumps(self.record))

    def test_recorded_runtime_and_frozen_inputs_pass(self):
        runtime.verify_runtime(self.base, self.source)
        bundle.verify_python_provenance(self.record, self.frozen, self.root / "bundled")

    def test_replaced_interpreter_rejected(self):
        (self.base / "lib/libpython3.11.dylib").write_bytes(b"replaced binary")
        with self.assertRaisesRegex(ValueError, "binary differs"):
            runtime.verify_runtime(self.base, self.source)

    def test_added_extension_rejected(self):
        (self.base / "lib/python3.11/lib-dynload/injected.so").write_bytes(
            b"unrecorded"
        )
        with self.assertRaisesRegex(ValueError, "binary coverage"):
            runtime.verify_runtime(self.base, self.source)

    def test_changed_recipe_rejected(self):
        self.record["recipeSha256"] = "changed"
        self.write_record()
        with self.assertRaisesRegex(ValueError, "recipe changed"):
            runtime.verify_runtime(self.base, self.source)

    def test_packaging_changes_do_not_invalidate_runtime_recipe(self):
        recipe = self.root / "recipe.sh"
        recipe.write_text(
            "flags before\nif $prepare_runtime; then\ncompile runtime\nif $release; then\npackage app"
        )
        original = runtime.runtime_recipe_digest(recipe)
        recipe.write_text(
            recipe.read_text().replace("package app", "package hobby app")
        )
        self.assertEqual(runtime.runtime_recipe_digest(recipe), original)
        recipe.write_text(
            recipe.read_text().replace("compile runtime", "different runtime flags")
        )
        self.assertNotEqual(runtime.runtime_recipe_digest(recipe), original)

    def test_missing_notice_rejected(self):
        del self.record["noticeHashes"]["libmpdec-COPYRIGHT.txt"]
        self.write_record()
        with self.assertRaisesRegex(ValueError, "notice coverage"):
            runtime.verify_runtime(self.base, self.source)
        with self.assertRaisesRegex(ValueError, "notice coverage"):
            bundle.verify_python_provenance(
                self.record, self.frozen, self.root / "bundled"
            )

    def test_frozen_input_changed_rejected(self):
        self.frozen[0]["buildInputSha256"] = "changed"
        with self.assertRaisesRegex(ValueError, "Frozen Python input differs"):
            bundle.verify_python_provenance(
                self.record, self.frozen, self.root / "bundled"
            )

    def test_tampered_bundled_notice_rejected(self):
        (
            self.root / "bundled/licenses/source/OpenSSL-3.5.9/OpenSSL-LICENSE.txt"
        ).write_text("changed")
        with self.assertRaisesRegex(ValueError, "notice differs"):
            bundle.verify_python_provenance(
                self.record, self.frozen, self.root / "bundled"
            )


if __name__ == "__main__":
    unittest.main()
