# QR Code Generator

A small Windows desktop app for Flooring Partners that turns a URL or a set of
contact details into a QR code, with the company logo embedded in the middle.

Built with Python and Tkinter, packaged as a standard Windows program with an
installer and built-in updates.

## Features

- **URL tab** — paste a link, get a PNG
- **vCard tab** — fill in contact details and produce a scannable contact card
- Company logo embedded in the code by default, or swap in any image you like
- Optional rounded module style
- Configurable save folder and filename, remembered between sessions
- Opens the finished image automatically (can be turned off)
- Checks for new versions on launch and updates itself

Codes use the highest error-correction level, so the embedded logo does not stop
them scanning.

## Installing

Download `FPQRGenerator-<version>-setup.exe` from the
[latest release](https://github.com/fpcolin/fp-qr-gen/releases/latest) and run
it.

It installs per-user under `%LOCALAPPDATA%\Programs`, so no administrator rights
are needed. Settings are stored in:

```
%LOCALAPPDATA%\Flooring Partners\QR Code Generator\config.json
```

Uninstall from Settings → Apps like any other program.

## Using it

**URL:** open the URL tab, paste the link, click Generate QR Code.

**vCard:** open the vCard tab and fill in the fields. First and last name are
required; everything else is optional and is left out of the contact card if
blank. Click Generate QR Code.

The file is saved to your chosen folder. If a file of that name already exists,
a number is appended rather than overwriting anything.

### Menus

| Menu | Item | What it does |
|---|---|---|
| File | Change folder… | Pick where QR codes are saved |
| File | Check for updates… | Look for a newer version now |
| Options | Change filename | Set the base name for saved files |
| Options | Change embedded image | Use your own image instead of the logo |
| Options | Open image on generate | Open the PNG when it is created |
| Options | Open folder on generate | Open the containing folder too |
| Options | Embed logo | Toggle the centre image |
| Options | Round edges | Rounded module style |
| Help | — | Usage instructions inside the app |

## Updates

On launch the app quietly checks the latest release for a newer version and
offers to install it. The download is verified against a SHA-256 checksum before
anything is run, and the app relaunches once the update finishes.

If the check fails — no network, VPN down, GitHub unreachable — it is ignored
silently and the app carries on.

## Building from source

Requires Python 3.12+, [Inno Setup](https://jrsoftware.org/isdl.php), and:

```
pip install pyinstaller qrcode pillow
```

Then:

```
pyinstaller build\fp_qr_gen.spec --noconfirm --clean --workpath dist\work
iscc build\installer.iss
```

Releases are built automatically by GitHub Actions when a version tag is pushed.
See [BUILD.md](BUILD.md) for the full process, including versioning, code
signing, and troubleshooting.

## Repository layout

```
src/       application source and assets
build/     PyInstaller spec, Inno Setup script, release helper
.github/   release workflow
```

## Licence

Source code and documentation are released under the MIT Licence.

The Flooring Partners name, logo (`src/fp_logo.png`), and icon (`src/fp.ico`)
are excluded and remain company property — no trademark rights are granted. If
you fork this project, replace those files with your own and change the `VENDOR`
and `APP_NAME` constants in `src/fp_qr_gen.pyw`.

See [LICENSE.txt](LICENSE.txt) for both.

## AI disclosure

Portions of this project were developed with the help of an AI assistant
(Anthropic's Claude).

The original working version of the program was written by hand. AI assistance
was then used to refactor that code, remove a dependency, and build out the
packaging and release tooling — the PyInstaller spec, the Inno Setup installer,
the update mechanism, the GitHub Actions workflow, and the documentation. Some
bug fixes and later features were also written with AI assistance.

All AI-generated code was reviewed and tested before being committed, and the
maintainer is responsible for everything in this repository regardless of how it
was produced. It is noted here for transparency, not as a disclaimer of
ownership or accountability.
