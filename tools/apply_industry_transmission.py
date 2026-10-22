"""Optional, licensed age-two sidework on native buildings; no installation or game launch."""
from build_support import sha256_file as sha, snapshot_files
from pathlib import Path
import argparse
import json
import re

from PIL import Image, ImageDraw, ImageFont
from build_flags import save_dds
from build_icon_assets import fit
from pdxscript import apply_edits, blocks, tokens




def load_config(root):
    return json.loads((Path(root) / 'data/industry_transmission.json').read_text(encoding='utf-8'))


def put(out, relative, text):
    path = Path(out) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    newline = '\r\n' if path.exists() and b'\r\n' in path.read_bytes() else '\n'
    path.write_text(text.rstrip() + '\n', encoding='utf-8-sig', newline=newline)


def ids(row):
    stem = 'hbe_transmission_' + row['id']
    return stem, stem + '_license', stem + '_ready', stem + '_sidework', stem + '_off'


def price_map(game, out):
    result = {}
    for folder in (Path(game) / 'in_game/common/goods', Path(out) / 'in_game/common/goods'):
        for path in folder.glob('*.txt'):
            text = path.read_text(encoding='utf-8-sig')
            for key, _, start, end, _ in blocks(text, 0):
                price = re.search(r'\bdefault_market_price\s*=\s*([\d.]+)', text[start:end])
                if price:
                    result[key] = float(price[1])
    return result


def native_extension(text, rows):
    """Only replace our own slots and the added salt exception; retain other native fields."""
    carriers = {carrier: row for row in rows for carrier in row['carriers']}
    edits = []
    found = set()
    for key, _, start, end, _ in blocks(text, 0):
        if key not in carriers:
            continue
        found.add(key)
        row = carriers[key]
        body = text[start:end].replace('    # Optional sidework; all native production slots above remain intact.\n', '')
        inner = []
        for field, field_start, a, b, field_end in blocks(body, 0):
            if field == 'possible_production_methods' and 'hbe_transmission_' in body[a:b]:
                inner.append((field_start, field_end, ''))
            if field == 'location_potential' and key == 'salt_collector':
                # Our exception lives alongside the two unmodified native branches.
                geo = body[a:b]
                ors = [(x, y) for k, _, x, y, _ in blocks(geo, 0) if k == 'OR']
                assert len(ors) == 1, 'Unexpected native salt location predicate'
                x, y = ors[0]
                choices = geo[x:y]
                old = [(fs, fe, '') for k, fs, u, v, fe in blocks(choices, 0)
                       if k == 'AND' and 'hbe_transmission_well_salt_ready' in choices[u:v]]
                choices = apply_edits(choices, old)
                choices = choices.replace('            # Licensed inland saltworks require an actual salt resource.\n', '').rstrip()
                choices += '''
            # Licensed inland saltworks require an actual salt resource.
            AND = {
                raw_material = goods:salt
                owner ?= { hbe_transmission_well_salt_ready = yes }
            }
'''
                inner.append((a, b, apply_edits(geo, [(x, y, choices)])))
        body = apply_edits(body, inner)
        _, _, _, active, off = ids(row)
        body = body.rstrip() + f'\n\n    # Optional sidework; all native production slots above remain intact.\n    possible_production_methods = {{ {off} {active} }}\n'
        edits.append((start, end, body))
    assert found == set(carriers), (found, set(carriers))
    return apply_edits(text, edits)


def export_icons(out, root, config):
    source = Path(root) / config['atlas']
    image = Image.open(source).convert('RGBA')
    assert image.width == image.height and image.getchannel('A').getextrema()[0] == 0
    proof = Image.new('RGB', (800, 460), '#302a23')
    draw = ImageDraw.Draw(proof)
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 20)
    result = []
    for index, row in enumerate(config['industries']):
        column, line = index % 2, index // 2
        box = tuple(round(v) for v in (column * image.width / 2, line * image.height / 2,
                                      (column + 1) * image.width / 2, (line + 1) * image.height / 2))
        sprite = fit(image.crop(box), 256)
        stem = ids(row)[0]
        png = Path(root) / f'assets/technology_icons/{stem}.png'
        png.parent.mkdir(parents=True, exist_ok=True)
        sprite.save(png)
        for folder in ('advance', 'hbe/technology'):
            save_dds(Path(out) / f'main_menu/gfx/interface/{folder}/{stem}.dds', sprite)
        x, y = index * 200, 22
        proof.paste(sprite.resize((176, 176), Image.Resampling.LANCZOS), (x + 12, y),
                    sprite.resize((176, 176), Image.Resampling.LANCZOS))
        draw.text((x + 30, 210), row['name'], fill='#ead59b', font=font)
        for j, size in enumerate((64, 40, 24)):
            small = fit(image.crop(box), size)
            proof.paste(small, (x + 18 + j * 62, 280), small)
        path = f'main_menu/gfx/interface/advance/{stem}.dds'
        result.append(dict(key=stem, cell=index, crop=list(box), image=path, sha256=sha(Path(out) / path)))
    preview = Path(root) / 'assets/industry_transmission/technology_icons_preview.png'
    proof.crop((0, 0, 800, 360)).save(preview)
    return result


