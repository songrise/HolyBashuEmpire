"""Final shared presentation pass: readable origins, first-choice parties and effects."""
from pathlib import Path
import json
import re
from pdxscript import blocks, apply_edits
from build_support import write_preserving_format as _write, snapshot_files

ICON_GAP = re.compile(r'(@hbe_[a-z0-9_]+!)[ \t]+(?=\[Concept\()')
WEST = ('chengdu_plain', 'western_tea_horse', 'southwestern_valleys')
EAST = ('eastern_river', 'central_hills', 'southern_salt_wine')
MEMBER = 'is_member_of_international_organization = international_organization:hbe_empire'
HIDDEN_DECISIONS = {
    'hbe_decisions.txt': ('hbe_status',),
    'hbe_banquet_decisions.txt': (
        'hbe_banquet_ledger', 'hbe_project_fund',
        'hbe_stance_change_1', 'hbe_stance_change_2',
    ),
    'hbe_civic_decisions.txt': (
        'hbe_civic_ledger', 'hbe_civic_audit', 'hbe_civic_revision',
    ),
}


def hide_redundant_decisions(out):
    # Retain definitions and shared effects; panel actions remain available.
    for filename, keys in HIDDEN_DECISIONS.items():
        path = Path(out)/'in_game/common/decisions'/filename
        text = path.read_text(encoding='utf-8-sig')
        edits, found = [], set()
        for key, _, a, b, _ in blocks(text, 0):
            if key not in keys:
                continue
            body = text[a:b]
            potential = next(x for x in blocks(body, 0) if x[0] == 'potential')
            edits.append((a+potential[2], a+potential[3], ' always = no '))
            found.add(key)
        if found != set(keys):
            raise ValueError('Missing decisions in '+filename+': '+str(set(keys)-found))
        write(path, apply_edits(text, edits))


def write(path, text):
    path=Path(path)
    if path.exists():
        _write(path,text)
    else:
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(text,encoding='utf-8-sig')


def origin_for_tags(tags, manifest):
    tags = set(tags)
    if tags == {c['tag'] for c in manifest['countries']}:
        return 'common'
    for region in manifest['regions']:
        if tags == {c['tag'] for c in manifest['countries'] if c['region'] == region[0]}:
            return region[0]
    raise ValueError('Research potential does not match an originating circle: '+str(tags))


def rewrite(path, replacements):
    text = path.read_text(encoding='utf-8-sig')
    write(path, apply_edits(text, [(a,b,replacements[k]) for k,_,a,b,_ in blocks(text,0) if k in replacements]))


