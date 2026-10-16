"""Exercise shared release transfer, private input scope and actual publisher."""

import copy
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
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
    "name": "desktop-release",
    "can_admins_bypass": False,
    "deployment_branch_policy": {
        "protected_branches": False,
        "custom_branch_policies": True,
    },
    "protection_rules": [{"type": "required_reviewers", "reviewers": [{"id": 123}]}],
}
POLICIES = {"branch_policies": [{"name": "main", "type": "branch"}]}
MAIN_RULES = [
    {"type": "pull_request"},
    {"type": "deletion"},
    {"type": "non_fast_forward"},
    {
        "type": "required_status_checks",
        "parameters": {
            "strict_required_status_checks_policy": True,
            "required_status_checks": [{"context": "gates", "integration_id": 15368}],
        },
    },
]


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


def legacy_combined(mac, win, output, mac_record):
    """Original v0.1.0 delivery, kept separate from the new packager."""
    output.mkdir()
    for directory in (mac, win):
        for path in directory.iterdir():
            shutil.copyfile(path, output / path.name)
    record = {
        **{
            key: mac_record[key]
            for key in (
                "sourceRevision",
                "version",
                "tag",
                "prerelease",
                "installedAppVerified",
            )
        },
        "platforms": ["macos-aarch64", "windows-x64"],
        "assets": {p.name: release.digest(p) for p in sorted(output.iterdir())},
    }
    update_combined(output, record)
    return record


