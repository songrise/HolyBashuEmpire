"""Fractional completion credit and terse member-row accounting."""
import re

from build_support import write_preserving_format
from pdxscript import blocks, apply_edits


def apply(out, put, loc, projects, cfg):
    reset_projects = ' '.join(f'set_variable = {{ name = hbe_af_round_credit_{p["id"]} value = 0 }}' for p in projects)
    values = f'''
hbe_af_feast_funding = {{ value = 0 if = {{ limit = {{ has_variable = hbe_round_contributed }} add = 1 }} }}
hbe_af_feast_projects = {{ value = 0 if = {{ limit = {{ has_variable = hbe_af_credit_round is_situation_active = situation:hbe_banquet var:hbe_af_credit_round = situation:hbe_banquet.var:hbe_round }} add = var:hbe_af_round_points }} }}
hbe_af_feast_prior = {{ value = var:hbe_feast_points subtract = hbe_af_feast_funding subtract = hbe_af_feast_projects min = 0 }}
hbe_af_feast_capacity = {{ value = {cfg['round_cap']:g} subtract = var:hbe_feast_points add = hbe_af_feast_funding min = 0 max = {cfg['round_cap']:g} }}
hbe_af_feast_last = {{ value = 0 if = {{ limit = {{ hbe_af_feast_projects > 0 }} add = var:hbe_af_credit_last }} }}
hbe_af_feast_time = {{ value = var:hbe_af_months divide = {cfg['time_reference_months']:g} min = 0 max = {cfg['time_ratio_cap']:g} multiply = {cfg['time_weight']:g} }}
hbe_af_feast_effort = {{ value = var:hbe_af_credit_net_cost divide = var:hbe_af_credit_economic min = 0 max = {cfg['effort_ratio_cap']:g} multiply = {cfg['effort_weight']:g} }}
hbe_af_feast_credit = {{ value = {cfg['base']:g} add = hbe_af_feast_time add = hbe_af_feast_effort multiply = var:hbe_af_credit_quality min = 0 max = {cfg['project_cap']:g} max = hbe_af_feast_capacity }}
# Continuous interpolation through the existing ln(1+points) anchors, capped at 3.
hbe_af_feast_dividend_weight = {{
 value = 0
 if = {{ limit = {{ var:hbe_feast_points > 0 }} add = {{ value = var:hbe_feast_points max = 1 multiply = 0.69315 }} }}
 if = {{ limit = {{ var:hbe_feast_points > 1 }} add = {{ value = var:hbe_feast_points subtract = 1 max = 1 multiply = 0.40546 }} }}
 if = {{ limit = {{ var:hbe_feast_points > 2 }} add = {{ value = var:hbe_feast_points subtract = 2 max = 1 multiply = 0.28768 }} }}
}}
'''
    put('in_game/common/script_values/hbe_af_contribution_values.txt', values)
    effect = '''hbe_af_record_contribution = {
 if = { limit = { has_variable = hbe_af_active NOT = { has_variable = hbe_af_credit_recorded } }
 set_variable = hbe_af_credit_recorded
 set_variable = { name = hbe_af_credit_last value = 0 }
 if = { limit = { is_situation_active = situation:hbe_banquet is_member_of_international_organization = international_organization:hbe_empire }
  hbe_banquet_register = yes
  set_variable = { name = hbe_af_credit_last_project value = var:hbe_af_active }
  if = { limit = { OR = { NOT = { has_variable = hbe_af_credit_round } NOT = { var:hbe_af_credit_round = situation:hbe_banquet.var:hbe_round } } }
   set_variable = { name = hbe_af_credit_round value = situation:hbe_banquet.var:hbe_round }
   set_variable = { name = hbe_af_round_points value = 0 }
  }
  if = { limit = { NOT = { has_variable = hbe_af_credit_economic } } set_variable = { name = hbe_af_credit_economic value = hbe_event_economic_base } }
  set_variable = { name = hbe_af_credit_last value = hbe_af_feast_credit }
  if = { limit = { var:hbe_af_credit_last > 0 }
   change_variable = { name = hbe_af_round_points add = var:hbe_af_credit_last }
   change_variable = { name = hbe_feast_points add = var:hbe_af_credit_last }
   set_variable = { name = hbe_af_credit_last_project value = var:hbe_af_active }
   hbe_feast_recount = yes
  }
 }
 }
}
'''
    effect = effect.replace('set_variable = { name = hbe_af_round_points value = 0 }', 'set_variable = { name = hbe_af_round_points value = 0 } '+reset_projects)
    entries = ' '.join(f'if = {{ limit = {{ var:hbe_af_active = {p["id"]} }} change_variable = {{ name = hbe_af_round_credit_{p["id"]} add = var:hbe_af_credit_last }} }}' for p in projects)
    effect = effect.replace('change_variable = { name = hbe_feast_points add = var:hbe_af_credit_last }', 'change_variable = { name = hbe_feast_points add = var:hbe_af_credit_last } '+entries)
    put('in_game/common/scripted_effects/hbe_af_contribution_effects.txt', effect)

    # Reset the new ledger with the existing 24-month feast round, never on load.
    path = out/'in_game/common/scripted_effects/hbe_banquet_effects.txt'
    text = path.read_text(encoding='utf-8-sig')
    marker = 'set_variable = { name = hbe_af_round_points value = 0 }'
    section = next(x for x in blocks(text, 0) if x[0] == 'hbe_open_accounts')
    body = text[section[2]:section[3]]
    if marker not in body:
        body = body.replace('set_variable = { name = hbe_feast_points value = 0 }',
            'set_variable = { name = hbe_feast_points value = 0 } '+marker+
            ' set_variable = { name = hbe_af_credit_last value = 0 }')
        text = apply_edits(text, [(section[2], section[3], body)])
    if 'name = hbe_af_round_credit_1 ' not in text:
        text = text.replace(marker, marker+' '+reset_projects)
    write_preserving_format(path, text)

    path = out/'in_game/common/scripted_effects/hbe_feast_dividend_effects.txt'
    text = path.read_text(encoding='utf-8-sig')
    start = r'if = \{ limit = \{ var:hbe_feast_points >= 3 \} set_variable = \{ name = hbe_member_dividend_weight value = 1\.38629 \} \}\s*else_if = \{ limit = \{ var:hbe_feast_points >= 2 \} set_variable = \{ name = hbe_member_dividend_weight value = 1\.09861 \} \}\s*else = \{ set_variable = \{ name = hbe_member_dividend_weight value = 0\.69315 \} \}'
    text = re.sub(start, 'set_variable = { name = hbe_member_dividend_weight value = hbe_af_feast_dividend_weight }', text)
    assert text.count('value = hbe_af_feast_dividend_weight') == 2
    write_preserving_format(path, text)

    # Row tooltips inherit the member Country, not Player or party leader.
    path = out/'in_game/gui/panels/situation/hbe_banquet.gui'
    text = path.read_text(encoding='utf-8-sig')
    text = text.replace('item = { widget = { size = { 210 30 }',
        'item = { widget = { size = { 210 30 } tooltip = "HBE_AF_MEMBER_CONTRIBUTION_TT"')
    text = text.replace('tooltipwidget = { using = CountryTooltip }', 'tooltip = "HBE_AF_MEMBER_CONTRIBUTION_TT"')
    text = text.replace('position = { 178 ', 'position = { 164 ').replace('size = { 28 26 } maximumsize = { 28 26 }', 'size = { 42 26 } maximumsize = { 42 26 }').replace('size = { 28 24 }', 'size = { 42 24 }')
    text = text.replace('size = { 137 ', 'size = { 123 ').replace('maximumsize = { 137 ', 'maximumsize = { 123 ')
    text = text.replace("GetVariable('hbe_feast_points').GetValue|0", "GetVariable('hbe_feast_points').GetValue|2")
    put('in_game/gui/panels/situation/hbe_banquet.gui', text)

    custom = '''hbe_af_feast_prior_text = { type = country text = { trigger = { hbe_af_feast_prior > 0.0005 } localization_key = HBE_AF_MEMBER_PRIOR } text = { fallback = yes localization_key = HBE_AF_BLANK } }
hbe_af_feast_last_text = { type = country text = { trigger = { hbe_af_feast_projects > 0 } localization_key = HBE_AF_MEMBER_LAST } text = { fallback = yes localization_key = HBE_AF_BLANK } }
'''
    names = ' '.join(f'text = {{ trigger = {{ var:hbe_af_credit_last_project = {p["id"]} }} localization_key = hbe_af_project_{p["id"]} }}' for p in projects)
    custom += f'hbe_af_feast_last_name = {{ type = country {names} text = {{ fallback = yes localization_key = HBE_AF_BLANK }} }}'
    for p in projects:
        pid = p['id']
        custom += f'\nhbe_af_feast_detail_{pid} = {{ type = country text = {{ trigger = {{ hbe_af_feast_projects > 0 var:hbe_af_round_credit_{pid} > 0 }} localization_key = HBE_AF_MEMBER_PROJECT_{pid} }} text = {{ fallback = yes localization_key = HBE_AF_BLANK }} }}'
        loc[f'HBE_AF_MEMBER_PROJECT_{pid}'] = f"\\n  · {p['name']}：[Country.MakeScope.GetVariable('hbe_af_round_credit_{pid}').GetValue|2]"
    put('in_game/common/customizable_localization/hbe_af_contribution_custom.txt', custom)
    loc['HBE_AF_BLANK'] = ''
    loc['HBE_AF_MEMBER_CONTRIBUTION_TT'] = "#T [Country.GetName]·本届贡献#!\\n席面出资：[Country.MakeScope.ScriptValue('hbe_af_feast_funding')|2]\\n地方事业：[Country.MakeScope.ScriptValue('hbe_af_feast_projects')|2] / 2.00[Country.Custom('hbe_af_feast_prior_text')]\\n合计：[Country.MakeScope.GetVariable('hbe_feast_points').GetValue|2][Country.Custom('hbe_af_feast_last_text')]"
    loc['HBE_AF_MEMBER_CONTRIBUTION_TT'] = loc['HBE_AF_MEMBER_CONTRIBUTION_TT'].replace("[Country.Custom('hbe_af_feast_prior_text')]", ''.join(f"[Country.Custom('hbe_af_feast_detail_{p['id']}')]" for p in projects)+"[Country.Custom('hbe_af_feast_prior_text')]")
    loc['HBE_AF_MEMBER_PRIOR'] = "\\n此前已记贡献：[Country.MakeScope.ScriptValue('hbe_af_feast_prior')|2]"
    loc['HBE_AF_MEMBER_LAST'] = "\\n\\n最近：[Country.Custom('hbe_af_feast_last_name')] +[Country.MakeScope.ScriptValue('hbe_af_feast_last')|2]"

    replacements = {
        'HBE_FEAST_GUIDE': '出资记1分；地方事业完工按投入与成果记分，每届至多2分。\\n每两年结算。悬浮成员可查看贡献明细。',
        'HBE_FEAST_ACTION_HELP': '出资每届一次；换派有五年间隔。悬浮按钮查看条件。',
        'game_concept_hbe_term_local_service_desc': '地方事业在右下角专用面板筹办，每轮从全国、地方两张候选中选一项。完工自动结算成果，并按投入、工期和实际成果计入本届贡献，每届至多2分；开工、撤办与候选过期不加分。',
    }
    for path in (out/'main_menu/localization').rglob('hbe_l_*.yml'):
        text = path.read_text(encoding='utf-8-sig')
        lines = []
        for line in text.splitlines():
            match = re.match(r'\s*([^:]+):', line)
            key = match[1] if match else ''
            if key in replacements:
                line = ' '+key+': "'+replacements[key]+'"'
            for name in ('hbe_feast_points','hbe_feast_total','hbe_party_points','hbe_contribution'):
                line = line.replace("GetVariable('"+name+"').GetValue|0", "GetVariable('"+name+"').GetValue|2")
            if key == 'HBE_FEAST_TOTAL_DISPLAY': line = line.replace('$VALUE|0$', '$VALUE|2$')
            if key == 'hbe_banquet.7.desc':
                line = re.sub(r'出资记1贡献，.*?每届各限一次。', replacements['HBE_FEAST_GUIDE'].split('\\n')[0], line)
            if key == 'game_concept_hbe_term_feast_dividend_desc':
                line = line.replace('分配权重为ln(1＋本届贡献)：', '分配权重按ln(1＋本届贡献)的分段线性近似连续计算（3分封顶）：')
            lines.append(line)
        write_preserving_format(path, '\n'.join(lines)+'\n')
