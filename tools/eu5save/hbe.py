"""HBE semantic projection. Country and project names come from supplied data."""
from collections import Counter
import statistics
from .eu5 import EU5Save
from .errors import SchemaError


def snapshot(game,manifest):
    meta={c['tag']:c for c in manifest.get('countries',[])}
    orgs=[o for o in game.organizations() if (o['type'] or '').startswith('hbe_')]
    members=set(i for o in orgs if o['type']=='hbe_empire' for i in o['members'])
    tags=game.tags
    selected={i for i,t in tags.items() if t in meta}|members
    # A missing native tag table is supported without a hard-coded tag fallback.
    rows=list(game.countries(selected if tags else None))
    if not tags:rows=[r for r in rows if r['tag'] in meta or r['id'] in members or 'hbe_af_initialized' in r['variables']]
    chars=game.records('character_db')
    for r in rows:
        r.update(name=meta.get(r['tag'],{}).get('name',r['tag']),region=meta.get(r['tag'],{}).get('region'),
                 member=r['id'] in members,alive=r['locations']>0,
                 valid_head=r['ruler'] in chars or r['regent'] in chars)
        v=r['variables']
        r['affairs']=dict(completed=v.get('hbe_af_completed',0),active=v.get('hbe_af_active'),
             tier=v.get('hbe_af_tier'),elapsed=v.get('hbe_af_elapsed'),months=v.get('hbe_af_months'),
             pause=v.get('hbe_af_pause',0),budget=v.get('hbe_af_budget'),spent=v.get('hbe_af_spent'),
             reserve=v.get('hbe_af_reserve'),burden_limit=v.get('hbe_af_limit'),
             national_offer=v.get('hbe_af_national'),local_offer=v.get('hbe_af_local'),
             personality=v.get('hbe_af_ai_personality'))
    live=[r for r in rows if r['alive']];totals=Counter()
    for r in rows:
        totals.update({k:v for k,v in r['variables'].items() if k.startswith('hbe_probe_') and isinstance(v,(float,int)) and not isinstance(v,bool)})
    def values(key):return [r[key] for r in live if r[key] is not None]
    burden=[r['variables']['hbe_burden'] for r in live if 'hbe_burden' in r['variables']]
    buildings=list(game.buildings('hbe_'));units=list(game.units('hbe_'))
    ids={r['id'] for r in rows};wars=[w for w in game.wars() if ids.intersection(w['participants'])]
    summary=dict(alive=len(live),members=sum(r['alive'] and r['member'] for r in rows),
        locations=sum(r['locations'] for r in live),gold_median=statistics.median(values('gold')) if values('gold') else None,
        gold_total=sum(values('gold')),population_total=sum(values('population')),
        burden_mean=statistics.mean(burden) if burden else None,burden_max=max(burden) if burden else None,
        completed_all=sum(r['affairs']['completed'] for r in rows),completed_live=sum(r['affairs']['completed'] for r in live),
        active=sum(bool(r['affairs']['active']) for r in live),paused=sum(bool(r['affairs']['active']) and r['affairs']['pause']>0 for r in live),
        missing_government_heads=[r['tag'] for r in live if not r['valid_head']],
        building_levels=sum(b['level'] for b in buildings),buildings=len(buildings),
        operating_buildings=sum(b['employed']>0 for b in buildings),special_units=len(units),wars=len(wars))
    goods=game.goods('hbe_');manager=game.root.block('market_manager')
    goods_available=manager is not None and manager.block('produced_goods') is not None
    if goods_available:
        for item in manifest.get('special_goods',{}).get('goods',[]):goods.setdefault(item['key'],0)
    return dict(schema_version=1,profile='hbe',**game.metadata,countries=rows,summary=summary,
        organizations=orgs,buildings=buildings,units=units,wars=wars,goods_production=goods,goods_available=goods_available,counters=dict(totals),
        scope='Current HBE members plus manifest principalities (including retained extinct records). Stock/flow population units are native thousands; HBE actual population reward counters are persons.')


def project_summary(data,catalogue=None):
    c=data.get('counters',{});rows=[]
    for p in (catalogue or {}).get('projects',[]):
        pid=p['id'];row=dict(id=pid,name=p.get('name',p.get('key')),pool=p.get('pool'))
        for action in ['starts','completed']:
            for tier in ['small','large']:row[action+'_'+tier]=c.get(f'hbe_probe_{action}_p{pid}_{tier}')
        rows.append(row)
    personalities={}
    configured=(catalogue or {}).get('ai_participation',{}).get('personalities',[])
    definitions=[(p['key'],p['chance']/100) for p in configured] or [('active',None),('cautious',None)]
    for label,chance in definitions:
        n=c.get('hbe_probe_eligible_'+label);hits=c.get('hbe_probe_accepted_'+label)
        personalities[label]=dict(eligible=n,accepted=hits,rate=hits/n if n and hits is not None else None,configured_rate=chance)
    return dict(telemetry_available=bool(c),projects=rows,personalities=personalities,
        note='Missing passive counters are null, not evidence of zero projects. Historical totals can be affected by deleted or recreated countries.')


def anomalies(data):
    problems=[]
    for r in data['countries']:
        if not r['alive']:continue
        v=r['variables'];a=r['affairs'];prefix=f'{r["tag"]}#{r["id"]}'
        if 'hbe_burden' in v and not 0<=v['hbe_burden']<=100:problems.append(prefix+': burden outside 0–100')
        if not r['valid_head']:problems.append(prefix+': no valid ruler or regent')
        if a['active'] and a['elapsed'] is not None and a['months'] is not None and a['elapsed']>a['months']:problems.append(prefix+': overdue project')
        if a['active'] and a['pause']>=12:problems.append(prefix+': long pause not cancelled')
        if 'hbe_probe_starts' in v:
            expected=v.get('hbe_probe_completed',0)+v.get('hbe_probe_cancelled',0)+int(bool(a['active']))
            if v['hbe_probe_starts']!=expected:problems.append(prefix+': starts do not reconcile')
            if v.get('hbe_probe_completed',0)!=a['completed']:problems.append(prefix+': completed counters differ')
    return problems
