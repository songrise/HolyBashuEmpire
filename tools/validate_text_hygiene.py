"""Reject localization that still points at retired local-affairs resources."""
import re

RETIRED = ('water', 'salt', 'river', 'roads', 'grain', 'tea', 'valleys')
_ALT = '|'.join(RETIRED)
LINK = re.compile(r"\[Concept\('hbe_term_(?:" + _ALT + r")'")
ICON = re.compile(r"@hbe_(?:" + _ALT + r")!")
CONCEPT = re.compile(r"^\s*game_concept_hbe_term_(?:" + _ALT + r"):")
OLD_RULE = '开局20，上限100'


def scan_text(text):
    hits = []
    for no, line in enumerate(text.splitlines(), 1):
        if LINK.search(line) or ICON.search(line) or CONCEPT.match(line):
            hits.append((no, line.strip()[:90]))
        elif OLD_RULE in line and 'game_concept' in line:
            hits.append((no, line.strip()[:90]))
    return hits


def validate(m, root, game, manifest, check):
    hits = []
    for path in sorted((m / 'main_menu/localization').rglob('hbe*.yml')):
        for no, line in scan_text(path.read_text(encoding='utf-8-sig')):
            hits.append(f'{path.name}:{no}: {line}')
    for row in hits[:10]:
        print('  text-hygiene: ' + row)
    check('localization no longer links or defines retired local-affairs resources', not hits)