def apply_building_caps(out, rows, loc):
    """Two institutions initially, a third after the matching transmission advance."""
    path = 'in_game/common/building_types/hbe_civic_buildings.txt'
    text = (out / path).read_text(encoding='utf-8-sig')
    by_building = {row['special_building']: row for row in rows}
    edits = []
    for building, _, start, end, _ in blocks(text, 0):
        if building not in by_building:
            continue
        row = by_building[building]
        stem = ids(row)[0]
        body = text[start:end]
        old = f'hbe_civil_institution_below_cap = {{ type = {building} }}'
        guard = f'{stem}_below_cap = yes'
        assert old in body or guard in body, building
        body = body.replace(old, guard).replace('# HBE_INDUSTRY_BALANCE_PATCH: national cap 3, civilian modifiers 0.5x.',
                                             '# HBE_INDUSTRY_BALANCE_PATCH: national cap 2, raised to 3 by transmission; civilian modifiers 0.5x.')
        edits.append((start, end, body))
    assert len(edits) == 4
    put(out, path, apply_edits(text, edits))
    # Keep existing localization keys unique instead of adding competing overrides.
    names_en = {'hbe_brocade_school': 'Brocade Instruction Hall', 'hbe_salt_office': 'Well-Salt Office',
                'hbe_gate_registry': 'Pass Contract Registry', 'hbe_tea_exchange': 'Tea-Horse Exchange'}
    for language in loc:
        chinese = language == 'simp_chinese'
        relative = f'main_menu/localization/{language}/hbe_l_{language}.yml'
        core = (out / relative).read_text(encoding='utf-8-sig')
        for row in rows:
            building, stem = row['special_building'], ids(row)[0]
            desc = (
                f"${building}$保存本地工艺与事业凭据，实际作用取决于就业和材料供养。\\n\\n取得基础建筑资格后，全国同类最多两座；研究「${stem}$」后，上限增加一座至三座。名额包含在建，每个地点最多一级。客籍与整国吞并继承沿用原有资格和地域条件。\\n\\n可选择${row['goods']}$基础工序或原版货物工序；进阶工序另需相应科技。生产消耗市场材料，产物进入市场，日常供养仍须维持。"
                if chinese else
                f"The ${building}$ preserves local crafts and institutional records. Its effects depend on employment and supplied materials.\\n\\nAn established building license permits two institutions nationwide. Researching ${stem}$ adds one slot, raising the cap to three. Construction queues count toward the cap; each location supports one level. Existing geographic rules and guest or full-annexation licenses still apply.\\n\\nSelect starter ${row['goods']}$ production or an ordinary-goods recipe; advanced recipes retain their own technology requirements. Materials are purchased and products sold through the market. Routine maintenance remains necessary."
            )
            # Keep actual newlines in Python strings; JSON encoding escapes them once.
            desc = desc.replace('\\n', '\n')
            core, count = re.subn(r'(?m)^ ' + re.escape(building + '_desc') + r':.*$',
                                  lambda _: ' ' + building + '_desc: ' + json.dumps(desc, ensure_ascii=False), core)
            assert count == 1, (language, building)
            if not chinese:
                core, count = re.subn(r'(?m)^ ' + re.escape(building) + r':.*$',
                                      lambda _: ' ' + building + ': ' + json.dumps(names_en[building]), core)
                assert count == 1
            # The original unlocking advance explains the initial cap, including the paper exception.
            key = row['building_advance'] + '_effects'
            match = re.search(r'(?m)^ ' + re.escape(key) + r':\s*(".*")$', core)
            assert match, key
            old_effects = json.loads(match[1])
            line = (f"${building}$基础上限两座；研究「${stem}$」后增至三座（含在建，每处一级）。"
                    if chinese else f"${building}$: initial cap of two; ${stem}$ raises it to three, including construction, one level per location.")
            lines = [s for s in old_effects.splitlines() if not (s.startswith('$' + building + '$') and ('上限' in s or 'initial cap' in s))]
            value = '\n'.join(lines + [line])
            core = core[:match.start(1)] + json.dumps(value, ensure_ascii=False) + core[match.end(1):]
        put(out, relative, core)


