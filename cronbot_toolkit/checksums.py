"""Create deterministic SHA-256 manifests for directory trees."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import TypedDict


class ManifestEntry(TypedDict):
    """One file in a checksum manifest."""

    path: str
    sha256: str
    size: int


def _hash_file(path: Path, chunk_size: int = 64 * 1024) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def _regular_files(root: Path) -> list[Path]:
    """Return files below *root*, propagating directory traversal errors."""

    files: list[Path] = []

    def visit(directory: Path) -> None:
        with os.scandir(directory) as iterator:
            entries = sorted(iterator, key=lambda entry: entry.name)
        for entry in entries:
            path = Path(entry.path)
            if entry.is_symlink():
                relative = path.relative_to(root).as_posix()
                raise ValueError(f"symbolic links are not supported: {relative}")
            if entry.is_dir(follow_symlinks=False):
                visit(path)
            elif entry.is_file(follow_symlinks=False):
                files.append(path)

    visit(root)
    return sorted(files, key=lambda path: path.relative_to(root).as_posix())


def _first_symlink_component(path: Path) -> Path | None:
    """Return the first symbolic link in *path*, including its parents."""

    absolute = path if path.is_absolute() else Path.cwd() / path
    current = Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current /= part
        if current.is_symlink():
            return current
    return None


def build_manifest(root: str | Path) -> list[ManifestEntry]:
    """Return a stable manifest for regular files below *root*.

    Symbolic links are rejected instead of followed so a manifest cannot
    silently include content outside the requested tree.
    """

    root_path = Path(root)
    symlink_component = _first_symlink_component(root_path)
    if symlink_component is not None:
        raise ValueError(
            f"root must not contain a symbolic link: {symlink_component}"
        )
    if not root_path.is_dir():
        raise ValueError(f"root is not a directory: {root_path}")

    entries: list[ManifestEntry] = []
    for path in _regular_files(root_path):
        checksum, size = _hash_file(path)
        entries.append(
            {
                "path": path.relative_to(root_path).as_posix(),
                "sha256": checksum,
                "size": size,
            }
        )
    return entries


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Print a deterministic SHA-256 manifest as JSON."
    )
    parser.add_argument("root", help="directory to include in the manifest")
    args = parser.parse_args(argv)
    try:
        manifest = build_manifest(args.root)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
