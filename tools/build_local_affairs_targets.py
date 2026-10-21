"""Project-specific target selection using native location and building checks."""
import re
from pdxscript import blocks
from build_local_affairs_rewards import building_condition, has_reward


def shortage_trigger(game):
    # A conservative proxy: existing laborer/peasant jobs of at least 100 workers,
    # with fewer than 50 employed. Do not mistake every small estate for a shortage.
    defaults=(game/'main_menu/common/script_values/default_values.txt').read_text(encoding='utf-8-sig')
    sizes={k:float(v) for k,v in re.findall(r'^([a-z_]+)\s*=\s*([0-9.]+)\s*(?:#.*)?$',defaults,re.M)}
    kinds=[]
    for path in (game/'in_game/common/building_types').glob('*.txt'):
        s=path.read_text(encoding='utf-8-sig')
        for key,_,a,b,_ in blocks(s,0):
            body=s[a:b]; m=re.search(r'\bemployment_size\s*=\s*(\w+)',body)
            if m and sizes.get(m[1],0)>=0.1 and re.search(r'pop_type\s*=\s*(laborers|peasants)\b',body): kinds.append(key)
    assert kinds, 'Vanilla worker-capacity catalogue missing'
    return 'hbe_af_short_workers = { any_buildings_in_location = { OR = { '+' '.join('building_type = building_type:'+k for k in sorted(kinds))+' } building_employed_amount < 0.05 } }'


def condition(p):
    base='is_in_scripted_geography = scripted_geography:hbe_domain owner = root controller = root NOT = { has_variable = hbe_af_local_cooldown } '
    for r in p['rewards']:
        if r['type']=='building': base+='OR = { '+' '.join('AND = { '+building_condition(b)+' }' for b in r['choices'])+' } '
        if r['type']=='road': base+='any_neighbor_location = { owner = root controller = root is_connected_to = prev NOT = { has_road_to = prev } } '
    if p.get('target_industry') and not has_reward(p,'building'):
        kinds=' '.join('building_type = building_type:'+b for b in p['target_industry'])
        active=' building_employed_amount >= 0.05' if p.get('target_active_industry') else ''
        base+='any_buildings_in_location = { OR = { '+kinds+' }'+active+' } '
    return base


def choose(p):
    base=condition(p)
    if has_reward(p,'building'):
        preferences=['population >= 20 NOT = { hbe_af_short_workers = yes }','population >= 10 NOT = { hbe_af_short_workers = yes }']
    elif has_reward(p,'road'):
        preferences=['location_building_level = { building_type = building_type:marketplace value >= 1 }','population >= 15']
    elif has_reward(p,'population'):
        preferences=['hbe_af_short_workers = yes','population < 20']
    else: preferences=['population >= 15']
    if p.get('guild_role')=='apprentices':
        kinds=' '.join('building_type = building_type:'+b for b in p['target_industry'])
        preferences=['any_buildings_in_location = { OR = { '+kinds+' } building_employed_amount < 0.05 }','population < 20']
    if p.get('guild_role'):
        from build_local_affairs_guilds import local_sponsor, config
        supplied='OR = { '+' '.join('AND = { '+local_sponsor(b)+' }' for b in config()['sponsor_buildings'])+' }'
        preferences=[supplied+' '+preferences[0],preferences[0],supplied]+preferences[1:]
    parts=[]
    for i,pref in enumerate(preferences):
        parts.append(('if' if i==0 else 'else_if')+' = { limit = { any_owned_location = { '+base+pref+' } } random_owned_location = { limit = { '+base+pref+' } save_scope_as = hbe_af_draw_location } }')
    parts.append('else = { random_owned_location = { limit = { '+base+' } save_scope_as = hbe_af_draw_location } }')
    parts.append('set_variable = { name = hbe_af_candidate_target value = scope:hbe_af_draw_location }')
    if has_reward(p,'road'):
        parts.append('var:hbe_af_candidate_target = { random_neighbor_location = { limit = { owner = root controller = root is_connected_to = prev NOT = { has_road_to = prev } } save_scope_as = hbe_af_draw_road } } set_variable = { name = hbe_af_candidate_road value = scope:hbe_af_draw_road }')
    return ' '.join(parts)
