"""Runtime, launcher, and licensed static-icon behavior checks."""

from __future__ import annotations

import json
from pathlib import Path
import re
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_SYMBOL_COUNT = 57
EXPECTED_STATIC_COUNT = 24


class RuntimeAndIconProvenanceTests(unittest.TestCase):
    def run_cli(self, *arguments: str, expected: int = 0) -> dict:
        command = [sys.executable, "-B", str(ROOT / "svgdrawer.py"), *arguments, "--json"]
        completed = subprocess.run(
            command,
            cwd=ROOT,
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
        self.assertEqual(completed.stderr, "")
        response = json.loads(completed.stdout)
        self.assertTrue(response["ok"])
        self.assertEqual(response["schema_version"], 2)
        return response["data"]

    def test_conda_runtime_and_legacy_launchers(self) -> None:
        environment = (ROOT / "environment.yml").read_text(encoding="utf-8").lower()
        self.assertIn("python=3.12", environment)
        self.assertIn("cairosvg=2.8.2", environment)
        self.assertIn("cairo", environment)
        self.assertIn("pillow", environment)
        self.assertTrue((ROOT / "start.py").is_file())
        self.assertFalse((ROOT / "start_windows.bat").exists())
        self.assertFalse((ROOT / "svgdrawer.cmd").exists())
        self.assertFalse((ROOT / "tools" / "install_cairo.py").exists())
        self.assertFalse((ROOT / "requirements-png.txt").exists())
        self.assertFalse((ROOT / "requirements-optional.txt").exists())

    def test_start_launcher_serves_health_on_a_custom_port(self) -> None:
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        process = subprocess.Popen(
            [sys.executable, str(ROOT / "start.py"), "--port", str(port), "--no-browser"],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            deadline = time.monotonic() + 12
            response = None
            while time.monotonic() < deadline:
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=1) as result:
                        response = json.loads(result.read())
                    break
                except (urllib.error.URLError, ConnectionError):
                    time.sleep(0.1)
            self.assertIsNotNone(response, "launcher did not start")
            self.assertEqual(response["app"], "svgdrawer")
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    def test_static_icon_catalog_and_per_symbol_provenance(self) -> None:
        data = self.run_cli("--list-all-flat")
        symbols = data["symbols"]
        self.assertEqual(data["symbol_count"], EXPECTED_SYMBOL_COUNT)
        static = [symbol for symbol in symbols if symbol["kind"] == "svg"]
        self.assertEqual(len(static), EXPECTED_STATIC_COUNT)
        self.assertEqual({symbol["style"] for symbol in static}, {"rounded-outline"})
        collections = {"lucide": 0, "tabler": 0}
        for symbol in static:
            with self.subTest(symbol=symbol["id"]):
                self.assertFalse(symbol["customizable"])
                source_dir = ROOT / "Gallery" / symbol["category"] / symbol["id"]
                definition = json.loads((source_dir / "symbol.json").read_text(encoding="utf-8"))
                source = definition["source"]
                collection = source["collection"].lower()
                self.assertIn(collection, collections)
                collections[collection] += 1
                self.assertTrue(source["icon"])
                self.assertIn("freeicons.org", source["discovery_url"])
                self.assertTrue(source["license"])
                license_text = (source_dir / "LICENSE.txt").read_text(encoding="utf-8")
                self.assertTrue(license_text.strip())
                for license_name in re.split(r"\s*/\s*", source["license"]):
                    self.assertIn(license_name.lower(), license_text.lower())
                source_svg = (source_dir / "source.svg").read_text(encoding="utf-8")
                self.assertIn(collection, source_svg.lower())
                self.assertIn(source["url"].lower(), source_svg.lower())
        self.assertEqual(collections, {"lucide": 12, "tabler": 12})

    def test_static_svg_export_and_png_preserve_source_notice(self) -> None:
        static = [symbol for symbol in self.run_cli("--list-all-flat")["symbols"] if symbol["kind"] == "svg"]
        symbol = static[0]
        source_dir = ROOT / "Gallery" / symbol["category"] / symbol["id"]
        source_svg = (source_dir / "source.svg").read_text(encoding="utf-8")
        source_root = ET.fromstring(source_svg)
        desc = next(node.text or "" for node in source_root.iter() if node.tag.rsplit("}", 1)[-1] == "desc")
        with tempfile.TemporaryDirectory(prefix="svgdrawer-static-export-") as temporary:
            output = Path(temporary) / f"{symbol['id']}.png"
            self.run_cli("--create", symbol["id"], "--format", "png", "--output", output)
            exported_svg = output.with_suffix(".svg").read_text(encoding="utf-8")
            self.assertIn(desc.splitlines()[0], exported_svg)
            with Image.open(output) as image:
                self.assertIn(desc.splitlines()[0], image.info.get("Description", ""))


if __name__ == "__main__":
    unittest.main()
