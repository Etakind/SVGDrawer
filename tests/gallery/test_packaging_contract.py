"""Release archive behavior for the local Python application."""

from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
import zipfile

from tools.package_release import package


class PackagingContractTests(unittest.TestCase):
    def test_package_returns_one_zip_with_active_sources_only(self) -> None:
        with tempfile.TemporaryDirectory(prefix="svgdrawer-release-") as temporary:
            archive_path = package(Path(temporary))
            self.assertEqual(archive_path, Path(temporary).resolve() / "SVGDrawer.zip")
            with zipfile.ZipFile(archive_path) as archive:
                names = set(archive.namelist())
            self.assertIn("SVGDrawer/Gallery/catalog.json", names)
            self.assertIn("SVGDrawer/Gallery/common.py", names)
            self.assertIn("SVGDrawer/server.py", names)
            self.assertNotIn("SVGDrawer/build.py", names)
            self.assertNotIn("SVGDrawer/index.html", names)
            self.assertFalse(any(name.startswith("SVGDrawer/.conda/") for name in names))
            self.assertFalse(any(name.startswith("SVGDrawer/.venv/") for name in names))
            self.assertIn("SVGDrawer/Gallery/basics/exchange_opposed_arrows/source.svg", names)
            self.assertIn("SVGDrawer/Gallery/basics/exchange_opposed_arrows/LICENSE.txt", names)
            self.assertFalse(any("/.trash/" in name or "/.history/" in name for name in names))
            self.assertFalse(any(name.endswith((".pyc", ".pyo")) for name in names))


if __name__ == "__main__":
    unittest.main()
