"""Build a complete distribution; compress eligible DDS without pruning any file."""
from __future__ import annotations
import argparse
from concurrent.futures import Future, ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
from threading import Lock


def digest(data):
    return hashlib.sha256(data).hexdigest()


def dds_layout(data):
    if len(data) < 128 or data[:4] != b'DDS ':
        return None
    height, width = struct.unpack_from('<II', data, 12)
    return dict(width=width, height=height, mips=struct.unpack_from('<I', data, 28)[0],
                fourcc=data[84:88], bits=struct.unpack_from('<I', data, 88)[0],
                masks=data[92:108])


def compress_dds(source, raw, texconv):
    """Fail closed to original bytes on unsupported layout or quality regression."""
    before = dds_layout(raw)
    eligible = (before and before['fourcc'] == b'\0'*4 and before['bits'] == 32
                and before['mips'] in (0, 1) and min(before['width'], before['height']) >= 4
                and before['masks'] == bytes.fromhex('0000ff0000ff0000ff000000000000ff'))
    if not eligible:
        return raw, dict(mode='original', reason='already compressed or unsupported layout')
    if not texconv or not Path(texconv).is_file():
        raise FileNotFoundError('Eligible DDS requires --texconv; no partial publication is allowed')
    from PIL import Image
    import numpy as np
    with tempfile.TemporaryDirectory(prefix='hbe-bc3-') as tmp:
        result = subprocess.run([str(texconv), '-nologo', '-f', 'BC3_UNORM', '-dx9',
                                 '-m', '1', '-nogpu', '--single-proc', '-y', '-o', tmp, str(source)],
                                capture_output=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        candidate = Path(tmp)/source.name
        if result.returncode or not candidate.exists():
            return raw, dict(mode='original', reason='encoder failed; source retained')
        encoded = candidate.read_bytes(); after = dds_layout(encoded)
        if (not after or after['fourcc'] != b'DXT5' or
                (after['width'], after['height']) != (before['width'], before['height'])):
            return raw, dict(mode='original', reason='encoded DDS header mismatch')
        with Image.open(source) as a, Image.open(candidate) as b:
            original = np.asarray(a.convert('RGBA'), dtype=np.int16)
            compressed = np.asarray(b.convert('RGBA'), dtype=np.int16)
        if original.shape != compressed.shape:
            return raw, dict(mode='original', reason='decoded dimensions differ')
        visible = original[:, :, 3] > 127
        rgb = float(np.abs(original[:, :, :3]-compressed[:, :, :3])[visible].mean()) if visible.any() else 0
        alpha = float(np.abs(original[:, :, 3]-compressed[:, :, 3]).mean())
        quality = dict(rgb_mae=rgb, alpha_mae=alpha)
        if rgb > 6 or alpha > 1.5 or len(encoded) >= len(raw):
            return raw, dict(mode='original', reason='quality or size guard', **quality)
        return encoded, dict(mode='BC3', **quality)


def build(source, output, *, texconv=None, workers=2):
    source, output = Path(source).resolve(), Path(output).resolve()
    if not source.is_dir(): raise FileNotFoundError(source)
    if output.exists(): raise FileExistsError('Never overwrite an existing package: '+str(output))
    if output == source or source in output.parents or output in source.parents:
        raise ValueError('Source and output must be independent directories')
    inventory = {p.relative_to(source).as_posix(): p for p in source.rglob('*') if p.is_file()}
    if not inventory: raise ValueError('Empty mod source')
    output.mkdir(parents=True)
    cache, lock = {}, Lock()
    def export(item):
        rel, p = item; stat = p.stat(); raw = p.read_bytes(); fingerprint = digest(raw)
        mode = dict(mode='original', reason='non-DDS')
        data = raw
        if p.suffix.lower() == '.dds':
            with lock:
                future = cache.get(fingerprint)
                owner = future is None
                if owner: future = Future(); cache[fingerprint] = future
            if owner:
                try: future.set_result(compress_dds(p, raw, texconv))
                except BaseException as exc: future.set_exception(exc); raise
            data, mode = future.result()
        final_stat = p.stat()
        if (stat.st_size, stat.st_mtime_ns) != (final_stat.st_size, final_stat.st_mtime_ns):
            raise RuntimeError('Source changed during packaging: '+rel)
        dest = output/rel; dest.parent.mkdir(parents=True, exist_ok=True); dest.write_bytes(data)
        return dict(path=rel, source_bytes=len(raw), bytes=len(data), source_sha256=fingerprint,
                    sha256=digest(data), **mode)
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        rows = list(pool.map(export, inventory.items()))
    # Keep the manifest path and all game metadata; update only distribution hashes.
    manifest = output/'build_manifest.json'
    if manifest.exists():
        doc = json.loads(manifest.read_text(encoding='utf-8-sig'))
        doc['files'] = {r['path']:r['sha256'] for r in rows if r['path'] != 'build_manifest.json'}
        doc['distribution_compaction'] = dict(strategy='all_files_preserved_bc3',
            source_manifest_sha256=next(r['source_sha256'] for r in rows if r['path']=='build_manifest.json'),
            compressed=sum(r['mode']=='BC3' for r in rows),rgb_mae_limit=6,alpha_mae_limit=1.5)
        manifest.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        row = next(r for r in rows if r['path']=='build_manifest.json')
        row.update(bytes=manifest.stat().st_size, sha256=digest(manifest.read_bytes()),
                   mode='distribution_manifest',reason='updated hashes; source manifest provenance retained')
    actual = {p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()}
    if actual != set(inventory): raise AssertionError('Package file inventory differs from source')
    return dict(strategy='complete_inventory_bc3',payload=str(output),source=str(source),
                source_bytes=sum(r['source_bytes'] for r in rows),payload_bytes=sum(r['bytes'] for r in rows),
                file_count=len(rows),files_preserved=True,compressed=sum(r['mode']=='BC3' for r in rows),
                quality_retained=sum(r.get('reason')=='quality or size guard' for r in rows),files=rows)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--texconv',type=Path);ap.add_argument('--workers',type=int,default=2)
    ap.add_argument('--report',type=Path,required=True);args=ap.parse_args()
    report=build(args.source,args.output,texconv=args.texconv,workers=args.workers)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='files'},ensure_ascii=False),flush=True)


if __name__=='__main__':main()
