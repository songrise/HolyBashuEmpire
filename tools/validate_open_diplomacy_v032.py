"""Regression checks for native diplomacy and 72 directed starting opinions."""
import re
from pathlib import Path
from pdxscript import blocks, tokens


def validate(out, manifest, check):
    out = Path(out)
    read = lambda rel: (out/rel).read_text(encoding='utf-8-sig')
    for filename in ('hbe_empire.txt', 'hbe_feast_parties.txt'):
        text = read('in_game/common/international_organizations/'+filename)
        check('no HBE declaration veto '+filename,
              not any(name == 'can_declare_war' for name, *_ in blocks(text)))
    rule = read('in_game/common/join_war_rules/hbe_isolation.txt')
    check('compatibility join rule never disables participation',
          [t.value for t in tokens(rule)] ==
          ['hbe_isolation_join_rule', '=', '{', 'join_war_disabled_trigger', '=', '{', 'always', '=', 'no', '}', '}'])
    check('obsolete border predicates removed',
          'hbe_war_is_internal' not in read('in_game/common/scripted_triggers/hbe_triggers.txt') and
          'hbe_common_defense_join_allowed' not in read('in_game/common/scripted_triggers/hbe_common_defense.txt'))
    setup = read('main_menu/setup/1337/98_hbe_yuan_opinions.txt')
    entries = re.findall(r'opinion\s*=\s*\{\s*first\s*=\s*(\w+)\s+second\s*=\s*(\w+)\s+type\s*=\s*(\w+)\s*\}', setup)
    tags = {c['tag'] for c in manifest['countries']}
    expected = {(a, b, 'hbe_yuan_opening_goodwill') for tag in tags for a, b in [('CHI', tag), (tag, 'CHI')]}
    check('exactly 72 unique reciprocal Yuan-prince opinions', len(entries) == len(set(entries)) == 72 and set(entries) == expected)
    check('Yuan opening bias uses native +100 and 25-year decay',
          [t.value for t in tokens(read('in_game/common/biases/hbe_yuan_opening.txt'))] ==
          ['hbe_yuan_opening_goodwill', '=', '{', 'value', '=', '100', 'max', '=', '100', 'yearly_decay', '=', '4', '}'])
    other_scripts = '\n'.join(p.read_text(encoding='utf-8-sig') for p in (out/'in_game').rglob('*.txt') if p.name != 'hbe_yuan_opening.txt')
    check('opening goodwill cannot be reapplied by pulses or save loads', 'hbe_yuan_opening_goodwill' not in other_scripts)
    for lang in ('simp_chinese', 'english'):
        check('localized opening opinion '+lang, ' hbe_yuan_opening_goodwill:' in read(f'main_menu/localization/{lang}/hbe_open_diplomacy_l_{lang}.yml'))
    io = read('in_game/common/international_organizations/hbe_empire.txt')
    check('imperial defense stays conditional and foreign offensives not automatic',
          'has_variable = hbe_common_defense_active' in io and io.count('join_offensive_wars_always = { always = no }') == 8)
