"""Behavioral RED tests for the shared Gallery command surface.

The test process copies the product into a temporary workspace so destructive
Gallery operations never touch the checkout used by the tester or implementer.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


REPOSITORY = Path(__file__).resolve().parents[2]


class SharedGalleryCliContractTests(unittest.TestCase):
    """The documented management capabilities must be available through CLI."""

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="svgdrawer-cli-")
        self.root = Path(self.temporary.name)
        for name in ("Gallery", "engine", "cli", "app"):
            shutil.copytree(REPOSITORY / name, self.root / name)
        for name in ("svgdrawer.py", "server.py"):
            shutil.copy2(REPOSITORY / name, self.root / name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def run_cli(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, "svgdrawer.py", *arguments],
            cwd=self.root,
            text=True,
            capture_output=True,
            encoding="utf-8",
            check=False,
        )

    def json_result(self, *arguments: str) -> dict:
        completed = self.run_cli(*arguments, "--json")
        self.assertEqual(
            completed.returncode,
            0,
            msg=f"command failed: {arguments}\nstdout={completed.stdout}\nstderr={completed.stderr}",
        )
        return json.loads(completed.stdout)

    def test_discovery_reports_customizable_capability(self) -> None:
        result = self.json_result("--list-all-flat")
        self.assertEqual(result["schema_version"], 2)
        self.assertGreaterEqual(result["data"]["symbol_count"], 33)
        self.assertTrue(all("customizable" in symbol for symbol in result["data"]["symbols"]))

    def test_symbol_favorite_is_a_shared_gallery_setting(self) -> None:
        favorited = self.json_result("--update-symbol", "circle", "--favorite")
        self.assertTrue(favorited["data"]["symbol"]["favorite"])
        listed = {symbol["id"]: symbol for symbol in self.json_result("--list-all-flat")["data"]["symbols"]}
        self.assertTrue(listed["circle"]["favorite"])
        unfavorited = self.json_result("--update-symbol", "circle", "--unfavorite")
        self.assertFalse(unfavorited["data"]["symbol"]["favorite"])

    def test_static_svg_import_is_additive_and_noncustomizable(self) -> None:
        source = self.root / "import.svg"
        source.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">'
            '<rect id="box" width="20" height="20" fill="#123456"/></svg>',
            encoding="utf-8",
        )
        result = self.json_result(
            "--import-svg",
            str(source),
            "--id",
            "imported-box",
            "--name",
            "Imported box",
            "--category",
            "uncategorized",
        )
        self.assertEqual(result["data"]["symbol"]["kind"], "svg")
        self.assertFalse(result["data"]["symbol"]["customizable"])
        listed = self.json_result("--list-all-flat")["data"]["symbols"]
        self.assertEqual(sum(symbol["name"] == "Imported box" for symbol in listed), 1)
        parts = self.json_result("--list-parts", "imported-box")["data"]["parts"]
        self.assertEqual([part["id"] for part in parts], ["imported-part-1"])
        output = self.root / "imported-box.svg"
        self.json_result(
            "--create",
            "imported-box",
            "--parts",
            '{"imported-part-1":{"fill":"ff0000","hidden":true}}',
            "--output",
            str(output),
        )
        rendered = output.read_text(encoding="utf-8")
        self.assertIn('fill="#FF0000"', rendered)
        self.assertIn('visibility="hidden"', rendered)
        self.assertNotIn("data-part", rendered)

    def test_variant_update_move_and_batch_trash_restore(self) -> None:
        recipe = self.root / "variant.asset.json"
        recipe.write_text(
            json.dumps(
                {
                    "format": "svgdrawer.asset",
                    "schema_version": 1,
                    "name": "Saved circle",
                    "asset": {"type": "circle", "params": {}},
                    "output": {"width": 128, "height": 128},
                }
            ),
            encoding="utf-8",
        )
        saved = self.json_result(
            "--save-symbol",
            "saved-circle",
            "--recipe",
            str(recipe),
            "--name",
            "Saved circle",
            "--category",
            "uncategorized",
        )
        self.assertEqual(saved["data"]["symbol"]["id"], "saved-circle")

        updated = self.json_result(
            "--update-symbol",
            "saved-circle",
            "--description",
            "Updated description",
            "--tags",
            "saved,variant",
            "--style",
            "custom",
        )
        self.assertEqual(updated["data"]["symbol"]["description"], "Updated description")
        self.assertEqual(updated["data"]["symbol"]["tags"], ["saved", "variant"])

        moved = self.json_result("--move-symbol", "saved-circle", "--category", "documents")
        self.assertEqual(moved["data"]["category"], "documents")

        trashed = self.json_result("--delete-symbol", "circle", "saved-circle")
        self.assertEqual(len(trashed["data"]["trash_ids"]), 2)
        trash = self.json_result("--list-trash")
        self.assertEqual(trash["data"]["entry_count"], 2)
        restored = self.json_result("--restore", *trashed["data"]["trash_ids"])
        self.assertEqual(restored["data"]["restored"], trashed["data"]["trash_ids"])

    def test_category_delete_requires_an_explicit_contents_choice(self) -> None:
        missing_choice = self.run_cli("--delete-category", "basics", "--json")
        self.assertNotEqual(missing_choice.returncode, 0)
        self.assertEqual(json.loads(missing_choice.stderr)["error"]["code"], "invalid_input")

        moved = self.json_result(
            "--delete-category",
            "basics",
            "--contents",
            "uncategorized",
        )
        self.assertEqual(moved["data"]["category"], "basics")
        moved_ids = set(moved["data"]["symbol_ids"])
        self.assertTrue(moved_ids)
        listed = {symbol["id"]: symbol for symbol in self.json_result("--list-all-flat")["data"]["symbols"]}
        self.assertTrue(all(listed[ident]["category"] == "uncategorized" for ident in moved_ids))

    def test_backup_import_and_confirmed_force_sync_contract(self) -> None:
        archive = self.root / "gallery-backup.zip"
        backup = self.json_result("--backup-gallery", "--output", str(archive))
        self.assertTrue(archive.is_file())
        self.assertEqual(backup["data"]["file"], str(archive))

        preview = self.json_result("--import-gallery", str(archive), "--dry-run")
        self.assertEqual(preview["data"]["mode"], "additive")

        denied = self.run_cli("--import-gallery", str(archive), "--force-sync", "--json")
        self.assertNotEqual(denied.returncode, 0)
        self.assertEqual(json.loads(denied.stderr)["error"]["code"], "confirmation_required")

        synced = self.json_result("--import-gallery", str(archive), "--force-sync", "--yes")
        self.assertEqual(synced["data"]["mode"], "force-sync")
        self.assertTrue(synced["data"]["snapshot_id"].startswith("trash-"))

    def test_permanent_removal_requires_confirmation(self) -> None:
        archive = self.root / "gallery-backup.zip"
        self.json_result("--backup-gallery", "--output", str(archive))
        trashed = self.json_result("--delete-symbol", "circle")
        denied = self.run_cli("--purge", *trashed["data"]["trash_ids"], "--json")
        self.assertNotEqual(denied.returncode, 0)
        self.assertEqual(json.loads(denied.stderr)["error"]["code"], "confirmation_required")
        purged = self.json_result("--purge", *trashed["data"]["trash_ids"], "--yes")
        self.assertEqual(len(purged["data"]["purged"]), len(trashed["data"]["trash_ids"]))


if __name__ == "__main__":
    unittest.main()
