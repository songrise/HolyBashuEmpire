"""Structural and cross-reference checks; these are not an in-game playtest."""
import argparse,csv,hashlib,json,re,struct
from collections import Counter
from pathlib import Path
from pdxscript import blocks,tokens

ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--mod-dir',type=Path,default=ROOT/'mod/holy_bashu_empire')
    ap.add_argument('--game-dir',type=Path,required=True);ap.add_argument('--report',type=Path)
    ap.add_argument('--keep-going',action='store_true',help='Report all failed assertions instead of stopping at the first one')
    a=ap.parse_args();m=a.mod_dir;game=a.game_dir/'game';checks=[]
    def check(name,ok):
        checks.append(dict(check=name,passed=bool(ok)))
        if not ok and not a.keep_going:raise AssertionError(name)
    manifest=json.loads((m/'build_manifest.json').read_text(encoding='utf-8'))
    check('36 selectable princes',len(manifest['countries'])==36)
    check('7 circles and 7 distinct electors',len(manifest['regions'])==7 and len(set(manifest['electors'].values()))==7)
    check('164 unique domain locations',len(set(l for c in manifest['countries'] for l in c['locations']))==164)
    check('all countries have 3 to 10 locations',all(3<=len(c['locations'])<=10 for c in manifest['countries']))
    check('country capitals belong to their countries',all(c['capital'] in c['locations'] for c in manifest['countries']))
    check('all source-owned locations were removed',manifest['removed_domain_tokens']>=164)
    for path,h in manifest['files'].items():
        check('file hash '+path,hashlib.sha256((m/path).read_bytes()).hexdigest()==h)
    defs={};custom={};script_files=list(m.rglob('*.txt'))
    check('bookmark files are UTF8 without BOM',all(not f.read_bytes().startswith(b'\xef\xbb\xbf') for f in (m/'main_menu/setup').rglob('*.txt')))
    check('database scripts use UTF8 BOM',all(f.read_bytes().startswith(b'\xef\xbb\xbf') for f in script_files if '/main_menu/setup/' not in f.as_posix()))
    for f in script_files:
        s=f.read_text(encoding='utf-8-sig');bs=blocks(s,0)
        for k,*_ in bs:
            if f.parent.name!='modifier_icons' and (k.startswith('hbe_') or re.fullmatch(r'hbe\.\d+',k)):
                if k in custom:raise AssertionError(f'duplicate custom definition {k}: {f} / {custom[k]}')
                custom[k]=str(f.relative_to(m))
        defs[str(f.relative_to(m))]=bs
    check('all script braces and custom definitions are valid',True)
    # Validate full country ownership and ensure there is no original core left.
    setup=(m/'main_menu/setup/1337/10_countries.txt').read_text(encoding='utf-8-sig')
    countries=manifest['countries'];tags={c['tag'] for c in countries};domain={l for c in countries for l in c['locations']}
    owners={};newcounts=Counter();coreleft=[]
    for tag,_,b,e,_ in blocks(setup,2):
        chunk=setup[b:e]
        for key,_,x,y,_ in blocks(chunk,0):
            ls=[t.value for t in tokens(chunk[x:y]) if t.value in domain]
            if ls and tag not in tags and (key.startswith('own_') or key.startswith('control') or key=='our_cores_conquered_by_others'):coreleft.append((tag,key,ls))
            if key.startswith('own_control_'):
                for loc in ls:
                    if loc in owners:raise AssertionError(f'duplicate owner for {loc}: {owners[loc]} / {tag}')
                    owners[loc]=tag;newcounts[tag]+=1
    check('every domain location has exactly one new owner',set(owners)==domain and not coreleft)
    check('ownership matches manifest',all(all(owners[l]==c['tag'] for l in c['locations']) for c in countries))
    native_defs=set()
    for category in ('cultures','religions'):
        for f in (game/'in_game/common'/category).glob('*.txt'):
            native_defs.update(k for k,*_ in blocks(f.read_text(encoding='utf-8-sig'),0))
    check('all capital cultures and religions exist',all(c['culture'] in native_defs and c['religion'] in native_defs for c in countries))
    loc_file=m/'main_menu/localization/simp_chinese/hbe_l_simp_chinese.yml'
    check('Chinese localization has UTF8 BOM',loc_file.read_bytes().startswith(b'\xef\xbb\xbf'))
    loc_keys=set(re.findall(r'^\s+([^\s:]+):','\n'.join(p.read_text(encoding='utf-8-sig') for p in (m/'main_menu/localization/simp_chinese').glob('*.yml')),re.M))
    refs=[];internal_variables=set()
    for f in script_files:
        s=f.read_text(encoding='utf-8-sig')
        internal_variables.update(re.findall(r'(?:set_variable|change_variable|save_scope_value_as)\s*=\s*\{[^{}]*?\bname\s*=\s*(hbe\w+)',s))
        refs+=re.findall(r'\b(?:title|desc|name|text|loc|leader_title_key|format)\s*=\s*(hbe[\w.]+|HBE_\w+)',s)
    check('all custom text references localized',set(refs)-internal_variables<=loc_keys)
    check('native numeric literals include a leading zero',all(not re.search(r'\b\w+\s*=\s*-?\.\d',f.read_text(encoding='utf-8-sig')) for f in script_files))
    char_keys={k for k,*_ in blocks((m/'main_menu/setup/1337/05_hbe_characters.txt').read_text(encoding="utf-8-sig"),1)}
    check('36 distinct starting rulers exist',char_keys=={f'hbe_ruler_{t.lower()}' for t in tags})
    election=(m/'in_game/common/resolutions/hbe_election.txt').read_text(encoding="utf-8-sig")
    check('7 seat election requires a strict majority', 'scope:highest_vote > scope:total_votes_needed' in election)
    modifiers=(m/'main_menu/common/static_modifiers/hbe_modifiers.txt').read_text(encoding="utf-8-sig")
    tianfu=next(modifiers[b:e] for k,_,b,e,_ in blocks(modifiers,0) if k=='hbe_tianfu')
    check('Tianfu has 7% food/construction and 5% disease resistance',all(abs(float(re.search(r'\b'+k+r'\s*=\s*([\d.]+)',tianfu)[1])-v)<1e-9 for k,v in {'local_monthly_food_modifier':.07,'local_construction_speed':.07,'local_disease_resistance':.05}.items()))
    effects=(m/'in_game/common/scripted_effects/hbe_effects.txt').read_text(encoding="utf-8-sig")
    check('Tianfu is permanent and idempotent','NOT = { has_location_modifier = hbe_tianfu }' in effects and 'modifier = hbe_tianfu years = -1' in effects)
    check('external owners have the Tianfu modifier removed','remove_location_modifier = hbe_tianfu' in effects)
    expected_nodes = 80 + manifest.get('industry_transmission', {}).get('advance_count', 0) + manifest.get('early_research_design', {}).get('military_count', 0) + manifest.get('local_affairs_research', {}).get('advance_count', 0) + manifest.get('civic_teahouse', {}).get('advance_count', 0)
    check('current decisions and native research node count',manifest['decisions']==97+len(manifest.get('formables_units_v031',{}).get('formations',[])) and manifest['research_nodes']==expected_nodes)
    check('35 regional milestone missions and repeatable services',manifest['regional_missions']==35 and manifest['recurring_services']==7)
    pulse=(m/'in_game/common/on_action/hbe_on_actions.txt').read_text(encoding="utf-8-sig")
    check('centennial content and repeatable pulse persist','current_year >= 1437' in pulse and 'yearly_country_pulse' in pulse and 'current_year < 1457' not in pulse)
    from validate_open_diplomacy_v032 import validate as validate_open_diplomacy
    validate_open_diplomacy(m,manifest,check)
    io_setup=(m/'main_menu/setup/1337/99_hbe_organizations.txt').read_text(encoding='utf-8')
    check('IO members precede leaders in the persistent reader',all(s.index('members =')<s.index('leader =') for k,_,b,e,_ in blocks(io_setup,1) for s in [io_setup[b:e]]))
    check('release metadata and manifest version match',manifest['version'] in ('0.2.0','0.2.1','0.3.0','0.3.1','0.3.2','0.3.3','0.4.0') and json.loads((m/'.metadata/metadata.json').read_text(encoding='utf-8'))['version']==manifest['version'])
    # Detect accidentally unlinked references to our own effects, events or variables.
    hbe_refs=set()
    variable_refs=set()
    for f in script_files:
        s=f.read_text(encoding='utf-8-sig')
        hbe_refs.update(re.findall(r'\b(hbe_[a-z0-9_]+)\s*=\s*(?:yes|no)',s))
        variable_refs.update(re.findall(r'(?:name\s*=|has_variable\s*=|set_variable\s*=|remove_variable\s*=)\s*(hbe_[a-z0-9_]+)',s))
    check('custom effect and trigger references resolve',hbe_refs<=set(custom)|variable_refs)
    sit=(m/'in_game/common/situations/hbe_banquet.txt').read_text(encoding='utf-8-sig')
    expansion=manifest['expansion']
    banquet=(m/'in_game/common/scripted_effects/hbe_banquet_effects.txt').read_text(encoding='utf-8-sig')
    new_decisions=(m/'in_game/common/decisions/hbe_banquet_decisions.txt').read_text(encoding='utf-8-sig')
    new_events=(m/'in_game/events/hbe_banquet_events.txt').read_text(encoding='utf-8-sig')
    check('native situation starts deterministically within first year','current_date >= 1337.7.1' in sit and 'monthly_spawn_chance = monthly_spawn_chance_unique' in sit)
    check('native spawn chance is 100 percent','monthly_spawn_chance_unique = 1' in (game/'main_menu/common/script_values/default_values.txt').read_text(encoding='utf-8-sig'))
    check('participation includes all IO members and subjects','visible = { is_member_of_international_organization = international_organization:hbe_empire }' in sit)
    check('monthly registration does not filter emperor or subjects','every_international_organization_member = { hbe_banquet_register = yes' in banquet)
    check('situation persists after charters and 1457','current_year < 1457' not in banquet and 'can_end = { NOT = { exists = international_organization:hbe_empire } }' in sit)
    if manifest['version'] in ('0.2.1','0.3.0','0.3.1','0.3.2','0.3.3','0.4.0'):
        check('two-year accounts are once per situation','var:hbe_round_month >= 24' in banquet and 'on_monthly = { hbe_banquet_monthly = yes }' in sit)
        check('cooperative settlement uses adaptive contribution target','var:hbe_feast_total >= var:hbe_feast_required' in banquet)
        check('funding requires real scaled payment','gold >= hbe_feast_fee' in new_decisions and 'hbe_fund_project' in banquet)
        check('obsolete promises and duplicate feast decision entrances hidden', 'hbe_project_pledge = {' in new_decisions and new_decisions.count('potential = { always = no }')==24)
        check('centennial arrangement needs a century and actual successes','current_year >= 1437' in banquet and 'var:hbe_completed_projects >= 6' in banquet)
    else:
        check('three-year accounts are once per situation','var:hbe_round_month >= 36' in banquet and 'on_monthly = { hbe_banquet_monthly = yes }' in sit)
        check('delivery requires all three roles and moderate dispute','var:hbe_role_1 >= 1 var:hbe_role_2 >= 1 var:hbe_role_3 >= 1 var:hbe_dispute < 75' in banquet)
        check('funding requires enough gold and does not supply role credits','gold >= 3' in new_decisions and 'hbe_fund_project' in banquet)
        check('pledges require later actual payment','var:hbe_round_month = 12' in banquet and 'gold >= 4' in banquet and 'add_gold = -4' in banquet)
        check('centennial charter needs 100 years and real projects','current_year >= 1437' in new_decisions and 'var:hbe_completed_projects >= 30' in new_decisions)
    check('exactly 36 historical capital seats are counted',sum(banquet.count('location:'+c['capital']+'.owner ?=') for c in countries)==36)
    check('each of seven circles needs strict local majority',banquet.count('var:hbe_ballot_seat_votes > ')==7 and 'var:hbe_ballot_circle_votes >= 4' in banquet)
    check('79 inherited banquet events plus authored story expansion',len([k for k,*_ in blocks(new_events,0) if k.startswith('hbe_banquet.')])==79 and manifest['events']==117+manifest.get('playable_stories',{}).get('event_count',0)+manifest.get('ending_art_v031',{}).get('new_afterwords',0)+manifest.get('common_defense_v032',{}).get('visible_events',0))
    check('all 36 princes have personal events',sum('has_or_had_tag = '+c['tag'] in new_events for c in countries)==36)
    check('regional researched options and late recurring events exist',('hbe_choice_western_tea_horse_1' in new_events if 'event_choices' in manifest else 'hbe_tech_western_tea_horse_3' in new_events) and 'current_year >= 1457' in new_events)
    check('situation has native GUI panel',(m/'in_game/gui/panels/situation/hbe_banquet.gui').is_file())
    flagdefs=(m/'main_menu/common/coat_of_arms/coat_of_arms/hbe_placeholders.txt').read_text(encoding='utf-8-sig')
    flagkeys=[k for k,*_ in blocks(flagdefs,0)]
    check('all 36 flag tag definitions exist exactly once',len(flagkeys)==36 and set(flagkeys)==tags)
    flaghashes=[]
    for f in expansion['flags']:
        texture=m/'main_menu/gfx/coat_of_arms'/f['texture_category']/f['texture'];b=texture.read_bytes()
        check('DDS heraldic charge '+f['tag'],b[:4]==b'DDS ' and struct.unpack_from('<2I',b,12)==(512,512) and len(b)==128+512*512*4 and hashlib.sha256(b).hexdigest()==f['sha256'] and f['inscription']=='' and f['font'] is None)
        check('native flag textures exist '+f['tag'],all((game/'main_menu/gfx/coat_of_arms'/ref['category']/ref['file']).is_file() for ref in f['native_assets']))
        flaghashes.append(f['sha256'])
    check('all 36 inscription textures are unique',len(set(flaghashes))==36)
    check('all 36 native heraldic definitions are unique',len({f['definition_sha256'] for f in expansion['flags']})==36)
    check('country event AI choices use native MTTH base syntax','ai_chance = { value' not in new_events and 'ai_chance = { base' in new_events)
    art=manifest['icon_art'];tech_art=art['technology_icons'];other_art=art['other_icons']
    check('eight sprite atlases map exactly 64 unique research icons',art['atlases']==8 and len(tech_art)==64 and len({e['key'] for e in tech_art})==64 and len({e['sha256'] for e in tech_art})==64)
    research_script=(m/'in_game/common/advances/hbe_advances.txt').read_text(encoding='utf-8-sig')
    for e in tech_art:
        p=m/e['image'];b=p.read_bytes()
        check('painted research icon '+e['key'],b[:4]==b'DDS ' and struct.unpack_from('<2I',b,12)==(256,256) and hashlib.sha256(b).hexdigest()==e['sha256'] and ('icon = '+e['key'].replace('hbe_tech_central_hills_8','hbe_tech_central_hills_witness_8')) in research_script and (m/'main_menu/gfx/interface/advance'/f'{e["key"]}.dds').read_bytes()==b)
    check('ten point icons and one native situation icon',len(other_art)==11 and sum(e['kind']=='point' for e in other_art)==10 and any(e['key']=='hbe_banquet' for e in other_art))
    for e in other_art:
        p=m/e['image'];b=p.read_bytes()
        check('painted specialty icon '+e['key'],b[:4]==b'DDS ' and struct.unpack_from('<2I',b,12)==(128,128) and hashlib.sha256(b).hexdigest()==e['sha256'])
    check('native font icons registered',(m/'main_menu/gui/shared/hbe_font_icons.gui').read_text(encoding='utf-8').count('texticon =')==10)
    full=manifest['full_art']
    def painted_dds(name,path,dimensions,expected):
        b=(m/path).read_bytes()
        check(name,b[:4]==b'DDS ' and struct.unpack_from('<2I',b,12)==dimensions and len(b)==128+dimensions[0]*dimensions[1]*4 and hashlib.sha256(b).hexdigest()==expected)
    check('12 painted event backgrounds serve all 96 events',len(full['event_backgrounds'])==12 and len(full['event_mapping'])==96 and len({e['id'] for e in full['event_mapping']})==96)
    event_keys={e['key'] for e in full['event_backgrounds']}
    check('event scene mapping resolves',all(e['scene'] in event_keys for e in full['event_mapping']))
    scene_script=(m/'in_game/gfx/scenes/hbe_event_scenes.txt').read_text(encoding='utf-8-sig')
    image_script=(m/'in_game/gfx/images/hbe_event_backgrounds.txt').read_text(encoding='utf-8-sig')
    database=(m/'loading_screen/gfx/illustrations/database/hbe_event_illustrations.txt').read_text(encoding='utf-8-sig')
    all_events='\n'.join(f.read_text(encoding='utf-8-sig') for f in (m/'in_game/events').glob('hbe*events.txt'))
    for e in full['event_backgrounds']:
        key=e['key'];painted_dds('painted event background '+key,e['image'],(440,1080),e['sha256'])
        check('private native illustration scene '+key,f'hbe_event_scene_{key} = ' in scene_script and f'list = "hbe_event_background_{key}"' in scene_script and f'hbe_event_art_{key}' in database and f'gfx/interface/hbe/events/{key}.dds' in image_script)
    event_blocks={key:all_events[a:b] for key,_,a,b,_ in blocks(all_events,0)}
    check('96 event illustration tags link private scenes',all(('1000 = hbe_event_art_feast_two_parties' if 'art_v021' in manifest and e['id'] in ['hbe_banquet.1','hbe_banquet.2','hbe_banquet.4','hbe_banquet.5','hbe_banquet.7'] else f'1000 = hbe_event_art_{e["scene"]}') in event_blocks[e['id']] for e in full['event_mapping']))
    check('native portrait layers retained and native scene database not overridden','list = "characters_regular"' in scene_script and not (m/'in_game/gfx/scenes/00_scenes_events.txt').exists())
    check('eight organization emblems and dedicated panel files',len(full['organizations'])==8 and {e['key'] for e in full['organizations']}=={'hbe_empire'}|{'hbe_circle_'+r[0] for r in manifest['regions']})
    for e in full['organizations']:
        painted_dds('organization emblem '+e['key'],e['icon'],(128,128),e['icon_sha256'])
        painted_dds('organization panel '+e['key'],e['panel'],(440,1080),e['panel_sha256'])
    panel=full['situation_panel'];painted_dds('painted banquet panel',panel['image'],(440,1080),panel['sha256'])
    check('banquet GUI uses painted panel',any(p in (m/'in_game/gui/panels/situation/hbe_banquet.gui').read_text(encoding='utf-8-sig') for p in ['gfx/interface/hbe/panels/hbe_banquet.dds','gfx/interface/hbe/panels/hbe_feast_two_parties_v021.dds']))
    pictures=full['decision_pictures']
    check('seven atlases supply 70 unique non-research pictures',full['decision_atlases']==7 and len(pictures)==70 and len({e['key'] for e in pictures})==70 and len({e['sha256'] for e in pictures})==70)
    decision_scripts='\n'.join(f.read_text(encoding='utf-8-sig') for f in (m/'in_game/common/decisions').glob('hbe*decisions.txt'))
    decision_blocks={key:decision_scripts[a:b] for key,_,a,b,_ in blocks(decision_scripts,0)}
    for e in pictures:
        painted_dds('painted non-research decision '+e['key'],e['image'],(440,1080),e['sha256'])
        check('decision picture linked '+e['key'],any(p in decision_blocks[e['key']] for p in [f'gfx/interface/hbe/decisions/{e["key"]}.dds',f'gfx/interface/hbe/v021/decisions/{e["key"]}.dds']))
    legacy_gui_files=[f for f in (m/'in_game/gui').rglob('*.gui') if not ('local_affairs' in manifest and f.name=='hbe_local_affairs.gui')]
    check('all current decision images exist and no active checker placeholders outside the explicit affairs prototype',len(decision_blocks)==97+len(manifest.get('formables_units_v031',{}).get('formations',[])) and 'placeholder.dds' not in decision_scripts and all((m/'main_menu'/p).is_file() for p in re.findall(r'image\s*=\s*"([^"]+)"',decision_scripts)) and not any('placeholder.dds' in f.read_text(encoding='utf-8-sig') for f in legacy_gui_files))
    check('all implicit decision titles and catalogue entries localized',all(k+'.title' in loc_keys and k+'.title.entry' in loc_keys and k+'.desc.entry' in loc_keys for k in decision_blocks))
    check('all visible decisions registered in native country category',all('decision_category = country_specific_decisions' in b and ('tags = {' in b or k.startswith('hbe_form_')) for k,b in decision_blocks.items()))
    native=json.loads((ROOT/'data/native_content_v011.json').read_text(encoding='utf-8'))
    advances=(m/'in_game/common/advances/hbe_advances.txt').read_text(encoding='utf-8-sig')
    advance_blocks={key:advances[a:b] for key,_,a,b,_ in blocks(advances,0)}
    check('64 research icons belong to native advance nodes only',len(advance_blocks)==64 and not any(k.startswith('hbe_tech_') for k in decision_blocks) and all('icon = '+k in b and k+'_desc' in loc_keys for k,b in advance_blocks.items()))
    from apply_presentation_v040 import origin_for_tags
    check('all native research nodes retain progression gates and originating-circle potentials',all(('current_year' not in advance_blocks[e['key']] if 'formables_units_v031' in manifest else 'current_year >= '+str(e['year']) in advance_blocks[e['key']]) and (('hbe_research_origin_'+origin_for_tags(e['tags'],manifest)+' = yes' in advance_blocks[e['key']]) if 'presentation_v040' in manifest else all('has_or_had_tag = '+t in advance_blocks[e['key']] for t in e['tags'])) for e in native['advances']))
    check('native starting technology does not pregrant regional research',all('starting_technology_level = 99' in b for b in advance_blocks.values()))
    def excludes(body,key):
        return any(re.search(r'(?:has_advance\s*=\s*'+re.escape(key)+r'\b|hbe_advance_gate_'+re.escape(key)+r'\s*=\s*yes)',body[b:e]) for k,_,b,e,_ in blocks(body) if k=='NOT')
    check('seven pairs of research branches are mutually exclusive',all(excludes(advance_blocks['hbe_tech_'+r[0]+'_3'],'hbe_tech_'+r[0]+'_6') and excludes(advance_blocks['hbe_tech_'+r[0]+'_6'],'hbe_tech_'+r[0]+'_3') for r in manifest['regions']))
    check('36 single-country events indexed without new autonomous event rolls',len(native['events'])==36 and all('monthly_chance = 0' in event_blocks[e['id']] and 'dynamic_historical_event' in event_blocks[e['id']] and 'fire_only_once = yes' in event_blocks[e['id']] for e in native['events']))
    check('60 shared or recurring events keep their original dispatch',len(native['non_dhe_event_ids'])==60 and all('dynamic_historical_event' not in event_blocks[k] and 'fire_only_once' not in event_blocks[k] for k in native['non_dhe_event_ids']))
    check('36 distinct native country histories and lobby profiles localized',len(native['country_biographies'])==36 and len({e['body'] for e in native['country_biographies']})==36 and all('country_history_'+e['tag'] in loc_keys and 'country_description_category_desc_hbe_profile_'+e['tag'].lower() in loc_keys for e in native['country_biographies']))
    check('36 redesigned flags contain no text or nameplates',flagdefs.count('texture = "te_hbe_crest_')==36 and 'hbe_name' not in flagdefs and all(f['inscription']=='' and f['nameplate'] is None for f in expansion['flags']))
    texts=json.loads((ROOT/'data/decision_texts_v011.json').read_text(encoding='utf-8'))
    check('70 decisions have full flavor prose separate from mechanics',len(texts)==70 and all('\n\n' in e['body'] and len(e['body'])>=75 for e in texts))
    prose=json.loads((ROOT/'data/event_texts_v01.json').read_text(encoding='utf-8'))
    check('all 96 events have independent two-paragraph Bashu narratives',manifest['event_prose']['events_rewritten']==96 and len(prose)==96 and len({e['body'] for e in prose})==96 and all('\n\n' in e['body'] and len(e['body'])>=120 for e in prose))
    check('rewritten event narratives omit HRE jokes',all(not any(word in e['body']+e['title'] for word in ('神罗','欧洲','祖传选票','椅子比别家','菜单先来')) for e in prose))
    concepts='\n'.join(p.read_text(encoding='utf-8-sig') for p in (m/'main_menu/common/game_concepts').glob('hbe*.txt'))
    concept_keys={key for key,*_ in blocks(concepts,0)}
    loc_text=loc_file.read_text(encoding='utf-8-sig')
    references=set(re.findall(r"Concept\('(hbe_(?:term|history)_[a-z_]+)'",loc_text))
    check('native glossary definitions have localized names and descriptions',all('game_concept_'+key in loc_keys and 'game_concept_'+key+'_desc' in loc_keys for key in concept_keys))
    check('all inline hover links resolve to private native game concepts',references<=concept_keys and len(references)>=45)
    check('mechanic and historical hover guides are present',len([k for k in concept_keys if k.startswith('hbe_term_')])==manifest['player_guides']['mechanic_concepts'] and len([k for k in concept_keys if k.startswith('hbe_history_')])==12+manifest.get('history_guides_v031',{}).get('new_concepts',0))
    check('all narrative descriptions include valid hover links',all('Concept(' in event_blocks[e['id']] or f'{e["id"]}.desc:' in loc_text and 'Concept(' in next(line for line in loc_text.splitlines() if line.lstrip().startswith(e['id']+'.desc:')) for e in prose))
    check('guide icon textures exist',all((m/'main_menu/gfx/interface/icons'/str(p+'.dds')).exists() for p in re.findall(r'texture\s*=\s*"([^"]+)"',concepts)))
    check('ledger narratives preserve dynamic state readouts',"GetVariable('hbe_yiqi')" in loc_text and "GetVariable('hbe_contribution')" in loc_text)
    from validate_unit_detail_art_v031 import validate_unit_detail_art
    validate_unit_detail_art(m,ROOT,game,manifest,check)
    from validate_social_expansion import validate_social_expansion
    validate_social_expansion(m,ROOT,game,manifest,loc_keys,check)
    from validate_annex_industry import validate_annex_industry
    validate_annex_industry(m,manifest,loc_keys,check)
    from validate_ending_art_v031 import validate_ending_art
    validate_ending_art(m,ROOT,manifest,loc_keys,check)
    from validate_story_logic_v031 import validate_story_logic
    story_paths=validate_story_logic(m,ROOT,manifest,loc_keys,check)
    from validate_red_turban_actions_v032 import validate as validate_red_turban_actions
    validate_red_turban_actions(m,game,manifest,check)
    from validate_common_defense_v032 import validate as validate_common_defense
    validate_common_defense(m,manifest,check)
    from validate_western_tributes_v032 import validate as validate_western_tributes
    validate_western_tributes(m,game,manifest,check)
    from validate_diplomacy_restraint_v032 import validate as validate_diplomacy_restraint
    validate_diplomacy_restraint(m,game,manifest,check)
    from validate_industry_transmission import validate as validate_industry_transmission
    validate_industry_transmission(m,ROOT,game,manifest,check)
    from validate_western_opening_v032 import validate as validate_western_opening
    validate_western_opening(m,game,manifest,check)
    from apply_production_advance_semantics_v032 import validate as validate_production_semantics
    validate_production_semantics(m,game,manifest,check)
    from apply_advance_display_v032 import validate as validate_advance_display
    validate_advance_display(m,game,manifest,check)
    from apply_opening_identity_v032 import validate as validate_opening_identity
    validate_opening_identity(m,game,manifest,check)
    from apply_population_identity_v032 import validate as validate_population_identity
    validate_population_identity(m,ROOT,game,manifest,check)
    from validate_early_research import validate as validate_early_research
    validate_early_research(m,ROOT,game,manifest,check)
    from validate_age2_military import validate as validate_age2_military
    validate_age2_military(m,ROOT,game,manifest,check)
    if 'panda_loading' in manifest:
        from apply_panda_loading import validate as validate_panda_loading
        validate_panda_loading(m,ROOT,game,manifest,check)
    if 'opening_territory' in manifest:
        from apply_opening_territory import validate as validate_opening_territory
        validate_opening_territory(m,ROOT,manifest,check)
    from validate_local_affairs import validate as validate_local_affairs
    validate_local_affairs(m,ROOT,game,manifest,check)
    from apply_presentation_v040 import validate as validate_presentation
    validate_presentation(m,manifest,check)
    failed=[row['check'] for row in checks if not row['passed']]
    report=dict(status='failed' if failed else 'passed',checks=checks,check_count=len(checks),failed=failed,story_paths=story_paths,gameplay_validation='Structural and resource-reference checks; runtime and visual verification reported separately',version=manifest['version'])
    if a.report:a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if failed:
        print(f'FAIL: {len(failed)} of {len(checks)} checks: '+ '; '.join(failed))
        raise SystemExit(1)
    print(f'PASS: {len(checks)} checks; 36 princes, 164 locations, 7 circles, {manifest["research_nodes"]} research nodes.')

if __name__=='__main__':main()
