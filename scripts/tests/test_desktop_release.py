"""Exercise shared release transfer, private input scope and actual publisher."""

import copy
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
import desktop_release as release

ROOT = Path(__file__).parents[2]
REVISION = "a" * 40
ENVIRONMENT = {
    "name": "macos-release",
    "can_admins_bypass": False,
    "deployment_branch_policy": {
        "protected_branches": False,
        "custom_branch_policies": True,
    },
    "protection_rules": [{"type": "required_reviewers", "reviewers": [{"id": 123}]}],
}
POLICIES = {"branch_policies": [{"name": "main", "type": "branch"}]}


def fixtures(root, version="0.1.0"):
    mac, win = root / "mac", root / "win"
    mac.mkdir()
    win.mkdir()
    for name in release.macos_names(version) - {"release-candidate.json"}:
        (mac / name).write_bytes(b"mac fixture " + name.encode())
    primary = sorted(
        n for n in release.macos_names(version) if n.endswith((".dmg", ".tar.gz"))
    )
    mac_record = {
        "sourceRevision": REVISION,
        "version": version,
        "tag": "v" + version,
        "prerelease": release.macos.is_prerelease(version),
        "mode": "unnotarized-hobby",
        "installedAppVerified": False,
        "assets": {n: release.digest(mac / n) for n in primary},
    }
    for name, sha in mac_record["assets"].items():
        (mac / (name + ".sha256")).write_text(f"{sha}  {name}\n")
    release.write_json(mac / "release-candidate.json", mac_record)
    for name in release.windows_names(version) - {
        "windows-candidate.json",
        "SHA256SUMS.txt",
    }:
        (win / name).write_bytes(b"windows fixture " + name.encode())
    win_private = {
        "mode": "private-test",
        "platform": "windows-x64",
        "sourceRevision": REVISION,
        "installedAppVerified": False,
        "publicDistributionApproved": False,
        "assets": {p.name: release.digest(p) for p in sorted(win.iterdir())},
    }
    release.write_json(win / "windows-candidate.json", win_private)
    sums = {
        **win_private["assets"],
        "windows-candidate.json": release.digest(win / "windows-candidate.json"),
    }
    (win / "SHA256SUMS.txt").write_text(
        "".join(f"{sha}  {name}\n" for name, sha in sums.items())
    )
    win_record = release.windows_record(win)
    return mac, win, mac_record, win_record


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, {"GITHUB_SHA": REVISION}).start()
        patch.object(release.macos, "version", return_value="0.1.0").start()
        self.mac, self.win, self.mac_record, self.win_record = fixtures(self.root)
        self.out = self.root / "combined"

    def combine(self):
        return release.combine(
            self.mac, self.win, self.out, self.mac_record, self.win_record
        )

    def test_both_platforms_have_one_identity_and_all_files(self):
        record = self.combine()
        self.assertEqual(len(record["assets"]), 15)
        self.assertEqual(len(list(self.out.iterdir())), 17)
        self.assertIs(record["installedAppVerified"], False)
        self.assertEqual(record["platforms"], ["macos-aarch64", "windows-x64"])
        release.verify_combined(self.out, record)

    def test_windows_tamper_and_wrong_source_block_combination(self):
        path = self.win / "YomiMado_0.1.0_x64-setup.exe"
        path.write_bytes(b"altered")
        with self.assertRaisesRegex(ValueError, "changed"):
            self.combine()
        self.assertFalse(self.out.exists())

    def test_missing_platform_and_extra_file_block_combination(self):
        (self.mac / "unreviewed.dll").write_bytes(b"extra")
        with self.assertRaisesRegex(ValueError, "Unexpected"):
            self.combine()
        (self.mac / "unreviewed.dll").unlink()
        (self.win / "windows-notices.tar.gz").unlink()
        with self.assertRaisesRegex(ValueError, "Unexpected"):
            self.combine()

    def test_mismatched_commit_and_version_fail_closed(self):
        self.mac_record["sourceRevision"] = "b" * 40
        release.write_json(self.mac / "release-candidate.json", self.mac_record)
        with self.assertRaisesRegex(ValueError, "identity differs"):
            self.combine()
        self.mac_record["sourceRevision"] = REVISION
        release.write_json(self.mac / "release-candidate.json", self.mac_record)
        with (
            patch.object(release.macos, "version", return_value="0.2.0"),
            self.assertRaisesRegex(ValueError, "versioned setup"),
        ):
            self.combine()

    def test_combined_identity_hash_checksum_and_symlink_rejection(self):
        record = self.combine()
        for field, wrong in (
            ("sourceRevision", "b" * 40),
            ("prerelease", False),
            ("platforms", ["windows-x64"]),
            ("installedAppVerified", True),
        ):
            with (
                self.subTest(field=field),
                self.assertRaisesRegex(ValueError, "identity"),
            ):
                changed = {**record, field: wrong}
                release.verify_combined(self.out, changed)
        path = self.out / "desktop-SHA256SUMS.txt"
        sums = path.read_text()
        path.write_text(sums + "extra")
        with self.assertRaisesRegex(ValueError, "checksums"):
            release.verify_combined(self.out, record)
        path.write_text(sums)
        target = self.out / "project-sources.tar.gz"
        target.unlink()
        target.symlink_to(self.win / target.name)
        with self.assertRaisesRegex(ValueError, "regular"):
            release.verify_combined(self.out, record)

    def test_uploaded_draft_requires_every_asset_and_matching_classification(self):
        record = self.combine()
        report = {
            "draft": True,
            "tag_name": "v0.1.0",
            "prerelease": True,
            "assets": [
                {
                    "name": p.name,
                    "digest": "sha256:" + release.digest(p),
                    "state": "uploaded",
                }
                for p in self.out.iterdir()
            ],
        }
        release.verify_uploaded(self.out, record, report)
        for field, wrong in (
            ("draft", False),
            ("prerelease", False),
            ("tag_name", "v0.2.0"),
        ):
            with (
                self.subTest(field=field),
                self.assertRaisesRegex(ValueError, "unpublished"),
            ):
                release.verify_uploaded(self.out, record, {**report, field: wrong})
        for scenario in ("missing", "duplicate", "digest", "state"):
            changed = copy.deepcopy(report)
            if scenario == "missing":
                changed["assets"].pop()
            elif scenario == "duplicate":
                changed["assets"].append(changed["assets"][0])
            elif scenario == "digest":
                changed["assets"][0]["digest"] = "sha256:" + "0" * 64
            else:
                changed["assets"][0]["state"] = "new"
            with (
                self.subTest(scenario=scenario),
                self.assertRaisesRegex(ValueError, "unpublished"),
            ):
                release.verify_uploaded(self.out, record, changed)


