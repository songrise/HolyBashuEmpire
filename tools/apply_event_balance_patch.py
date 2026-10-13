"""Scale event rewards, raise real costs, synchronize affordability and copy."""
from pathlib import Path
from decimal import Decimal,ROUND_HALF_UP,ROUND_CEILING
import re,json,hashlib,sys
from pdxscript import blocks,apply_edits
from event_resource_balance import adjust
GAME=Path('D:/SteamLibrary/steamapps/common/Europa Universalis V/game')
D=Decimal
def fmt(v):return f'{v.normalize():f}'
def rounded_reward(v,percent=False):
    # Display ordinary percentages in whole points; preserve genuinely small
    # rates such as monthly literacy/interest rather than rounding them to zero.
    quantum=D('.01') if percent and abs(v)>=D('.01') and abs(v)<1 else D('1') if abs(v)>=1 else D('.001')
    return (v*D('.7')).quantize(quantum,rounding=ROUND_HALF_UP)
def money_cost(v):return max(D(10),(v*4/D(10)).quantize(D(1),rounding=ROUND_HALF_UP)*10)
def other_cost(v):return (v*D('1.5')).quantize(D(1) if v>=1 else D('.01'),rounding=ROUND_CEILING)
def cn(n):
    n=int(n);s='零一二三四五六七八九'
    if n<10:return s[n]
    if n<100:return (s[n//10] if n>=20 else '')+'十'+(s[n%10] if n%10 else '')
    return str(n)

def apply(out,root):
    out,root=Path(out),Path(root);report=dict(version='0.3.1',factor=.7,costs=[],reward_modifiers=[],immediate_rewards=[],files=[])
    definitions={}
    for folder in (GAME/'main_menu/common/modifier_type_definitions',out/'main_menu/common/modifier_type_definitions'):
        for p in folder.glob('*.txt'):
            t=p.read_text(encoding='utf-8-sig')
            for key,_,s,e,_ in blocks(t,0):definitions[key]=t[s:e]
    effect_bodies={}
    for p in (out/'in_game/common/scripted_effects').glob('hbe*.txt'):
        t=p.read_text(encoding='utf-8-sig')
        for key,_,s,e,_ in blocks(t,0):effect_bodies[key]=t[s:e]
    event_paths=list((out/'in_game/events').glob('hbe*.txt'));source='\n'.join(p.read_text(encoding='utf-8-sig') for p in event_paths)
    reached=set();pending=set(re.findall(r'\b(hbe_\w+)\s*=',source))&set(effect_bodies)
    while pending:
        key=pending.pop()
        if key in reached:continue
        reached.add(key);pending.update((set(re.findall(r'\b(hbe_\w+)\s*=',effect_bodies[key]))&set(effect_bodies))-reached)
    all_effects=source+'\n'+'\n'.join(effect_bodies[k] for k in reached)
    reward_modifiers=set(re.findall(r'\b(?:add_country_modifier|add_location_modifier)\s*=\s*\{\s*modifier\s*=\s*(hbe_\w+)',all_effects))
    for p in (out/'main_menu/common/static_modifiers').glob('hbe*.txt'):
        t=p.read_text(encoding='utf-8-sig');edits=[]
        for key,_,s,e,_ in blocks(t,0):
            if key not in reward_modifiers:continue
            body=t[s:e];changes=[]
            def scale(m):
                name=m[1];value=D(m[2]);definition=definitions.get(name,'');bad=bool(re.search(r'color\s*=\s*bad',definition))
                beneficial=value<0 if bad else value>0
                if not beneficial:return m[0]
                percent=bool(re.search(r'percent\s*=\s*yes',definition))
                new=rounded_reward(value,percent);changes.append(dict(type=name,before=fmt(value),after=fmt(new)))
                return f'{name} = {fmt(new)}'
            new=re.sub(r'\b(\w+)\s*=\s*(-?\d+(?:\.\d+)?)',scale,body)
            if changes:edits.append((s,e,new));report['reward_modifiers'].append(dict(modifier=key,changes=changes))
        if edits:p.write_text(apply_edits(t,edits),encoding='utf-8-sig');report['files'].append(p.relative_to(out).as_posix())
    label_costs={}
    for p in event_paths:
        t=p.read_text(encoding='utf-8-sig');edits=[]
        for event,_,s,e,_ in blocks(t,0):
            if '.' not in event:continue
            body=t[s:e];oe=[]
            for _,_,a,z,_ in (b for b in blocks(body,0) if b[0]=='option'):
                opt=body[a:z];name=re.search(r'\bname\s*=\s*(\S+)',opt)[1];old=opt
                payments=list(re.finditer(r'\badd_gold\s*=\s*-(\d+(?:\.\d+)?)',opt));pairs=[]
                total=D(0)
                for m in payments:pairs.append((D(m[1]),money_cost(D(m[1]))));total+=money_cost(D(m[1]))
                # These are explicit flat costs. Nested conditional payments are
                # still individually scaled, while the paid option requires the
                # full possible total, preventing an unaffordable choice.
                opt=re.sub(r'\badd_gold\s*=\s*-(\d+(?:\.\d+)?)',lambda m:'add_gold = -'+fmt(money_cost(D(m[1]))),opt)
                if total:
                    trigger=next((b for b in blocks(opt,0) if b[0]=='trigger'),None)
                    if trigger:
                        tr=opt[trigger[2]:trigger[3]];tr=re.sub(r'\bgold\s*>=\s*\d+(?:\.\d+)?','gold >= '+fmt(total),tr)
                        if not re.search(r'\bgold\s*>=',tr):tr+=' gold >= '+fmt(total)+' '
                        opt=apply_edits(opt,[(trigger[2],trigger[3],tr)])
                    else:opt+=' trigger = { gold >= '+fmt(total)+' } '
                    label_costs[name]=pairs;report['costs'].append(dict(option=name,payments=[(fmt(x),fmt(y)) for x,y in pairs],minimum_gold=fmt(total)))
                def resource(m):
                    kind,value=m[1],D(m[2]);new=rounded_reward(value) if value>0 else -other_cost(-value) if value<0 else value
                    report['immediate_rewards'].append(dict(option=name,type=kind,before=fmt(value),after=fmt(new)))
                    return kind+' = '+fmt(new)
                opt=re.sub(r'\b(add_prestige|add_stability|add_legitimacy|add_research_progress|add_gold)\s*=\s*(-?\d+(?:\.\d+)?)',lambda m:m[0] if m[1]=='add_gold' and D(m[2])<0 else resource(m),opt)
                # Native estate satisfaction is a fraction. Preserve penalties,
                # reduce beneficial rewards to whole percentage points.
                for block in reversed([b for b in blocks(opt) if b[0]=='add_estate_satisfaction']):
                    b=opt[block[2]:block[3]]
                    b=re.sub(r'\bvalue\s*=\s*(\d+(?:\.\d+)?)',lambda m:'value = '+fmt(rounded_reward(D(m[1]),True)),b)
                    opt=apply_edits(opt,[(block[2],block[3],b)])
                opt, special_changes = adjust(opt)
                if opt!=old:oe.append((a,z,opt))
            if oe:edits.append((s,e,apply_edits(body,oe)))
        if edits:p.write_text(apply_edits(t,edits),encoding='utf-8-sig');report['files'].append(p.relative_to(out).as_posix())
    # Keep authored option labels and explicit explanatory costs accurate.
    for folder in (out/'main_menu/localization').iterdir():
        if not folder.is_dir():continue
        for p in folder.glob('hbe*.yml'):
            t=p.read_text(encoding='utf-8-sig');original=t
            for key,pairs in label_costs.items():
                pattern=r'(?m)^( '+re.escape(key)+r':\s*"[^\n]*)$'
                def update(m):
                    text=m[0]
                    for old,new in pairs:
                        o,n=fmt(old),fmt(new)
                        text=re.sub(r'(?<!\d)'+re.escape(o)+r'(?=\s*(?:金币|金|gold|ducats))',n,text)
                        text=re.sub(r'(?<![零一二三四五六七八九十百])'+re.escape(cn(old))+r'(?=金)',cn(new),text)
                        if old==2:text=text.replace('两金',cn(new)+'金')
                    return text
                t=re.sub(pattern,update,t)
            if t!=original:p.write_text(t,encoding='utf-8-sig');report['files'].append(p.relative_to(out).as_posix())
    from dynamic_event_costs import apply as apply_dynamic_costs
    return apply_dynamic_costs(out, report)

if __name__=='__main__':
    root=Path(sys.argv[1]);out=root/'mod/holy_bashu_empire';r=apply(out,root)
    (root/'docs/testing/event-balance-patch-v031.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    p=out/'build_manifest.json';m=json.loads(p.read_text(encoding='utf-8-sig'));m['event_balance_patch']=r;m['files']={p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and p.name!='build_manifest.json'};p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(modifiers=len(r['reward_modifiers']),paid_options=len(r['costs']),resources=len(r['immediate_rewards'])),ensure_ascii=False))
