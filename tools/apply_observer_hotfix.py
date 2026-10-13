"""Targeted corrections from the 20-year observer; never rebuild setup or art.

Run after normal builders/localization when rebuilding. Existing era-two gates
and the user's 0.8x technology balance remain intact. Only starter production,
AI priorities, native registration and diagnostic text are changed.
"""
import hashlib
import json
import re
import shutil
from pathlib import Path
from pdxscript import blocks, apply_edits

ROOT = Path(__file__).resolve().parents[1]
OLD = 'hbe_tech_central_hills_8'
NEW = 'hbe_tech_central_hills_witness_8'
PRODUCERS = [
    ('chengdu_plain', 'hbe_brocade_school', 'hbe_shu_embroidery', .60, 2, '乡坊绣作', 'Workshop Embroidery'),
    ('southern_salt_wine', 'hbe_salt_office', 'hbe_well_salt', .90, 1, '小灶井盐', 'Small Salt Furnaces'),
    ('northern_shudao', 'hbe_gate_registry', 'hbe_shu_paper', .625, 6, '乡坊抄纸', 'Local Papermaking'),
    ('western_tea_horse', 'hbe_tea_exchange', 'hbe_border_tea', .60, 1, '边市茶饼', 'Frontier Tea Cakes'),
]


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + '\n', encoding='utf-8-sig')


