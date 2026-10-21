"""Native age-two boolean permissions for local-affairs investment and offers."""
import json
import re
from PIL import Image
from pdxscript import blocks
from build_icon_assets import fit
from build_flags import save_dds
from build_support import sha256_file, write_preserving_format

CONFIG = 'data/local_affairs_research.json'
ADVANCES = 'in_game/common/advances/hbe_af_advances.txt'
LARGE = 'hbe_af_allow_large_investment'
REFRESH = 'hbe_af_allow_local_refresh'


def build(out, root, put, loc, manifest):
    config = json.loads((root / CONFIG).read_text(encoding='utf-8'))
    # Reuse common-node visibility, including preserved identity after formation.
    path = out / 'in_game/common/advances/hbe_advances.txt'
    text = path.read_text(encoding='utf-8-sig')
    common = next(text[a:b] for key, _, a, b, _ in blocks(text, 0) if key == 'hbe_tech_common_3')
    potential = next(common[a:b] for key, _, a, b, _ in blocks(common, 0) if key == 'potential')
    # Remove the superseded age-one capability hint, including on incremental builds.
    text = re.sub(r'(?m)^[ \t]*pure_tooltip_entry\s*=\s*hbe_af_large_unlocked[^\n]*\n?', '', text)
    write_preserving_format(path, text)
    advances, types, icons, art = [], [], [], []
    for i, row in enumerate(config['advances']):
        key, permission = row['key'], row['permission']
        advances.append(f'''{key} = {{
 age = {config['age']}
 starting_technology_level = 99
 research_cost = {row['research_cost']:g}
 icon = {key}
 content_priority = {835-i*5}
 potential = {{ {potential.strip()} }}
 allow = {{ is_member_of_international_organization = international_organization:hbe_empire NOT = {{ has_variable = hbe_research_pending }} }}
 requires = {row['parent']}
 {permission} = yes
 ai_weight = {{ add = 20 }}
}}''')
        types.append(f'{permission} = {{ boolean = yes game_data = {{ category = country }} }}')
        icon = f'gfx/interface/icons/modifier_types/{permission}.dds'
        icons.append(f'{permission} = {{ positive = "{icon}" negative = "{icon}" }}')
        loc.update({key: row['name'], key+'_desc': row['description'], permission: row['permission_name'],
                    'MODIFIER_TYPE_NAME_'+permission: row['permission_name'],
                    'MODIFIER_TYPE_DESC_'+permission: row['permission_description']})
        with Image.open(root / row['source']) as source:
            sprite = fit(source, 256)
        sprite_path = root / f'assets/technology_icons/{key}.png'
        sprite.save(sprite_path)
        for folder in ('advance', 'hbe/technology'):
            save_dds(out / f'main_menu/gfx/interface/{folder}/{key}.dds', sprite)
        save_dds(out / ('main_menu/'+icon), fit(sprite, 128))
        art.append(dict(key=key, source=row['source'], source_sha256=sha256_file(root/row['source']),
                        sprite=sprite_path.relative_to(root).as_posix()))
    put(ADVANCES, '\n\n'.join(advances)+'\n')
    put('main_menu/common/modifier_type_definitions/hbe_af_permissions.txt', '\n'.join(types)+'\n')
    put('main_menu/common/modifier_icons/hbe_af_permissions.txt', '\n'.join(icons)+'\n')
    files = ['hbe_advances.txt', 'hbe_civic_advances.txt', 'hbe_local_military.txt',
             'hbe_industry_transmission.txt', 'hbe_af_advances.txt']
    keys = [key for name in files for key, *_ in blocks((out/'in_game/common/advances'/name).read_text(encoding='utf-8-sig'), 0)]
    assert len(keys) == len(set(keys)), 'Duplicate HBE research identity'
    manifest['research_nodes'] = len(keys)
    manifest['formables_units_v031']['date_free_advances'] = keys
    manifest['local_affairs_research'] = dict(advance_count=len(advances), advances=config['advances'],
        age=config['age'], refresh_cooldown_months=config['refresh_cooldown_months'],
        native_boolean=True, art=art, runtime_verified=False, visual_verified=False)
    return config


def refresh_support(config, projects, triggers, effects, sguis, loc):
    """One guarded local-only redraw; no charges, outcome rolls or construction reset."""
    months = config['refresh_cooldown_months']
    alternatives = ' '.join(f'AND = {{ NOT = {{ var:hbe_af_local = {p["id"]} }} hbe_af_eligible_{p["id"]} = yes }}'
                            for p in projects if p['pool'] == 'local')
    triggers.append(f'''hbe_af_can_refresh_local = {{
 hbe_af_access = yes hbe_af_idle = yes modifier:{REFRESH} = yes
 has_variable = hbe_af_local NOT = {{ has_variable = hbe_af_local_refresh_cooldown }}
 OR = {{ {alternatives} }}
}}''')
    effects.append(f'''hbe_af_refresh_local = {{ if = {{ limit = {{ hbe_af_can_refresh_local = yes }}
 hbe_af_draw_local = yes
 set_variable = {{ name = hbe_af_local_refresh_cooldown value = yes months = {months} }}
}} }}''')
    sguis.append(f'''hbe_af_ui_refresh_local = {{ scope = country
 is_shown = {{ hbe_af_access = yes modifier:{REFRESH} = yes }}
 is_valid = {{ hbe_af_can_refresh_local = yes }}
 effect = {{ hbe_af_refresh_local = yes }}
}}''')
    loc['HBE_AF_REFRESH_LOCAL'] = '刷新地区项目'
    loc['HBE_AF_REFRESH_LOCAL_TT'] = f'另取一项地区议案；每{months}个月可刷新一次。须当前空闲且有其他合格项目。'
