"""Data-driven local-affairs MVP; runs last, after all legacy generators.

The catalogue drives eligibility, both investment tiers, GUI, settlement and AI.
No installation or release operations. Vanilla GUI primitives / scripted GUIs.
"""
from pathlib import Path
import json
import re

from build_support import write_preserving_format
from pdxscript import blocks, apply_edits

COUNTERS = ('hbe_water', 'hbe_salt', 'hbe_river', 'hbe_roads', 'hbe_grain', 'hbe_tea', 'hbe_valleys')
MEMBER = 'is_member_of_international_organization = international_organization:hbe_empire'


def burden(n):
    return f'change_variable = {{ name = hbe_burden add = {n} }} hbe_clamp_burden = yes'


def migrate(out, regions):
    """Retire old balances without leaving financial or progression dead ends."""
    changed = []
    group_for = {r[4]: r[0] for r in regions}
    for path in (out / 'in_game').rglob('*.txt'):
        if path.name.startswith('hbe_af_'):
            continue
        text = path.read_text(encoding='utf-8-sig')
        if not any(re.search(r'\b' + c + r'\b', text) for c in COUNTERS):
            continue
        edits = []
        for key, start, a, b, end in blocks(text):
            if key not in ('change_variable', 'set_variable'):
                continue
            m = re.search(r'\bname\s*=\s*(' + '|'.join(COUNTERS) + r')\b', text[a:b])
            if not m:
                continue
            # Payments become a small labor cost. Old rewards / initialization disappear.
            debit = re.search(r'\bsubtract\s*=\s*(\d+(?:\.\d+)?)', text[a:b])
            replacement = burden(2) if key == 'change_variable' and debit else ''
            edits.append((start, end, replacement))
        text = apply_edits(text, edits)
        for counter, group in group_for.items():
            text = re.sub(r'\bvar:' + counter + r'\s*>=\s*\d+(?:\.\d+)?', f'hbe_af_basis_{group} = yes', text)
            # Old caps have no remaining purpose; keep their enclosing empty clauses harmless.
            text = re.sub(r'\bvar:' + counter + r'\s*>\s*100', 'always = no', text)
            text = re.sub(r'\bhas_variable\s*=\s*' + counter + r'\b', 'always = yes', text)
        if path.name == 'hbe_banquet_decisions.txt':
            # No more per-circle balance / yiqi fallback. One explicit cost per contract.
            edits = []
            for key, _, a, b, _ in blocks(text, 0):
                if not key.startswith('hbe_role_'):
                    continue
                body = text[a:b]
                body = re.sub(r'OR = \{ hbe_af_basis_\w+ = yes AND = \{ NOT = \{ always = yes \} has_variable = hbe_tech_common_2 var:hbe_yiqi >= 10 \} \}', 'var:hbe_burden <= 64', body)
                body = re.sub(r'if = \{ limit = \{ always = yes \}.*?\}\s*else = \{.*?hbe_clamp_yiqi = yes \}', burden(6), body, flags=re.S)
                edits.append((a, b, body))
            text = apply_edits(text, edits)
        if path.name == 'hbe_technology_effects.txt':
            # Institutional production should not require periodic decision clicking.
            text = re.sub(r'has_variable = hbe_recent_delivery_\w+', '', text)
        if path.name == 'hbe_decisions.txt':
            edits = []
            for key, _, a, b, _ in blocks(text, 0):
                if key.startswith('hbe_service_'):
                    body = text[a:b]
                    pot = next(x for x in blocks(body, 0) if x[0] == 'potential')
                    body = body[:pot[2]] + ' always = no ' + body[pot[3]:]
                    edits.append((a, b, body))
            text = apply_edits(text, edits)
        write_preserving_format(path, text)
        changed.append(path.relative_to(out).as_posix())
    return changed


