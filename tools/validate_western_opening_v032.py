"""Native setup checks for exact population deltas, eight opinions and four trade-access links."""
from decimal import Decimal
from pathlib import Path
import re
from pdxscript import blocks, tokens
from build_opening_population import COUNTRY_DELTAS, FIXED_POPULATIONS, owned_locations, population
from apply_western_tributes_v032 import ASSIGNMENTS
from apply_western_opening_v032 import SETUP, BIAS


def validate(out, game, manifest, check):
    if 'western_opening_v032' not in manifest:
        return
    out, game = map(Path, (out, game))
    wanted = set(COUNTRY_DELTAS) | set(FIXED_POPULATIONS)
    places = owned_locations((out / 'main_menu/setup/1337/10_countries.txt').read_text(encoding='utf-8-sig'), wanted)
    # The requested population deltas were allocated before later border changes.
    # Reconstruct that allocation territory so a land transfer does not deduct people again.
    for row in manifest.get('opening_territory', {}).get('transfers', []):
        if row['to'] in places:
            places[row['to']].remove(row['location'])
        if row['from'] in places:
            places[row['from']].append(row['location'])
    owner = {location: tag for tag, locations in places.items() for location in locations}
    tables = []
    for path in (game / 'main_menu/setup/1337/06_pops.txt', out / 'main_menu/setup/1337/06_pops.txt'):
        text = path.read_text(encoding='utf-8-sig')
        _, _, a, z, _ = blocks(text, 0)[0]
        body = text[a:z]
        tables.append({key: body[a:z] for key, _, a, z, _ in blocks(body, 0)})
    before, after = tables
    check('population setup preserves every native location', before.keys() == after.keys())
    for tag, locations in places.items():
        old = sum((population(before[l]) for l in locations), Decimal(0))
        new = sum((population(after[l]) for l in locations), Decimal(0))
        target = Decimal(FIXED_POPULATIONS[tag]) if tag in FIXED_POPULATIONS else old + Decimal(COUNTRY_DELTAS[tag])
        check(tag + ' exact requested bookmark population', new == target)
        erase = lambda text: re.sub(r'\bsize\s*=\s*[\d.]+', 'size = POPULATION_SIZE', text)
        check(tag + ' preserves pop group culture religion type and all non-size fields',
              all([t.value for t in tokens(erase(before[l]))] == [t.value for t in tokens(erase(after[l]))] for l in locations))
        check(tag + ' retains positive populations', all(Decimal(v) > 0 for l in locations for v in re.findall(r'\bsize\s*=\s*([\d.]+)', after[l])))
    check('unrelated locations preserve their complete native populations',
          all([t.value for t in tokens(before[l])] == [t.value for t in tokens(after[l])] for l in before if l not in owner))
    setup = (out / SETUP).read_text(encoding='utf-8-sig')
    blocks(setup)
    check('new bookmark diplomacy has no BOM', not (out / SETUP).read_bytes().startswith(b'\xef\xbb\xbf'))
    actual = re.findall(r'opinion\s*=\s*\{ first = (\w+) second = (\w+) type = (\w+) \}', setup)
    expected = {(a, b, BIAS) for tag, lord in ASSIGNMENTS.items() for a, b in ((tag, lord), (lord, tag))}
    check('eight unique reciprocal subject-overlord opinions', len(actual) == len(set(actual)) == 8 and set(actual) == expected)
    relations = re.findall(r'scripted_oneway\s*=\s*\{ first = (\w+) second = (\w+) type = (\w+) \}', setup)
    check('Chengdu grants native trade access to exactly four tributaries', set(relations) == {('BAB', tag, 'trade_access') for tag in ASSIGNMENTS} and len(relations) == 4)
    bias = (out / 'in_game/common/biases/hbe_western_opening.txt').read_text(encoding='utf-8-sig')
    check('opening goodwill uses +100 with normal native decay', all(term in bias for term in ('value = 100', 'max = 100', 'yearly_decay = 4')))
    check('no override to native trade-access or tributary rules', not (out / 'in_game/common/scripted_relations/trade_access.txt').exists() and not (out / 'in_game/common/subject_types/tributary.txt').exists())
    check('population changes are bookmark data and not repeated startup effects',
          manifest['opening_population']['requested_deltas_people'] == {tag: value * 1000 for tag, value in COUNTRY_DELTAS.items()})
    for language in ('simp_chinese', 'english'):
        check(language + ' western goodwill localized', f' {BIAS}:' in (out / f'main_menu/localization/{language}/hbe_western_opening_l_{language}.yml').read_text(encoding='utf-8-sig'))
