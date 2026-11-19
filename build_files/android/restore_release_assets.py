#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Restore the Android runtime's Git LFS assets from a Blender release archive."""

import argparse
import hashlib
import re
import subprocess
import tarfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    archive_path = parser.parse_args().archive

    root = Path(__file__).resolve().parents[2]
    files = subprocess.check_output(
        ["git", "ls-files", "-z", "--", "assets", "release/datafiles", "scripts"],
        cwd=root,
    )
    pointer = re.compile(
        rb"version https://git-lfs.github.com/spec/v1\noid sha256:([0-9a-f]{64})\nsize (\d+)\n"
    )
    pending = {}
    for name in files.decode().split("\0"):
        if not name:
            continue
        path = root / name
        if not path.is_file() or path.stat().st_size > 1024:
            continue
        match = pointer.fullmatch(path.read_bytes())
        if match:
            pending[name] = (match[1].decode(), int(match[2]))

    restored = 0
    with tarfile.open(archive_path, "r|xz") as archive:
        for member in archive:
            name = member.name.partition("/")[2]
            if name not in pending or not member.isfile():
                continue
            digest, size = pending[name]
            if member.size != size:
                raise SystemExit(f"Release archive has an unexpected size for {name}")
            with archive.extractfile(member) as source:
                contents = source.read()
            if hashlib.sha256(contents).hexdigest() != digest:
                raise SystemExit(f"Release archive failed SHA-256 verification for {name}")
            (root / name).write_bytes(contents)
            del pending[name]
            restored += 1

    if pending:
        raise SystemExit("Release archive is missing Android assets:\n" + "\n".join(sorted(pending)))
    print(f"Restored {restored} Android runtime assets from the Blender release archive.")


if __name__ == "__main__":
    main()