def apply(out, root, game):
    out, root = Path(out), Path(root)
    manifest_path = out / 'build_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    regions = manifest['regions']
    catalogue = json.loads((root / 'data/local_affairs_projects.json').read_text(encoding='utf-8'))
    projects, tiers = catalogue['projects'], catalogue['tiers']
    assert len({p['id'] for p in projects}) == len(projects)
    assert {p['pool'] for p in projects} == {'national', 'local'}
    assert len(tiers) == 2, 'MVP layout supports two configured tiers'
    loc = {}
    effects, triggers, values, sguis = [], [], [], []
    from build_local_affairs_rewards import has_reward
    from build_local_affairs_targets import condition as target_condition, choose as choose_target, shortage_trigger
    gold_scale = catalogue["gold_cost_multiplier"]
    burden_scale = catalogue["burden_cost_multiplier"]

    def put(rel, text):
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        write_preserving_format(path, text) if path.exists() else path.write_text(text, encoding='utf-8-sig')

    def requires(items):
        return ' '.join('has_advance = ' + x for x in items)

    def tier_requirements(tier):
        return requires(tier['requires']) + ' ' + ' '.join(
            'modifier:' + key + ' = yes' for key in tier.get('requires_modifiers', []))

    triggers.append(f'hbe_af_access = {{ hbe_is_prince = yes {MEMBER} }}')
    triggers.append('hbe_af_idle = { NOT = { has_variable = hbe_af_active } NOT = { has_variable = hbe_af_wait } }')
    triggers.append('hbe_af_target_owned = { exists = var:hbe_af_target var:hbe_af_target = { owner = root controller = root } OR = { NOT = { exists = var:hbe_af_road_target } var:hbe_af_road_target = { owner = root controller = root } } }')
    triggers.append(shortage_trigger(Path(game)))
    for r in regions:
        group = r[0]
        # A real operating institution OR a project completed in the circle is evidence.
        from expansion_catalogue import BUILDINGS
        buildings = [b[0].removeprefix('hbe_') for b in BUILDINGS if b[2] == group]
        basis = ' '.join('hbe_operating_' + b + ' = yes' for b in buildings)
        triggers.append(f'hbe_af_basis_{group} = {{ OR = {{ has_variable = hbe_af_done_{group} {basis} }} }}')

    from build_local_affairs_guilds import build as build_guilds, sponsor as guild_sponsor, start as guild_start
    guilds = build_guilds(out, root, put, loc, projects, catalogue)
    from build_local_affairs_rewards import build as build_rewards, reward, preview
    effects += build_rewards(put, loc, projects)
    changed = migrate(out, regions)
    # This feature owns only its own GUI; retain the accepted situation panel bytes.
    (out / 'in_game/gui/panels/situation/hbe_banquet.gui').write_bytes((root / 'assets/gui/hbe_banquet.gui').read_bytes())
    from build_local_affairs_research import build as build_research, refresh_support
    research = build_research(out, root, put, loc, manifest)
    from build_civic_teahouse import build as build_teahouse
    build_teahouse(out, root, put, loc, manifest)
    # Legacy service orders are retired separately; no hidden reward loop remains.
    values += ['hbe_af_reserve = { value = 10 }', 'hbe_af_budget = { value = hbe_event_economic_base multiply = 8 min = 20 }',
               'hbe_af_local_reward_multiplier = { value = 1 add = modifier:hbe_af_local_reward_modifier min = 0 }',
               'hbe_af_remaining = { value = var:hbe_af_months subtract = var:hbe_af_elapsed min = 0 }']
    for p in projects:
        pid, key = p['id'], p['key']
        category = catalogue['categories'][p['category']]
        extra = requires(category['requires'] + p['requires'])
        extra += ' ' + ' '.join('modifier:'+key+' = yes' for key in p.get('requires_modifiers', []))
        if p['pool'] == 'local':
            extra += f' any_owned_location = {{ {target_condition(p)} }}'
        if p.get('relief_weight'):
            extra += ' var:hbe_burden >= 6'
        for item in p['rewards']:
            if item['type'] == 'modifier' and 'modifier' in item and catalogue['modifiers'][item['modifier']]['scope'] == 'country':
                extra += f' NOT = {{ has_country_modifier = hbe_af_{item["modifier"]} }}'
                variants={row['modifier'] for q in projects for row in q['rewards'] if row.get('guild_variant')}
                if item['modifier'] in variants:
                    extra += ' ' + ' '.join(f'NOT = {{ has_country_modifier = hbe_af_{item["modifier"]}_guild_{n} }}' for n in range(1,5))
        triggers.append(f'hbe_af_eligible_{pid} = {{ {extra or "always = yes"} }}')
        loc[f'hbe_af_project_{pid}'] = p['name']
        loc[f'hbe_af_desc_{pid}'] = p['description']
        for i, tier in enumerate(tiers):
            ident = f'{pid}_{tier["key"]}'
            multiplier = p['cost'] / 4 * tier['cost_multiplier'] * gold_scale
            values.append(f'hbe_af_cost_{ident} = {{ value = hbe_event_economic_base multiply = {multiplier:g} min = {p["cost"] * tier["cost_multiplier"] * gold_scale:g} }}')
            sponsored = f' if = {{ limit = {{ {guild_sponsor(p)} }} multiply = {1-catalogue["guilds"]["sponsor_discount"]:g} }}' if p.get('guild_role') else ''
            values.append(f'hbe_af_load_{ident} = {{ value = {p["burden"][i] * burden_scale:g} if = {{ limit = {{ has_policy = hbe_paid_policy }} multiply = 0.5 }} else_if = {{ limit = {{ has_policy = hbe_levy_policy }} multiply = 1.25 }}{sponsored} }}')
            local = p['pool'] == 'local'
            candidate = 'hbe_af_local' if local else 'hbe_af_national'
            allowed = f'hbe_af_access = yes hbe_af_idle = yes var:{candidate} = {pid} hbe_af_eligible_{pid} = yes {tier_requirements(tier)} gold >= hbe_af_cost_{ident} '
            allowed += f'var:hbe_burden <= {{ value = 70 subtract = hbe_af_load_{ident} }} '
            if local:
                allowed += f'exists = var:hbe_af_candidate_target var:hbe_af_candidate_target = {{ {target_condition(p)} }} '
                if has_reward(p, 'road'):
                    allowed += 'exists = var:hbe_af_candidate_road var:hbe_af_candidate_road = { owner = root controller = root is_connected_to = root.var:hbe_af_candidate_target NOT = { has_road_to = root.var:hbe_af_candidate_target } } '
            triggers.append(f'hbe_af_can_{ident} = {{ {allowed} }}')
            start = f'''add_gold = {{ value = hbe_af_cost_{ident} multiply = -1 }}
change_variable = {{ name = hbe_af_spent add = hbe_af_cost_{ident} }}
change_variable = {{ name = hbe_burden add = hbe_af_load_{ident} }} hbe_clamp_burden = yes
set_variable = {{ name = hbe_af_active value = {pid} }} set_variable = {{ name = hbe_af_tier value = {i + 1} }}
set_variable = {{ name = hbe_af_months value = {p['months'][i]} }} set_variable = {{ name = hbe_af_elapsed value = 0 }} set_variable = {{ name = hbe_af_progress value = 0 }}
set_variable = {{ name = hbe_af_credit_economic value = hbe_event_economic_base }}
set_variable = {{ name = hbe_af_paid value = hbe_af_cost_{ident} }} set_variable = {{ name = hbe_af_load value = hbe_af_load_{ident} }}
set_variable = {{ name = hbe_af_last_national value = var:hbe_af_national }} set_variable = {{ name = hbe_af_last_local value = var:hbe_af_local }}
remove_variable = hbe_af_pause remove_variable = hbe_af_credit_recorded remove_variable = hbe_af_factor_0 remove_variable = hbe_af_factor_1 remove_variable = hbe_af_factor_2 remove_variable = hbe_af_factor_3
hbe_af_roll_outcome = yes hbe_af_roll_rewards_{pid} = yes hbe_af_update_eta = yes
'''
            if local:
                start += 'set_variable = { name = hbe_af_target value = var:hbe_af_candidate_target } '
            else:
                start += 'remove_variable = hbe_af_target '
            if has_reward(p, 'road'):
                start += 'set_variable = { name = hbe_af_road_target value = var:hbe_af_candidate_road } '
            else:
                start += 'remove_variable = hbe_af_road_target '
            start += guild_start(p)
            start += 'set_variable = { name = hbe_af_reward_multiplier value = '+('hbe_af_local_reward_multiplier' if local else '1')+' } '
            # Retain both offers and the local target for the dimmed unselected card.
            effects.append(f'hbe_af_start_{ident} = {{ if = {{ limit = {{ hbe_af_can_{ident} = yes }} {start} }} }}')
            sguis.append(f'hbe_af_choose_{ident} = {{ scope = country is_shown = {{ hbe_af_access = yes }} is_valid = {{ hbe_af_can_{ident} = yes }} effect = {{ hbe_af_start_{ident} = yes }} }}')
            loc[f'hbe_af_tier_{ident}'] = f'{tier["name"]}：金币 [GuiScope.SetRoot(Player.MakeScope).ScriptValue(\'hbe_af_cost_{ident}\')|2]；役负 +[GuiScope.SetRoot(Player.MakeScope).ScriptValue(\'hbe_af_load_{ident}\')|1]；{p["months"][i]}个月。\\n' + preview(p, i)
            loc[f'hbe_af_button_{ident}'] = tier['name']
            if tier.get('requires_modifiers'):
                loc[f'hbe_af_tier_{ident}'] += '\\n须解锁「$hbe_af_allow_large_investment$」（$hbe_af_public_funding$）。'
            effects.append(f'hbe_af_reward_{ident} = {{ {reward(p, i)} }}')
            loc[f'hbe_af_reward_text_{pid}_{i}'] = preview(p, i)
    # Each candidate owns a persisted 12-24 month lifetime; GUI opening never rerolls.
    low, high = catalogue['offer_lifetime_months']
    assert 12 <= low <= high <= 24
    for pool in ('national', 'local'):
        timer = f'hbe_af_{pool}_expires'
        rolls = ' '.join(f'1 = {{ set_variable = {{ name = {timer} value = {n} }} }}' for n in range(low, high + 1))
        effects.append(f'hbe_af_reset_{pool}_expiry = {{ random_list = {{ {rolls} }} }}')
        choices = []
        for p in projects:
            if p['pool'] != pool: continue
            pid = p['id']
            others = ' '.join(f'hbe_af_eligible_{q["id"]} = yes' for q in projects if q['pool']==pool and q['id']!=pid)
            choice = f'100 = {{ trigger = {{ hbe_af_eligible_{pid} = yes OR = {{ NOT = {{ var:hbe_af_last_{pool} = {pid} }} NOT = {{ OR = {{ {others} }} }} }} }} '
            if p.get('relief_weight'):
                choice += 'modifier = { factor = 2 var:hbe_burden >= 40 } modifier = { factor = 1.5 var:hbe_burden >= 60 } '
            choice += f'set_variable = {{ name = hbe_af_{pool} value = {pid} }} hbe_af_reset_{pool}_expiry = yes '
            if pool == 'local': choice += choose_target(p)
            choices.append(choice+' }')
        clear = 'remove_variable = hbe_af_candidate_target remove_variable = hbe_af_candidate_road ' if pool=='local' else ''
        effects.append(f'hbe_af_draw_{pool} = {{ if = {{ limit = {{ has_variable = hbe_af_{pool} }} set_variable = {{ name = hbe_af_last_{pool} value = var:hbe_af_{pool} }} }} {clear} remove_variable = hbe_af_{pool} remove_variable = {timer} random_list = {{ {" ".join(choices)} }} remove_variable = hbe_af_notice_dismissed }}')
    effects.append('hbe_af_draw = { hbe_af_draw_national = yes hbe_af_draw_local = yes change_variable = { name = hbe_af_round add = 1 } }')
    # Only cancellation retains the accepted three-month cooldown, never auto/manual skip.
    effects.append('hbe_af_begin_wait = { set_variable = hbe_af_wait set_variable = { name = hbe_af_wait_left value = 3 } set_variable = { name = hbe_af_wait_progress value = 0 } }')
    expiry_migration = ['if = { limit = { NOT = { has_variable = hbe_af_expiry_v1 } } set_variable = hbe_af_expiry_v1 if = { limit = { has_variable = hbe_af_wait NOT = { has_variable = hbe_af_active } } remove_variable = hbe_af_wait hbe_af_draw = yes } }']
    tick = []
    for pool in ('national','local'):
        timer = f'hbe_af_{pool}_expires'
        expiry_migration.append(f'if = {{ limit = {{ has_variable = hbe_af_{pool} NOT = {{ has_variable = {timer} }} }} hbe_af_reset_{pool}_expiry = yes }}')
        expiry_migration.append(f'if = {{ limit = {{ hbe_af_idle = yes NOT = {{ has_variable = hbe_af_{pool} }} }} hbe_af_draw_{pool} = yes }}')
        tick.append(f'if = {{ limit = {{ has_variable = hbe_af_{pool} }} change_variable = {{ name = {timer} subtract = 1 }} if = {{ limit = {{ var:{timer} <= 0 }} hbe_af_draw_{pool} = yes }} }} else = {{ hbe_af_draw_{pool} = yes }}')
    effects.append('hbe_af_migrate_expiry = { '+' '.join(expiry_migration)+' }')
    effects.append('hbe_af_tick_offers = { if = { limit = { hbe_af_idle = yes } '+' '.join(tick)+' } }')
    effects.append('hbe_af_update_eta = { set_variable = { name = hbe_af_eta_year value = current_year } set_variable = { name = hbe_af_eta_month value = { value = current_month add = var:hbe_af_months subtract = var:hbe_af_elapsed } } while = { limit = { var:hbe_af_eta_month > 12 } change_variable = { name = hbe_af_eta_year add = 1 } change_variable = { name = hbe_af_eta_month subtract = 12 } } }')
    complete = []
    for p in projects:
        for tier in tiers:
            ti = tiers.index(tier) + 1
            complete.append(f'if = {{ limit = {{ var:hbe_af_active = {p["id"]} var:hbe_af_tier = {ti} }} hbe_af_reward_{p["id"]}_{tier["key"]} = yes hbe_af_record_contribution = yes hbe_af_receipt_{p["id"]} = yes }}')
    mark = ' '.join(f'if = {{ limit = {{ var:hbe_af_target = {{ is_in_scripted_geography = scripted_geography:hbe_geo_{r[0]} }} }} set_variable = hbe_af_done_{r[0]} }}' for r in regions)
    effects.append('hbe_af_complete = { if = { limit = { has_variable = hbe_af_active } ' + ' '.join(complete) + f' if = {{ limit = {{ exists = var:hbe_af_target }} {mark} var:hbe_af_target = {{ set_variable = {{ name = hbe_af_local_cooldown value = yes years = 5 }} }} }} set_variable = {{ name = hbe_af_last_project value = var:hbe_af_active }} change_variable = {{ name = hbe_af_completed add = 1 }} remove_variable = hbe_af_active remove_variable = hbe_af_target remove_variable = hbe_af_road_target remove_variable = hbe_af_pause hbe_af_draw = yes }} }}')
    # Budgeted deterministic scoring over exactly the same two cards / tiers.
    auto = 'set_variable = { name = hbe_af_best value = 0 } set_variable = { name = hbe_af_choice value = 0 } '
    for p in projects:
        for i, tier in enumerate(tiers):
            ident = f'{p["id"]}_{tier["key"]}'
            choice_id = p['id'] * 10 + i + 1
            score = p['score'] + (2 if i else 0)
            auto_preferences = f'NOT = {{ has_variable = hbe_af_no_{p["pool"]} }} '
            if i:
                auto_preferences += 'NOT = { has_variable = hbe_af_no_large } '
            auto += f'''if = {{ limit = {{ {auto_preferences} hbe_af_can_{ident} = yes gold >= {{ value = hbe_af_cost_{ident} add = var:hbe_af_reserve }} var:hbe_af_spent <= {{ value = var:hbe_af_budget subtract = hbe_af_cost_{ident} }} var:hbe_burden <= {{ value = var:hbe_af_limit subtract = hbe_af_load_{ident} }} }}
set_variable = {{ name = hbe_af_score value = {score} }}
if = {{ limit = {{ gold < {{ value = hbe_af_cost_{ident} multiply = 4 }} }} change_variable = {{ name = hbe_af_score subtract = {4 if i else 1} }} }}
if = {{ limit = {{ var:hbe_burden >= 40 }} change_variable = {{ name = hbe_af_score subtract = {p['burden'][i] * burden_scale:g} }} }}
'''
            if p.get('relief_weight'):
                auto += 'change_variable = { name = hbe_af_score add = { value = var:hbe_burden multiply = 0.2 } } '
            auto += f'if = {{ limit = {{ var:hbe_af_score > var:hbe_af_best }} set_variable = {{ name = hbe_af_best value = var:hbe_af_score }} set_variable = {{ name = hbe_af_choice value = {choice_id} }} }} }} '
    dispatch = []
    for p in projects:
        for i, tier in enumerate(tiers):
            dispatch.append(f'if = {{ limit = {{ var:hbe_af_choice = {p["id"] * 10 + i + 1} var:hbe_af_best >= 7 }} hbe_af_start_{p["id"]}_{tier["key"]} = yes }} ')
    effects.append('hbe_af_auto_start = { ' + ''.join(dispatch) + ' }')
    from build_local_affairs_ai import participation_effect
    effects.append(participation_effect(catalogue['ai_participation']))
    auto += 'if = { limit = { var:hbe_af_choice > 0 var:hbe_af_best >= 7 } if = { limit = { is_ai = yes } hbe_af_ai_consider = yes } else = { hbe_af_auto_start = yes } }'
    # If nothing qualifies, leave both offers intact until their natural expiry.
    effects.append('hbe_af_auto_choose = { ' + auto + ' }')
    initialize = ' '.join('remove_variable = ' + c for c in COUNTERS)
    effects.append(f'''hbe_af_initialize = {{ hbe_af_retire_legacy_country = yes if = {{ limit = {{ NOT = {{ has_variable = hbe_af_initialized }} }}
set_variable = hbe_af_initialized set_variable = {{ name = hbe_af_round value = 0 }} set_variable = {{ name = hbe_af_completed value = 0 }}
set_variable = {{ name = hbe_af_spent value = 0 }} set_variable = {{ name = hbe_af_reserve value = 10 }} set_variable = {{ name = hbe_af_budget value = hbe_af_budget }} set_variable = {{ name = hbe_af_limit value = 50 }} {initialize}
if = {{ limit = {{ NOT = {{ has_variable = hbe_burden }} }} set_variable = {{ name = hbe_burden value = 20 }} }}
if = {{ limit = {{ hbe_af_idle = yes }} hbe_af_draw = yes }} }} }}''')
    effects.append("""hbe_af_migrate_cards = { if = { limit = { NOT = { has_variable = hbe_af_cards_v2 } }
set_variable = hbe_af_cards_v2
if = { limit = { has_variable = hbe_af_active }
 set_variable = { name = hbe_af_national value = var:hbe_af_last_national }
 set_variable = { name = hbe_af_local value = var:hbe_af_last_local }
 if = { limit = { exists = var:hbe_af_target } set_variable = { name = hbe_af_candidate_target value = var:hbe_af_target } }
 if = { limit = { NOT = { has_variable = hbe_af_outcome } } hbe_af_roll_outcome = yes }
 hbe_af_update_eta = yes
}
if = { limit = { has_variable = hbe_af_wait } hbe_af_begin_wait = yes }
} }""")
    # Availability means a real, affordable choice; merely seeing a card is insufficient.
    available = ' '.join(f'hbe_af_can_{p["id"]}_{t["key"]} = yes' for p in projects for t in tiers)
    triggers.append('hbe_af_available = { hbe_af_access = yes hbe_af_idle = yes OR = { '+available+' } }')
    effects.append('''hbe_af_monthly = {
 hbe_af_initialize = yes hbe_af_migrate_cards = yes hbe_af_migrate_expiry = yes hbe_af_tick_offers = yes
 if = { limit = { has_variable = hbe_af_wait }
 change_variable = { name = hbe_af_wait_left subtract = 1 }
 set_variable = { name = hbe_af_wait_progress value = { value = 3 subtract = var:hbe_af_wait_left divide = 3 min = 0 max = 1 } }
 if = { limit = { var:hbe_af_wait_left <= 0 } remove_variable = hbe_af_wait hbe_af_draw = yes }
 }
 if = { limit = { has_variable = hbe_af_active }
  if = { limit = { OR = { NOT = { exists = var:hbe_af_target } hbe_af_target_owned = yes } }
   remove_variable = hbe_af_pause change_variable = { name = hbe_af_elapsed add = 1 }
   set_variable = { name = hbe_af_progress value = { value = var:hbe_af_elapsed divide = var:hbe_af_months max = 1 } }
   hbe_af_update_eta = yes
   if = { limit = { var:hbe_af_elapsed >= var:hbe_af_months } hbe_af_complete = yes }
  } else = { change_variable = { name = hbe_af_pause add = 1 } hbe_af_update_eta = yes
   if = { limit = { var:hbe_af_pause >= 12 } hbe_af_cancel = yes }
  }
 }
 if = { limit = { OR = { has_variable = hbe_af_auto is_ai = yes } hbe_af_idle = yes NOT = { at_war = yes } } hbe_af_auto_choose = yes }
}''')
    effects.append('hbe_af_cancel = { if = { limit = { has_variable = hbe_af_active } add_gold = { value = var:hbe_af_paid multiply = 0.25 } remove_variable = hbe_af_active remove_variable = hbe_af_target remove_variable = hbe_af_road_target remove_variable = hbe_af_pause hbe_af_begin_wait = yes } }')
    refresh_support(research, projects, triggers, effects, sguis, loc)
    put('in_game/common/scripted_effects/hbe_af_effects.txt', '\n'.join(effects))
    put('in_game/common/scripted_triggers/hbe_af_triggers.txt', '\n'.join(triggers))
    put('in_game/common/script_values/hbe_af_values.txt', '\n'.join(values))
    put('in_game/common/on_action/hbe_af_on_actions.txt', f'''on_game_start = {{ on_actions = {{ hbe_af_start }} }}
hbe_af_start = {{ effect = {{ every_country = {{ limit = {{ hbe_af_access = yes }} hbe_af_initialize = yes }} }} }}
monthly_country_pulse = {{ on_actions = {{ hbe_af_pulse }} }}
hbe_af_pulse = {{ trigger = {{ hbe_af_access = yes }} effect = {{ hbe_af_monthly = yes }} }}
yearly_country_pulse = {{ on_actions = {{ hbe_af_year }} }}
hbe_af_year = {{ trigger = {{ hbe_af_access = yes }} effect = {{ set_variable = {{ name = hbe_af_spent value = 0 }} }} }}''')
    modifiers=[]
    for key, spec in catalogue['modifiers'].items():
        modifiers.append('hbe_af_'+key+' = { '+' '.join(f'{k} = {v:g}' for k,v in spec['effects'].items())+' }')
        loc['STATIC_MODIFIER_NAME_hbe_af_'+key]=spec['name']
        loc['hbe_af_'+key+'_desc']=spec['description']
        loc['STATIC_MODIFIER_DESC_hbe_af_'+key]='$hbe_af_'+key+'_desc$'
    put('main_menu/common/static_modifiers/hbe_af_modifiers.txt', '\n'.join(modifiers))
    # Scripted GUI execution always rechecks cost, eligibility and one-choice round lock.
    for key, valid, eff in [
        ('access', 'hbe_af_access = yes', ''),
        ('prepare', 'hbe_af_access = yes', 'hbe_af_initialize = yes hbe_af_migrate_cards = yes hbe_af_migrate_expiry = yes'),
        ('panel_open', 'hbe_af_access = yes', 'hbe_af_migrate_cards = yes hbe_af_migrate_expiry = yes set_variable = hbe_af_panel_visible'),
        ('panel_close', 'hbe_af_access = yes', 'remove_variable = hbe_af_panel_visible'),
        ('auto', 'hbe_af_access = yes', 'if = { limit = { has_variable = hbe_af_auto } remove_variable = hbe_af_auto } else = { set_variable = hbe_af_auto }'),
        ('cancel', 'hbe_af_access = yes has_variable = hbe_af_active', 'hbe_af_cancel = yes'),
        ('dismiss_notice', 'hbe_af_available = yes', 'set_variable = hbe_af_notice_dismissed'),
    ]:
        prepare = 'hbe_af_initialize = yes ' if key not in ('access', 'prepare') else ''
        sguis.append(f'hbe_af_ui_{key} = {{ scope = country is_shown = {{ hbe_af_access = yes }} is_valid = {{ {valid} }} effect = {{ {prepare}{eff} }} }}')
    from build_local_affairs_hud import states as hud_states
    for state, trigger in [('ready', 'hbe_af_idle = yes'), ('running', 'has_variable = hbe_af_active'), ('waiting', 'has_variable = hbe_af_wait'), ('panel_visible', 'has_variable = hbe_af_panel_visible'), ('auto_state', 'has_variable = hbe_af_auto'), ('available', 'hbe_af_available = yes NOT = { has_variable = hbe_af_notice_dismissed }')] + hud_states(projects):
        sguis.append(f'hbe_af_ui_{state} = {{ scope = country is_shown = {{ hbe_af_access = yes {trigger} }} is_valid = {{ hbe_af_access = yes }} effect = {{ }} }}')
    for option in ('national', 'local', 'large'):
        flag = 'hbe_af_no_' + option
        sguis.append(f'hbe_af_allow_{option} = {{ scope = country is_shown = {{ hbe_af_access = yes NOT = {{ has_variable = {flag} }} }} is_valid = {{ hbe_af_access = yes }} effect = {{ hbe_af_initialize = yes if = {{ limit = {{ has_variable = {flag} }} remove_variable = {flag} }} else = {{ set_variable = {flag} }} }} }}')
    for var, label, low, high, step in [('reserve', '保留国库', 0, 1000, 10), ('budget', '年度预算', 0, 5000, 10), ('limit', '役负上限', 20, 70, 5)]:
        for sign, delta in [('minus', -step), ('plus', step)]:
            sguis.append(f'hbe_af_{var}_{sign} = {{ scope = country is_shown = {{ hbe_af_access = yes }} is_valid = {{ hbe_af_access = yes }} effect = {{ hbe_af_initialize = yes set_variable = {{ name = hbe_af_{var} value = {{ value = var:hbe_af_{var} add = {delta} min = {low} max = {high} }} }} }} }}')
    put('in_game/common/scripted_guis/hbe_af_gui.txt', '\n'.join(sguis))
    from build_local_affairs_contribution import apply as contribution
    contribution(out, put, loc, projects, catalogue['contribution'])
    from retire_local_affairs_legacy import apply as retire_legacy
    retire_legacy(out, put, regions)
    build_gui(out, put, loc, projects, tiers, game)
    from build_local_affairs_notices import build as build_notices
    build_notices(out,put,loc,game)
    # Retire balance-centric UI prose across the existing three locale files.
    for path in (out / 'main_menu/localization').rglob('hbe_l_*.yml'):
        text = path.read_text(encoding='utf-8-sig')
        lines = []
        labels = ('水权储备', '盐引信用', '江运互保', '轮戍履约', '义仓储备', '商队互保', '地方共治')
        for line in text.splitlines():
            for counter in COUNTERS:
                line = re.sub(r"\[[^\]]*GetVariable\('" + counter + r"'\)[^\]]*\]", '—', line)
            if re.match(r'\s*hbe_(?:mission_|role_|coordinate_)', line):
                for label in labels:
                    line = re.sub(r'(?:消耗|扣除|支付)\s*(?:十|10)\s*点' + label, '承担相应役负', line)
                line = line.replace('没有本地储备时改用十点义气作担保', '资格以实际机构与当前条件为准')
            key = re.match(r'\s*([^:]+):', line)
            if key:
                key = key[1]
                retired_terms = ('water', 'salt', 'river', 'roads', 'grain', 'tea', 'valleys')
                if any(key == 'game_concept_hbe_term_' + term + '_desc' for term in retired_terms):
                    line = ' ' + key + ': "本圈地方经营以实际机构、产业与工程成果为凭据，不再积攒或支付独立点数。地方事业在专用面板中筹办，金币与役负的费用在投入前显示。"'
                if key == 'game_concept_hbe_term_trial_desc':
                    line = ' ' + key + ': "地方事业每轮提供全国、地方各一张候选卡，选择其中一项的少量或大量投入；候选各有一至两年的有效期，到期自动更新。施工自动推进，完工自动结算。"'
                if key == 'game_concept_hbe_term_yiqi_desc':
                    line = ' ' + key + ': "本国的履约信誉，范围0—100，用于合作与政治资格；事业不再普遍附赠义气，专业交付不再以义气替代已取消的地方余额。"'
            # Resource labels are no longer an independent spendable UI element.
            lines.append(line)
        write_preserving_format(path, '\n'.join(lines) + '\n')
    for lang in ('simp_chinese', 'english', 'traditional_chinese'):
        header = {'simp_chinese': 'l_simp_chinese:', 'english': 'l_english:', 'traditional_chinese': 'l_traditional_chinese:'}[lang]
        put(f'main_menu/localization/{lang}/hbe_af_l_{lang}.yml', header + '\n' + '\n'.join(' ' + k + ': "' + v.replace('"', '\\"') + '"' for k, v in loc.items()) + '\n')
    report = dict(schema_version=1, projects=len(projects), categories=catalogue['categories'], tiers=tiers, old_counter_files=changed, legacy_retired=True, hidden_regional_coordination=7, placeholder_art=True, runtime_verified=False, visual_verified=False, release_status='pending', independent_gui='in_game/gui/hbe_local_affairs.gui', gui_host='in_game/gui/ingame_topbar.gui')
    manifest['local_affairs'] = report
    report['ai_participation'] = catalogue['ai_participation']
    report['guilds'] = guilds
    version = json.loads((root / 'data/release.json').read_text(encoding='utf-8'))['version']
    manifest['version'] = version
    manifest.setdefault('current_release', {})['version'] = version
    metadata_path = out / '.metadata/metadata.json'
    metadata = json.loads(metadata_path.read_text(encoding='utf-8-sig'))
    metadata['version'] = version
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    from apply_presentation_v040 import apply as polish_presentation
    polish_presentation(out, root, manifest)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return report


