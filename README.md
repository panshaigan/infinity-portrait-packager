# Infinity Portrait Packager

Prepare portrait files for distribution and promotion. Converts portrait groups from a source folder tree into flat destination folders with configurable formats, resolutions, and thumbnails.

## Requirements

- Python 3.10+ (for running from source)
- Or download a release binary for [Windows](https://github.com/panshaigan/infinity-portrait-packager/releases) or Linux

## Quick start

### 1. Configuration

Copy the example config and edit paths and mappings:

```bash
cp config.example.yaml config.yaml
```

Place `config.yaml` next to the executable, or in the current working directory when running from source.

### 2. Source folder layout

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

### 3. Run

**Windows (release binary):**

```powershell
portrait-packager.exe party_bg1
portrait-packager.exe party_bg1 --config D:\path\config.yaml
portrait-packager.exe party_bg1 --dest game_bmp --dry-run --verbose
```

**Linux (release binary):**

```bash
chmod +x portrait-packager-linux-x86_64
./portrait-packager-linux-x86_64 party_bg1
./portrait-packager-linux-x86_64 party_bg1 --config /path/to/config.yaml
```

**From source (Windows or Linux):**

```bash
pip install -r requirements.txt
python -m portrait_packager party_bg1
```

## Output

For each destination, all categories are written flat into the destination path. Filenames keep the original stem with the category appended (no separator):

- `party_bg1/L/portrait001.png` → `{dest}/portrait001L.bmp`

When thumbnails are configured, they are written to `{dest}/thumbs/` with the same filename and destination format.

Images are downscaled only (never upscaled), preserving aspect ratio to fit within the configured box.

## Config reference

See [config.example.yaml](config.example.yaml). Key fields:

| Field | Description |
|-------|-------------|
| `sources.root` | Root folder containing portrait group subfolders |
| `categories` | Category subfolder names (`M`, `L`, `r`) |
| `destinations[].format` | Output format: `bmp` (24-bit RGB) or `webp` |
| `destinations[].mappings` | Per-category max width/height (downscale fit) |
| `destinations[].thumbnails.max_size` | Optional; longest side for thumbs in `thumbs/` |

## Development

```bash
pip install -r requirements-dev.txt
pytest
```

Build a standalone binary locally:

```bash
pyinstaller portrait-packager.spec
# Output: dist/portrait-packager.exe (Windows) or dist/portrait-packager (Linux)
```

## Releases

Tag a version to trigger a GitHub Actions build for Windows and Linux:

```bash
git tag v1.0.0
git push origin v1.0.0
```

**Important:** Push the tag from git (`git push origin v1.0.0`). Creating a release only through the GitHub web UI may not trigger the workflow if Actions was not yet enabled.

If Actions did not run, check **Settings → Actions → General** and ensure Actions are enabled for the repository. You can also run the **Release** workflow manually from the Actions tab (enter the tag, e.g. `v1.0.0`).

Release assets:

- `portrait-packager-windows-x86_64.exe`
- `portrait-packager-linux-x86_64`
- `config.example.yaml`

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Portrait group not found |
| 2 | Config error |
| 3 | Processing error |
