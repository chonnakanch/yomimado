"""Vendor missing license texts from pinned upstream GitHub commits.

Run this deliberately when auditing a release. The normal build stays offline
and copies the checked-in results. Downloaded texts are third-party notices,
not YomiMado source code.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "THIRD_PARTY_LICENSES/upstream"
SOURCES = {
    "loguru": ("Delgan", "loguru", ["LICENSE"]),
    "sentencepiece": ("google", "sentencepiece", ["LICENSE"]),
    "sudachi-rs": ("WorksApplications", "sudachi.rs", ["LICENSE"]),
    "tokenizers": ("huggingface", "tokenizers", ["LICENSE"]),
    "torchsummary": ("sksq96", "pytorch-summary", ["LICENSE"]),
    "alloc-stdlib": ("dropbox", "rust-alloc-no-stdlib", ["LICENSE"]),
    "objc2": (
        "madsmtm",
        "objc2",
        ["LICENSE.md", "LICENSE-MIT.txt", "LICENSE-APACHE.txt", "LICENSE-ZLIB.txt"],
    ),
    "defmt": ("knurling-rs", "defmt", ["LICENSE-MIT", "LICENSE-APACHE"]),
    "selectors": ("spdx", "license-list-data", ["text/MPL-2.0.txt"]),
    "lgpl-2.1": ("spdx", "license-list-data", ["text/LGPL-2.1-only.txt"]),
    "tauri": ("tauri-apps", "tauri", ["LICENSE-MIT", "LICENSE-APACHE-2.0"]),
    "unic": ("open-i18n", "rust-unic", ["LICENSE-MIT", "LICENSE-APACHE"]),
}
EXTERNAL_FILES = {
    "EDRDG-dictionary-licence.html": "https://www.edrdg.org/edrdg/licence.html",
    "CC-BY-SA-4.0.txt": "https://creativecommons.org/licenses/by-sa/4.0/legalcode.txt",
    "Apache-2.0.txt": "https://www.apache.org/licenses/LICENSE-2.0.txt",
    "manga-ocr-model-card.md": (
        "https://huggingface.co/kha-white/manga-ocr-base/raw/"
        "aa6573bd10b0d446cbf622e29c3e084914df9741/README.md"
    ),
}


def request(url: str) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": "YomiMado-release-notice-audit"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read(200_001)
    if len(data) > 200_000:
        raise ValueError(f"Unexpectedly large notice: {url}")
    return data


def main() -> None:
    index = {}
    for group, (owner, repo, paths) in SOURCES.items():
        project = f"{owner}/{repo}"
        repository = json.loads(request(f"https://api.github.com/repos/{project}"))
        default_branch = repository["default_branch"]
        reference = json.loads(
            request(
                f"https://api.github.com/repos/{project}/git/ref/heads/{default_branch}"
            )
        )
        commit = reference["object"]["sha"]
        files = []
        for path in paths:
            url = f"https://raw.githubusercontent.com/{project}/{commit}/{path}"
            data = request(url)
            data.decode("utf-8")
            filename = Path(path).name
            if group == "lgpl-2.1":
                filename = "LICENSE-LGPL-2.1.txt"
            elif group == "selectors":
                filename = f"LICENSE-{filename}"
            destination = OUTPUT / group / filename
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            files.append(
                {
                    "path": str(destination.relative_to(OUTPUT)),
                    "source": url,
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
            )
        index[group] = {"project": project, "commit": commit, "files": files}
        print(f"{group}: {commit[:12]}, {len(files)} file(s)")
    assets = []
    for filename, url in EXTERNAL_FILES.items():
        data = request(url)
        data.decode("utf-8")
        destination = OUTPUT / "assets" / filename
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        assets.append(
            {
                "path": str(destination.relative_to(OUTPUT)),
                "source": url,
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    index["assets"] = {"files": assets}
    print(f"assets: {len(assets)} file(s)")
    (OUTPUT / "sources.json").write_text(json.dumps(index, indent=2) + "\n")


if __name__ == "__main__":
    main()
