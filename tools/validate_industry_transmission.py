"""Native-recipe preservation, access scenarios, economics and art checks for sidework."""
from pathlib import Path
import argparse
import hashlib
import itertools
import json
import re
import struct

from PIL import Image
from apply_industry_transmission import ids, load_config, native_extension, price_map
from pdxscript import apply_edits, blocks, tokens


def definitions(text):
    return {key: text[start:end] for key, _, start, end, _ in blocks(text, 0)}


def direct_values(text):
    """Only scalar fields at this depth; inputs and gates cannot masquerade as outputs."""
    stream = tokens(text)
    depth, result = 0, {}
    for i, token in enumerate(stream):
        if token.value == '{':
            depth += 1
        elif token.value == '}':
            depth -= 1
        elif not depth and i + 2 < len(stream) and stream[i + 1].value == '=' and stream[i + 2].value != '{':
            result[token.value] = stream[i + 2].value
    return result


def evaluate(text, advances, member=True, tag_history=(), origin=None, definitions=None):
    """Evaluate the qualification subset without discarding repeated predicates."""
    def terms(source):
        result=[]
        for key,_,a,b,_ in blocks(source,0):
            values=terms(source[a:b])
            if key in ('AND','custom_tooltip'):result.append(all(values))
            elif key=='OR':result.append(any(values))
            elif key=='NOT':result.append(not all(values))
            else:raise AssertionError('Unrecognized trigger block: '+key)
        depth=0;stream=tokens(source)
        for i,token in enumerate(stream):
            if token.value=='{':depth+=1
            elif token.value=='}':depth-=1
            elif not depth and i+2<len(stream) and stream[i+1].value=='=' and stream[i+2].value!='{':
                key,value=token.value,stream[i+2].value
                if key=='has_advance':result.append(value in advances)
                elif key=='has_or_had_tag':result.append(value in tag_history)
                elif key=='is_member_of_international_organization':result.append(member if value=='international_organization:hbe_empire' else value=='international_organization:hbe_circle_'+str(origin))
                elif key=='has_variable' and value.startswith('hbe_home_'):result.append(value=='hbe_home_'+str(origin))
                elif key=='has_variable' and value=='hbe_initialized':result.append(origin is not None)
                elif definitions and key in definitions:result.append(all(terms(definitions[key])))
                elif key=='always':result.append(value=='yes')
                elif key!='text':raise AssertionError('Unrecognized trigger scalar: '+key)
        return result
    return all(terms(text))


def strip_sidework(body):
    edits = [(a, z, '') for k, a, start, end, z in blocks(body, 0)
             if k == 'possible_production_methods' and 'hbe_transmission_' in body[start:end]]
    return apply_edits(body, edits)


def token_values(text):
    return [token.value for token in tokens(text)]


