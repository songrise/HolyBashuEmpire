"""Replace flat event prices with the vanilla economic-base scaling formula."""
from pathlib import Path
from decimal import Decimal
import json,re
from pdxscript import blocks,apply_edits

def scale_for(original):
    v=Decimal(original)
    return '1' if v<=2 else '1.5' if v<=4 else '2' if v<=6 else '3'

def apply(out,report):
    out=Path(out); costs={r['option']:r for r in report['costs']}
    assert all(len(r['payments'])==1 for r in costs.values())
    used=set(); changed=[]
    for p in (out/'in_game/events').glob('hbe*.txt'):
        t=p.read_text(encoding='utf-8-sig'); edits=[]
        for event,_,s,e,_ in blocks(t,0):
            if '.' not in event:continue
            body=t[s:e];oe=[]
            for _,_,a,z,_ in [b for b in blocks(body,0) if b[0]=='option']:
                opt=body[a:z];m=re.search(r'\bname\s*=\s*(\S+)',opt)
                if not m or m[1] not in costs:continue
                key=m[1]; row=costs[key]; scale=scale_for(row['payments'][0][0]);sv='hbe_event_cost_'+scale.replace('.','_')
                assert len(re.findall(r'\badd_gold\s*=\s*-\d+(?:\.\d+)?',opt))==1,key
                opt=re.sub(r'\badd_gold\s*=\s*-\d+(?:\.\d+)?','add_gold = { value = '+sv+' multiply = -1 }',opt)
                trigger=next(b for b in blocks(opt,0) if b[0]=='trigger')
                tr=opt[trigger[2]:trigger[3]]
                tr,n=re.subn(r'\bgold\s*>=\s*\d+(?:\.\d+)?','gold >= '+sv,tr)
                assert n==1,key
                opt=apply_edits(opt,[(trigger[2],trigger[3],tr)])
                oe.append((a,z,opt));used.add(key)
                row.update(cost_model='vanilla economic-base scaling',scale=scale,value=sv,minimum_gold=sv)
                row['superseded_flat_price']=row['payments'][0][1]
                row['payments']=[[row['payments'][0][0],sv]]
            if oe:edits.append((s,e,apply_edits(body,oe)))
        if edits:p.write_text(apply_edits(t,edits),encoding='utf-8-sig');changed.append(p.relative_to(out).as_posix())
    assert used==set(costs),sorted(set(costs)-used)
    values='# Same economic scaling and bounds as vanilla scaled_gold_for_effect.\n'
    values+='hbe_event_economic_base = { value = 1 add = { value = capital_wealth multiply = 0.2 } add = { value = country_economical_base multiply = 0.05 } }\n'
    for scale in ('1','1.5','2','3'):
        name='hbe_event_cost_'+scale.replace('.','_')
        values+=f'{name} = {{ value = hbe_event_economic_base multiply = {scale} min = {scale} max = {{ value = 5000 multiply = {scale} }} }}\n'
    p=out/'in_game/common/script_values/hbe_event_costs.txt';p.write_text(values,encoding='utf-8-sig');changed.append(p.relative_to(out).as_posix())
    for p in (out/'main_menu/localization').rglob('hbe*.yml'):
        t=p.read_text(encoding='utf-8-sig');old=t
        def label(m):
            if m[1] not in costs:return m[0]
            line=re.sub(r'(?:\d+(?:\.\d+)?|[零一二三四五六七八九十百两]+)\s*(?:金币|金)','款项',m[0])
            line=re.sub(r'(?:\d+(?:\.\d+)?|[零一二三四五六七八九十百两]+)\s*(?:金币|金)(?=[，。；：、,.;\s])','款项',line)
            line=re.sub(r'\b\d+(?:\.\d+)?\s+(?:gold|ducats)\b','funds',line,flags=re.I)
            line=line.replace('出款项','拨款').replace('拿拨款','拿出款项')
            return line
        t=re.sub(r'(?m)^ (\S+):[^\n]*$',label,t)
        if t!=old:p.write_text(t,encoding='utf-8-sig');changed.append(p.relative_to(out).as_posix())
    report['cost_formula']='scale * (1 + 0.2 * capital_wealth + 0.05 * country_economical_base), bounded to [scale, 5000 * scale]'
    report['cost_tiers']={'original <= 2':'1','original 3-4':'1.5','original 5-6':'2','original 7-10':'3'}
    report['files']=sorted(set(report.get('files',[])+changed))
    return report
