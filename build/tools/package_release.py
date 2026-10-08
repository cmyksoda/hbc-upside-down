"""Build and verify separate platform ZIPs in the v1.0.0 archive layout."""

from pathlib import Path
import subprocess
import sys
import zipfile

from build_wad import build_platform
from hbcud import OUT, ROOT, TOOLS, VWII_WAD_PATH, WAD_NAME, WII_WAD_PATH


def write_zip(path, wad_path, platform):
    root = Path(ROOT)
    license_text = (root / "LICENSE").read_bytes()
    if platform == "vwii":
        license_text += b"\n\n" + (root / "build/licenses/vwii-loader.txt").read_bytes()
    entries = {
        "UHBC-v1/": b"",
        "UHBC-v1/README.md": (root / "README.md").read_bytes(),
        "UHBC-v1/LICENSE": license_text,
        f"UHBC-v1/{WAD_NAME}": Path(wad_path).read_bytes(),
    }
    with zipfile.ZipFile(path, "w") as archive:
        for name, content in entries.items():
            entry = zipfile.ZipInfo(name, date_time=(2026, 9, 27, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = 0x41ED0010 if name.endswith("/") else 0x81A40000
            entry.compress_type = zipfile.ZIP_STORED if name.endswith("/") else zipfile.ZIP_DEFLATED
            archive.writestr(entry, content)
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None or archive.namelist() != list(entries):
            raise ValueError(f"invalid release ZIP: {path}")
        for name, content in entries.items():
            if archive.read(name) != content:
                raise ValueError(f"release ZIP content mismatch: {name}")


def main():
    targets = (("wii", "Wii-ONLY-UHBC-v1.zip", WII_WAD_PATH),
               ("vwii", "vWii-ONLY-UHBC-v1.zip", VWII_WAD_PATH))
    for platform, _, _ in targets:
        build_platform(platform)
        subprocess.run([sys.executable, str(Path(TOOLS) / "verify.py"), f"--{platform}"],
                       check=True)
    for platform, name, wad_path in targets:
        path = Path(OUT) / name
        write_zip(path, wad_path, platform)
        print(f"  {path}: {path.stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
