"""Second-age HBE successors attached to existing native advances; no new nodes."""
from pathlib import Path
import argparse
import copy
import json
import re

from pdxscript import blocks, apply_edits
from build_early_research import scalars, remove_fields, set_fields, update_localization
from build_support import snapshot_files, sha256_file, write_preserving_format

CONFIG = 'data/age2_military.json'
UNITS = 'in_game/common/unit_types/hbe_civic_units.txt'
TRIGGERS = 'in_game/common/scripted_triggers/hbe_age2_military.txt'


def put(path, text):
    path = Path(path)
    if not path.exists() and path.suffix in ('.txt', '.yml'):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8-sig', newline='\n')
    else:
        write_preserving_format(path, text)


def definitions(text):
    return {key: text[a:b] for key, _, a, b, _ in blocks(text, 0)}


def child(body, key):
    return next(body[a:b] for name, _, a, b, _ in blocks(body, 0) if name == key)


def replace_child(body, key, replacement):
    return apply_edits(body, [(a, b, replacement) for name, _, a, b, _ in blocks(body, 0) if name == key])


def ready_key(row):
    return 'hbe_age2_' + row['region'] + '_qualified'


def patch_native(text, rows):
    """Only append unlock fields; preserve native cost, prerequisites and first unit."""
    edits = []
    for key, _, a, b, _ in blocks(text, 0):
        additions = [row['key'] for row in rows if row['native_advance'] == key]
        if not additions:
            continue
        body = text[a:b]
        # Regenerate from the native source on every run, never accumulate additions.
        body = body.rstrip() + '\n' + ''.join('\tunlock_unit = ' + unit + '\n' for unit in additions)
        edits.append((a, b, body))
    return apply_edits(text, edits)


def scalar_script(values):
    text = ''
    for key, value in values.items():
        if isinstance(value, dict):
            text += ' ' + key + ' = { ' + ' '.join(k + ' = ' + f'{v:g}' for k, v in value.items()) + ' }\n'
        else:
            value = f'{value:g}' if isinstance(value, (int, float)) else value
            text += ' ' + key + ' = ' + value + '\n'
    return text


