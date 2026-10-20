"""Exercise actual git-cliff drafts on synthetic histories, including side branches."""

import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
import release_notes as notes


class ReleaseNotesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # CI explicitly prepares the real, hash-verified tool before this suite.
        notes.tool()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.git("init", "-b", "main")
        self.git("config", "user.name", "Synthetic Release Test")
        self.git("config", "user.email", "release-test@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "tag.gpgsign", "false")
        app = self.root / "apps/desktop/package.json"
        app.parent.mkdir(parents=True)
        app.write_text(json.dumps({"version": "0.4.0"}))
        self.base = self.commit("chore: old release", "base.txt")
        self.git("tag", "-a", "v0.3.0", "-m", "previous app release")
        self.output = self.root / "draft.md"

    def git(self, *args):
        return notes.git(*args, root=self.root)

    def commit(self, message, name="change.txt"):
        (self.root / name).write_text(message)
        self.git("add", ".")
        self.git("commit", "-m", message)
        return self.git("rev-parse", "HEAD")

    def generate(self, tag="v0.3.0", revision="HEAD"):
        return notes.generate(tag, revision, self.output, root=self.root)

    def test_all_commits_are_present_with_groups_reverts_merges_and_private_tags(self):
        feature = self.commit("feat: add temporary bubble action")
        self.git("tag", "macos-reviewed-seed-test")
        self.git("switch", "-c", "side")
        side = self.commit("Improve Japanese 学校 selection", "side.txt")
        self.git("switch", "main")
        fixed = self.commit("Fix: handle an empty selection", "fix.txt")
        self.git("merge", "--no-ff", "side", "-m", "Merge side changes")
        merged = self.git("rev-parse", "HEAD")
        reverted = self.commit("revert: remove temporary bubble action", "revert.txt")
        revision, count = self.generate()
        text = self.output.read_text()
        self.assertEqual(revision, reverted)
        self.assertEqual(count, 5)
        expected = [feature, side, fixed, merged, reverted]
        links = re.findall(r"/commit/([0-9a-f]{40})", text)
        self.assertEqual(Counter(links), Counter(expected))
        self.assertNotIn(self.base, links)
        for group in ("Features", "Fixes", "Reverts to review", "Other changes"):
            self.assertIn("### " + group, text)
        self.assertIn("Improve Japanese 学校 selection", text)
        self.assertIn("Added-then-reverted features are not available features", text)
        self.assertNotIn("Changes for macos-reviewed-seed", text)

    def test_exact_revision_excludes_later_commits_and_does_not_mutate_git(self):
        selected = self.commit("docs: selected target")
        later = self.commit("feat: later work", "later.txt")
        before = {
            name: self.git(*args)
            for name, args in (
                ("tags", ("show-ref", "--tags")),
                ("head", ("rev-parse", "HEAD")),
                ("status", ("status", "--porcelain")),
            )
        }
        revision, count = self.generate(revision=selected)
        self.assertEqual((revision, count), (selected, 1))
        text = self.output.read_text()
        self.assertIn("/commit/" + selected, text)
        self.assertNotIn("/commit/" + later, text)
        self.output.unlink()
        self.assertEqual(before["tags"], self.git("show-ref", "--tags"))
        self.assertEqual(before["head"], self.git("rev-parse", "HEAD"))
        self.assertEqual(before["status"], self.git("status", "--porcelain"))

    def test_existing_notes_are_never_overwritten(self):
        self.output.write_text("Reviewed notes and source notices\n")
        with self.assertRaisesRegex(ValueError, "already exists"):
            self.generate()
        self.assertEqual(self.output.read_text(), "Reviewed notes and source notices\n")

    def test_missing_private_and_nonancestor_base_tags_fail_without_a_draft(self):
        with self.assertRaises(subprocess.CalledProcessError):
            self.generate(tag="v9.9.9")
        with self.assertRaisesRegex(ValueError, "app release tag"):
            self.generate(tag="macos-reviewed-seed-test")
        self.git("switch", "-c", "future")
        self.commit("feat: other branch")
        self.git("tag", "v0.5.0")
        self.git("switch", "main")
        with self.assertRaises(subprocess.CalledProcessError):
            self.generate(tag="v0.5.0")
        self.assertFalse(self.output.exists())

    def test_empty_range_and_shallow_checkout_fail_without_a_draft(self):
        with self.assertRaisesRegex(ValueError, "No commits"):
            self.generate()
        clone = self.root / "shallow"
        self.git("clone", "--depth=1", self.root.as_uri(), str(clone))
        with self.assertRaisesRegex(ValueError, "full Git history"):
            notes.generate("v0.3.0", "HEAD", self.output, root=clone)
        self.assertFalse(self.output.exists())

    def test_untrusted_environment_cannot_filter_commits_or_redirect_output(self):
        target = self.commit("An unconventional change")
        redirected = self.root / "unexpected.md"
        with patch.dict(
            "os.environ",
            {
                "GIT_CLIFF_SKIP_COMMIT": target,
                "GIT_CLIFF_OUTPUT": str(redirected),
                "GIT_CLIFF_CONFIG": "missing.toml",
            },
        ):
            self.generate()
        self.assertIn("/commit/" + target, self.output.read_text())
        self.assertFalse(redirected.exists())

    def test_filtering_a_commit_is_detected_before_writing_a_draft(self):
        self.commit("A change without a conventional prefix")
        executable = notes.tool()
        config = (notes.ROOT / "cliff.toml").read_text()
        config = config.replace(
            "conventional_commits = false", "conventional_commits = true"
        )
        config = config.replace(
            "filter_unconventional = false", "filter_unconventional = true"
        )
        (self.root / "cliff.toml").write_text(config)
        with (
            patch.object(notes, "ROOT", self.root),
            patch.object(notes, "tool", return_value=executable),
            self.assertRaisesRegex(ValueError, "omitted or duplicated"),
        ):
            self.generate()
        self.assertFalse(self.output.exists())

    def test_tampered_cached_archive_and_executable_are_rejected(self):
        original, expected, name = notes.tool_input()
        archive = self.root / original.name
        shutil.copyfile(original, archive)
        executable = (
            archive.parent
            / archive.name.removesuffix(".tar.gz").removesuffix(".zip")
            / name
        )
        executable.parent.mkdir()
        executable.write_bytes(b"changed executable")
        with patch.object(notes, "tool_input", return_value=(archive, expected, name)):
            with self.assertRaisesRegex(ValueError, "executable differs"):
                notes.tool()
            archive.write_bytes(b"changed archive")
            with self.assertRaisesRegex(ValueError, "SHA-256"):
                notes.tool()

    def test_link_executable_is_rejected_without_extracting_archive_paths(self):
        archive = self.root / "unsafe.tar.gz"
        with tarfile.open(archive, "w:gz") as source:
            entry = tarfile.TarInfo("../../git-cliff")
            entry.type = tarfile.SYMTYPE
            entry.linkname = "/outside"
            source.addfile(entry, io.BytesIO())
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, "regular git-cliff"):
            notes.binary_bytes(archive, digest, "git-cliff")


if __name__ == "__main__":
    unittest.main()
