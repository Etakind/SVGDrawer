"""Loopback HTTP contract tests for the Python-backed Gallery application."""

from __future__ import annotations

import json
import io
from pathlib import Path
import struct
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from PIL import Image


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server import Handler, cairosvg
from cli.main import parser


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def fetch(self, path: str, payload: object | None = None, headers: dict | None = None):
        request_headers = {"Content-Type": "application/json"}
        request_headers.update(headers or {})
        request = urllib.request.Request(
            self.url + path,
            data=None if payload is None else json.dumps(payload).encode("utf-8"),
            headers=request_headers,
        )
        try:
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            with opener.open(request, timeout=15) as response:
                return response.status, response.headers, response.read()
        except urllib.error.HTTPError as error:
            return error.code, error.headers, error.read()

    def test_health_and_local_frontend(self) -> None:
        code, _, body = self.fetch("/api/health")
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["app"], "svgdrawer")

        code, _, body = self.fetch("/")
        self.assertEqual(code, 200)
        self.assertIn(b"SVGDrawer", body)
        self.assertNotIn(b"__BOOT_DATA__", body)

    def test_default_and_custom_ports_are_explicit(self) -> None:
        self.assertEqual(parser().parse_args(["--serve"]).port, 9178)
        self.assertEqual(parser().parse_args(["--serve", "--port", "0"]).port, 0)

    def test_gallery_metadata_and_trash_are_disk_backed(self) -> None:
        code, _, body = self.fetch("/api/gallery")
        self.assertEqual(code, 200)
        gallery = json.loads(body)
        self.assertGreaterEqual(len(gallery["symbols"]), 33)
        self.assertTrue(all("customizable" in symbol for symbol in gallery["symbols"]))

        code, _, body = self.fetch("/api/trash")
        self.assertEqual(code, 200)
        trash = json.loads(body)
        self.assertIn("entries", trash)
        self.assertEqual(trash["entry_count"], len(trash["entries"]))

    def test_management_dry_run_uses_schema_two(self) -> None:
        payload = {
            "action": "update-symbol",
            "id": "circle",
            "description": "HTTP dry run",
            "tags": ["http", "test"],
            "dry_run": True,
        }
        code, _, body = self.fetch("/api/manage", payload)
        self.assertEqual(code, 200)
        result = json.loads(body)
        self.assertEqual(result["schema_version"], 2)
        self.assertTrue(result["ok"])
        self.assertEqual(result["action"], "update-symbol")
        self.assertEqual(result["data"]["symbol"]["description"], "HTTP dry run")

    def test_backup_is_an_active_gallery_zip(self) -> None:
        code, headers, body = self.fetch("/api/backup")
        self.assertEqual(code, 200)
        self.assertEqual(headers.get_content_type(), "application/zip")
        self.assertEqual(body[:2], b"PK")

    def test_svg_and_management_errors(self) -> None:
        code, _, body = self.fetch("/api/render", {"action": "export", "asset": {"type": "chip"}})
        self.assertEqual(code, 200)
        self.assertIn("<svg", json.loads(body)["svg"])

        self.assertEqual(self.fetch("/missing")[0], 404)
        self.assertEqual(self.fetch("/api/render", [])[0], 400)
        self.assertEqual(self.fetch("/api/manage", {"action": "unknown"})[0], 400)
        self.assertEqual(self.fetch("/api/render", {}, headers={"Content-Type": "text/plain"})[0], 415)

    def test_remote_origins_and_hosts_are_rejected(self) -> None:
        self.assertEqual(self.fetch("/api/health", headers={"Host": "evil.example"})[0], 403)
        self.assertEqual(
            self.fetch(
                "/api/manage",
                {"action": "list-trash"},
                headers={"Origin": "https://evil.example"},
            )[0],
            403,
        )

    @unittest.skipIf(cairosvg is None, "Provisioned CairoSVG is not installed")
    def test_python_png_has_requested_dimensions(self) -> None:
        code, headers, body = self.fetch(
            "/api/png",
            {"asset": {"type": "chip"}, "options": {"width": 300, "height": 200}, "scale": 2},
        )
        self.assertEqual(code, 200)
        self.assertEqual(headers.get_content_type(), "image/png")
        self.assertEqual(body[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(struct.unpack(">II", body[16:24]), (600, 400))
        self.assertEqual(
            self.fetch(
                "/api/png",
                {"asset": {"type": "chip"}, "options": {"width": 4096, "height": 4096}, "scale": 4},
            )[0],
            400,
        )

    @unittest.skipIf(cairosvg is None, "Provisioned CairoSVG is not installed")
    def test_static_png_preserves_source_notice(self) -> None:
        code, _, body = self.fetch("/api/gallery")
        self.assertEqual(code, 200)
        static = next(symbol for symbol in json.loads(body)["symbols"] if symbol["kind"] == "svg")
        code, headers, body = self.fetch(
            "/api/png",
            {"asset": {"type": static["id"]}, "options": {"width": 256, "height": 256}},
        )
        self.assertEqual(code, 200)
        self.assertEqual(headers.get_content_type(), "image/png")
        with Image.open(io.BytesIO(body)) as image:
            description = image.info.get("Description", "").lower()
        self.assertTrue(any(provider in description for provider in ("lucide", "tabler")))


if __name__ == "__main__":
    unittest.main()
