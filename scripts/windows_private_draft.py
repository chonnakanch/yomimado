"""Shared GitHub API and hash validation for Windows transfer candidates.

The historical module name is retained for current callers; private staging
commands have retired. The protected shared workflow owns publication.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
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
