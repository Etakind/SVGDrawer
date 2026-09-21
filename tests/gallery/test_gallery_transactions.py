"""Functional tests for Gallery transaction, archive, and live-cache behavior."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
import zipfile
from unittest.mock import patch


REPOSITORY = Path(__file__).resolve().parents[2]


class GalleryTransactionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="svgdrawer-transaction-")
        self.root = Path(self.temporary.name)
        self.copy_project(self.root)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @staticmethod
    def copy_project(destination: Path) -> None:
        ignored = shutil.ignore_patterns("__pycache__", ".git", ".conda", ".venv", "tests", "docs", "exports", "index.html")
        shutil.copytree(REPOSITORY, destination, ignore=ignored, dirs_exist_ok=True)

    def run_cli(self, *arguments: str, root: Path | None = None, expected: int = 0) -> dict:
        root = root or self.root
        completed = subprocess.run(
            [sys.executable, "svgdrawer.py", *arguments, "--json"],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=90,
        )
        self.assertEqual(
            completed.returncode,
            expected,
            msg=f"command failed: {arguments}\nstdout={completed.stdout}\nstderr={completed.stderr}",
        )
        if expected:
            return json.loads(completed.stderr)["error"]
        return json.loads(completed.stdout)["data"]

    def write_probe(self, root: Path, ident: str = "probe") -> tuple[Path, Path]:
        script = root / f"{ident}.py"
        spec = root / f"{ident}.json"
        script.write_text(
            "def render(drawing, params):\n"
            "    drawing.rect('probe-body', 32, 32, 192, 192, params['fill'], params['stroke'])\n",
            encoding="utf-8",
        )
        spec.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "id": ident,
                    "version": 1,
                    "name": ident.replace("_", " ").title(),
                    "description": "A transaction probe.",
                    "category": "uncategorized",
                    "style": "probe",
                    "defaults": {},
                    "controls": [],
                }
            ),
            encoding="utf-8",
        )
        return script, spec

    def test_shared_renderer_trash_requires_a_complete_batch(self) -> None:
        chip_spec = json.loads(
            (self.root / "Gallery" / "hardware" / "chip" / "symbol.json").read_text(encoding="utf-8")
        )
        chip_spec.update(
            id="shared_variant",
            name="Shared variant",
            renderer="chip",
            category="hardware",
            style="alternate",
        )
        variant = self.root / "shared_variant.json"
        variant.write_text(json.dumps(chip_spec), encoding="utf-8")
        self.run_cli("--add-symbol", "shared_variant", "--spec", variant)

        error = self.run_cli("--delete-symbol", "chip", expected=3)
        self.assertEqual(error["code"], "conflict")
        listed = self.run_cli("--list-all-flat")["symbols"]
        self.assertEqual({item["id"] for item in listed} & {"chip", "shared_variant"}, {"chip", "shared_variant"})

        deleted = self.run_cli("--delete-symbol", "chip", "shared_variant")
        self.assertEqual(len(deleted["trash_ids"]), 2)

    def test_additive_import_reports_helper_mismatch_without_installing(self) -> None:
        source_project = self.root / "source-project"
        target_project = self.root / "target-project"
        self.copy_project(source_project)
        self.copy_project(target_project)
        script, spec = self.write_probe(source_project, "helper_probe")
        self.run_cli("--add-symbol", "helper_probe", "--script", script, "--spec", spec, root=source_project)
        archive = source_project / "incoming.zip"
        self.run_cli("--backup-gallery", "--output", archive, root=source_project)

        common = target_project / "Gallery" / "common.py"
        common.write_text(common.read_text(encoding="utf-8") + "\n# local helper revision\n", encoding="utf-8")
        result = self.run_cli("--import-gallery", archive, root=target_project)
        self.assertEqual(result["mode"], "additive")
        self.assertFalse((target_project / "Gallery" / "uncategorized" / "helper_probe").exists())
        self.assertTrue(any(item["id"] == "helper_probe" for item in result["conflicts"]))

    def test_additive_import_creates_a_missing_empty_category(self) -> None:
        source_project = self.root / "source-project"
        target_project = self.root / "target-project"
        self.copy_project(source_project)
        self.copy_project(target_project)
        self.run_cli("--add-category", "incoming", "--name", "Incoming", root=source_project)
        archive = source_project / "incoming.zip"
        self.run_cli("--backup-gallery", "--output", archive, root=source_project)

        result = self.run_cli("--import-gallery", archive, root=target_project)
        self.assertEqual(result["added_categories"], ["incoming"])
        self.assertIn("incoming", [row["id"] for row in self.run_cli("--list-category", root=target_project)["categories"]])

    def test_invalid_archive_does_not_change_active_gallery(self) -> None:
        invalid = self.root / "invalid.zip"
        invalid.write_bytes(b"not a zip archive")
        before = self.run_cli("--list-all-flat")["symbol_count"]
        error = self.run_cli("--import-gallery", invalid, expected=2)
        self.assertIn("ZIP", error["message"])
        self.assertEqual(self.run_cli("--list-all-flat")["symbol_count"], before)

        unsafe = self.root / "unsafe.zip"
        with zipfile.ZipFile(unsafe, "w") as archive:
            archive.writestr("Gallery/../evil", b"bad")
        error = self.run_cli("--import-gallery", unsafe, expected=2)
        self.assertIn("Unsafe", error["message"])
        self.assertEqual(self.run_cli("--list-all-flat")["symbol_count"], before)

    def test_publication_rolls_back_when_a_later_write_fails(self) -> None:
        import cli.common as common

        catalog = self.root / "Gallery" / "catalog.json"
        settings = self.root / "Gallery" / "settings.json"
        original_catalog = catalog.read_bytes()
        original_settings = settings.read_bytes()
        calls = 0
        real_write = common.atomic_write

        def fail_on_second_write(path, content, overwrite=True):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected publication failure")
            return real_write(path, content, overwrite=overwrite)

        with patch.object(common, "atomic_write", side_effect=fail_on_second_write):
            with self.assertRaises(OSError):
                common.commit_gallery(
                    {catalog: b"changed catalog", settings: b"changed settings"},
                    root=self.root,
                    keep_history=False,
                )
        self.assertEqual(catalog.read_bytes(), original_catalog)
        self.assertEqual(settings.read_bytes(), original_settings)

    def test_force_sync_retains_and_restores_active_snapshot(self) -> None:
        archive = self.root / "baseline.zip"
        self.run_cli("--backup-gallery", "--output", archive)
        self.run_cli("--add-category", "temporary", "--name", "Temporary")
        synced = self.run_cli("--import-gallery", archive, "--force-sync", "--yes")
        self.assertEqual(synced["mode"], "force-sync")
        snapshot_id = synced["snapshot_id"]
        self.assertEqual(self.run_cli("--list-all-flat")["symbol_count"], 57)
        trash = self.run_cli("--list-trash")
        self.assertTrue(any(entry["trash_id"] == snapshot_id and entry["kind"] == "snapshot" for entry in trash["entries"]))

        restored = self.run_cli("--restore", snapshot_id, "--yes")
        self.assertEqual(restored["mode"], "force-sync")
        self.assertEqual(self.run_cli("--list-category")["category_count"], 7)
        trash = self.run_cli("--list-trash")
        self.assertGreaterEqual(sum(entry["kind"] == "snapshot" for entry in trash["entries"]), 2)

    def test_running_server_refreshes_after_cli_source_change(self) -> None:
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            port = listener.getsockname()[1]
        process = subprocess.Popen(
            [sys.executable, "server.py", "--port", str(port), "--no-browser"],
            cwd=self.root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
        )
        try:
            url = f"http://127.0.0.1:{port}"

            def metadata() -> dict:
                with urllib.request.urlopen(url + "/api/gallery", timeout=10) as response:
                    return json.loads(response.read())

            deadline = time.time() + 20
            while True:
                try:
                    self.assertGreaterEqual(len(metadata()["symbols"]), 57)
                    break
                except (OSError, AssertionError):
                    if time.time() >= deadline:
                        output = process.stdout.read() if process.stdout else ""
                        self.fail(f"server did not start: {output}")
                    time.sleep(0.1)

            script, spec = self.write_probe(self.root, "live_probe")
            self.run_cli("--add-symbol", "live_probe", "--script", script, "--spec", spec, root=self.root)
            deadline = time.time() + 10
            while time.time() < deadline:
                if any(symbol["id"] == "live_probe" for symbol in metadata()["symbols"]):
                    break
                time.sleep(0.1)
            else:
                self.fail("running server did not observe the CLI Gallery publication")
        finally:
            process.terminate()
            process.wait(timeout=10)


if __name__ == "__main__":
    unittest.main()
