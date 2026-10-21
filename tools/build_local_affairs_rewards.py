"""Composite, data-driven affair rewards and immutable completion receipts."""
import json
from pathlib import Path


def catalogue():
    return json.loads((Path(__file__).resolve().parents[1]/'data/local_affairs_projects.json').read_text(encoding='utf-8'))


def outcomes():
    return tuple((r['weight'], r['factor']) for r in catalogue()['outcomes'])


def has_reward(p, kind):
    return any(r['type'] == kind for r in p['rewards'])


def building_condition(kind):
    return f'can_build_building = building_type:{kind} owner = {{ can_build_building = building_type:{kind} }} location_building_level = {{ building_type = building_type:{kind} value < 2 }}'


def reward_expression(row, tier, factor='var:hbe_af_effective_factor'):
    """Native bases stay live at settlement; configuration stores only multipliers."""
    basis = row.get('basis')
    value = row.get('amount', [0, 0])[tier]
    if basis == 'target_population':
        calc = f'value = var:hbe_af_target.population multiply = {value:g}'
    elif basis:
        calc = f'value = {basis} multiply = {value:g}'
    else:
        calc = f'value = {value:g}'
    calc += f' multiply = {factor}'
    kind = row['type']
    if kind == 'gold': calc += ' multiply = var:hbe_af_paid'
    if kind == 'burden': calc += ' max = var:hbe_burden'
    if kind == 'manpower':
        caps = catalogue()['manpower_limits']
        calc += f' max = {{ value = monthly_manpower multiply = {caps["monthly_recovery"]:g} }} max = {{ value = max_manpower multiply = {caps["capacity_fraction"]:g} }} min = 0'
    return calc


def reward(p, i):
    result = ['set_variable = { name = hbe_af_fallback_gold value = 0 }', 'set_variable = { name = hbe_af_credit_quality value = 0 }']
    for j, r in enumerate(p['rewards']):
        kind = r['type']; var = f'hbe_af_actual_{j}'
        result.append(f'set_variable = {{ name = {var} value = 0 }}')
        # Capture the no-random nominal reward before effects change the target state.
        basis = r.get('basis')
        nominal = ('var:hbe_af_target.population' if basis == 'target_population' else basis) or str(r.get('amount',[1,1])[i])
        calc = f'value = {nominal}'
        if basis: calc += f' multiply = {r["amount"][i]:g}'
        if kind == 'gold': calc += ' multiply = var:hbe_af_paid'
        if kind == 'modifier': calc = f'value = {r["months"][i]}'
        if kind in ('population','manpower'): calc += ' multiply = 1000'
        result.append(f'set_variable = {{ name = hbe_af_nominal value = {{ {calc} }} }}')

        result.append(f'set_variable = {{ name = hbe_af_effective_factor value = var:hbe_af_factor }} if = {{ limit = {{ has_variable = hbe_af_factor_{j} }} set_variable = {{ name = hbe_af_effective_factor value = var:hbe_af_factor_{j} }} }}')
        if kind in ('burden', 'population', 'research', 'gold', 'prestige', 'stability', 'manpower', 'army_tradition'):
            calc = reward_expression(r, i)
            result.append(f'set_variable = {{ name = {var} value = {{ {calc} }} }}')
            if kind == 'burden': result.append(f'change_variable = {{ name = hbe_burden subtract = var:{var} }} hbe_clamp_burden = yes')
            if kind == 'research': result.append(f'add_research_progress = var:{var}')
            if kind == 'gold': result.append(f'add_gold = var:{var}')
            if kind in ('prestige', 'stability', 'manpower', 'army_tradition'):
                # Measure the native currency delta so capped resources report actual gains.
                result.append(f'set_variable = {{ name = hbe_af_resource_before value = {kind} }} add_{kind} = var:{var} set_variable = {{ name = {var} value = {{ value = {kind} subtract = var:hbe_af_resource_before min = 0 }} }}')
                if kind == 'manpower': result.append(f'change_variable = {{ name = {var} multiply = 1000 }}')

            if kind == 'population':
                result.append(f'var:hbe_af_target = {{ add_pop = {{ culture = root.culture religion = root.religion type = pop_type:peasants size = root.var:{var} }} }} change_variable = {{ name = {var} multiply = 1000 }}')
        elif kind == 'modifier':
            key = r.get('modifier') or r['modifiers'][i]
            scope = catalogue()['modifiers'][key]['scope']
            result.append(f'set_variable = {{ name = {var} value = {{ value = {r["months"][i]} multiply = var:hbe_af_effective_factor floor = yes }} }}')
            eff = f'add_{"country" if scope == "country" else "location"}_modifier = {{ modifier = hbe_af_{key} months = {"root." if scope == "location" else ""}var:{var} mode = replace }}'
            result.append(f'var:hbe_af_target = {{ {eff} }}' if scope == 'location' else eff)
        elif kind == 'building':
            choices = ' '.join(f'100 = {{ trigger = {{ var:hbe_af_target = {{ {building_condition(b)} }} }} var:hbe_af_target = {{ change_building_level_in_location = {{ building = building_type:{b} value = 1 }} }} set_variable = {{ name = {var} value = 1 }} }}' for b in r['choices'])
            result.append('random_list = { '+choices+' }')
            result.append(f'if = {{ limit = {{ var:{var} = 0 }} change_variable = {{ name = hbe_af_fallback_gold add = {{ value = var:hbe_af_paid multiply = 0.75 }} }} }}')
        elif kind == 'road':
            valid = 'exists = var:hbe_af_road_target var:hbe_af_road_target = { owner = root controller = root } var:hbe_af_target = { is_connected_to = root.var:hbe_af_road_target NOT = { has_road_to = root.var:hbe_af_road_target } }'
            result.append(f'if = {{ limit = {{ {valid} }} var:hbe_af_target = {{ add_road_to = {{ target = root.var:hbe_af_road_target type = gravel_road }} }} set_variable = {{ name = {var} value = 1 }} }} else = {{ change_variable = {{ name = hbe_af_fallback_gold add = {{ value = var:hbe_af_paid multiply = 0.35 }} }} }}')
        else: raise ValueError(kind)

        weight = catalogue()['contribution']['role_weights'][r['role']]
        result.append(f'if = {{ limit = {{ var:hbe_af_nominal > 0 }} change_variable = {{ name = hbe_af_credit_quality add = {{ value = var:{var} divide = var:hbe_af_nominal min = 0 max = {catalogue()["contribution"]["quality_cap"]:g} multiply = {weight:g} }} }} }}')
    total_weight = sum(catalogue()['contribution']['role_weights'][row['role']] for row in p['rewards'])
    result.append(f'change_variable = {{ name = hbe_af_credit_quality divide = {total_weight:g} }}')
    gold_rows = ' '.join('subtract = var:hbe_af_actual_'+str(j) for j,r in enumerate(p['rewards']) if r['type']=='gold')
    result.append('set_variable = { name = hbe_af_fallback_gold value = { value = var:hbe_af_fallback_gold max = { value = var:hbe_af_paid '+gold_rows+' min = 0 } } }')
    result.append('add_gold = var:hbe_af_fallback_gold')
    result.append('set_variable = { name = hbe_af_credit_net_cost value = { value = var:hbe_af_paid subtract = var:hbe_af_fallback_gold '+gold_rows+' min = 0 } }')
    return '\n'.join(result)


