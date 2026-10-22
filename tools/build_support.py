"""Shared byte-preserving I/O for build stages; no feature or game rules."""
from pathlib import Path
import hashlib
from contextlib import contextmanager
from contextvars import ContextVar
from io import BytesIO
import os
import tempfile


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


def normalize_text_newlines(out):
    """Write generated text as LF so a rebuild never inherits the target's history.

    `write_preserving_format` keeps whatever newline the existing file had, so an
    incremental build produced CRLF while a clean build produced LF. Normalising the
    whole tree after the last stage makes both paths byte-identical.
    """
    out = Path(out)
    changed = 0
    for path in out.rglob('*'):
        if not path.is_file() or path.suffix not in ('.txt', '.yml', '.gui'):
            continue
        data = path.read_bytes()
        if b'\r\n' not in data:
            continue
        path.write_bytes(data.replace(b'\r\n', b'\n'))
        changed += 1
    return changed


def save_png(path, image):
    """Keep Pillow's PNG bytes, skip equal content, replace through a closed temporary file.

    Reopening a recently read PNG with Pillow's w+b mode can fail on Windows.
    The destination is never truncated if encoding or replacement fails.
    """
    path = Path(path)
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    content = buffer.getvalue()
    if path.exists() and path.read_bytes() == content:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.stem+'-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
