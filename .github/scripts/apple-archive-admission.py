#!/usr/bin/env python3
"""Fail-closed admission check for bounded Xcode archive artifacts."""

import os
import stat
import sys
from pathlib import Path


MAX_ARCHIVE_BYTES = 268435456


def admit_archive(path: os.PathLike[str] | str, max_bytes: int = MAX_ARCHIVE_BYTES) -> bool:
    """Return true only for a regular, contained archive tree within the cap."""
    archive = Path(path)
    try:
        root_stat = archive.lstat()
        if not stat.S_ISDIR(root_stat.st_mode):
            return False
        info_stat = (archive / "Info.plist").lstat()
        if not stat.S_ISREG(info_stat.st_mode):
            return False

        total = 0
        pending = [archive]
        while pending:
            directory = pending.pop()
            with os.scandir(directory) as entries:
                for entry in entries:
                    entry_stat = entry.stat(follow_symlinks=False)
                    if stat.S_ISDIR(entry_stat.st_mode):
                        pending.append(Path(entry.path))
                    elif stat.S_ISREG(entry_stat.st_mode):
                        total += entry_stat.st_size
                        if total > max_bytes:
                            return False
                    else:
                        return False
        return total <= max_bytes
    except (OSError, ValueError):
        return False


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: apple-archive-admission.py ARCHIVE", file=sys.stderr)
        return 2
    if not admit_archive(argv[1]):
        print("archive rejected: missing, unsafe, unreadable, or over the size limit", file=sys.stderr)
        return 1
    print("archive admitted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
