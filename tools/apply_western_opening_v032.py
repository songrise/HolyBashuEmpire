"""Native bookmark goodwill and Chengdu trade access for the four western tributaries."""
from build_support import snapshot_files
from pathlib import Path
import json
from apply_western_tributes_v032 import ASSIGNMENTS

SETUP = 'main_menu/setup/1337/97_hbe_western_opening.txt'
BIAS = 'hbe_western_tributary_goodwill'


def apply(out, root=None, game=None):
    out = Path(out)
    def put(relative, text, setup=False):
        p = out / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text.rstrip() + '\n', encoding='utf-8' if setup else 'utf-8-sig', newline='\n')
    pairs = [(a, b) for subject, overlord in ASSIGNMENTS.items() for a, b in ((subject, overlord), (overlord, subject))]
    text = '# Bookmark only: reciprocal goodwill and native Chengdu trade access.\ndiplomacy_manager = {\n'
    text += ''.join(f' opinion = {{ first = {a} second = {b} type = {BIAS} }}\n' for a, b in pairs)
    # This is the documented native relation: +20% attraction of the first country's
    # markets in the second country. It grants access, not forced market membership.
    text += ''.join(f' scripted_oneway = {{ first = BAB second = {tag} type = trade_access }}\n' for tag in ASSIGNMENTS)
    text += '}\n'
    put(SETUP, text, setup=True)
    put('in_game/common/biases/hbe_western_opening.txt',
        '# Native opening goodwill: +100, -4/year, naturally expires after 25 years.\n' + BIAS + ' = { value = 100 max = 100 yearly_decay = 4 }\n')
    for language, label in (('simp_chinese', '川西朝贡旧约'), ('english', 'Western Tributary Goodwill')):
        put(f'main_menu/localization/{language}/hbe_western_opening_l_{language}.yml',
            f'l_{language}:\n {BIAS}: ' + json.dumps(label, ensure_ascii=False))
    report = dict(setup_file=SETUP, assignments=ASSIGNMENTS, directed_opinions=len(pairs), opinion_value=100,
                  yearly_decay=4, trade_access_provider='BAB', trade_access_recipients=list(ASSIGNMENTS),
                  native_relation='trade_access', market_attraction_bonus=.2, forced_market_membership=False,
                  no_runtime_effects=True, note='Market assignment remains native and is checked after bookmark initialization.')
    p = out / 'build_manifest.json'
    m = json.loads(p.read_text(encoding='utf-8-sig'))
    m['western_opening_v032'] = report
    m['files'] = snapshot_files(out)
    newline = '\r\n' if b'\r\n' in p.read_bytes() else '\n'
    p.write_text(json.dumps(m, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline=newline)
    return report
