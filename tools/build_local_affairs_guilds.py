"""Guild project permissions, supplied sponsors and specialized reward variants."""
import json
from pathlib import Path
from pdxscript import blocks, apply_edits

PERMISSION = 'hbe_af_allow_guild_projects'


def config():
    return json.loads((Path(__file__).resolve().parents[1]/'data/local_affairs_projects.json').read_text(encoding='utf-8'))['guilds']


def local_sponsor(building):
    return ('any_buildings_in_location = { building_type = building_type:'+building+
            ' building_employed_amount >= 0.05 } owner = { hbe_operating_'+building.removeprefix('hbe_')+' = yes }')


def sponsor(p):
    choices = [local_sponsor(b) if p['pool']=='local' else 'hbe_operating_'+b.removeprefix('hbe_')+' = yes'
               for b in config()['sponsor_buildings']]
    condition = 'OR = { '+' '.join('AND = { '+c+' }' for c in choices)+' }'
    return 'var:hbe_af_candidate_target = { '+condition+' }' if p['pool']=='local' else condition


def industry_condition(p, row):
    # Qualification, including originating circle and its actual production advance.
    condition = 'hbe_transmission_'+row['id']+'_ready = yes'
    if p['pool']=='local':
        condition += ' var:hbe_af_candidate_target = { '+local_sponsor(row['special_building'])+' }'
    else:
        condition += ' hbe_operating_'+row['special_building'].removeprefix('hbe_')+' = yes'
    return condition


def industries():
    return json.loads((Path(__file__).resolve().parents[1]/'data/industry_transmission.json').read_text(encoding='utf-8'))['industries']


def start(p):
    result = 'set_variable = { name = hbe_af_guild_variant value = 0 } '
    if not p.get('guild_role'):
        return result
    # An originating country normally has one variant; first qualified one wins.
    for i, row in enumerate(industries(),1):
        result += ('if' if i==1 else 'else_if')+' = { limit = { '+industry_condition(p,row)+' } set_variable = { name = hbe_af_guild_variant value = '+str(i)+' } } '
    return result


def variant_key(base, i):
    return base+'_guild_'+str(i)


def modifier_effect(p, row, tier, duration):
    """One modifier per reward, specialized at start; no extra contribution award."""
    base=row.get('modifier') or row['modifiers'][tier]
    scope=config()['modifier_scopes'][base]
    def effect(key):
        inner=f'add_{"country" if scope=="country" else "location"}_modifier = {{ modifier = hbe_af_{key} months = {"root." if scope=="location" else ""}var:{duration} mode = replace }}'
        return 'var:hbe_af_target = { '+inner+' }' if scope=='location' else inner
    if not row.get('guild_variant'):
        return effect(base)
    result=''
    for i,_ in enumerate(industries(),1):
        result+=('if' if i==1 else 'else_if')+f' = {{ limit = {{ var:hbe_af_guild_variant = {i} }} '+effect(variant_key(base,i))+' } '
    return result+'else = { '+effect(base)+' }'


def build(out, root, put, loc, projects, catalogue):
    from build_support import write_preserving_format
    cfg=catalogue['guilds']
    path=out/'in_game/common/advances/hbe_advances.txt'
    text=path.read_text(encoding='utf-8-sig');edits=[]
    for key,_,a,b,_ in blocks(text,0):
        if key=='hbe_tech_common_5':
            body=text[a:b]
            if PERMISSION+' = yes' not in body:body+='\n    '+PERMISSION+' = yes\n'
            edits.append((a,b,body))
    assert len(edits)==1
    write_preserving_format(path,apply_edits(text,edits))
    put('main_menu/common/modifier_type_definitions/hbe_af_guild_permission.txt',PERMISSION+' = { boolean = yes game_data = { category = country } }\n')
    # Reuse the accepted guild technology icon, keeping its color and silhouette.
    source=out/'main_menu/gfx/interface/advance/hbe_tech_common_5.dds'
    target=out/f'main_menu/gfx/interface/icons/modifier_types/{PERMISSION}.dds'
    target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists() or target.read_bytes()!=source.read_bytes():target.write_bytes(source.read_bytes())
    icon=f'gfx/interface/icons/modifier_types/{PERMISSION}.dds'
    put('main_menu/common/modifier_icons/hbe_af_guild_permission.txt',f'{PERMISSION} = {{ positive = "{icon}" negative = "{icon}" }}\n')
    loc[PERMISSION]=loc['MODIFIER_TYPE_NAME_'+PERMISSION]='允许行会传习项目'
    loc['MODIFIER_TYPE_DESC_'+PERMISSION]='地方事业可抽到工法整理、工料采办、验货定样、招收学徒、扩建作坊与试作新法项目。正常运转的产业机构可使相关项目役负减少20%；本地项目须在机构所在地点承办。'
    # Specialized versions replace the ordinary modifier, retaining its base effect.
    bases={r['modifier'] for p in projects for r in p['rewards'] if r.get('guild_variant')}
    for base in sorted(bases):
        for i,row in enumerate(industries(),1):
            spec=json.loads(json.dumps(catalogue['modifiers'][base]))
            local=spec['scope']=='location'
            value=cfg['special_output'][spec['scope']]
            spec['effects'][('local_' if local else 'global_')+row['goods']+'_output_modifier']=value
            spec['name']+='·'+cfg['goods_names'][row['goods']]
            addition=f'{"当地" if local else "全国"}{cfg["goods_names"][row["goods"]]}产出 +{value*100:g}%'
            spec['summary']+='；'+addition
            spec['description']+='已掌握的工法用于对应产业，'+addition+'。'
            catalogue['modifiers'][variant_key(base,i)]=spec
    return dict(projects=[p['id'] for p in projects if p.get('guild_role')],permission=PERMISSION,
                sponsor_discount=cfg['sponsor_discount'],special_output=cfg['special_output'])