def apply(out, root, game):
    out, root, game = map(Path, (out, root, game))
    config = load_config(root)
    rows = config['industries']
    # Native advance potential is evaluated when the country's tree is created;
    # earned research/licenses belong in allow, so nodes remain visible beforehand.
    manifest = json.loads((out / 'build_manifest.json').read_text(encoding='utf-8-sig'))
    visibility_by_advance = {}
    loc = {language: {} for language in ('simp_chinese', 'english')}
    advances, triggers, methods = [], [], []
    for row in rows:
        stem, license_trigger, ready, active, off = ids(row)
        region = row['region']
        visibility_tags = [country['tag'] for country in manifest['countries'] if country['region'] == region]
        visibility_by_advance[stem] = visibility_tags
        visibility = 'OR = { ' + ' '.join('has_or_had_tag = ' + tag for tag in visibility_tags) + ' }'
        qualification = f"{visibility} has_advance = {row['building_advance']}"
        triggers.append(f'''{license_trigger} = {{
    custom_tooltip = {{ text = {license_trigger}_tt {qualification} }}
}}
{ready} = {{
    {license_trigger} = yes
    custom_tooltip = {{ text = {stem}_researched_tt has_advance = {stem} }}
}}
# Location scope, matching the existing building allow/actor convention.
{stem}_below_cap = {{
    custom_tooltip = {{
        text = {stem}_cap_tt
        scope:actor = {{
            OR = {{
                AND = {{ NOT = {{ has_advance = {stem} }} total_building_levels_including_construction:{row['special_building']} < 2 }}
                AND = {{ has_advance = {stem} total_building_levels_including_construction:{row['special_building']} < 3 }}
            }}
        }}
    }}
}}''')
        advances.append(f'''{stem} = {{
    age = {config['age']}
    starting_technology_level = 99
    research_cost = {config['research_cost']:g}
    content_priority = 830
    icon = {stem}
    requires = {row.get('parent', config['parent'])}
    potential = {{ hbe_research_origin_{region} = yes }}
    allow = {{
        is_member_of_international_organization = international_organization:hbe_empire
        {license_trigger} = yes
    }}
    pure_tooltip_entry = {stem}_effects
    unlock_production_method = {active}
    ai_weight = {{ add = 20 }}
}}''')
        inputs = '\n'.join(f'    {good} = {amount:g}' for good, amount in row['inputs'].items())
        methods.append(f'''# The first option is deliberately free and always available, including before research.
{off} = {{
    icon_type = goods
    icon = {row['goods']}
    category = {row['category']}
}}
{active} = {{
    icon_type = goods
    icon = {row['goods']}
    allow = {{ {ready} = yes }}
{inputs}
    produced = {row['goods']}
    output = {row['output']:g}
    category = {row['category']}
}}''')
        for language, entries in loc.items():
            chinese = language == 'simp_chinese'
            carriers = '、'.join('$' + k + '$' for k in row['carriers']) if chinese else ', '.join('$' + k + '$' for k in row['carriers'])
            costs = ('、' if chinese else ', ').join(f"{amount:g} ${good}$" for good, amount in row['inputs'].items())
            entries[stem] = row['name'] if chinese else row['english']
            entries[stem + '_desc'] = row['description'] if chinese else row['description_english']
            entries[stem + '_effects'] = (
                f"{carriers}可选择「{row['method_name']}」。保留原有生产；每级副产{row['output']:g} ${row['goods']}$，额外消耗{costs}。约{row['levels_per_special_building']}级抵一座${row['special_building']}$基础工序。副业可关闭，不提供全局加成。"
                if chinese else
                f"Enables {row['method_english']} in {carriers}. Existing production is retained. Each level adds {row['output']:g} ${row['goods']}$ and consumes {costs}. About {row['levels_per_special_building']} levels match one ${row['special_building']}$ starter recipe. Sidework can be disabled; no national modifiers are granted."
            )
            if row['id'] == 'well_salt':
                entries[stem + '_effects'] += ('允许在本国普通盐资源地点建设原版盐场；沿海与沙漠的原有条件保留。' if chinese else ' Also permits native saltworks on owned salt-resource locations; existing coastal and desert eligibility is preserved.')
            recipe_description = entries[stem + '_effects']
            entries[stem + '_effects'] += (f"\n${row['special_building']}$全国上限增加一座：由两座增至三座（含在建，每处一级）。" if chinese else
                                          f"\nAdds one national ${row['special_building']}$ slot, increasing the cap from two to three, including construction; one level per location.")
            entries[stem + '_cap_tt'] = (f"同类机构基础上限两座；研究「${stem}$」后为三座（含在建），每处最多一级。" if chinese else
                                       f"The national cap is two, increased to three by ${stem}$; includes construction, one level per location.")
            entries[license_trigger + '_tt'] = (
                f"本国源自本圈，并已研究「${row['building_advance']}$」；客籍与吞并凭据仅承继基础产业，不授予本圈专属进阶工艺"
                if chinese else f"Originates in this circle and has researched ${row['building_advance']}$. Guest and annexation certificates retain starter industries only, not this circle-specific advanced craft."
            )
            entries[stem + '_researched_tt'] = (f'已研究「${stem}$」' if chinese else f'Has researched ${stem}$.')
            entries[active] = row['method_name'] if chinese else row['method_english']
            entries[off] = '不兼营' if chinese else 'No Sidework'
            entries[active + '_desc'] = recipe_description
            entries[off + '_desc'] = ('仅维持原有工序；不消耗副业原料，也不产出特产。' if chinese else 'Retains existing production without sidework inputs or specialty output.')
    apply_building_caps(out, rows, loc)
    put(out, 'in_game/common/advances/hbe_industry_transmission.txt', '\n\n'.join(advances))
    put(out, 'in_game/common/scripted_triggers/hbe_industry_transmission.txt', '\n\n'.join(triggers))
    put(out, 'in_game/common/production_methods/hbe_industry_transmission.txt', '\n\n'.join(methods))
    for language, entries in loc.items():
        put(out, f'main_menu/localization/{language}/hbe_industry_transmission_l_{language}.yml',
            f'l_{language}:\n' + '\n'.join(' ' + k + ': ' + json.dumps(v, ensure_ascii=False) for k, v in entries.items()))

    native_hashes = {}
    for filename in dict.fromkeys(row['file'] for row in rows):
        relative = 'in_game/common/building_types/' + filename
        native = game / relative
        target = out / relative
        text = (target if target.exists() else native).read_text(encoding='utf-8-sig')
        put(out, relative, native_extension(text, [row for row in rows if row['file'] == filename]))
        native_hashes[relative] = sha(native)
    icons = export_icons(out, root, config)
    prices = price_map(game, out)
    balance = []
    for row in rows:
        cost = sum(prices[g] * value for g, value in row['inputs'].items())
        value = prices[row['goods']] * row['output']
        assert .70 <= cost / value <= .85, (row['id'], cost / value)
        balance.append(dict(id=row['id'], output=row['output'], levels=row['levels_per_special_building'],
                            inputs=row['inputs'], reference_input_value=round(cost, 6),
                            reference_output_value=round(value, 6), cost_share=round(cost / value, 6)))
    result = dict(advance_count=4, carrier_count=sum(len(row['carriers']) for row in rows),
                  advances=[ids(row)[0] for row in rows], active_methods=[ids(row)[3] for row in rows],
                  off_methods=[ids(row)[4] for row in rows], age=config['age'],
                  parents={ids(row)[0]: row.get('parent', config['parent']) for row in rows},
                  institution_caps={row['special_building']: dict(initial=2, researched=3, advance=ids(row)[0], includes_construction=True, levels_per_location=1) for row in rows},
                  balance=balance, icons=icons, native_source_hashes=native_hashes,
                  visibility='Stable originating-circle tag history; never all HBE tags or earned research in potential.',
                  visibility_tags=visibility_by_advance,
                  qualification='Originating circle AND actual original building advance. Guest and annexation certificates retain starter industries only.',
                  reference_price_note='Reference-price arithmetic only; actual supply, wages, prices and modifiers determine realized profitability.')
    path = out / 'build_manifest.json'
    manifest = json.loads(path.read_text(encoding='utf-8-sig'))
    manifest['industry_transmission'] = result
    for building in manifest.get('social_expansion', {}).get('buildings', []):
        if building['key'] in result['institution_caps']:
            building['unique_country'] = False
            building['national_cap'] = result['institution_caps'][building['key']]
    manifest['research_nodes'] = 80 + len(rows)
    if 'formables_units_v031' in manifest:
        manifest['formables_units_v031']['date_free_advances'] = [k for p in (out / 'in_game/common/advances').glob('hbe*.txt') for k, *_ in blocks(p.read_text(encoding='utf-8-sig'), 0)]
    manifest['files'] = snapshot_files(out)
    newline = '\r\n' if b'\r\n' in path.read_bytes() else '\n'
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline=newline)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--mod-dir', type=Path)
    parser.add_argument('--game-dir', type=Path, default=Path('D:/SteamLibrary/steamapps/common/Europa Universalis V/game'))
    args = parser.parse_args()
    result = apply(args.mod_dir or args.root / 'mod/holy_bashu_empire', args.root, args.game_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))
