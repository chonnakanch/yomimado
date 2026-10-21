"""Exercise fixed-artifact recovery, repair scope and the protected publisher."""

import copy
import os
import stat
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
import desktop_release_recovery as recovery
import test_desktop_release as shared_tests
from test_desktop_release import ENVIRONMENT, MAIN_RULES, POLICIES, fixtures

release = recovery.release
REPAIR_SHA = "e" * 40


class RecoveryOriginTests(unittest.TestCase):
    def reports(self):
        run = {
            "id": recovery.RUN,
            "head_sha": recovery.RUN_HEAD,
            "head_branch": "release/0.5.0",
            "event": "pull_request",
            "path": ".github/workflows/release.yml",
            "status": "completed",
            "conclusion": "failure",
        }
        jobs = {
            "total_count": 6,
            "jobs": [
                {
                    "name": name,
                    "status": "completed",
                    "conclusion": "success",
                    "steps": [],
                }
                for name in (
                    "plan",
                    "seed-inputs",
                    "Build macOS Apple Silicon",
                    "Build Windows 11 x64 CPU installer",
                    "verify-transfer",
                    "publish",
                )
            ],
        }
        jobs["jobs"][-1]["conclusion"] = "failure"
        artifacts = [
            {
                "id": pin["id"],
                "name": pin["name"],
                "size_in_bytes": pin["size"],
                "digest": "sha256:" + pin["sha256"],
                "expired": False,
                "workflow_run": {"id": recovery.RUN, "head_sha": recovery.RUN_HEAD},
            }
            for pin in recovery.ARTIFACTS.values()
        ]
        return [run, jobs, *artifacts]

    def test_original_builds_and_immutable_artifact_pins_are_required(self):
        with patch.object(recovery, "request", side_effect=self.reports()) as api:
            recovery.verify_origin()
        self.assertTrue(all(len(c.args) == 1 for c in api.call_args_list))
        for scenario in (
            "wrong-run",
            "wrong-head",
            "wrong-event",
            "missing-job",
            "ambiguous-job",
            "failed-build",
            "publisher-ran",
            "expired",
            "digest",
            "size",
            "artifact-run",
        ):
            reports = self.reports()
            if scenario == "wrong-run":
                reports[0]["id"] += 1
            elif scenario == "wrong-head":
                reports[0]["head_sha"] = recovery.SOURCE
            elif scenario == "wrong-event":
                reports[0]["event"] = "workflow_dispatch"
            elif scenario == "missing-job":
                reports[1]["jobs"].pop()
            elif scenario == "ambiguous-job":
                reports[1]["jobs"][0]["name"] = "publish"
            elif scenario == "failed-build":
                reports[1]["jobs"][2]["conclusion"] = "failure"
            elif scenario == "publisher-ran":
                reports[1]["jobs"][-1]["steps"] = [{"name": "Upload"}]
            elif scenario == "expired":
                reports[2]["expired"] = True
            elif scenario == "digest":
                reports[2]["digest"] = "sha256:" + "0" * 64
            elif scenario == "size":
                reports[2]["size_in_bytes"] += 1
            else:
                reports[3]["workflow_run"]["id"] += 1
            with (
                self.subTest(scenario=scenario),
                patch.object(recovery, "request", side_effect=reports),
                self.assertRaises(ValueError),
            ):
                recovery.verify_origin()

    def test_only_manual_main_repair_changes_can_reuse_original_installers(self):
        env = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_REPOSITORY": release.REPOSITORY,
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_SHA": REPAIR_SHA,
        }
        for path in (
            "scripts/desktop_release_recovery.py",
            "apps/desktop/src/main.tsx",
            "services/ocr/app/main.py",
            "",
        ):
            answers = [REPAIR_SHA, "", "", path]
            with (
                self.subTest(path=path),
                patch.dict(os.environ, env),
                patch.object(recovery, "git", side_effect=answers),
            ):
                if path == "scripts/desktop_release_recovery.py":
                    recovery.verify_repair_scope()
                else:
                    with self.assertRaisesRegex(
                        ValueError, "explicit publication repair"
                    ):
                        recovery.verify_repair_scope()
        with (
            patch.dict(os.environ, {**env, "GITHUB_REF": "refs/pull/27/merge"}),
            self.assertRaises(ValueError),
        ):
            recovery.verify_repair_scope()

    def test_repository_requires_current_main_protection_and_green_exact_checks(self):
        checks = {
            "total_count": 1,
            "check_runs": [
                {
                    "name": "gates",
                    "head_sha": REPAIR_SHA,
                    "app": {"id": 15368},
                    "status": "completed",
                    "conclusion": "success",
                }
            ],
        }
        valid = [
            {"default_branch": "main"},
            {"object": {"sha": REPAIR_SHA}},
            MAIN_RULES,
            ENVIRONMENT,
            POLICIES,
            checks,
        ]
        for scenario in (
            "pass",
            "main-advanced",
            "unprotected",
            "no-review",
            "failed-checks",
        ):
            reports = copy.deepcopy(valid)
            if scenario == "main-advanced":
                reports[1]["object"]["sha"] = "b" * 40
            elif scenario == "unprotected":
                reports[2] = []
            elif scenario == "no-review":
                reports[3]["protection_rules"] = []
            elif scenario == "failed-checks":
                reports[-1]["check_runs"][0]["conclusion"] = "failure"
            with (
                self.subTest(scenario=scenario),
                patch.dict(os.environ, {"GITHUB_SHA": REPAIR_SHA}),
                patch.object(recovery, "request", side_effect=reports),
            ):
                if scenario == "pass":
                    recovery.verify_repository()
                else:
                    with self.assertRaises(ValueError):
                        recovery.verify_repository()


