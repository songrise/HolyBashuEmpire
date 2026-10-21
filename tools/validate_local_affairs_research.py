"""Native research graph, actual capability gates and local-only redraw contracts."""
import json
import re
from PIL import Image
from pdxscript import blocks
from build_local_affairs_research import CONFIG, ADVANCES, LARGE, REFRESH


def validate(mod, root, game, manifest, check):
    config = json.loads((root/CONFIG).read_text(encoding='utf-8'))
    read = lambda rel: (mod/rel).read_text(encoding='utf-8-sig')
    definitions = {key: read(ADVANCES)[a:b] for key, _, a, b, _ in blocks(read(ADVANCES), 0)}
    types = read('main_menu/common/modifier_type_definitions/hbe_af_permissions.txt')
    icons = read('main_menu/common/modifier_icons/hbe_af_permissions.txt')
    loc = read('main_menu/localization/simp_chinese/hbe_af_l_simp_chinese.yml')
    expected = {row['key'] for row in config['advances']}
    check('affairs exactly two new permission technologies',set(definitions) == expected and manifest['local_affairs_research']['advance_count'] == 2)
    for row in config['advances']:
        body, key, permission = definitions[row['key']], row['key'], row['permission']
        check(key+' uses age two with native parent and no calendar gate',all(s in body for s in (
            'age = age_2_renaissance', 'starting_technology_level = 99', 'requires = '+row['parent'])) and not re.search(r'current_(?:date|year)|year\s*=',body))
        check(key+' retains all HBE identities and membership requirement',set(re.findall(r'has_or_had_tag = (\w+)',body)) == {c['tag'] for c in manifest['countries']} and 'is_member_of_international_organization = international_organization:hbe_empire' in body)
        check(key+' grants its sole registered country boolean',permission+' = yes' in body and permission+' = { boolean = yes game_data = { category = country } }' in types and not re.search(r'\b(?:unlock_\w+|research_speed_modifier|global_\w+)\s*=',body))
        check(key+' localizes its native boolean name and description',all(s in loc for s in ('MODIFIER_TYPE_NAME_'+permission+':', 'MODIFIER_TYPE_DESC_'+permission+':', row['permission_name'])))
        with Image.open(root/f'assets/technology_icons/{key}.png') as im:
            sprite=im.convert('RGBA'); bounds=sprite.getchannel('A').getbbox()
            check(key+' has a padded transparent 256px painted icon',sprite.size==(256,256) and sprite.getchannel('A').getextrema()==(0,255) and min(bounds[0],bounds[1],256-bounds[2],256-bounds[3]) >= 10)
            for folder in ('advance','hbe/technology'):
                raw=(mod/f'main_menu/gfx/interface/{folder}/{key}.dds').read_bytes()
                check(key+' '+folder+' exact uncompressed BGRA export',raw[:4]==b'DDS ' and raw[128:]==sprite.tobytes('raw','BGRA'))
        check(permission+' has native modifier icon mapping',f'positive = "gfx/interface/icons/modifier_types/{permission}.dds"' in icons and (mod/f'main_menu/gfx/interface/icons/modifier_types/{permission}.dds').is_file())
    old=read('in_game/common/advances/hbe_advances.txt')
    check('affairs removes superseded age-one capability hint','hbe_af_large_unlocked' not in old+loc and '仍须匠人互访' not in loc)
    triggers=read('in_game/common/scripted_triggers/hbe_af_triggers.txt')
    defs={k:triggers[a:b] for k,_,a,b,_ in blocks(triggers,0)}
    check('affairs small investment remains free of the new research gate',all(LARGE not in body for k,body in defs.items() if k.startswith('hbe_af_can_') and k.endswith('_small')))
    gate=defs['hbe_af_can_refresh_local']
    check('affairs local redraw requires permission idle cooldown and alternative',all(s in gate for s in ('modifier:'+REFRESH+' = yes', 'hbe_af_idle = yes', 'NOT = { has_variable = hbe_af_local_refresh_cooldown }', 'has_variable = hbe_af_local')) and gate.count('AND = { NOT = { var:hbe_af_local = ')==8)
    effects=read('in_game/common/scripted_effects/hbe_af_effects.txt')
    body=next(effects[a:b] for k,_,a,b,_ in blocks(effects,0) if k=='hbe_af_refresh_local')
    check('affairs redraw effect rechecks gate and only redraws local offer',all(s in body for s in ('hbe_af_can_refresh_local = yes','hbe_af_draw_local = yes','months = 3')) and not any(s in body for s in ('draw_national','hbe_af_active','add_gold','hbe_burden','roll_outcome')))
    gui=read('in_game/gui/hbe_local_affairs.gui')
    check('affairs refresh uses native round button and native change arrows',all(s in gui for s in ('button_round_shortcut = { name = "hbe_af_refresh_local"', 'hbe_af_ui_refresh_local', 'gfx/interface/icons/international_organizations/change.dds')) and (game/'main_menu/gfx/interface/icons/international_organizations/change.dds').is_file())
    check('affairs both boolean names are present in every shipped locale',all(all(row['permission_name'] in read(f'main_menu/localization/{lang}/hbe_af_l_{lang}.yml') for row in config['advances']) for lang in ('simp_chinese','english','traditional_chinese')))