class PrivateInputTests(unittest.TestCase):
    def test_wrong_branch_repository_and_non_actions_cannot_read_inputs(self):
        valid = {
            "GITHUB_ACTIONS": "true",
            "GITHUB_REPOSITORY": release.REPOSITORY,
            "GITHUB_REF": "refs/heads/main",
            "GITHUB_SHA": REVISION,
        }
        with patch.dict(os.environ, valid):
            release.main_scope()
        for field, value in (
            ("GITHUB_ACTIONS", "false"),
            ("GITHUB_REF", "refs/heads/develop"),
            ("GITHUB_REPOSITORY", "other/repo"),
            ("GITHUB_SHA", "main"),
        ):
            with (
                patch.dict(os.environ, {**valid, field: value}),
                self.assertRaisesRegex(ValueError, "main workflow"),
            ):
                release.main_scope()

    def test_private_seed_requires_pinned_digests_and_unambiguous_draft(self):
        for platform, pinned in release.INPUTS.items():
            draft = {
                "tag_name": pinned["tag"],
                "draft": True,
                "target_commitish": release.WINDOWS_SEED,
                "assets": [
                    {
                        "name": n,
                        "digest": "sha256:" + sha,
                        "id": i + 1,
                        "state": "uploaded",
                    }
                    for i, (n, sha) in enumerate(pinned["assets"].items())
                ],
            }
            self.assertEqual(release.seed_release([draft], platform), draft)
            for scenario in ("published", "ambiguous", "digest", "missing", "state"):
                changed = copy.deepcopy(draft)
                listing = [changed]
                if scenario == "published":
                    changed["draft"] = False
                elif scenario == "ambiguous":
                    listing.append(changed)
                elif scenario == "digest":
                    changed["assets"][0]["digest"] = "sha256:" + "0" * 64
                elif scenario == "missing":
                    changed["assets"].pop()
                else:
                    changed["assets"][0]["state"] = "new"
                with (
                    self.subTest(platform=platform, scenario=scenario),
                    self.assertRaises(ValueError),
                ):
                    release.seed_release(listing, platform)

    def test_download_sends_only_get_and_checks_actual_bytes(self):
        data = b"pinned fixture input"
        sha = __import__("hashlib").sha256(data).hexdigest()
        pinned = {"windows": {"tag": "private-seed", "assets": {"seed.tar.gz": sha}}}
        draft = {
            "tag_name": "private-seed",
            "draft": True,
            "target_commitish": release.WINDOWS_SEED,
            "assets": [
                {
                    "id": 123,
                    "name": "seed.tar.gz",
                    "digest": "sha256:" + sha,
                    "state": "uploaded",
                }
            ],
        }
        answers = [
            {"default_branch": "main"},
            {"object": {"sha": REVISION}},
            ENVIRONMENT,
            POLICIES,
            [draft],
        ]
        queries = []

        def open_query(query, timeout):
            self.assertEqual(query.get_method(), "GET")
            self.assertEqual(query.full_url, release.API + "/releases/assets/123")
            queries.append(query)
            return io.BytesIO(data)

        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.object(release, "main_scope"),
            patch.dict(
                os.environ, {"GITHUB_SHA": REVISION, "GH_TOKEN": "test-placeholder"}
            ),
            patch.object(release, "INPUTS", pinned),
            patch.object(release, "request", side_effect=answers) as api,
            patch.object(release, "build_opener") as opener,
        ):
            opener.return_value.open.side_effect = open_query
            release.download_inputs(Path(temporary))
            self.assertEqual(len(queries), 1)
            self.assertTrue(
                all(len(c.args) == 1 and not c.kwargs for c in api.call_args_list)
            )
            self.assertEqual(
                (Path(temporary) / "windows/seed.tar.gz").read_bytes(), data
            )


