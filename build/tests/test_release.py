"""Check platform separation and the published v1 archive layout."""

from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from build_wad import build_platform
from hbcud import VWII_LOADER, WAD_NAME, WAD_PATH
from package_release import write_zip
from wiilib import WAD


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_platforms_keep_their_own_loaders(self):
        base = WAD.load(WAD_PATH)
        for platform in ("wii", "vwii"):
            with self.subTest(platform=platform):
                path = self.root / f"{platform}.wad"
                build_platform(platform, output_path=path)
                wad = WAD.load(path)
                expected = (Path(VWII_LOADER).read_bytes()
                            if platform == "vwii" else base.contents[1])
                self.assertEqual(wad.contents[1], expected)
                self.assertEqual(wad.contents[0], base.contents[0])
                self.assertEqual(wad.title_id, base.title_id)

    def test_wii_rejects_vwii_loader_in_base(self):
        base = self.root / "vwii.wad"
        build_platform("vwii", output_path=base)
        with self.assertRaisesRegex(ValueError, "original Wii release"):
            build_platform("wii", base_path=base, output_path=self.root / "bad.wad")

    def test_rejects_unknown_platform(self):
        with self.assertRaisesRegex(ValueError, "platform"):
            build_platform("universal", output_path=self.root / "bad.wad")

    def test_zip_layout_and_payloads(self):
        for platform in ("wii", "vwii"):
            with self.subTest(platform=platform):
                wad = self.root / f"{platform}.wad"
                archive = self.root / f"{platform}.zip"
                build_platform(platform, output_path=wad)
                write_zip(archive, wad, platform)
                first = archive.read_bytes()
                write_zip(archive, wad, platform)
                self.assertEqual(archive.read_bytes(), first)
                with zipfile.ZipFile(archive) as z:
                    self.assertIsNone(z.testzip())
                    self.assertEqual(z.namelist(), ["UHBC-v1/", "UHBC-v1/README.md",
                                                   "UHBC-v1/LICENSE", f"UHBC-v1/{WAD_NAME}"])
                    self.assertEqual(z.read(f"UHBC-v1/{WAD_NAME}"), wad.read_bytes())
                    self.assertEqual(z.getinfo("UHBC-v1/").external_attr, 0x41ED0010)
                    license_text = z.read("UHBC-v1/LICENSE")
                    self.assertEqual(b"COPYING.tinyload" in license_text, platform == "vwii")


if __name__ == "__main__":
    unittest.main()
