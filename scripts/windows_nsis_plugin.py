"""Stage a short, locked source build of the exact NSIS plugin version."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import tomllib
from windows_release import (
    BUILD,
    RESOURCES,
    ROOT,
    digest,
    fetch,
    pe_info,
    read_json,
    write_json,
)
from windows_sudachi_runtime import extract_original

MANIFEST = ROOT / "docs/windows-nsis-plugin-inputs.json"
LOCK = ROOT / "docs/windows-nsis-plugin-Cargo.lock"
AUDIT = BUILD / "nsis-plugin"
TEMPLATE_LINE = '!define ADDITIONALPLUGINSPATH "{{additional_plugins_path}}"'


def validate(inputs: dict) -> None:
    if digest(LOCK) != inputs["lockSha256"]:
        raise ValueError("NSIS plugin lock differs")
    packages = tomllib.loads(LOCK.read_text())["package"]
    expected = {}
    for package in packages:
        if not package.get("source"):
            continue
        if package["source"] != "registry+https://github.com/rust-lang/crates.io-index":
            raise ValueError("NSIS plugin has an unretained source")
        expected[(package["name"], package["version"])] = package["checksum"]
    actual = {(p["name"], p["version"]): p["sha256"] for p in inputs["crates"]}
    if expected != actual or len(actual) != len(inputs["crates"]):
        raise ValueError("NSIS plugin sources do not cover its exact lock")
    if not inputs["source"]["noticeHashes"] or any(
        not p["noticeHashes"] for p in inputs["crates"]
    ):
        raise ValueError("NSIS plugin is missing original notices")
    if inputs["target"] != "i686-pc-windows-msvc":
        raise ValueError("NSIS plugin must match its 32-bit installer host")


def template(original: str, plugin: Path) -> str:
    # Preserve the upstream installation flow; change only plugin lookup.
    path = plugin.resolve().as_posix()
    if any(c in path for c in '$"\r\n') or original.count(TEMPLATE_LINE) != 1:
        raise ValueError("Unsafe or changed NSIS plugin template input")
    return original.replace(TEMPLATE_LINE, f'!define ADDITIONALPLUGINSPATH "{path}"')


def prepare() -> tuple[dict, Path, Path]:
    inputs = read_json(MANIFEST)
    validate(inputs)
    if AUDIT.exists():
        shutil.rmtree(AUDIT)
    originals = AUDIT / "originals"
    original = originals / inputs["source"]["filename"]
    fetch(inputs["source"], original)
    extract_original(inputs["source"], original, AUDIT / "source", AUDIT / "notices")
    root = AUDIT / "source" / inputs["source"]["prefix"]
    if (root / "Cargo.lock").exists():
        raise ValueError("Upstream NSIS plugin unexpectedly contains a lock")
    shutil.copy2(LOCK, root / "Cargo.lock")
    vendor = AUDIT / "vendor"
    for entry in inputs["crates"]:
        archive = originals / entry["filename"]
        fetch(entry, archive)
        extract_original(entry, archive, vendor, AUDIT / "notices")
        crate = vendor / (entry["name"] + "-" + entry["version"])
        files = {
            p.relative_to(crate).as_posix(): digest(p)
            for p in sorted(crate.rglob("*"))
            if p.is_file() and p.name != ".cargo-checksum.json"
        }
        write_json(
            crate / ".cargo-checksum.json", {"files": files, "package": entry["sha256"]}
        )
    home = AUDIT / "cargo-home"
    home.mkdir()
    (home / "config.toml").write_text(
        '[source.crates-io]\nreplace-with = "retained"\n[source.retained]\ndirectory = '
        + json.dumps(str(vendor.resolve()))
        + "\n"
    )
    fetch(inputs["template"], originals / inputs["template"]["filename"])
    return inputs, root, home


def stage() -> None:
    if sys.platform != "win32":
        raise ValueError("NSIS plugin build requires Windows")
    inputs, root, home = prepare()
    rust = subprocess.check_output(["rustc", "--version", "--verbose"], text=True)
    if f"release: {inputs['rustVersion']}\n" not in rust:
        raise ValueError("NSIS plugin compiler differs")
    cli = read_json(ROOT / "apps/desktop/node_modules/@tauri-apps/cli/package.json")
    if cli["version"] != inputs["cliVersion"]:
        raise ValueError("NSIS template differs from installed Tauri CLI")
    subprocess.run(
        ["rustup", "target", "add", inputs["target"]], check=True, timeout=120
    )
    vc = Path(os.environ["VCToolsInstallDir"])
    sdk = Path(os.environ["WindowsSdkDir"])
    sdk_version = os.environ["WindowsSDKVersion"].rstrip("\\/")
    libs = [
        vc / "lib/x86",
        sdk / "Lib" / sdk_version / "ucrt/x86",
        sdk / "Lib" / sdk_version / "um/x86",
    ]
    linker = vc / "bin/HostX64/x86/link.exe"
    if not linker.is_file() or not all(p.is_dir() for p in libs):
        raise ValueError("Pinned x86 installer toolchain is unavailable")
    link_script = AUDIT / "link-x86.cmd"
    link_script.write_text(
        '@set "LIB='
        + ";".join(str(p.resolve()) for p in libs)
        + '"\n@"'
        + str(linker.resolve())
        + '" %*\n'
    )
    env = {
        **os.environ,
        "CARGO_HOME": str(home.resolve()),
        "CARGO_TARGET_DIR": str((AUDIT / "target").resolve()),
        "CARGO_TARGET_I686_PC_WINDOWS_MSVC_LINKER": str(link_script.resolve()),
        "CARGO_TARGET_I686_PC_WINDOWS_MSVC_RUSTFLAGS": "-C target-feature=+crt-static",
    }
    commands = []
    for operation, extra in (
        ("test", ["--workspace", "--features", "test"]),
        ("build", ["--package", "nsis-tauri-utils"]),
    ):
        command = [
            "cargo",
            operation,
            "--offline",
            "--locked",
            "--release",
            "--target",
            inputs["target"],
            "--manifest-path",
            str(root / "Cargo.toml"),
            *extra,
        ]
        log = AUDIT / (operation + ".log")
        with log.open("w") as stream:
            subprocess.run(
                command,
                cwd=root,
                env=env,
                stdout=stream,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=300,
            )
        commands.append({"command": command, "logSha256": digest(log)})
    built = AUDIT / "target" / inputs["target"] / "release/nsis_tauri_utils.dll"
    info = pe_info(built)
    if info["machine"] != "0x14c" or any(
        "vcruntime" in p or "msvcp" in p for p in info["imports"]
    ):
        raise ValueError("NSIS plugin architecture or static CRT mode differs")
    generated = AUDIT / "installer.nsi"
    original = AUDIT / "originals" / inputs["template"]["filename"]
    generated.write_bytes(template(original.read_text(), built.parent).encode())
    record = {
        "passed": True,
        "nativeSha256": digest(built),
        "manifestSha256": digest(MANIFEST),
        "lockSha256": digest(LOCK),
        "recipeSha256": digest(Path(__file__)),
        "templateSha256": digest(generated),
        "originalTemplateSha256": digest(original),
        "rustc": rust,
        "msvc": os.environ["VCToolsVersion"],
        "sdk": sdk_version,
        "commands": commands,
        **info,
        "publicDistributionApproved": False,
    }
    write_json(AUDIT / "build-verification.json", record)
    destination = BUILD / "sources/source-built-nsis-plugin"
    notices = RESOURCES / "notices/source-built-nsis-plugin"
    shutil.copytree(AUDIT / "originals", destination / "originals", dirs_exist_ok=True)
    shutil.copytree(AUDIT / "notices", notices, dirs_exist_ok=True)
    for path in (
        MANIFEST,
        LOCK,
        Path(__file__),
        AUDIT / "build-verification.json",
        AUDIT / "build.log",
        AUDIT / "test.log",
        link_script,
        generated,
    ):
        for directory in (destination, notices):
            directory.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, directory / path.name)
    print(
        "Locked NSIS plugin built and tested; exact installer verification remains required",
        flush=True,
    )


def verify(installed: Path, installer: Path) -> dict:
    record = read_json(
        installed / "ocr/notices/source-built-nsis-plugin/build-verification.json"
    )
    built = AUDIT / "target/i686-pc-windows-msvc/release/nsis_tauri_utils.dll"
    generated = AUDIT / "installer.nsi"
    if (
        not record["passed"]
        or record["manifestSha256"] != digest(MANIFEST)
        or record["lockSha256"] != digest(LOCK)
        or record["recipeSha256"] != digest(Path(__file__))
        or record["nativeSha256"] != digest(built)
        or record["templateSha256"] != digest(generated)
    ):
        raise ValueError("Unbound NSIS plugin build inputs")
    # The exact template is used by this Windows-only configuration. The stock
    # plugin may remain in Tauri's tool cache, but it is outside this search path.
    configuration = read_json(
        ROOT / "apps/desktop/src-tauri/tauri.windows-release.conf.json"
    )
    expected = "../../../services/ocr/build/windows/nsis-plugin/installer.nsi"
    if configuration["bundle"]["windows"]["nsis"].get("template") != expected:
        raise ValueError("Installer does not select the retained NSIS template")
    original = AUDIT / "originals" / read_json(MANIFEST)["template"]["filename"]
    if digest(original) != record[
        "originalTemplateSha256"
    ] or generated.read_text() != template(original.read_text(), built.parent):
        raise ValueError("Installer plugin lookup changed")
    rendered = (
        ROOT
        / "apps/desktop/src-tauri/target/x86_64-pc-windows-msvc/release/nsis/x64/installer.nsi"
    )
    expected_line = (
        f'!define ADDITIONALPLUGINSPATH "{built.parent.resolve().as_posix()}"'
    )
    if rendered.read_text(encoding="utf-8-sig").count(expected_line) != 1:
        raise ValueError("Rendered installer does not select the source-built plugin")
    extracted = AUDIT / "embedded"
    if extracted.exists():
        shutil.rmtree(extracted)
    subprocess.run(
        [
            "7z",
            "x",
            str(installer.resolve()),
            "*nsis_tauri_utils.dll",
            "-r",
            "-y",
            "-o" + str(extracted.resolve()),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        timeout=120,
    )
    plugins = list(extracted.rglob("nsis_tauri_utils.dll"))
    if not plugins or any(digest(p) != record["nativeSha256"] for p in plugins):
        raise ValueError("Embedded NSIS plugin differs from its source build")
    return {
        **record,
        "installerSha256": digest(installer),
        "renderedTemplateSha256": digest(rendered),
        "embeddedPluginVerified": True,
        "embeddedCopies": len(plugins),
    }


if __name__ == "__main__":
    stage()
