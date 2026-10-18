"""Targeted setup checks; these do not launch EU5 or simulate a campaign."""
from pathlib import Path
import re
from pdxscript import blocks, tokens
from apply_western_tributes_v032 import ASSIGNMENTS, RELATIVE, dependencies, patch


def validate(out, game, manifest, check):
    out, game = Path(out), Path(game)
    text = (out/RELATIVE).read_text(encoding='utf-8-sig')
    native = (game/RELATIVE).read_text(encoding='utf-8-sig')
    entries = dependencies(text)
    native_entries = dependencies(native)
    check('setup has no BOM and balanced native syntax',
          not (out/RELATIVE).read_bytes().startswith(b'\xef\xbb\xbf') and bool(blocks(text)))
    check('only the four approved diplomacy entries change', text == patch(native))
    for tag, overlord in ASSIGNMENTS.items():
        found = [fields for fields, _, _ in entries if fields['second'] == tag]
        check('one tributary overlord for '+tag, found == [{'first': overlord, 'second': tag, 'subject_type': 'tributary'}])
    untouched = lambda rows: [fields for fields, _, _ in rows if fields['second'] not in ASSIGNMENTS]
    check('all other native dependencies including Liang remain unchanged', untouched(entries) == untouched(native_entries))
    check('Liang remains a Yuan vassal',
          [fields for fields, _, _ in entries if fields['second'] == 'LNG'] ==
          [{'first': 'CHI', 'second': 'LNG', 'subject_type': 'vassal'}])
    check('all 63 original Liang subject registrations remain',
          len([fields for fields, _, _ in entries if fields['first'] == 'LNG']) == 63)
    parent = {fields['second']: fields['first'] for fields, _, _ in entries}
    no_cycles = True
    for tag in ASSIGNMENTS:
        seen = set()
        while tag in parent:
            if tag in seen:
                no_cycles = False
                break
            seen.add(tag)
            tag = parent[tag]
    check('new subject chains have no cycles', no_cycles)
    setup = (out/'main_menu/setup/1337/10_countries.txt').read_text(encoding='utf-8-sig')
    lands = {}
    for tag, _, begin, end, _ in blocks(setup, 2):
        if tag not in set(ASSIGNMENTS) | set(ASSIGNMENTS.values()):
            continue
        body = setup[begin:end]
        lands[tag] = []
        for name, _, x, y, _ in blocks(body, 0):
            if name.startswith('own_'):
                lands[tag].extend(t.value for t in tokens(body[x:y]) if t.value not in ('{', '}', '='))
    check('all four tributaries and three overlords have starting land',
          set(lands) == set(ASSIGNMENTS) | set(ASSIGNMENTS.values()) and all(lands.values()))
    check('exactly 17 tributary locations without land transfer',
          {tag: len(lands[tag]) for tag in ASSIGNMENTS} == {'GYE': 4, 'HOR': 5, 'NYA': 2, 'CKL': 6})
    organizations = (out/'main_menu/setup/1337/99_hbe_organizations.txt').read_text(encoding='utf-8-sig')
    members = re.findall(r'members\s*=\s*\{([^}]+)\}', organizations)
    check('western tributaries are not added to HBE or its circles',
          not set(ASSIGNMENTS) & set(' '.join(members).split()))
    check('native tributary type is reused without an override',
          not (out/'in_game/common/subject_types/tributary.txt').exists() and
          (game/'in_game/common/subject_types/tributary.txt').is_file())
    check('new setup generation is idempotent', patch(text) == text)
    check('manifest records the approved assignments', manifest['western_tributes_v032']['assignments'] == ASSIGNMENTS)