def update_combined(output, record):
    release.write_json(output / "desktop-release-candidate.json", record)
    sums = {
        **record["assets"],
        "desktop-release-candidate.json": release.digest(
            output / "desktop-release-candidate.json"
        ),
    }
    (output / "desktop-SHA256SUMS.txt").write_text(
        "".join(f"{sha}  {name}\n" for name, sha in sums.items())
    )


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
        self.assertEqual(len(record["assets"]), 4)
        self.assertEqual(len(list(self.out.iterdir())), 6)
        self.assertIs(record["installedAppVerified"], False)
        self.assertEqual(record["platforms"], ["macos-aarch64", "windows-x64"])
        release.verify_combined(self.out, record)

    def test_all_original_sources_data_notices_and_records_are_preserved(self):
        record = self.combine()
        retained = {}
        for kind in ("sources", "notices"):
            with tarfile.open(self.out / f"YomiMado_0.1.0_{kind}.tar.gz") as archive:
                for member in archive:
                    data = archive.extractfile(member).read()
                    if member.name == "README.txt":
                        self.assertEqual(data, release.bundle_guide("0.1.0", kind))
                    else:
                        platform, name = member.name.split("/")
                        original = (
                            self.mac if platform == "macos" else self.win
                        ) / name
                        self.assertEqual(data, original.read_bytes())
                        retained[name] = release.digest(original)
        for name in record["assets"]:
            if name.endswith((".dmg", ".exe")):
                retained[name] = release.digest(self.out / name)
        self.assertEqual(retained, record["inputs"])
        self.assertEqual(len(retained), 15)

    def test_packaging_is_deterministic_and_does_not_change_installer_bytes(self):
        first = self.combine()
        for directory in (self.mac, self.win):
            for path in directory.iterdir():
                os.utime(path, (123456789, 123456789))
                path.chmod(0o600)
        second = release.combine(
            self.mac, self.win, self.root / "second", self.mac_record, self.win_record
        )
        self.assertEqual(first, second)

    def test_existing_17_file_delivery_remains_verifiable(self):
        record = legacy_combined(self.mac, self.win, self.out, self.mac_record)
        self.assertEqual(len(list(self.out.iterdir())), 17)
        release.verify_combined(self.out, record)

    def test_unknown_layout_and_missing_input_or_platform_provenance_fail_closed(self):
        record = self.combine()
        for field, wrong in (
            ("layout", "unreviewed"),
            ("inputs", {}),
            ("platformCandidates", {}),
        ):
            changed = {**record, field: wrong}
            update_combined(self.out, changed)
            with self.subTest(field=field), self.assertRaises(ValueError):
                release.verify_combined(self.out, changed)

    def test_combined_installer_stays_bound_to_original_platform_record(self):
        record = self.combine()
        name = "YomiMado_0.1.0_x64-setup.exe"
        (self.out / name).write_bytes(b"replacement")
        record["assets"][name] = release.digest(self.out / name)
        update_combined(self.out, record)
        with self.assertRaisesRegex(ValueError, "installer bytes"):
            release.verify_combined(self.out, record)

    def test_missing_altered_duplicate_or_unsafe_archived_inputs_are_rejected(self):
        record = self.combine()
        path = self.out / "YomiMado_0.1.0_sources.tar.gz"
        with tarfile.open(path) as archive:
            entries = [(m.name, archive.extractfile(m).read()) for m in archive]
        for scenario in ("missing", "altered", "duplicate", "traversal", "symlink"):
            modified = list(entries)
            if scenario == "missing":
                modified.pop()
            elif scenario == "altered":
                name, data = modified[-1]
                modified[-1] = (name, data + b"tampered")
            elif scenario == "duplicate":
                modified.append(modified[-1])
            elif scenario == "traversal":
                modified[-1] = ("../outside", modified[-1][1])
            with tarfile.open(path, "w:gz") as archive:
                for name, data in modified:
                    member = tarfile.TarInfo(name)
                    member.size = len(data)
                    if scenario == "symlink" and name == modified[-1][0]:
                        member.type = tarfile.SYMTYPE
                        member.linkname = "../../outside"
                        member.size = 0
                        archive.addfile(member)
                    else:
                        archive.addfile(member, io.BytesIO(data))
            record["assets"][path.name] = release.digest(path)
            update_combined(self.out, record)
            with self.subTest(scenario=scenario), self.assertRaises(ValueError):
                release.verify_combined(self.out, record)

    def test_oversized_combined_sources_stop_before_publication(self):
        with (
            patch.object(release, "ASSET_LIMIT", 1024),
            self.assertRaisesRegex(ValueError, "exceeds the upload limit"),
        ):
            self.combine()

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
        target = self.out / "YomiMado_0.1.0_sources.tar.gz"
        target.unlink()
        target.symlink_to(self.mac / target.name)
        with self.assertRaisesRegex(ValueError, "regular"):
            release.verify_combined(self.out, record)

    def test_uploaded_draft_requires_every_asset_and_matching_classification(self):
        record = self.combine()
        report = {
            "draft": True,
            "tag_name": "v0.1.0",
            "target_commitish": REVISION,
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
            ("target_commitish", "b" * 40),
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

    def test_draft_listing_rejects_ambiguity_and_wrong_identity(self):
        record = self.combine()
        draft = {
            "id": 123,
            "name": "YomiMado v0.1.0",
            "tag_name": record["tag"],
            "target_commitish": REVISION,
            "draft": True,
            "prerelease": True,
        }
        self.assertEqual(release.select_uploaded_release([[draft]], record), 123)
        for pages in ([], [[]], [[draft, draft]], [[draft] * 100], [[]] * 21):
            with self.subTest(pages=pages), self.assertRaises(ValueError):
                release.select_uploaded_release(pages, record)
        for field, wrong in (
            ("id", True),
            ("id", 0),
            ("draft", False),
            ("prerelease", False),
            ("target_commitish", "main"),
            ("name", "Unrelated draft"),
        ):
            with self.subTest(field=field), self.assertRaises(ValueError):
                release.select_uploaded_release([[{**draft, field: wrong}]], record)


class PrivateInputTests(unittest.TestCase):
    def test_main_protection_requires_each_rule_and_trusted_current_base_check(self):
        release.verify_main_rules(MAIN_RULES)
        for index in range(len(MAIN_RULES)):
            with self.subTest(missing=index), self.assertRaises(ValueError):
                release.verify_main_rules(MAIN_RULES[:index] + MAIN_RULES[index + 1 :])
        for wrong in (False, None):
            changed = copy.deepcopy(MAIN_RULES)
            changed[-1]["parameters"]["strict_required_status_checks_policy"] = wrong
            with self.assertRaises(ValueError):
                release.verify_main_rules(changed)
        for field, wrong in (("context", "other"), ("integration_id", None)):
            changed = copy.deepcopy(MAIN_RULES)
            changed[-1]["parameters"]["required_status_checks"][0][field] = wrong
            with self.assertRaises(ValueError):
                release.verify_main_rules(changed)
        for wrong in (None, {}, MAIN_RULES * 25):
            with self.assertRaises(ValueError):
                release.verify_main_rules(wrong)

    def test_unprotected_main_cannot_enumerate_or_download_private_seeds(self):
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.object(release, "main_scope"),
            patch.dict(os.environ, {"GITHUB_SHA": REVISION}),
            patch.object(
                release,
                "request",
                side_effect=[
                    {"default_branch": "main"},
                    {"object": {"sha": REVISION}},
                    [],
                ],
            ) as api,
            patch.object(release, "build_opener") as opener,
            self.assertRaisesRegex(ValueError, "Main requires"),
        ):
            release.download_inputs(Path(temporary))
        self.assertEqual(api.call_count, 3)
        opener.assert_not_called()

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
            MAIN_RULES,
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


