"""Supplied government teahouses: monthly relief and local assimilation."""
import json
from pdxscript import blocks


def build(out, root, put, loc, manifest):
    from PIL import Image
    from build_icon_assets import fit
    from build_flags import save_dds
    from build_support import sha256_file
    cfg=json.loads((root/'data/civic_teahouse.json').read_text(encoding='utf-8'))
    advance,building=cfg['advance'],cfg['building']
    permission='hbe_teahouse_monthly_burden_relief'
    put('in_game/common/advances/hbe_teahouse.txt',f'''{advance} = {{
 age = {cfg['age']} starting_technology_level = 99
 icon = {advance} content_priority = 845 research_cost = {cfg['research_cost']:g}
 potential = {{ hbe_research_origin_common = yes }}
 allow = {{ is_member_of_international_organization = international_organization:hbe_empire }}
 requires = {cfg['parent']}
 unlock_building = {building}
 ai_weight = {{ add = 15 }}
}}''')
    upkeep=' '.join(f'{k} = {v:g}' for k,v in cfg['maintenance'].items())
    put('in_game/common/building_types/hbe_teahouse.txt',f'''{building} = {{
 is_special = yes is_foreign = no forbidden_for_estates = yes
 category = government_category pop_type = burghers employment_size = {cfg['employment_per_level']:g}
 max_levels = {cfg['local_level_cap']} build_time = {cfg['build_time']} construction_demand = hbe_institution_construction
 town = yes city = yes megalopolis = yes
 country_potential = {{ is_member_of_international_organization = international_organization:hbe_empire }}
 location_potential = {{ is_in_scripted_geography = scripted_geography:hbe_domain }}
 allow = {{ scope:actor = {{ has_advance = {advance} total_building_levels_including_construction:{building} < {cfg['national_level_cap']} }} }}
 modifier = {{ {permission} = {cfg['monthly_burden_relief']:g} local_pop_assimilation_speed_modifier = {cfg['local_assimilation_per_level']:g} }}
 unique_production_methods = {{ {building}_maintenance = {{ icon_type = building_type icon = {building} {upkeep} category = building_maintenance }} }}
 ai_construct_weight = {{ value = 0.5 if = {{ limit = {{ scope:owner = {{ var:hbe_burden >= 40 }} }} add = 1 }} }}
}}''')
    put('main_menu/common/modifier_type_definitions/hbe_teahouse.txt',permission+' = { game_data = { category = location } }')
    icon='gfx/interface/icons/text_icons/hbe_burden.dds'
    put('main_menu/common/modifier_icons/hbe_teahouse.txt',f'{permission} = {{ positive = "{icon}" negative = "{icon}" }}')
    put('in_game/common/script_values/hbe_teahouse.txt',f'''hbe_teahouse_monthly_relief = {{
 value = total_effective_building_levels:{building} min = 0 max = {cfg['national_level_cap']} multiply = {cfg['monthly_burden_relief']:g}
}}''')
    put('in_game/common/scripted_effects/hbe_teahouse.txt','''hbe_teahouse_relieve_burden = {
 if = { limit = { is_member_of_international_organization = international_organization:hbe_empire hbe_teahouse_monthly_relief > 0 }
 change_variable = { name = hbe_burden subtract = hbe_teahouse_monthly_relief }
 hbe_clamp_burden = yes
 }
}''')
    put('in_game/common/on_action/hbe_teahouse.txt','''monthly_country_pulse = { on_actions = { hbe_teahouse_pulse } }
hbe_teahouse_pulse = { trigger = { is_member_of_international_organization = international_organization:hbe_empire } effect = { hbe_teahouse_relieve_burden = yes } }''')
    loc.update({advance:cfg['name'],advance+'_desc':'府署与乡里在茶社商议工期、轮歇和新户安置。账上已有的分担，仍须有人当面说明。',
        building:cfg['building_name'],building+'_desc':f'供居民饮茶、休憩与议事的政府建筑。每个有效等级每月减少{cfg["monthly_burden_relief"]:g}役负，所在地人口同化速度每级增加{cfg["local_assimilation_per_level"]*100:g}%。\n\n全国总等级上限{cfg["national_level_cap"]}（含在建），可在同一地点升级或分散建设。满额有效运转每月减少{cfg["national_level_cap"]*cfg["monthly_burden_relief"]:g}役负。须有雇员并持续取得茶与纸；实际减役随有效建筑等级缩放，同化遵循原版就业与供养规则。',
        building+'_maintenance':'茶社公所日常供养',building+'_maintenance_desc':'消耗茶与纸，供居民饮茶议事，维持日常接待。',
        permission:'每月役负自然衰减', 'MODIFIER_TYPE_NAME_'+permission:'每月役负自然衰减',
        'MODIFIER_TYPE_DESC_'+permission:'每月减少全国役负，实际数值按有效建筑等级计算；失去供养时相应收益降低。'})
    loc[building+'_desc']=loc[building+'_desc'].replace('\n','\\n')
    with Image.open(root/cfg['technology_art']) as source:technology=fit(source,256)
    with Image.open(root/cfg['building_art']) as source:building_icon=fit(source,128)
    for folder in ('advance','hbe/technology'):
        save_dds(out/f'main_menu/gfx/interface/{folder}/{advance}.dds',technology)
    save_dds(out/f'main_menu/gfx/interface/icons/buildings/{building}.dds',building_icon)
    # Count the actual native registry, including this separate child node.
    files=['hbe_advances.txt','hbe_civic_advances.txt','hbe_local_military.txt','hbe_industry_transmission.txt','hbe_af_advances.txt','hbe_teahouse.txt']
    keys=[k for f in files for k,*_ in blocks((out/'in_game/common/advances'/f).read_text(encoding='utf-8-sig'),0)]
    assert len(keys)==len(set(keys))
    manifest['research_nodes']=len(keys)
    manifest['formables_units_v031']['date_free_advances']=keys
    manifest['civic_teahouse']=dict(cfg,advance_count=1,art_status='ImageGen, matched separately to vanilla technology and building references',art_sha256={key:sha256_file(root/cfg[key]) for key in ('technology_art','building_art')},runtime_verified=False)
    return cfg


