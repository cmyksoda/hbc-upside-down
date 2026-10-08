"""Packaging regression checks using the released WAD and pinned local loader."""

import hashlib
from pathlib import Path
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from build_wad import build_platform
from hbcud import FORWARDER_DOL, VWII_LOADER, WAD_PATH
from wiilib import WAD


class VwiiBuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.base = self.root / "original.wad"
        self.base.write_bytes(Path(WAD_PATH).read_bytes())
        self.output = self.root / "vwii.wad"

    def build(self, **kwargs):
        return build_platform("vwii", base_path=self.base, output_path=self.output, **kwargs)

    def mutate_base(self, change):
        wad = WAD.load(self.base)
        change(wad)
        wad.save(self.base)

    def test_round_trip_preserves_banner_forwarder_and_original(self):
        original = self.base.read_bytes()
        old = WAD.load(self.base)
        size = self.build()
        new = WAD.load(self.output)
        self.assertEqual(size, self.output.stat().st_size)
        self.assertEqual(self.base.read_bytes(), original)
        self.assertEqual(new.contents[0], old.contents[0])
        self.assertEqual(new.contents[1], Path(VWII_LOADER).read_bytes())
        self.assertNotEqual(new.contents[1], old.contents[1])
        self.assertEqual(new.contents[2], Path(FORWARDER_DOL).read_bytes())
        self.assertEqual(new.tik, old.tik)
        self.assertEqual(new.certs, old.certs)
        self.assertEqual(new.crl, old.crl)
        self.assertEqual(new.footer, old.footer)
        # Only the fakesign nonce, loader size and loader hash may change in the TMD
        # when the rebuilt forwarder matches the release.
        expected_tmd = bytearray(old.tmd)
        loader_entry = 0x1E4 + 36
        expected_tmd[0x1D4:0x1D6] = new.tmd[0x1D4:0x1D6]
        expected_tmd[loader_entry + 8:loader_entry + 36] = \
            new.tmd[loader_entry + 8:loader_entry + 36]
        if new.contents[2] == old.contents[2]:
            self.assertEqual(new.tmd, expected_tmd)
        for i, content in enumerate(new.contents):
            entry = 0x1E4 + i * 36
            self.assertEqual(hashlib.sha1(content).digest(), new.tmd[entry + 16:entry + 36])
        self.assertEqual(hashlib.sha1(new.tmd[0x140:]).digest()[0], 0)

    def test_build_is_deterministic(self):
        self.build()
        first = self.output.read_bytes()
        self.build()
        self.assertEqual(self.output.read_bytes(), first)

    def test_rejects_wii_loader(self):
        loader = self.root / "wii.app"
        loader.write_bytes(WAD.load(self.base).contents[1])
        with self.assertRaisesRegex(ValueError, "FIX94 r2"):
            self.build(loader_path=loader)
        self.assertFalse(self.output.exists())

    def test_rejects_other_title(self):
        self.mutate_base(lambda wad: wad.set_title_id("LULZ"))
        with self.assertRaisesRegex(ValueError, "UHBC"):
            self.build()

    def test_rejects_wrong_boot_index(self):
        def change(wad):
            tmd = bytearray(wad.tmd)
            struct.pack_into(">H", tmd, 0x1E0, 2)
            wad.tmd = bytes(tmd)
        self.mutate_base(change)
        with self.assertRaisesRegex(ValueError, "boot index 1"):
            self.build()

    def test_rejects_wrong_content_index(self):
        def change(wad):
            tmd = bytearray(wad.tmd)
            struct.pack_into(">H", tmd, 0x1E4 + 2 * 36 + 4, 4)
            wad.tmd = bytes(tmd)
        self.mutate_base(change)
        with self.assertRaisesRegex(ValueError, "indices 0, 1, 2"):
            self.build()

    def test_rejects_corrupt_base(self):
        raw = bytearray(self.base.read_bytes())
        raw[-128] ^= 1
        self.base.write_bytes(raw)
        with self.assertRaisesRegex(ValueError, "SHA-1 mismatch"):
            self.build()

    def test_refuses_overwriting_original(self):
        original = self.base.read_bytes()
        with self.assertRaisesRegex(ValueError, "overwrite"):
            build_platform("vwii", base_path=self.base, output_path=self.base)
        self.assertEqual(self.base.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
