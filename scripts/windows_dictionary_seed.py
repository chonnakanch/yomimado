"""Shared safe redirects and hash-checked restoration of dictionary originals."""

from __future__ import annotations

import hashlib
import tarfile
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler

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
