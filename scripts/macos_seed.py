"""Owner-reviewed macOS seed manifests and source-bound run selections.

An owner uploads the manifest last, after actual source approval and input
verification. A draft label alone never establishes approval. This module never
uploads files, records approval on someone's behalf, or publishes installers.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import tarfile
from datetime import date
from pathlib import Path, PurePosixPath

OWNER = "chonnakanch"
MANIFEST = "macos-seed.json"
LIMIT = 2 * 1024**3
ROLES = {
    "dmg": r"YomiMado_[0-9A-Za-z.-]+_aarch64\.dmg",
    "sources": r"YomiMado_[0-9A-Za-z.-]+_sources_[0-9a-f]{7}\.tar\.gz",
    "notices": r"YomiMado_[0-9A-Za-z.-]+_notices_[0-9a-f]{7}\.tar\.gz",
    "translation": r"YomiMado_[0-9A-Za-z.-]+_translation_torch\.zip",
}
LEGACY_REVISION = "46a5649007caf09538adb7d7d0bc4bda763c095e"
# Migration only: exact input/approval evidence in the OCR seed review. Future
# seeds carry owner-uploaded manifests and require no edits to these constants.
LEGACY = {
    "schemaVersion": 1,
    "platform": "macos-aarch64",
    "sourceRevision": LEGACY_REVISION,
    "sourceDirectory": "source-delivery-46a5649",
    "approvedBy": OWNER,
    "reviewedAt": "2026-10-20",
    "sourceDeliverySha256": "37eebd41afe82f538d41fafb1cba7bd4045e223b5b64c88d843f5efd616dcfd7",
    "assets": {
        "dmg": {
            "name": "YomiMado_0.4.0_aarch64.dmg",
            "size": 656270895,
            "sha256": "19ff1c941f866df73653769f7e6b4b1c7e310509ed7e13757fd0c80e5945bf1e",
        },
        "sources": {
            "name": "YomiMado_0.4.0_sources_46a5649.tar.gz",
            "size": 936122263,
            "sha256": "ae6322ed25f79226057dade2787a5acf1a61786de0714caa36008a62da5c7b71",
        },
        "notices": {
            "name": "YomiMado_0.4.0_notices_46a5649.tar.gz",
            "size": 1104586,
            "sha256": "0a9fcdd3e5a1c1b284e7a70f321475afc932edd905ace2fdea27fe9a92d67c6d",
        },
        "translation": {
            "name": "YomiMado_0.4.0_translation_torch.zip",
            "size": 306394404,
            "sha256": "e1c6a0ae58777d1eb4e8085eddff7a908fe0035e95c82178707178b7690434ef",
        },
    },
}


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def checksum(value) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def validate_manifest(value: dict) -> None:
    if (
        not isinstance(value, dict)
        or set(value) != set(LEGACY)
        or type(value.get("schemaVersion")) is not int
        or value.get("schemaVersion") != 1
        or value.get("platform") != "macos-aarch64"
        or not re.fullmatch(r"[0-9a-f]{40}", value.get("sourceRevision", ""))
        or value.get("sourceDirectory")
        != "source-delivery-" + value["sourceRevision"][:7]
        or value.get("approvedBy") != OWNER
        or not checksum(value.get("sourceDeliverySha256"))
        or not isinstance(value.get("assets"), dict)
        or set(value["assets"]) != set(ROLES)
    ):
        raise ValueError("Invalid owner-reviewed macOS seed manifest")
    try:
        reviewed = date.fromisoformat(value["reviewedAt"])
        if reviewed.isoformat() != value["reviewedAt"]:
            raise ValueError("Invalid seed review date")
    except (TypeError, ValueError) as error:
        raise ValueError("Invalid seed review date") from error
    names = set()
    for role, pattern in ROLES.items():
        entry = value["assets"][role]
        if (
            not isinstance(entry, dict)
            or set(entry) != {"name", "size", "sha256"}
            or not re.fullmatch(pattern, entry.get("name", ""))
            or type(entry.get("size")) is not int
            or not 0 < entry["size"] < LIMIT
            or not checksum(entry.get("sha256"))
            or entry["name"] in names
        ):
            raise ValueError("Invalid seed input: " + role)
        if role in {"sources", "notices"} and not entry["name"].endswith(
            "_" + value["sourceRevision"][:7] + ".tar.gz"
        ):
            raise ValueError("Seed input source revision differs")
        names.add(entry["name"])


def asset_identity(asset: dict, expected: dict, owner: bool = True) -> dict:
    if (
        type(asset.get("id")) is not int
        or asset["id"] <= 0
        or asset.get("state") != "uploaded"
        or asset.get("name") != expected["name"]
        or asset.get("digest") != "sha256:" + expected["sha256"]
        or asset.get("size") != expected["size"]
        or (owner and asset.get("uploader", {}).get("login") != OWNER)
    ):
        raise ValueError("Reviewed seed asset identity differs: " + expected["name"])
    return {"id": asset["id"], **expected}


def selection(
    release: dict, manifest: dict, source: str, manifest_asset: dict | None = None
) -> dict:
    validate_manifest(manifest)
    legacy = manifest_asset is None and manifest == LEGACY
    if manifest_asset is None and not legacy:
        raise ValueError("A new seed requires an owner-uploaded activation manifest")
    if (
        type(release.get("id")) is not int
        or release["id"] <= 0
        or release.get("draft") is not True
        or release.get("tag_name")
        != "macos-reviewed-seed-" + manifest["sourceRevision"][:7]
        or release.get("target_commitish") != manifest["sourceRevision"]
        or (not legacy and release.get("author", {}).get("login") != OWNER)
    ):
        raise ValueError("Reviewed macOS seed draft/source differs")
    assets = release.get("assets", [])
    by_name = {a.get("name"): a for a in assets}
    expected_names = {e["name"] for e in manifest["assets"].values()}
    if manifest_asset:
        expected_names.add(MANIFEST)
    if len(by_name) != len(assets) or set(by_name) != expected_names:
        raise ValueError("Reviewed seed draft has unexpected or duplicate assets")
    bound = {
        role: asset_identity(by_name[e["name"]], e, owner=not legacy)
        for role, e in manifest["assets"].items()
    }
    if manifest_asset:
        expected = {
            "name": MANIFEST,
            "size": manifest_asset["size"],
            "sha256": manifest_asset["digest"].removeprefix("sha256:"),
        }
        manifest_asset = asset_identity(manifest_asset, expected)
    return {
        "schemaVersion": 1,
        "sourceRevision": source,
        "releaseId": release["id"],
        "tag": release["tag_name"],
        "manifestAsset": manifest_asset,
        "seed": copy.deepcopy(manifest),
        "assets": bound,
    }


def resolve(releases: list[dict], source: str, read_manifest, compatible, rank) -> dict:
    """Resolve once; never use latest-release or mutable branch names as source."""
    candidates = []
    tags = set()
    for release in releases:
        tag = release.get("tag_name", "")
        if (
            not tag.startswith("macos-reviewed-seed-")
            or release.get("draft") is not True
        ):
            continue
        if tag in tags:
            raise ValueError("Ambiguous reviewed seed draft: " + tag)
        tags.add(tag)
        manifests = [a for a in release.get("assets", []) if a.get("name") == MANIFEST]
        if len(manifests) > 1:
            raise ValueError("Ambiguous seed review manifest")
        manifest_asset = manifests[0] if manifests else None
        if manifest_asset:
            if release.get("author", {}).get("login") != OWNER:
                raise ValueError("Seed review manifest must be staged by the owner")
            manifest = read_manifest(manifest_asset)
        elif tag == "macos-reviewed-seed-" + LEGACY_REVISION[:7]:
            manifest = LEGACY
        else:
            # An uploaded candidate without owner activation is not eligible.
            continue
        chosen = selection(release, manifest, source, manifest_asset)
        if compatible(manifest["sourceRevision"]):
            candidates.append((rank(manifest["sourceRevision"]), chosen))
    if not candidates:
        raise ValueError(
            "No compatible owner-reviewed macOS seed; prepare, review and stage a new seed, then start Release again"
        )
    candidates.sort(key=lambda item: item[0], reverse=True)
    if len(candidates) > 1 and candidates[0][0] == candidates[1][0]:
        raise ValueError("Ambiguous equally recent compatible macOS seeds")
    return candidates[0][1]


def load_selection(path: Path, expected_sha256: str, source: str) -> dict:
    if (
        path.is_symlink()
        or not checksum(expected_sha256)
        or sha256(path) != expected_sha256
    ):
        raise ValueError("Run-bound seed selection hash differs")
    value = json.loads(path.read_text())
    if (
        value.get("schemaVersion") != 1
        or value.get("sourceRevision") != source
        or type(value.get("releaseId")) is not int
    ):
        raise ValueError("Seed selection belongs to another release source")
    validate_manifest(value["seed"])
    if value.get("tag") != "macos-reviewed-seed-" + value["seed"]["sourceRevision"][:7]:
        raise ValueError("Seed selection tag differs")
    if set(value.get("assets", {})) != set(ROLES):
        raise ValueError("Seed selection input membership differs")
    for role, entry in value["seed"]["assets"].items():
        bound = value["assets"][role]
        if (
            type(bound.get("id")) is not int
            or bound["id"] <= 0
            or bound != {"id": bound["id"], **entry}
        ):
            raise ValueError("Seed selection asset differs")
    return value


def verify_delivery(directory: Path, manifest: dict) -> None:
    path = directory / "source-delivery.json"
    delivery = json.loads(path.read_text())
    if (
        directory.is_symlink()
        or path.is_symlink()
        or sha256(path) != manifest["sourceDeliverySha256"]
        or delivery.get("projectRevision") != manifest["sourceRevision"]
        or delivery.get("reviewer") != manifest["approvedBy"]
        or delivery.get("reviewedAt") != manifest["reviewedAt"]
    ):
        raise ValueError(
            "Seed source approval/delivery differs from the approved manifest"
        )


def extract_sources(directory: Path, manifest: dict) -> Path:
    target = directory / manifest["sourceDirectory"]
    if target.exists():
        raise ValueError("Seed source destination already exists")
    with tarfile.open(
        directory / manifest["assets"]["sources"]["name"], "r:gz"
    ) as archive:
        members = archive.getmembers()
        if (
            not members
            or len(members) > 500000
            or sum(m.size for m in members) > 16 * 1024**3
        ):
            raise ValueError("Seed source archive exceeds extraction bounds")
        seen = set()
        for member in members:
            path = PurePosixPath(member.name)
            if (
                not path.parts
                or path.parts[0] != target.name
                or path.is_absolute()
                or ".." in path.parts
                or member.name in seen
                or not (member.isfile() or member.isdir())
            ):
                raise ValueError("Unsafe or unexpected seed source member")
            seen.add(member.name)
        archive.extractall(directory, members=members, filter="data")
    verify_delivery(target, manifest)
    return target


def create_manifest(inputs: Path, sources: Path, approval: Path, output: Path) -> None:
    """Package existing exact approval evidence; never create approval fields."""
    if output.exists():
        raise ValueError("Refuse to overwrite seed activation manifest")
    review = json.loads(approval.read_text())
    delivery_path = sources / "source-delivery.json"
    delivery = json.loads(delivery_path.read_text())
    if (
        review.get("reviewer") != OWNER
        or not review.get("scope")
        or not review.get("statement")
        or review.get("projectRevision") != delivery.get("projectRevision")
        or review.get("approvedManifestSha256") != sha256(delivery_path)
        or review.get("reviewedAt") != delivery.get("reviewedAt")
    ):
        raise ValueError("Missing or mismatched actual owner source approval")
    value = {
        "schemaVersion": 1,
        "platform": "macos-aarch64",
        "sourceRevision": review["projectRevision"],
        "sourceDirectory": sources.name,
        "approvedBy": review["reviewer"],
        "reviewedAt": review["reviewedAt"],
        "sourceDeliverySha256": sha256(delivery_path),
        "assets": {},
    }
    files = list(inputs.iterdir())
    for role, pattern in ROLES.items():
        matches = [p for p in files if re.fullmatch(pattern, p.name)]
        if len(matches) != 1 or matches[0].is_symlink() or not matches[0].is_file():
            raise ValueError("Expected one regular seed input for " + role)
        path = matches[0]
        value["assets"][role] = {
            "name": path.name,
            "size": path.stat().st_size,
            "sha256": sha256(path),
        }
    if len(files) != len(ROLES):
        raise ValueError("Unexpected seed input files")
    validate_manifest(value)
    verify_delivery(sources, value)
    # The approved JSON must be in the actual uploaded source archive, not just
    # in a separate local directory beside different staged bytes.
    with tarfile.open(inputs / value["assets"]["sources"]["name"], "r:gz") as archive:
        member = archive.getmember(value["sourceDirectory"] + "/source-delivery.json")
        if not member.isfile() or member.size >= 1024**2:
            raise ValueError("Invalid archived source approval manifest")
        with archive.extractfile(member) as stream:
            if (
                hashlib.sha256(stream.read()).hexdigest()
                != value["sourceDeliverySha256"]
            ):
                raise ValueError(
                    "Uploaded source archive has another approval manifest"
                )
    with output.open("x") as stream:
        json.dump(value, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inputs", required=True, type=Path)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--approval", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    create_manifest(args.inputs, args.sources, args.approval, args.output)
