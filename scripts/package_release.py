"""Create a release zip with the binary and config.yaml."""

from __future__ import annotations

import argparse
import os
import shutil
import zipfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Package release zip for portrait-packager")
    parser.add_argument("--binary-name", required=True, help="Built binary filename in dist/")
    parser.add_argument("--zip-name", required=True, help="Output zip filename")
    args = parser.parse_args()

    package_dir = Path("release-staging/package")
    package_dir.mkdir(parents=True, exist_ok=True)

    binary_src = Path("dist") / args.binary_name
    binary_dst = package_dir / args.binary_name
    shutil.copy2(binary_src, binary_dst)
    shutil.copy2("config.example.yaml", package_dir / "config.yaml")

    if os.name != "nt":
        binary_dst.chmod(0o755)

    zip_path = Path("release-staging") / args.zip_name
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(package_dir.iterdir()):
            if file_path.is_file():
                archive.write(file_path, file_path.name)


if __name__ == "__main__":
    main()
