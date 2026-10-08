# Building

The build runs on Linux and makes `Homebrew Channel Upside Down - UHBC [cmyksoda].wad` at the root of the repo.

## You'll need

- Python 3 (the build makes its own venv in `build/.venv`)
- `wine`, to run Benzin
- [devkitPPC](https://devkitpro.org) with libogc, for the forwarder
- `ffmpeg`, only for the preview video

## Files to add yourself

These aren't in the repo, because they're other people's work.

- `donor/hbc1.1.4-unpatched.wad`: any official Homebrew Channel WAD, e.g. from [ForwarderFactory's hbc-archive](https://github.com/ForwarderFactory/hbc-archive). Every 1.1.x release has the same banner. Only the banner is used.
- `donor/Pink HBC - PHBC.wad`: any HBC forwarder WAD, e.g. from [MarioCube](https://repo.mariocube.com/WADs/Forwarders/Homebrew%20Channel%20Forwarders/). Only its NAND loader, ticket and TMD are used.
- `build/tools/benzin/BENZIN.EXE` and `CYGWIN1.DLL`: [Benzin](https://wiibrew.org/wiki/Benzin).

Different file names? Change them in `build/tools/hbcud.py`, where every setting lives.

## Platform packages

```sh
build/build.sh --release
```

This rebuilds the forwarder and makes `build/out/Wii-ONLY-UHBC-v1.zip` and
`build/out/vWii-ONLY-UHBC-v1.zip`. Both keep the v1.0.0 ZIP layout: `UHBC-v1/`
containing the WAD, README and license. The Wii package keeps its original loader;
the vWii package uses FIX94’s r2 loader. The root-level Wii WAD stays untouched.

This path reuses its finished banner, so it needs only devkitPPC, Python and
PyCryptodome (installed in the build venv), plus `donor/00000001-vwii.app`.
Extract `00000001.app` from [FIX94’s r2 ZIP](https://github.com/FIX94/tiny-vwii-nand-loader/blob/2eed1fa0a5c88bda0c96d47cf31fcde88c6c344e/binary/vWii_NAND_Loader_svn_r2.zip) and save it as `donor/00000001-vwii.app`.
The build checks its SHA-256; other loaders are rejected.

Use `--wii` or `--vwii` instead for just that platform’s WAD in `build/out/`.
Run regression checks with `build/.venv/bin/python -m unittest discover -s build/tests -v`.

## Rebuild the banner

```sh
build/build.sh
```

That builds the forwarder, flips the banner and icon, packs the WAD, and runs `build/tools/verify.py`. The checks catch mistakes that only show up on a console: an icon too big for the Wii Menu, wrong sizes or checksums, broken archives, or a title ID that clashes with HBC or a known forwarder.

```sh
build/build.sh --previews
```

This also renders the images in `preview/` and `build/out/banner_16_9.mp4`, a video of the banner with its sound. It takes a few minutes.

## What each script does

- `forwarder/`: the forwarder DOL (`make`, with `DEVKITPRO` set).
- `build/tools/build_banner.py`: turns the banner and icon upside down.
- `build/tools/build_wad.py`: packs the banner and forwarder into a WAD with title ID `UHBC`.
- `build/tools/package_release.py`: builds and checks the two platform ZIPs.
- `build/tools/verify.py`: the console checks.
- `build/tools/render.py`, `make_previews.py`, `make_video.py`: the previews. They render the finished files, so a mistake in the WAD shows up in them too.
- `build/tools/wiilib.py`, `tpl.py`: WAD, archive, compression and texture helpers.
