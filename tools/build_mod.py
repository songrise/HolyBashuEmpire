"""Generate the standalone EU5 0.1 mod from an installed game's setup.

Run with Python 3.10+. No changes are made to the installation. The large setup
override is generated locally and pinned to the source hash in build_manifest.
"""
import argparse, colorsys, csv, hashlib, json, re, struct, zlib
from collections import OrderedDict
from pathlib import Path
from pdxscript import blocks, tokens, apply_edits
from build_banquet import build_banquet
from build_icon_assets import build_icon_assets
from build_full_art_assets import build_full_art_assets
from build_event_prose import apply_event_prose
from build_player_guides import build_player_guides
from build_native_content import build_native_content
from build_social_expansion import build_social_expansion
from build_technology_rewards import build_technology_rewards
from build_bashu_ai import build_bashu_ai
from build_simple_banquet import build_simple_banquet
from build_quality_hotfix import build_quality_hotfix
from build_opening_pacts import build_opening_pacts
from build_art_v021 import build_art_v021
from build_special_goods import prepare_special_goods,finish_special_goods
from build_event_choices import build_event_choices

ROOT = Path(__file__).resolve().parents[1]
REGIONS = [
 ('chengdu_plain','成都平原圈','chengdu','水权储备','hbe_water','修渠分水','官学讲会'),
 ('southern_salt_wine','川南盐酒圈','yibin','盐引信用','hbe_salt','井灶公账','宴席采办'),
 ('eastern_river','重庆川东圈','baxian','江运互保','hbe_river','江岸转运','河防巡察'),
 ('northern_shudao','川北蜀道圈','langzhong','轮戍履约','hbe_roads','关隘轮戍','驿路接力'),
 ('central_hills','川中丘陵圈','suining','义仓储备','hbe_grain','分仓赈贷','契约见证'),
 ('western_tea_horse','川西茶马圈','yandao','商队互保','hbe_tea','茶马采办','山门调停'),
 ('southwestern_valleys','川西南山谷圈','jianchang','地方共治','hbe_valleys','山谷互市','地方议约'),
]

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def write(path, text, bom=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    clean='\n'.join(re.sub(r'^[ \t]+',lambda m:m[0].expandtabs(4),line.rstrip()) for line in text.rstrip().splitlines())+'\n'
    path.write_text(clean, encoding='utf-8-sig' if bom else 'utf-8', newline='\n')
def csv_write(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def table_nodes():
    text=(ROOT/'data/technology_design.md').read_text(encoding='utf-8-sig')
    tables=re.findall(r'(?ms)^\| 节点 \|.*?(?=\n\s*\n)',text)
    catalog=[]
    for table_index,t in enumerate(tables):
        rows=[s for s in t.splitlines()[2:] if s.startswith('| ')]
        for index,row in enumerate(rows):
            cells=[s.strip() for s in row.strip('|').split('|')]
            group='common' if table_index==0 else REGIONS[table_index-1][0]
            name,req,desc=cells[:3]
            key=f'hbe_tech_{group}_{index+1}'
            predecessor=None
            if group=='common':
                p=[None,0,1,None,3,4,None,6][index]
                gate=[1337,1342,1372,1337,1352,1372,1337,1372][index]
            else:
                p=[None,0,1,2,3,1,5,6][index]
                gate=[1337,1342,1352,1372,1397,1352,1372,1397][index]
            if p is not None: predecessor=f'hbe_tech_{group}_{p+1}'
            catalog.append(dict(key=key,group=group,index=index,name=name,description=desc,
                                predecessor=predecessor,year=gate,years=3 if index<2 else 5 if index in (2,5) else 8,
                                cost=3 if index<2 else 6 if index in (2,5) else 10))
    assert len(catalog)==64,(len(tables),len(catalog))
    return catalog

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--game-dir',type=Path,required=True)
    ap.add_argument('--output',type=Path,default=ROOT/'mod/holy_bashu_empire')
    args=ap.parse_args();game=args.game_dir/'game';out=args.output
    rows=list(csv.DictReader((ROOT/'data/prince_locations.csv').open(encoding='utf-8-sig')))
    assert len(rows)==164 and len({r['location_id'] for r in rows})==164
    # Match the current 36 province groups, preserving all location IDs.
    groups=OrderedDict()
    for row in rows: groups.setdefault(row['original_province_id'],[]).append(row)
    assert len(groups)==36
    existing=set()
    for f in (game/'in_game/setup/countries').glob('*.txt'):
        existing.update(k for k,*_ in blocks(f.read_text(encoding='utf-8-sig'),0))
    # Reserve dormant and localized tags as well as currently defined countries.
    for f in (game/'main_menu/localization').rglob('country_names_l_*.yml'):
        existing.update(re.findall(r'^\s+([A-Z]{3}):',f.read_text(encoding='utf-8-sig'),re.M))
    unused=[f'B{a}{b}' for a in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' for b in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
            if f'B{a}{b}' not in existing]
    countries=[];loc_to_tag={};region_to_tags={k:[] for k,*_ in REGIONS};electors={}
    group_names={
        'chengdu_province':'成都锦官公国','xuzhou_sichuan_province':'叙州盐酒商邦',
        'chongqing_province':'重庆山城公国','baoning_province':'保宁蜀道侯国',
        'suining_province':'遂宁义仓侯国','yazhou_province':'雅州茶马侯国',
        'sichuan_province':'建昌共治侯国','jiading_province':'嘉定山门侯国'}
    for index,(province,locations) in enumerate(groups.items()):
        region=locations[0]['circle_design_key'];tag=unused[index]
        preferred=next((cap for key,_,cap,*_ in REGIONS if key==region and any(r['location_id']==cap for r in locations)),None)
        # Installed location IDs sometimes differ from their commonly used name.
        if region=='eastern_river' and province=='chongqing_province':
            preferred=next(r['location_id'] for r in locations if r['planned_location_name']=='巴县')
        if region=='southwestern_valleys' and province=='sichuan_province':
            preferred=locations[0]['location_id']
        capital=next((r for r in locations if r['location_id']==preferred),locations[0])
        base=capital['prince_group'].replace('诸侯组','')
        name=group_names.get(province,base+'侯国')
        countries.append(dict(tag=tag,name=name,province=province,region=region,capital=capital['location_id'],
                              culture=capital['original_culture'],religion=capital['original_religion'],
                              locations=[r['location_id'] for r in locations],group=base))
        loc_to_tag.update({r['location_id']:tag for r in locations});region_to_tags[region].append(tag)
        if province in ('chengdu_province','xuzhou_sichuan_province','chongqing_province','baoning_province',
                        'suining_province','yazhou_province','sichuan_province'):electors[region]=tag
    assert len(electors)==7
    emperor=electors['chengdu_plain'];locs=set(loc_to_tag)
    loc={}
    def L(key,value):
        assert key not in loc,key
        loc[key]=value
    def put(rel,text,bom=False):
        # The script reader wants BOM; the bookmark persistent reader treats it as a token.
        write(out/rel,text,bom or (rel.endswith('.txt') and not rel.startswith('main_menu/setup/')))
    # Same fields as the game's -mod_stubber output; do not depend on a scratch directory.
    metadata=dict(name='',id='',version='',supported_game_version='',short_description='',tags=[],relationships=[],game_custom_data={})
    metadata.update(name='神圣巴蜀帝国 Holy Bashu Empire',version='0.3.1',supported_game_version='1.4.*',
                    short_description='架空巴蜀：七个帝国圈、三十六诸侯，天府加成、选举、地区经营与百年传承。',
                    tags=['Alternative History','Gameplay'])
    put('.metadata/metadata.json',json.dumps(metadata,ensure_ascii=False,indent=2))
    # Patch ownership/core token spans only; comments, other countries and setups survive.
    original_path=game/'main_menu/setup/1337/10_countries.txt'
    original=original_path.read_text(encoding='utf-8-sig');edits=[];removed=[]
    for key,start,body,end,finish in blocks(original):
        if key in ('own_control_core','own_control_integrated','own_control_conquered','own_control_colony',
                   'own_core','own_conquered','own_integrated','own_colony','control_core','control','our_cores_conquered_by_others'):
            for token in tokens(original[body:end]):
                if token.value in locs:
                    edits.append((body+token.start,body+token.end,''));removed.append(token.value)
    patched=apply_edits(original,edits)
    # Move a surviving original country's capital if its former capital is in our domain.
    edits=[]
    for tag,start,body,end,finish in blocks(patched,2):
        chunk=patched[body:end]
        cap=re.search(r'\bcapital\s*=\s*([a-zA-Z0-9_]+)',chunk)
        if not cap or cap.group(1) not in locs:continue
        owned=[]
        for key,_,b,c,_ in blocks(chunk,0):
            if key.startswith('own_'):owned += [t.value for t in tokens(chunk[b:c]) if t.value not in ('{','}','=')]
        replacement=owned[0] if owned else cap.group(1)
        if owned:edits.append((body+cap.start(1),body+cap.end(1),replacement))
    patched=apply_edits(patched,edits)
    new_setup=[];definitions=[];chars=[];dynasties=[];flags=[]
    for i,c in enumerate(countries):
        tag=c['tag'];character=f'hbe_ruler_{tag.lower()}';dynasty=f'hbe_dynasty_{tag.lower()}'
        rgb=tuple(round(v*255) for v in colorsys.hsv_to_rgb((i*0.61803398875)%1,.45,.82))
        definitions.append(f'''{tag} = {{
    color = rgb {{ {' '.join(map(str,rgb))} }}
    color2 = rgb {{ 236 216 158 }}
    culture_definition = {c['culture']}
    religion_definition = {c['religion']}
    description_category = administrative
    difficulty = 2
}}''')
        new_setup.append(f'''{tag} = {{
    own_control_core = {{ {' '.join(c['locations'])} }}
    include = "hbe_monarchy"
    country_rank = rank_duchy
    capital = {c['capital']}
    government = {{ type = monarchy ruler = {character} }}
}}''')
        chars.append(f'''{character} = {{
    first_name = {{ name = hbe_given_name_{i%8} }}
    culture = {c['culture']}
    religion = {c['religion']}
    adm = {45+i%20} dip = {40+(i*3)%25} mil = {35+(i*7)%30}
    birth_date = {1295+i%15}.1.1
    birth = {c['capital']}
    dynasty = {dynasty}
    tag = {tag}
}}''')
        dynasties.append(f'{dynasty} = {{ name = {{ name = {dynasty} }} home = {c["capital"]} }}')
        flags.append(f'{tag} = {{ pattern = "pattern_diagonal_split_01.dds" color1 = "red" color2 = "gold" }}')
        L(tag,c['name']);L(tag+'_ADJ',c['group']);L(tag+'_ADJ2',c['group']);L(dynasty,c['group']+'氏')
    # Replace the existing 1337 ownership file (all other starts remain unaffected).
    put('main_menu/setup/1337/10_countries.txt',patched+'\n\ncountries = { countries = {\n'+'\n'.join(new_setup)+'\n} }')
    put('in_game/setup/countries/hbe_countries.txt','\n'.join(definitions))
    put('main_menu/setup/1337/05_hbe_characters.txt','character_db = {\n'+'\n'.join(chars)+'\n}')
    put('main_menu/setup/1337/04_hbe_dynasties.txt','dynasty_manager = {\n'+'\n'.join(dynasties)+'\n}')
    template=(game/'main_menu/setup/templates/chinese_monarchy.txt').read_text(encoding='utf-8-sig')
    template=template.replace('three_departments_system','autocracy')
    template=re.sub(r'^\s*marriage_law\s*=\s*dishu_system\s*$', '',template,flags=re.M)
    put('main_menu/setup/templates/hbe_monarchy.txt',template)
    put('main_menu/common/coat_of_arms/coat_of_arms/hbe_placeholders.txt','\n'.join(flags))
    for i,name in enumerate(('守义','承川','维新','景和','允诚','怀远','明理','济民')):L(f'hbe_given_name_{i}',name)
    geo=['hbe_domain = { location = { '+' '.join(sorted(locs))+' } }']
    for key,name,*_ in REGIONS:
        owned=[r['location_id'] for r in rows if r['circle_design_key']==key]
        geo.append(f'hbe_geo_{key} = {{ location = {{ {" ".join(owned)} }} }}');L(f'hbe_geo_{key}',name)
    put('in_game/common/scripted_geography/hbe_geography.txt','\n'.join(geo));L('hbe_domain','神圣巴蜀帝国地域')
    # Tags certify indigenous polities, geography limits protection to the domain.
    tag_trigger='OR = { '+' '.join(f'has_or_had_tag = {c["tag"]}' for c in countries)+' }'
    triggers=f'''hbe_is_prince = {{
    {tag_trigger}
    capital ?= {{ is_in_scripted_geography = scripted_geography:hbe_domain }}
}}
hbe_is_domain_polity = {{
    OR = {{ hbe_is_prince = yes AND = {{ is_rebel_country = yes capital ?= {{ is_in_scripted_geography = scripted_geography:hbe_domain }} }} }}
}}
hbe_war_is_internal = {{
    OR = {{
        AND = {{ scope:attacker = {{ hbe_is_domain_polity = yes }} scope:defender = {{ hbe_is_domain_polity = yes }} }}
        AND = {{ scope:attacker = {{ hbe_is_domain_polity = no }} scope:defender = {{ hbe_is_domain_polity = no }} }}
    }}
}}'''
    put('in_game/common/scripted_triggers/hbe_triggers.txt',triggers)
    # Independent organization: never overwrite the European HRE.
    org=f'''hbe_empire = {{
    unique = yes has_target = no has_leader_country = yes leader_type = character
    leader_title_key = HBE_EMPEROR
    leader = {{ leader_country ?= {{ ruler ?= {{ add_to_list = leaders }} }} }}
    leader_change_trigger_type = rulerchange leader_change_method = vote
    leadership_election_resolution = hbe_election
    disband_if_no_leader = no disband_minimum_member_count = 1
    expel_members_who_are_targets_of_other_members = no
    join_defensive_wars = Never join_offensive_wars = Never
    show_on_diplomatic_map = yes show_as_overlord_on_map_trigger = {{ always = yes }}
    land_ownership_rule = hbe_land_ownership
    can_declare_war = {{ custom_tooltip = {{ text = hbe_isolation_tt hbe_war_is_internal = yes }} }}
    create_visible_trigger = {{ always = no }} invite_visible_trigger = {{ always = no }}
    can_join_trigger = {{ hbe_is_prince = yes }}
    can_leave_trigger = {{ always = no }} auto_leave_trigger = {{ hbe_is_prince = no }}
    auto_disband_trigger = {{ always = no }}
    can_lead_trigger = {{ hbe_is_prince = yes is_subject = no has_ruler = yes }}
    special_statuses_implemented = {{ hbe_elector }}
    variables = {{ hbe_guoqi = {{ format = HBE_GUOQI_DISPLAY change_format = VARIABLE_CHANGE_FORMAT min = 0 max = 100 start = 40 }} }}
    leader_modifier = {{ monthly_prestige = 0.05 }}
}}'''
    circle_defs=[];ios=[f'add_international_organization = {{ type = hbe_empire creation_date = 1337.4.1 members = {{ {" ".join(c["tag"] for c in countries)} }} leader = {emperor} locations = {{ {" ".join(sorted(locs))} }} hbe_elector = {{ {" ".join(electors.values())} }} }}']
    for key,name,*_ in REGIONS:
        typ=f'hbe_circle_{key}';ts=region_to_tags[key]
        circle_defs.append(f'''{typ} = {{
    unique = yes has_target = no has_leader_country = yes leader_type = country
    leader_change_trigger_type = none
    disband_if_no_leader = no disband_minimum_member_count = 1
    expel_members_who_are_targets_of_other_members = no
    create_visible_trigger = {{ always = no }} invite_visible_trigger = {{ always = no }}
    can_join_trigger = {{ OR = {{ {' '.join('has_or_had_tag = '+t for t in ts)} }} }}
    can_leave_trigger = {{ always = no }} auto_leave_trigger = {{ hbe_is_prince = no }}
    auto_disband_trigger = {{ always = no }}
    join_defensive_wars = Never join_offensive_wars = Never
    can_declare_war = {{ hbe_war_is_internal = yes }}
}}''')
        ios.append(f'add_international_organization = {{ type = {typ} creation_date = 1337.4.1 members = {{ {" ".join(ts)} }} leader = {electors[key]} }}')
        L(typ,name);L(typ+'_desc',name+'是神圣巴蜀帝国的地区协作组织，所属府州诸侯保有自己的军队、财政与帝国议事权。')
    put('in_game/common/international_organizations/hbe_empire.txt',org+'\n'+'\n'.join(circle_defs))
    put('in_game/common/international_organization_land_ownership_rules/hbe_land.txt','''hbe_land_ownership = {
    modifier = { }
    can_add_trigger = { always = yes }
    can_add_location_trigger = { is_in_scripted_geography = scripted_geography:hbe_domain }
    can_remove_trigger = { always = no }
    can_remove_location_trigger = { always = no }
    on_added = { } on_removed = { }
    ai_desire_to_add = { value = 0 }
}''')
    L('hbe_land_ownership','巴蜀敕书地域')
    put('main_menu/setup/1337/99_hbe_organizations.txt','international_organization_manager = {\n'+'\n'.join(ios)+'\n}')
    put('in_game/common/international_organization_special_statuses/hbe_statuses.txt','''hbe_elector = {
    max_countries = 7 priority = 10 elector = yes
    can_bestow_trigger = { is_member_of_international_organization = scope:recipient is_subject = no }
    auto_bestowal_trigger = { always = yes }
    auto_rescind_trigger = { NOT = { is_member_of_international_organization = scope:recipient } }
    special_status_power = { value = 1 }
}''')
    put('main_menu/common/modifier_type_definitions/hbe_types.txt','''hbe_elector_can_participate_in_parliament = {
    boolean = yes game_data = { category = internationalorganization }
}
hbe_elector_agenda_impact = {
    percent = yes game_data = { category = internationalorganization }
}''')
    L('hbe_elector_can_participate_in_parliament','巴蜀选侯可参与议事')
    L('hbe_elector_agenda_impact','巴蜀选侯议案影响')
    for key,title,desc in (
        ('hbe_elector_can_participate_in_parliament','巴蜀选侯议事资格','巴蜀选侯在共同议事中的资格。'),
        ('hbe_elector_agenda_impact','巴蜀选侯议案影响','巴蜀选侯在共同议案中的影响。')):
        L('MODIFIER_TYPE_NAME_'+key,title);L('MODIFIER_TYPE_DESC_'+key,desc)
    put('main_menu/common/modifier_icons/hbe_icons.txt','''hbe_elector_can_participate_in_parliament = {
    positive = "gfx/interface/icons/modifier_types/elector_can_participate_in_parliament.dds"
    negative = "gfx/interface/icons/modifier_types/elector_can_participate_in_parliament.dds"
}
hbe_elector_agenda_impact = {
    positive = "gfx/interface/icons/modifier_types/elector_agenda_impact.dds"
    negative = "gfx/interface/icons/modifier_types/elector_agenda_impact.dds"
}''')
    org_names=[('hbe_empire','神圣巴蜀帝国')]+[(f'hbe_circle_{r[0]}',r[1]) for r in REGIONS]
    put('in_game/common/biases/hbe_opinions.txt','\n'.join(f'io_opinion_{key} = {{ value = 10 }}' for key,_ in org_names))
    for key,name in org_names:
        L('io_opinion_'+key,'共同参加'+name)
        L('diplomatic_status_'+key+'_name',name+'成员')
        L('diplomatic_status_'+key+'_tooltip','参与'+name+'的共同事务。')
        L(key+'_list_who_tt',name+'的成员诸侯')
    for k,v in {'hbe_guoqi_desc':'共同信用与公共事务余力，范围 0–100。',
                'HBE_EMPEROR_MALE':'巴蜀皇帝','HBE_EMPEROR_FEMALE':'巴蜀女皇',
                'hbe_election_desc':'七席选侯以严格多数选出巴蜀皇帝。',
                'hbe_election_specific':'投票选择巴蜀皇帝','hbe_election_specific_desc':'从合资格的成员诸侯中选择。',
                'vote_in_hbe_election':'投票：巴蜀皇帝','vote_in_hbe_election_desc':'每名选侯有一票。'}.items():L(k,v)
    # Message types are registered from one fixed file; preserve the native list.
    messages=(game/'main_menu/gui/messagetypes.txt').read_text(encoding='utf-8-sig')
    for prefix in ('PERFORM','WE_PERFORM','OTHER_PERFORMS'):
        message=f'{prefix}_hbe_election_ACTION'
        messages+=f'\n{message} = {{ log = yes onmap = no popup = no idle = no option = yes pausepopup = no message_category = government }}\n'
        L(message,'巴蜀选侯投票')
        for suffix in ('HEADER','TITLE','DESC','LOG','MAP','SETUP'):
            L(message+'_'+suffix,'巴蜀选侯就皇帝人选投票。')
    put('main_menu/gui/messagetypes.txt',messages)
    put('in_game/common/resolutions/hbe_election.txt','''hbe_election = {
    loc = hbe_election potential = { always = yes } allow = { }
    ai_tick = monthly is_live = { always = yes } requires_explicit_votes = no
    can_vote = { scope:actor = { is_member_of_international_organization = scope:recipient
        has_special_status_in_international_organization = { type = special_status:hbe_elector international_organization = scope:recipient } } }
    votes = { add = { desc = hbe_elector value = 1 } }
    total_votes_needed = { add = { value = scope:total_votes_available multiply = 0.5 } }
    should_finalize_vote = { scope:recipient = { international_organization_has_leader = no } scope:highest_vote > scope:total_votes_needed }
    select_trigger = { looking_for_a = international_organization target_flag = recipient name = choose_international_organization
        column = { data = name } visible = { international_organization_type = international_organization_type:hbe_empire } enabled = { } }
    select_trigger = { looking_for_a = country source = recipient target_flag = vote allow_self = yes name = election_select_country
        none_available_msg_key = election_select_no_countries default_sort = country_tax_base column = { data = name }
        visible = { can_lead_international_organization = scope:recipient } enabled = { } }
    effect = { scope:recipient = { set_leader_country = scope:vote } }
    ai_will_do = { add = { desc = hbe_election_merit value = scope:vote.country_tax_base multiply = 2 }
        add = { desc = hbe_election_trust value = "scope:actor.opinion(scope:vote)" multiply = 0.5 } }
}''')
    put('in_game/common/join_war_rules/hbe_isolation.txt','''hbe_isolation_join_rule = {
    join_war_disabled_trigger = {
        OR = {
            AND = { hbe_is_domain_polity = yes OR = { scope:first_leader = { hbe_is_domain_polity = no } scope:second_leader = { hbe_is_domain_polity = no } } }
            AND = { hbe_is_domain_polity = no OR = { scope:first_leader = { hbe_is_domain_polity = yes } scope:second_leader = { hbe_is_domain_polity = yes } } }
        }
    }
}''')
    L('hbe_empire','神圣巴蜀帝国');L('hbe_empire_desc','巴蜀诸侯的自治会盟。天府富庶，诸侯各有算盘。')
    for k,v in {'HBE_EMPEROR':'巴蜀皇帝','hbe_elector':'巴蜀选侯','hbe_elector_desc':'七个帝国圈各有一名选侯。',
                'hbe_election':'巴蜀皇帝选举','hbe_election_merit':'经营实力','hbe_election_trust':'诸侯关系',
                'HBE_GUOQI_DISPLAY':'锅气：$VALUE|0$','hbe_isolation_join_rule':'巴蜀自治盟约',
                'hbe_isolation_tt':'自治盟约限制圈内与圈外之间的战争；帝国内部战争仍可进行。',
                'hbe_tianfu':'天府之国','hbe_tianfu_desc':'地里有粮，城里有匠；诸侯再吵，日子照过。\n粮食产出 +10%，本地建造速度 +10%。'}.items():L(k,v)
    L('STATIC_MODIFIER_NAME_hbe_tianfu','天府之国')
    L('STATIC_MODIFIER_NAME_hbe_project_food','公共粮政投入')
    L('STATIC_MODIFIER_NAME_hbe_project_build','地方协作')
    statics=['hbe_tianfu = { local_monthly_food_modifier = 0.10 local_construction_speed = 0.10 }',
             'hbe_project_food = { local_monthly_food_modifier = 0.05 }',
             'hbe_project_build = { local_construction_speed = 0.05 }']
    L('hbe_project_food','公共粮政投入');L('hbe_project_food_desc','真实投入维护后的临时粮政收益。')
    L('hbe_project_build','地方协作');L('hbe_project_build_desc','真实投入后的临时工程收益。')
    put('main_menu/common/static_modifiers/hbe_modifiers.txt','\n'.join(statics))
    # Idempotent maintenance and research completion. Data survives ruler changes.
    effects=['''hbe_clamp_yiqi = {
    if = { limit = { var:hbe_yiqi > 100 } set_variable = { name = hbe_yiqi value = 100 } }
    if = { limit = { var:hbe_yiqi < 0 } set_variable = { name = hbe_yiqi value = 0 } }
}
hbe_apply_tianfu = {
    every_owned_location = {
        limit = { is_in_scripted_geography = scripted_geography:hbe_domain NOT = { has_location_modifier = hbe_tianfu } }
        add_location_modifier = { modifier = hbe_tianfu years = -1 }
    }
}
hbe_add_credit = {
    change_variable = { name = hbe_yiqi add = 3 }
    hbe_clamp_yiqi = yes
    international_organization:hbe_empire ?= {
        change_variable = { name = hbe_guoqi add = 1 }
        if = { limit = { var:hbe_guoqi > 100 } set_variable = { name = hbe_guoqi value = 100 } }
    }
}''']
    init=['if = { limit = { NOT = { has_variable = hbe_initialized } } set_variable = hbe_initialized set_variable = { name = hbe_yiqi value = 40 } add_gold = 5 trigger_event_non_silently = { id = hbe.1 days = 1 } }']
    for key,_,_,_,counter,*_ in REGIONS:
        tags=region_to_tags[key]
        init.append(f'''if = {{ limit = {{ OR = {{ {' '.join('has_or_had_tag = '+t for t in tags)} }} NOT = {{ has_variable = hbe_home_{key} }} }}
            set_variable = hbe_home_{key} set_variable = {{ name = {counter} value = 20 }} }}''')
    effects.append('hbe_initialize = {\n'+'\n'.join(init)+'\nhbe_apply_tianfu = yes\n}')
    # Research uses decisions and timed projects, not an unverified new vanilla tree UI.
    catalog=table_nodes();decisions=[];monthly=[];events=[]
    def decision(key,title,desc,potential,allow,effect,cost=0,ai=10):
        L(key,title);L(key+'.desc',desc);L(key+'.a','执行')
        image=f'gfx/interface/hbe/technology/{key}.dds' if key.startswith('hbe_tech_') else 'gfx/interface/hbe/placeholder.dds'
        decisions.append(f'''{key} = {{
    decision_category = other_decisions image = "{image}"
    potential = {{ hbe_is_prince = yes {potential} }}
    allow = {{ {allow} {'gold >= '+str(cost) if cost else ''} }}
    ai_will_do = {{ value = {ai} }}
    option = {{ name = {key}.a ai_chance = {{ value = 100 }} effect = {{ {'add_gold = -'+str(cost) if cost else ''} {effect} }} }}
}}''')
    for n in catalog:
        key=n['key'];idx=n['index'];group=n['group'];allowed=''
        if group!='common':allowed=f'has_variable = hbe_home_{group}'
        req=f'has_variable = {n["predecessor"]}' if n['predecessor'] else ''
        opposite=''
        if group!='common' and idx in (2,5):opposite=f'NOT = {{ has_variable = hbe_tech_{group}_{6 if idx==2 else 3} }}'
        decision(key,'研究：'+n['name'],f'{n["description"]}\n费用 {n["cost"]}，研究 {n["years"]} 年；须达到 {n["year"]} 年。',
                 f'{allowed} NOT = {{ has_variable = {key} }}',
                 f'current_year >= {n["year"]} {req} {opposite} NOT = {{ has_variable = hbe_research_pending }}',
                 f'set_variable = hbe_research_pending set_variable = {key}_pending set_variable = {{ name = hbe_research_timer value = yes years = {n["years"]} }}',cost=n['cost'])
        monthly.append(f'''if = {{ limit = {{ has_variable = {key}_pending NOT = {{ has_variable = hbe_research_timer }} }}
            remove_variable = {key}_pending remove_variable = hbe_research_pending set_variable = {key}
            hbe_add_credit = yes trigger_event_non_silently = {{ id = hbe.2 }} }}''')
    # Seven real regional state counters, recurring services, and debt repayment.
    for ri,(group,name,_,label,counter,action_a,action_b) in enumerate(REGIONS):
        pending=f'hbe_service_{group}_pending';timer=f'hbe_service_{group}_timer'
        project=f'hbe_service_{group}'
        decision(project,action_a+'与'+action_b,
                 f'投入 4 金币，三年后交付本圈事业，取得 10 点{label}、3 点义气与五年经营收益。\n当前{label}：[ROOT.GetVariable(\'{counter}\').GetValue|0]。',
                 f'has_variable = hbe_home_{group}',
                 f'has_variable = hbe_tech_{group}_1 NOT = {{ has_variable = {pending} }} NOT = {{ has_variable = hbe_service_cooldown }}',
                 f'set_variable = {pending} set_variable = {{ name = {timer} value = yes years = 3 }} set_variable = {{ name = hbe_service_cooldown value = yes years = 5 }}',cost=4)
        monthly.append(f'''if = {{ limit = {{ has_variable = {pending} NOT = {{ has_variable = {timer} }} }}
            remove_variable = {pending} change_variable = {{ name = {counter} add = 10 }}
            if = {{ limit = {{ var:{counter} > 100 }} set_variable = {{ name = {counter} value = 100 }} }}
            hbe_add_credit = yes every_owned_location = {{ limit = {{ is_in_scripted_geography = scripted_geography:hbe_geo_{group} }}
                add_location_modifier = {{ modifier = {'hbe_project_food' if ri in (0,4) else 'hbe_project_build'} years = 5 mode = replace }} }}
            trigger_event_non_silently = {{ id = hbe.3 }} }}''')
        # Actual generational progression; goals work for small and unified countries.
        for stage,(year,phase) in enumerate(zip((1337,1352,1372,1397,1437),('起业','成长','旧约重审','地区重组','百年章程'))):
            previous=f'has_variable = hbe_mission_{group}_{stage}' if stage else ''
            tech_req=f'has_variable = hbe_tech_{group}_1' if stage==0 else f'has_variable = hbe_tech_{group}_2' if stage==1 else f'OR = {{ has_variable = hbe_tech_{group}_{4 if stage==2 else 5} has_variable = hbe_tech_{group}_{7 if stage==2 else 8} }}'
            key=f'hbe_mission_{group}_{stage+1}';cost=2+stage*2
            decision(key,name+'：'+phase,f'{phase}验收需要研究、持续交付与真实出资。消耗 10 点{label}和 {cost} 金币；义气增加 5，锅气增加 2。',
                     f'has_variable = hbe_home_{group} NOT = {{ has_variable = {key} }}',
                     f'current_year >= {year} {previous} {tech_req} var:{counter} >= 10',
                     f'set_variable = {key} change_variable = {{ name = {counter} subtract = 10 }} change_variable = {{ name = hbe_yiqi add = 5 }} hbe_clamp_yiqi = yes international_organization:hbe_empire ?= {{ change_variable = {{ name = hbe_guoqi add = 2 }} if = {{ limit = {{ var:hbe_guoqi > 100 }} set_variable = {{ name = hbe_guoqi value = 100 }} }} }} add_prestige = 2',cost=cost)
        eventid=100+ri
        L(f'hbe.{eventid}.title',action_a+'，账谁来认？')
        L(f'hbe.{eventid}.desc',f'{name}的新主持翻出旧合同，发现大家都记得出过力，只有账本忘了谁付钱。\n本圈{label}可以承担一次纠纷；也可以拨款核账，或把账暂时搁下。')
        L(f'hbe.{eventid}.a','按旧约履行。');L(f'hbe.{eventid}.b','拨三金，重新核账。');L(f'hbe.{eventid}.c','先喝茶，账下次算。')
        events.append(f'''hbe.{eventid} = {{
    type = country_event title = hbe.{eventid}.title desc = hbe.{eventid}.desc outcome = neutral
    illustration_tags = {{ 10 = regular 10 = interior }}
    trigger = {{ hbe_is_prince = yes has_variable = hbe_home_{group} NOT = {{ has_variable = hbe_flavor_cooldown }} }}
    immediate = {{ set_variable = {{ name = hbe_flavor_cooldown value = yes years = 5 }} }}
    option = {{ name = hbe.{eventid}.a trigger = {{ var:{counter} >= 10 }} change_variable = {{ name = {counter} subtract = 10 }} hbe_add_credit = yes }}
    option = {{ name = hbe.{eventid}.b trigger = {{ gold >= 3 }} add_gold = -3 change_variable = {{ name = {counter} add = 5 }} hbe_add_credit = yes }}
    option = {{ name = hbe.{eventid}.c change_variable = {{ name = hbe_yiqi subtract = 5 }} hbe_clamp_yiqi = yes add_prestige = -1 }}
}}''')
    decision('hbe_salt_loan','发行盐引周转','取得 15 金币，增加 10 点盐债；每年需支付 1 金币利息，欠债上限 30。',
             'has_variable = hbe_home_southern_salt_wine',
             'has_variable = hbe_tech_southern_salt_wine_4 NOT = { has_variable = hbe_loan_cooldown } OR = { NOT = { has_variable = hbe_salt_debt } var:hbe_salt_debt <= 20 }',
             'if = { limit = { NOT = { has_variable = hbe_salt_debt } } set_variable = { name = hbe_salt_debt value = 0 } } add_gold = 15 change_variable = { name = hbe_salt_debt add = 10 } set_variable = { name = hbe_loan_cooldown value = yes years = 5 }',ai=0)
    decision('hbe_salt_repay','归还盐债','支付 10 金币，归还 10 点盐债并恢复义气。',
             'has_variable = hbe_salt_debt','var:hbe_salt_debt >= 10',
             'change_variable = { name = hbe_salt_debt subtract = 10 } hbe_add_credit = yes',cost=10,ai=20)
    decision('hbe_status','查看巴蜀会盟账本','查看义气、锅气、研究进度和自治盟约。','', 'always = yes','trigger_event_non_silently = { id = hbe.4 }',ai=0)
    decision('hbe_assembly','召开帝国茶会','皇帝出资召集诸侯，讨论公共经费与自治。五年可召开一次。',
             'is_leader_of_international_organization = international_organization:hbe_empire',
             'NOT = { has_variable = hbe_assembly_cooldown }',
             'set_variable = { name = hbe_assembly_cooldown value = yes years = 5 } trigger_event_non_silently = { id = hbe.5 }',cost=5,ai=5)
    monthly.extend(f'if = {{ limit = {{ has_variable = {r[4]} var:{r[4]} > 100 }} set_variable = {{ name = {r[4]} value = 100 }} }}' for r in REGIONS)
    monthly_effect='hbe_country_monthly = {\nif = { limit = { hbe_is_prince = yes } hbe_initialize = yes\n'+'\n'.join(monthly)+'\n}\nelse = { every_owned_location = { limit = { has_location_modifier = hbe_tianfu } remove_location_modifier = hbe_tianfu } }\n}'
    effects.append(monthly_effect)
    put('in_game/common/scripted_effects/hbe_effects.txt','\n'.join(effects))
    put('in_game/common/decisions/hbe_decisions.txt','\n'.join(decisions))
    # Startup, research completion, service completion, status, five dated turning points.
    simple=[(1,'巴蜀敕书，诸侯开席','大元以稳定盐粮、茶马供应换取巴蜀自治。朝廷写的是治事会盟，我们印的是神圣帝国。\n你是三十六个独立诸侯之一；七圈协作，七席选侯。天府之国常驻加成：粮食产出与本地建造速度各 +10%。','先把本府经营起来。'),
            (2,'课题告成','本国资助的地方课题已经完成。后续研究与地区验收现在可以在决议中推进。','记入本府账簿。'),
            (3,'事业交付，账目入册','三年的地方投入已经交付。地区履约、义气与临时经营收益已结算；这项事业五年后可以再办。','这次确实出了力。'),
            (4,'会盟账本','本国义气：[ROOT.GetVariable(\'hbe_yiqi\').GetValue|0] / 100。\n帝国锅气：[GetUniqueInternationalOrganization(\'hbe_empire\').MakeScope.GetVariable(\'hbe_guoqi\').GetValue|0] / 100。\n地区研究通过决议资助，完成计时后自动交付；同一时刻只能研究一项。\n自治盟约限制域外宣战与战争召集。百年经营继续开放，天府加成不会到期。','账看完了，继续忙。')]
    for stage,(year,title,desc) in enumerate(((1352,'第一代事业，第二本账','地方课题开始长成圈级事业。接下来的验收需要更成熟的研究与更多地区履约。'),
          (1372,'旧约重审，人人有功','三十五年过去，旧合同的受益者与新主持需要重新认账。深化课题与第三阶段任务继续开放。'),
          (1397,'地区重组，债随人走','皇帝换了，诸侯换了，欠条还在。地区终点研究与第四阶段任务现在进入长期治理。'),
          (1422,'八十五载，商路换了','外部市场和采购条件改变，但自治盟约仍然有效。保持地区事业，不断续办公共项目。'),
          (1437,'百年巴蜀，重新盖章','百年章程验收开放。地区治理须继续出资与履约；统一国家也可以继续维护本乡机构。'))):
        eid=10+stage;simple.append((eid,title,desc,'旧约重认，事业续办。'))
    for eid,title,desc,option in simple:
        L(f'hbe.{eid}.title',title);L(f'hbe.{eid}.desc',desc);L(f'hbe.{eid}.a',option)
        events.append(f'hbe.{eid} = {{ type = country_event title = hbe.{eid}.title desc = hbe.{eid}.desc outcome = neutral illustration_tags = {{ 10 = regular 10 = interior }} option = {{ name = hbe.{eid}.a }} }}')
    yearly=[]
    for eid,year in zip(range(10,15),(1352,1372,1397,1422,1437)):
        yearly.append(f'if = {{ limit = {{ current_year >= {year} NOT = {{ has_variable = hbe_epoch_{eid} }} }} set_variable = hbe_epoch_{eid} trigger_event_non_silently = {{ id = hbe.{eid} }} }}')
    L('hbe.5.title','皇帝请喝茶，账单请看清')
    L('hbe.5.desc','诸侯已经到齐，公共工程与自治章程堆满案头。皇帝可以消耗锅气换各国支持，也可以让诸侯承担更多责任，以信任换取共同信用。')
    L('hbe.5.a','公共事业，皇帝先认账。');L('hbe.5.b','各位也该分担一点。')
    events.append('''hbe.5 = {
        type = country_event title = hbe.5.title desc = hbe.5.desc outcome = neutral
        illustration_tags = { 10 = regular 10 = interior }
        option = { name = hbe.5.a trigger = { international_organization:hbe_empire = { var:hbe_guoqi >= 10 } }
            international_organization:hbe_empire = { change_variable = { name = hbe_guoqi subtract = 10 }
                every_international_organization_member = { change_variable = { name = hbe_yiqi add = 5 } hbe_clamp_yiqi = yes } } }
        option = { name = hbe.5.b international_organization:hbe_empire = {
            change_variable = { name = hbe_guoqi add = 5 }
            if = { limit = { var:hbe_guoqi > 100 } set_variable = { name = hbe_guoqi value = 100 } }
            every_international_organization_member = { change_variable = { name = hbe_yiqi subtract = 3 } hbe_clamp_yiqi = yes } } }
    }''')
    put('in_game/events/hbe_events.txt','namespace = hbe\n'+'\n'.join(events))
    on_actions='''on_game_start = { on_actions = { hbe_start } }
hbe_start = { effect = { every_country = { limit = { hbe_is_prince = yes } hbe_initialize = yes } } }
monthly_country_pulse = { on_actions = { hbe_monthly } }
hbe_monthly = { effect = { hbe_country_monthly = yes } }
yearly_country_pulse = { on_actions = { hbe_yearly } }
hbe_yearly = { trigger = { hbe_is_prince = yes } effect = {
    if = { limit = { has_variable = hbe_salt_debt var:hbe_salt_debt > 0 } add_gold = -1 }
    '''+'\n'.join(yearly)+''' }
    random_events = { chance_to_happen = 20 '''+' '.join(f'1 = hbe.{100+i}' for i in range(7))+''' }
}'''
    put('in_game/common/on_action/hbe_on_actions.txt',on_actions)
    scenarios=[]
    for c in countries:
        scenarios.append(f'hbe_{c["tag"]}_scenario = {{ country = {c["tag"]} player_playstyle = ADMINISTRATIVE player_proficiency = EXPERIENCED bookmark = bookmark_1337 }}')
        L(f'hbe_{c["tag"]}_scenario',c['name']);L(f'hbe_{c["tag"]}_scenario_desc',c['name']+'，所属'+next(n for k,n,*_ in REGIONS if k==c['region'])+'。独立诸侯，可以经营、结盟或竞选巴蜀皇帝。')
    put('main_menu/common/scenarios/hbe_scenarios.txt','\n'.join(scenarios))
    # Neutral original scene is an illustration placeholder; custom DDS is used on decisions.
    width,height=384,192
    pixels=bytearray()
    for y in range(height):
        for x in range(width):
            border=x<8 or y<8 or x>=width-8 or y>=height-8
            color=(166,139,86) if border else ((57,67,61) if ((x//32+y//32)%2) else (45,52,48))
            pixels.extend((color[2],color[1],color[0],255))
    header=struct.pack('<7I',124,0x100F,height,width,width*4,0,0)+bytes(44)
    header+=struct.pack('<8I',32,0x41,0,32,0x00FF0000,0x0000FF00,0x000000FF,0xFF000000)+struct.pack('<5I',0x1000,0,0,0,0)
    image=out/'loading_screen/gfx/interface/hbe/placeholder.dds';image.parent.mkdir(parents=True,exist_ok=True);image.write_bytes(b'DDS '+header+pixels)
    # Plain original cover placeholder; PNG built with the standard library.
    cover_width,cover_height=1280,720
    scanlines=bytearray()
    for y in range(cover_height):
        scanlines.append(0)
        for x in range(cover_width):
            border=x<20 or y<20 or x>=cover_width-20 or y>=cover_height-20
            color=(166,139,86) if border else ((57,67,61) if ((x//80+y//80)%2) else (45,52,48))
            scanlines.extend(color)
    def png_chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    cover=b'\x89PNG\r\n\x1a\n'+png_chunk(b'IHDR',struct.pack('>2I5B',cover_width,cover_height,8,2,0,0,0))
    cover+=png_chunk(b'IDAT',zlib.compress(scanlines,9))+png_chunk(b'IEND',b'')
    (out/'.metadata/thumbnail.png').write_bytes(cover)
    expansion = build_banquet(out, countries, REGIONS, L, put, ROOT, game)
    event_prose = apply_event_prose(out, ROOT, L, loc)
    icon_art = build_icon_assets(out, ROOT, catalog, put, game)
    full_art = build_full_art_assets(out, ROOT, countries, REGIONS, put, game)
    # A repeated build must not register the previous expansion before its keys exist.
    stale_decisions = out/'in_game/common/decisions/hbe_civic_decisions.txt'
    if stale_decisions.exists(): stale_decisions.unlink()
    native_content = build_native_content(out, ROOT, countries, REGIONS, catalog, loc, put, full_art, game)
    social_expansion = build_social_expansion(out, ROOT, countries, REGIONS, loc, put)
    special_goods = prepare_special_goods(out, ROOT, loc, put, game)
    technology_rewards = build_technology_rewards(out, ROOT, loc, put, game)
    internal_ai = build_bashu_ai(out, ROOT, loc, put, game)
    simple_banquet = build_simple_banquet(out, ROOT, countries, loc, put, game)
    art_v021 = build_art_v021(out, ROOT, loc, put, game)
    finish_special_goods(out, ROOT, loc, put, game, special_goods)
    event_choices = build_event_choices(out, ROOT, loc, put, game)
    # Both Chinese and English UI modes have complete keys (English uses Chinese placeholder text).
    variable_labels={'hbe_yiqi':'义气','hbe_guoqi':'锅气','hbe_salt_debt':'盐债',
                     'hbe_research_timer':'地方课题计时','hbe_flavor_cooldown':'地方事件间隔',
                     'hbe_service_cooldown':'事业续办间隔','hbe_assembly_cooldown':'帝国茶会间隔',
                     'hbe_loan_cooldown':'盐引发行间隔'}
    variable_labels.update({r[4]:r[3] for r in REGIONS})
    for f in out.rglob('*.txt'):
        for key in re.findall(r'\bname\s*=\s*(hbe_[a-z0-9_]+)',f.read_text(encoding='utf-8-sig')):
            if key not in loc:L(key,variable_labels.get(key,'地区事业交付计时'))
    from build_player_guides import GUIDES
    GUIDES.extend((key.removeprefix('hbe_term_'),v[0],[v[0]],v[1],'hbe_burden' if key=='hbe_term_burden' else None) for key,v in social_expansion['concepts'].items())
    player_guides = build_player_guides(ROOT, loc, L, put)
    quality_hotfix = build_quality_hotfix(out, ROOT, loc, put)
    player_guides['mechanic_concepts']=quality_hotfix['mechanic_guide_count']
    opening_pacts=build_opening_pacts(out,countries,loc,put)
    for language in ('simp_chinese','english'):
        strings=[f'l_{language}:']+[f' {k}: "{v.replace(chr(92),chr(92)*2).replace(chr(34),chr(92)+chr(34)).replace(chr(10),chr(92)+"n")}"' for k,v in loc.items()]
        put(f'main_menu/localization/{language}/hbe_l_{language}.yml','\n'.join(strings),True)
    roster=[dict(tag=c['tag'],country=c['name'],circle=c['region'],group=c['group'],capital=c['capital'],locations=len(c['locations']),elector='yes' if c['tag'] in electors.values() else 'no') for c in countries]
    csv_write(ROOT/'data/countries_v001.csv',roster)
    assignments=[dict(location=r['location_id'],country=loc_to_tag[r['location_id']],circle=r['circle_design_key'],province=r['original_province_id']) for r in rows]
    csv_write(ROOT/'data/locations_v001.csv',assignments)
    write(ROOT/'data/technology_v001.json',json.dumps(catalog,ensure_ascii=False,indent=2))
    manifest=dict(version='0.3.1',quality_hotfix=quality_hotfix,opening_pacts=opening_pacts,countries=countries,electors=electors,regions=[list(r) for r in REGIONS],
                  source_setup_sha256=sha(original_path),removed_domain_tokens=len(removed),
                  research_nodes=len(catalog)+len(social_expansion['advances']),regional_missions=35,recurring_services=7,events=len(events)+expansion['new_events']+len(social_expansion['events']),
                  decisions=70+len(social_expansion['decisions']),social_expansion=social_expansion,expansion=expansion,native_content=native_content,
                  technology_rewards=technology_rewards,internal_ai=internal_ai,simple_banquet=simple_banquet,art_v021=art_v021,special_goods=special_goods,event_choices=event_choices,
                  illustrations='15 shared painted event backgrounds, 8 organization emblems and panels, situation panel, 97 illustrated decisions, 80 native advance icons, 16 building icons, 9 unit illustrations and 36 text-free heraldic flags',
                  icon_art=icon_art,
                  full_art=full_art,
                  event_prose=event_prose,player_guides=player_guides,
                  files={str(f.relative_to(out)).replace(chr(92),'/'):sha(f) for f in sorted(out.rglob('*')) if f.is_file() and f.name!='build_manifest.json'})
    put('build_manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    # Final observer diagnostics/AI correction pass; retain current art and setup.
    from apply_observer_hotfix import apply as apply_observer_hotfix
    apply_observer_hotfix(out, ROOT)
    from apply_name_hotfix import apply as apply_name_hotfix
    apply_name_hotfix(out, ROOT)
    from export_goods_modifier_icons import apply as export_goods_modifier_icons
    export_goods_modifier_icons(out, ROOT)
    from build_playable_stories import build as build_playable_stories
    build_playable_stories(out, ROOT)
    import export_story_art
    export_story_art.OUT = out
    export_story_art.export()
    from apply_industry_balance_patch import apply as apply_industry_balance
    from apply_advance_gate_patch import apply as apply_advance_gates
    from apply_event_balance_patch import apply as apply_event_balance
    from apply_red_turban_caution import apply as apply_red_turban_caution
    apply_industry_balance(out, ROOT)
    apply_advance_gates(out, ROOT)
    apply_event_balance(out, ROOT)
    apply_red_turban_caution(out, ROOT)
    from apply_unit_maintenance_patch import apply as apply_unit_maintenance
    apply_unit_maintenance(out, ROOT)
    from apply_local_ui_patch import apply as apply_local_ui_patch
    apply_local_ui_patch(out, ROOT)
    from apply_deep_balance_v031 import apply as apply_deep_balance
    deep_balance_report = apply_deep_balance(out, ROOT)
    from apply_guest_production_patch import apply as apply_guest_production
    guest_production_report = apply_guest_production(out, ROOT)
    from build_opening_population import apply as apply_opening_population
    opening_population_report = apply_opening_population(out, ROOT, game)
    from apply_opening_armistice_fix import apply as apply_opening_armistice
    opening_armistice_report = apply_opening_armistice(out, ROOT, game)
    from apply_formables_units_v031 import apply as apply_formables_units
    apply_formables_units(out, ROOT, game)
    from apply_annex_industry_v031 import apply as apply_annex_industry
    apply_annex_industry(out, ROOT, game)
    from apply_ending_art_v031 import apply as apply_ending_art
    apply_ending_art(out, ROOT, game)
    manifest_path = out / "build_manifest.json"
    final_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    final_manifest["deep_balance_v031"] = {"version":"0.3.1", "local_only":True, "decision_prices":len(deep_balance_report["decision_prices"]), "event_receipts":len(deep_balance_report["event_receipts"]), "national_output_caps":deep_balance_report["national_output_caps"], "reforms":deep_balance_report["reforms"], "support_duration_rule":deep_balance_report["support_duration_rule"]}
    final_manifest["guest_production_patch"] = guest_production_report
    final_manifest["opening_population"] = opening_population_report
    final_manifest["opening_armistice"] = opening_armistice_report
    final_manifest["files"] = {p.relative_to(out).as_posix():sha(p) for p in out.rglob("*") if p.is_file() and p.name != "build_manifest.json"}
    manifest_path.write_text(json.dumps(final_manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:manifest[k] for k in ('version','research_nodes','regional_missions','recurring_services','events','decisions')},ensure_ascii=False))
    print(f'Built {len(countries)} countries / {len(locs)} locations / {len(REGIONS)} circles at {out}')

if __name__=='__main__':main()