class PlanRehearsalTests(unittest.TestCase):
    def test_published_version_skips_but_missing_tag_checks_runtime_before_builds(self):
        workflow = (ROOT / ".github/workflows/release.yml").read_text()
        plan_step = workflow.split("id: plan\n", 1)[1].split("  seed-inputs:", 1)[0]
        shell = textwrap.dedent(plan_step.split("run: |\n", 1)[1].split("\n  #", 1)[0])
        for published in (True, False):
            with (
                self.subTest(published=published),
                tempfile.TemporaryDirectory() as temp,
            ):
                root = Path(temp)
                binary = root / "bin"
                binary.mkdir()
                for name, body in {
                    "git": "sys.exit(0 if os.environ['PUBLISHED']=='true' else 1)",
                    "gh": "print('{\"draft\": false}')",
                    "python": (
                        "if sys.argv[-1]=='plan':\n"
                        '    print(\'{"version":"0.1.0","tag":"v0.1.0","prerelease":true}\')\n'
                        "else:\n"
                        "    print('Changed runtime requires a new seed', file=sys.stderr)\n"
                        "    sys.exit(1)"
                    ),
                }.items():
                    path = binary / name
                    path.write_text(
                        f"#!{sys.executable}\n"
                        "import os,sys\n"
                        "from pathlib import Path\n"
                        "with (Path(os.environ['RUNNER_TEMP'])/'calls').open('a') as log:\n"
                        f"    log.write({name!r}+' '+' '.join(sys.argv[1:])+'\\n')\n"
                        + body
                        + "\n"
                    )
                    path.chmod(0o755)
                result = subprocess.run(
                    ["bash", "-c", shell],
                    env={
                        **os.environ,
                        "PATH": str(binary) + os.pathsep + os.environ["PATH"],
                        "PUBLISHED": str(published).lower(),
                        "RUNNER_TEMP": str(root),
                        "GITHUB_OUTPUT": str(root / "outputs"),
                        "GITHUB_REPOSITORY": release.REPOSITORY,
                    },
                    capture_output=True,
                    text=True,
                    check=False,
                )
                calls = (root / "calls").read_text()
                outputs = (root / "outputs").read_text()
                if published:
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn("release=false", outputs)
                    self.assertNotIn("verify-reuse", calls)
                else:
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("requires a new seed", result.stderr)
                    self.assertIn("verify-reuse", calls)
                    self.assertNotIn("gh ", calls)
                    self.assertNotIn("release=true", outputs.splitlines())


