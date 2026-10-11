"""Restore exact dictionary originals from a private candidate, never runtime approval."""

from __future__ import annotations

import hashlib
import os
import sys
import tarfile
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from windows_private_draft import API, REPOSITORY, request
from windows_release import BUILD, RESOURCES, SERVICE, digest, read_json, write_json

REVISION = "79065df7ba34a3aaa4ddb3a1ebb30e164405742a"
TAG = "windows-private-test-" + REVISION
FILENAME = "windows-dictionary-snapshots.tar.gz"
ARCHIVE_SHA256 = "5c0a690c74b1d361b061b0ec02b7bace314e1cdcdc985c1ed4675270c15e0db8"
NAMES = {"JMdict_e.gz", "kanjidic2.xml.gz"}


class SafeRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urlsplit(newurl).scheme != "https":
            raise ValueError("Dictionary asset redirected away from HTTPS")
        redirected = super().redirect_request(req, fp, code, msg, headers, newurl)
        if redirected and urlsplit(req.full_url).netloc != urlsplit(newurl).netloc:
            # GitHub's signed asset URL does not need the repository token.
            redirected.remove_header("Authorization")
        return redirected


def restore(archive: Path, assets: Path, expected: dict[str, str]) -> None:
    if set(expected) != NAMES:
        raise ValueError("Dictionary manifest membership differs")
    contents = {}
    with tarfile.open(archive, "r:gz") as source:
        members = source.getmembers()
        if len(members) != 2 or {m.name for m in members} != NAMES:
            raise ValueError("Unexpected dictionary seed members")
        for member in members:
            if not member.isfile() or member.size > 64 * 1024**2:
                raise ValueError("Dictionary seed contains a link or oversized input")
            stream = source.extractfile(member)
            if stream is None:
                raise ValueError("Missing dictionary seed data")
            with stream:
                data = stream.read()
            if hashlib.sha256(data).hexdigest() != expected[member.name]:
                raise ValueError("Dictionary original hash differs: " + member.name)
            contents[member.name] = data
    # Validate both originals before writing either resource. Never extract paths.
    assets.mkdir(parents=True, exist_ok=True)
    for name, data in contents.items():
        (assets / name).write_bytes(data)


def main() -> None:
    if (
        sys.platform != "win32"
        or os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("GITHUB_REPOSITORY") != REPOSITORY
        or os.environ.get("GITHUB_REF") != "refs/heads/develop"
    ):
        raise ValueError("Dictionary seed is restricted to Windows development CI")
    drafts = [
        r for r in request(API + "/releases?per_page=100") if r["tag_name"] == TAG
    ]
    if (
        len(drafts) != 1
        or drafts[0]["draft"] is not True
        or drafts[0]["target_commitish"] != REVISION
    ):
        raise ValueError("Pinned dictionary seed draft identity differs")
    assets = [a for a in drafts[0]["assets"] if a["name"] == FILENAME]
    if (
        len(assets) != 1
        or assets[0]["digest"] != "sha256:" + ARCHIVE_SHA256
        or not isinstance(assets[0]["id"], int)
    ):
        raise ValueError("Pinned dictionary seed asset identity differs")
    archive = BUILD / FILENAME
    archive.parent.mkdir(parents=True, exist_ok=True)
    if not archive.exists():
        query = Request(
            API + "/releases/assets/" + str(assets[0]["id"]),
            headers={
                "Authorization": "Bearer " + os.environ["GH_TOKEN"],
                "Accept": "application/octet-stream",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        with build_opener(SafeRedirect()).open(query, timeout=120) as response:
            data = response.read(64 * 1024**2 + 1)
        if len(data) > 64 * 1024**2:
            raise ValueError("Dictionary seed archive exceeds its size limit")
        if hashlib.sha256(data).hexdigest() != ARCHIVE_SHA256:
            raise ValueError("Downloaded dictionary seed hash differs")
        archive.write_bytes(data)
    if digest(archive) != ARCHIVE_SHA256:
        raise ValueError("Retained dictionary seed hash differs")
    expected = {
        e["path"]: e["sha256"]
        for e in read_json(SERVICE / "windows-assets.json")
        if e["path"] in NAMES
    }
    restore(archive, RESOURCES / "assets", expected)
    write_json(
        BUILD / "dictionary-seed.json",
        {
            "sourceRevision": REVISION,
            "releaseId": drafts[0]["id"],
            "assetId": assets[0]["id"],
            "archiveSha256": ARCHIVE_SHA256,
            "originals": expected,
            "scope": "dictionary-originals-only",
            "publicDistributionApproved": False,
        },
    )
    print("Restored hash-pinned dictionary originals; no runtime approval inherited")


if __name__ == "__main__":
    main()
