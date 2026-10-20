"""Bookmark land redistribution after population allocation; residents are untouched."""
from pathlib import Path
import csv, json
from pdxscript import blocks, tokens, apply_edits
from build_support import sha256_file, snapshot_files, write_preserving_format

SETUP = 'main_menu/setup/1337/10_countries.txt'
POPS = 'main_menu/setup/1337/06_pops.txt'
CONFIG = 'data/opening_territory.json'


def transfer_lists(territories, transfers):
    result = {tag: list(locations) for tag, locations in territories.items()}
    for row in transfers:
        location, source, target = row['location'], row['from'], row['to']
        owners = [tag for tag, locations in result.items() if location in locations]
        assert owners in ([source], [target]), (location, owners)
        if owners == [source]:
            result[source].remove(location)
            result[target].append(location)
    return result


def apply(out, root, game=None, update_catalogues=True):
    out, root = Path(out), Path(root)
    transfers = json.loads((root / CONFIG).read_text(encoding='utf-8'))['transfers']
    mp = out / 'build_manifest.json'
    manifest = json.loads(mp.read_text(encoding='utf-8-sig'))
    territories = {c['tag']: list(c['locations']) for c in manifest['countries']}
    expected = transfer_lists(territories, transfers)
    before_pop = sha256_file(out / POPS)
    text = (out / SETUP).read_text(encoding='utf-8-sig')
    affected = {row[side] for row in transfers for side in ('from', 'to')}
    edits, seen = [], set()
    for tag, _, begin, end, _ in blocks(text, 2):
        if tag not in affected:
            continue
        body = text[begin:end]
        core_blocks = [(a, b) for key, _, a, b, _ in blocks(body, 0) if key == 'own_control_core']
        assert len(core_blocks) == 1, tag
        a, b = core_blocks[0]
        actual = [t.value for t in tokens(body[a:b])]
        assert actual == territories[tag], (tag, actual, territories[tag])
        if actual != expected[tag]:
            edits.append((begin + a, begin + b, ' ' + ' '.join(expected[tag]) + ' '))
        seen.add(tag)
    assert seen == affected
    write_preserving_format(out / SETUP, apply_edits(text, edits))
    for country in manifest['countries']:
        country['locations'] = expected[country['tag']]
        assert country['capital'] in country['locations']
    assert sha256_file(out / POPS) == before_pop
    report = {
        'transfers': transfers, 'bookmark_only': True, 'runtime_transfer_events': False,
        'ownership_control_and_core_transferred': True, 'residents_unchanged': True,
        'population_file_sha256': before_pop, 'population_allocation_before_transfers': True,
        'country_circles_and_geographical_circles_unchanged': True,
        'country_location_counts': {tag: len(expected[tag]) for tag in sorted(affected)},
    }
    manifest['opening_territory'] = report
    manifest['files'] = snapshot_files(out)
    write_preserving_format(mp, json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    if update_catalogues:
        owners = {location: tag for tag, locations in expected.items() for location in locations}
        for filename in ('countries_v001.csv', 'locations_v001.csv'):
            path = root / 'data' / filename
            with path.open(encoding='utf-8-sig', newline='') as stream:
                reader = csv.DictReader(stream)
                fields, rows = reader.fieldnames, list(reader)
            for row in rows:
                if filename == 'countries_v001.csv':
                    row['locations'] = str(len(expected[row['tag']]))
                else:
                    row['country'] = owners[row['location']]
            with path.open('w', encoding='utf-8-sig', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n')
                writer.writeheader(); writer.writerows(rows)
    return report


def validate(out, root, manifest, check):
    out, root = Path(out), Path(root)
    wanted = json.loads((root / CONFIG).read_text(encoding='utf-8'))['transfers']
    report = manifest['opening_territory']
    check('approved bookmark territory transfers are recorded', report['transfers'] == wanted and report['bookmark_only'] and not report['runtime_transfer_events'])
    territories = {c['tag']: c['locations'] for c in manifest['countries']}
    for row in wanted:
        check(row['location']+' belongs exclusively to '+row['to'], [tag for tag, places in territories.items() if row['location'] in places] == [row['to']])
    check('Jianzhou Meizhou and Jiading have four five seven locations', {tag: len(territories[tag]) for tag in ('BBQ', 'BAL', 'BAO')} == {'BBQ': 4, 'BAL': 5, 'BAO': 7})
    check('territory transfers preserve the complete population file', sha256_file(out / POPS) == report['population_file_sha256'])
    check('territory catalogue patch is idempotent', transfer_lists(territories, wanted) == territories)
    # Geography is deliberately not regenerated from the new country borders.
    text = (out / 'in_game/common/scripted_geography/hbe_geography.txt').read_text(encoding='utf-8-sig')
    bodies = {key: text[a:b] for key, _, a, b, _ in blocks(text, 0)}
    check('transferred places retain original geographical circle', all(row['location'] in bodies['hbe_geo_central_hills'] for row in wanted))
