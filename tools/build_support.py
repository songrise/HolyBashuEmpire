"""Shared byte-preserving I/O for build stages; no feature or game rules."""
from pathlib import Path
import hashlib
from contextlib import contextmanager
from contextvars import ContextVar


_deferred_root = ContextVar("deferred_snapshot_root", default=None)


@contextmanager
def defer_file_snapshots(out):
    """Batch-only: intermediate manifests have no file hashes; force a final snapshot.

    Standalone stages remain eager. The builder retains its initial inventory for
    legacy stages that discover that map, then writes a complete final inventory.
    """
    token = _deferred_root.set(Path(out).resolve())
    try:
        yield
    finally:
        _deferred_root.reset(token)


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshot_files(out, *, force=False):
    out = Path(out)
    if not force and _deferred_root.get() == out.resolve():
        return {}
    return {path.relative_to(out).as_posix(): sha256_file(path)
            for path in out.rglob('*')
            if path.is_file() and path.name != 'build_manifest.json'}


def write_preserving_format(path, text):
    path = Path(path)
    previous = path.read_bytes() if path.exists() else b''
    newline = '\r\n' if b'\r\n' in previous else '\n'
    encoding = 'utf-8-sig' if previous.startswith(b'\xef\xbb\xbf') else 'utf-8'
    content = text.replace('\n', newline).encode(encoding)
    if path.exists() and content == previous:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
