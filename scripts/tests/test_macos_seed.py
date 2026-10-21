"""Rehearse dynamic seed approval, compatibility, transfer and source binding."""

import copy
import hashlib
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
import desktop_release as release
import macos_seed as seed
from test_desktop_release import ENVIRONMENT, MAIN_RULES, POLICIES

SOURCE = "a" * 40


def fixture(revision="b" * 40, number=100):
    manifest = copy.deepcopy(seed.LEGACY)
    manifest.update(
        sourceRevision=revision,
        sourceDirectory="source-delivery-" + revision[:7],
        reviewedAt="2020-01-01",
    )
    blobs = {}
    delivery = {
        "projectRevision": revision,
        "reviewer": seed.OWNER,
        "reviewedAt": manifest["reviewedAt"],
    }
    delivery_bytes = json.dumps(delivery).encode()
    manifest["sourceDeliverySha256"] = hashlib.sha256(delivery_bytes).hexdigest()
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w:gz") as stream:
        member = tarfile.TarInfo(manifest["sourceDirectory"] + "/source-delivery.json")
        member.size = len(delivery_bytes)
        stream.addfile(member, io.BytesIO(delivery_bytes))
    assets = []
    for i, (role, entry) in enumerate(manifest["assets"].items()):
        entry["name"] = entry["name"].replace("46a5649", revision[:7])
        data = archive.getvalue() if role == "sources" else (role + revision).encode()
        entry.update(size=len(data), sha256=hashlib.sha256(data).hexdigest())
        identifier = number + i
        blobs[identifier] = data
        assets.append(
            {
                "id": identifier,
                "name": entry["name"],
                "size": len(data),
                "digest": "sha256:" + entry["sha256"],
                "state": "uploaded",
                "uploader": {"login": seed.OWNER},
            }
        )
    data = json.dumps(manifest).encode()
    blobs[number + 4] = data
    assets.append(
        {
            "id": number + 4,
            "name": seed.MANIFEST,
            "size": len(data),
            "digest": "sha256:" + hashlib.sha256(data).hexdigest(),
            "state": "uploaded",
            "uploader": {"login": seed.OWNER},
        }
    )
    draft = {
        "id": number,
        "tag_name": "macos-reviewed-seed-" + revision[:7],
        "target_commitish": revision,
        "draft": True,
        "author": {"login": seed.OWNER},
        "assets": assets,
    }
    return manifest, draft, blobs, delivery_bytes