def validate(out, root, check):
    data=json.loads((root/'data/local_affairs_projects.json').read_text(encoding='utf-8'))
    guilds=[p for p in data['projects'] if p.get('guild_role')]
    read=lambda rel:(out/rel).read_text(encoding='utf-8-sig')
    triggers=read('in_game/common/scripted_triggers/hbe_af_triggers.txt')
    effects=read('in_game/common/scripted_effects/hbe_af_effects.txt')
    values=read('in_game/common/script_values/hbe_af_values.txt')
    tdefs={k:triggers[a:b] for k,_,a,b,_ in blocks(triggers,0)}
    edefs={k:effects[a:b] for k,_,a,b,_ in blocks(effects,0)}
    check('guild pools have three distinct roles each',len(guilds)==6 and len({p['guild_role'] for p in guilds})==6 and all(sum(p['pool']==pool for p in guilds)==3 for pool in ('national','local')))
    check('guild merge preserves four existing catalogue entries without duplicate concepts',{p['id'] for p in guilds}=={3,7,10,13,17,18})
    advance=read('in_game/common/advances/hbe_advances.txt')
    body=next(advance[a:b] for k,_,a,b,_ in blocks(advance,0) if k=='hbe_tech_common_5')
    check('guild transmission keeps literacy and grants one native project permission',PERMISSION+' = yes' in body and 'global_burghers_max_literacy = 4' in body)
    for p in data['projects']:
        eligible=tdefs['hbe_af_eligible_'+str(p['id'])]
        check(p['key']+' guild gate has correct scope',(PERMISSION in eligible)==bool(p.get('guild_role')))
        for tier in ('small','large'):
            start_body=edefs[f'hbe_af_start_{p["id"]}_{tier}']
            check(p['key']+' '+tier+' uses exactly one guarded normal completion path',start_body.count('hbe_af_can_')==1 and 'hbe_af_record_contribution' not in start_body)
            expected='hbe_af_local_reward_multiplier' if p['pool']=='local' else '1'
            check(p['key']+' '+tier+' snapshots the correct local reward bonus','name = hbe_af_reward_multiplier value = '+expected+' }' in start_body)
            if not p.get('guild_role'):continue
            vbody=next(values[a:b] for k,_,a,b,_ in blocks(values,0) if k==f'hbe_af_load_{p["id"]}_{tier}')
            check(p['key']+' '+tier+' sponsor discount is once-only and employment-based',vbody.count('multiply = 0.8')==1 and 'building_employed_amount >= 0.05' in vbody if p['pool']=='local' else vbody.count('multiply = 0.8')==1 and 'hbe_operating_' in vbody)
            if p['pool']=='local':check(p['key']+' sponsor uses candidate location','var:hbe_af_candidate_target = {' in vbody)
            check(p['key']+' locks only qualified specialized production at start',all('hbe_transmission_'+r['id']+'_ready = yes' in start_body for r in industries()) and 'hbe_af_guild_variant' in start_body)
            reward_body=edefs[f'hbe_af_reward_{p["id"]}_{tier}']
            check(p['key']+' variants replace ordinary modifiers without extra contribution',all('var:hbe_af_guild_variant = '+str(i) in reward_body for i in range(1,5)) and 'hbe_af_record_contribution' not in reward_body)
    workshop=next(p for p in guilds if p['id']==17)
    choices=next(r['choices'] for r in workshop['rewards'] if r['type']=='building')
    check('guild workshop only adds vanilla industry scale, never special institutions',all(not k.startswith('hbe_') for k in choices) and len(choices)==20)
    # All country booleans, including observer goods, must explain a concrete action.
    bools=[]
    for path in (out/'main_menu/common/modifier_type_definitions').glob('hbe*.txt'):
        text=path.read_text(encoding='utf-8-sig')
        bools.extend(k for k,_,a,b,_ in blocks(text,0) if 'boolean = yes' in text[a:b])
    for lang in ('simp_chinese','english','traditional_chinese'):
        desc=read(f'main_menu/localization/{lang}/hbe_permission_descriptions_l_{lang}.yml')
        check(lang+' all mod booleans have a single plain-language definition',all(desc.count(' MODIFIER_TYPE_DESC_'+k+':')==1 for k in bools))
    core=read('main_menu/localization/simp_chinese/hbe_l_simp_chinese.yml')
    import re
    plain=re.sub(r"\[Concept\('[^']+',\s*'([^']+)'\)\|e\]",r'\1',core)
    check('no retired service unlock or recent-service network condition remains',not re.search(r'解锁本圈三年地方事业|近五年完成本圈事业|半年专业交付计2|通过研究决议资助|地区研究通过决议资助',plain))
