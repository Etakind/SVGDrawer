"""Behavioral coverage for the symbol Gallery migration.

The tests deliberately exercise the public CLI and the file-backed Gallery.
The temporary projects used by source-registration checks keep the real
Gallery immutable while still running the same validation and write paths.
"""

from __future__ import annotations

import copy
import difflib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
BASELINE = Path(os.environ.get("SVGDRAWER_BASELINE", Path(tempfile.gettempdir()) / "svgdrawer-baseline-current"))
sys.path.insert(0, str(ROOT))

from engine.gallery import Gallery, validate_spec
from engine.service import handle_request, validate_library


class SymbolMigrationTests(unittest.TestCase):
    """The source Gallery and machine-facing CLI use the symbol contract."""

    def run_cli(self, *arguments: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, "-B", str(cwd / "svgdrawer.py"), *arguments]
        if "--json" not in arguments:
            command.append("--json")
        return subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=90)

    def successful_data(self, *arguments: str, cwd: Path = ROOT) -> dict:
        result = self.run_cli(*arguments, cwd=cwd)
        self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))
        self.assertEqual(result.stderr, "")
        envelope = json.loads(result.stdout)
        self.assertEqual(envelope["schema_version"], 2)
        self.assertTrue(envelope["ok"], envelope)
        return envelope["data"]

    def copy_registration_project(self, destination: Path) -> None:
        for name in ("Gallery", "engine", "cli"):
            shutil.copytree(ROOT / name, destination / name, ignore=shutil.ignore_patterns("__pycache__"))
        for name in ("svgdrawer.py", "build.py"):
            shutil.copy2(ROOT / name, destination / name)

    def test_catalog_is_authoritative_and_sources_are_nested(self) -> None:
        catalog_path = ROOT / "Gallery" / "catalog.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        self.assertIsInstance(catalog.get("categories"), list)
        symbols = catalog["symbols"]
        self.assertEqual(len(symbols), 33)
        self.assertTrue((ROOT / "Gallery" / "uncategorized").is_dir())
        self.assertFalse((ROOT / "Gallery" / "elements").exists())
        self.assertFalse((ROOT / "Gallery" / "renderers").exists())
        self.assertFalse((ROOT / "Gallery" / "categories.json").exists())

        identities = {"id", "name", "category", "style"}
        seen_names: set[str] = set()
        rows_by_id = {row["id"]: row for row in symbols}
        self.assertEqual(len(rows_by_id), len(symbols))
        for row in symbols:
            self.assertEqual(set(row), identities)
            self.assertEqual(row["style"], "default")
            name = row["name"].strip()
            self.assertEqual(name, row["name"])
            self.assertNotIn(name.casefold(), seen_names)
            seen_names.add(name.casefold())
            source_dir = ROOT / "Gallery" / row["category"] / row["id"]
            self.assertTrue((source_dir / "symbol.json").is_file(), source_dir)
            self.assertTrue((source_dir / "render.py").is_file(), source_dir)
            config = json.loads((source_dir / "symbol.json").read_text(encoding="utf-8"))
            self.assertTrue(identities.isdisjoint(config), (row["id"], config))
            owner = config.get("renderer", row["id"])
            owner_row = rows_by_id[owner]
            self.assertTrue(
                (ROOT / "Gallery" / owner_row["category"] / owner / "render.py").is_file(),
                owner,
            )

    def test_discovery_is_lazy_and_does_not_import_renderers(self) -> None:
        script = """
import importlib
from engine.gallery import Gallery
module = importlib.import_module('engine.gallery')
real_import = module.importlib.import_module
def reject_renderer(name, *args, **kwargs):
    if name.startswith('Gallery.') and name.count('.') >= 2:
        raise AssertionError('renderer imported during discovery: ' + name)
    return real_import(name, *args, **kwargs)
module.importlib.import_module = reject_renderer
gallery = Gallery()
assert len(gallery.symbols) == 33
"""
        result = subprocess.run(
            [sys.executable, "-B", "-c", script],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, (result.stdout, result.stderr))

    def test_gallery_rejects_duplicate_trimmed_casefold_names(self) -> None:
        with tempfile.TemporaryDirectory(prefix="svgdrawer-duplicate-name-") as temporary:
            root = Path(temporary)
            shutil.copytree(ROOT / "Gallery", root / "Gallery", ignore=shutil.ignore_patterns("__pycache__"))
            catalog_path = root / "Gallery" / "catalog.json"
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            catalog["symbols"][1]["name"] = "  " + catalog["symbols"][0]["name"].upper() + "  "
            catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate"):
                Gallery(root, check_lock=False)

    def test_gallery_rejects_missing_definition_and_renderer(self) -> None:
        with tempfile.TemporaryDirectory(prefix="svgdrawer-missing-source-") as temporary:
            root = Path(temporary)
            shutil.copytree(ROOT / "Gallery", root / "Gallery", ignore=shutil.ignore_patterns("__pycache__"))
            (root / "Gallery" / "hardware" / "chip" / "symbol.json").unlink()
            with self.assertRaises(ValueError):
                Gallery(root, check_lock=False)

        with tempfile.TemporaryDirectory(prefix="svgdrawer-missing-renderer-") as temporary:
            root = Path(temporary)
            shutil.copytree(ROOT / "Gallery", root / "Gallery", ignore=shutil.ignore_patterns("__pycache__"))
            (root / "Gallery" / "hardware" / "chip" / "render.py").unlink()
            with self.assertRaisesRegex(ValueError, "renderer"):
                Gallery(root, check_lock=False)

    def test_missing_category_and_style_use_declared_defaults(self) -> None:
        spec = {
            "schema_version": 1,
            "id": "sample",
            "version": 1,
            "name": "Sample",
            "description": "A sample symbol.",
            "defaults": {},
            "controls": [],
        }
        resolved = validate_spec(spec, {"uncategorized"})
        self.assertEqual(resolved["category"], "uncategorized")
        self.assertEqual(resolved["style"], "default")
        self.assertEqual(resolved["renderer"], "sample")

    def test_cli_schema_two_and_old_management_flags_are_rejected(self) -> None:
        listed = self.successful_data("--list-all-flat")
        self.assertEqual(listed["symbol_count"], 33)
        self.assertNotIn("elements", listed)
        self.assertTrue(all("style" in symbol for symbol in listed["symbols"]))

        described = self.successful_data("--describe", "chip")
        self.assertIn("symbol", described)
        self.assertNotIn("element", described)
        self.assertIn("Gallery/hardware/chip/symbol.json", described["source"]["definition"])
        self.assertIn("Gallery/hardware/chip/render.py", described["source"]["renderer"])

        for old_flag in ("--add-element", "--init-element"):
            result = self.run_cli(old_flag, "sample")
            self.assertNotEqual(result.returncode, 0, old_flag)

    def test_default_renders_and_part_ids_match_captured_baseline(self) -> None:
        manifest_path = BASELINE / "baseline-manifest.json"
        if not manifest_path.is_file():
            self.skipTest(f"baseline not found: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(manifest["element_count"], 33)
        for symbol_id in manifest["ids"]:
            with self.subTest(symbol_id=symbol_id):
                expected = (BASELINE / f"{symbol_id}.svg").read_text(encoding="utf-8")
                actual = handle_request({"asset": {"type": symbol_id}})["svg"]
                if expected != actual:
                    diff = "".join(difflib.unified_diff(expected.splitlines(True), actual.splitlines(True)))
                    self.fail(diff[:3000])
                parts = self.successful_data("--list-parts", symbol_id)["parts"]
                actual_ids = [part["id"] for part in parts]
                self.assertEqual(actual_ids, manifest["symbols"][symbol_id]["part_ids"])

    def test_library_schema_one_and_vector_foundry_convert_to_schema_two(self) -> None:
        library = {
            "format": "svgdrawer.library",
            "schema_version": 1,
            "categories": [{"id": "science", "name": "Science"}],
            "elements": [
                {
                    "id": "old-chip",
                    "name": "Old chip",
                    "category": "science",
                    "asset": {"type": "chip", "params": {"pins": 9}, "parts": {}},
                    "tags": ["legacy"],
                }
            ],
            "favorites": ["old-chip"],
        }
        original = copy.deepcopy(library)
        converted = validate_library(library)
        self.assertEqual(library, original)
        self.assertEqual(converted["schema_version"], 2)
        self.assertIn("symbols", converted)
        self.assertNotIn("elements", converted)
        self.assertEqual(converted["symbols"][0]["asset"]["params"]["pins"], 9)
        self.assertEqual(converted["favorites"], ["old-chip"])

        legacy_format = dict(original, format="vector-foundry.library")
        self.assertEqual(validate_library(legacy_format)["schema_version"], 2)
        with self.assertRaises(ValueError):
            validate_library({"format": "svgdrawer.library", "schema_version": 2, "elements": []})

    def test_browser_storage_uses_v2_and_preserves_legacy_read_keys(self) -> None:
        app = (ROOT / "app" / "app.js").read_text(encoding="utf-8")
        init = (ROOT / "app" / "init.js").read_text(encoding="utf-8")
        self.assertIn("svgdrawer.gallery.v2", app)
        self.assertIn("schema_version:2", app)
        self.assertIn("svgdrawer.gallery.v1", init)
        self.assertIn("vector-foundry.catalog.v1", init)
        self.assertIn("validate_library", init)


class RegistrationMigrationTests(unittest.TestCase):
    """Source writes keep catalog/config/renderer ownership consistent."""

    def run_cli(self, root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        command = [sys.executable, "-B", str(root / "svgdrawer.py"), *arguments, "--json"]
        return subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=90)

    @staticmethod
    def write_symbol_source(root: Path, symbol_id: str, body: str) -> tuple[Path, Path]:
        script = root / f"{symbol_id}.py"
        spec = root / f"{symbol_id}.json"
        script.write_text(
            "def render(drawing, params):\n" + body + "\n",
            encoding="utf-8",
        )
        spec.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "id": symbol_id,
                    "version": 1,
                    "name": symbol_id.replace("_", " ").title(),
                    "description": "A registration test symbol.",
                    "category": "uncategorized",
                    "style": "prototype",
                    "defaults": {},
                    "controls": [],
                }
            ),
            encoding="utf-8",
        )
        return script, spec

    def test_dry_run_replacement_and_shared_renderer_owner(self) -> None:
        with tempfile.TemporaryDirectory(prefix="svgdrawer-registration-") as temporary:
            root = Path(temporary)
            self.addCleanup(shutil.rmtree, root, ignore_errors=True)
            SymbolMigrationTests().copy_registration_project(root)
            source, spec = self.write_symbol_source(root, "prototype", "    drawing.rect('body', 30, 30, 196, 196)")
            catalog_before = (root / "Gallery" / "catalog.json").read_bytes()

            dry_run = self.run_cli(
                root,
                "--add-symbol",
                "prototype",
                "--script",
                str(source),
                "--spec",
                str(spec),
                "--dry-run",
            )
            self.assertEqual(dry_run.returncode, 0, (dry_run.stdout, dry_run.stderr))
            self.assertFalse((root / "Gallery" / "uncategorized" / "prototype").exists())
            self.assertEqual((root / "Gallery" / "catalog.json").read_bytes(), catalog_before)

            installed = self.run_cli(root, "--add-symbol", "prototype", "--script", str(source), "--spec", str(spec))
            self.assertEqual(installed.returncode, 0, (installed.stdout, installed.stderr))
            target = root / "Gallery" / "uncategorized" / "prototype"
            self.assertTrue((target / "render.py").is_file())
            config = json.loads((target / "symbol.json").read_text(encoding="utf-8"))
            self.assertNotIn("id", config)
            catalog = json.loads((root / "Gallery" / "catalog.json").read_text(encoding="utf-8"))
            row = next(symbol for symbol in catalog["symbols"] if symbol["id"] == "prototype")
            self.assertEqual(row["style"], "prototype")

            conflict = self.run_cli(root, "--add-symbol", "prototype", "--script", str(source), "--spec", str(spec))
            self.assertNotEqual(conflict.returncode, 0)

            variant_spec = root / "variant.json"
            variant_spec.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "id": "prototype_variant",
                        "version": 1,
                        "name": "Prototype variant",
                        "description": "A shared renderer variant.",
                        "category": "uncategorized",
                        "style": "alternate",
                        "renderer": "prototype",
                        "defaults": {},
                        "controls": [],
                    }
                ),
                encoding="utf-8",
            )
            shared = self.run_cli(root, "--add-symbol", "prototype_variant", "--spec", str(variant_spec))
            self.assertEqual(shared.returncode, 0, (shared.stdout, shared.stderr))
            variant_dir = root / "Gallery" / "uncategorized" / "prototype_variant"
            self.assertFalse((variant_dir / "render.py").exists())
            variant_config = json.loads((variant_dir / "symbol.json").read_text(encoding="utf-8"))
            self.assertEqual(variant_config["renderer"], "prototype")

            replacement_source, replacement_spec = self.write_symbol_source(
                root,
                "prototype",
                "    drawing.rect('body', 20, 20, 216, 216)",
            )
            shared_replacement = self.run_cli(
                root,
                "--add-symbol",
                "prototype",
                "--script",
                str(replacement_source),
                "--spec",
                str(replacement_spec),
                "--force",
            )
            self.assertNotEqual(shared_replacement.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
