"""Exercise the same-draft recovery without real credentials or publication."""

import copy
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
import desktop_release as release
import desktop_release_recovery as recovery
from test_desktop_release import ENVIRONMENT, MAIN_RULES, POLICIES, REVISION, fixtures

REPAIR_SHA = "b" * 40


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        with patch.dict(os.environ, {"GITHUB_SHA": REVISION}):
            mac, win, mr, wr = fixtures(root)
            self.record = release.combine(mac, win, root / "candidate", mr, wr)
        self.directory = root / "candidate"
        self.report = {
            "id": 123,
            "name": "YomiMado v0.1.0",
            "tag_name": "v0.1.0",
            "target_commitish": REVISION,
            "draft": True,
            "prerelease": True,
            "assets": [
                {
                    "name": p.name,
                    "state": "uploaded",
                    "digest": "sha256:" + release.digest(p),
                }
                for p in self.directory.iterdir()
            ],
        }
        self.responses = {
            recovery.API: {"default_branch": "main"},
            recovery.API + "/git/ref/heads/main": {"object": {"sha": REPAIR_SHA}},
            recovery.API + "/rules/branches/main?per_page=100": MAIN_RULES,
            recovery.API + "/environments/macos-release": ENVIRONMENT,
            recovery.API
            + "/environments/macos-release/deployment-branch-policies": POLICIES,
            recovery.API + "/git/ref/tags/v0.1.0": {
                "object": {"sha": REVISION, "type": "commit"}
            },
            recovery.API + f"/actions/runs/{recovery.RUN}": {
                "head_sha": REVISION,
                "head_branch": "main",
                "event": "push",
                "path": ".github/workflows/macos-prerelease.yml",
                "status": "completed",
                "conclusion": "failure",
            },
            recovery.API + f"/actions/runs/{recovery.RUN}/jobs?per_page=100": {
                "total_count": 6,
                "jobs": [
                    {
                        "name": n,
                        "status": "completed",
                        "conclusion": "failure" if n == "publish" else "success",
                    }
                    for n in (
                        "plan",
                        "seed-inputs",
                        "Build macOS Apple Silicon",
                        "Build Windows 11 x64 CPU installer",
                        "verify-transfer",
                        "publish",
                    )
                ],
            },
            recovery.API + f"/actions/artifacts/{recovery.ARTIFACT}": {
                "name": "verified-desktop-candidate",
                "expired": False,
                "digest": "sha256:" + recovery.ARTIFACT_SHA,
                "workflow_run": {"id": recovery.RUN, "head_sha": REVISION},
            },
            recovery.API + "/releases?per_page=100&page=1": [self.report],
            recovery.API + "/releases/123": self.report,
        }
        self.calls = []
        self.changed = "scripts/desktop_release_recovery.py"
        env = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_REPOSITORY": release.REPOSITORY,
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_SHA": REPAIR_SHA,
        }
        for mocked in (
            patch.dict(os.environ, env),
            patch.object(recovery, "SOURCE", REVISION),
            patch.object(
                recovery,
                "RECORD_SHA",
                release.digest(self.directory / "desktop-release-candidate.json"),
            ),
            patch.object(
                recovery,
                "INSTALLERS",
                {
                    n: s
                    for n, s in self.record["assets"].items()
                    if n.endswith((".dmg", "-setup.exe"))
                },
            ),
            patch.object(recovery, "git", side_effect=self.git),
            patch.object(recovery, "request", side_effect=self.request),
        ):
            mocked.start()
            self.addCleanup(mocked.stop)

    def git(self, *args):
        if args == ("rev-parse", "HEAD"):
            return REPAIR_SHA
        if args[:2] == ("diff", "--name-only"):
            return self.changed
        return ""

    def request(self, url, method="GET", data=None):
        self.calls.append((url, method, data))
        if method == "PATCH":
            self.assertEqual(url, recovery.API + "/releases/123")
            self.assertEqual(data, {"draft": False})
            return {**copy.deepcopy(self.report), "draft": False}
        self.assertEqual(method, "GET")
        return copy.deepcopy(self.responses[url])

    def assert_no_mutation(self):
        self.assertTrue(all(method == "GET" for _, method, _ in self.calls))

    def test_review_is_read_only_and_preserves_candidate_bytes(self):
        before = {p.name: release.digest(p) for p in self.directory.iterdir()}
        self.assertEqual(recovery.review_candidate(self.directory), self.record)
        self.assert_no_mutation()
        self.assertEqual(
            before, {p.name: release.digest(p) for p in self.directory.iterdir()}
        )

    def test_recovery_publishes_only_existing_release_by_id(self):
        self.assertFalse(recovery.publish_existing(self.directory)["draft"])
        writes = [c for c in self.calls if c[1] != "GET"]
        self.assertEqual(
            writes, [(recovery.API + "/releases/123", "PATCH", {"draft": False})]
        )

    def test_changed_app_runtime_or_unrelated_cleanup_cannot_recover(self):
        for path in (
            "apps/desktop/src/main.tsx",
            "README.md",
            "services/ocr/windows-inputs.json",
            "AGENTS.md",
        ):
            with (
                self.subTest(path=path),
                self.assertRaisesRegex(ValueError, "repair files"),
            ):
                self.changed = path
                recovery.publish_existing(self.directory)
        self.assert_no_mutation()

    def test_stale_main_unprotected_environment_or_changed_tag_cannot_publish(self):
        cases = [
            ("/git/ref/heads/main", {"object": {"sha": REVISION}}),
            ("/rules/branches/main?per_page=100", []),
            ("/environments/macos-release", {**ENVIRONMENT, "can_admins_bypass": True}),
            ("/git/ref/tags/v0.1.0", {"object": {"sha": REPAIR_SHA, "type": "commit"}}),
        ]
        for suffix, wrong in cases:
            key = recovery.API + suffix
            saved = self.responses[key]
            with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                self.responses[key] = wrong
                recovery.publish_existing(self.directory)
            self.responses[key] = saved
        self.assert_no_mutation()

    def test_expired_artifact_wrong_digest_or_failed_builder_cannot_publish(self):
        key = recovery.API + f"/actions/artifacts/{recovery.ARTIFACT}"
        saved = self.responses[key]
        for field, value in (
            ("expired", True),
            ("digest", "sha256:" + "0" * 64),
            ("workflow_run", {"id": 1}),
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.responses[key] = {**saved, field: value}
                recovery.publish_existing(self.directory)
        self.responses[key] = saved
        self.responses[
            recovery.API + f"/actions/runs/{recovery.RUN}/jobs?per_page=100"
        ]["jobs"][2]["conclusion"] = "failure"
        with self.assertRaisesRegex(ValueError, "build/transfer"):
            recovery.publish_existing(self.directory)
        self.assert_no_mutation()

    def test_tampered_local_file_or_uploaded_asset_cannot_publish(self):
        self.report["assets"][0]["digest"] = "sha256:" + "0" * 64
        with self.assertRaises(ValueError):
            recovery.publish_existing(self.directory)
        (self.directory / "project-sources.tar.gz").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "hash differs"):
            recovery.publish_existing(self.directory)
        self.assert_no_mutation()

    def test_published_duplicate_wrong_target_or_classification_draft_is_rejected(self):
        key = recovery.API + "/releases?per_page=100&page=1"
        for field, value in (
            ("draft", False),
            ("target_commitish", "main"),
            ("prerelease", False),
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.responses[key] = [{**self.report, field: value}]
                recovery.publish_existing(self.directory)
        self.responses[key] = [self.report, self.report]
        with self.assertRaisesRegex(ValueError, "ambiguous"):
            recovery.publish_existing(self.directory)
        self.assert_no_mutation()

    def test_workflow_keeps_owner_gate_and_no_build_or_tag_upload_path(self):
        workflow = (
            recovery.ROOT / ".github/workflows/desktop-release-resume.yml"
        ).read_text()
        review, publisher = workflow.split("\n  publish:\n", 1)
        self.assertNotIn("contents: write", review)
        self.assertIn("needs: verify-existing-candidate", publisher)
        self.assertIn("environment: macos-release", publisher)
        self.assertIn("group: desktop-main-publish", publisher)
        self.assertIn("cancel-in-progress: false", publisher)
        self.assertEqual(workflow.count("run-id: 38201230907"), 2)
        self.assertIn("refs/heads/main", review)
        for forbidden in (
            "gh release create",
            "tauri build",
            "gh release edit",
            "workflow_run:",
            "secrets.",
        ):
            self.assertNotIn(forbidden, workflow)


if __name__ == "__main__":
    unittest.main()