def preview(p, i):
    # Deliberately expose only the ordinary range, never the great-success amount.
    lines=[]
    for j,r in enumerate(p['rewards']):
        kind=r['type']; base=r.get('amount', [0,0])[i]; low,high=r['ordinary_factors']
        def displayed(edge):
            key=f'hbe_af_preview_{p["id"]}_{i}_{j}_{edge}'
            return f"[GetPlayer.MakeScope.ScriptValue('{key}')|2]"
        if kind=='burden': lines.append(f'降低役负 {base*low:g}—{base*high:g}（以现有役负为限）。')
        elif kind=='research': lines.append(f'研究进度 +{displayed("low")}—{displayed("high")} 点。')
        elif kind in ('prestige','stability','army_tradition'):
            label={'prestige':'威望','stability':'稳定度','army_tradition':'陆军传统'}[kind]
            lines.append(f'{label} +{displayed("low")}—{displayed("high")} 点。')
        elif kind=='manpower':
            lines.append(f'兵员储备约 +{displayed("low")}—{displayed("high")} 人，随月度人力恢复量调整。')

        elif kind=='gold': lines.append(f'金币回收为已付费用的 {base*low*100:g}%—{base*high*100:g}%。')
        elif kind=='population': lines.append(f'增加相当于目标地点人口 {base*low*100:g}%—{base*high*100:g}% 的本国文化、国教农民。')
        elif kind=='modifier':
            key=r.get('modifier') or r['modifiers'][i]
            lines.append(catalogue()['modifiers'][key]['summary']+f'，持续 {int(r["months"][i]*low)}—{int(r["months"][i]*high)} 个月。')
        elif kind=='building':
            names={'granary':'粮仓','marketplace':'集市','temple':'庙宇','library':'图书馆'}
            lines.append('合格公共建筑随机 +1 级（'+'／'.join(names[b] for b in r['choices'])+'）；资格改变时返还75%已付金币。')
        elif kind=='road': lines.append('接通目标与一处直属相邻地点的碎石道路；已通路或条件改变时返还35%已付金币。')
    return '\\n'.join(lines)


