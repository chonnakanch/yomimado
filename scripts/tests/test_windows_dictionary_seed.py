"""Pinned daily dictionaries must survive upstream updates without repinning."""

import hashlib
import io
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from urllib.request import Request

sys.path.insert(0, str(Path(__file__).parents[1]))
import windows_dictionary_seed as seed


class DictionarySeedTests(unittest.TestCase):
    def test_original_hashes_and_members_are_checked_before_any_write(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            archive = root / "seed.tar.gz"
            data = {name: name.encode() for name in seed.NAMES}
            expected = {
                name: hashlib.sha256(value).hexdigest() for name, value in data.items()
            }
            with tarfile.open(archive, "w:gz") as output:
                for name, value in data.items():
                    member = tarfile.TarInfo(name)
                    member.size = len(value)
                    output.addfile(member, io.BytesIO(value))
            bad = {**expected, "JMdict_e.gz": "0" * 64}
            with self.assertRaisesRegex(ValueError, "original hash differs"):
                seed.restore(archive, root / "bad", bad)
            self.assertFalse((root / "bad").exists())
            seed.restore(archive, root / "assets", expected)
            for name, value in data.items():
                self.assertEqual((root / "assets" / name).read_bytes(), value)
            with tarfile.open(archive, "w:gz") as output:
                output.addfile(tarfile.TarInfo("../escape"), io.BytesIO())
            with self.assertRaisesRegex(ValueError, "Unexpected"):
                seed.restore(archive, root / "escape", expected)
            self.assertFalse((root / "escape").exists())

    def test_cross_host_redirect_does_not_forward_the_repository_token(self):
        original = Request(
            "https://api.github.com/repos/example/releases/assets/1",
            headers={"Authorization": "Bearer example-only", "Accept": "binary"},
        )
        redirected = seed.SafeRedirect().redirect_request(
            original,
            None,
            302,
            "Found",
            {},
            "https://release-assets.githubusercontent.com/asset",
        )
        self.assertIsNone(redirected.get_header("Authorization"))
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            seed.SafeRedirect().redirect_request(
                original, None, 302, "Found", {}, "http://example.invalid/asset"
            )


if __name__ == "__main__":
    unittest.main()
