"""Move premium industrial recipes from broad regional advances to craft transmission."""
from build_support import snapshot_files
from pathlib import Path
import json, re
from pdxscript import blocks,apply_edits
from build_support import write_preserving_format as put

MOVES = {
 'hbe_transmission_embroidery': ('hbe_tech_chengdu_plain_4', ('hbe_chengdu_plain_advanced_production','hbe_chengdu_plain_paper_production')),
 'hbe_transmission_well_salt': ('hbe_tech_southern_salt_wine_3', ('hbe_southern_salt_wine_advanced_production',)),
 'hbe_transmission_paper': ('hbe_tech_northern_shudao_7', ('hbe_northern_shudao_advanced_production',)),
 'hbe_transmission_border_tea': ('hbe_tech_western_tea_horse_3', ('hbe_western_tea_horse_advanced_production','hbe_western_tea_horse_paper_production')),
}

def apply(out,root,game=None):
    out,root=Path(out),Path(root);moved={p:new for new,(_,ps) in MOVES.items() for p in ps};locs={}
    for language in ('simp_chinese','english'):
        path=out/f'main_menu/localization/{language}/hbe_l_{language}.yml';text=path.read_text(encoding='utf-8-sig')
        entries={q[1]:json.loads(q[2]) for q in re.finditer(r'^[ \t]+(\w+):[ \t]*("(?:[^"\\]|\\.)*")',text,re.M)};locs[language]=entries
        def clean(q):
            key,value=q[1],json.loads(q[2]);old=key.removesuffix('_effects')
            if old not in {x[0] for x in MOVES.values()} or not key.endswith('_effects'):return q[0]
            for method,new in moved.items():
                if MOVES[new][0]==old:value=value.replace('解锁机构生产方式：'+entries[method]+'。','')
            value='\n'.join(s for s in value.splitlines() if s.strip())
            return ' '+key+': '+json.dumps(value,ensure_ascii=False)
        put(path,re.sub(r'^[ \t]+(\w+):[ \t]*("(?:[^"\\]|\\.)*")[ \t]*$',clean,text,flags=re.M))
    for filename in ('hbe_advances.txt','hbe_industry_transmission.txt'):
        path=out/'in_game/common/advances'/filename;text=path.read_text(encoding='utf-8-sig');edits=[]
        for key,_,a,b,_ in blocks(text,0):
            body=text[a:b];body=re.sub(r'^[ \t]*unlock_production_method[ \t]*=[ \t]*(\w+)[ \t]*\n?',lambda q:'' if q[1] in moved else q[0],body,flags=re.M)
            if key in MOVES:
                # Put these before the existing sidework unlock so scalar readers
                # that expose the last field retain the native-sidework contract.
                addition=''.join('    unlock_production_method = '+p+'\n' for p in MOVES[key][1])
                marker='    unlock_production_method = '+key+'_sidework';assert marker in body
                body=body.replace(marker,addition+marker)
            edits.append((a,b,body))
        put(path,apply_edits(text,edits))
    # Keep advanced recipes region-specific even if a legacy save holds an
    # incorrectly granted transmission advance; retain all existing extra gates.
    path=out/'in_game/common/building_types/hbe_civic_buildings.txt'
    text=path.read_text(encoding='utf-8-sig');edits=[]
    for method,_,a,b,_ in blocks(text):
        if method not in moved:continue
        body=text[a:b];guard=moved[method]+'_ready = yes'
        if guard in body:continue
        allow=next((item for item in blocks(body,0) if item[0]=='allow'),None)
        if allow:body=apply_edits(body,[(allow[3],allow[3],' '+guard+' ')])
        else:body+='\n allow = { '+guard+' }\n'
        edits.append((a,b,body))
    if edits:put(path,apply_edits(text,edits))
    catalogue=root/'data/technology_rewards_v021.json'
    if catalogue.exists():
        data=json.loads(catalogue.read_text(encoding='utf-8'))
        for row in data.get('advances',[]):
            row['unlocks']=[p for p in row['unlocks'] if p not in moved]
            for method in moved:row['link']=row['link'].replace('解锁机构生产方式：'+locs['simp_chinese'][method]+'。','')
            row['link']='\n'.join(s for s in row['link'].splitlines() if s.strip())
        for row in data.get('production',[]):
            if row['key'] in moved:row['advance']=moved[row['key']]
        data['premium_recipe_advances']=moved
        put(catalogue,json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    # Keep existing generated documentation aligned with the effective unlocks.
    transmission_loc=out/'main_menu/localization/simp_chinese/hbe_industry_transmission_l_simp_chinese.yml'
    new_names={q[1]:json.loads(q[2]) for q in re.finditer(r'^[ \t]+(\w+):[ \t]*("(?:[^"\\]|\\.)*")',transmission_loc.read_text(encoding='utf-8-sig'),re.M)}
    for filename in ('technology_rewards_v021.md','special_goods_v021.md'):
        doc=root/'docs'/filename
        if not doc.exists():continue
        text=doc.read_text(encoding='utf-8').replace('本课题的永久加成立即生效，并推进后续地区课题与验收。','')
        for method,new in moved.items():
            old=MOVES[new][0]
            text=text.replace('解锁机构生产方式：'+locs['simp_chinese'][method]+'。','')
            lines=text.splitlines()
            for i,line in enumerate(lines):
                if '|'+locs['simp_chinese'][method]+'|' in line:
                    lines[i]=line.replace('|'+locs['simp_chinese'][old]+'|','|'+new_names[new]+'|')
            text='\n'.join(lines)+'\n'
        if filename=='special_goods_v021.md':
            for new,(old,_) in MOVES.items():
                text=text.replace('|'+locs['simp_chinese'][old]+'|','|'+new_names[new]+'|')
            text=text.replace('锦坊绣作、井灶精煎、蜀纸精抄和边茶压砖保留原科技门槛。','锦坊绣作、井灶精煎、蜀纸精抄和边茶压砖改由第二时代对应的四项传习科技解锁；基础生产资格仍随原建筑科技取得。')
        put(doc,text)
    doc=root/'docs/industry_transmission.md'
    if doc.exists():
        text=doc.read_text(encoding='utf-8')
        paragraph='四项传习科技同时解锁对应特色机构的高级工艺：锦样分授提供锦坊绣作与蜀纸描样，井灶合煎提供井灶精煎，槽帘传习提供蜀纸精抄，茶引分庄提供边茶压砖与蜀纸包茶。这六项工序不再挂在联渠灌溉、井灶改良、公文分驿或商队互保上；蜀纸描样与蜀纸包茶保留原有额外前置。配方、基础生产和原地区科技数值不变。旧档须研究对应传习科技后才能取得这些高级工艺，不自动补发研究。'
        if paragraph not in text:text=text.replace('## 资格',paragraph+'\n\n## 资格',1)
        put(doc,text)
    report={'moves':[{'from':old,'to':new,'methods':list(ps)} for new,(old,ps) in MOVES.items()],
            'moved_methods':list(moved),'recipe_values_changed':False,'base_qualifications_changed':False,
            'research_costs_changed':False,'stat_modifiers_changed':False,'auto_granted_research':False,
            'advanced_recipe_region_guards':moved,
            'note':'Special-building premium production now requires the matching age-two transmission advance. Basic production, original building unlocks and regional modifiers remain in place.'}
    mp=out/'build_manifest.json';m=json.loads(mp.read_text(encoding='utf-8'));m['production_advance_semantics_v032']=report
    m['files']=snapshot_files(out)
    put(mp,json.dumps(m,ensure_ascii=False,indent=2)+'\n');return report

def validate(out,game,manifest,check):
    if 'production_advance_semantics_v032' not in manifest:return
    out=Path(out);definitions={}
    for path in (out/'in_game/common/advances').glob('hbe*.txt'):
        text=path.read_text(encoding='utf-8-sig');definitions.update({key:text[a:b] for key,_,a,b,_ in blocks(text,0)})
    for new,(old,methods) in MOVES.items():
        for method in methods:
            owners={key for key,body in definitions.items() if re.search(r'\bunlock_production_method\s*=\s*'+re.escape(method)+r'\b',body)}
            check(method+' unlocked only by semantically matching transmission advance',owners=={new})
        check(old+' retains its original modifiers and no misplaced premium recipe',not any(re.search(r'\bunlock_production_method\s*=\s*'+re.escape(p)+r'\b',definitions[old]) for p in methods))
        check(new+' retains the native sidework recipe',new+'_sidework' in definitions[new])
        check(new+' remains manually researched in the second age','age = age_2_renaissance' in definitions[new] and 'starting_technology_level = 99' in definitions[new])
    recipes=(out/'in_game/common/building_types/hbe_civic_buildings.txt').read_text(encoding='utf-8-sig')
    recipe_bodies={key:recipes[a:b] for key,_,a,b,_ in blocks(recipes)}
    for advance,(_,methods) in MOVES.items():
        for method in methods:
            body=recipe_bodies[method]
            check(method+' enforces originating-circle readiness at actual production selection',advance+'_ready = yes' in body)
            if '_paper_production' in method:
                check(method+' retains its extra paper-pattern research gate','has_advance = hbe_tech_common_6' in body)
    for lang in ('simp_chinese','english'):
        text=(out/f'main_menu/localization/{lang}/hbe_l_{lang}.yml').read_text(encoding='utf-8-sig');entries={q[1]:json.loads(q[2]) for q in re.finditer(r'^[ \t]+(\w+):[ \t]*("(?:[^"\\]|\\.)*")',text,re.M)}
        for _,(old,methods) in MOVES.items():check(lang+' '+old+' has no stale recipe tooltip',all('解锁机构生产方式：'+entries[p]+'。' not in entries[old+'_effects'] for p in methods))
