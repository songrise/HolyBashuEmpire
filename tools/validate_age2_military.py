"""Verify effective inherited stats, native-only append patches and eligibility scope."""
from pathlib import Path
import json
import re
from collections import Counter

from pdxscript import blocks, tokens
from build_early_research import scalars
from build_age2_military import CONFIG, UNITS, TRIGGERS, definitions, child, ready_key


def resolve_units(mod, game):
    database = {}
    for folder in (game/'in_game/common/unit_categories', game/'in_game/common/unit_types', mod/'in_game/common/unit_types'):
        for path in folder.glob('*.txt'):
            database.update(definitions(path.read_text(encoding='utf-8-sig')))

    def resolve(key, seen=()):
        assert key not in seen, key
        body = database[key]
        values = {name: value for name, value, _, _ in scalars(body)}
        parent = values.get('copy_from') or values.get('category')
        result = resolve(parent, seen+(key,)) if parent and parent != key else {}
        result = dict(result)
        for name, value in values.items():
            if re.fullmatch(r'-?\d+(?:\.\d+)?', value):
                result[name] = round(result.get(name, 0)+float(value), 8)
            else:
                result[name] = value
        terrain = dict(result.get('combat', {}))
        for name, _, a, b, _ in blocks(body, 0):
            if name == 'combat':
                for land, value, _, _ in scalars(body[a:b]):
                    terrain[land] = round(terrain.get(land, 0)+float(value), 8)
        result['combat'] = terrain
        return result
    return resolve


def validate(mod, root, game, manifest, check):
    if 'age2_military' not in manifest:
        return
    mod, root, game = map(Path, (mod, root, game))
    config = json.loads((root/CONFIG).read_text(encoding='utf-8'))
    rows = config['units']
    text = (mod/UNITS).read_text(encoding='utf-8-sig')
    units = definitions(text)
    triggers = definitions((mod/TRIGGERS).read_text(encoding='utf-8-sig'))
    resolve = resolve_units(mod, game)
    expected_nodes=91+manifest.get('local_affairs_research',{}).get('advance_count',0)+manifest.get('civic_teahouse',{}).get('advance_count',0)
    check('age-two military adds five unit types and no military research nodes', len(units) == 14 and manifest['research_nodes'] == expected_nodes and config['new_advance_count'] == 0)
    check('all fourteen types remain 500 men', all(resolve(key)['max_strength'] == .5 for key in units))
    counter = definitions((mod/'in_game/common/script_values/hbe_civic_values.txt').read_text(encoding='utf-8-sig'))['hbe_civic_special_count']
    counts = Counter(re.findall(r'total_sub_unit_type_count:(\w+)', counter))
    check('burden counter includes every successor exactly once', set(counts) == set(units) and all(v == 1 for v in counts.values()))
    effect = (mod/'in_game/common/scripted_effects/hbe_civic_effects.txt').read_text(encoding='utf-8-sig')
    check('only net new regiments cost two burden', 'hbe_civic_special_count > var:hbe_special_record' in effect and 'multiply = 2' in effect and 'destroy' not in effect and 'create_sub_unit' not in effect)
    actual_unlocks = {}
    hbe_count = 0
    for path in (mod/'in_game/common/advances').glob('*.txt'):
        for key, body in definitions(path.read_text(encoding='utf-8-sig')).items():
            hbe_count += key.startswith('hbe_') and not key.startswith(('hbe_guest_license_', 'hbe_inherited_industry_'))
            for field, value, _, _ in scalars(body):
                if field == 'unlock_unit':
                    actual_unlocks.setdefault(value, []).append(key)
    check('HBE advance registry matches all declared research modules', hbe_count == expected_nodes)
    for relative in config['tech_files']:
        original = definitions((game/relative).read_text(encoding='utf-8-sig'))
        patched = definitions((mod/relative).read_text(encoding='utf-8-sig'))
        check(relative+' retains every native definition', original.keys() == patched.keys())
        for key, body in original.items():
            added = {r['key'] for r in rows if r['native_advance'] == key}
            new_body = patched[key]
            for field, value, a, b in reversed(scalars(new_body)):
                if field == 'unlock_unit' and value in added:
                    new_body = new_body[:a]+new_body[b:]
            check(key+' native properties unchanged', [t.value for t in tokens(body)] == [t.value for t in tokens(new_body)])
    for row in rows:
        key, first, region = row['key'], row['from_unit'], row['region']
        values = resolve(key)
        for field, expected in row['target_effective_stats'].items():
            check(key+' effective '+field, values.get(field, 0) == expected)
        check(key+' unlocked exactly once by its native advance', actual_unlocks.get(key) == [row['native_advance']])
        check(first+' preferred successor is correct', dict((k, v) for k, v, _, _ in scalars(units[first])).get('upgrades_to') == key)
        check(first+' upgrade preserves unit category and strength', values['category'] == resolve(first)['category'] and values['max_strength'] == resolve(first)['max_strength'])
        check(key+' shares the original family cap', values['family'] == config['unit_family'] and 'limit =' not in units[key])
        origin = child(units[key], 'country_potential').strip()
        expected = {c['tag'] for c in manifest['countries'] if c['region'] == region}
        if 'presentation_v040' in manifest:
            # 0.4.0 replaced the tag list with the shared origin trigger.
            check(key+' elite visibility is home-circle only', origin == 'hbe_research_origin_'+region+' = yes')
        else:
            check(key+' elite visibility is home-circle only', set(re.findall(r'has_or_had_tag\s*=\s*(\w+)', origin)) == expected and 'has_variable' not in origin)
        gate = triggers[ready_key(row)]
        check(key+' requires both native and studied home military', 'has_advance = '+row['native_advance'] in gate and 'has_advance = hbe_military_'+region in gate and 'has_variable' not in gate)
        check(key+' has no calendar or final-story requirement', not any(term in units[key]+gate for term in ('current_year', 'current_date', 'hbe_mission_', 'hbe_civic_'+region+'_2')))
        check(key+' retains employed local institution and burden checks', 'building_employed_amount >= 0.05' in units[key] and 'var:hbe_burden < 70' in units[key] and 'hbe_operating_' in units[key])
        check(first+' guest base recruitment survives native era research', 'NOT = { '+ready_key(row)+' = yes }' in units[first] and 'has_variable = hbe_guest_'+region in units[first])
        for lang in ('simp_chinese', 'english'):
            loc = '\n'.join(p.read_text(encoding='utf-8-sig') for p in (mod/f'main_menu/localization/{lang}').glob('*.yml'))
            check(key+' '+lang+' name and description unique', all(len(re.findall(r'(?m)^ '+re.escape(k)+':', loc)) == 1 for k in (key, key+'_desc')))
    recipes = definitions((mod/'in_game/common/goods_demand/hbe_age2_military.txt').read_text(encoding='utf-8-sig'))
    for key, expected in config['recipes'].items():
        actual = {k: float(v) if re.fullmatch(r'\d+(?:\.\d+)?', v) else v for k, v, _, _ in scalars(recipes[key])}
        check(key+' uses dynamic priced equipment with the agreed surcharge', actual == expected)
    check('no global technology or unit GUI overrides introduced', not any((mod/path).exists() for path in ('main_menu/gui/shared/advances_tooltips.gui', 'in_game/gui/technology_lateralview.gui', 'in_game/gui/unit_type_lateralview.gui', 'in_game/gui/unit_overview.gui')))
