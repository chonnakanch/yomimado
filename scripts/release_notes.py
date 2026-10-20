"""Preview GitHub PR release notes and compose source-bound publication notes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELEASE_TAG = re.compile(
    r"v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:-(?:alpha|beta|rc)\.(?:0|[1-9][0-9]*))?"
)


def run(*args: str, root: Path) -> str:
    return subprocess.run(
        args,
        cwd=root,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=True,
    ).stdout


def git(*args: str, root: Path) -> str:
    return run("git", *args, root=root).strip()


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
        if args.action == "github":
            record = github_preview(args.revision, args.output, args.previous_tag)
            print(
                f"Previewed {record['previousTag']} to v{record['version']} at {record['sourceRevision']}"
            )
        else:
            compose(args.input, args.sha256, json.loads(args.record), args.output)
            print(f"Composed release notes at {args.output}")
    except subprocess.CalledProcessError as error:
        parser.error(error.stderr.strip() or str(error))
    except (OSError, ValueError, KeyError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
