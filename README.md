[![GitHub release (latest by date)](https://img.shields.io/github/v/release/panshaigan/infinity-portrait-packager?color=darkred&include_prereleases&label=latest%20release)](https://github.com/panshaigan/infinity-portrait-packager/releases/latest)
[![Github downloads (all releases)](https://img.shields.io/github/downloads/panshaigan/infinity-portrait-packager/total.svg?color=gold)](https://github.com/panshaigan/infinity-portrait-packager/releases)
[![Platform](https://img.shields.io/static/v1?label=platform&message=Windows%20%7C%20Linux&color=informational)](https://github.com/panshaigan/infinity-portrait-packager/releases/latest)
[![Supported games](https://img.shields.io/static/v1?label=supported%20games&message=BG%3AEE%20%7C%20BG2%3AEE%20%7C%20EET%20%7C%20IWD%3AEE%20%7C%20PST%3AEE&color=indigo)](https://github.com/panshaigan/infinity-portrait-packager)
[![Language](https://img.shields.io/static/v1?label=language&message=English&color=limegreen)](https://github.com/panshaigan/infinity-portrait-packager)

# Infinity Portrait Packager

A command-line tool for preparing Baldur's Gate / Infinity Engine portrait packs. Point it at a portrait group (e.g. `party_bg1`), and it downscales and converts `M`, `L`, and `r` category images into per-group destination subfolders — with optional thumbnails — for game distribution or web promotion. Windows and Linux binaries available.

## Requirements

- Python 3.10+ (for running from source)
- Or download a release binary for [Windows](https://github.com/panshaigan/infinity-portrait-packager/releases) or Linux

## Quick start

### 1. Download and unpack

Download the zip for your platform from [Releases](https://github.com/panshaigan/infinity-portrait-packager/releases) and unzip it. The package contains:

- `ppackage` (or `ppackage.exe` on Windows) — the CLI binary
- `config.yaml` — ready-to-use configuration; edit paths if needed

### 2. Configuration

Edit `config.yaml` in the unpacked folder if your source/destination paths differ from the defaults. The config must sit next to the executable (or pass `--config` explicitly).

When running from source, copy the example config first:

```bash
cp config.example.yaml config.yaml
```

### 3. Source folder layout

```
sources/
  party_bg1/
    M/
      portrait001.png
    L/
      portrait001.png
    r/
      portrait001.png
  party_bg2/
    ...
```

### 4. Run

**Windows (release package):**

```powershell
ppackage.exe party_bg1
ppackage.exe party_bg1 --config D:\path\config.yaml
ppackage.exe party_bg1 --dest game_bmp --dry-run --verbose
```

**Linux (release package):**

```bash
chmod +x ppackage
./ppackage party_bg1
./ppackage party_bg1 --config /path/to/config.yaml
```

**From source (Windows or Linux):**

```bash
pip install -r requirements.txt
python -m portrait_packager party_bg1
```



## Output

For each destination, all categories are written into a subfolder named after the portrait group (e.g. `party_bg1/`). Filenames keep the original stem with the category appended (no separator):

- `party_bg1/L/portrait001.png` → `{dest}/party_bg1/portrait001L.bmp`

When thumbnails are configured, they are written to `{dest}/{group}/thumbs/` with the same filename and destination format.

When `contact_sheet` is configured, one WebP grid is built per processed category from the destination outputs (1px black gaps between cells), saved as `{path}/{group}_{category}.webp`, plus a downscaled `{path}/{group}_{category}_thumb.webp`.

Images are resized to the exact configured width and height for each category mapping.

## Config reference

See [config.example.yaml](config.example.yaml). Key fields:


| Field                                | Description                                                         |
| ------------------------------------ | ------------------------------------------------------------------- |
| `sources.root`                       | Root folder containing portrait group subfolders                    |
| `categories`                         | Category subfolder names (`M`, `L`, `r`)                            |
| `destinations[].format`              | Output format: `bmp` (24-bit RGB) or `webp`                         |
| `destinations[].mappings`            | Per-category exact output width/height; omit categories to skip them |
| `destinations[].prefixes`            | Optional; maps source stem → prefix for output sort order           |
| `destinations[].thumbnails.max_size` | Optional; longest side for thumbs in `thumbs/`                      |
| `destinations[].contact_sheet`       | Optional; grid sheet + thumb WebPs in `path/` per category          |
| `destinations[].contact_sheet.width` | Full sheet target width in pixels                                   |
| `destinations[].contact_sheet.thumb_width` | Thumb sheet target width in pixels                              |
| `destinations[].contact_sheet.cols`  | Per-group column counts (group name → columns)                        |
| `destinations[].contact_sheet.path`  | Output folder for `{group}_{category}.webp` files                   |

Each destination may define mappings for only some categories — unconfigured categories are skipped. When `prefixes` is set, matching files are named `{prefix}{stem}{category}.{ext}` (e.g. `L/bdimoen.png` with prefix `sod` → `sodbdimoenL.webp`).




## Development

```bash
pip install -r requirements-dev.txt
python -m pytest
```

### Run locally without building an exe

From the project root, with your config beside you or passed explicitly:

```bash
pip install -r requirements.txt
cp config.example.yaml config.yaml   # first time only; edit paths
python -m portrait_packager party_bg1 --config config.yaml --verbose
```

Useful flags while iterating:

```bash
python -m portrait_packager party_bg1 --dest promo_compilation --dry-run --verbose
python -m portrait_packager party_bg1 --cols 12
```

`--dry-run` shows what would be written; `--verbose` prints each source file and output name (check prefix matching there). `--cols` overrides the contact sheet column count from config for the current group.

### Build the executable

PyInstaller is included in the dev dependencies. Install them first, then build with the module form (works even when `pyinstaller` is not on your PATH):

```bash
pip install -r requirements-dev.txt
python -m PyInstaller portrait-packager.spec
```

Output:

- Windows: `dist/ppackage.exe`
- Linux: `dist/ppackage`

Test the built binary from the project root (place or point to a `config.yaml`):

```powershell
# Windows
.\dist\ppackage.exe party_bg1 --config config.yaml --verbose
```

```bash
# Linux
chmod +x dist/ppackage
./dist/ppackage party_bg1 --config config.yaml --verbose
```

Optional: package a release-style zip (binary + `config.yaml`), same as CI:

```bash
python -m PyInstaller portrait-packager.spec
python scripts/package_release.py --binary-name ppackage.exe --zip-name portrait-packager-windows-x86_64.zip
# Linux: --binary-name ppackage --zip-name portrait-packager-linux-x86_64.zip
```

The zip is written to `release-staging/`.



## Releases

Tag a version to trigger a GitHub Actions build for Windows and Linux:

```bash
git tag v1.0.0
git push origin v1.0.0
```

**Important:** Push the tag from git (`git push origin v1.0.0`). Creating a release only through the GitHub web UI may not trigger the workflow if Actions was not yet enabled.

If Actions did not run, check **Settings → Actions → General** and ensure Actions are enabled for the repository. You can also run the **Release** workflow manually from the Actions tab (enter the tag, e.g. `v1.0.0`).

Release assets (one zip per platform):

- `portrait-packager-windows-x86_64.zip` — `ppackage.exe` + `config.yaml`
- `portrait-packager-linux-x86_64.zip` — `ppackage` + `config.yaml`



## Exit codes


| Code | Meaning                  |
| ---- | ------------------------ |
| 0    | Success                  |
| 1    | Portrait group not found |
| 2    | Config error             |
| 3    | Processing error         |


