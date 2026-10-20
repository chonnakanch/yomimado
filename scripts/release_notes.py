"""Preview GitHub PR release notes, compose publication notes, or audit with git-cliff."""

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


def release_key(tag: str) -> tuple[int, ...]:
    if not RELEASE_TAG.fullmatch(tag):
        raise ValueError("Expected an app release tag such as v0.4.0")
    version, _, suffix = tag[1:].partition("-")
    major, minor, patch = (int(part) for part in version.split("."))
    stage, _, number = suffix.partition(".")
    return (
        major,
        minor,
        patch,
        {"alpha": 0, "beta": 1, "rc": 2, "": 3}[stage],
        int(number or "0"),
    )


def github_api(*args: str, root: Path) -> object:
    return json.loads(run("gh", "api", *args, root=root))


def github_preview(
    revision: str, output: Path, previous_tag: str | None = None, *, root: Path = ROOT
) -> dict:
    """Generate notes content only; never create a tag, draft release or approval."""
    preview = output.with_suffix(".md")
    if output.suffix != ".json" or any(
        path.exists() or path.is_symlink() for path in (output, preview)
    ):
        raise ValueError("Choose a new .json output and matching .md preview path")
    if git("rev-parse", "--is-shallow-repository", root=root) != "false":
        raise ValueError(
            "Fetch full Git history and release tags before generating notes"
        )
    end = git(
        "rev-parse", "--verify", "--end-of-options", f"{revision}^{{commit}}", root=root
    )
    version = json.loads(git("show", f"{end}:apps/desktop/package.json", root=root))[
        "version"
    ]
    target = "v" + version
    target_key = release_key(target)
    existing = run("git", "show-ref", "--tags", root=root)
    if any(line.endswith(" refs/tags/" + target) for line in existing.splitlines()):
        tagged = git("rev-parse", f"refs/tags/{target}^{{commit}}", root=root)
        if tagged != end:
            raise ValueError("Target version tag already points to a different source")
    repository = "chonnakanch/yomimado"
    pages = github_api(
        f"repos/{repository}/releases?per_page=100", "--paginate", "--slurp", root=root
    )
    published = {
        item["tag_name"]
        for page in pages
        for item in page
        if item.get("draft") is False
        and item.get("published_at")
        and RELEASE_TAG.fullmatch(item.get("tag_name", ""))
        and release_key(item["tag_name"]) < target_key
    }
    if previous_tag is not None:
        release_key(previous_tag)
        if previous_tag not in published:
            raise ValueError(
                "Previous tag must be a published app release before the target version"
            )
        candidates = [previous_tag]
    else:
        candidates = sorted(published, key=release_key, reverse=True)
    start = None
    for tag in candidates:
        candidate = git(
            "rev-parse",
            "--verify",
            "--end-of-options",
            f"refs/tags/{tag}^{{commit}}",
            root=root,
        )
        try:
            git("merge-base", "--is-ancestor", candidate, end, root=root)
        except subprocess.CalledProcessError as error:
            if error.returncode != 1:
                raise
            continue
        if candidate != end:
            previous_tag, start = tag, candidate
            break
    if start is None:
        raise ValueError(
            "No previous published app release is an ancestor of the target"
        )
    response = github_api(
        "--method",
        "POST",
        f"repos/{repository}/releases/generate-notes",
        "-f",
        f"tag_name={target}",
        "-f",
        f"target_commitish={end}",
        "-f",
        f"previous_tag_name={previous_tag}",
        root=root,
    )
    if not isinstance(response.get("body"), str) or not response["body"].strip():
        raise ValueError("GitHub returned no release-note content")
    # GitHub supplies the PR titles/numbers. Keep one canonical comparison last.
    changes = re.sub(
        r"^\*\*Full Changelog\*\*:.*$", "", response["body"], flags=re.MULTILINE
    ).strip()
    record = {
        "sourceRevision": end,
        "version": version,
        "previousTag": previous_tag,
        "previousRevision": start,
        "changes": changes,
        "comparison": f"https://github.com/{repository}/compare/{previous_tag}...{target}",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as destination:
        json.dump(record, destination, ensure_ascii=False, indent=2)
        destination.write("\n")
    with preview.open("x", encoding="utf-8") as destination:
        destination.write(f"{changes}\n\n**Full Changelog**: {record['comparison']}\n")
    return record


def compose(prepared: Path, expected_hash: str, candidate: dict, output: Path) -> None:
    """Use the exact pre-approval preview with a verified candidate after approval."""
    if output.exists() or output.is_symlink():
        raise ValueError("Output already exists; choose a new release-note path")
    data = prepared.read_bytes()
    if hashlib.sha256(data).hexdigest() != expected_hash:
        raise ValueError("Release-note preview SHA-256 differs from the plan")
    record = json.loads(data)
    if any(
        record[field] != candidate[field] for field in ("sourceRevision", "version")
    ):
        raise ValueError(
            "Release-note preview does not match the candidate source/version"
        )
    tag = "v" + candidate["version"]
    if candidate["tag"] != tag or type(candidate["prerelease"]) is not bool:
        raise ValueError("Invalid candidate release identity")
    release_key(record["previousTag"])
    comparison = f"https://github.com/chonnakanch/yomimado/compare/{record['previousTag']}...{tag}"
    if record["comparison"] != comparison:
        raise ValueError("Release-note comparison differs from the selected app tags")
    text = f"{record['changes']}\n\n**Full Changelog**: {comparison}\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as destination:
        destination.write(text)


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
        help="new local commit-audit file; not used as the public release body",
    )
    github = commands.add_parser(
        "github", help="preview GitHub PR notes without creating a release"
    )
    github.add_argument("--revision", default="HEAD")
    github.add_argument(
        "--previous-tag",
        help="published ancestor app tag; default: highest earlier version",
    )
    github.add_argument(
        "--output",
        required=True,
        type=Path,
        help="new .json file; also writes a .md preview",
    )
    publication = commands.add_parser(
        "compose", help="compose the approved candidate's release body"
    )
    publication.add_argument("--input", required=True, type=Path)
    publication.add_argument("--sha256", required=True)
    publication.add_argument(
        "--record", required=True, help="verified candidate JSON from the workflow"
    )
    publication.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.action == "prepare":
            print(tool(prepare=True))
        elif args.action == "generate":
            revision, count = generate(args.previous_tag, args.revision, args.output)
            print(f"Drafted {count} commits at {revision} to {args.output}")
        elif args.action == "github":
            record = github_preview(args.revision, args.output, args.previous_tag)
            print(
                f"Previewed {record['previousTag']} to v{record['version']} at {record['sourceRevision']}"
            )
        else:
            compose(args.input, args.sha256, json.loads(args.record), args.output)
            print(f"Composed release notes at {args.output}")
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
