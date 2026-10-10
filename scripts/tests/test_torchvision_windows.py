"""Keep minimal torchvision source edits and CPU ABI checks fail-closed."""

import hashlib
import importlib.util
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parents[1]))


def load(name, filename):
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).parents[1] / filename
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


build = load("vision_build", "build-torchvision-windows.py")
probe = load("vision_probe", "torchvision-windows-probe.py")


class TorchvisionWindowsTests(unittest.TestCase):
    def test_pillow_original_notice_is_required_and_verified(self):
        data = b"original licence notice\n"
        sha = hashlib.sha256(data).hexdigest()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root / "pillow.whl"
            with zipfile.ZipFile(archive, "w") as wheel:
                wheel.writestr("licenses/LICENSE", data)
                wheel.writestr("../outside", data)
            destination = root / "notices"
            build.copy_pillow_notices(archive, {"licenses/LICENSE": sha}, destination)
            self.assertEqual((destination / "licenses/LICENSE").read_bytes(), data)
            for hashes in ({}, {"licenses/LICENSE": "0" * 64}, {"../outside": sha}):
                with self.subTest(hashes=hashes), self.assertRaises(ValueError):
                    build.copy_pillow_notices(archive, hashes, destination)
            self.assertFalse((root / "outside").exists())

    def test_patch_preserves_cpu_operator_extension(self):
        source = (
            "extensions = [\n        make_C_extension(),\n"
            "        make_image_extension(),\n"
            "        *make_video_decoders_extensions(),\n]\n"
        )
        self.assertEqual(
            build.patch_setup(source),
            "extensions = [\n        make_C_extension(),\n]\n",
        )
        for changed in (
            source.replace("make_image_extension", "new_image_extension"),
            source + source,
        ):
            with self.assertRaises(ValueError):
                build.patch_setup(changed)

    def test_cpu_abi_and_source_identity_are_required(self):
        torch = SimpleNamespace(
            __version__="2.8.0+cpu",
            version=SimpleNamespace(
                git_version="a1cb3cc05d46d198467bebbb6e8fba50a325d4e7", cuda=None
            ),
        )
        vision = SimpleNamespace(
            __version__="0.23.0+cpu",
            version=SimpleNamespace(
                git_version="824e8c8726b65fd9d5abdc9702f81c2b0c4c0dc8"
            ),
            extension=SimpleNamespace(
                _has_ops=lambda: True, _check_cuda_version=lambda: -1
            ),
        )
        probe.verify_versions(torch, vision)
        for obj, key, value in (
            (vision.extension, "_has_ops", lambda: False),
            (vision.extension, "_check_cuda_version", lambda: 12000),
            (vision.version, "git_version", "other"),
            (torch.version, "cuda", "12.8"),
        ):
            old = getattr(obj, key)
            setattr(obj, key, value)
            with self.assertRaises(ValueError):
                probe.verify_versions(torch, vision)
            setattr(obj, key, old)


if __name__ == "__main__":
    unittest.main()
