"""Shared byte-preserving I/O for build stages; no feature or game rules."""
from pathlib import Path
import hashlib


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def snapshot_files(out):
    out = Path(out)
    return {path.relative_to(out).as_posix(): sha256_file(path)
            for path in out.rglob('*')
            if path.is_file() and path.name != 'build_manifest.json'}


def write_preserving_format(path, text):
    path = Path(path)
    previous = path.read_bytes() if path.exists() else b''
    newline = '\r\n' if b'\r\n' in previous else '\n'
    encoding = 'utf-8-sig' if previous.startswith(b'\xef\xbb\xbf') else 'utf-8'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding=encoding, newline=newline)