class PublisherRehearsalTests(unittest.TestCase):
    def rehearsal(self, version, scenario="pass"):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scripts = root / "scripts"
            scripts.mkdir()
            for name in (
                "desktop_release.py",
                "macos-ci-release.py",
                "windows_dictionary_seed.py",
                "windows_private_draft.py",
                "windows_release.py",
            ):
                shutil.copyfile(ROOT / "scripts" / name, scripts / name)
            for name in (
                "package.json",
                "package-lock.json",
                "src-tauri/tauri.conf.json",
                "src-tauri/Cargo.toml",
                "src-tauri/Cargo.lock",
            ):
                source = ROOT / "apps/desktop" / name
                target = root / "apps/desktop" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                text = source.read_text()
                if name.endswith(".json"):
                    value = json.loads(text)
                    value["version"] = version
                    if name == "package-lock.json":
                        value["packages"][""]["version"] = version
                    text = json.dumps(value)
                else:
                    text = text.replace(
                        'name = "yomimado"\nversion = "0.1.0"',
                        f'name = "yomimado"\nversion = "{version}"',
                    )
                target.write_text(text)
            env = {
                **os.environ,
                "GITHUB_SHA": REVISION,
                "GITHUB_REPOSITORY": release.REPOSITORY,
                "RUNNER_TEMP": str(root),
                "RELEASE_TAG": "v" + version,
                "RELEASE_PRERELEASE": str(release.macos.is_prerelease(version)).lower(),
                "SCENARIO": scenario,
            }
            with (
                patch.dict(os.environ, env),
                patch.object(release.macos, "version", return_value=version),
            ):
                mac, win, mr, wr = fixtures(root, version)
                record = release.combine(mac, win, root / "candidate", mr, wr)
            env["EXPECTED_RECORD"] = json.dumps(record)
            (root / "docs").mkdir()
            shutil.copyfile(
                ROOT / "docs/desktop-release-notes.md",
                root / "docs/desktop-release-notes.md",
            )
            release.write_json(root / "environment.json", ENVIRONMENT)
            release.write_json(root / "policies.json", POLICIES)
            binary = root / "bin"
            binary.mkdir()
            (binary / "python3").symlink_to(sys.executable)
            fake = binary / "gh"
            fake.write_text(
                "#!"
                + sys.executable
                + "\n"
                + textwrap.dedent("""
                import hashlib,json,os,sys
                from pathlib import Path
                args=sys.argv[1:]; root=Path(os.environ['RUNNER_TEMP']); scenario=os.environ['SCENARIO']
                with (root/'calls.txt').open('a') as stream: stream.write(' '.join(args)+'\\n')
                if args[0]=='api':
                    endpoint=next(a for a in args[1:] if a.startswith('repos/'))
                    if '--method' in args:
                        (root/'tag.txt').write_text(os.environ['GITHUB_SHA']); print('{}')
                    elif endpoint.endswith('/deployment-branch-policies'): print((root/'policies.json').read_text())
                    elif endpoint.endswith('/environments/macos-release'):
                        value=json.loads((root/'environment.json').read_text())
                        if scenario=='unprotected': value['protection_rules']=[]
                        print(json.dumps(value))
                    elif endpoint.endswith('/git/ref/heads/main'): print('b'*40 if (scenario=='stale' or (scenario=='advance-during-upload' and (root/'created.txt').exists())) else os.environ['GITHUB_SHA'])
                    elif '/git/ref/tags/' in endpoint: print((root/'tag.txt').read_text())
                    elif '/releases/tags/' in endpoint:
                        record=json.loads(os.environ['EXPECTED_RECORD'])
                        assets=[{'name':p.name,'digest':'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest(),'state':'uploaded'} for p in (root/'candidate').iterdir()]
                        if scenario=='upload-tamper': assets[0]['digest']='sha256:'+'0'*64
                        print(json.dumps({'draft':True,'tag_name':record['tag'],'prerelease':record['prerelease'],'assets':assets}))
                    else: print('develop' if scenario=='default-branch' else 'main')
                elif args[:2]==['release','create']:
                    (root/'created.txt').write_text(' '.join(args))
                elif args[:2]==['release','edit']:
                    (root/'published.txt').write_text('published')
                else: sys.exit(2)
                """)
            )
            fake.chmod(0o755)
            git = binary / "git"
            git.write_text(
                "#!"
                + sys.executable
                + '\nimport os\nprint("existing-tag" if os.environ["SCENARIO"]=="tag-collision" else "")\n'
            )
            git.chmod(0o755)
            env["PATH"] = str(binary) + os.pathsep + env["PATH"]
            workflow = (ROOT / ".github/workflows/macos-prerelease.yml").read_text()
            actual = workflow.split(
                "      - name: Recheck files, protection, main and tag before publishing",
                1,
            )[1].split("        run: |\n", 1)[1]
            command = textwrap.dedent(actual)
            result = subprocess.run(
                ["bash", "-c", command],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            if scenario == "pass":
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue((root / "published.txt").exists())
                created = (root / "created.txt").read_text()
                self.assertIn("--draft", created)
                self.assertEqual(
                    "--prerelease" in created, release.macos.is_prerelease(version)
                )
                calls = (root / "calls.txt").read_text()
                self.assertEqual(calls.count("api --method POST"), 1)
                self.assertEqual(calls.count("release create"), 1)
                self.assertIn(
                    "Both exact CI installers", (root / "release-notes.md").read_text()
                )
            else:
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse((root / "published.txt").exists())
                if scenario not in {"upload-tamper", "advance-during-upload"}:
                    self.assertFalse((root / "created.txt").exists())

    def test_actual_publisher_prerelease_and_stable_paths(self):
        for version in ("0.1.0", "1.0.0-beta.1", "1.0.0"):
            with self.subTest(version=version):
                self.rehearsal(version)

    def test_actual_publisher_refuses_unsafe_states(self):
        for scenario in (
            "default-branch",
            "stale",
            "unprotected",
            "tag-collision",
            "upload-tamper",
            "advance-during-upload",
        ):
            with self.subTest(scenario=scenario):
                self.rehearsal("0.1.0", scenario)

    def test_builders_have_no_write_token_and_one_publisher_waits_for_both(self):
        workflow = (ROOT / ".github/workflows/macos-prerelease.yml").read_text()
        for job, next_job in (
            ("build", "windows-build"),
            ("windows-build", "verify-transfer"),
        ):
            block = workflow.split("\n  " + job + ":\n", 1)[1].split(
                "\n  " + next_job + ":\n", 1
            )[0]
            self.assertNotIn("contents: write", block)
            self.assertNotIn("GH_TOKEN", block)
            self.assertNotIn("gh release", block)
        self.assertIn("needs: [build, windows-build]", workflow)
        self.assertEqual(workflow.count("gh release create"), 1)
        self.assertEqual(workflow.count("gh release edit"), 1)
        self.assertIn("name: Desktop release from main", workflow)


if __name__ == "__main__":
    unittest.main()
