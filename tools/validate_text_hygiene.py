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
    keys = {}
    duplicates = []
    for path in sorted((m / 'main_menu/localization').rglob('hbe*.yml')):
        text = path.read_text(encoding='utf-8-sig')
        language = path.relative_to(m / 'main_menu/localization').parts[0]
        for key in re.findall(r'^\s+([A-Za-z0-9_.]+):(?:\d+)?\s+"', text, re.M):
            identity = (language, key)
            if identity in keys:
                duplicates.append(f'{language}:{key}: {keys[identity]} / {path.name}')
            keys[identity] = path.name
        for no, line in scan_text(text):
            hits.append(f'{path.name}:{no}: {line}')
    for row in hits[:10]:
        print('  text-hygiene: ' + row)
    check('localization no longer links or defines retired local-affairs resources', not hits)
    for row in duplicates[:10]:
        print('  duplicate-localization: ' + row)
    check('mod localization keys are unique across files within each language', not duplicates)
    from normalize_concept_labels import validate as validate_concept_labels
    validate_concept_labels(m,check)
