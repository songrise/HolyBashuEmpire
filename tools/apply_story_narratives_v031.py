"""Recollect the actual prior choice, then describe a distinct present conflict."""
from pathlib import Path
import argparse,hashlib,json,re,sys
from pdxscript import blocks,apply_edits

def apply(out,root,game=None):
    out,root=Path(out),Path(root)
    sys.path[:0]=[str(root/'data'),str(root/'tools')]
    from story_narratives_v031 import RECAPS,SHORT_DETAILS,LONG_FIXES,ENDING_DETAILS,CURRENT_OVERRIDES
    from story_blueprints import LONG
    from short_stories import SHORT
    from shared_stories import SHORT as SHARED
    from migration_stories import CHAPTERS,OFFSETS
    from build_playable_stories import END_PROSE
    from history_guides_v031 import ANCHORS
    files={};texts={};rows=[];chains=[];tracked=0
    for lang in ('simp_chinese','english'):
        p=out/f'main_menu/localization/{lang}/hbe_story_l_{lang}.yml'
        texts[lang]={m[1]:json.loads(m[2]) for line in p.read_text(encoding='utf-8-sig').splitlines() if (m:=re.match(r'\s*(\S+):\s*(".*")$',line))}
    def load(rel):
        if rel not in files:files[rel]=(out/rel).read_text(encoding='utf-8-sig')
        return files[rel]
    def event(rel,eid,fn):
        t=load(rel);b,e=next((b,e) for k,_,b,e,_ in blocks(t,0) if k==eid)
        files[rel]=t[:b]+fn(t[b:e])+t[e:]
    def fix(t):
        for old,new in LONG_FIXES.items():t=t.replace(old,new)
        return t
    def decorate(key,t):
        for family,target,phrase,concept in ANCHORS:
            if family!='story' or target!=key:continue
            cid=concept if concept.startswith('hbe_history_') else 'hbe_history_'+concept
            link=f"[Concept('{cid}', '{phrase}')|e]"
            if link in t:continue
            parts=re.split(r'(\[[^\]]*\])',t)
            for i,part in enumerate(parts):
                if not part.startswith('[') and phrase in part:
                    parts[i]=part.replace(phrase,link,1);break
            t=''.join(parts)
        return t
    def L(key,value,base=None):
        value=decorate(base or key,fix(value))
        for loc in texts.values():loc[key]=value
    def replace_desc(body,desc):
        span=next(((a,z) for k,a,_,_,z in blocks(body,0) if k=='desc'),None)
        if span:return body[:span[0]]+desc+body[span[1]:]
        body,n=re.subn(r'\bdesc\s*=\s*\S+',lambda m:desc,body,count=1)
        assert n==1;return body
    def remember(body,eid,var):
        nonlocal tracked
        edits=[]
        for k,_,b,e,_ in blocks(body,0):
            if k!='option':continue
            part=body[b:e];m=re.search(r'\bname\s*=\s*'+re.escape(eid)+r'\.([abc])\b',part)
            if not m:continue
            part=re.sub(r'\s*# HBE_RECAP_CHOICE_BEGIN.*?# HBE_RECAP_CHOICE_END\s*','\n',part,flags=re.S)
            value='abc'.index(m[1])+1
            part=part.rstrip()+f'\n # HBE_RECAP_CHOICE_BEGIN\n hidden_effect = {{ set_variable = {{ name = {var} value = {value} }} }}\n # HBE_RECAP_CHOICE_END\n '
            edits.append((b,e,part));tracked+=1
        assert len(edits)==3,(eid,len(edits));return apply_edits(body,edits)
    def chapter(rel,eid,key,number,opening,current,var,previous=None):
        desc_key=eid+'.desc'
        if number==1:
            L(desc_key,opening+'\n\n'+current)
            event(rel,eid,lambda b:replace_desc(b,'desc = '+desc_key))
            variants=[]
        else:
            a,b,c,legacy=RECAPS[key][number-2]
            L(desc_key,legacy+'\n\n'+current)
            variants=[]
            for n,recap in enumerate((a,b,c),1):
                loc_key=desc_key+'.after_'+'abc'[n-1]
                L(loc_key,recap+'\n\n'+current,desc_key)
                variants.append(dict(value=n,key=loc_key,previous_option=previous+'.'+'abc'[n-1]))
            desc='desc = { first_valid = { '+' '.join(f'triggered_desc = {{ trigger = {{ has_variable = {var} var:{var} = {v["value"]} }} desc = {v["key"]} }}' for v in variants)+' triggered_desc = { desc = '+desc_key+' } } }'
            event(rel,eid,lambda b:replace_desc(b,desc))
        rows.append(dict(id=eid,chain=key,chapter=number,source=rel,previous=previous,recap_variable=var if previous else None,variants=variants,fallback=desc_key))
    for region,story in LONG.items():
        ns='hbe_story_'+region;rel=f'in_game/events/{ns}.txt';var=ns+'_recap_choice';ids=[]
        for i,(title,body,labels) in enumerate(story['steps'],1):
            eid=ns+'.'+str(i);ids.append(eid)
            paras=fix(body).split('\n\n')
            opening=paras[0];current=''.join(paras[1:]) if i==1 else ''.join(paras)
            chapter(rel,eid,region,i,opening,current,var,ns+'.'+str(i-1) if i>1 else None)
            if i<8:event(rel,eid,lambda b:remember(b,eid,var))
        ending_ids=[]
        for n in (1,2):
            eid=ns+'.'+str(200+n);ending_ids.append(eid)
            L(eid+'.desc',fix(END_PROSE[region][n-1])+'\n\n'+ENDING_DETAILS[region][n-1])
        chains.append(dict(key=region,name=story['name'],kind='regional',nodes=ids,endings=ending_ids,wait_years=story['offsets'],branch_variable=ns+'_direction',ending_gate=['>= 0','< 0'],abort_choices=[eid+'.d' for eid in ids[:-1]]+[ids[-1]+'.c']))
    counts={}
    for story in SHORT+SHARED:
        region=story['region'];index=counts.get(region,0);counts[region]=index+1
        key=f'short_{region}_{index+1}';ns='hbe_short_'+region;rel=f'in_game/events/{ns}.txt';ids=[]
        var='hbe_'+key+'_art_route' # already recorded by the illustration pass
        for i,(title,body,labels) in enumerate(story['chapters'],1):
            eid=ns+'.'+str(index*10+i);ids.append(eid)
            current=CURRENT_OVERRIDES.get(eid,fix(body)+SHORT_DETAILS[key][i-1])
            chapter(rel,eid,key,i,story['context'],current,var,ns+'.'+str(index*10+i-1) if i>1 else None)
        chains.append(dict(key=key,name=story['name'],kind='short',nodes=ids,wait_months=[0,6,18],recap_variable=var,abort_choices=[eid+'.d' for eid in ids]))
    ns='hbe_migration';rel='in_game/events/hbe_migration_events.txt';var='hbe_migration_recap_choice';ids=[]
    for i,(title,body,labels,plans,art) in enumerate(CHAPTERS,1):
        eid=ns+'.'+str(i);ids.append(eid);paras=body.split('\n\n');opening=''
        current=''.join(paras[1:]) if i==1 else ''.join(paras)
        if i==1:
            opening=paras[0]+'来往船户把这阵求田寻工的动静称作“湖广填四川”。'
        elif i==2:
            current='查田书吏指给求租的人一片荒坡，旧村却说冬天要在那里放牲畜，春天还须从坡脚引水。田主愿招佃户开荒，请求将整块地列入自己的庄册；几户人家已经借来木桩，想先把可修的埂标出来。若另给新户小契，旧牧路便须补偿；若让田主包办出租，租额又可能在下一季上调。过境与居留的先前裁定仍须分别遵守，这一次应给哪些家庭开垦凭据，眼下还没有定论。'
        elif i==10:
            current='最早来问田地的几位长者已经去世，他们的子女把旧乡信件、入蜀路凭与本府契纸一并交来。书记从中翻出准入、限留、担保与过境的不同批语，发现它们仍是遇事逐案援引，没有一份办法能说清后来的家庭应当怎样申请。旧户请求保留祖辈出钱修桥养仓的份额，新户则想让多年居住与出资得到持续承认。前几次府议留下的支持各不相同，如今须据此为下一代定下一条能够遵循的路。'
        else:opening=''
        chapter(rel,eid,'migration',i,opening,current,'hbe_migration_first_policy' if i==2 else var,ns+'.'+str(i-1) if i>1 else None)
        if i<10:event(rel,eid,lambda b:remember(b,eid,var))
    # Keep old localization aliases useful to consumers without pointing the game at them.
    for suffix,letter in zip(('open','sponsored','transit'),'abc'):
        L('hbe_migration.2.desc.'+suffix,texts['simp_chinese']['hbe_migration.2.desc.after_'+letter],'hbe_migration.2.desc')
    chains.append(dict(key='migration',name='湖广填四川',kind='migration',nodes=ids,endings=['hbe_ending.2001','hbe_ending.2002'],wait_years=OFFSETS,branch_variable='hbe_migration_acceptance',ending_gate=['>= 6','< 6'],abort_choices=['hbe_migration.10.c']))
    for lang,loc in texts.items():
        files[f'main_menu/localization/{lang}/hbe_story_l_{lang}.yml']='l_'+lang+':\n'+'\n'.join(' '+k+': '+json.dumps(v,ensure_ascii=False) for k,v in loc.items())
    for rel,t in files.items():
        p=out/rel;p.write_text(t.rstrip()+'\n',encoding='utf-8-sig',newline='\n' if '/localization/' in rel else '\r\n')
    result=dict(chains=chains,chapters=rows,chain_count=41,stage_events=165,dynamic_recaps=124,unique_long_epilogues=14,new_hidden_choice_records=tracked,gameplay_effects_changed=False,english_status='Existing Chinese fallback policy retained for this authored story batch.',files=sorted(files))
    (root/'data/story_narratives_v031.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    mp=out/'build_manifest.json';m=json.loads(mp.read_text(encoding='utf8'));m['story_narratives_v031']={k:v for k,v in result.items() if k not in ('chains','chapters')}
    m['files']={p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and p.name!='build_manifest.json'}
    mp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('chains','chapters','files')},ensure_ascii=False));return result

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);a=ap.parse_args();apply(a.root/'mod/holy_bashu_empire',a.root)
