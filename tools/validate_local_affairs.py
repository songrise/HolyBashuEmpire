"""Checks specific invariants of the local-affairs MVP, not a visual test."""
import json
import math
import re

from pdxscript import blocks
from build_local_affairs import COUNTERS


def implied_basis(scripts, basis):
    """Return 'file:basis trigger' for every basis gate its own block already satisfies.

    `scripts` is an iterable of (name, text); `basis` maps a basis trigger to the
    operating-building triggers that make up its OR.
    """
    hits = []
    for name, text in scripts:
        if 'hbe_af_basis_' not in text:
            continue
        spans = sorted(((a, b) for _, _, a, b, _ in blocks(text)), key=lambda s: s[1] - s[0])
        for m in re.finditer(r'hbe_af_basis_(\w+) = yes', text):
            gate = 'hbe_af_basis_' + m.group(1)
            ops = basis.get(gate)
            if not ops:
                continue
            for a, b in spans:
                if a <= m.start() and m.end() <= b:
                    if any(op + ' = yes' in text[a:b] for op in ops):
                        hits.append(f'{name}:{gate}')
                    break
    return hits


def validate(mod, root, game, manifest, check):
    if 'local_affairs' not in manifest:
        return
    data = json.loads((root / 'data/local_affairs_projects.json').read_text(encoding='utf-8'))
    count = len(data['projects'])
    def read(path):
        return (mod / path).read_text(encoding='utf-8-sig')
    effects = read('in_game/common/scripted_effects/hbe_af_effects.txt')
    triggers = read('in_game/common/scripted_triggers/hbe_af_triggers.txt')
    gui = read('in_game/gui/hbe_local_affairs.gui')
    host = read('in_game/gui/ingame_topbar.gui')
    vanilla_host = (game/'in_game/gui/ingame_topbar.gui').read_text(encoding='utf-8-sig')
    mount = '\n\t# HBE: mount the independent affairs panel, not the situation panel.\n\thbe_af_overlay = {}\n'
    check('affairs GUI type has exactly one live HUD instance','type hbe_af_overlay = widget' in gui and host.count('hbe_af_overlay = {}') == 1)
    check('affairs HUD override only wraps the native alert row and adds its mount',host.replace(mount,'',1).replace('hbox = { # HBE affairs alert row\n using = layoutpolicy_expanding ignoreinvisible = yes hbe_af_alert = {}\n','',1).replace('\n} # HBE affairs alert row end','',1)==vanilla_host)
    check('affairs entry is anchored to screen bottom right',bool(re.search(r'parentanchor = bottom\|right\s+widgetanchor = bottom\|right\s+position = \{ -24 -96 \}',gui)))
    sguis = read('in_game/common/scripted_guis/hbe_af_gui.txt')
    check('affairs one window for ready running and waiting',gui.count('window = { name = "hbe_af_window"') == 1 and 'hbe_af_wait_window' not in gui and 'hbe_af_running_window' not in gui)
    check('affairs visibility does not read a valueless country flag','hbe_af_open' not in gui and 'hbe_af_ui_toggle' not in gui and 'hbe_af_ui_toggle' not in sguis)
    loc = read('main_menu/localization/simp_chinese/hbe_af_l_simp_chinese.yml')
    auto_gui = read('in_game/gui/hbe_local_affairs_automation.gui')
    feast_gui=read('in_game/gui/panels/situation/hbe_banquet.gui')
    base_gui=(root/'assets/gui/hbe_banquet.gui').read_text(encoding='utf-8-sig')
    normalize=lambda s: re.sub(r'\s+', ' ',s).strip()
    check('affairs keeps situation layout with only authorized row accounting changes',all(normalize(feast_gui.split('blockoverride "'+name+'"')[1].split('blockoverride')[0])==normalize(base_gui.split('blockoverride "'+name+'"')[1].split('blockoverride')[0]) for name in ('situation_header_left','situation_header_right','situation_panel_main_actions')) and feast_gui.count('tooltip = "HBE_AF_MEMBER_CONTRIBUTION_TT"')==4)
    contribution=read('in_game/common/scripted_effects/hbe_af_contribution_effects.txt')
    contribution_values=read('in_game/common/script_values/hbe_af_contribution_values.txt')
    check('affairs credits completion once before immutable receipt',effects.count('hbe_af_record_contribution = yes hbe_af_receipt_')==count*2 and 'is_situation_active = situation:hbe_banquet' in contribution and 'hbe_feast_recount = yes' in contribution)
    check('affairs round contribution cap is shared with prior service credit','subtract = var:hbe_feast_points add = hbe_af_feast_funding min = 0 max = 2' in contribution_values and 'NOT = { has_variable = hbe_af_credit_recorded }' in contribution)
    check('affairs credit uses realized rewards and net cost','divide = var:hbe_af_nominal' in effects and 'hbe_af_credit_net_cost' in effects and 'hbe_af_credit_economic' in effects)
    check('affairs member scores display fractions without deprecated source',feast_gui.count("GetVariable('hbe_feast_points').GetValue|2")==2 and '此前已记贡献' in loc and '旧版履约' not in loc)
    check('affairs dividends use continuous fractional weights',read('in_game/common/scripted_effects/hbe_feast_dividend_effects.txt').count('value = hbe_af_feast_dividend_weight')==2 and all(x in contribution_values for x in ('multiply = 0.69315','multiply = 0.40546','multiply = 0.28768')))
    check('affairs contribution has its own deduplication guard','NOT = { has_variable = hbe_af_credit_recorded }' in contribution and 'remove_variable = hbe_af_credit_recorded' in effects)
    check('affairs member hover itemizes every credited project',all('hbe_af_round_credit_'+str(p['id']) in contribution and 'HBE_AF_MEMBER_PROJECT_'+str(p['id'])+':' in loc for p in data['projects']))
    check('affairs automation keeps rules in hover and compact state only','text = "HBE_AF_AUTO_RULES"' not in auto_gui and 'tooltip = "HBE_AF_AUTO_RULES"' in auto_gui and 'size = { -1 42 }' in auto_gui)
    check('affairs twenty definitions retain six distinct guild roles',count == 20 and sum(p['pool']=='national' for p in data['projects'])==10 and sum(p['pool']=='local' for p in data['projects'])==10)
    check('affairs guarded selections for both tiers',sum(k.startswith('hbe_af_choose_') for k,*_ in blocks(sguis,0)) == count*2 and triggers.count('hbe_af_idle = yes var:') == count*2)
    check('affairs large investment uses its boolean permission for all projects',all('modifier:hbe_af_allow_large_investment = yes' in triggers[a:b] and 'has_advance = hbe_tech_common_2' not in triggers[a:b] for k,_,a,b,_ in blocks(triggers,0) if k.startswith('hbe_af_can_') and k.endswith('_large')))
    check('affairs persistent draws not GUI randomization','random_list' not in gui and effects.count('random_list =') >= 5 and 'hbe_af_wait_left value = 3' in effects)
    spending_projects=sum(not any(row['type']=='burden' for row in p['rewards']) for p in data['projects'])
    check('affairs auto checks budgets and caps burden-increasing projects',effects.count('add = var:hbe_af_reserve') == count*2 and effects.count('var:hbe_af_budget subtract') == count*2 and effects.count('var:hbe_af_limit subtract') == spending_projects*2)
    relief_ids={p['id'] for p in data['projects'] if any(row['type']=='burden' for row in p['rewards'])}
    check('zero-load relief remains available above burden caps',all('value = 70 subtract' not in triggers[a:b] for k,_,a,b,_ in blocks(triggers,0) if k in {f'hbe_af_can_{pid}_{tier}' for pid in relief_ids for tier in ('small','large')}))
    ai_rules = data['ai_participation']['personalities']
    effect_defs = {k: effects[a:b] for k, _, a, b, _ in blocks(effects, 0)}
    ai = effect_defs['hbe_af_ai_consider']
    check('affairs AI two persistent equally weighted personalities use 70 and 40 percent',
          [(p['id'], p['weight'], p['chance']) for p in ai_rules] == [(1, 50, 70), (2, 50, 40)]
          and 'NOT = { has_variable = hbe_af_ai_personality }' in ai
          and all(f"chance = {p['chance']} hbe_af_auto_start = yes" in ai for p in ai_rules))
    check('affairs AI rolls only for a scored affordable idle peaceful choice',
          'is_ai = yes hbe_af_idle = yes NOT = { at_war = yes } var:hbe_af_choice > 0 var:hbe_af_best >= 7' in ai
          and effect_defs['hbe_af_auto_choose'].index('add = var:hbe_af_reserve') < effect_defs['hbe_af_auto_choose'].index('hbe_af_ai_consider = yes'))
    check('affairs AI consumes one decision per calendar month including refusal',
          'value = current_year multiply = 12 add = current_month' in ai
          and 'NOT = { var:hbe_af_ai_last_month = var:hbe_af_ai_current_month }' in ai
          and ai.index('name = hbe_af_ai_last_month value = var:hbe_af_ai_current_month') < ai.index('random_list =')
          and 'remove_variable = hbe_af_ai_last_month' not in effects)
    check('affairs player automation bypasses personality dice and all starts recheck eligibility',
          'if = { limit = { is_ai = yes } hbe_af_ai_consider = yes } else = { hbe_af_auto_start = yes }' in effect_defs['hbe_af_auto_choose']
          and all(f'hbe_af_start_{p["id"]}_{t["key"]} = yes' in effect_defs['hbe_af_auto_start'] for p in data['projects'] for t in data['tiers']))
    check('affairs monthly progress bounded and paused on lost control','divide = var:hbe_af_months max = 1' in effects and 'hbe_af_target_owned = yes' in effects and 'var:hbe_af_pause >= 12' in effects)
    reward_blocks={k:effects[a:b] for k,_,a,b,_ in blocks(effects,0) if k.startswith('hbe_af_reward_5_')}
    check('affairs population and building use native outcomes','add_pop = {' in effects and len(reward_blocks)==2 and all('change_building_level_in_location' in b and 'can_build_building' in b and 'location_building_level' in b for b in reward_blocks.values()))
    check('affairs fixed compact dual cards and all guarded choices','size = { 840 628 }' in gui and 'size = { 376 420 }' in gui and gui.count('using = hbe_af_card_surface') == 2 and gui.count('hbe_af_choose_') == count*4)
    check('affairs tall rewards and two masked illustrated headers',gui.count('size = { 344 138 }') == count*2+2 and gui.count('name = "hbe_af_illustrated_header"') == 2 and gui.count('mask_fade_vertical.dds') == 2 and gui.count('mask_fade_horizontal_right.dds') == 2)
    check('affairs cards leave padding and only local card has a refresh button',all(x in gui for x in ('position = { 32 124 }', 'position = { 432 124 }', 'position = { 326 12 } size = { 36 36 }')) and gui.count('name = "hbe_af_refresh_reserved"') == 1 and gui.count('name = "hbe_af_refresh_local"') == 1)
    check('affairs panel initializes old saves before opening',"onclick = \"[GetScriptedGui('hbe_af_ui_panel_open').Execute" in gui and 'hbe_af_initialize = yes set_variable = hbe_af_panel_visible' in sguis)
    check('affairs uses treasury rather than monthly balance',"GetCurrencyValue('gold')" in loc and "GetCurrencyBalance('gold')" not in loc)
    auto_gui=read('in_game/gui/hbe_local_affairs_automation.gui')
    auto_host=read('in_game/gui/automation_lateralview.gui')
    auto_native=(game/'in_game/gui/automation_lateralview.gui').read_text(encoding='utf-8-sig')
    auto_mount='\n\t\t\t\t\t\t\t# HBE: script-backed economy automation entry.\n\t\t\t\t\t\t\thbe_af_automation_card = {}\n'
    check('affairs automation host only adds one economy entry',auto_host.count('hbe_af_automation_card = {}') == 1 and auto_host.replace(auto_mount,'',1) == auto_native)
    check('affairs automation uses native economy filter and controls',all(s in auto_gui for s in ('= AutomationCard', 'AutomationCheckbox =', 'checkbox_square_alt =', "SearchBar.IsFilterEnabledByKey('automation_filter_economy')")))
    check('affairs automation explicitly supplies native search context','datacontext = "[FilteredSortedList.GetSearchBar]"' in auto_gui)
    check('affairs native circular refresh remains inside dual-card window',all(x in gui for x in ('piechart =', 'using = piechart_angles', 'pie_chart_blue_progress.dds', 'hbe_af_wait_progress')))
    check('affairs global investment preview changes both cards',gui.count("Toggle('hbe_af_preview_large')") == 2 and gui.count('text = "hbe_af_costline_') == count*2)
    check('affairs active card shows paid cost date and remaining months',all(x in gui for x in ('bg_selected_law_frame','text = "HBE_AF_PAID"','text = "HBE_AF_ETA"')) and "ScriptValue('hbe_af_remaining')" in loc and 'subtract = var:hbe_af_elapsed min = 0' in read('in_game/common/script_values/hbe_af_values.txt'))
    check('affairs availability mounts a native top ribbon',host.count('hbe_af_alert = {}') == 1 and all(x in gui for x in ('using = alert_banner_setup','using = green_alert',"hbe_af_ui_available")))
    check('affairs outcomes locked once at guarded start',effects.count('hbe_af_roll_outcome = yes') == count*2 and effects.count('hbe_af_factor value = ') == 4)
    receipts=read('in_game/events/hbe_af_results.txt')
    expected_receipts=count*2+sum(bool(p.get('guild_role')) for p in data['projects'])*8
    check('affairs completion receipts include immutable specialized guild variants',sum(k.startswith('hbe_af_result.') for k,*_ in blocks(receipts,0))==expected_receipts and 'add_gold' not in receipts and 'add_pop' not in receipts)
    check('affairs receipts snapshot actual gains before clearing active project','save_scope_value_as = { name = af_actual' in effects and 'save_scope_as = af_location' in effects and 'hbe_af_receipt_4 = yes' in effects)
    check('affairs settlement is guarded against duplicate completion','hbe_af_complete = { if = { limit = { has_variable = hbe_af_active }' in effects)
    check('affairs target loss still pauses and dates update','hbe_af_update_eta = yes' in effects and 'hbe_af_target_owned = yes' in effects)
    check('affairs main panel only has a status cog, with right-click toggle','AutomationCheckbox =' in gui and 'click_type = right' in gui and 'OpenLateralView' not in gui and 'HBE_AF_SETTING_' not in gui)
    check('affairs auto respects national local and large preferences',all(effects.count('has_variable = hbe_af_no_'+pool)==sum(p['pool']==pool for p in data['projects'])*len(data['tiers']) for pool in ('national','local')) and effects.count('has_variable = hbe_af_no_large') == count)
    check('affairs descriptive grades use explicit vanilla colors',all(x in loc for x in ('#color_light_gray 少量','#color_green 中量','#color_yellow 大量')))
    check('affairs outcome weights and greatness are bounded',sum(x['weight'] for x in data['outcomes'])==100 and data['outcomes'][-1]['great_success'] and data['outcomes'][-1]['factor']==1.5)
    main_window=next(gui[a:b] for k,_,a,b,_ in blocks(gui) if k=='window' and 'name = "hbe_af_window"' in gui[a:b])
    check('affairs project cards keep ETA rather than a progress meter','progressbar =' not in main_window and 'HBE_AF_PROGRESS_SHORT' not in main_window and 'hbe_af_progress' not in main_window)
    check('affairs project titles have distinct visual hierarchy','fontsize = 22' in gui and 'fontsize = 16' in gui and 'text = "HBE_AF_PICK_HINT"' not in gui)
    check('affairs event modifiers expose native description keys',all('STATIC_MODIFIER_DESC_hbe_af_'+k+':' in loc and 'hbe_af_'+k+'_desc:' in loc for k in ('fair','materials','food_small','food_large')))
    check('affairs title status and panel use the same center','size = { 840 42 }' in gui and 'size = { 840 32 } autoresize = no align = center' in gui and 'blockoverride "header_text_object" { widget = { size = { 0 0 } } }' in gui and 'position = { 32 53 } size = { 776 30 }' in gui and 'position = { 0 0 } parentanchor = center' in gui)
    check('affairs time uses the native clock icon','gfx/interface/icons/text_icons/time.dds' in gui and 'position = { 58 349 }' in gui)
    check('affairs only two pool header textures',all((mod/'main_menu/gfx/interface/hbe/local_affairs'/f'{pool}_header.dds').read_bytes()[84:88] == b'DXT5' for pool in ('national','local')))
    check('affairs manual skip removed and auto preserves current offers','hbe_af_ui_reroll' not in gui+sguis and 'hbe_af_reroll' not in effects)
    check('affairs every candidate has a bounded persisted random expiry',all('value = '+str(n)+' }' in effects for n in range(12,25)) and all('hbe_af_reset_'+pool+'_expiry = yes' in effects for pool in ('national','local')) and 'hbe_af_tick_offers = { if = { limit = { hbe_af_idle = yes }' in effects)
    check('affairs expiry labels sit below both cards',all('HBE_AF_EXPIRY_'+pool in gui+loc for pool in ('NATIONAL','LOCAL')) and 'position = { 32 550 }' in gui and 'position = { 432 550 }' in gui)
    check('affairs panel opening uses idempotent current initialization','hbe_af_initialize = yes' in sguis and 'hbe_af_migrate_' not in effects+sguis)
    check('affairs all projects have two to four reward types',all(2 <= len(p['rewards']) <= 4 for p in data['projects']))
    previews=[line for line in loc.splitlines() if line.strip().startswith(('hbe_af_exact_', 'hbe_af_reward_text_','hbe_af_tier_'))]
    check('affairs preview hides great success amounts and removes probability lecture','HBE_AF_ROLL_TT' not in loc and all('大成功' not in line and '普通成果' not in line for line in previews))
    check('affairs no project both charges and reduces burden',all(not any(x['type']=='burden' for x in p['rewards']) or p['burden']==[0,0] for p in data['projects']))
    check('affairs primary secondary and minor grades differ in both tiers',all(len({b['grades'][i] for b in p['benefits']})>1 for p in data['projects'] for i in range(2)))
    check('affairs independent random rewards are locked on project start',all(effects.count('hbe_af_roll_rewards_'+str(p['id'])+' = yes')==2 for p in data['projects']) and all('hbe_af_factor_'+str(j) in effects for j in range(4)))
    manpower_rewards=[(p,r) for p in data['projects'] for r in p['rewards'] if r['type']=='manpower']
    check('affairs real population remains distinct from conservative manpower',len(manpower_rewards)==1 and all(r['role']=='minor' and r.get('basis')=='monthly_manpower' and max(r['amount'])<=0.1 for p,r in manpower_rewards) and sum(r['type']=='population' for p in data['projects'] for r in p['rewards'])>=5 and 'add_pop = {' in effects and '兵员储备' in loc)
    check('affairs manpower has no fixed headcount floor and caps apply after random factor',data['manpower_limits']=={'monthly_recovery':0.2,'capacity_fraction':0.002} and 'multiply = var:hbe_af_effective_factor max = { value = monthly_manpower multiply = 0.2 } max = { value = max_manpower multiply = 0.002 } min = 0' in effects)
    check('affairs all population and native currency rewards use their declared bases',all(row.get('basis') in {'target_population','monthly_manpower','prestige_weak_bonus','stability_weak_bonus','research_progress_weak_bonus','army_tradition_weak_bonus'} for p in data['projects'] for row in p['rewards'] if row['type'] in {'population','manpower','prestige','stability','research','army_tradition'}) and 'value = var:hbe_af_target.population multiply =' in effects)
    check('affairs resource hover values are live and hide implementation details','GetPlayer.MakeScope.ScriptValue(\'hbe_af_preview_' in loc and '原版小额奖励' not in loc and (mod/'in_game/common/script_values/hbe_af_reward_values.txt').is_file())
    check('affairs four additional native resource rewards have measured deltas',all('add_'+kind+' = var:hbe_af_actual_' in effects for kind in ('prestige','stability','manpower','army_tradition')) and 'subtract = var:hbe_af_resource_before min = 0' in effects)
    check('affairs each component has its own ordinary range',all(0 < row['ordinary_factors'][0] <= 1 <= row['ordinary_factors'][1] < min(data['great_reward_factors']) for p in data['projects'] for row in p['rewards'] if row['type'] not in ('courtier','patronage')))
    check('affairs shared cost multipliers match latest balance',data['gold_cost_multiplier']==2.5 and data['gold_economic_multiplier']==0.7 and data['burden_cost_multiplier']==1.8)
    generated_values=read('in_game/common/script_values/hbe_af_values.txt')
    numeric_ok=True
    for project in data['projects']:
        for i,tier in enumerate(data['tiers']):
            key=str(project['id'])+'_'+tier['key']
            cost=project['cost']*tier['cost_multiplier']*data['gold_economic_multiplier']
            minimum=project['cost']*tier['cost_multiplier']*data['gold_cost_multiplier']
            load=math.ceil(project['burden'][i]*1.8)
            numeric_ok &= f'hbe_af_cost_{key} = {{ value = hbe_event_economic_base multiply = {cost:g} min = {minimum:g} }}' in generated_values
            numeric_ok &= f'hbe_af_load_{key} = {{ value = {load:g} ' in generated_values
    check('affairs every generated cost and burden applies the shared multipliers',numeric_ok)
    check('affairs fallback plus cash rewards cannot exceed paid cost','value = var:hbe_af_fallback_gold max = { value = var:hbe_af_paid' in effects)

    check('affairs relief requires burden above fifty and has lower draw weight',all('var:hbe_burden > 50' in triggers[a:b] for k,_,a,b,_ in blocks(triggers,0) if k in {'hbe_af_eligible_'+str(p['id']) for p in data['projects'] if p.get('relief_weight')}) and 'factor = 2 var:hbe_burden >= 40' not in effects and data['relief_draw']['weight']==70)
    check('affairs native research road and varied buildings supported','add_research_progress = var:hbe_af_actual_' in effects and 'add_road_to =' in effects and all('building = building_type:'+b in effects for b in ('granary','marketplace','temple','library')))
    check('affairs targets prefer suitable workers and infrastructure',all(x in effects for x in ('population >= 20 NOT = { hbe_af_short_workers = yes }','hbe_af_short_workers = yes','random_neighbor_location','is_connected_to = prev')) and 'building_employed_amount < 0.05' in triggers)
    check('affairs modifier names and descriptions are complete',all('STATIC_MODIFIER_DESC_hbe_af_'+key+':' in loc and 'STATIC_MODIFIER_NAME_hbe_af_'+key+':' in loc for key in data['modifiers']))
    notice_sguis=read('in_game/common/scripted_guis/hbe_af_notice_settings.txt')
    check('affairs all scripted GUI references exist',set(re.findall(r"GetScriptedGui\('([^']+)'\)",gui+auto_gui)) <= {k for k,*_ in blocks(sguis+notice_sguis,0)})
    for p in data['projects']:
        check('affairs localized complete card '+p['key'],all('hbe_af_tier_'+str(p['id'])+'_'+t['key']+':' in loc for t in data['tiers']))
    scripts='\n'.join(read(p.relative_to(mod).as_posix()) for p in (mod/'in_game').rglob('*.txt'))
    for c in COUNTERS:
        check('retired balance never read or awarded '+c,not re.search(r'(?:var:|has_variable\s*=\s*)'+c+r'\b|name\s*=\s*'+c+r'\b',scripts))
    decisions=read('in_game/common/decisions/hbe_decisions.txt')
    check('seven old service decisions retired',all('potential = { always = no }' in decisions[a:b] for k,_,a,b,_ in blocks(decisions,0) if k.startswith('hbe_service_')))
    civic_decisions=read('in_game/common/decisions/hbe_civic_decisions.txt')
    coordinates=[civic_decisions[a:b] for k,_,a,b,_ in blocks(civic_decisions,0) if k.startswith('hbe_coordinate_')]
    check('seven regional coordination decisions are temporarily hidden',not coordinates)
    check('retired service dependencies are removed outright',not re.search(r'\bhas_variable\s*=\s*(?:hbe_recent_delivery_\w+|hbe_service_cooldown)\b',scripts))
    check('retired pending orders cannot finish or trigger rewards',not re.search(r'\bhas_variable\s*=\s*(?:hbe_service_\w+_pending|hbe_project_pending)\b',scripts) and not re.search(r'\bhbe_(?:record|pay)_service_\w+\s*=',scripts))
    old_callbacks={}
    for rel in ('hbe_banquet_effects.txt','hbe_simple_banquet_effects.txt'):
        text=read('in_game/common/scripted_effects/'+rel)
        old_callbacks.update({k:text[a:b].strip() for k,_,a,b,_ in blocks(text,0) if k in ('hbe_feast_help','hbe_deliver_contract')})
    check('retired callbacks only perform marker cleanup',not old_callbacks)
    check('legacy country migration state is no longer registered',not (mod/'in_game/common/scripted_effects/hbe_af_legacy_effects.txt').exists() and 'hbe_af_retire_legacy_country' not in effects)
    base_loc=read('main_menu/localization/simp_chinese/hbe_l_simp_chinese.yml')
    mission_lines=[line for line in base_loc.splitlines() if line.strip().startswith('hbe_mission_')]
    check('regional mission descriptions no longer charge retired resources',all(not re.search(r'@hbe_(?:water|salt|river|roads|grain|tea|valleys)!',line) for line in mission_lines) and '役负投入降低50%' in base_loc)
    from validate_local_affairs_research import validate as validate_research
    validate_research(mod, root, game, manifest, check)
    from build_local_affairs_guilds import validate as validate_guilds
    validate_guilds(mod,root,check)
    from build_civic_teahouse import validate as validate_teahouse
    validate_teahouse(mod,root,manifest,check)
    from build_local_affairs_notices import validate as validate_notices
    validate_notices(mod,game,check)
    from build_local_affairs_people import validate as validate_people
    validate_people(mod,game,data,check)
    from build_local_affairs_hud import ICONS, COLORS
    entry=next(gui[a:b] for k,_,a,b,_ in blocks(gui) if k=='widget' and 'name = "hbe_af_hud_entry"' in gui[a:b])
    check('affairs one circular 64px HUD entry replaces old text button',gui.count('name = "hbe_af_hud_entry"')==1 and 'size = { 64 64 }' in entry and 'text = "HBE_AF_OPEN"' not in gui)
    check('affairs HUD follows native research circle and cultural frame',all(s in entry for s in ('circle_background.dds','circle_progress_bg.dds',"GetGraphicalCultureTexture('circle_frame')",'size = { 89% 89% }','size = { 65% 65% }')))
    check('affairs HUD has three independently painted state icons',all(entry.count('name = "hbe_af_hud_icon_'+state+'"')==1 and texture in entry and (mod/'main_menu'/texture).is_file() for state,texture in ICONS.items()) and len({(mod/'main_menu'/texture).read_bytes() for texture in ICONS.values()})==3)
    check('affairs HUD uses muted slate moss and cinnabar state backplates',all('name = "hbe_af_hud_tint_'+state+'"' in entry and 'color = { '+' '.join(f'{n:g}' for n in color)+' 1 }' in entry for state,color in COLORS.items()) and len(set(COLORS.values()))==3)
    from PIL import Image
    from build_icon_assets import fit
    for state,texture in ICONS.items():
        with Image.open(root/f'assets/local_affairs_hud_v2/{state}.png') as source:
            sprite=fit(source,128)
            raw=(mod/'main_menu'/texture).read_bytes()
            check('affairs '+state+' HUD transparent 128px art exports exactly',source.mode=='RGBA' and source.getchannel('A').getextrema()==(0,255) and raw[128:]==sprite.tobytes('raw','BGRA'))
    gui_defs={k:sguis[a:b] for k,_,a,b,_ in blocks(sguis,0)}
    check('affairs HUD idle icon also covers cancellation wait','NOT = { has_variable = hbe_af_active }' in gui_defs['hbe_af_ui_hud_idle'])
    for pool in ('local','national'):
        ids=set(re.findall(r'var:hbe_af_active = (\d+)',gui_defs['hbe_af_ui_hud_'+pool]))
        check('affairs HUD '+pool+' state covers exactly its catalogue projects',ids=={str(p['id']) for p in data['projects'] if p['pool']==pool})
    check('affairs HUD ring uses running progress with transparent remainder',"GetVariable('hbe_af_progress').GetValue" in entry and 'hbe_af_ui_running' in entry and 'color = { 1 1 1 0 }' in entry and entry.count('piechart =')==2)
    check('affairs HUD wait ring is separate from construction',"GetVariable('hbe_af_wait_progress').GetValue" in entry and 'hbe_af_ui_waiting' in entry and 'Not(GetScriptedGui(\'hbe_af_ui_running\')' in entry)
    check('affairs HUD decoration cannot intercept clicks',entry.count('alwaystransparent = yes')==12 and 'filter_mouse = none' in entry and "GetScriptedGui('hbe_af_ui_panel_open').Execute" in entry)
    check('affairs HUD uses native separate hit surface and explicit open action','button_regular = { name = "hbe_af_hud_hitbox"' in entry and entry.count('onclick =')==1 and 'on_action =' not in entry)
    check('affairs window and close button read same explicit boolean marker','has_variable = hbe_af_panel_visible' in sguis and 'remove_variable = hbe_af_panel_visible' in sguis and "GetScriptedGui('hbe_af_ui_panel_visible').IsShown" in gui and "GetScriptedGui('hbe_af_ui_panel_close').Execute" in gui and "GetVariableSystem.Exists('hbe_af_panel_open')" not in gui)
    check('affairs HUD tooltip names actual project and ETA',all(s in loc for s in ('HBE_AF_HUD_TT:',"Player.Custom('hbe_af_active_name')",'$HBE_AF_ETA$','$HBE_AF_PAUSED$')))

    # A retired counter threshold is replaced by hbe_af_basis_<group>, which is
    # `done OR operating building A OR operating building B`. Where the same block
    # already requires A or B the replacement can never fail and the gate is gone.
    basis = {k: set(re.findall(r'hbe_operating_\w+', triggers[a:b]))
             for k, _, a, b, _ in blocks(triggers) if k.startswith('hbe_af_basis_')}
    scripts = [(p.name, p.read_text(encoding='utf-8-sig'))
               for p in sorted((mod/'in_game').rglob('*.txt'))]
    check('no basis gate is satisfied by an operating building in the same block',
          not implied_basis(scripts, basis))