def build_gui(out, put, loc, projects, tiers, game):
    loc.update(HBE_AF_TITLE='地方事业', HBE_AF_OPEN='地方事业', HBE_AF_CLOSE='收起', HBE_AF_AUTO='自动筹办：切换', HBE_AF_CANCEL='撤办：返还25%已付金币', HBE_AF_NATIONAL='全国筹办', HBE_AF_LOCAL='地方经营', HBE_AF_EMPTY='本方向暂无合格项目。', HBE_AF_WAIT='撤办后等待三个月重新筹办。', HBE_AF_RUNNING='项目施工期间不生成新一轮，完工后自动结算并抽取。')
    loc['HBE_AF_STATUS'] = "国库：[Player.GetCurrencyValue('gold')|2] @gold!　役负：[Player.MakeScope.GetVariable('hbe_burden').GetValue|1] / 100　轮次：[Player.MakeScope.GetVariable('hbe_af_round').GetValue|0]　完工：[Player.MakeScope.GetVariable('hbe_af_completed').GetValue|0]"
    loc['HBE_AF_AUTO_STATUS'] = "年度支出：[Player.MakeScope.GetVariable('hbe_af_spent').GetValue|2] @gold!\\n状态：[Player.Custom('hbe_af_state_text')]"
    loc['HBE_AF_TARGET'] = "目标：[Player.MakeScope.GetVariable('hbe_af_candidate_target').GetLocation.GetName]"
    loc['HBE_AF_PROGRESS'] = "[Player.Custom('hbe_af_active_name')]　档次：[Player.MakeScope.GetVariable('hbe_af_tier').GetValue|0]（1少量／2大量）\\n进度：[Player.MakeScope.GetVariable('hbe_af_elapsed').GetValue|0] / [Player.MakeScope.GetVariable('hbe_af_months').GetValue|0] 月；连续暂停：[Player.MakeScope.GetVariable('hbe_af_pause').GetValue|0]月\\n已付：[Player.MakeScope.GetVariable('hbe_af_paid').GetValue|2]金币；已增役负：[Player.MakeScope.GetVariable('hbe_af_load').GetValue|1]。\\n预计成果：[Player.Custom('hbe_af_active_reward')]"
    custom = []
    from build_local_affairs_hud import custom_text as hud_text
    custom.extend(hud_text(projects))
    for key, var, entries, fallback in [
        ('hbe_af_auto_text', 'hbe_af_auto', [(None, 'HBE_AF_ON')], 'HBE_AF_OFF'),
        ('hbe_af_state_text', '', [], 'HBE_AF_READY'),
    ]:
        if var:
            custom.append(f'{key} = {{ type = country text = {{ trigger = {{ has_variable = {var} }} localization_key = HBE_AF_ON }} text = {{ fallback = yes localization_key = HBE_AF_OFF }} }}')
        else:
            custom.append(f'{key} = {{ type = country text = {{ trigger = {{ has_variable = hbe_af_active }} localization_key = HBE_AF_RUNNING }} text = {{ trigger = {{ has_variable = hbe_af_wait }} localization_key = HBE_AF_WAIT }} text = {{ fallback = yes localization_key = HBE_AF_READY }} }}')
    loc.update(HBE_AF_ON='开启', HBE_AF_OFF='关闭', HBE_AF_READY='待选项目', HBE_AF_RUNNING='筹办中', HBE_AF_WAIT='等待下一轮')
    for typ in ('name', 'reward'):
        rows = []
        for p in projects:
            if typ == 'name':
                rows.append(f'text = {{ trigger = {{ var:hbe_af_active = {p["id"]} }} localization_key = hbe_af_project_{p["id"]} }}')
            else:
                for i, tier in enumerate(tiers):
                    k = f'hbe_af_reward_text_{p["id"]}_{i}'
                    from build_local_affairs_rewards import preview
                    loc[k] = preview(p, i)
                    rows.append(f'text = {{ trigger = {{ var:hbe_af_active = {p["id"]} var:hbe_af_tier = {i + 1} }} localization_key = {k} }}')
        custom.append(f'hbe_af_active_{typ} = {{ type = country {" ".join(rows)} text = {{ fallback = yes localization_key = HBE_AF_EMPTY }} }}')
    put('in_game/common/customizable_localization/hbe_af_custom.txt', '\n'.join(custom))
    from build_local_affairs_gui import render
    render(out, put, loc, projects, tiers, game)


if __name__ == '__main__':
    import argparse
    from build_support import snapshot_files
    parser = argparse.ArgumentParser(description='Apply the affairs stage to an existing accepted package.')
    parser.add_argument('--mod-dir', type=Path, required=True)
    parser.add_argument('--game-dir', type=Path, required=True)
    args = parser.parse_args()
    apply(args.mod_dir, Path(__file__).resolve().parents[1], args.game_dir / 'game')
    path = args.mod_dir / 'build_manifest.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    data['files'] = snapshot_files(args.mod_dir, force=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