def apply(out, root=ROOT):
    changed = set()
    skip = {'hbe_observer_compatibility.txt', 'hbe_observer_sync.txt'}
    # The engine derives an advance description key from its identifier. Rename
    # the active definition instead of overriding REGENCY_NO_REGENT globally.
    for p in out.rglob('*'):
        if p.suffix not in ('.txt', '.yml') or p.name in skip or p.name.startswith('hbe_observer_hotfix_l_'):
            continue
        old = p.read_text(encoding='utf-8-sig')
        new = re.sub(r'\b' + OLD + r'(?=\b|_)', NEW, old)
        if old != new:
            write(p, new.rstrip('\n'))
            changed.add(p.relative_to(out).as_posix())
    # The old identifier must not remain an advance: the engine requests its
    # colliding *_desc even when its potential is false. Already-earned monthly
    # completion flags provide the compatibility bridge without that definition.
    alias = out / 'in_game/common/advances/hbe_observer_compatibility.txt'
    removed = [alias.relative_to(out).as_posix()]
    if alias.exists(): alias.unlink()
    sync = out / 'in_game/common/scripted_effects/hbe_observer_sync.txt'
    write(sync, f'''hbe_observer_compatibility_sync = {{
 if = {{ limit = {{ has_variable = {OLD} NOT = {{ has_variable = {NEW} }} }}
  set_variable = {OLD}
  set_variable = {NEW}
  if = {{ limit = {{ NOT = {{ has_advance = {NEW} }} }} research_advance = advance_type:{NEW} }}
 }}
}}''')
    changed.add(sync.relative_to(out).as_posix())
    p = out / 'in_game/common/scripted_effects/hbe_native_content_effects.txt'
    text = p.read_text(encoding='utf-8-sig')
    text = re.sub(r'\n?\s*hbe_observer_compatibility_sync = yes\s*\n?', '\n', text)
    start = re.search(r'hbe_sync_native_research\s*=\s*\{', text)
    assert start
    text = text[:start.end()] + '\n hbe_observer_compatibility_sync = yes\n' + text[start.end():]
    write(p, text.rstrip('\n')); changed.add(p.relative_to(out).as_posix())
    # The icon name changes with its active technology identifier. Reuse its art.
    for p in list((out / 'main_menu/gfx').rglob('*' + OLD + '*')):
        if p.is_file():
            q = p.with_name(p.name.replace(OLD, NEW))
            shutil.copyfile(p, q); changed.add(q.relative_to(out).as_posix())

    # Goods require these native types even when their default value is zero.
    path = out / 'main_menu/common/modifier_type_definitions/hbe_observer_goods_types.txt'
    required = [
        ('{g}_impacts_inflation','percent','country','铸币通胀影响','Minting Inflation Impact'),
        ('{g}_used_for_minting','boolean','country','可用于铸币','May Be Used for Minting'),
        ('ban_exports_of_{g}','boolean','country','禁止出口','Exports Banned'),
        ('ban_imports_of_{g}','boolean','country','禁止进口','Imports Banned'),
        ('can_extract_{g}','boolean','country','允许采集','Extraction Allowed'),
        ('global_{g}_pop_demand','percent','country','人口需求','Population Demand'),
        ('local_{g}_establishment_speed','percent','location','本地开设速度','Local Establishment Speed'),
        ('global_{g}_establishment_speed','percent','country','开设速度','Establishment Speed'),
    ]
    write(path, '\n'.join(f'{pattern.format(g=good)} = {{ {kind} = yes game_data = {{ category = {scope} }} }}' for _, _, good, _, _, _, _ in PRODUCERS for pattern, kind, scope, _, _ in required))
    changed.add(path.relative_to(out).as_posix())

    # Keep all existing timings/options intact; supply missing metadata only.
    events_fixed = []
    for p in (out / 'in_game/events').glob('hbe*events.txt'):
        text = p.read_text(encoding='utf-8-sig'); edits = []
        for name, _, s, e, _ in blocks(text, 0):
            if not re.fullmatch(r'hbe\w*\.\d+', name): continue
            body = text[s:e]; added = []
            if not re.search(r'\boutcome\s*=', body): added.append('outcome = neutral')
            if not re.search(r'\btitle\s*=', body): added.append('title = ' + name + '.title')
            if added:
                edits.append((s, s, '\n ' + ' '.join(added) + '\n')); events_fixed.append(name)
        if edits:
            write(p, apply_edits(text, edits).rstrip('\n')); changed.add(p.relative_to(out).as_posix())

    # First-era institutions can begin a small real specialty industry. The era-
    # two recipe keeps its existing date/advance gates and doubles this output.
    buildings_path = out / 'in_game/common/building_types/hbe_civic_buildings.txt'
    buildings_text = buildings_path.read_text(encoding='utf-8-sig'); edits = []
    fallback_unlocks = {}
    for region, building, good, amount, tier, _, _ in PRODUCERS:
        item = next(b for b in blocks(buildings_text, 0) if b[0] == building)
        body = buildings_text[item[2]:item[3]]
        parts = [b for b in blocks(body, 0) if b[0] == 'unique_production_methods']
        methods = []
        for part in parts:
            content = body[part[2]:part[3]]
            methods.extend((name, content[s:e]) for name, _, s, e, _ in blocks(content, 0))
        basic = f'hbe_{region}_basic_production'
        fallback = f'hbe_{region}_ordinary_production'
        original = next(content for name, content in methods if name == basic)
        if not any(name == fallback for name, _ in methods):
            methods.append((fallback, original))
        updated = []
        for name, content in methods:
            if name == basic:
                content = re.sub(r'\bicon\s*=\s*\w+', 'icon = ' + good, content)
                content = re.sub(r'\bproduced\s*=\s*\w+', 'produced = ' + good, content)
                content = re.sub(r'\boutput\s*=\s*[\d.]+', f'output = {amount:g}', content)
                if region == 'western_tea_horse':
                    # The ordinary method processes livestock into leather.
                    # Tea cakes must instead consume real tea, never livestock.
                    content = re.sub(r'\b(?:livestock|tea)\s*=\s*[\d.]+', '', content)
                    content += '\n tea = 0.45\n'
            updated.append(name + ' = {' + content + '}')
        body = apply_edits(body, [(part[1], part[4], '' if n else 'unique_production_methods = {\n' + '\n'.join(updated) + '\n}') for n, part in enumerate(parts)])
        body = re.sub(r'ai_construct_weight\s*=\s*\{[^{}]*\}', 'ai_construct_weight = { value = 4 }', body)
        edits.append((item[2], item[3], body))
        fallback_unlocks[f'hbe_tech_{region}_{tier}'] = fallback
    write(buildings_path, apply_edits(buildings_text, edits).rstrip('\n')); changed.add(buildings_path.relative_to(out).as_posix())

    p = out / 'in_game/common/advances/hbe_advances.txt'
    text = p.read_text(encoding='utf-8-sig'); edits = []
    for name, _, s, e, _ in blocks(text, 0):
        if not name.startswith('hbe_tech_'): continue
        body = text[s:e]
        if name == 'hbe_tech_common_1' or re.search(r'hbe_tech_(?!common)\w+_[12]$', name) or name in fallback_unlocks:
            body = re.sub(r'\bai_weight\s*=\s*\{[^{}]*\}', '', body)
            body += '\n    ai_weight = { add = 20 }\n'
        for fallback in fallback_unlocks.values():
            body = re.sub(r'\n\s*unlock_production_method = ' + fallback + r'\b', '', body)
        if name in fallback_unlocks:
            body += f'\n    unlock_production_method = {fallback_unlocks[name]}\n'
        if body != text[s:e]: edits.append((s, e, body))
    write(p, apply_edits(text, edits).rstrip('\n')); changed.add(p.relative_to(out).as_posix())

    p = out / 'in_game/common/goods/hbe_special_goods.txt'
    text = p.read_text(encoding='utf-8-sig')
    part = next(b for b in blocks(text,0) if b[0] == 'hbe_border_tea')
    body = text[part[2]:part[3]]
    demand = next(b for b in blocks(body,0) if b[0] == 'demand_add')
    demand_body = re.sub(r'\bpeasants\s*=\s*[\d.]+', '', body[demand[2]:demand[3]])
    body = apply_edits(body, [(demand[2],demand[3],demand_body+' peasants = 0.025 ')])
    write(p, apply_edits(text,[(part[2],part[3],body)]).rstrip('\n'))
    changed.add(p.relative_to(out).as_posix())

    # Native per-target war scoring, not a world-wide pacifism modifier. The
    # multiplier is a score adjustment, NOT a guaranteed probability reduction.
    p = out / 'in_game/common/ai_scripted_expansion_score/hbe_external_caution.txt'
    write(p, '''hbe_external_caution = {
 attacker_potential = { NOT = { is_member_of_international_organization = international_organization:hbe_empire } }
 target_trigger = { is_member_of_international_organization = international_organization:hbe_empire }
 multiplier = { value = 0.90 }
}'''); changed.add(p.relative_to(out).as_posix())

    cn = {
        'hbe_party_points_desc': '本派成员在本轮积累的贡献总和。',
        'hbe_round_desc': '当前大开席的届次。',
        'hbe_round_month_desc': '本届已经经过的月数。',
        'hbe_feast_total_desc': '本届共同事业已经积累的贡献。',
        'hbe_completed_projects_desc': '历届已经完成的共同事业数。',
        'hbe_member_party_pool_desc': '本府所属派系本轮可分配的金币池。',
        'hbe_member_party_weight_desc': '本派成员按贡献对数计算的分红权重总和。',
        'hbe_member_dividend_weight_desc': '本府按贡献对数计算的分红权重。',
        'hbe_feast_last_dividend_desc': '本府最近一次实际获得的金币分红。',
        'hbe_feast_last_prestige_desc': '本府最近一次实际获得的威望分红。',
        'hbe_member_imperial_bonus_desc': '本府本轮计入分红池的额外金币奖励。',
        'hbe_opening_family.1.title': '开局家族与盟约登记',
        OLD: '乡社公信（旧存档记录）',
    }
    en = {
        'hbe_party_points_desc': 'The total contribution accumulated by this party during the current gathering.',
        'hbe_round_desc': 'The number of the current gathering.',
        'hbe_round_month_desc': 'Months elapsed during the current gathering.',
        'hbe_feast_total_desc': 'Contribution accumulated towards the current common project.',
        'hbe_completed_projects_desc': 'Common projects completed at earlier gatherings.',
        'hbe_member_party_pool_desc': 'The gold pool available to this country\'s party.',
        'hbe_member_party_weight_desc': 'The sum of logarithmic contribution weights within the party.',
        'hbe_member_dividend_weight_desc': 'This country\'s logarithmic contribution weight.',
        'hbe_feast_last_dividend_desc': 'Gold actually received at the most recent distribution.',
        'hbe_feast_last_prestige_desc': 'Prestige actually received at the most recent distribution.',
        'hbe_member_imperial_bonus_desc': 'Additional gold rewards contributed to this country\'s party pool.',
        'hbe_opening_family.1.title': 'Opening Family and Pact Registration',
        OLD: 'Public Credit (Legacy Save Record)',
    }
    # The engine generates these message keys from the three situation actions.
    # They were absent from the earlier audit because the hbe token follows an
    # underscore. Supply every view/suffix, without relying on a fallback label.
    for action, title, explanation, etitle, eexplanation in [
        ('hbe_feast_fund_action','为会盟出资','一笔出资记入本届会盟，由本派与共同事业使用。','Contribution to the Gathering','A contribution has been recorded for the current gathering and its common project.'),
        ('hbe_feast_common_action','支持共建派','本府转而支持共建派，将道路、粮仓与水利列为共同事业。','Support for the Common Works Party','The country now supports the Common Works Party and its roads, granaries and waterways.'),
        ('hbe_feast_local_action','支持兴业派','本府转而支持兴业派，将作坊、茶市与商运列为共同事业。','Support for the Industry Party','The country now supports the Industry Party and its workshops, tea markets and commerce.'),
    ]:
        for prefix in ('PERFORM','WE_PERFORM','OTHER_PERFORMS'):
            for suffix in ('HEADER','TITLE','SETUP','LOG','MAP'):
                key = f'{prefix}_{action}_ACTION_{suffix}'
                cn[key] = title if suffix in ('HEADER','TITLE','MAP') else explanation
                en[key] = etitle if suffix in ('HEADER','TITLE','MAP') else eexplanation
    for region, _, good, _, _, cname, ename in PRODUCERS:
        cn[f'hbe_{region}_basic_production'] = cname
        en[f'hbe_{region}_basic_production'] = ename
        cn[f'hbe_{region}_ordinary_production'] = '普通商品生产'
        en[f'hbe_{region}_ordinary_production'] = 'Ordinary Goods Production'
        for pattern, _, _, label, elabel in required:
            key = pattern.format(g=good)
            name = dict(hbe_shu_embroidery='蜀绣', hbe_well_salt='井盐', hbe_shu_paper='蜀纸', hbe_border_tea='边茶')[good]
            ename = good.removeprefix('hbe_').replace('_', ' ').title()
            cn['MODIFIER_TYPE_NAME_' + key] = name + label
            en['MODIFIER_TYPE_NAME_' + key] = ename + ': ' + elabel
            cn['MODIFIER_TYPE_DESC_' + key] = '调整' + name + '的' + label + '。'
            en['MODIFIER_TYPE_DESC_' + key] = 'Adjusts ' + elabel.lower() + ' for ' + ename + '.'
    for language, entries in [('simp_chinese', cn), ('english', en)]:
        core = out / f'main_menu/localization/{language}/hbe_l_{language}.yml'
        content = core.read_text(encoding='utf-8-sig')
        extra = {}
        for k, v in entries.items():
            line = ' ' + k + ': ' + json.dumps(v, ensure_ascii=False)
            content, n = re.subn(r'(?m)^\s*'+re.escape(k)+r':[^\n]*$', lambda m:line, content)
            if not n: extra[k] = v
        write(core, content.rstrip('\n')); changed.add(core.relative_to(out).as_posix())
        p = out / f'main_menu/localization/{language}/hbe_observer_hotfix_l_{language}.yml'
        write(p, 'l_' + language + ':\n' + '\n'.join(' ' + k + ': ' + json.dumps(v, ensure_ascii=False) for k, v in extra.items()))
        changed.add(p.relative_to(out).as_posix())
    summary = dict(version='0.3.0', active_advance_rename={OLD: NEW}, goods_required_types=8, event_metadata_fixed=events_fixed, starter_output={good: amount for _, _, good, amount, _, _, _ in PRODUCERS}, starter_advance={good: f'hbe_tech_{region}_{tier}' for region, _, good, _, tier, _, _ in PRODUCERS}, ordinary_recipe_retained=True, advanced_era_gates_unchanged=True, paper_institution_remains_era_two=True, early_research_ai_weight=20, producer_construction_weight=4, external_target_score_adjustment=-.10, troop_stats_unchanged=True, changed_files=sorted(changed))
    summary['goods_required_types'] = len(required) * len(PRODUCERS)
    summary['external_target_score_multiplier'] = .90
    summary['additional_goods_diagnostics'] = 'Full-log audit found 24 more native goods modifier types beyond the eight minting types in the first report.'
    manifest_path = out / 'build_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    previous = manifest.get('observer_hotfix', {})
    summary['event_metadata_fixed'] = sorted(set(events_fixed + previous.get('event_metadata_fixed', [])))
    summary['changed_files'] = sorted((set(summary['changed_files']) | set(previous.get('changed_files', []))) - set(removed))
    summary['removed_files'] = removed
    summary['legacy_migration'] = 'Already-set old monthly completion flag grants the renamed advance without repeat rewards; old enum-only saves may report the removed identifier when loading.'
    def update_catalog(value):
        if isinstance(value, str): return re.sub(r'\b'+OLD+r'(?=\b|_)', NEW, value)
        if isinstance(value, list): return [update_catalog(v) for v in value]
        if isinstance(value, dict): return {update_catalog(k): update_catalog(v) for k,v in value.items()}
        return value
    for key in list(manifest):
        if key not in ('observer_hotfix','files','file_hashes'):
            manifest[key] = update_catalog(manifest[key])
    for filename in ('native_content_v011.json','technology_v001.json','technology_rewards_v021.json','social_expansion_v020.json'):
        p = root/'data'/filename
        if p.exists():
            data = json.loads(p.read_text(encoding='utf-8-sig'))
            p.write_text(json.dumps(update_catalog(data),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    manifest['observer_hotfix'] = summary
    hashes = manifest.get('file_hashes')
    if hashes is None:
        hashes = next(v for v in manifest.values() if isinstance(v, dict) and any('/' in k and isinstance(w, str) and len(w) == 64 for k, w in v.items()))
    hashes.update({name: hashlib.sha256((out / name).read_bytes()).hexdigest() for name in changed})
    for name in removed: hashes.pop(name, None)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (root / 'data/observer_hotfix_v030.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return summary


if __name__ == '__main__':
    summary = apply(ROOT / 'mod/holy_bashu_empire')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
