import json,re,struct,hashlib
from pdxscript import blocks
def validate_social_expansion(mod,root,game,manifest,loc,check):
    data=manifest['social_expansion'];art=json.loads((root/'data/social_art_v020.json').read_text())
    def resolve(key):return manifest.get('observer_hotfix',{}).get('active_advance_rename',{}).get(key,key)
    def read(p):return (mod/p).read_text(encoding='utf-8-sig')
    buildings=read('in_game/common/building_types/hbe_civic_buildings.txt');units=read('in_game/common/unit_types/hbe_civic_units.txt')
    advances=read('in_game/common/advances/hbe_civic_advances.txt');old=read('in_game/common/advances/hbe_advances.txt')
    slots=19 if 'observer_hotfix' in manifest else 23 if 'technology_rewards' in manifest else 16
    check('16 native special buildings with employment and real maintenance',len(blocks(buildings,0))==16 and buildings.count('is_special = yes')==16 and buildings.count('employment_size = 0.15')==16 and buildings.count('unique_production_methods =')==slots)
    check('all buildings unlocked by preexisting native advances',all('unlock_building = '+b['key'] in old for b in data['buildings']))
    check('all buildings have domain or circle location potential',buildings.count('location_potential = { is_in_scripted_geography =')==16)
    check('seven nationwide institution limits include unfinished construction',buildings.count('country_has_no_other_copy_of_building')==sum(b['unique_country'] for b in data['buildings']))
    check('9 native special recruitable unit types in one shared family',len(blocks(units,0))==9 and units.count('family = hbe_civic_special_family')==9 and units.count('hide = no buildable = yes levy = no is_special = yes')==9)
    check('unit family shares supply-scaled 20 percent capacity','limit = hbe_civic_special_limit' in read('in_game/common/unit_families/hbe_civic_families.txt') and 'multiply = 0.2 divide = 0.5' in read('in_game/common/script_values/hbe_civic_values.txt'))
    check('all nine unit types use real supply and geographic recruitment',units.count('construction_demand =')==9 and units.count('maintenance_demand =')==9 and units.count('is_in_scripted_geography = scripted_geography:hbe_geo_')==9)
    check('early and late unit unlocking ties to actual advances',all('unlock_unit = '+u['key'] in old+advances for u in data['units']))
    check('two late types replace their base troops', 'upgrades_to = hbe_trained_river' in units and 'upgrades_to = hbe_permanent_pass' in units and units.count('current_year >= 1457')==2)
    check('native research catalogue now has 80 nodes',len(blocks(old,0))+len(blocks(advances,0))==manifest['research_nodes']==80)
    allnodes={k:(old+advances)[a:b] for k,_,a,b,_ in blocks(old+advances,0)}
    ages={k:re.search(r'age = (\w+)',body)[1] for k,body in allnodes.items()}
    check('native visual prerequisite edges stay inside their era',all(ages[k]==ages[p] for k,body in allnodes.items() for p in re.findall(r'requires = (hbe_\w+)',body)))
    check('late original and civic courses appear in the second era',sum(v=='age_2_renaissance' for v in ages.values())>=22)
    history=read('in_game/common/customizable_localization/country_history.txt')
    check('agenda country histories selected before vanilla cultural fallback',all('localization_key = country_history_'+c['tag']+' trigger = { has_or_had_tag = '+c['tag']+' }' in history for c in manifest['countries']) and history.index('country_history_BAB')<history.index('country_history_china'))
    check('16 new nodes have icons, localization and year gates',len(blocks(advances,0))==16 and all(k['key'] in loc and k['key']+'_desc' in loc and 'current_year >= '+str(k['year']) in advances for k in data['advances']))
    check('regional institution advances accept either A or B qualification',all('OR = { has_advance = hbe_tech_'+r[0]+'_4 has_advance = hbe_tech_'+r[0]+'_7 }' in advances and 'OR = { has_advance = hbe_tech_'+r[0]+'_5 has_advance = '+resolve('hbe_tech_'+r[0]+'_8')+' }' in advances for r in manifest['regions']))
    check('no opening free grants of new research',advances.count('starting_technology_level = 99')==16)
    law=read('in_game/common/laws/hbe_civic_law.txt')
    check('native law has exactly three policies and five-year switch lock',all(p+' = {' in law for p in ('hbe_levy_policy','hbe_communal_policy','hbe_paid_policy')) and law.count('years = 5')==3 and 'locked = { has_variable = hbe_policy_lock }' in law and 'type = country' in law)
    check('two native estate privileges and seven parliamentary topics',len(blocks(read('in_game/common/estate_privileges/hbe_civic_privileges.txt'),0))==2 and len(blocks(read('in_game/common/parliament_issues/hbe_civic_issues.txt'),0))==7)
    eff=read('in_game/common/scripted_effects/hbe_civic_effects.txt')
    check('clamped burden with three-year relief and yearly recovery', 'var:hbe_burden > 100' in eff and 'var:hbe_burden < 0' in eff and 'add = -3' in eff)
    check('seven offices have real-delivery eligibility, five-year terms and 2-office cap',all('has_variable = hbe_recent_delivery_'+r[0] in eff and 'name = hbe_office_'+r[0]+'_term value = yes years = 5' in eff for r in manifest['regions']) and eff.count('var:hbe_office_count < 2')==7)
    check('old service markers are updated at completion rather than commitment',all('hbe_record_service_'+r[0]+' = yes remove_variable = hbe_service_'+r[0]+'_pending' in read('in_game/common/scripted_effects/hbe_effects.txt') for r in manifest['regions']))
    check('service starts account for policy-specific affordability',read('in_game/common/decisions/hbe_decisions.txt').count('value = hbe_paid_bill add = 4')==7)
    check('existing regiments persist when over supply limit', 'hbe_civic_over_supply' in eff and 'destroy' not in eff and 'delete' not in eff)
    check('all three charter outcomes continue after 1457','var:hbe_charter = 1' in read('in_game/events/hbe_civic_events.txt') and 'var:hbe_charter = 2' in read('in_game/events/hbe_civic_events.txt') and 'current_year >= 1457' in read('in_game/common/decisions/hbe_civic_decisions.txt'))
    check('21 new events localized with repeat-safe dispatch',len(data['events'])==21 and all(e['id']+'.title' in loc and '\n\n' in e['body'] for e in data['events']) and 'fire_only_once' not in read('in_game/events/hbe_civic_events.txt'))
    check('27 native country decisions have multi-paragraph narrative',len(data['decisions'])==27 and all('\n\n' in e['body'] and e['key']+'.title.entry' in loc for e in data['decisions']))
    check('57 distinct new icon/illustration cells plus 3 event scenes',len(art['exports'])==60 and len({e['sha256'] for e in art['exports']})==60)
    for e in art['exports']:
        b=(mod/e['path']).read_bytes();w,h=e['dimensions']
        check('expansion artwork '+e['key'],b[:4]==b'DDS ' and struct.unpack_from('<2I',b,12)==(h,w) and len(b)==128+w*h*4 and hashlib.sha256(b).hexdigest()==e['sha256'])
        if e['kind']=='units':check('explicit unit illustration selector '+e['key'],'is_unit_type = '+e['key'] in read('in_game/gfx/unit_illustrations/hbe_civic_illustrations.txt') and (mod/'main_menu/gfx/interface/illustrations/units/masks'/f'{e["key"]}.dds').is_file())
    check('all five new mechanics have native hover concepts',all('game_concept_'+k+'_desc' in loc for k in data['concepts']))
    # Verify actual native names rather than carrying typo demand IDs into the engine.
    demands='\n'.join(f.read_text(encoding='utf-8-sig') for f in (game/'in_game/common/goods_demand').glob('*.txt'))
    demandkeys={k for k,*_ in blocks(demands,0)}|{'hbe_institution_construction'}
    check('unit and building construction/maintenance IDs resolve',set(re.findall(r'(?:construction_demand|maintenance_demand) = (\w+)',buildings+units))<=demandkeys)