class RecoveryArchiveTests(unittest.TestCase):
    def test_hash_membership_and_regular_flat_files_before_extraction(self):
        for scenario in ("pass", "hash", "traversal", "duplicate", "link", "missing"):
            with (
                self.subTest(scenario=scenario),
                tempfile.TemporaryDirectory() as temporary,
            ):
                root = Path(temporary)
                archive = root / "notes.zip"
                with zipfile.ZipFile(archive, "w") as output:
                    if scenario == "link":
                        member = zipfile.ZipInfo("notes.json")
                        member.external_attr = (stat.S_IFLNK | 0o777) << 16
                        output.writestr(member, "/outside")
                    else:
                        output.writestr(
                            "../notes.json"
                            if scenario == "traversal"
                            else "notes.json",
                            "{}",
                        )
                    if scenario == "duplicate":
                        with self.assertWarns(UserWarning):
                            output.writestr("notes.json", "{}")
                    if scenario != "missing":
                        output.writestr("notes.md", "preview")
                pinned = {
                    "notes": {
                        "size": archive.stat().st_size,
                        "sha256": release.digest(archive),
                    }
                }
                if scenario == "hash":
                    pinned["notes"]["sha256"] = "0" * 64
                with patch.object(recovery, "ARTIFACTS", pinned):
                    if scenario == "pass":
                        recovery.extract_artifact(archive, root / "notes", "notes")
                        self.assertEqual(
                            (root / "notes/notes.md").read_text(), "preview"
                        )
                    else:
                        with self.assertRaises(ValueError):
                            recovery.extract_artifact(archive, root / "notes", "notes")
                        self.assertFalse((root / "notes").exists())


class RecoveryPublisherTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        self.env = patch.dict(os.environ, {"GITHUB_SHA": recovery.SOURCE})
        self.env.start()
        self.addCleanup(self.env.stop)
        version = patch.object(release.macos, "version", return_value="0.5.0")
        version.start()
        self.addCleanup(version.stop)
        with patch.object(shared_tests, "REVISION", recovery.SOURCE):
            mac, win, mr, wr = fixtures(self.work, "0.5.0", components=True)
        self.record = release.combine(mac, win, self.work / "candidate", mr, wr)
        pinned = patch.object(
            recovery,
            "INSTALLERS",
            {name: self.record["assets"][name] for name in recovery.INSTALLERS},
        )
        pinned.start()
        self.addCleanup(pinned.stop)
        (self.work / "notes").mkdir()
        release.write_json(
            self.work / "notes/notes.json",
            {
                "sourceRevision": recovery.SOURCE,
                "version": "0.5.0",
                "previousTag": "v0.4.0",
                "changes": "## What's Changed\n\n* Capture shortcuts (#26)",
                "comparison": "https://github.com/chonnakanch/yomimado/compare/v0.4.0...v0.5.0",
            },
        )

    def report(self, draft=True):
        return {
            "id": 123,
            "name": "YomiMado v0.5.0",
            "draft": draft,
            "tag_name": "v0.5.0",
            "target_commitish": recovery.SOURCE,
            "prerelease": True,
            "assets": [
                {
                    "name": p.name,
                    "digest": "sha256:" + release.digest(p),
                    "state": "uploaded",
                }
                for p in (self.work / "candidate").iterdir()
            ],
        }

    def run_publish(self, scenario="pass"):
        created = False
        mutations = []

        def gh(*args, **kwargs):
            nonlocal created
            created = True
            command = args[0]
            self.assertIn("--draft", command)
            self.assertIn("--prerelease", command)
            self.assertEqual(command[command.index("--target") + 1], recovery.SOURCE)

        def api(endpoint, method="GET", data=None):
            if method != "GET":
                mutations.append((method, endpoint, data))
                return self.report(False) if method == "PATCH" else {}
            if "/releases?" in endpoint:
                return [self.report()] if created else []
            if "/git/ref/tags/" in endpoint:
                return {"object": {"sha": recovery.SOURCE, "type": "commit"}}
            report = self.report()
            if scenario == "upload-tamper":
                report["assets"][0]["digest"] = "sha256:" + "0" * 64
            return report

        with (
            patch.object(
                recovery,
                "prepare",
                side_effect=lambda work: recovery.review_files(work),
            ),
            patch.object(
                recovery,
                "verify_repository",
                side_effect=[None, ValueError("main advanced")]
                if scenario == "main-advanced"
                else None,
            ),
            patch.object(
                recovery,
                "git",
                return_value="existing tag" if scenario == "tag-collision" else "",
            ),
            patch.object(recovery.subprocess, "run", side_effect=gh) as cli,
            patch.object(recovery, "request", side_effect=api),
        ):
            if scenario == "pass":
                recovery.publish(self.work)
                self.assertEqual([m[0] for m in mutations], ["POST", "PATCH"])
                self.assertEqual(mutations[0][2]["sha"], recovery.SOURCE)
                self.assertTrue(
                    (self.work / "release-notes.md")
                    .read_text()
                    .rstrip()
                    .endswith("v0.4.0...v0.5.0")
                )
            else:
                with self.assertRaises(ValueError):
                    recovery.publish(self.work)
                self.assertNotIn("PATCH", [m[0] for m in mutations])
                if scenario == "tag-collision":
                    cli.assert_not_called()
                    self.assertEqual(mutations, [])

    def test_original_files_and_notes_publish_only_after_draft_verification(self):
        self.run_publish()

    def test_download_extract_and_review_preserve_the_full_original_delivery(self):
        (self.work / "notes/notes.md").write_text("retained original preview")
        archives = {}
        pins = {}
        for index, kind in enumerate(("candidate", "notes"), 1):
            archive = self.work / f"original-{kind}.zip"
            with zipfile.ZipFile(archive, "w") as output:
                for path in (self.work / kind).iterdir():
                    output.write(path, path.name)
            archives[index] = archive.read_bytes()
            pins[kind] = {
                "id": index,
                "size": archive.stat().st_size,
                "sha256": release.digest(archive),
            }

        def download(command, *, stdout, check):
            self.assertEqual(command[:2], ["gh", "api"])
            self.assertTrue(check)
            artifact_id = int(command[-1].split("/")[-2])
            stdout.write(archives[artifact_id])

        with (
            patch.object(recovery, "ARTIFACTS", pins),
            patch.object(recovery, "verify_repair_scope"),
            patch.object(recovery, "verify_repository"),
            patch.object(recovery, "verify_origin"),
            patch.object(recovery.subprocess, "run", side_effect=download) as api,
        ):
            destination = self.work / "downloaded"
            self.assertEqual(recovery.prepare(destination), self.record)
        self.assertEqual(api.call_count, 2)
        for path in (self.work / "candidate").iterdir():
            self.assertEqual(
                path.read_bytes(), (destination / "candidate" / path.name).read_bytes()
            )
        self.assertIn(
            "Capture shortcuts (#26)", (destination / "release-notes.md").read_text()
        )

    def test_tag_collision_never_creates_or_overwrites_assets(self):
        self.run_publish("tag-collision")

    def test_main_advancing_during_upload_leaves_draft_unpublished(self):
        self.run_publish("main-advanced")

    def test_changed_upload_leaves_draft_unpublished(self):
        self.run_publish("upload-tamper")

    def test_candidate_tampering_stops_before_any_remote_mutation(self):
        (self.work / "candidate/YomiMado_0.5.0_x64-setup.exe").write_bytes(b"tampered")
        with patch.object(recovery, "request") as api, self.assertRaises(ValueError):
            recovery.review_files(self.work)
        api.assert_not_called()

    def test_note_source_mismatch_stops_before_tag_creation(self):
        path = self.work / "notes/notes.json"
        notes = release.read_json(path)
        notes["sourceRevision"] = "b" * 40
        release.write_json(path, notes)
        with (
            patch.object(recovery, "request") as api,
            self.assertRaisesRegex(ValueError, "source/version"),
        ):
            recovery.review_files(self.work)
        api.assert_not_called()


if __name__ == "__main__":
    unittest.main()
