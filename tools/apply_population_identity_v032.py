"""Align Dechang with its residents and remove competing pop-state claims in two HBE realms."""
from build_support import snapshot_files
from pathlib import Path
import hashlib,json,re
from pdxscript import blocks,tokens,apply_edits
from build_support import write_preserving_format as put

CONFIG='data/opening_population_identity_v032.json'
SETUP='main_menu/setup/1337/10_countries.txt'
POPS='main_menu/setup/1337/06_pops.txt'

def country_bodies(text):
    return {key:text[a:b] for key,_,a,b,_ in blocks(text,2)}

def owned(body):
    return [t.value for key,_,a,b,_ in blocks(body,0) if key.startswith('own_') for t in tokens(body[a:b])]

def pop_claims(text):
    result={}
    for tag,_,a,b,_ in blocks(text,2):
        body=text[a:b]
        if not re.search(r'\btype\s*=\s*pop\b',body):continue
        result[tag]=[t.value for key,_,u,v,_ in blocks(body,0) if key=='add_pops_from_locations' for t in tokens(body[u:v])]
    return result

def apply(out,root,game):
    out,root,game=map(Path,(out,root,game));config=json.loads((root/CONFIG).read_text(encoding='utf-8-sig'))
    mp=out/'build_manifest.json';m=json.loads(mp.read_text(encoding='utf-8'));bytag={r['tag']:r for r in m['countries']}
    for tag,values in config['country_overrides'].items():
        bytag[tag].update(values)
        path=out/'in_game/setup/countries/hbe_countries.txt';text=path.read_text(encoding='utf-8-sig');edits=[]
        for key,_,a,b,_ in blocks(text,0):
            if key!=tag:continue
            body=text[a:b]
            for field,value in [('culture_definition',values['culture']),('religion_definition',values['religion'])]:
                body,n=re.subn(r'\b'+field+r'\s*=\s*\w+',field+' = '+value,body);assert n==1
            edits.append((a,b,body))
        assert len(edits)==1;put(path,apply_edits(text,edits))
        path=out/'main_menu/setup/1337/05_hbe_characters.txt';text=path.read_text(encoding='utf-8-sig');edits=[]
        for key,_,a,b,_ in blocks(text,1):
            if key!='hbe_ruler_'+tag.lower():continue
            body=text[a:b]
            for field in ('culture','religion'):
                body,n=re.subn(r'\b'+field+r'\s*=\s*\w+',field+' = '+values[field],body);assert n==1
            edits.append((a,b,body))
        assert len(edits)==1;put(path,apply_edits(text,edits))
    text=(out/SETUP).read_text(encoding='utf-8-sig');records=country_bodies(text)
    locations={tag:owned(records[tag]) for tag in config['population_ownership_countries']};wanted={l for ls in locations.values() for l in ls}
    edits=[]
    for tag,_,a,b,_ in blocks(text,2):
        body=text[a:b]
        if not re.search(r'\btype\s*=\s*pop\b',body):continue
        for key,_,u,v,_ in blocks(body,0):
            if key!='add_pops_from_locations':continue
            for token in tokens(body[u:v]):
                if token.value in wanted:
                    start=u+token.start;end=u+token.end;line_end=body.find('\n',end)
                    if line_end<0:line_end=len(body)
                    if not body[end:line_end].strip():
                        while start>0 and body[start-1] in ' \t':start-=1
                    edits.append((a+start,a+end,''))
    put(out/SETUP,apply_edits(text,edits))
    native_claims=pop_claims((game/SETUP).read_text(encoding='utf-8-sig'))
    removed={tag:[l for l in ls if l in wanted] for tag,ls in native_claims.items() if wanted & set(ls)}
    report={'country_overrides':config['country_overrides'],'population_ownership_countries':locations,
            'removed_native_pop_state_claims':removed,'native_pop_states_preserved_outside_target_locations':True,
            'population_sizes_types_cultures_religions_changed':False,'province_ownership_changed':False,
            'new_campaign_bookmark_only':True,'runtime_population_grants':False,
            'population_file_sha256':hashlib.sha256((out/POPS).read_bytes()).hexdigest()}
    m['population_identity_v032']=report;m['files']=snapshot_files(out)
    put(mp,json.dumps(m,ensure_ascii=False,indent=2)+'\n');return report

def validate(out,root,game,manifest,check):
    if 'population_identity_v032' not in manifest:return
    out,root,game=map(Path,(out,root,game));config=json.loads((root/CONFIG).read_text(encoding='utf-8-sig'))
    text=(out/SETUP).read_text(encoding='utf-8-sig');records=country_bodies(text)
    wanted={l for tag in config['population_ownership_countries'] for l in owned(records[tag])}
    current=pop_claims(text);native=pop_claims((game/SETUP).read_text(encoding='utf-8-sig'))
    check('two target states cover exactly eight original locations',len(wanted)==8)
    for tag,locations in native.items():
        check(tag+' pop-state claims outside the eight target locations preserved',current[tag]==[l for l in locations if l not in wanted])
    definitions=(out/'in_game/setup/countries/hbe_countries.txt').read_text(encoding='utf-8-sig');defs={key:definitions[a:b] for key,_,a,b,_ in blocks(definitions,0)}
    chars=(out/'main_menu/setup/1337/05_hbe_characters.txt').read_text(encoding='utf-8-sig');cb={key:chars[a:b] for key,_,a,b,_ in blocks(chars,1)}
    poptext=(out/POPS).read_text(encoding='utf-8-sig');_,_,a,b,_=blocks(poptext,0)[0];body=poptext[a:b];pops={key:body[a:b] for key,_,a,b,_ in blocks(body,0)}
    nativepop=(game/POPS).read_text(encoding='utf-8-sig');_,_,a,b,_=blocks(nativepop,0)[0];body=nativepop[a:b];oldpops={key:body[a:b] for key,_,a,b,_ in blocks(body,0)}
    for loc in wanted:check(loc+' resident counts types cultures and religions unchanged',[t.value for t in tokens(pops[loc])]==[t.value for t in tokens(oldpops[loc])])
    for tag,values in config['country_overrides'].items():
        check(tag+' country and ruler match real resident culture and religion',all(field+' = '+values[key] in defs[tag] for field,key in [('culture_definition','culture'),('religion_definition','religion')]) and all(key+' = '+value in cb['hbe_ruler_'+tag.lower()] for key,value in values.items()))
        check(tag+' manifest configuration agrees',all(next(r for r in manifest['countries'] if r['tag']==tag)[k]==v for k,v in values.items()))
        for field in ('culture','religion'):
            check(tag+' has residents of its official '+field,any(re.search(r'\b'+field+r'\s*=\s*'+values[field]+r'\b',pops[l]) for l in owned(records[tag])))
    check('population table has not been rewritten by the identity patch',hashlib.sha256((out/POPS).read_bytes()).hexdigest()==manifest['population_identity_v032']['population_file_sha256'])