def validate(out, root, manifest, check):
    cfg=json.loads((root/'data/civic_teahouse.json').read_text(encoding='utf-8'))
    read=lambda p:(out/p).read_text(encoding='utf-8-sig')
    a=read('in_game/common/advances/hbe_teahouse.txt')
    b=read('in_game/common/building_types/hbe_teahouse.txt')
    v=read('in_game/common/script_values/hbe_teahouse.txt')
    check('teahouse is an age-two child of works archive research',all(s in a for s in ('requires = hbe_tech_common_3','age = age_2_renaissance','unlock_building = hbe_public_teahouse','hbe_research_origin_common = yes')))
    check('teahouse government building allows five local and five total levels including queues',all(s in b for s in ('category = government_category','max_levels = 5','total_building_levels_including_construction:hbe_public_teahouse < 5','tea = 0.1','paper = 0.02')))
    check('teahouse monthly relief scales by supplied effective levels capped at 2.5',all(s in v for s in ('total_effective_building_levels:hbe_public_teahouse','max = 5 multiply = 0.5')) and 'hbe_clamp_burden = yes' in read('in_game/common/scripted_effects/hbe_teahouse.txt'))
    check('teahouse provides local native assimilation only','local_pop_assimilation_speed_modifier = 0.1' in b and 'global_pop_assimilation' not in b)
    from PIL import Image
    for folder,key,size in [('advance',cfg['advance'],256),('icons/buildings',cfg['building'],128)]:
        with Image.open(out/f'main_menu/gfx/interface/{folder}/{key}.dds') as image:
            check('teahouse '+folder+' has a unique transparent native-sized icon',image.size==(size,size) and image.mode=='RGBA' and image.getchannel('A').getextrema()[0]==0 and image.getchannel('A').getextrema()[1]>=250)