def build(put, loc, projects):
    choices=' '.join(f'{weight} = {{ set_variable = {{ name = hbe_af_outcome value = {j+1} }} set_variable = {{ name = hbe_af_factor value = {factor} }} }}' for j,(weight,factor) in enumerate(outcomes()))
    effects=['hbe_af_roll_outcome = { random_list = { '+choices+' } }']
    range_values=[]
    for project in projects:
        for j,row in enumerate(project['rewards']):
            if row['type'] not in ('research','prestige','stability','manpower','army_tradition'): continue
            for tier in range(2):
                for edge,factor in zip(('low','high'),row['ordinary_factors']):
                    calc=reward_expression(row,tier,f'{factor:g}')
                    if row['type']=='manpower': calc+=' multiply = 1000'
                    range_values.append(f'hbe_af_preview_{project["id"]}_{tier}_{j}_{edge} = {{ {calc} }}')
    put('in_game/common/script_values/hbe_af_reward_values.txt','\n'.join(range_values))

    events=['namespace = hbe_af_result']; loc['hbe_af_result.accept']='验收归档。'
    for project in projects:
        rolls=[]
        for j,item in enumerate(project['rewards']):
            if item['type'] in ('building','road'): continue
            lo,hi=item['ordinary_factors']
            ordinary=[(15,lo),(20,(1+lo)/2),(30,1),(20,(1+hi)/2),(15,hi)]
            great=list(zip((1,2,1),catalogue()['great_reward_factors']))
            def branches(options):
                return ' '.join(f'{w} = {{ set_variable = {{ name = hbe_af_factor_{j} value = {v:g} }} }}' for w,v in options)
            rolls.append('if = { limit = { var:hbe_af_outcome = 4 } random_list = { '+branches(great)+' } } else = { random_list = { '+branches(ordinary)+' } }')
        effects.append('hbe_af_roll_rewards_'+str(project['id'])+' = { '+' '.join(rolls)+' }')

    for p in projects:
        snapshot=['save_scope_value_as = { name = af_contribution value = var:hbe_af_credit_last }']; lines=[]
        for j,r in enumerate(p['rewards']):
            snapshot.append(f'save_scope_value_as = {{ name = af_actual_{j} value = var:hbe_af_actual_{j} }}')
            val=f"[SCOPE.GetValue('af_actual_{j}')|{'0' if r['type'] in ('population','modifier','building','road') else '2'}]"
            kind=r['type']
            if kind=='burden': lines.append(f'役负实际降低 {val} 点。')
            elif kind=='research': lines.append(f'研究进度实际增加 {val} 点。')
            elif kind=='gold': lines.append(f'实际收回 {val} @gold!。')
            elif kind in ('prestige','stability','army_tradition'):
                label={'prestige':'威望','stability':'稳定度','army_tradition':'陆军传统'}[kind]
                lines.append(f'{label}实际增加 {val} 点。')
            elif kind=='manpower': lines.append(f'兵员储备实际增加 {val} 人。')

            elif kind=='population': lines.append(f"[SCOPE.sLocation('af_location').GetName]实际增加 {val} 名本国文化、国教农民。")
            elif kind=='building': lines.append(f"[SCOPE.sLocation('af_location').GetName]合格公共建筑实际增加 {val} 级。")
            elif kind=='road': lines.append(f'实际接通 {val} 段碎石道路。')
            elif kind=='modifier':
                # Per-tier receipt text is selected below; all amounts are immutable scope values.
                lines.append(('MODIFIER',r,j))
        for great in (False,True):
            eid=p['id']*10+int(great); key=f'hbe_af_result.{eid}'
            loc[key+'.title']=p['name']+('：#color_yellow 大成功#!' if great else '：工程验收')
            rows=[]
            for row in lines:
                if isinstance(row,str): rows.append(row)
                else:
                    _,a,j=row; mk=a.get('modifier') or a['modifiers'][0]
                    summary=catalogue()['modifiers'][mk]['summary']
                    if 'modifiers' in a: summary='当地粮食产出增加 '+"[SCOPE.GetValue('af_modifier_strength')|0]%"
                    rows.append(summary+f"，实际持续 [SCOPE.GetValue('af_actual_{j}')|0] 个月。")
            loc[key+'.desc']=('各处交割清楚，实得成果超过原先预计。' if great else '工程已按册验收，实际成果如下。')+'\\n\\n'+'\\n'.join(rows)+"\\n\\n本届贡献实际增加 [SCOPE.GetValue('af_contribution')|2]。\\n条件改变时补退金币：[SCOPE.GetValue('af_fallback_gold')|2] @gold!。"
            events.append(f'{key} = {{ type = country_event outcome = positive title = {key}.title desc = {key}.desc illustration_tags = {{ 1000 = hbe_event_art_civic_council }} option = {{ name = hbe_af_result.accept ai_chance = {{ base = 100 }} }} }}')
        snapshot += ['save_scope_value_as = { name = af_fallback_gold value = var:hbe_af_fallback_gold }','save_scope_value_as = { name = af_modifier_strength value = { value = 6 if = { limit = { var:hbe_af_tier = 2 } add = 2 } } }','if = { limit = { exists = var:hbe_af_target } var:hbe_af_target = { save_scope_as = af_location } }']
        effects.append(f'hbe_af_receipt_{p["id"]} = {{ if = {{ limit = {{ is_ai = no }} '+ ' '.join(snapshot)+f' if = {{ limit = {{ var:hbe_af_outcome = 4 }} trigger_event_non_silently = {{ id = hbe_af_result.{p["id"]*10+1} }} }} else = {{ trigger_event_non_silently = {{ id = hbe_af_result.{p["id"]*10} }} }} }} }}')
    put('in_game/events/hbe_af_results.txt','\n'.join(events))
    return effects
