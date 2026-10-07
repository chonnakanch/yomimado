"""Stage an exact private Windows test candidate; never publish or create a tag."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

from windows_release import digest, read_json

REPOSITORY = "chonnakanch/yomimado"
API = "https://api.github.com/repos/" + REPOSITORY


def request(url: str, method="GET", data=None, content_type="application/json"):
    # The Actions token stays in an HTTP header and is never printed or saved.
    headers = {
        "Authorization": "Bearer " + os.environ["GH_TOKEN"],
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": content_type,
    }
    body = json.dumps(data).encode() if isinstance(data, dict) else data
    with urlopen(
        Request(url, data=body, headers=headers, method=method), timeout=600
    ) as response:
        return json.load(response)


def tag_absent(tag: str) -> None:
    try:
        request(API + "/git/ref/tags/" + tag)
    except HTTPError as error:
        if error.code == 404:
            return
        raise
    raise ValueError("Private staging must not create or reuse a public tag")


def candidate_files(directory: Path, revision: str) -> list[Path]:
    record = read_json(directory / "windows-candidate.json")
    if (
        record["sourceRevision"] != revision
        or record["mode"] != "private-test"
        or record["installedAppVerified"] is not False
        or record["publicDistributionApproved"] is not False
    ):
        raise ValueError("Private candidate provenance/gates differ")
    expected = dict(record["assets"])
    expected["windows-candidate.json"] = digest(directory / "windows-candidate.json")
    sums = (directory / "SHA256SUMS.txt").read_text()
    if sums != "".join(f"{sha}  {name}\n" for name, sha in expected.items()):
        raise ValueError("Checksum file differs")
    expected["SHA256SUMS.txt"] = digest(directory / "SHA256SUMS.txt")
    files = sorted(directory.iterdir())
    if {p.name for p in files} != set(expected):
        raise ValueError("Unexpected private candidate files")
    for path in files:
        if (
            not path.is_file()
            or path.is_symlink()
            or digest(path) != expected[path.name]
        ):
            raise ValueError("Private candidate changed: " + path.name)
        if path.stat().st_size >= 2 * 1024**3:
            raise ValueError("Asset exceeds GitHub's release asset limit")
    return files


def stage(directory: Path) -> None:
    revision = os.environ["GITHUB_SHA"]
    if (
        os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("GITHUB_REPOSITORY") != REPOSITORY
        or os.environ.get("GITHUB_REF") != "refs/heads/develop"
        or not re.fullmatch(r"[0-9a-f]{40}", revision)
    ):
        raise ValueError(
            "Private staging is restricted to the tracked development workflow"
        )
    files = candidate_files(directory, revision)
    tag = "windows-private-test-" + revision
    tag_absent(tag)
    existing = [
        r for r in request(API + "/releases?per_page=100") if r["tag_name"] == tag
    ]
    if len(existing) > 1:
        raise ValueError("Ambiguous private draft")
    if existing:
        release = existing[0]
        if (
            release["draft"] is not True
            or release["target_commitish"] != revision
            or release["assets"]
        ):
            raise ValueError("Only an empty exact-commit private draft can be staged")
    else:
        release = request(
            API + "/releases",
            "POST",
            {
                "tag_name": tag,
                "target_commitish": revision,
                "name": "PRIVATE Windows installer test — " + revision[:12],
                "draft": True,
                "prerelease": True,
                "body": "Private maintainer test only. Source/licence review and exact-installer human approval remain OPEN. Do not publish this draft.\n\nSource: "
                + revision
                + "\n\n"
                + (directory / "SHA256SUMS.txt").read_text(),
            },
        )
    if release["draft"] is not True:
        raise ValueError("GitHub did not create an unpublished draft")
    upload = release["upload_url"].split("{")[0]
    for path in files:
        print("Staging private asset: " + path.name, flush=True)
        request(
            upload + "?name=" + quote(path.name),
            "POST",
            path.read_bytes(),
            "application/octet-stream",
        )
    final = request(API + "/releases/" + str(release["id"]))
    if (
        final["draft"] is not True
        or final["target_commitish"] != revision
        or final["tag_name"] != tag
    ):
        raise ValueError("Private draft identity changed")
    uploaded = {
        a["name"]: a["digest"] for a in final["assets"] if a["state"] == "uploaded"
    }
    if uploaded != {p.name: "sha256:" + digest(p) for p in files}:
        raise ValueError("GitHub uploaded asset hashes differ")
    tag_absent(tag)
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
        summary.write("\nOwner-only draft: " + final["html_url"] + "\n")
    print("Verified owner-only draft: " + final["html_url"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    stage(parser.parse_args().directory)
