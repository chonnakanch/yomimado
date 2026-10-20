"""Exercise GitHub PR previews and source-bound publication on synthetic histories."""

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
import release_notes as notes


class GithubNotesTests(unittest.TestCase):
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
        self.output = self.root / "notes.json"

    def git(self, *args):
        return notes.git(*args, root=self.root)

    def commit(self, message, name="change.txt"):
        (self.root / name).write_text(message)
        self.git("add", ".")
        self.git("commit", "-m", message)
        return self.git("rev-parse", "HEAD")

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

    def test_shallow_history_cannot_generate_incomplete_release_notes(self):
        clone = self.root / "shallow"
        self.git("clone", "--depth=1", self.root.as_uri(), str(clone))
        with (
            patch.object(notes, "github_api") as api,
            self.assertRaisesRegex(ValueError, "full Git history"),
        ):
            notes.github_preview("HEAD", self.output, root=clone)
        api.assert_not_called()
        self.assertFalse(self.output.exists())

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
