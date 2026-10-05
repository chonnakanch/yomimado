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
            path = output / original
            path.parent.mkdir(parents=True)
            path.write_text("libquadmath: LGPL-2.1-or-later original notice")
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

    def test_accelerate_numpy_does_not_claim_libquadmath_is_bundled(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            (output / "LICENSE.txt").write_text(
                "NumPy BSD and embedded permissive notices"
            )
            component = {
                "name": "numpy",
                "version": "1.26.4",
                "noticeFiles": ["LICENSE.txt"],
            }
            notices.supplement_python_notices(output, component)
            self.assertEqual(component["noticeFiles"], ["LICENSE.txt"])

    def test_tampered_supplement_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "fake.txt").write_text("tampered license")
            (root / "sources.json").write_text(
                json.dumps(
                    {"lgpl-2.1": {"files": [{"path": "fake.txt", "sha256": "wrong"}]}}
                )
            )
            (root / "numpy-notice.txt").write_text("libquadmath: LGPL-2.1-or-later")
            with (
                patch.object(notices, "UPSTREAM", root),
                self.assertRaisesRegex(ValueError, "checksum mismatch"),
            ):
                notices.supplement_python_notices(
                    root,
                    {
                        "name": "numpy",
                        "version": "1.26.4",
                        "noticeFiles": ["numpy-notice.txt"],
                    },
                )


class NumPyProvenanceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.site = self.root / "site/numpy"
        self.site.mkdir(parents=True)
        self.source = self.root / "source"
        self.source.mkdir()
        binary = self.site / "core.so"
        binary.write_bytes(b"built NumPy")
        self.source_file = self.source / "numpy-1.26.4.tar.gz"
        self.source_file.write_bytes(b"pinned source")
        self.notice = self.site.parent / "numpy-1.26.4.dist-info/LICENSE.txt"
        self.notice.parent.mkdir()
        self.notice.write_text("BSD, MIT, Zlib and embedded original notices")
        self.config = {"Build Dependencies": {"blas": {"name": "accelerate"}}}
        self.record = {
            "version": "1.26.4",
            "sourceSha256": hashlib.sha256(self.source_file.read_bytes()).hexdigest(),
            "recipeSha256": runtime.numpy_recipe_digest(
                runtime.LOCK.parents[2] / "scripts/build-macos-prerelease.sh"
            ),
            "mesonArgs": [
                "-Dblas=accelerate",
                "-Dlapack=accelerate",
                "-Duse-ilp64=true",
                "-Dallow-noblas=false",
            ],
            "binaries": {"core.so": hashlib.sha256(binary.read_bytes()).hexdigest()},
            "noticeSha256": hashlib.sha256(self.notice.read_bytes()).hexdigest(),
            "configuration": self.config,
        }
        self.write_record()
        pinned = patch.object(
            runtime, "NUMPY_SOURCE_SHA256", self.record["sourceSha256"]
        )
        pinned.start()
        self.addCleanup(pinned.stop)
        links = patch.object(
            runtime.subprocess,
            "check_output",
            return_value="core.so:\n\t/System/Library/Frameworks/Accelerate.framework/Accelerate (compatibility version 1.0.0)\n",
        )
        links.start()
        self.addCleanup(links.stop)

    def write_record(self):
        (self.source / "build-record.json").write_text(json.dumps(self.record))

    def check(self):
        runtime.verify_numpy(self.site, self.source, self.config)

    def test_accelerate_source_build_passes(self):
        self.check()

    def test_wrong_blas_and_external_link_rejected(self):
        self.config["Build Dependencies"]["blas"]["name"] = "openblas"
        with self.assertRaisesRegex(ValueError, "Accelerate BLAS"):
            self.check()
        self.config["Build Dependencies"]["blas"]["name"] = "accelerate"
        with (
            patch.object(
                runtime.subprocess,
                "check_output",
                return_value="core.so:\n\t@rpath/libquadmath.dylib (version)\n",
            ),
            self.assertRaisesRegex(ValueError, "non-system"),
        ):
            self.check()

    def test_replaced_binary_and_extra_library_rejected(self):
        (self.site / "core.so").write_bytes(b"stock wheel")
        with self.assertRaisesRegex(ValueError, "differs from its source build"):
            self.check()
        (self.site / "core.so").write_bytes(b"built NumPy")
        (self.site / "libquadmath.dylib").write_bytes(b"unreviewed library")
        with self.assertRaisesRegex(ValueError, "bundled native runtime"):
            self.check()

    def test_notice_and_source_tampering_rejected(self):
        self.notice.write_text("missing embedded notices")
        with self.assertRaisesRegex(ValueError, "embedded notices"):
            self.check()
        self.notice.write_text("BSD, MIT, Zlib and embedded original notices")
        self.source_file.write_bytes(b"another source")
        with self.assertRaisesRegex(ValueError, "original source"):
            self.check()

    def test_missing_binary_and_modified_recipe_rejected(self):
        (self.site / "extra.so").write_bytes(b"unrecorded")
        with self.assertRaisesRegex(ValueError, "coverage"):
            self.check()
        (self.site / "extra.so").unlink()
        self.record["recipeSha256"] = "modified"
        self.write_record()
        with self.assertRaisesRegex(ValueError, "recipe changed"):
            self.check()

    def test_frozen_provenance_and_notice_checks(self):
        self.record["sourceSha256"] = (
            "2a02aba9ed12e4ac4eb3ea9421c420301a0c6460d9830d74a9df87efa4912010"
        )
        notices_path = self.root / "notices"
        notice = notices_path / "licenses/python/numpy-1.26.4/LICENSE.txt"
        notice.parent.mkdir(parents=True)
        notice.write_bytes(self.notice.read_bytes())
        inputs = [
            {
                "buildInput": "site-packages/numpy/core.so",
                "buildInputSha256": self.record["binaries"]["core.so"],
            }
        ]
        bundle.verify_numpy_provenance(self.record, inputs, notices_path)
        inputs[0]["buildInputSha256"] = "stock wheel"
        with self.assertRaisesRegex(ValueError, "Frozen NumPy input"):
            bundle.verify_numpy_provenance(self.record, inputs, notices_path)
        inputs[0]["buildInputSha256"] = self.record["binaries"]["core.so"]
        notice.write_text("modified")
        with self.assertRaisesRegex(ValueError, "embedded notices"):
            bundle.verify_numpy_provenance(self.record, inputs, notices_path)


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