def apply(out, root, manifest):
    out = Path(out)
    hide_redundant_decisions(out)
    # Use existing persistent home markers plus native setup-time memberships.
    # No guest license or conquest can count as an originating-circle identity.
    definitions, labels = [], {}
    for group, name in [('common', '巴蜀诸侯')]+[(r[0],r[1]) for r in manifest['regions']]:
        condition = f'OR = {{ {MEMBER} has_variable = hbe_initialized }}' if group == 'common' else f'OR = {{ has_variable = hbe_home_{group} is_member_of_international_organization = international_organization:hbe_circle_{group} }}'
        key = 'hbe_research_origin_'+group
        definitions.append(f'{key} = {{ custom_tooltip = {{ text = {key}_tt {condition} }} }}')
        labels[key+'_tt'] = '具有巴蜀诸侯资格' if group == 'common' else '本国传承'+name+'的本圈制度'
    # North remains neutral, while east/west AI preferences are 70:30.
    for side, regions in [('west',WEST),('east',EAST)]:
        definitions.append('hbe_initial_party_'+side+' = { OR = { '+' '.join(f'capital = {{ is_in_scripted_geography = scripted_geography:hbe_geo_{r} }}' for r in regions)+' } }')
    write(out/'in_game/common/scripted_triggers/hbe_research_origins.txt','\n'.join(definitions)+'\n')
    origins = {}
    for path in (out/'in_game/common/advances').glob('hbe*.txt'):
        text = path.read_text(encoding='utf-8-sig'); edits = []
        for key,_,a,b,_ in blocks(text,0):
            body = text[a:b]
            for field,_,c,d,_ in blocks(body,0):
                if field != 'potential':continue
                potential = body[c:d]
                tags = re.findall(r'has_or_had_tag\s*=\s*(\w+)',potential)
                old = re.search(r'\bhbe_research_origin_(\w+)\s*=\s*yes',potential)
                if not tags and not old:continue
                group = origin_for_tags(tags,manifest) if tags else old[1]
                origins[key] = group
                edits.append((a+c,a+d,' hbe_research_origin_'+group+' = yes '))
        write(path,apply_edits(text,edits))
    for lang in ('simp_chinese','english','traditional_chinese'):
        write(out/f'main_menu/localization/{lang}/hbe_presentation_l_{lang}.yml',f'l_{lang}:\n'+'\n'.join(f' {k}: "{v}"' for k,v in labels.items())+'\n')

    path = out/'in_game/common/scripted_effects/hbe_banquet_effects.txt'
    register = f'''if = {{ limit = {{ NOT = {{ has_variable = hbe_banquet_joined }} }}
 hbe_initialize = yes set_variable = hbe_banquet_joined set_variable = {{ name = hbe_contribution value = 0 }}
 set_variable = {{ name = hbe_stance value = 0 }}
 trigger_event_non_silently = {{ id = hbe_banquet.1 days = 1 }}
}} hbe_feast_sync_party = yes'''
    replacements = {'hbe_banquet_register':register}
    for i, old in [(1,'hbe_local_party'),(2,'hbe_common_party')]:
        replacements['hbe_choose_stance_'+str(i)] = f'''if = {{ limit = {{ NOT = {{ var:hbe_stance = {i} }} NOT = {{ has_variable = hbe_stance_cooldown }} }}
 save_scope_as = hbe_party_departing
 if = {{ limit = {{ is_member_of_international_organization = international_organization:{old} }}
  international_organization:{old} = {{ every_international_organization_member = {{
   limit = {{ NOT = {{ this = scope:hbe_party_departing }} }}
   add_opinion = {{ modifier = hbe_left_feast_party target = scope:hbe_party_departing }}
  }} }}
 }}
 set_variable = {{ name = hbe_stance value = {i} }}
 set_variable = {{ name = hbe_stance_cooldown value = yes years = 5 }}
 hbe_feast_sync_party = yes
}}'''
    rewrite(path,replacements)
    path = out/'in_game/common/scripted_effects/hbe_simple_banquet_effects.txt'
    text = path.read_text(encoding='utf-8-sig');edits=[]
    for key,_,a,b,_ in blocks(text,0):
        if key != 'hbe_feast_sync_party':continue
        body = text[a:b]
        for field,s,c,d,z in blocks(body,0):
            if field == 'if' and 'var:hbe_stance > 2' in body[c:d]:
                edits.append((a+s,a+z,'if = { limit = { has_variable = hbe_stance var:hbe_stance > 2 } set_variable = { name = hbe_stance value = 2 } }'))
    write(path,apply_edits(text,edits))
    write(out/'in_game/common/on_action/hbe_simple_banquet_on_actions.txt',f'''monthly_country_pulse = {{ on_actions = {{ hbe_simple_feast_country }} }}
hbe_simple_feast_country = {{ trigger = {{ hbe_is_prince = yes }} effect = {{
 if = {{ limit = {{ {MEMBER} }}
  if = {{ limit = {{ is_situation_active = situation:hbe_banquet }} hbe_banquet_register = yes }}
 }} else = {{
  if = {{ limit = {{ is_member_of_international_organization = international_organization:hbe_common_party }} international_organization:hbe_common_party = {{ remove_country_from_international_organization = prev }} }}
  if = {{ limit = {{ is_member_of_international_organization = international_organization:hbe_local_party }} international_organization:hbe_local_party = {{ remove_country_from_international_organization = prev }} }}
 }}
}} }}
''')

    # Keep all existing numeric effects. Remove an old arrangement only if present;
    # reselecting the same one uses native mode=replace rather than deleting it.
    choices = 0
    for path in (out/'in_game/events').glob('hbe*.txt'):
        text = path.read_text(encoding='utf-8-sig');edits=[]
        for event,_,a,b,_ in blocks(text,0):
            body=text[a:b]
            for field,_,c,d,_ in blocks(body,0):
                if field!='option':continue
                option=body[c:d]
                if event=='hbe_banquet.1':
                    side='west' if 'name = hbe_banquet.1.a' in option else 'east'
                    option=apply_edits(option,[(s,z,'ai_chance = { base = 30 modifier = { add = 40 hbe_initial_party_'+side+' = yes } }') for k,s,_,_,z in blocks(option,0) if k=='ai_chance'])
                added=re.findall(r'add_country_modifier\s*=\s*\{\s*modifier\s*=\s*(hbe_choice_(\w+)_[123])\b',option)
                if added:
                    assert len(added)==1,event
                    selected,group=added[0]
                    old_guards=[(s,z,'') for k,s,e,f,z in blocks(option,0) if k=='if' and re.search(r'remove_country_modifier\s*=\s*hbe_choice_\w+',option[e:f])]
                    option=apply_edits(option,old_guards)
                    option=re.sub(r'\bremove_country_modifier\s*=\s*hbe_choice_\w+','',option)
                    guards=' '.join(f'if = {{ limit = {{ has_country_modifier = hbe_choice_{group}_{i} }} remove_country_modifier = hbe_choice_{group}_{i} }}' for i in (1,2,3) if f'hbe_choice_{group}_{i}'!=selected)
                    option=option.rstrip()+' '+guards+' ';choices+=1
                if option!=body[c:d]:edits.append((a+c,a+d,option))
        write(path,apply_edits(text,edits))

    gaps=0
    for path in (out/'main_menu/localization').rglob('hbe*.yml'):
        text=path.read_text(encoding='utf-8-sig');text,n=ICON_GAP.subn(r'\1',text);gaps+=n
        lines=[]
        for line in text.splitlines():
            if re.match(r'\s*(?:STATIC_MODIFIER_NAME_)?hbe_choice_\w+:',line):
                line=line.replace('：','·')
            lines.append(line)
        write(path,'\n'.join(lines)+'\n')
    report=dict(schema_version=1,research_origins=origins,origin_conditions='Persistent home markers or native organization membership; no tag lists in advances.',initial_party_weights=dict(preferred=70,other=30,north='neutral'),conditional_arrangement_options=choices,icon_word_gap_removed=True,visual_verified=False)
    from retire_local_affairs_legacy import clean_descriptions
    clean_descriptions(out)
    manifest['presentation_v040']=report
    return dict(report=report,removed_icon_gaps=gaps)