def apply(out, root, game):
    out, root, game = map(Path, (out, root, game))
    config = json.loads((root / CONFIG).read_text(encoding='utf-8'))
    rows = config['units']
    mp = out / 'build_manifest.json'
    manifest = json.loads(mp.read_text(encoding='utf-8-sig'))
    before = (out / UNITS).read_text(encoding='utf-8-sig')
    source = definitions(before)
    military = definitions((out / 'in_game/common/advances/hbe_local_military.txt').read_text(encoding='utf-8-sig'))
    # Retain the original unit ordering, required by the nine-cell artwork atlas.
    base_keys = [row['from_unit'] for row in rows] + ['hbe_trained_river', 'hbe_permanent_pass']
    bodies = {key: source[key] for key in base_keys}
    triggers = []
    entries = {'simp_chinese': {}, 'english': {}}
    for row in rows:
        region, key, first = row['region'], row['key'], row['from_unit']
        origin = child(military['hbe_military_' + region], 'potential')
        qualified = ready_key(row)
        triggers.append(qualified + ' = {\n' + origin + '\n is_member_of_international_organization = international_organization:hbe_empire\n has_advance = hbe_military_' + region + '\n has_advance = ' + row['native_advance'] + '\n}')
        # Reuse the real building/employment, supply, local compact and burden gates.
        trigger = child(source[first], 'location_trigger')
        owner = child(trigger, 'owner')
        owner = re.sub(r'NOT\s*=\s*\{\s*has_advance\s*=\s*hbe_civic_\w+_2\s*\}', '', owner)
        owner = re.sub(r'NOT\s*=\s*\{\s*hbe_age2_\w+_qualified\s*=\s*yes\s*\}', '', owner)
        gate_edits = [(s, e, '') for name, s, a, b, e in blocks(owner, 0)
                      if name == 'OR' and ('has_advance = hbe_military_' + region in owner[a:b])]
        owner = apply_edits(owner, gate_edits) + '\n ' + qualified + ' = yes\n'
        trigger = replace_child(trigger, 'owner', owner)
        values = row['unit_definition_scalars_and_combat']
        # Keep this declaration compact for compatibility with existing validators.
        body = '\n copy_from = ' + values['copy_from'] + '\n hide = no buildable = yes levy = no is_special = yes family = ' + config['unit_family'] + '\n'
        body += scalar_script({k: v for k, v in values.items() if k not in {'copy_from', 'hide', 'buildable', 'levy', 'is_special', 'family'}})
        body += ' country_potential = { ' + origin + ' }\n'
        body += ' location_potential = { ' + child(source[first], 'location_potential') + ' }\n'
        body += ' location_trigger = { ' + trigger + ' }\n'
        body += ' gfx_tags = { ' + child(source[first], 'gfx_tags') + ' }\n'
        bodies[key] = body
        # Retire first-age recruitment only for a qualified home-circle country.
        old = bodies[first]
        old = re.sub(r'NOT\s*=\s*\{\s*has_advance\s*=\s*hbe_civic_\w+_2\s*\}', '', old)
        old = re.sub(r'NOT\s*=\s*\{\s*hbe_age2_\w+_qualified\s*=\s*yes\s*\}', '', old)
        loc = child(old, 'location_trigger')
        own = child(loc, 'owner') + '\n NOT = { ' + qualified + ' = yes }\n'
        old = replace_child(old, 'location_trigger', replace_child(loc, 'owner', own))
        bodies[first] = set_fields(old, {'upgrades_to': key})
        for lang in entries:
            zh = lang == 'simp_chinese'
            name = row['name'] if zh else row['english']
            entries[lang][key] = name
            entries[lang][qualified + '_tt'] = ('已研究本圈基础军制及「$' + row['native_advance'] + '$」，并保持HBE成员身份。' if zh else 'Requires home-circle military training, $' + row['native_advance'] + '$ and HBE membership.')
            entries[lang][key + '_desc'] = (row['description'] if zh else row['english'] + ' continues the home-circle military tradition with improved equipment and organization.') + ('\n\n每队500人。研究「$' + row['native_advance'] + '$」后可用；仍须掌握「$hbe_military_' + region + '$」并满足当地机构、供养、役负与共同额度条件。客籍议约仅提供基础军制资格。旧队可依原版规则付费换装，不另增役负。' if zh else '\n\n500 men per regiment. Unlocked by $' + row['native_advance'] + '$; home-circle $hbe_military_' + region + '$, local institutions, supply, burden and shared capacity remain required. Guest compacts grant only basic military rights. Existing regiments use native paid upgrades without an extra burden charge.')
        # Provide a localized, collapsible requirement in recruitment tooltips.
        triggers[-1] = qualified + ' = { custom_tooltip = { text = ' + qualified + '_tt\n' + triggers[-1].split('{', 1)[1].rsplit('}', 1)[0] + '\n} }'
    order = base_keys + [row['key'] for row in rows if row['key'] not in base_keys]
    def clean(body):
        return '\n' + '\n'.join(' ' + ' '.join(line.split()) for line in body.splitlines() if line.strip())
    put(out / UNITS, '\n'.join(key + ' = {' + clean(bodies[key]) + '\n}\n' for key in order))
    put(out / TRIGGERS, '\n'.join(triggers) + '\n')

    native_patches = []
    for relative in config['tech_files']:
        native = (game / relative).read_text(encoding='utf-8-sig')
        target = out / relative
        if target.exists():
            current = target.read_text(encoding='utf-8-sig')
            allowed = patch_native(native, rows)
            assert current in (native, allowed), 'Unexpected existing native advance override: ' + str(target)
        put(target, patch_native(native, rows))
        native_patches.append({'file': relative, 'source_sha256': sha256_file(game / relative), 'patched_advances': [k for k in definitions(native) if any(r['native_advance'] == k for r in rows)]})

    civic = out / 'in_game/common/advances/hbe_civic_advances.txt'
    text = civic.read_text(encoding='utf-8-sig')
    edits = []
    for name, _, a, b, _ in blocks(text, 0):
        if name in ('hbe_civic_eastern_river_2', 'hbe_civic_northern_shudao_2'):
            edits.append((a, b, remove_fields(text[a:b], {'unlock_unit'})))
    put(civic, apply_edits(text, edits))
    for lang in entries:
        core = out / f'main_menu/localization/{lang}/hbe_l_{lang}.yml'
        # Existing names and descriptions are updated in place, avoiding duplicate keys.
        old = {key: entries[lang].pop(key) for key in ('hbe_trained_river', 'hbe_trained_river_desc', 'hbe_permanent_pass', 'hbe_permanent_pass_desc')}
        zh = lang == 'simp_chinese'
        for region in ('eastern_river', 'northern_shudao'):
            old['hbe_civic_' + region + '_2_effects'] = ('完善本圈军队的长期供养与统筹；二代特色兵由原版重步兵科技解锁，仍须掌握本圈基础军制。' if zh else 'Improves long-term military administration. Second-age troops are unlocked by the native men-at-arms advance and still require home-circle military training.')
        update_localization(core, old)
        for recipe in config['recipes']:
            entries[lang][recipe] = ('二代特色兵装备维护' if 'maintenance' in recipe else '劲弩装备制作') if zh else ('Second-age Specialty Equipment Upkeep' if 'maintenance' in recipe else 'Veteran Crossbow Equipment')
        put(out / f'main_menu/localization/{lang}/hbe_age2_military_l_{lang}.yml', 'l_' + lang + ':\n' + '\n'.join(' ' + key + ': ' + json.dumps(value, ensure_ascii=False) for key, value in entries[lang].items()) + '\n')

    put(out / 'in_game/common/goods_demand/hbe_age2_military.txt', '\n'.join(key + ' = {\n' + scalar_script(values) + '}\n' for key, values in config['recipes'].items()))
    path = out / 'in_game/common/script_values/hbe_civic_values.txt'
    text = path.read_text(encoding='utf-8-sig')
    put(path, apply_edits(text, [(a, b, ' ' + ' '.join('add = total_sub_unit_type_count:' + key for key in order) + ' ') for key, _, a, b, _ in blocks(text, 0) if key == 'hbe_civic_special_count']))

    # Alias the five new units to their continuous native-layout predecessor art.
    # No duplicate DDS, no new portrait cropping, no GUI override.
    registry = out / 'in_game/gfx/unit_illustrations/hbe_civic_illustrations.txt'
    registry_text = registry.read_text(encoding='utf-8-sig')
    existing_keys = set(base_keys)
    registry_text = '\n'.join(registry_text[s:e] for key, s, _, _, e in blocks(registry_text, 0) if key.removesuffix('_illustration') in existing_keys) + '\n'
    art = manifest['unit_detail_art_v031']
    art['assets'] = [row for row in art['assets'] if row['unit'] in existing_keys]
    art_by_unit = {row['unit']: row for row in art['assets']}
    for row in rows:
        if row['key'] in existing_keys:
            continue
        first, key = row['from_unit'], row['key']
        texture = art_by_unit[first]['texture']
        relative = texture.removeprefix('main_menu/')
        registry_text += key + '_illustration = { texture = "' + relative + '" priority = 950000 trigger = { is_unit_type = ' + key + ' } }\n'
        alias = copy.deepcopy(art_by_unit[first])
        alias.update(unit=key, artwork_from=first)
        art['assets'].append(alias)
    art['units'] = len(order)
    put(registry, registry_text)
    # Keep the old catalogue's two unit unlock owners in agreement with the database.
    for item in manifest['social_expansion']['units']:
        match = next((r for r in rows if r['key'] == item['key']), None)
        if match:
            item['advance'] = match['native_advance']
    report = {'unit_count': len(order), 'new_units': 5, 'new_advances': 0, 'lines': [{k: row[k] for k in ('region', 'from_unit', 'key', 'name', 'native_advance', 'target_effective_stats')} for row in rows], 'native_patches': native_patches, 'all_men': 500, 'native_upgrade': True, 'upgrade_burden': 0, 'net_new_regiment_burden': 2, 'guest_elites': False, 'art_reuse': True, 'visual_verified': False}
    manifest['age2_military'] = report
    metadata_path = out / '.metadata/metadata.json'
    metadata = json.loads(metadata_path.read_text(encoding='utf-8-sig'))
    metadata['short_description'] = metadata['short_description'].replace('九种特色兵', '七条特色兵换代线')
    put(metadata_path, json.dumps(metadata, ensure_ascii=False, indent=2) + '\n')
    manifest['files'] = snapshot_files(out)
    put(mp, json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--game', type=Path, required=True)
    args = parser.parse_args()
    result = apply(args.root / 'mod/holy_bashu_empire', args.root, args.game)
    print(json.dumps({key: result[key] for key in ('unit_count', 'new_units', 'new_advances', 'all_men')}))
