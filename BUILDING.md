# Building

The build runs on Linux and makes `build/out/Homebrew Channel Upside Down - UHBC [cmyksoda].wad`.

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

## Build

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
- `build/tools/verify.py`: the console checks.
- `build/tools/render.py`, `make_previews.py`, `make_video.py`: the previews. They render the finished files, so a mistake in the WAD shows up in them too.
- `build/tools/wiilib.py`, `tpl.py`: WAD, archive, compression and texture helpers.
