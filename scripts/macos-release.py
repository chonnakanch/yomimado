"""Fail-closed checks and inside-out signing for the direct-download release."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import plistlib
import re
import subprocess
import sys
from pathlib import Path

MACHO = {
    b"\xfe\xed\xfa\xce",
    b"\xce\xfa\xed\xfe",
    b"\xfe\xed\xfa\xcf",
    b"\xcf\xfa\xed\xfe",
    b"\xca\xfe\xba\xbe",
    b"\xbe\xba\xfe\xca",
    b"\xca\xfe\xba\xbf",
    b"\xbf\xba\xfe\xca",
}


def run(*args: str) -> str:
    return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT)


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(chunk)
    return result.hexdigest()


def contained(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(root.resolve()):
        raise ValueError(f"Path escapes release directory: {relative}")
    if not path.is_file():
        raise ValueError(f"Missing release file: {relative}")
    return path


def inventory(notices: Path) -> dict:
    return {
        "third-party-manifest.json": digest(notices / "third-party-manifest.json"),
        "native-libraries.json": digest(notices / "native-libraries.json"),
    }


def source_items(notices: Path) -> dict[str, list[str]]:
    items = {"project:yomimado": ["LICENSE"]}
    for component in json.loads((notices / "third-party-manifest.json").read_text())[
        "components"
    ]:
        key = f"{component['ecosystem']}:{component['name']}@{component['version']}"
        items[key] = component["noticeFiles"]
    for binary in json.loads((notices / "native-libraries.json").read_text())[
        "binaries"
    ]:
        if not binary.get("aliasOf"):
            items[binary["id"]] = []
    return items


def verify_sources(notices: Path, source_dir: Path, revision: str) -> None:
    """Validate review evidence and local source delivery, never just homepage URLs.

    Archive contents and legal compatibility still need the named human review.
    Requiring every component is deliberately conservative for frozen imports.
    """
    delivery = json.loads((source_dir / "source-delivery.json").read_text())
    if delivery.get("projectRevision") != revision:
        raise ValueError("Source delivery is for a different project revision")
    if delivery.get("inventorySha256") != inventory(notices):
        raise ValueError(
            "Source delivery is for a different dependency/native inventory"
        )
    if not delivery.get("reviewer") or not delivery.get("reviewedAt"):
        raise ValueError("Source and licence review has not been recorded")
    if not delivery.get("buildInstructions"):
        raise ValueError("Source delivery needs build/installation instructions")
    contained(source_dir, delivery["buildInstructions"])
    expected = source_items(notices)
    covered = {}
    source_hashes = {}
    for entry in delivery.get("components", []):
        key = entry["id"]
        if key in covered or key not in expected:
            raise ValueError(f"Duplicate or unexpected source component: {key}")
        source = contained(source_dir, entry.get("archive", ""))
        if source not in source_hashes:
            source_hashes[source] = digest(source)
        if not entry.get("sha256") or source_hashes[source] != entry["sha256"]:
            raise ValueError(f"Source checksum mismatch: {key}")
        if not entry.get("licenseEvidence") or not entry.get("noticeFiles"):
            raise ValueError(f"Unreviewed licence/notice evidence: {key}")
        for notice in entry["noticeFiles"]:
            contained(notices, notice)
        covered[key] = entry
    missing = set(expected) - set(covered)
    if missing:
        raise ValueError(
            f"Missing corresponding-source entries: {', '.join(sorted(missing))}"
        )


def verify_hobby(notices: Path) -> None:
    metadata = json.loads((notices / "distribution.json").read_text())
    if metadata != {
        "mode": "unnotarized-hobby",
        "developerIdSigned": False,
        "appleNotarized": False,
        "manualGatekeeperApproval": True,
    }:
        raise ValueError("Not an explicitly unnotarized hobby candidate")


def preflight() -> None:
    if sys.platform != "darwin":
        raise ValueError("Release signing requires macOS")
    identity = os.environ.get("APPLE_SIGNING_IDENTITY", "")
    team = os.environ.get("YOMIMADO_APPLE_TEAM_ID", "")
    profile = os.environ.get("YOMIMADO_NOTARY_PROFILE", "")
    if not re.fullmatch(r"[A-Z0-9]{10}", team):
        raise ValueError("Set YOMIMADO_APPLE_TEAM_ID to your Developer ID team")
    if not identity.startswith("Developer ID Application: ") or not identity.endswith(
        f"({team})"
    ):
        raise ValueError(
            "Set APPLE_SIGNING_IDENTITY to a Developer ID Application identity for that team"
        )
    if identity not in run("security", "find-identity", "-v", "-p", "codesigning"):
        raise ValueError(
            "Developer ID certificate and its private key are not available in the Keychain"
        )
    if not profile:
        raise ValueError("Set YOMIMADO_NOTARY_PROFILE to a notarytool Keychain profile")
    # Authenticates without submitting a binary or putting passwords on argv.
    run(
        "xcrun",
        "notarytool",
        "history",
        "--keychain-profile",
        profile,
        "--output-format",
        "json",
    )


def macho_files(root: Path) -> list[Path]:
    paths = []
    for path in root.rglob("*"):
        if path.is_file() and not path.is_symlink():
            with path.open("rb") as stream:
                if stream.read(4) in MACHO:
                    paths.append(path)
    return sorted(paths, key=lambda path: (-len(path.parts), str(path)))


def sign_runtime(root: Path) -> None:
    identity = os.environ["APPLE_SIGNING_IDENTITY"]
    files = macho_files(root)
    if not files:
        raise ValueError("No Mach-O runtime binaries to sign")
    for path in files:
        run(
            "codesign",
            "--force",
            "--timestamp",
            "--options",
            "runtime",
            "--sign",
            identity,
            str(path),
        )
    # Framework resource seals must be signed after their inner binaries.
    frameworks = sorted(root.rglob("*.framework"), key=lambda path: -len(path.parts))
    for path in frameworks:
        run(
            "codesign",
            "--force",
            "--timestamp",
            "--options",
            "runtime",
            "--sign",
            identity,
            str(path),
        )
    print(f"Signed {len(files)} Mach-O files and {len(frameworks)} frameworks")


def verify_signature(path: Path, *, executable: bool = True) -> None:
    team = os.environ.get("YOMIMADO_APPLE_TEAM_ID", "")
    if not re.fullmatch(r"[A-Z0-9]{10}", team):
        raise ValueError("Set YOMIMADO_APPLE_TEAM_ID for signature verification")
    run("codesign", "--verify", "--strict", "--verbose=2", str(path))
    info = run("codesign", "--display", "--verbose=4", str(path))
    if (
        f"TeamIdentifier={team}\n" not in info
        or "Authority=Developer ID Application:" not in info
    ):
        raise ValueError(f"Not signed by the expected Developer ID team: {path.name}")
    runtime = re.search(r"flags=.*\([^\n)]*\bruntime\b[^\n)]*\)", info)
    if "Timestamp=" not in info or (executable and not runtime):
        raise ValueError(f"Missing secure timestamp/hardened runtime: {path.name}")


def verify_hobby_app(app: Path) -> None:
    """Require a valid local bundle seal without claiming Developer ID trust."""
    if not (app / "Contents/_CodeSignature/CodeResources").is_file():
        raise ValueError("Hobby app is missing its signed resource seal")
    run("codesign", "--verify", "--deep", "--strict", str(app))
    info = run("codesign", "--display", "--verbose=4", str(app))
    with (app / "Contents/Info.plist").open("rb") as stream:
        identifier = plistlib.load(stream)["CFBundleIdentifier"]
    if "Signature=adhoc\n" not in info or f"Identifier={identifier}\n" not in info:
        raise ValueError("Hobby app needs a local ad-hoc bundle signature")
    for path in macho_files(app):
        run("codesign", "--verify", "--strict", str(path))


def minimum_versions(load_commands: str) -> list[tuple[int, ...]]:
    versions = []
    for command in load_commands.split("Load command"):
        field = None
        if "cmd LC_BUILD_VERSION\n" in command:
            field = "minos"
        elif "cmd LC_VERSION_MIN_MACOSX\n" in command:
            field = "version"
        if field:
            for value in re.findall(rf"\b{field}\s+(\d+\.\d+(?:\.\d+)?)", command):
                parts = tuple(map(int, value.split(".")))
                versions.append(parts + (0,) * (3 - len(parts)))
    return versions


def verify_platform(app: Path) -> None:
    with (app / "Contents/Info.plist").open("rb") as stream:
        version = plistlib.load(stream)["LSMinimumSystemVersion"]
    declared = tuple(map(int, version.split(".")))
    declared += (0,) * (3 - len(declared))
    for path in macho_files(app):
        if "arm64" not in run("lipo", "-archs", str(path)).split():
            raise ValueError(f"Runtime binary lacks Apple Silicon support: {path.name}")
        versions = minimum_versions(run("otool", "-l", "-arch", "arm64", str(path)))
        if not versions or max(versions) > declared:
            raise ValueError(
                f"Binary deployment target exceeds declared macOS {version}: {path.name}"
            )
        for line in run("otool", "-L", "-arch", "arm64", str(path)).splitlines()[1:]:
            dependency = line.strip().split(" (", 1)[0]
            if dependency.startswith("/") and not dependency.startswith(
                ("/System/Library/", "/usr/lib/")
            ):
                raise ValueError(
                    f"Non-system absolute dylib dependency: {path.name}: {dependency}"
                )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=[
            "preflight",
            "sign-runtime",
            "verify-platform",
            "verify-app",
            "verify-dmg",
            "notarize",
            "source-template",
            "verify-sources",
            "verify-hobby",
            "verify-hobby-app",
        ],
    )
    parser.add_argument("path", type=Path, nargs="?")
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--revision")
    args = parser.parse_args()
    try:
        if args.action == "preflight":
            preflight()
        elif args.path is None:
            raise ValueError("This action requires a path")
        elif args.action == "sign-runtime":
            sign_runtime(args.path)
        elif args.action == "verify-platform":
            verify_platform(args.path)
        elif args.action == "verify-hobby":
            verify_hobby(args.path)
        elif args.action == "verify-hobby-app":
            verify_hobby_app(args.path)
        elif args.action == "notarize":
            profile = os.environ.get("YOMIMADO_NOTARY_PROFILE")
            if not profile:
                raise ValueError("Set YOMIMADO_NOTARY_PROFILE")
            response = json.loads(
                run(
                    "xcrun",
                    "notarytool",
                    "submit",
                    str(args.path),
                    "--keychain-profile",
                    profile,
                    "--wait",
                    "--output-format",
                    "json",
                )
            )
            report = {"id": response.get("id"), "status": response.get("status")}
            args.path.with_name(args.path.name + ".notarization.json").write_text(
                json.dumps(report, indent=2) + "\n"
            )
            if report["status"] != "Accepted":
                raise ValueError(
                    "Apple did not accept notarization; inspect the submission log locally"
                )
        elif args.action == "verify-app":
            verify_platform(args.path)
            verify_signature(args.path)
            for path in macho_files(args.path):
                verify_signature(path)
            run("codesign", "--verify", "--deep", "--strict", str(args.path))
            run("xcrun", "stapler", "validate", str(args.path))
            run("spctl", "--assess", "--type", "execute", "--verbose=4", str(args.path))
        elif args.action == "verify-dmg":
            verify_signature(args.path, executable=False)
            run("xcrun", "stapler", "validate", str(args.path))
            run(
                "spctl",
                "--assess",
                "--type",
                "open",
                "--context",
                "context:primary-signature",
                "--verbose=4",
                str(args.path),
            )
        elif args.action == "verify-sources":
            if args.source_dir is None or args.revision is None:
                raise ValueError(
                    "Source verification needs --source-dir and --revision"
                )
            verify_sources(args.path, args.source_dir, args.revision)
        else:
            print(
                json.dumps(
                    {
                        "projectRevision": args.revision,
                        "inventorySha256": inventory(args.path),
                        "reviewer": "",
                        "reviewedAt": "",
                        "buildInstructions": "BUILD.md",
                        "components": [
                            {
                                "id": key,
                                "archive": "",
                                "sha256": "",
                                "licenseEvidence": "",
                                "noticeFiles": notices,
                            }
                            for key, notices in source_items(args.path).items()
                        ],
                    },
                    indent=2,
                )
            )
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as error:
        # Avoid logging subprocess output: a failed credential tool may expose
        # account details. The operator can inspect Keychain/notarytool locally.
        message = (
            f"Command failed: {error.cmd[0]}"
            if isinstance(error, subprocess.CalledProcessError)
            else str(error)
        )
        print(f"FAIL: {message}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
