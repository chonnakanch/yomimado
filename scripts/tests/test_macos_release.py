"""Exercise release rejection paths without Apple credentials or network access."""

import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "macos_release", Path(__file__).parents[1] / "macos-release.py"
)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


class SourceDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.notices = self.root / "notices"
        self.notices.mkdir()
        (self.notices / "LICENSE").write_text("licence")
        (self.notices / "third-party-manifest.json").write_text(
            json.dumps(
                {
                    "components": [
                        {
                            "ecosystem": "rust",
                            "name": "mpl-library",
                            "version": "1",
                            "noticeFiles": ["LICENSE"],
                        },
                    ]
                }
            )
        )
        (self.notices / "native-libraries.json").write_text(
            json.dumps({"binaries": [{"id": "native:libcodec.dylib"}]})
        )
        (self.root / "source.tar.gz").write_bytes(b"test-source")
        (self.root / "BUILD.md").write_text("build instructions")
        self.delivery = {
            "projectRevision": "revision",
            "inventorySha256": release.inventory(self.notices),
            "reviewer": "Test reviewer",
            "reviewedAt": "2026-10-05",
            "buildInstructions": "BUILD.md",
            "components": [
                {
                    "id": key,
                    "archive": "source.tar.gz",
                    "sha256": release.digest(self.root / "source.tar.gz"),
                    "licenseEvidence": "review evidence",
                    "noticeFiles": ["LICENSE"],
                }
                for key in release.source_items(self.notices)
            ],
        }

    def verify(self):
        (self.root / "source-delivery.json").write_text(json.dumps(self.delivery))
        release.verify_sources(self.notices, self.root, "revision")

    def test_complete_delivery(self):
        self.verify()

    def test_missing_native_source_is_rejected(self):
        self.delivery["components"].pop()
        with self.assertRaisesRegex(ValueError, "Missing corresponding-source"):
            self.verify()

    def test_source_tampering_is_rejected(self):
        (self.root / "source.tar.gz").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            self.verify()

    def test_stale_revision_is_rejected(self):
        self.delivery["projectRevision"] = "other"
        with self.assertRaisesRegex(ValueError, "different project revision"):
            self.verify()

    def test_duplicate_source_id_is_rejected(self):
        self.delivery["components"].append(self.delivery["components"][0])
        with self.assertRaisesRegex(ValueError, "Duplicate or unexpected"):
            self.verify()

    def test_changed_native_inventory_is_rejected(self):
        (self.notices / "native-libraries.json").write_text('{"binaries": []}')
        with self.assertRaisesRegex(
            ValueError, "different dependency/native inventory"
        ):
            self.verify()

    def test_unreviewed_source_is_rejected(self):
        self.delivery["reviewer"] = ""
        with self.assertRaisesRegex(ValueError, "review has not been recorded"):
            self.verify()

    def test_archive_escape_is_rejected(self):
        self.delivery["components"][0]["archive"] = "../outside.tar.gz"
        with self.assertRaisesRegex(ValueError, "escapes release directory"):
            self.verify()

    def test_symlink_escape_is_rejected(self):
        (self.root / "escape").symlink_to(self.root.parent)
        with self.assertRaisesRegex(ValueError, "escapes release directory"):
            release.contained(self.root, "escape/outside.tar.gz")


