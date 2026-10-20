"""Exercise actual git-cliff drafts on synthetic histories, including side branches."""

import copy
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


class GithubNotesTests(unittest.TestCase):
    setUp = ReleaseNotesTests.setUp
    git = ReleaseNotesTests.git
    commit = ReleaseNotesTests.commit

    def preview(self, pages=None, previous=None, body=None, revision="HEAD"):
        self.output = self.root / "notes.json"
        self.commit("feat: selected change " + self.git("rev-list", "--count", "HEAD"))
        if pages is None:
            pages = [[self.published("v0.3.0")]]
        response = {
            "body": body
            if body is not None
            else (
                "## What's Changed\n\n* Add Japanese selection by @owner in #123\n\n"
                "**Full Changelog**: https://github.com/chonnakanch/yomimado/compare/v0.3.0...v0.4.0"
            )
        }
        with patch.object(notes, "github_api", side_effect=[pages, response]) as api:
            record = notes.github_preview(
                revision, self.output, previous, root=self.root
            )
        return record, api

    @staticmethod
    def published(tag):
        return {"tag_name": tag, "draft": False, "published_at": "2026-10-20T00:00:00Z"}

    def test_selects_latest_published_ancestor_including_prereleases_across_pages(self):
        self.git("tag", "v0.3.1-beta.2")
        self.git("switch", "-c", "other")
        self.commit("other branch", "other.txt")
        self.git("tag", "v0.3.9")
        self.git("switch", "main")
        record, api = self.preview(
            pages=[
                [
                    self.published("v0.3.0"),
                    {**self.published("v0.3.8"), "draft": True},
                    self.published("macos-reviewed-seed-test"),
                    self.published("v0.5.0"),
                    self.published("v0.4.0"),
                ],
                [self.published("v0.3.1-beta.2"), self.published("v0.3.9")],
            ]
        )
        self.assertEqual(record["previousTag"], "v0.3.1-beta.2")
        self.assertEqual(record["sourceRevision"], self.git("rev-parse", "HEAD"))
        self.assertIn("--paginate", api.call_args_list[0].args)
        request = api.call_args_list[1].args
        self.assertIn("previous_tag_name=v0.3.1-beta.2", request)
        self.assertIn("target_commitish=" + record["sourceRevision"], request)
        self.assertEqual(request[0:2], ("--method", "POST"))
        self.assertIn("/releases/generate-notes", request[2])
        self.assertIn("#123", record["changes"])
        preview = self.output.with_suffix(".md").read_text()
        self.assertEqual(preview.count("**Full Changelog**:"), 1)
        self.assertTrue(preview.rstrip().endswith(record["comparison"]))
        self.assertNotIn("Both exact CI installers", preview)
        self.assertEqual(self.git("tag", "--list", "v0.4.0"), "")

    def test_explicit_base_must_be_published_and_ancestral(self):
        for tag in ("v0.2.0", "macos-reviewed-seed-test"):
            with (
                self.subTest(tag=tag),
                self.assertRaisesRegex(
                    ValueError, "app release tag|published app release"
                ),
            ):
                self.preview(previous=tag)
        self.git("switch", "-c", "unmerged")
        self.commit("unmerged", "unmerged.txt")
        self.git("tag", "v0.3.5")
        self.git("switch", "main")
        with self.assertRaisesRegex(ValueError, "ancestor"):
            self.preview(pages=[[self.published("v0.3.5")]], previous="v0.3.5")
        self.assertFalse(self.output.exists())

    def test_no_published_base_or_empty_response_does_not_write_preview(self):
        for pages, body, message in (
            ([], None, "ancestor"),
            (None, "", "no release-note content"),
        ):
            with self.subTest(pages=pages), self.assertRaisesRegex(ValueError, message):
                self.preview(pages=pages, body=body)
            self.assertFalse(self.output.exists())

    def test_existing_output_and_existing_target_on_another_commit_are_rejected(self):
        self.output = self.root / "notes.json"
        self.output.with_suffix(".md").write_text("retained preview")
        with self.assertRaisesRegex(ValueError, "new .json"):
            notes.github_preview("HEAD", self.output, root=self.root)
        self.output.with_suffix(".md").unlink()
        self.git("tag", "v0.4.0")
        with self.assertRaisesRegex(ValueError, "different source"):
            self.preview()
        self.assertFalse(self.output.exists())

    def test_exact_target_excludes_later_source_and_existing_tag_must_match(self):
        target = self.commit("selected source")
        self.git("tag", "v0.4.0")
        record, api = self.preview(revision=target)
        self.assertEqual(record["sourceRevision"], target)
        self.assertIn("target_commitish=" + target, api.call_args_list[1].args)

    def test_compose_uses_bound_preview_and_puts_comparison_last(self):
        record, _ = self.preview()
        candidate = {
            "sourceRevision": record["sourceRevision"],
            "version": "0.4.0",
            "tag": "v0.4.0",
            "prerelease": True,
            "assets": {"YomiMado_0.4.0_aarch64.dmg": "a" * 64},
        }
        digest = hashlib.sha256(self.output.read_bytes()).hexdigest()
        final = self.root / "final.md"
        notes.compose(self.output, digest, candidate, final)
        text = final.read_text()
        self.assertIn("Add Japanese selection by @owner in #123", text)
        self.assertEqual(text, self.output.with_suffix(".md").read_text())
        for unwanted in (
            "Source commit:",
            "Both exact CI installers",
            "SHA-256",
            "Installation",
            "Release verification",
        ):
            self.assertNotIn(unwanted, text)
        self.assertTrue(text.rstrip().endswith(record["comparison"]))
        self.assertEqual(text.count("**Full Changelog**:"), 1)
        with self.assertRaisesRegex(ValueError, "already exists"):
            notes.compose(self.output, digest, candidate, final)
        final.unlink()
        for field, value in (("sourceRevision", "b" * 40), ("version", "0.5.0")):
            changed = {**candidate, field: value}
            with (
                self.subTest(field=field),
                self.assertRaisesRegex(ValueError, "source/version"),
            ):
                notes.compose(self.output, digest, changed, final)
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            notes.compose(self.output, "0" * 64, candidate, final)
        changed = copy.deepcopy(record)
        changed["comparison"] = "https://example.invalid/wrong"
        self.output.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError, "comparison"):
            notes.compose(
                self.output,
                hashlib.sha256(self.output.read_bytes()).hexdigest(),
                candidate,
                final,
            )
        self.assertFalse(final.exists())


if __name__ == "__main__":
    unittest.main()
