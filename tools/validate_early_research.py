"""Contracts for separate industry, military and civic research."""
from pathlib import Path
import json,re,struct
from PIL import Image
from pdxscript import blocks
from build_early_research import CONFIG,MIL_FILE,TRIGGER_FILE,load_config,military_key,scalars

def validate(mod,root,game,manifest,check):
    if 'early_research_design' not in manifest:return
    mod,root,game=map(Path,(mod,root,game));config=load_config(root);data=manifest['early_research_design'];permission=config['cross_permission']
    read=lambda rel:(mod/rel).read_text(encoding='utf-8-sig')
    definitions={}
    for rel in ('in_game/common/advances/hbe_advances.txt','in_game/common/advances/hbe_civic_advances.txt',MIL_FILE,'in_game/common/advances/hbe_industry_transmission.txt'):
        text=read(rel);definitions.update({key:text[a:b] for key,_,a,b,_ in blocks(text,0)})
    check('91 active research nodes include exactly seven new military nodes',len(definitions)==91==manifest['research_nodes'] and len(blocks(read(MIL_FILE),0))==7)
    units=read('in_game/common/unit_types/hbe_civic_units.txt');unit_defs={key:units[a:b] for key,_,a,b,_ in blocks(units,0)}
    buildings=read('in_game/common/building_types/hbe_civic_buildings.txt');building_defs={key:buildings[a:b] for key,_,a,b,_ in blocks(buildings,0)}
    unit_unlocks={unit:[key for key,body in definitions.items() if re.search(r'\bunlock_unit\s*=\s*'+re.escape(unit)+r'\b',body)] for unit in unit_defs}
    for row in config['military']:
        key=military_key(row);body=definitions[key];values={k:v for k,v,_,_ in scalars(body)};region=row['region']
        expected={c['tag'] for c in manifest['countries'] if c['region']==region}
        tags=set(re.findall(r'has_or_had_tag\s*=\s*(\w+)',body))
        check(key+' retains stable originating-circle visibility',tags==expected and 'has_variable = hbe_home' not in body)
        for country in manifest['countries']:
            check(key+' visible only to '+country['tag']+' native circle',(country['tag'] in tags)==(country['region']==region))
        check(key+' researched separately in age one after the regional foundation',values['age']=='age_1_traditions' and values['requires']=='hbe_tech_'+region+'_1' and values['starting_technology_level']=='99' and float(values['research_cost'])==config['military_cost'])
        check(key+' grants only its own base unit',unit_unlocks[row['unit']]==[key] and re.findall(r'unlock_unit\s*=\s*(\w+)',body)==[row['unit']])
        check(key+' no national army buffs automatic research or calendar gates',not any(k in body for k in ('country_modifier','current_year','current_date','research_advance','combat_power','discipline','army_maintenance_efficiency')))
        check(key+' industry node no longer grants an army','unlock_unit' not in definitions['hbe_tech_'+region+'_2'])
        troop=unit_defs[row['unit']]
        check(key+' local recruitment reads its actual military research','has_advance = '+key in troop and 'has_advance = hbe_tech_'+region+'_2' not in troop)
        check(key+' guest military still requires studied local military training','hbe_has_regional_military_training = yes' in troop and 'has_variable = hbe_guest_'+region in troop)
        check(key+' keeps 500-man inherited strength and unchanged maintenance interface','max_strength = 0' in troop or 'max_strength = 0.3' in troop)
        for b in row['buildings']:
            owners=[name for name,value in definitions.items() if 'unlock_building = '+b in value]
            check(b+' is unlocked only by its military technology',owners==[key])
            check(b+' actual construction reads the same military technology','has_advance = '+key in building_defs[b])
        civ='hbe_civic_'+region+'_1';civfields={k:v for k,v,_,_ in scalars(definitions[civ])}
        check(civ+' is honestly a second-age administrative node',civfields['age']=='age_2_renaissance' and civfields['requires']=='renaissance_development')
        sprite=Image.open(root/f'assets/technology_icons/{key}.png').convert('RGBA');bounds=sprite.getchannel('A').getbbox()
        check(key+' complete 256px icon has transparent margins',sprite.size==(256,256) and sprite.getchannel('A').getextrema()==(0,255) and bounds and min(bounds[0],bounds[1],256-bounds[2],256-bounds[3])>=10)
        for folder in ('advance','hbe/technology'):
            image=(mod/f'main_menu/gfx/interface/{folder}/{key}.dds').read_bytes()
            check(key+' '+folder+' uses exact exported sprite',image[:4]==b'DDS ' and struct.unpack_from('<2I',image,12)==(256,256) and image[128:]==sprite.tobytes('raw','BGRA'))
    for key,expected in config['modifiers'].items():
        actual={name:float(value) for name,value,_,_ in scalars(definitions[key]) if re.fullmatch(r'-?\d+(?:\.\d+)?',value) and name not in ('research_cost','starting_technology_level','content_priority')}
        check(key+' has only its budgeted permanent modifiers',actual==expected)
    check('granary begins in age one while its agricultural production remains later', 'unlock_building = hbe_community_granary' in definitions['hbe_tech_central_hills_1'] and 'has_advance = hbe_tech_central_hills_1' in building_defs['hbe_community_granary'] and 'unlock_production_method = hbe_central_hills_basic_production' in definitions['hbe_tech_central_hills_3'])
    for region in ('eastern_river','northern_shudao'):
        body=definitions['hbe_civic_'+region+'_2']
        check(region+' advanced military requires its actual base military training','hbe_has_military_'+region+' = yes' in body and 'has_advance = hbe_military_' not in body and 'requires = renaissance_development' in body and 'requires = hbe_civic_common_2' not in body)
    check('military qualification registry contains exactly seven military technologies',set(re.findall(r'has_advance\s*=\s*(\w+)',read(TRIGGER_FILE)))=={'hbe_military_'+r['region'] for r in config['military']})
    check('craftsmen exchanges owns a registered country boolean',permission+' = yes' in definitions['hbe_tech_common_4'] and permission+' = { boolean = yes game_data = { category = country } }' in read('main_menu/common/modifier_type_definitions/hbe_early_research.txt'))
    check('cross-circle permission uses ordinary native modifier icons',('positive = "gfx/interface/icons/modifier_types/'+permission+'.dds"') in read('main_menu/common/modifier_icons/hbe_early_research.txt') and (mod/f'main_menu/gfx/interface/icons/modifier_types/{permission}.dds').exists())
    decisions=read('in_game/common/decisions/hbe_civic_decisions.txt');decision_defs={key:decisions[a:b] for key,_,a,b,_ in blocks(decisions,0)}
    for key,body in decision_defs.items():
        if key.startswith('hbe_guest_'):
            check(key+' reads the real cross-circle boolean and preserves actual prerequisites','modifier:'+permission+' = yes' in body and all(s in body for s in ('var:hbe_yiqi >= 60','has_policy = hbe_communal_policy','any_owned_location','gold >= hbe_paid_bill')))
    check('guest receipt synchronization also reads the boolean',read('in_game/common/scripted_effects/hbe_guest_license_effects.txt').count('modifier:'+permission+' = yes')==7)
    check('local council belongs to the original ledger foundation','has_advance = hbe_tech_common_1' in decision_defs['hbe_civic_council'])
    check('garrison provisioning belongs to studied military organization','hbe_has_regional_military_training = yes' in decision_defs['hbe_civic_garrison'] and 'has_advance = hbe_civic_common_1' not in decision_defs['hbe_civic_garrison'])
    privileges=read('in_game/common/estate_privileges/hbe_civic_privileges.txt');priv_defs={key:privileges[a:b] for key,_,a,b,_ in blocks(privileges,0)}
    check('estate guarantees moved to their own thematic civilian research','has_advance = hbe_tech_common_2' in priv_defs['hbe_village_witnesses'] and 'has_advance = hbe_tech_common_5' in priv_defs['hbe_guild_payment_guarantee'])
    for lang in ('simp_chinese','english'):
        text=read(f'main_menu/localization/{lang}/hbe_early_research_l_{lang}.yml')
        check(lang+' has all military labels descriptions and native modifier labels',all(k in text for k in ['MODIFIER_TYPE_NAME_'+permission,'MODIFIER_TYPE_DESC_'+permission]+[military_key(row)+'_desc' for row in config['military']]))
    check('new research never overrides the global advance GUI',not (mod/'main_menu/gui/shared/advances_tooltips.gui').exists())
