"""Read-only byte sources: mmap text saves and bounded text ZIP members."""
from pathlib import Path
import mmap
import re
import zipfile
from .errors import UnsupportedFormat, SourceChanged, SaveSyntaxError


class SaveSource:
    def __init__(self, path, *, max_bytes=2*1024**3):
        self.path = Path(path).resolve()
        self.file = None
        self.data = None
        self.zip_metadata = None
        self.closed = False
        self.signature = self._signature()
        if self.signature[0] == 0:
            raise SaveSyntaxError('Empty save', 0)
        if self.signature[0] > max_bytes:
            raise UnsupportedFormat('Save exceeds configured size limit')
        try:
            if zipfile.is_zipfile(self.path):
                with zipfile.ZipFile(self.path) as archive:
                    names = archive.namelist()
                    candidates = [n for n in names if n in ('gamestate', 'game_state')]
                    if len(candidates) != 1 or names.count(candidates[0]) != 1:
                        raise UnsupportedFormat('ZIP must contain one unambiguous gamestate member')
                    info = archive.getinfo(candidates[0])
                    if info.file_size > max_bytes or info.flag_bits & 1:
                        raise UnsupportedFormat('Oversized or encrypted gamestate')
                    self.data = archive.read(info)
                    if 'meta' in names:
                        meta = archive.getinfo('meta')
                        if meta.file_size > 1024**2 or names.count('meta') != 1:
                            raise UnsupportedFormat('Invalid ZIP metadata member')
                        self.zip_metadata = archive.read(meta)
                self.format = 'zip-text'
            else:
                self.file = self.path.open('rb')
                self.data = mmap.mmap(self.file.fileno(), 0, access=mmap.ACCESS_READ)
                self.format = 'text'
            self.start = self._text_start(self.data)
            self.assert_unchanged()
        except (zipfile.BadZipFile,NotImplementedError,RuntimeError) as exc:
            self.close()
            raise UnsupportedFormat('ZIP body cannot be read safely: '+str(exc)) from exc
        except BaseException:
            self.close()
            raise

    @staticmethod
    def _text_start(data):
        start = 3 if data[:3] == b'\xef\xbb\xbf' else 0
        if data[start:start+3] == b'SAV':
            line = re.search(rb'\r\n|\r|\n',data[start:min(len(data),start+128)])
            if line is None:
                raise UnsupportedFormat('SAV header has no text body; binary saves require text export')
            start += line.end()
        sample = data[start:min(len(data),start+65536)]
        if b'\0' in sample or any(x < 9 or 13 < x < 32 for x in sample):
            raise UnsupportedFormat('Binary save body is not supported; use -force_text_save')
        return start

    @classmethod
    def from_bytes(cls, data):
        if not data:raise SaveSyntaxError('Empty save',0)
        obj = cls.__new__(cls)
        obj.path = None; obj.file = None; obj.data = bytes(data)
        obj.signature = None; obj.closed = False; obj.zip_metadata = None; obj.format = 'memory-text'
        obj.start = obj._text_start(obj.data)
        return obj

    def _signature(self):
        stat = self.path.stat()
        return stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns

    def assert_unchanged(self):
        if self.path and self._signature() != self.signature:
            raise SourceChanged('Save changed while being read: '+str(self.path))

    def close(self):
        if self.closed: return
        self.closed = True
        if isinstance(self.data,mmap.mmap): self.data.close()
        if self.file: self.file.close()

    def __enter__(self): return self
    def __exit__(self,*args): self.close()