class PublisherRehearsalTests(unittest.TestCase):
    def rehearsal(self, version, scenario="pass"):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scripts = root / "scripts"
            scripts.mkdir()
            for name in (
                "desktop_release.py",
                "macos-ci-release.py",
                "release_dictionaries.py",
                "release_api.py",
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
                    text = re.sub(
                        r'(name = "yomimado"\nversion = )"[^"\n]+"',
                        lambda match: match[1] + f'"{version}"',
                        text,
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
            release.write_json(root / "expected-main-rules.json", MAIN_RULES)
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
                def report(draft=True):
                    record=json.loads(os.environ['EXPECTED_RECORD'])
                    assets=[{'name':p.name,'digest':'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest(),'state':'uploaded'} for p in (root/'candidate').iterdir()]
                    if scenario=='upload-tamper': assets[0]['digest']='sha256:'+'0'*64
                    return {'id':123,'name':'YomiMado '+record['tag'],'draft':draft,'target_commitish':record['sourceRevision'],'tag_name':record['tag'],'prerelease':record['prerelease'],'assets':assets}
                with (root/'calls.txt').open('a') as stream: stream.write(' '.join(args)+'\\n')
                if args[0]=='api':
                    endpoint=next(a for a in args[1:] if a.startswith('repos/'))
                    if '--method' in args:
                        method=args[args.index('--method')+1]
                        if method=='POST':
                            (root/'tag.txt').write_text(os.environ['GITHUB_SHA']); print('{}')
                        elif method=='PATCH' and endpoint.endswith('/releases/123'):
                            assert '-F' in args and 'draft=false' in args
                            (root/'published.txt').write_text('published'); print(json.dumps(report(False)))
                        else: sys.exit(2)
                    elif '/rules/branches/main?' in endpoint:
                        print('[]' if scenario=='unprotected-main' else (root/'expected-main-rules.json').read_text())
                    elif endpoint.endswith('/deployment-branch-policies'): print((root/'policies.json').read_text())
                    elif endpoint.endswith('/environments/desktop-release'):
                        value=json.loads((root/'environment.json').read_text())
                        if scenario=='unprotected': value['protection_rules']=[]
                        print(json.dumps(value))
                    elif endpoint.endswith('/git/ref/heads/main'): print('b'*40 if (scenario=='stale' or (scenario=='advance-during-upload' and (root/'created.txt').exists())) else os.environ['GITHUB_SHA'])
                    elif '/git/ref/tags/' in endpoint: print((root/'tag.txt').read_text())
                    elif '/releases/tags/' in endpoint:
                        print('Draft by-tag lookup returns HTTP 404',file=sys.stderr); sys.exit(1)
                    elif '/releases?per_page=100' in endpoint:
                        reports=[report()]
                        if scenario=='duplicate-draft': reports.append(report())
                        elif scenario=='wrong-draft-target': reports[0]['target_commitish']='b'*40
                        print(json.dumps([reports]))
                    elif endpoint.endswith('/releases/123'): print(json.dumps(report()))
                    else: print('develop' if scenario=='default-branch' else 'main')
                elif args[:2]==['release','create']:
                    (root/'created.txt').write_text(' '.join(args))
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
            workflow = (ROOT / ".github/workflows/release.yml").read_text()
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
                self.assertIn("--title YomiMado v" + version + " --notes-file", created)
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
                if scenario not in {
                    "upload-tamper",
                    "advance-during-upload",
                    "duplicate-draft",
                    "wrong-draft-target",
                }:
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
            "unprotected-main",
            "tag-collision",
            "upload-tamper",
            "advance-during-upload",
            "duplicate-draft",
            "wrong-draft-target",
        ):
            with self.subTest(scenario=scenario):
                self.rehearsal("0.1.0", scenario)

    def test_builders_have_no_write_token_and_one_publisher_waits_for_both(self):
        workflow = (ROOT / ".github/workflows/release.yml").read_text()
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
        self.assertNotIn("gh release edit", workflow)
        self.assertEqual(workflow.count("gh api --method PATCH"), 1)
        self.assertIn("name: Release", workflow)
        inputs = workflow.split("\n  seed-inputs:\n", 1)[1].split("\n  build:\n", 1)[0]
        self.assertNotIn("environment:", inputs)
        self.assertEqual(workflow.count("environment: desktop-release"), 1)
        self.assertNotIn("environments/macos-release", workflow)
        self.assertEqual(workflow.count("environments/desktop-release"), 4)
        # An owner review can stay pending while a later main build starts.
        # Publication alone must serialize tag creation and uploads.
        self.assertNotIn("concurrency:", workflow.split("\njobs:\n", 1)[0])
        publisher = workflow.split("\n  publish:\n", 1)[1]
        self.assertIn("group: desktop-main-publish", publisher)
        self.assertIn("cancel-in-progress: false", publisher)
        checks = (ROOT / ".github/workflows/checks.yml").read_text()
        self.assertIn(
            "\n  gates:\n", checks
        )  # Required main status context stays unchanged.
        self.assertIn("branches: [develop, main]", checks)
        self.assertIn("pull_request:\n    branches: [main]", checks)
        self.assertNotIn("paths:", checks)


if __name__ == "__main__":
    unittest.main()
