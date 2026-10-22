"""Artifact identity and inventory checks shared by tests, install and release."""
from __future__ import annotations

import hashlib
from pathlib import Path

from .common import read_json, within


def sha_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory(folder):
    folder = Path(folder).resolve()
    if not folder.is_dir():
        raise FileNotFoundError(folder)
    files = {}
    for path in sorted(folder.rglob("*")):
        # Reject links rather than publishing files outside the artifact tree.
        if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
            raise ValueError(f"Artifact contains a link: {path}")
        if path.is_file():
            within(folder, path)
            stat = path.stat()
            files[path.relative_to(folder).as_posix()] = dict(
                size=stat.st_size, mtime_ns=stat.st_mtime_ns, ctime_ns=stat.st_ctime_ns)
    return files


def inspect(folder, *, hashes=False, distribution=False):
    folder = Path(folder).resolve()
    meta = read_json(folder / ".metadata/metadata.json")
    manifest_path = folder / "build_manifest.json"
    manifest = read_json(manifest_path)
    files = inventory(folder)
    expected = set(manifest["files"]) | {"build_manifest.json"}
    missing, extra = sorted(expected - files.keys()), sorted(files.keys() - expected)
    invalid = []
    for relative in manifest["files"]:
        within(folder, folder / relative)
    if hashes:
        invalid = [name for name, digest in manifest["files"].items()
                   if name in files and sha_file(folder / name) != digest]
    if distribution and manifest.get("distribution_compaction", {}).get("strategy") != "all_files_preserved_bc3":
        raise ValueError("Workshop content must be a complete compact distribution; run package first")
    if missing or extra or invalid:
        raise ValueError(f"Artifact mismatch: missing={missing}, extra={extra}, invalid={invalid}")
    return dict(path=str(folder), version=meta["version"], file_count=len(files),
                bytes=sum(row["size"] for row in files.values()),
                manifest_sha256=sha_file(manifest_path), files=files,
                full_hashes_checked=hashes,
                distribution=bool(manifest.get("distribution_compaction")))


def unchanged(identity):
    """Cheap freeze guard, not a substitute for a cryptographic audit."""
    fresh = inspect(identity["path"], distribution=identity.get("distribution", False))
    if (fresh["files"], fresh["manifest_sha256"]) != (identity["files"], identity["manifest_sha256"]):
        raise ValueError("Artifact changed after the plan was prepared; prepare a new plan")
    return fresh
