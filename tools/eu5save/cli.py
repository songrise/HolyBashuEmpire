"""Reusable semantic commands; large save files are projected once then cached."""
import argparse,glob,json,sys,time
from pathlib import Path
from .cache import load_snapshot
from .hbe import project_summary,anomalies
from .errors import SaveError


def select(data,fields):
    if not fields:return data
    result={}
    for field in fields.split(','):
        value=data
        for key in field.strip().split('.'):
            if not isinstance(value,dict) or key not in value:value=None;break
            value=value[key]
        result[field.strip()]=value
    return result


def main(argv=None):
    root=Path(__file__).resolve().parents[2]
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest',type=Path,default=root/'mod/holy_bashu_empire/build_manifest.json')
    ap.add_argument('--catalogue',type=Path,default=root/'data/local_affairs_projects.json')
    ap.add_argument('--cache',type=Path,default=root/'work/save-cache')
    ap.add_argument('--no-cache',action='store_true');ap.add_argument('--refresh',action='store_true')
    ap.add_argument('--output',type=Path)
    commands=ap.add_subparsers(dest='command',required=True)
    for name in ['summary','snapshot','projects','check']:
        p=commands.add_parser(name);p.add_argument('save',type=Path)
    p=commands.add_parser('country');p.add_argument('save',type=Path);p.add_argument('tag');p.add_argument('--alive',action='store_true');p.add_argument('--id',type=int);p.add_argument('--fields')
    p=commands.add_parser('timeline');p.add_argument('saves',nargs='+');p.add_argument('--allow-mixed',action='store_true')
    args=ap.parse_args(argv)
    def load(path):
        return load_snapshot(path,manifest=args.manifest,cache_dir=None if args.no_cache else args.cache,refresh=args.refresh)
    try:
        start=time.perf_counter();cache_info=[]
        if args.command=='timeline':
            paths=[]
            for pattern in args.saves:
                matches=glob.glob(pattern)
                if not matches:raise SaveError('No save matches '+pattern)
                paths.extend(Path(p).resolve() for p in matches)
            rows=[];runs=set()
            for path in dict.fromkeys(paths):
                data,cache=load(path);cache_info.append(cache);runs.add(data['playthrough_id'])
                if data['date'] is None:raise SaveError('Timeline requires a game date: '+str(path))
                rows.append(dict(date=data['date'],playthrough_id=data['playthrough_id'],save=str(path),**data['summary']))
            if not args.allow_mixed and (len(runs)!=1 or None in runs):raise SaveError('Timeline requires one known playthrough; use --allow-mixed explicitly')
            rows.sort(key=lambda r:tuple(map(int,r['date'].split('.'))) if r['date'] else (0,0,0))
            result=rows
        else:
            data,cache=load(args.save);cache_info.append(cache)
            if args.command=='snapshot':result=data
            elif args.command=='summary':result=dict(date=data['date'],playthrough_id=data['playthrough_id'],summary=data['summary'],goods_production=data['goods_production'])
            elif args.command=='check':result=dict(date=data['date'],anomalies=anomalies(data),scope='Parsed state checks only; not a runtime log audit')
            elif args.command=='projects':
                catalogue=json.loads(args.catalogue.read_text(encoding='utf-8-sig'))
                result=dict(date=data['date'],**project_summary(data,catalogue))
            else:
                found=[r for r in data['countries'] if r['tag'].casefold()==args.tag.casefold() and (not args.alive or r['alive']) and (args.id is None or r['id']==args.id)]
                if not found:raise SaveError('Country not found in projection: '+args.tag)
                result=[select(r,args.fields) for r in found]
        payload=dict(result=result,cache=cache_info,elapsed_seconds=round(time.perf_counter()-start,4))
        text=json.dumps(payload,ensure_ascii=False,indent=2)+'\n'
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(text,encoding='utf-8')
            print(str(args.output))
        else:print(text,end='')
        return 0
    except (SaveError,OSError,ValueError) as exc:
        print(json.dumps(dict(error=type(exc).__name__,message=str(exc)),ensure_ascii=False),file=sys.stderr)
        return 2


if __name__=='__main__':raise SystemExit(main())