class SigningTests(unittest.TestCase):
    def test_rejected_notarization_returns_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            artifact = Path(temporary) / "test.dmg"
            with (
                patch.dict(os.environ, {"YOMIMADO_NOTARY_PROFILE": "test-profile"}),
                patch.object(
                    release.sys, "argv", ["macos-release.py", "notarize", str(artifact)]
                ),
                patch.object(
                    release, "run", return_value='{"id":"test-id","status":"Invalid"}'
                ),
                patch.object(release.sys, "stderr", io.StringIO()),
            ):
                self.assertEqual(release.main(), 1)
            self.assertEqual(
                json.loads(
                    artifact.with_name("test.dmg.notarization.json").read_text()
                )["status"],
                "Invalid",
            )

    def test_accepted_notarization_records_submission(self):
        with tempfile.TemporaryDirectory() as temporary:
            artifact = Path(temporary) / "test.dmg"
            with (
                patch.dict(os.environ, {"YOMIMADO_NOTARY_PROFILE": "test-profile"}),
                patch.object(
                    release.sys, "argv", ["macos-release.py", "notarize", str(artifact)]
                ),
                patch.object(
                    release, "run", return_value='{"id":"test-id","status":"Accepted"}'
                ),
            ):
                self.assertEqual(release.main(), 0)
            self.assertEqual(
                json.loads(
                    artifact.with_name("test.dmg.notarization.json").read_text()
                ),
                {"id": "test-id", "status": "Accepted"},
            )

    def test_missing_identity_fails_before_authentication(self):
        with (
            patch.dict(
                os.environ, {"YOMIMADO_APPLE_TEAM_ID": "ABCDEFGHIJ"}, clear=True
            ),
            patch.object(release.sys, "platform", "darwin"),
            patch.object(release, "run") as command,
        ):
            with self.assertRaisesRegex(ValueError, "Developer ID Application"):
                release.preflight()
            command.assert_not_called()

    def test_adhoc_signature_is_rejected(self):
        with (
            patch.dict(os.environ, {"YOMIMADO_APPLE_TEAM_ID": "ABCDEFGHIJ"}),
            patch.object(
                release,
                "run",
                side_effect=["", "Signature=adhoc\nTeamIdentifier=not set\n"],
            ),
            self.assertRaisesRegex(ValueError, "expected Developer ID"),
        ):
            release.verify_signature(Path("App"))

    def test_wrong_team_is_rejected(self):
        with (
            patch.dict(os.environ, {"YOMIMADO_APPLE_TEAM_ID": "ABCDEFGHIJ"}),
            patch.object(
                release,
                "run",
                side_effect=[
                    "",
                    "Authority=Developer ID Application: Name\nTeamIdentifier=OTHERTEAM1\nTimestamp=today\nflags=0x10000(runtime)\n",
                ],
            ),
            self.assertRaisesRegex(ValueError, "expected Developer ID"),
        ):
            release.verify_signature(Path("App"))

    def test_missing_runtime_is_rejected(self):
        with (
            patch.dict(os.environ, {"YOMIMADO_APPLE_TEAM_ID": "ABCDEFGHIJ"}),
            patch.object(
                release,
                "run",
                side_effect=[
                    "",
                    "Authority=Developer ID Application: Name\nTeamIdentifier=ABCDEFGHIJ\nTimestamp=today\n",
                ],
            ),
            self.assertRaisesRegex(ValueError, "hardened runtime"),
        ):
            release.verify_signature(Path("App"))

    def test_missing_secure_timestamp_is_rejected(self):
        with (
            patch.dict(os.environ, {"YOMIMADO_APPLE_TEAM_ID": "ABCDEFGHIJ"}),
            patch.object(
                release,
                "run",
                side_effect=[
                    "",
                    "Authority=Developer ID Application: Name\nTeamIdentifier=ABCDEFGHIJ\nflags=0x10000(runtime)\n",
                ],
            ),
            self.assertRaisesRegex(ValueError, "secure timestamp"),
        ):
            release.verify_signature(Path("App"))

    def test_nested_signing_skips_symlink_aliases(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "inner").mkdir()
            binary = root / "inner/lib.dylib"
            binary.write_bytes(b"\xcf\xfa\xed\xfe" + b"binary")
            (root / "alias").symlink_to(binary)
            (root / "weights.bin").write_bytes(b"weights")
            self.assertEqual(release.macho_files(root), [binary])

    def test_deployment_version_ignores_build_tool_version(self):
        commands = """Load command 1
      cmd LC_BUILD_VERSION
    minos 14.0
      sdk 15.0
     tool LD
  version 1900.180.0
Load command 2
      cmd LC_VERSION_MIN_MACOSX
  version 11.1
      sdk 11.3
"""
        self.assertEqual(release.minimum_versions(commands), [(14, 0, 0), (11, 1, 0)])


if __name__ == "__main__":
    unittest.main()
