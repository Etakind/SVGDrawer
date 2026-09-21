"""Behavior checks for the custom static icons needed by the figure."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
DRAFTS = ROOT.parent / "pic" / "SVGDrawerOutputs"
ICON_IDS = (
    "cloud",
    "enterprise",
    "graduate_cap",
    "research_flask",
    "trophy",
    "checklist",
    "bar_chart",
    "vivado_symbol",
    "vitis_symbol",
    "icarus_symbol",
    "git_symbol",
    "feedback_cycle",
    "person_computer",
    "curve_arrow",
)


class GalleryIconTests(unittest.TestCase):
    def run_cli(self, *args: str) -> dict:
        command = [sys.executable, "-B", str(ROOT / "svgdrawer.py"), *args, "--json"]
        result = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=45,
        )
        self.assertEqual(result.returncode, 0, (command, result.stdout, result.stderr))
        self.assertEqual(result.stderr, "")
        response = json.loads(result.stdout)
        self.assertTrue(response["ok"])
        return response["data"]

    def skip_if_unregistered(self, icon_id: str) -> None:
        listed = self.run_cli("--list-all-flat")
        actual_ids = {symbol["id"] for symbol in listed["symbols"]}
        if icon_id not in actual_ids:
            self.skipTest(f"{icon_id} is awaiting Gallery registration")

    def write_svg(self, output_dir: Path, icon_id: str, suffix: str, *args: str) -> str:
        output = output_dir / f"{icon_id}-{suffix}.svg"
        self.run_cli("--create", icon_id, *args, "--output", str(output))
        return output.read_text(encoding="utf-8")

    @staticmethod
    def drawing_shapes(svg: str) -> list[ET.Element]:
        root = ET.fromstring(svg)
        drawing = next(child for child in root if child.tag.endswith("svg"))
        return list(drawing)

    def test_icon_drafts_pass_add_symbol_dry_run(self):
        for icon_id in ICON_IDS:
            with self.subTest(icon_id=icon_id):
                draft = DRAFTS / f"{icon_id}.py"
                self.assertTrue(draft.is_file(), draft)
                data = self.run_cli(
                    "--add-symbol",
                    icon_id,
                    "--script",
                    str(draft),
                    "--force",
                    "--dry-run",
                )
                self.assertTrue(data["dry_run"])
                self.assertEqual(data["id"], icon_id)
                self.assertGreaterEqual(data["validation"]["symbols"][0]["cases"], 3)

    def test_registered_icons_are_discoverable_and_export_clean_svg(self):
        listed = self.run_cli("--list-all-flat")
        actual_ids = {symbol["id"] for symbol in listed["symbols"]}
        missing = set(ICON_IDS) - actual_ids
        self.assertFalse(missing, f"custom icons are not registered: {sorted(missing)}")

        with tempfile.TemporaryDirectory(prefix="svgdrawer-icons-") as temp:
            output_dir = Path(temp)
            for icon_id in ICON_IDS:
                with self.subTest(icon_id=icon_id):
                    first = output_dir / f"{icon_id}-first.svg"
                    second = output_dir / f"{icon_id}-second.svg"
                    self.run_cli("--create", icon_id, "--output", str(first))
                    self.run_cli("--create", icon_id, "--output", str(second))
                    first_svg = first.read_text(encoding="utf-8")
                    second_svg = second.read_text(encoding="utf-8")
                    self.assertEqual(first_svg, second_svg)
                    root = ET.fromstring(first_svg)
                    self.assertTrue(root.tag.endswith("svg"))
                    self.assertNotIn("<image", first_svg.lower())
                    self.assertNotIn("data:image", first_svg.lower())
                    self.assertNotIn("<script", first_svg.lower())

    def test_person_computer_variants_keep_the_same_computer(self):
        self.skip_if_unregistered("person_computer")
        colors = ("2878B5", "F2C94C", "E53935")
        with tempfile.TemporaryDirectory(prefix="svgdrawer-person-computer-") as temp:
            output_dir = Path(temp)
            variants = [
                self.drawing_shapes(
                    self.write_svg(output_dir, "person_computer", color, "--set", f"fill={color}")
                )
                for color in colors
            ]
            computer_parts = [
                [ET.tostring(shape, encoding="unicode") for shape in shapes[2:]]
                for shapes in variants
            ]
            self.assertEqual(computer_parts[0], computer_parts[1])
            self.assertEqual(computer_parts[0], computer_parts[2])
            head_and_body_colors = [
                [shape.attrib["fill"] for shape in shapes[:2]] for shapes in variants
            ]
            self.assertEqual(head_and_body_colors, [[f"#{color}", f"#{color}"] for color in colors])
            repeated = self.write_svg(output_dir, "person_computer", "repeat", "--set", "fill=2878B5")
            self.assertEqual(repeated, (output_dir / "person_computer-2878B5.svg").read_text(encoding="utf-8"))

    def test_curve_arrow_controls_change_path_geometry(self):
        self.skip_if_unregistered("curve_arrow")
        with tempfile.TemporaryDirectory(prefix="svgdrawer-curve-arrow-") as temp:
            output_dir = Path(temp)
            base = self.drawing_shapes(self.write_svg(output_dir, "curve_arrow", "base"))
            base_paths = tuple(shape.attrib.get("d") for shape in base)
            self.assertEqual(
                self.write_svg(output_dir, "curve_arrow", "repeat"),
                (output_dir / "curve_arrow-base.svg").read_text(encoding="utf-8"),
            )
            for control, value in (
                ("length", "60"),
                ("bend", "-65"),
                ("head_length", "10"),
                ("head_width", "34"),
                ("angle", "90"),
            ):
                with self.subTest(control=control):
                    changed = self.drawing_shapes(
                        self.write_svg(output_dir, "curve_arrow", control, "--set", f"{control}={value}")
                    )
                    changed_paths = tuple(shape.attrib.get("d") for shape in changed)
                    self.assertNotEqual(base_paths, changed_paths)


if __name__ == "__main__":
    unittest.main()