def validate(mod, root, game, manifest, check):
    if 'industry_transmission' not in manifest:
        return
    mod, root, game = map(Path, (mod, root, game))
    config = load_config(root)
    rows = config['industries']
    read = lambda path: (mod / path).read_text(encoding='utf-8-sig')
    data = manifest['industry_transmission']
    advance_text = read('in_game/common/advances/hbe_industry_transmission.txt')
    advances = definitions(advance_text)
    trigger_text = read('in_game/common/scripted_triggers/hbe_industry_transmission.txt')
    triggers = definitions(trigger_text)
    method_text = read('in_game/common/production_methods/hbe_industry_transmission.txt')
    methods = definitions(method_text)
    check('four licensed transmission advances, eight sidework choices and ten carriers',
          len(advances) == len(rows) == data['advance_count'] == 4 and len(methods) == 8 and data['carrier_count'] == 10)
    check('transmission advances have no calendar gates or free scripted research',
          'current_year' not in advance_text and 'current_date' not in advance_text and
          not any(re.search(r'research_advance\s*=\s*advance_type:' + re.escape(key) + r'\b', p.read_text(encoding='utf-8-sig'))
                  for p in (mod / 'in_game/common/scripted_effects').glob('*.txt') for key in advances))
    prices = price_map(game, mod)
    original_building_text = read('in_game/common/building_types/hbe_civic_buildings.txt')
    original_buildings = definitions(original_building_text)
    unlocked = re.findall(r'\bunlock_production_method\s*=\s*(\w+)', advance_text)
    premium = set(manifest.get('production_advance_semantics_v032', {}).get('moved_methods', []))
    check('four paid sidework recipes and assigned premium processes are advance-locked; off remains available', set(unlocked) == set(data['active_methods']) | premium and not set(data['off_methods']) & set(unlocked))
    native_sources = {}
    for filename in {row['file'] for row in rows}:
        relative = 'in_game/common/building_types/' + filename
        native = (game / relative).read_text(encoding='utf-8-sig')
        output = read(relative)
        original, patched = definitions(native), definitions(output)
        native_sources[filename] = original
        carriers = {carrier for row in rows if row['file'] == filename for carrier in row['carriers']}
        check(filename + ' preserves every native building definition exactly once',
              len(blocks(output, 0)) == len(patched) == len(original) and patched.keys() == original.keys())
        check(filename + ' native baseline fingerprint matches manifest',
              hashlib.sha256((game / relative).read_bytes()).hexdigest() == data['native_source_hashes'][relative])
        for key, body in patched.items():
            cleaned = strip_sidework(body)
            if key == 'salt_collector':
                edits = []
                for k, _, start, end, _ in blocks(cleaned, 0):
                    if k == 'location_potential':
                        edits.append((start, end, '\n OR = { vegetation = desert is_coastal = yes }\n'))
                cleaned = apply_edits(cleaned, edits)
            check(key + ' retains native inputs outputs upkeep employment modifiers and upgrade path',
                  token_values(cleaned) == token_values(original[key]))
            if key in carriers:
                slots = [body[a:b] for k, _, a, b, _ in blocks(body, 0) if k == 'possible_production_methods' and 'hbe_transmission_' in body[a:b]]
                check(key + ' has exactly one optional sidework slot', len(slots) == 1)
        check(filename + ' patch is byte-stable when repeated', native_extension(output, [r for r in rows if r['file'] == filename]) == output)
    salt = definitions(read('in_game/common/building_types/common_buildings.txt'))['salt_collector']
    geo = next(salt[a:b] for k, _, a, b, _ in blocks(salt, 0) if k == 'location_potential')
    check('inland salt exception checks actual salt resource and current owner readiness',
          'raw_material = goods:salt' in geo and 'owner ?= { hbe_transmission_well_salt_ready = yes }' in geo and 'vegetation = desert' in geo and 'is_coastal = yes' in geo)
    native_advances = '\n'.join(p.read_text(encoding='utf-8-sig') for p in (game / 'in_game/common/advances').glob('*.txt'))
    check('native tree parent is a real age-two technology', 'renaissance_development' in definitions(native_advances) and 'age = age_2_renaissance' in definitions(native_advances)['renaissance_development'])
    licenses = definitions(read('in_game/common/advances/hbe_guest_licenses.txt'))
    licenses.update(definitions(read('in_game/common/advances/hbe_inherited_industry_licenses.txt')))
    licenses.update(definitions(read('in_game/common/advances/hbe_advances.txt')))
    all_unlocks = '\n'.join(p.read_text(encoding='utf-8-sig') for p in (mod / 'in_game/common/advances').glob('*.txt'))
    for row in rows:
        stem, licensed, ready, active, off = ids(row)
        values = direct_values(advances[stem])
        check(stem + ' manually researched at age two with native tree parent and no stat grants',
              values == {'age': config['age'], 'starting_technology_level': '99',
                         'content_priority': '830', 'icon': stem, 'requires': row.get('parent', config['parent']),
                         'pure_tooltip_entry': stem + '_effects', 'unlock_production_method': active})
        allow = next(advances[stem][a:b] for key, _, a, b, _ in blocks(advances[stem], 0) if key == 'allow')
        check(stem + ' native parent plus industry qualification',
              licensed+' = yes' in allow and 'is_member_of_international_organization' in allow)
        potential=next(advances[stem][a:b] for key,_,a,b,_ in blocks(advances[stem],0) if key=='potential')
        expected_tags={country['tag'] for country in manifest['countries'] if country['region']==row['region']}
        actual_tags=set(re.findall(r'has_or_had_tag\s*=\s*(\w+)',potential))
        origin_definitions={}
        if 'presentation_v040' in manifest:
            origin_text=(mod/'in_game/common/scripted_triggers/hbe_research_origins.txt').read_text(encoding='utf-8-sig')
            origin_definitions={k:origin_text[a:b] for k,_,a,b,_ in blocks(origin_text,0)}
        check(stem+' is visible only to its originating circle before any research',(('hbe_research_origin_'+row['region']+' = yes' in potential) if origin_definitions else actual_tags==expected_tags) and
              not any(word in potential for word in ('has_advance','has_variable',licensed,'is_member_of_international_organization')))
        check(stem+' actual industry eligibility also enforces origin and its original building advance',
              set(re.findall(r'has_or_had_tag\s*=\s*(\w+)',triggers[licensed]))==expected_tags and
              re.findall(r'has_advance\s*=\s*(\w+)',triggers[licensed])==[row['building_advance']])
        expanded_ready=triggers[ready].replace(licensed+' = yes',triggers[licensed])
        expanded_allow=allow.replace(licensed+' = yes',triggers[licensed])
        all_licenses={row['building_advance'],'hbe_guest_license_'+row['region'],'hbe_inherited_industry_license_'+row['region']}
        for country in manifest['countries']:
            history={country['tag']};native=country['region']==row['region'];label=stem+' '+country['tag']
            check(label+' tree visibility matches originating circle',evaluate(potential,set(),tag_history=history,origin=country['region'],definitions=origin_definitions)==native)
            check(label+' researched industry eligibility matches originating circle',evaluate(triggers[licensed],all_licenses,tag_history=history)==native)
            check(label+' industry qualification without transmission cannot operate sidework',not evaluate(expanded_ready,all_licenses,tag_history=history))
            check(label+' transmission without original industry research cannot operate sidework',not evaluate(expanded_ready,{stem},tag_history=history))
            check(label+' even an already held foreign transmission cannot bypass origin',evaluate(expanded_ready,all_licenses|{stem},tag_history=history)==native)
            check(label+' advance allow rejects every non-originating state',evaluate(expanded_allow,all_licenses,tag_history=history)==native)
        native_tag=next(iter(expected_tags))
        for bits in itertools.product((False,True),repeat=3):
            keys=[row['building_advance'],'hbe_guest_license_'+row['region'],'hbe_inherited_industry_license_'+row['region']]
            held={key for key,selected in zip(keys,bits) if selected}
            check(stem+' only original industry research qualifies '+str(bits),evaluate(triggers[licensed],held,tag_history={native_tag})==bits[0])
        check(stem+' keeps its originating right after forming a new tag',evaluate(potential,set(),tag_history={native_tag,'HQS'},origin=row['region'],definitions=origin_definitions))
        for member in (False,True):
            check(stem+f' advance allow requires HBE membership member={member}',evaluate(expanded_allow,{row['building_advance']},member,tag_history={native_tag})==member)
        inputs = {g: float(direct_values(methods[active])[g]) for g in row['inputs']}
        check(active + ' paid recipe matches planned goods inputs and output',
              inputs == row['inputs'] and direct_values(methods[active])['produced'] == row['goods'] and
              float(direct_values(methods[active])['output']) == row['output'] and f'allow = {{ {ready} = yes }}' in methods[active])
        check(off + ' always available with zero output zero inputs and no upkeep waiver',
              set(direct_values(methods[off])) == {'icon_type', 'icon', 'category'} and not blocks(methods[off], 0) and
              re.search(r'\bunlock_production_method\s*=\s*' + re.escape(off) + r'\b', all_unlocks) is None)
        # The disabled method contributes nothing; a shortage cannot become a free event grant.
        check(active + ' no scripted minting refunds or forced AI selection',
              not any(k in methods[active] for k in ('add_gold', 'set_production', 'no_upkeep', 'debug_max_profit')))
        building_body = original_buildings[row['special_building']]
        current = {key: building_body[a:b] for key, _, a, b, _ in blocks(building_body)}
        basic = current['hbe_' + row['region'] + '_basic_production']
        base_output = float(direct_values(basic)['output'])
        check(stem + ' meets agreed six/eight-level ratio within numeric rounding', abs(row['output'] * row['levels_per_special_building'] - base_output) <= .0005)
        cost = sum(prices[g] * amount for g, amount in inputs.items())
        value = prices[row['goods']] * row['output']
        check(stem + ' reference input value covers 70 to 85 percent of marginal output', .70 <= cost / value <= .85)
        check(stem + ' scarce inputs can make disabling sidework economical', cost * 1.5 > value)
        for carrier in row['carriers']:
            body = definitions(read('in_game/common/building_types/' + row['file']))[carrier]
            slot = next(body[a:b] for k, _, a, b, _ in blocks(body, 0) if k == 'possible_production_methods' and active in body[a:b])
            check(carrier + ' slot offers free off first and only its own active recipe', token_values(slot) == [off, active])
        for language in ('simp_chinese', 'english'):
            localization = read(f'main_menu/localization/{language}/hbe_industry_transmission_l_{language}.yml')
            entries = {match[1]: json.loads(match[2]) for match in re.finditer(r'(?m)^ ([^:]+): (".*")$', localization)}
            required = (stem, stem + '_desc', stem + '_effects', stem + '_cap_tt', licensed + '_tt', stem + '_researched_tt', active, active + '_desc', off, off + '_desc')
            check(language + ' complete names descriptions effects recipes and license tooltips ' + stem, all(k in entries for k in required))
            check(language + ' commodity tooltip reports configured output and inputs ' + stem, f"{row['output']:g}" in entries[stem + '_effects'] and all(f'{value:g}' in entries[stem + '_effects'] for value in inputs.values()))
            check(language + ' new advance explicitly increases national building cap by one ' + stem, ('由两座增至三座' if language == 'simp_chinese' else 'from two to three') in entries[stem + '_effects'])
            check(language + ' recipe tooltip does not imply selecting sidework grants a building slot ' + stem,
                  '全国上限增加一座' not in entries[active + '_desc'] and 'Adds one national' not in entries[active + '_desc'])
            core = {match[1]: json.loads(match[2]) for match in re.finditer(r'(?m)^ ([^:]+): (".*")$', read(f'main_menu/localization/{language}/hbe_l_{language}.yml'))}
            building_desc = core[row['special_building'] + '_desc']
            check(language + ' building description matches two-to-three progression ' + stem,
                  ('最多两座' in building_desc and '三座' in building_desc if language == 'simp_chinese' else 'two institutions' in building_desc and 'three' in building_desc) and
                  not any(old in building_desc for old in ('最多一所', '最多一座', 'one per country', 'only one')))
            check(language + ' original unlocking advance explains initial and upgraded caps ' + stem,
                  ('$' + stem + '$') in core[row['building_advance'] + '_effects'] and ('两座' if language == 'simp_chinese' else 'two') in core[row['building_advance'] + '_effects'])
        cap = triggers[stem + '_below_cap']
        branches = [cap[a:b] for k, _, a, b, _ in blocks(cap) if k == 'AND']
        count_key = 'total_building_levels_including_construction:' + row['special_building']
        check(stem + ' national cap uses current actor and includes construction queues',
              len(branches) == 2 and 'scope:actor' in cap and all(count_key in branch for branch in branches))
        for researched, count in itertools.product((False, True), range(5)):
            held = {stem} if researched else set()
            allowed = any(evaluate(branch, held) and count < int(re.search(re.escape(count_key) + r'\s*<\s*(\d+)', branch)[1]) for branch in branches)
            check(stem + f' national cap researched={researched} completed-plus-queued={count}', allowed == (count < (3 if researched else 2)))
        png = root / f'assets/technology_icons/{stem}.png'
        image = Image.open(png).convert('RGBA')
        a = image.getchannel('A')
        bounds = a.getbbox()
        check(stem + ' sprite has a transparent safe margin at native 256px resolution',
              image.size == (256, 256) and a.getextrema() == (0, 255) and bounds and min(bounds[0], bounds[1], 256 - bounds[2], 256 - bounds[3]) >= 10)
        for folder in ('advance', 'hbe/technology'):
            dds = (mod / f'main_menu/gfx/interface/{folder}/{stem}.dds').read_bytes()
            check(stem + ' ' + folder + ' DDS contains the same complete RGBA sprite',
                  dds[:4] == b'DDS ' and struct.unpack_from('<2I', dds, 12) == (256, 256) and dds[128:] == image.tobytes('raw', 'BGRA'))
    check('four specialty institutions use researched cap guards and retain one level per location',
          all(ids(row)[0] + '_below_cap = yes' in original_buildings[row['special_building']] and
              direct_values(original_buildings[row['special_building']])['max_levels'] == '1' for row in rows))
    original_advances = definitions(read('in_game/common/advances/hbe_advances.txt'))
    check('paper remains second-era gated and the new paper advance is its direct child',
          'age = age_2_renaissance' in original_advances['hbe_tech_northern_shudao_6'] and
          'unlock_building = hbe_gate_registry' in original_advances['hbe_tech_northern_shudao_6'] and
          'unlock_production_method = hbe_northern_shudao_basic_production' in original_advances['hbe_tech_northern_shudao_6'] and
          'hbe_gate_registry' not in original_advances['hbe_tech_northern_shudao_2'] and
          direct_values(advances['hbe_transmission_paper'])['requires'] == 'hbe_tech_northern_shudao_6')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--mod-dir', type=Path)
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    mod = args.mod_dir or args.root / 'mod/holy_bashu_empire'
    manifest = json.loads((mod / 'build_manifest.json').read_text(encoding='utf-8-sig'))
    checks = []
    def check(name, ok):
        checks.append(dict(check=name, passed=bool(ok)))
        assert ok, name
    validate(mod, args.root, Path('D:/SteamLibrary/steamapps/common/Europa Universalis V/game'), manifest, check)
    report = dict(status='passed', checks=checks, check_count=len(checks), scope='Static source checks only; no engine launch or installed-mod changes.')
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'PASS: {len(checks)} industry-transmission checks.')
