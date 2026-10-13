"""Version updates preserve dependencies and fail without partial input edits."""

import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))
import update_version as updater


class UpdateVersionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        for name in updater.FILES:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(updater.ROOT / name, target)
        self.current = updater.ci.version(self.root)

    def snapshot(self):
        return {name: (self.root / name).read_bytes() for name in updater.FILES}

    def update(self, version, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            previous = updater.update(version, root=self.root, **kwargs)
        return previous, output.getvalue()

    def test_release_transitions_and_roundtrip_preserve_all_other_bytes(self):
        original = self.snapshot()
        previous = self.current
        for version in (
            "0.2.0",
            "1.0.0-alpha.1",
            "1.0.0-beta.2",
            "1.0.0-rc.3",
            "1.0.0",
        ):
            with self.subTest(version=version):
                old, output = self.update(version)
                self.assertEqual(old, previous)
                self.assertEqual(updater.ci.version(self.root), version)
                self.assertIn("stable" if version == "1.0.0" else "pre-release", output)
                for name, data in original.items():
                    self.assertEqual(
                        updater.ci.normalized(name, data.decode()),
                        updater.ci.normalized(name, (self.root / name).read_text()),
                    )
                previous = version
        self.update(self.current)
        self.assertEqual(self.snapshot(), original)

    def test_dry_run_and_same_version_leave_every_file_unchanged(self):
        original = self.snapshot()
        _, output = self.update("0.2.0", dry_run=True)
        self.assertIn("Would update", output)
        self.assertEqual(self.snapshot(), original)
        self.update(self.current)
        self.assertEqual(self.snapshot(), original)

    def test_matching_dependency_version_is_never_updated(self):
        npm_lock = self.root / "apps/desktop/package-lock.json"
        data = json.loads(npm_lock.read_text())
        data["packages"]["node_modules/synthetic"] = {"version": self.current}
        npm_lock.write_text(json.dumps(data, indent=2) + "\n")
        cargo_lock = self.root / "apps/desktop/src-tauri/Cargo.lock"
        cargo_lock.write_text(
            cargo_lock.read_text()
            + f'\n[[package]]\nname = "yomimado"\nversion = "{self.current}"\nsource = "registry+https://example.invalid/index"\n'
        )
        original = self.snapshot()
        self.update("0.2.0")
        for name, before in original.items():
            self.assertEqual(
                updater.ci.normalized(name, before.decode()),
                updater.ci.normalized(name, (self.root / name).read_text()),
            )
        self.assertEqual(
            json.loads(npm_lock.read_text())["packages"]["node_modules/synthetic"][
                "version"
            ],
            self.current,
        )

    def test_invalid_release_versions_fail_without_edits(self):
        original = self.snapshot()
        for version in (
            "v0.2.0",
            "0.2",
            "01.2.0",
            "1.0.0-beta.01",
            "1.0.0-preview.1",
            "1.0.0+build.1",
        ):
            with self.subTest(version=version), self.assertRaises(ValueError):
                self.update(version)
            self.assertEqual(self.snapshot(), original)

    def test_mismatch_missing_file_and_malformed_last_file_fail_before_writes(self):
        original = self.snapshot()
        cases = (
            (
                "apps/desktop/package.json",
                original["apps/desktop/package.json"].replace(
                    self.current.encode(), b"9.9.9"
                ),
            ),
            ("apps/desktop/src-tauri/Cargo.lock", b"not valid toml"),
            ("apps/desktop/src-tauri/Cargo.lock", None),
        )
        for name, replacement in cases:
            with self.subTest(path=name, replacement=replacement):
                for path, data in original.items():
                    (self.root / path).write_bytes(data)
                path = self.root / name
                if replacement is None:
                    path.unlink()
                else:
                    path.write_bytes(replacement)
                before = {
                    p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()
                }
                with self.assertRaises((ValueError, OSError)):
                    self.update("0.2.0")
                self.assertEqual(
                    {p: p.read_bytes() for p in self.root.rglob("*") if p.is_file()},
                    before,
                )

    def test_unsupported_layout_fails_before_any_file_is_written(self):
        path = self.root / "apps/desktop/src-tauri/Cargo.lock"
        path.write_text(
            path.read_text().replace(
                f'version = "{self.current}"', f"version = '{self.current}'"
            )
        )
        original = self.snapshot()
        with self.assertRaisesRegex(ValueError, "version field"):
            self.update("0.2.0")
        self.assertEqual(self.snapshot(), original)

    def test_windows_crlf_line_endings_survive_update_and_roundtrip(self):
        for name in updater.FILES:
            path = self.root / name
            path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
        original = self.snapshot()
        self.update("0.2.0")
        self.assertEqual(updater.ci.version(self.root), "0.2.0")
        self.update(self.current)
        self.assertEqual(self.snapshot(), original)

    def test_write_failure_restores_earlier_and_partially_written_files(self):
        original = self.snapshot()
        write_bytes = Path.write_bytes
        failing_path = self.root / updater.FILES[-1]
        failed = False

        def write(path, data):
            nonlocal failed
            if path == failing_path and not failed:
                failed = True
                write_bytes(path, b"partial write")
                raise OSError("synthetic disk failure")
            return write_bytes(path, data)

        with (
            patch.object(Path, "write_bytes", write),
            self.assertRaisesRegex(OSError, "disk failure"),
        ):
            self.update("0.2.0")
        self.assertEqual(self.snapshot(), original)

    def test_cli_resolves_repository_from_outside_checkout(self):
        original = {name: (updater.ROOT / name).read_bytes() for name in updater.FILES}
        result = subprocess.run(
            [
                sys.executable,
                updater.ROOT / "scripts/update_version.py",
                "0.2.0",
                "--dry-run",
            ],
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Would update", result.stdout)
        self.assertEqual(
            {name: (updater.ROOT / name).read_bytes() for name in updater.FILES},
            original,
        )


if __name__ == "__main__":
    unittest.main()
