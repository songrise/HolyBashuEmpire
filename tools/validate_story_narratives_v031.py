"""Verify prior-choice recollections against the actual preceding event scripts."""
from pathlib import Path
import argparse,hashlib,importlib.util,json,re,subprocess,sys
from pdxscript import tokens,blocks,apply_edits

def validate(root,baseline='86df6d5'):
    root=Path(root);mod=root/'mod/holy_bashu_empire';sys.path[:0]=[str(root/'tools'),str(root/'data')]
    from story_narratives_v031 import RECAPS,SHORT_DETAILS
    spec=importlib.util.spec_from_file_location('narrative_catalog',root/'devtools/event-browser/catalog.py');cat=importlib.util.module_from_spec(spec);spec.loader.exec_module(cat)
    parse,field=cat.parse,cat.field
    report=json.loads((root/'data/story_narratives_v031.json').read_text(encoding='utf8'));checks=[]
    def check(label,ok):checks.append(dict(check=label,passed=bool(ok)));assert ok,label
    def clean(t):
        t=re.sub(r'\s*# HBE_RECAP_CHOICE_BEGIN.*?# HBE_RECAP_CHOICE_END\s*','\n',t,flags=re.S)
        t=apply_edits(t,[(a,z,'') for k,a,_,_,z in blocks(t) if k=='desc'])
        return re.sub(r'\bdesc\s*=\s*[^\s{}]+','',t)
    events={};locs={}
    for rel in report['files']:
        p=mod/rel
        if not rel.startswith('in_game/events/'):continue
        old=subprocess.check_output(['git','-C',str(root),'show',baseline+':mod/holy_bashu_empire/'+rel]).decode('utf-8-sig');new=p.read_text(encoding='utf-8-sig')
        check('gameplay and transitions preserved: '+rel,[x.value for x in tokens(clean(old))]==[x.value for x in tokens(clean(new))])
        events.update({n['key']:n['value'] for n in parse(new) if isinstance(n['value'],list) and re.fullmatch(r'\w+\.\d+',n['key'])})
    for lang in ('simp_chinese','english'):
        p=mod/f'main_menu/localization/{lang}/hbe_story_l_{lang}.yml'
        locs[lang]={m[1]:json.loads(m[2]) for line in p.read_text(encoding='utf-8-sig').splitlines() if (m:=re.match(r'\s*(\S+):\s*(".*")$',line))}
    def visible(t):return re.sub(r"\[Concept\('[^']+', '([^']+)'\)\|e\]",lambda m:m[1],t)
    marker_cases=0
    for row in report['chapters']:
        eid=row['id'];desc=field(events[eid],'desc');texts=[]
        for lang,loc in locs.items():
            keys=[row['fallback']]+[v['key'] for v in row['variants']]
            for key in keys:
                check(lang+' exactly two narrative paragraphs: '+key,len(loc[key].split('\n\n'))==2)
                check(lang+' no mechanical chapter footer: '+key,not re.search(r'本篇是|第\d+[章篇]|历次决定，会影响|至此，这段事业',loc[key]))
            texts=[visible(loc[k]) for k in keys]
            if row['previous']:
                check(lang+' prior choices have distinct recollections: '+eid,len({t.split('\n\n')[0] for t in texts})==4)
                check(lang+' current scene stays the same across prior choices: '+eid,len({t.split('\n\n')[1] for t in texts})==1)
        if not row['previous']:continue
        choices=field(desc,'first_valid');check('three guarded branches plus old-save fallback: '+eid,len(choices)==4)
        previous=events[row['previous']]
        for variant,candidate in zip(row['variants'],choices):
            trigger=field(candidate['value'],'trigger');var=row['recap_variable']
            check('description checks previous-choice variable exists: '+variant['key'],field(trigger,'has_variable')==var)
            check('native branch value and localization resolve: '+variant['key'],field(trigger,'var:'+var)==str(variant['value']) and field(candidate['value'],'desc')==variant['key'])
            option=next(n['value'] for n in previous if n['key']=='option' and field(n['value'],'name')==variant['previous_option'])
            def assignments(nodes):
                found=[]
                for n in nodes:
                    if n['key']=='set_variable' and isinstance(n['value'],list) and field(n['value'],'name')==var:found.append(field(n['value'],'value'))
                    elif isinstance(n['value'],list):found+=assignments(n['value'])
                return found
            check('actual preceding option records matching recap: '+variant['previous_option'],str(variant['value']) in assignments(option));marker_cases+=1
        check('missing or unknown value reaches neutral fallback: '+eid,not field(choices[-1]['value'],'trigger',[]) and field(choices[-1]['value'],'desc')==row['fallback'])
    from short_stories import SHORT
    from shared_stories import SHORT as SHARED
    counts={}
    for story in SHORT+SHARED:
        r=story['region'];idx=counts.get(r,0);counts[r]=idx+1
        for chapter in (2,3):
            key=f'hbe_short_{r}.{idx*10+chapter}.desc'
            check('opening synopsis never repeated: '+key,story['context'] not in locs['simp_chinese'][key])
    for region in (k for k in RECAPS if not k.startswith('short_') and k!='migration'):
        for ending in (201,202):
            key=f'hbe_story_{region}.{ending}.desc'
            check('individual epilogue: '+key,'几十年的笔记、工钱与争执没有凭空消失' not in locs['simp_chinese'][key] and len(locs['simp_chinese'][key].split('\n\n'))==2)
    catalogue=cat.build_catalog(mod);dynamic=[e for e in catalogue['events'] if e.get('descriptionVariants')]
    check('browser exposes all 124 branch recollections',len(dynamic)==124)
    check('41 chains and 165 stage descriptions',len(report['chains'])==41 and len(report['chapters'])==165)
    check('all 372 previous option links checked',marker_cases==372)
    check('all 33 short chains have authored current-scene detail',len(SHORT_DETAILS)==33 and all(len(v)==3 for v in SHORT_DETAILS.values()))
    return dict(status='passed',checks=checks,check_count=len(checks),baseline=baseline,chains=41,stage_events=165,conditional_stages=124,previous_option_links=marker_cases,gameplay_changed=False)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);ap.add_argument('--baseline',default='86df6d5');ap.add_argument('--report',type=Path);a=ap.parse_args();r=validate(a.root,a.baseline)
    if a.report:a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:v for k,v in r.items() if k!='checks'}))
