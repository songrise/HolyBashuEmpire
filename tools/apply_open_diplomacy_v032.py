"""Remove HBE's military border gates and seed native Yuan starting opinions."""
from pathlib import Path
import hashlib
import json
import re
from pdxscript import blocks, apply_edits

RULE = '''hbe_isolation_join_rule = {
 # Compatibility registration only; no country is barred from joining by HBE.
 join_war_disabled_trigger = { always = no }
}
'''
BIAS = '''# Same scale as vanilla's extreme_bonus example: +100, -4/year, 25 years.
hbe_yuan_opening_goodwill = {
 value = 100
 max = 100
 yearly_decay = 4
}
'''
GUIDE_ZH = ('会盟依共同盐粮交割维护诸府自治。自治盟约不再限制帝国与域外之间的宣战和参战；'
            '宣战理由、停战、盟约和其他原版条件仍适用。\n\n'
            '七圈保留本圈防御协作；七圈共防获准后，符合条件的帝国成员共同应对外部进攻，'
            '不自动参加成员的对外进攻。开局元与三十六府互获100点「元蜀旧好」，每年衰减4点，25年归零。')
GUIDE_EN = ('The assembly maintains local autonomy through common salt and grain obligations. '
            'Its charter no longer bars declarations of war or war participation across the imperial boundary. '
            'Normal casus belli, truces, alliances and other vanilla requirements still apply.\n\n'
            'Circle defense remains in place. Once approved, the Seven Circles treaty brings eligible members '
            'into defense against outside attacks, without automatically joining foreign offensives. '
            'At the 1337 start, Yuan and each of the thirty-six principalities receive mutual +100 Yuan-Shu goodwill, '
            'decaying by 4 each year to zero after 25 years.')


def remove_definition(text, key):
    return apply_edits(text, [(start, end, '') for name, start, _, _, end in blocks(text, 0) if name == key])


def apply(out, root=None, game=None):
    out = Path(out)
    manifest_path = out/'build_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf8'))
    touched = []

    def put(rel, value, setup=False):
        target = out/rel
        data = value.encode('utf8' if setup else 'utf-8-sig')
        if not target.exists() or target.read_bytes() != data:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            touched.append(rel)

    removed = 0
    for rel in ('in_game/common/international_organizations/hbe_empire.txt',
                'in_game/common/international_organizations/hbe_feast_parties.txt'):
        text = (out/rel).read_text(encoding='utf-8-sig')
        edits = []
        for name, start, body, close, end in blocks(text):
            if name != 'can_declare_war':
                continue
            assert 'hbe_war_is_internal = yes' in text[body:close], 'Review unexpected HBE declaration rule'
            edits.append((start, end, ''))
        removed += len(edits)
        put(rel, apply_edits(text, edits))
    assert removed in (0, 10), removed
    put('in_game/common/join_war_rules/hbe_isolation.txt', RULE)
    for rel, key in (
        ('in_game/common/scripted_triggers/hbe_triggers.txt', 'hbe_war_is_internal'),
        ('in_game/common/scripted_triggers/hbe_common_defense.txt', 'hbe_common_defense_join_allowed'),
    ):
        put(rel, remove_definition((out/rel).read_text(encoding='utf-8-sig'), key))

    tags = [country['tag'] for country in manifest['countries']]
    assert len(tags) == len(set(tags)) == 36 and 'CHI' not in tags
    # Native 1337 setup uses CHI for Yuan; YUA is its fallback tag.
    if game:
        native = (Path(game)/'main_menu/setup/1337/10_countries.txt').read_text(encoding='utf-8-sig')
        assert re.search(r'CHI\s*=\s*\{\s*#Yuán', native)
    pairs = [(a, b) for tag in tags for a, b in [('CHI', tag), (tag, 'CHI')]]
    setup = '# New campaigns only: native starting opinions; never refreshed on monthly pulses or save loads.\n'
    setup += 'diplomacy_manager = {\n'
    setup += ''.join(f' opinion = {{ first = {a} second = {b} type = hbe_yuan_opening_goodwill }}\n' for a, b in pairs)
    setup += '}\n'
    put('main_menu/setup/1337/98_hbe_yuan_opinions.txt', setup, setup=True)
    put('in_game/common/biases/hbe_yuan_opening.txt', BIAS)

    for lang, label, guide in [('simp_chinese', '元蜀旧好', GUIDE_ZH),
                               ('english', 'Yuan-Shu goodwill', GUIDE_EN)]:
        for path in (out/f'main_menu/localization/{lang}').rglob('*.yml'):
            text = path.read_text(encoding='utf-8-sig')
            original = text
            text = text.replace('共同防卫不改变帝国的外围隔离协议。', '对外宣战与参战仍须满足通常外交条件。')
            text = text.replace('会盟敕书维护外部隔离，广元仍需经营境内的通行与守备。',
                                '会盟敕书维护诸府自治，广元仍需经营境内的通行与守备。')
            values = {
                'game_concept_hbe_term_isolation_desc': guide,
                'hbe_isolation_tt': ('对外宣战与参战遵循通常外交条件。' if lang == 'simp_chinese'
                                     else 'Foreign declarations and war participation follow normal diplomatic requirements.'),
            }
            for key, value in values.items():
                replacement = ' '+key+': '+json.dumps(value, ensure_ascii=False)
                text = re.sub(r'^ '+re.escape(key)+r':.*$', lambda _: replacement, text, flags=re.M)
            if text != original:
                put(path.relative_to(out).as_posix(), text)
        put(f'main_menu/localization/{lang}/hbe_open_diplomacy_l_{lang}.yml',
            f'l_{lang}:\n hbe_yuan_opening_goodwill: '+json.dumps(label, ensure_ascii=False)+'\n')

    report = dict(version='0.3.2', local_only=True, declaration_border_gate=False,
                  joining_border_gate=False, disabled_rule_retained_for_compatibility=True,
                  removed_declaration_rules=10, yuan_tag='CHI', principalities=tags,
                  directed_starting_opinions=len(pairs), opinion_value=100, yearly_decay=4,
                  natural_decay_years=25, scope='1337 new campaigns only; no on-load or monthly reapplication',
                  common_defense_preserved=True)
    manifest['open_diplomacy_v032'] = report
    manifest['files'] = {p.relative_to(out).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in out.rglob('*') if p.is_file() and p.name != 'build_manifest.json'}
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    return dict(report, touched_files=touched)


if __name__ == '__main__':
    import sys
    print(json.dumps(apply(Path(sys.argv[1]), game=Path(sys.argv[2]) if len(sys.argv)>2 else None), ensure_ascii=False))
