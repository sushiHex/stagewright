"""Publish a complete immutable USD package, then advance the current revision."""
import argparse
import json
import os
import tempfile
from pathlib import Path

from physics_usd import pack


def publish(source, directory):
    directory = directory.resolve()
    revisions = directory / "revisions"
    revisions.mkdir(parents=True, exist_ok=True)
    # Serialize numbering and pointer replacement as one operation.
    lock = revisions / ".publisher.lock"
    with lock.open("a+b") as stream:
        # Keep a stable lock file. The OS releases its lock if the worker exits.
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except (BlockingIOError, PermissionError) as error:
            raise RuntimeError(f"Another publisher is active in {directory}") from error
        return _publish(source, directory, revisions)


def _publish(source, directory, revisions):
    revision = 1 + max((int(path.stem) for path in revisions.glob("*.usdz")
                        if path.stem.isascii() and path.stem.isdecimal()), default=0)
    relative = Path("revisions") / f"{revision:04d}.usdz"
    pack(source, directory / relative)
    record = {"revision": revision, "scene": relative.as_posix()}
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory,
                                     suffix=".json", delete=False) as output:
        json.dump(record, output)
        output.write("\n")
        temporary = Path(output.name)
    try:
        temporary.replace(directory / "current.json")
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Published revision {revision}: {directory / relative}")
    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    publish(args.source, args.directory)
