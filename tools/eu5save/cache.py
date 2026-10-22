"""Versioned semantic cache; invalidate by source identity and adapter inputs."""
from pathlib import Path
import hashlib,json,os,tempfile
from .eu5 import EU5Save
from .hbe import snapshot
from .errors import SourceChanged

CACHE_VERSION=2


def identity(path):
    p=Path(path).resolve();s=p.stat()
    return dict(path=str(p),size=s.st_size,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)


def load_snapshot(path,*,manifest=None,cache_dir=None,refresh=False):
    manifest_path=Path(manifest).resolve() if manifest else None
    meta=json.loads(manifest_path.read_text(encoding='utf-8-sig')) if manifest_path else {}
    signature=dict(cache_version=CACHE_VERSION,adapter='hbe:1',source=identity(path),manifest=identity(manifest_path) if manifest_path else None)
    cache=None
    if cache_dir:
        root=Path(cache_dir);root.mkdir(parents=True,exist_ok=True)
        # Hash the identity only, not hundreds of MB of save bytes on every query.
        key=hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest()
        cache=root/(key+'.json')
        if cache.exists() and not refresh:
            try:
                stored=json.loads(cache.read_text(encoding='utf-8'))
                value=stored.get('snapshot') if isinstance(stored,dict) else None
                if (isinstance(stored,dict) and stored.get('identity')==signature and isinstance(value,dict)
                    and value.get('schema_version')==1 and value.get('profile')=='hbe'
                    and isinstance(value.get('countries'),list) and isinstance(value.get('summary'),dict)):
                    return stored['snapshot'],dict(hit=True,path=str(cache))
            except (OSError,ValueError):
                pass # A corrupt cache is disposable; parsing failures themselves propagate.
    with EU5Save(path) as game:
        result=snapshot(game,meta);game.source.assert_unchanged()
    if identity(path)!=signature['source']:raise SourceChanged('Save changed before cache commit')
    if manifest_path and identity(manifest_path)!=signature['manifest']:raise SourceChanged('Manifest changed during projection')
    if cache:
        name=None
        try:
            with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=cache.parent,delete=False) as f:
                name=f.name;json.dump(dict(identity=signature,snapshot=result),f,ensure_ascii=False,separators=(',',':'))
            os.replace(name,cache);name=None
        finally:
            if name:Path(name).unlink(missing_ok=True)
    return result,dict(hit=False,path=str(cache) if cache else None)
