"""Create deterministic SHA-256 manifests for directory trees."""

from __future__ import annotations

import argparse
import errno
import hashlib
import json
import os
import stat
from pathlib import Path
from typing import TypedDict


class ManifestEntry(TypedDict):
    """One file in a checksum manifest."""

    path: str
    sha256: str
    size: int


_SECURE_OPEN_AVAILABLE = (
    hasattr(os, "O_DIRECTORY")
    and hasattr(os, "O_NOFOLLOW")
    and os.open in os.supports_dir_fd
)
_DIRECTORY_FLAGS = (
    os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
)
_FILE_FLAGS = (
    os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
)


def _hash_file_at(
    directory_fd: int, name: str, chunk_size: int = 64 * 1024
) -> tuple[str, int] | None:
    file_fd = os.open(name, _FILE_FLAGS, dir_fd=directory_fd)
    digest = hashlib.sha256()
    size = 0
    try:
        if not stat.S_ISREG(os.fstat(file_fd).st_mode):
            return None
        while chunk := os.read(file_fd, chunk_size):
            digest.update(chunk)
            size += len(chunk)
    finally:
        os.close(file_fd)
    return digest.hexdigest(), size


def _open_root(path: Path) -> int:
    if not _SECURE_OPEN_AVAILABLE:
        raise OSError(errno.ENOTSUP, "secure directory traversal is unavailable")
    absolute = path if path.is_absolute() else Path.cwd() / path
    descriptor = os.open(absolute.anchor, _DIRECTORY_FLAGS)
    try:
        for part in absolute.parts[1:]:
            try:
                child = os.open(part, _DIRECTORY_FLAGS, dir_fd=descriptor)
            except OSError as error:
                if error.errno in {errno.ELOOP, errno.ENOTDIR}:
                    try:
                        metadata = os.stat(
                            part, dir_fd=descriptor, follow_symlinks=False
                        )
                    except OSError:
                        pass
                    else:
                        if stat.S_ISLNK(metadata.st_mode):
                            raise ValueError(
                                f"root must not contain a symbolic link: {path}"
                            ) from error
                if error.errno in {errno.ENOENT, errno.ENOTDIR}:
                    raise ValueError(f"root is not a directory: {path}") from error
                raise
            os.close(descriptor)
            descriptor = child
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _open_descendant(root_fd: int, parts: tuple[str, ...]) -> int:
    descriptor = os.dup(root_fd)
    try:
        for part in parts:
            child = os.open(part, _DIRECTORY_FLAGS, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def build_manifest(root: str | Path) -> list[ManifestEntry]:
    """Return a stable manifest for regular files below *root*.

    Symbolic links are rejected instead of followed so a manifest cannot
    silently include content outside the requested tree.
    """

    root_path = Path(root)
    entries: list[ManifestEntry] = []
    root_fd = _open_root(root_path)
    pending: list[tuple[str, ...]] = [()]
    try:
        while pending:
            directory_parts = pending.pop()
            directory_fd = _open_descendant(root_fd, directory_parts)
            try:
                with os.scandir(directory_fd) as iterator:
                    children = sorted(iterator, key=lambda entry: entry.name)
                for child in children:
                    relative_parts = directory_parts + (child.name,)
                    relative = Path(*relative_parts).as_posix()
                    if child.is_symlink():
                        raise ValueError(
                            f"symbolic links are not supported: {relative}"
                        )
                    if child.is_dir(follow_symlinks=False):
                        pending.append(relative_parts)
                    elif child.is_file(follow_symlinks=False):
                        result = _hash_file_at(directory_fd, child.name)
                        if result is not None:
                            checksum, size = result
                            entries.append(
                                {
                                    "path": relative,
                                    "sha256": checksum,
                                    "size": size,
                                }
                            )
            finally:
                os.close(directory_fd)
    finally:
        os.close(root_fd)
    return sorted(entries, key=lambda entry: entry["path"])


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
