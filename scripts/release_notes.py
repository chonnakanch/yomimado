"""Prepare pinned git-cliff or generate a complete, reviewable local notes draft."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import stat
import subprocess
import tarfile
import tempfile
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
VERSION = "2.14.2"
ASSETS = {
    ("Darwin", "arm64"): (
        "aarch64-apple-darwin.tar.gz",
        "a0be97e237d440d34c5e508ec21d070b2c85cbb8be48a46a56f9a4e8bd247f05",
    ),
    ("Windows", "amd64"): (
        "x86_64-pc-windows-msvc.zip",
        "6ece2112b3f4af462190ecbea4aeb1315fff6af415629b597f84319073c31131",
    ),
    # CI verification host only; this does not add a Linux desktop target.
    ("Linux", "x86_64"): (
        "x86_64-unknown-linux-gnu.tar.gz",
        "24f397c733add5390fdceee3a2088588ab0d5f944ce00d34cb7029b888cf2db4",
    ),
}
RELEASE_TAG = re.compile(
    r"v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:-(?:alpha|beta|rc)\.(?:0|[1-9][0-9]*))?"
)


def tool_input() -> tuple[Path, str, str]:
    key = (platform.system(), platform.machine().lower())
    if key not in ASSETS:
        raise ValueError(
            "git-cliff preparation supports macOS ARM64, Windows x64 and Linux x64 CI"
        )
    suffix, expected = ASSETS[key]
    name = f"git-cliff-{VERSION}-{suffix}"
    archive = ROOT / "services/ocr/build/release-tools/git-cliff" / VERSION / name
    binary = "git-cliff.exe" if key[0] == "Windows" else "git-cliff"
    return archive, expected, binary


def binary_bytes(archive: Path, expected: str, binary: str) -> bytes:
    if (
        archive.is_symlink()
        or hashlib.sha256(archive.read_bytes()).hexdigest() != expected
    ):
        raise ValueError("git-cliff archive SHA-256 differs from its reviewed pin")
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as source:
            members = [
                p for p in source.infolist() if PurePosixPath(p.filename).name == binary
            ]
            if (
                len(members) != 1
                or members[0].is_dir()
                or stat.S_ISLNK(members[0].external_attr >> 16)
            ):
                raise ValueError("Expected one regular git-cliff executable")
            return source.read(members[0])
    with tarfile.open(archive) as source:
        members = [
            p for p in source.getmembers() if PurePosixPath(p.name).name == binary
        ]
        if len(members) != 1 or not members[0].isfile():
            raise ValueError("Expected one regular git-cliff executable")
        with source.extractfile(members[0]) as executable:
            return executable.read()


def tool(*, prepare: bool = False) -> Path:
    archive, expected, name = tool_input()
    if not archive.exists():
        if not prepare:
            raise ValueError("Run Python 3.11+ scripts/release_notes.py prepare first")
        archive.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://github.com/orhun/git-cliff/releases/download/v{VERSION}/{archive.name}"
        with urlopen(url, timeout=120) as response:
            data = response.read(64 * 1024**2 + 1)
        if len(data) > 64 * 1024**2 or hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(
                "Downloaded git-cliff size/hash differs from its reviewed pin"
            )
        with archive.open("xb") as output:
            output.write(data)
    data = binary_bytes(archive, expected, name)
    executable = (
        archive.parent
        / (archive.name.removesuffix(".tar.gz").removesuffix(".zip"))
        / name
    )
    if executable.is_symlink():
        raise ValueError("git-cliff executable must not be a symlink")
    if not executable.exists() and prepare:
        executable.parent.mkdir(parents=True, exist_ok=True)
        with executable.open("xb") as output:
            output.write(data)
        executable.chmod(0o755)
    if not executable.is_file() or executable.read_bytes() != data:
        raise ValueError("Cached git-cliff executable differs from the pinned archive")
    return executable


def run(*args: str, root: Path) -> str:
    # Do not let user git-cliff environment overrides select filters, paths or remotes.
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_CLIFF_")}
    return subprocess.run(
        args,
        cwd=root,
        env=env,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=True,
    ).stdout


def git(*args: str, root: Path) -> str:
    return run("git", *args, root=root).strip()


def generate(
    previous_tag: str, revision: str, output: Path, *, root: Path = ROOT
) -> tuple[str, int]:
    if output.exists() or output.is_symlink():
        raise ValueError("Output already exists; choose a new draft path")
    if not RELEASE_TAG.fullmatch(previous_tag):
        raise ValueError("Previous tag must be an app release tag such as v0.3.0")
    if git("rev-parse", "--is-shallow-repository", root=root) != "false":
        raise ValueError(
            "Fetch full Git history and release tags before generating notes"
        )
    start = git(
        "rev-parse",
        "--verify",
        "--end-of-options",
        f"refs/tags/{previous_tag}^{{commit}}",
        root=root,
    )
    end = git(
        "rev-parse", "--verify", "--end-of-options", f"{revision}^{{commit}}", root=root
    )
    git("merge-base", "--is-ancestor", start, end, root=root)
    expected = git("rev-list", f"{start}..{end}", root=root).splitlines()
    if not expected:
        raise ValueError("No commits after the selected previous release tag")
    version = json.loads(git("show", f"{end}:apps/desktop/package.json", root=root))[
        "version"
    ]
    if not RELEASE_TAG.fullmatch("v" + version):
        raise ValueError("Target commit has an unsupported app version")
    executable = str(tool())
    if run(executable, "--version", root=root).strip() != f"git-cliff {VERSION}":
        raise ValueError("git-cliff version differs from its reviewed pin")
    common = (
        executable,
        "--config",
        str(ROOT / "cliff.toml"),
        "--offline",
        "--no-exec",
    )
    context = json.loads(
        run(
            *common,
            "--context",
            "--tag",
            "v" + version,
            "--",
            f"{start}..{end}",
            root=root,
        )
    )
    actual = [commit["id"] for release in context for commit in release["commits"]]
    if Counter(actual) != Counter(expected):
        raise ValueError(
            "git-cliff omitted or duplicated commits; refusing incomplete release notes"
        )
    with tempfile.TemporaryDirectory(prefix="yomimado-release-notes-") as temporary:
        path = Path(temporary) / "context.json"
        path.write_text(json.dumps(context), encoding="utf-8")
        body = run(*common, "--from-context", str(path), root=root)
    if any(f"/commit/{sha}" not in body for sha in expected):
        raise ValueError("Rendered release notes omit commit links")
    header = (
        f"# YomiMado {version} — release notes draft\n\n"
        "Review this commit inventory against the final diff and CHANGELOG.md. "
        "Added-then-reverted features are not available features.\n\n"
        f"Previous release: `{previous_tag}` (`{start}`).\n\n"
        f"Target source: `{end}`. Included commits: {len(expected)}.\n\n"
        f"[Full comparison](https://github.com/chonnakanch/yomimado/compare/{start}...{end})\n\n"
        f"Generated locally with git-cliff {VERSION}; no tag, release or approval created.\n\n"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as destination:
        destination.write(header + body.rstrip() + "\n")
    return end, len(expected)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser(
        "prepare", help="explicitly download and verify the pinned maintainer tool"
    )
    draft = commands.add_parser(
        "generate", help="write a local draft; never overwrite a file or publish"
    )
    draft.add_argument(
        "--previous-tag",
        required=True,
        help="previous published release, including pre-releases",
    )
    draft.add_argument(
        "--revision",
        default="HEAD",
        help="proposed release commit/ref (resolved to an exact SHA)",
    )
    draft.add_argument(
        "--output",
        required=True,
        type=Path,
        help="new draft file; keep curated notes separate",
    )
    args = parser.parse_args()
    try:
        if args.action == "prepare":
            print(tool(prepare=True))
        else:
            revision, count = generate(args.previous_tag, args.revision, args.output)
            print(f"Drafted {count} commits at {revision} to {args.output}")
    except subprocess.CalledProcessError as error:
        parser.error(error.stderr.strip() or str(error))
    except (
        OSError,
        ValueError,
        KeyError,
        tarfile.TarError,
        zipfile.BadZipFile,
    ) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