class SeedTests(unittest.TestCase):
    def resolve(
        self, drafts, compatible=lambda revision: True, rank=lambda revision: 1
    ):
        manifests = {
            fixture(r["target_commitish"], r["id"])[1]["assets"][-1]["id"]: fixture(
                r["target_commitish"], r["id"]
            )[0]
            for r in drafts
        }
        return seed.resolve(
            drafts, SOURCE, lambda asset: manifests[asset["id"]], compatible, rank
        )

    def test_selects_closest_compatible_source_not_latest_upload_or_first_page_order(
        self,
    ):
        old, old_draft, _, _ = fixture("b" * 40, 100)
        new, new_draft, _, _ = fixture("c" * 40, 200)
        incompatible, bad_draft, _, _ = fixture("d" * 40, 300)
        manifests = {104: old, 204: new, 304: incompatible}
        result = seed.resolve(
            [bad_draft, old_draft, new_draft],
            SOURCE,
            lambda a: manifests[a["id"]],
            lambda r: r != "d" * 40,
            lambda r: {"b" * 40: -3, "c" * 40: -1}[r],
        )
        self.assertEqual(result["releaseId"], 200)
        self.assertEqual(result["sourceRevision"], SOURCE)
        self.assertEqual(result["seed"], new)

    def test_unactivated_candidates_and_published_seeds_cannot_supply_runtime(self):
        _, draft, _, _ = fixture()
        for mode in ("no-manifest", "published", "incompatible"):
            changed = copy.deepcopy(draft)
            if mode == "no-manifest":
                changed["assets"].pop()
            if mode == "published":
                changed["draft"] = False
            with (
                self.subTest(mode=mode),
                self.assertRaisesRegex(ValueError, "No compatible"),
            ):
                self.resolve(
                    [changed], compatible=lambda _, mode=mode: mode != "incompatible"
                )

    def test_rejects_nonowner_approval_and_changed_upload_identity(self):
        manifest, draft, _, _ = fixture()
        with self.assertRaisesRegex(ValueError, "activation manifest"):
            seed.selection(draft, manifest, SOURCE)
        for mode in (
            "author",
            "uploader",
            "target",
            "tag",
            "digest",
            "size",
            "state",
            "extra",
            "duplicate",
        ):
            changed = copy.deepcopy(draft)
            if mode == "author":
                changed["author"]["login"] = "someone-else"
            elif mode == "uploader":
                changed["assets"][0]["uploader"]["login"] = "someone-else"
            elif mode == "target":
                changed["target_commitish"] = "main"
            elif mode == "tag":
                changed["tag_name"] = "macos-reviewed-seed-fffffff"
            elif mode == "digest":
                changed["assets"][0]["digest"] = "sha256:" + "0" * 64
            elif mode == "size":
                changed["assets"][0]["size"] += 1
            elif mode == "state":
                changed["assets"][0]["state"] = "new"
            elif mode == "extra":
                changed["assets"].append({"name": "unreviewed"})
            else:
                changed["assets"].append(changed["assets"][0])
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                seed.selection(changed, manifest, SOURCE, changed["assets"][4])

    def test_manifest_schema_rejects_unsigned_scope_paths_and_oversized_inputs(self):
        manifest, _, _, _ = fixture()
        for mode in (
            "approval",
            "date",
            "source",
            "directory",
            "path",
            "size",
            "sha",
            "missing",
            "extra",
        ):
            changed = copy.deepcopy(manifest)
            if mode == "approval":
                changed["approvedBy"] = "CI"
            elif mode == "date":
                changed["reviewedAt"] = ""
            elif mode == "source":
                changed["sourceRevision"] = "main"
            elif mode == "directory":
                changed["sourceDirectory"] = "../source"
            elif mode == "path":
                changed["assets"]["dmg"]["name"] = "../runtime.dmg"
            elif mode == "size":
                changed["assets"]["dmg"]["size"] = seed.LIMIT
            elif mode == "sha":
                changed["sourceDeliverySha256"] = ""
            elif mode == "missing":
                changed["assets"].pop("translation")
            else:
                changed["autoApproved"] = True
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                seed.validate_manifest(changed)

    def test_duplicate_drafts_and_equal_rank_are_rejected(self):
        _, draft, _, _ = fixture()
        with self.assertRaisesRegex(ValueError, "Ambiguous"):
            self.resolve([draft, draft])
        _, other, _, _ = fixture("c" * 40, 200)
        with self.assertRaisesRegex(ValueError, "equally recent"):
            self.resolve([draft, other])

    def test_existing_exact_seed_remains_available_without_remote_activation(self):
        manifest = copy.deepcopy(seed.LEGACY)
        draft = {
            "id": 12,
            "tag_name": "macos-reviewed-seed-46a5649",
            "draft": True,
            "target_commitish": seed.LEGACY_REVISION,
            "assets": [
                {
                    "id": i + 1,
                    "state": "uploaded",
                    **e,
                    "digest": "sha256:" + e["sha256"],
                }
                for i, e in enumerate(manifest["assets"].values())
            ],
        }
        result = seed.resolve(
            [draft],
            SOURCE,
            lambda _: self.fail("Unexpected manifest fetch"),
            lambda _: True,
            lambda _: 0,
        )
        self.assertIsNone(result["manifestAsset"])
        self.assertEqual(result["seed"], seed.LEGACY)
        draft["assets"][0]["digest"] = "sha256:" + "0" * 64
        with self.assertRaises(ValueError):
            seed.selection(draft, manifest, SOURCE)

    def test_record_cannot_change_source_or_seed_between_jobs(self):
        manifest, draft, _, _ = fixture()
        value = seed.selection(draft, manifest, SOURCE, draft["assets"][-1])
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "selected.json"
            path.write_text(json.dumps(value))
            checksum = seed.sha256(path)
            self.assertEqual(seed.load_selection(path, checksum, SOURCE), value)
            with self.assertRaisesRegex(ValueError, "another release source"):
                seed.load_selection(path, checksum, "f" * 40)
            path.write_text(path.read_text() + " ")
            with self.assertRaisesRegex(ValueError, "hash differs"):
                seed.load_selection(path, checksum, SOURCE)

    def test_manifest_http_bytes_are_hashed_and_nonowner_metadata_never_downloads(self):
        _, draft, blobs, _ = fixture()
        asset = draft["assets"][-1]
        for data in (blobs[104] + b" ", b"{}"):
            with (
                patch.dict(os.environ, {"GH_TOKEN": "fixture"}),
                patch.object(release, "build_opener") as opener,
            ):
                opener.return_value.open.return_value = io.BytesIO(data)
                with self.assertRaisesRegex(ValueError, "byte hash differs"):
                    release.read_seed_manifest(asset)
        changed = copy.deepcopy(asset)
        changed["uploader"]["login"] = "someone-else"
        with patch.object(release, "build_opener") as opener:
            with self.assertRaisesRegex(ValueError, "identity differs"):
                release.read_seed_manifest(changed)
            opener.assert_not_called()

    def test_archive_links_outside_destination_and_duplicate_members_are_rejected(self):
        manifest, _, _, _ = fixture()
        for mode in ("symlink", "hardlink", "duplicate"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                with tarfile.open(
                    root / manifest["assets"]["sources"]["name"], "w:gz"
                ) as archive:
                    member = tarfile.TarInfo(
                        manifest["sourceDirectory"] + "/source-delivery.json"
                    )
                    if mode == "symlink":
                        member.type = tarfile.SYMTYPE
                    if mode == "hardlink":
                        member.type = tarfile.LNKTYPE
                    member.linkname = "/outside"
                    archive.addfile(member)
                    if mode == "duplicate":
                        archive.addfile(member)
                with self.assertRaises((ValueError, tarfile.FilterError)):
                    seed.extract_sources(root, manifest)

    def test_actual_git_runtime_changes_require_matching_new_seed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)

            def git(*args):
                return subprocess.check_output(
                    ["git", *args], cwd=root, text=True
                ).strip()

            git("init", "-q")
            git("config", "user.email", "fixture@example.invalid")
            git("config", "user.name", "Fixture")
            runtime = root / "services/ocr/app/pipeline.py"
            runtime.parent.mkdir(parents=True)
            runtime.write_text("# old runtime\n")
            git("add", ".")
            git("commit", "-qm", "old")
            old = git("rev-parse", "HEAD")
            runtime.write_text("# new runtime\n")
            git("add", ".")
            git("commit", "-qm", "new")
            new = git("rev-parse", "HEAD")
            original_git = release.macos.git
            original_verify = release.macos.verify_reuse
            with (
                patch.object(
                    release.macos,
                    "git",
                    side_effect=lambda *a, **kw: original_git(*a, root=root),
                ),
                patch.object(
                    release.macos,
                    "verify_reuse",
                    side_effect=lambda seed_revision: original_verify(
                        root, seed_revision
                    ),
                ),
            ):
                self.assertFalse(release.compatible_seed(old))
                self.assertTrue(release.compatible_seed(new))
                self.assertGreater(release.seed_rank(new), release.seed_rank(old))

    def test_source_archive_and_approval_are_verified_before_staging(self):
        manifest, _, blobs, _ = fixture()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            archive = root / manifest["assets"]["sources"]["name"]
            archive.write_bytes(blobs[101])
            directory = seed.extract_sources(root, manifest)
            self.assertEqual(directory.name, manifest["sourceDirectory"])
            (directory / "source-delivery.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "approval/delivery differs"):
                seed.verify_delivery(directory, manifest)

    def test_archive_traversal_is_rejected(self):
        manifest, _, _, _ = fixture()
        for name in ("../escape", "source-delivery-bbbbbbb/../../escape", "/escape"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                with tarfile.open(
                    root / manifest["assets"]["sources"]["name"], "w:gz"
                ) as archive:
                    member = tarfile.TarInfo(name)
                    archive.addfile(member)
                with self.assertRaisesRegex(ValueError, "Unsafe"):
                    seed.extract_sources(root, manifest)

    def test_manifest_creation_uses_existing_approval_without_uploading(self):
        manifest, draft, blobs, delivery = fixture()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            inputs = root / "inputs"
            inputs.mkdir()
            for entry in draft["assets"][:-1]:
                (inputs / entry["name"]).write_bytes(blobs[entry["id"]])
            sources = root / manifest["sourceDirectory"]
            sources.mkdir()
            (sources / "source-delivery.json").write_bytes(delivery)
            approval = root / "approval.json"
            report = {
                "reviewer": seed.OWNER,
                "reviewedAt": manifest["reviewedAt"],
                "projectRevision": manifest["sourceRevision"],
                "approvedManifestSha256": manifest["sourceDeliverySha256"],
                "scope": "Exact source delivery",
                "statement": "Owner approval fixture",
            }
            approval.write_text(json.dumps(report))
            output = root / seed.MANIFEST
            seed.create_manifest(inputs, sources, approval, output)
            self.assertEqual(json.loads(output.read_text()), manifest)
            with self.assertRaisesRegex(ValueError, "overwrite"):
                seed.create_manifest(inputs, sources, approval, output)
            output.unlink()
            report["approvedManifestSha256"] = "0" * 64
            approval.write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, "actual owner source approval"):
                seed.create_manifest(inputs, sources, approval, output)

    def test_no_compatible_seed_stops_before_any_installer_or_windows_download(self):
        manifest, draft, _, _ = fixture()
        reports = [
            {"default_branch": "main"},
            {"object": {"sha": SOURCE}},
            MAIN_RULES,
            ENVIRONMENT,
            POLICIES,
            [draft],
        ]
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.dict(os.environ, {"GITHUB_SHA": SOURCE}),
            patch.object(release, "main_scope"),
            patch.object(release, "request", side_effect=reports),
            patch.object(release, "read_seed_manifest", return_value=manifest),
            patch.object(release, "compatible_seed", return_value=False),
            patch.object(release, "build_opener") as opener,
        ):
            with self.assertRaisesRegex(ValueError, "No compatible owner-reviewed"):
                release.download_inputs(Path(temporary) / "inputs")
            opener.assert_not_called()
            self.assertFalse((Path(temporary) / "inputs").exists())

    def test_actual_download_transfer_and_source_stage_use_same_selected_seed(self):
        manifest, draft, blobs, _ = fixture()
        win = b"dictionary fixture"
        pinned = {
            "macos": release.INPUTS["macos"],
            "windows": {
                "tag": "windows-fixture",
                "assets": {
                    "windows-dictionary-snapshots.tar.gz": hashlib.sha256(
                        win
                    ).hexdigest()
                },
            },
        }
        win_draft = {
            "tag_name": "windows-fixture",
            "draft": True,
            "target_commitish": release.WINDOWS_SEED,
            "assets": [
                {
                    "id": 999,
                    "name": "windows-dictionary-snapshots.tar.gz",
                    "state": "uploaded",
                    "digest": "sha256:" + hashlib.sha256(win).hexdigest(),
                }
            ],
        }
        blobs[999] = win
        queried = []

        def open_query(query, timeout):
            self.assertEqual(query.get_method(), "GET")
            identifier = int(query.full_url.rsplit("/", 1)[1])
            queried.append(identifier)
            return io.BytesIO(blobs[identifier])

        reports = [
            {"default_branch": "main"},
            {"object": {"sha": SOURCE}},
            MAIN_RULES,
            ENVIRONMENT,
            POLICIES,
            [{"id": i + 2000, "tag_name": "historical-" + str(i)} for i in range(100)],
            [draft, win_draft],
        ]
        with (
            tempfile.TemporaryDirectory() as temporary,
            patch.dict(
                os.environ,
                {
                    "GITHUB_SHA": SOURCE,
                    "GH_TOKEN": "fixture",
                    "GITHUB_ENV": temporary + "/environment",
                },
            ),
            patch.object(release, "main_scope"),
            patch.object(release, "INPUTS", pinned),
            patch.object(release, "request", side_effect=reports) as api,
            patch.object(release, "compatible_seed", return_value=True),
            patch.object(release, "seed_rank", return_value=0),
            patch.object(release, "build_opener") as opener,
            patch.object(release.macos, "verify_reuse"),
        ):
            opener.return_value.open.side_effect = open_query
            root = Path(temporary) / "inputs"
            release.download_inputs(root)
            path = root / "selected-macos-seed.json"
            chosen = seed.load_selection(path, seed.sha256(path), SOURCE)
            self.assertEqual(chosen["seed"], manifest)
            dmg = root / "macos" / manifest["assets"]["dmg"]["name"]
            original = dmg.read_bytes()
            dmg.write_bytes(b"changed")
            with self.assertRaisesRegex(
                ValueError, "Transferred reviewed input changed"
            ):
                release.verify_inputs(root / "macos", "macos", chosen)
            dmg.write_bytes(original)
            release.prepare_macos_inputs(root / "macos", chosen)
            self.assertIn(
                "YOMIMADO_SEED_DMG=", Path(os.environ["GITHUB_ENV"]).read_text()
            )
            self.assertEqual(set(queried), {100, 101, 102, 103, 104, 999})
            self.assertTrue(
                all(len(c.args) == 1 and not c.kwargs for c in api.call_args_list)
            )


if __name__ == "__main__":
    unittest.main()
