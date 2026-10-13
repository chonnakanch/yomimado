"""Update npm, Tauri and Cargo app versions together (Python 3.11+)."""

from __future__ import annotations

import argparse
import importlib.util
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = (
    "apps/desktop/package.json",
    "apps/desktop/package-lock.json",
    "apps/desktop/src-tauri/tauri.conf.json",
    "apps/desktop/src-tauri/Cargo.toml",
    "apps/desktop/src-tauri/Cargo.lock",
)
spec = importlib.util.spec_from_file_location(
    "release_ci", ROOT / "scripts/macos-ci-release.py"
)
ci = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci)


def replace_one(text: str, pattern: str, version: str) -> str:
    result, count = re.subn(pattern, lambda match: match[1] + f'"{version}"', text)
    if count != 1:
        raise ValueError("Expected exactly one app version field in its section")
    return result


def updated_text(name: str, text: str, version: str) -> str:
    if name.endswith(".json"):
        # Target the repository's root fields without reformatting the JSON or
        # replacing unrelated dependency versions that happen to match the app.
        result = replace_one(text, r'(?m)^(  "version"\s*:\s*)"[^"\r\n]*"', version)
        if name.endswith("package-lock.json"):
            result = replace_one(
                result,
                r'(?m)^(    ""\s*:\s*\{[\s\S]*?^      "version"\s*:\s*)"[^"\r\n]*"',
                version,
            )
    else:
        header = "[[package]]" if name.endswith("Cargo.lock") else "[package]"
        sections = list(
            re.finditer(rf"(?ms)^{re.escape(header)}[^\r\n]*\r?\n.*?(?=^\[|\Z)", text)
        )
        selected = []
        for match in sections:
            package = tomllib.loads(match[0])["package"]
            if isinstance(package, list):
                package = package[0]
            if package.get("name") == "yomimado" and "source" not in package:
                selected.append(match)
        if len(selected) != 1:
            raise ValueError("Expected exactly one local yomimado package")
        match = selected[0]
        block = replace_one(
            match[0], r'(?m)^([ \t]*version\s*=\s*)"[^"\r\n]*"', version
        )
        result = text[: match.start()] + block + text[match.end() :]
    if ci.normalized(name, text) != ci.normalized(name, result):
        raise ValueError("Version update would change non-version data: " + name)
    return result


def update(version: str, *, root: Path = ROOT, dry_run: bool = False) -> str:
    prerelease = ci.is_prerelease(version)
    current = ci.version(root)
    # Prepare and validate every file before writing any of them. Preserve exact
    # formatting and line endings, including Windows checkouts using CRLF.
    originals = {root / name: (root / name).read_bytes() for name in FILES}
    replacements = {
        root / name: updated_text(
            name, originals[root / name].decode("utf-8"), version
        ).encode("utf-8")
        for name in FILES
    }
    if not dry_run:
        written = []
        try:
            for path, data in replacements.items():
                if data != originals[path]:
                    written.append(path)
                    path.write_bytes(data)
        except OSError:
            for path in written:
                path.write_bytes(originals[path])
            raise
    label = "pre-release" if prerelease else "stable"
    verb = "Would update" if dry_run else "Updated"
    print(f"{verb} {current} -> {version} ({label})")
    for name in FILES:
        print("  " + name)
    return current


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", help="e.g. 0.2.0, 1.0.0-beta.1 or 1.0.0 (without v)")
    parser.add_argument(
        "--dry-run", action="store_true", help="validate and preview without writing"
    )
    args = parser.parse_args()
    try:
        update(args.version, dry_run=args.dry_run)
    except (OSError, ValueError, KeyError, StopIteration) as error:
        parser.error(str(error) or "Required app version field is missing")


if __name__ == "__main__":
    main()