def validate(out, manifest, check):
    if 'presentation_v040' not in manifest:return
    out=Path(out)
    read=lambda p:(out/p).read_text(encoding='utf-8-sig')
    for filename, keys in HIDDEN_DECISIONS.items():
        text=read('in_game/common/decisions/'+filename)
        definitions={k:text[a:b] for k,_,a,b,_ in blocks(text,0)}
        for key in keys:
            potential=next((definitions[key][a:b] for k,_,a,b,_ in blocks(definitions[key],0) if k=='potential'), '')
            check(key+' duplicate or legacy decision stays hidden',potential.strip()=='always = no')
    origins=read('in_game/common/scripted_triggers/hbe_research_origins.txt')
    check('research origins use persistent identities and organization membership without tag lists','has_or_had_tag' not in origins and MEMBER in origins and 'has_variable = hbe_initialized' in origins)
    for r in manifest['regions']:
        check(r[0]+' origin survives formation but excludes guests',f'has_variable = hbe_home_{r[0]}' in origins and f'international_organization:hbe_circle_{r[0]}' in origins and 'hbe_guest_' not in origins)
    count=0
    for path in (out/'in_game/common/advances').glob('hbe*.txt'):
        s=path.read_text(encoding='utf-8-sig')
        for k,_,a,b,_ in blocks(s,0):
            for f,_,c,d,_ in blocks(s[a:b],0):
                if f!='potential':continue
                potential=s[a+c:a+d]
                check(k+' potential does not expand a country-tag list','has_or_had_tag' not in potential)
                count+=bool(re.search(r'hbe_research_origin_\w+\s*=\s*yes',potential))
    check('all research nodes retain a compact origin gate',count==manifest['research_nodes'] and len(manifest['presentation_v040']['research_origins'])==manifest['research_nodes'])
    effects=read('in_game/common/scripted_effects/hbe_banquet_effects.txt')
    defs={k:effects[a:b] for k,_,a,b,_ in blocks(effects,0)}
    check('first registration leaves the faction undecided and queues one choice','name = hbe_stance value = 0' in defs['hbe_banquet_register'] and defs['hbe_banquet_register'].count('id = hbe_banquet.1')==1 and 'has_or_had_tag' not in defs['hbe_banquet_register'])
    sync=read('in_game/common/scripted_effects/hbe_simple_banquet_effects.txt')
    check('faction synchronization never converts an unset stance to a default faction','NOT = { has_variable = hbe_stance }' not in sync and 'has_variable = hbe_stance var:hbe_stance > 2' in sync)
    pulse=read('in_game/common/on_action/hbe_simple_banquet_on_actions.txt')
    pulse_body=next(pulse[a:b] for k,_,a,b,_ in blocks(pulse,0) if k=='hbe_simple_feast_country')
    effect=next(pulse_body[a:b] for k,_,a,b,_ in blocks(pulse_body,0) if k=='effect')
    top=next(effect[a:b] for k,_,a,b,_ in blocks(effect,0) if k=='if')
    limit=next(top[a:b] for k,_,a,b,_ in blocks(top,0) if k=='limit')
    check('monthly cleanup cannot expel HBE members before the feast starts',limit.strip()==MEMBER and 'remove_country_from_international_organization' not in top)
    for i,other in [(1,'hbe_local_party'),(2,'hbe_common_party')]:
        check('stance '+str(i)+' penalizes only an actual old-party member',f'limit = {{ is_member_of_international_organization = international_organization:{other} }}' in defs['hbe_choose_stance_'+str(i)] and 'NOT = { has_variable = hbe_stance_cooldown }' in defs['hbe_choose_stance_'+str(i)])
    choices=0
    for path in (out/'in_game/events').glob('hbe*.txt'):
        text=path.read_text(encoding='utf-8-sig')
        for event,_,a,b,_ in blocks(text,0):
            for field,_,c,d,_ in blocks(text[a:b],0):
                if field!='option':continue
                option=text[a+c:a+d]
                if event=='hbe_banquet.1':
                    side='west' if 'name = hbe_banquet.1.a' in option else 'east'
                    check('initial '+side+' choice uses 70:30 regional AI weighting','base = 30 modifier = { add = 40 hbe_initial_party_'+side+' = yes }' in option)
                added=re.findall(r'add_country_modifier\s*=\s*\{\s*modifier\s*=\s*(hbe_choice_(\w+)_[123])\b',option)
                if not added:continue
                selected,group=added[0]
                guarded=[option[e:f] for k,_,e,f,_ in blocks(option,0) if k=='if' and 'remove_country_modifier = hbe_choice_' in option[e:f]]
                removed=re.findall(r'remove_country_modifier\s*=\s*(hbe_choice_\w+)',option)
                check(event+' option '+str(choices)+' adds one arrangement and clears only two existing alternatives',len(added)==1 and len(guarded)==2 and len(removed)==2 and selected not in removed and all('has_country_modifier = '+k in g and 'remove_country_modifier = '+k in g for k,g in zip(removed,guarded)))
                choices+=1
    check('all 126 regional policy options retain the guarded replacement contract',choices==126)
    for path in (out/'main_menu/localization').rglob('hbe*.yml'):
        text=path.read_text(encoding='utf-8-sig')
        check('no icon-to-concept word gap '+path.name,not ICON_GAP.search(text))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--mod-dir',type=Path,required=True);args=parser.parse_args()
    path=args.mod_dir/'build_manifest.json';manifest=json.loads(path.read_text(encoding='utf-8'))
    result=apply(args.mod_dir,Path(__file__).resolve().parents[1],manifest)
    manifest['files']=snapshot_files(args.mod_dir,force=True)
    write(path,json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(advances=len(result['report']['research_origins']),options=result['report']['conditional_arrangement_options'],removed_icon_gaps=result['removed_icon_gaps'])))
