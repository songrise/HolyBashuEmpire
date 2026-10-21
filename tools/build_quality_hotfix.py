"""Targeted technology registrations and native GUI fixes, without art regeneration."""
import re
from collections import defaultdict
from pdxscript import blocks, apply_edits, tokens, close_index

# Era-two prerequisites come from the unrestricted vanilla renaissance trees.
VANILLA_ANCHORS = {
 'hbe_tech_chengdu_plain_6':'global_clergy_max_literacy_advance',
 'hbe_tech_southern_salt_wine_6':'renaissance_urbanisation',
 'hbe_tech_eastern_river_3':'merchants_and_trade',
 'hbe_tech_northern_shudao_6':'government_size_renaissance',
 'hbe_tech_central_hills_6':'law_making_renaissance',
 'hbe_tech_western_tea_horse_3':'trade_range_advance_age_2',
 'hbe_tech_southwestern_valleys_6':'recruitment_improvements_renaissance',
 'hbe_civic_common_2':'government_size_renaissance',
 'hbe_civic_eastern_river_2':'drill_army_advance',
 'hbe_civic_northern_shudao_2':'supply_depot_advance_age_2_renaissance',
}

def build_quality_hotfix(out,root,loc,put):
    path=out/'in_game/common/situations/hbe_banquet.txt'
    text=path.read_text(encoding='utf-8-sig').replace('current_date >= 1337.10.1','current_date >= 1337.7.1')
    put('in_game/common/situations/hbe_banquet.txt',text)
    from expansion_catalogue import BUILDINGS,UNITS
    groups={b[2] for b in BUILDINGS if b[2]!='common'}
    path=out/'in_game/common/advances/hbe_advances.txt';text=path.read_text(encoding='utf-8-sig');edits=[];layout={}
    for k,_,s,e,_ in blocks(text,0):
        group,index=k.removeprefix('hbe_tech_').rsplit('_',1);i=int(index)
        if group not in groups or i<3:continue
        body=text[s:e]
        body=re.sub(r'\bage\s*=\s*age_[12]_\w+','age = age_2_renaissance',body)
        parent=VANILLA_ANCHORS.get(k,'renaissance_development' if i in (3,6) else f'hbe_tech_{group}_{i-1}')
        body=re.sub(r'(?m)^\s*requires\s*=\s*\w+', '\n    requires = '+parent,body)
        if i in (3,6) and 'has_advance = hbe_tech_'+group+'_2' not in body:
            allow=next(x for x in blocks(body,0) if x[0]=='allow')
            body=apply_edits(body,[(allow[3],allow[3],f' has_advance = hbe_tech_{group}_2 ')])
        if k=='hbe_tech_northern_shudao_6' and 'has_advance = chancery_records' not in body:
            allow=next(x for x in blocks(body,0) if x[0]=='allow');body=apply_edits(body,[(allow[3],allow[3],' has_advance = chancery_records ')])
        edits.append((s,e,body));layout[k]=dict(age='age_2_renaissance',predecessor=parent,logical_predecessor=f'hbe_tech_{group}_{2 if i in (3,6) else i-1}')
    put('in_game/common/advances/hbe_advances.txt',apply_edits(text,edits))
    # Only the red-box 3/4 and 6/7 move; 5/8 were already era two.
    path=out/'in_game/common/unit_types/hbe_civic_units.txt';text=path.read_text(encoding='utf-8-sig');edits=[]
    improved={u[0]:u[5] for u in UNITS if u[-1]}
    for k,_,s,e,_ in blocks(text,0):
        if k not in improved:continue
        body=text[s:e]
        for field in ('combat_power','strength_damage_done','strength_damage_taken','morale_damage_taken','supply_weight'):
            body=re.sub(r'\b'+field+r'\s*=\s*-?[\d.]+','',body)
        body+='\n '+improved[k]+'\n';edits.append((s,e,body))
        base='川江寨兵' if k=='hbe_trained_river' else '关隘轮戍兵'
        extra='基础战斗力1.20（前身1.00），杀伤+8%，士气损失−12%。' if k=='hbe_trained_river' else '基础战斗力1.15（前身1.00），兵力损失−15%，士气损失−8%。'
        loc[k+'_desc']=f'由{base}改编的常备军，训练与驻守不再随短期轮役中断。\n\n'+extra+'编制仍为500人，补给负担+20%。1457年后，完成本圈续约课题及百年验收，并维持招募机构供养后可用；替代原有兵种。'
    put('in_game/common/unit_types/hbe_civic_units.txt',apply_edits(text,edits))
    path=out/'in_game/common/advances/hbe_civic_advances.txt'
    text=path.read_text(encoding='utf-8-sig')
    audit=next(x for x in blocks(text,0) if x[0]=='hbe_civic_common_2')
    body=re.sub(r'\bunlock_(?:building|unit)\s*=\s*hbe_\w+','',text[audit[2]:audit[3]])
    text=apply_edits(text,[(audit[2],audit[3],body)])
    edits=[]
    for k,_,s,e,_ in blocks(text,0):
        if k not in VANILLA_ANCHORS:continue
        body=text[s:e];body=re.sub(r'\brequires\s*=\s*\w+','requires = '+VANILLA_ANCHORS[k],body)
        if k=='hbe_civic_common_2' and 'has_advance = chancery_records' not in body:
            allow=next(x for x in blocks(body,0) if x[0]=='allow');body=apply_edits(body,[(allow[3],allow[3],' has_advance = chancery_records ')])
        if k in ('hbe_civic_eastern_river_2','hbe_civic_northern_shudao_2') and 'has_advance = hbe_civic_common_2' not in body:
            allow=next(x for x in blocks(body,0) if x[0]=='allow')
            body=apply_edits(body,[(allow[3],allow[3],' has_advance = hbe_civic_common_2 ')])
        edits.append((s,e,body))
    put('in_game/common/advances/hbe_civic_advances.txt',apply_edits(text,edits))

    # Native unlock registration stays real, but is granted per signed compact.
    # These seven certificates appear only after signing and cannot be researched.
    grouped=defaultdict(list)
    for key,name,g,*_ in BUILDINGS:
        if g!='common':grouped[g].append('unlock_building = '+key)
    for key,name,g,base,bld,mods,gfx,late in UNITS:
        if not late:grouped[g].append('unlock_unit = '+key)
    advances=[];sync=[]
    for g,unlocks in grouped.items():
        key='hbe_guest_license_'+g
        circle=loc.get('hbe_circle_'+g,g)
        loc[key]=circle+'客籍资格'
        loc[key+'_desc']='本府已承认当地旧约，并取得该圈机构及基础军制的使用资格。营建与招募仍须在该圈土地进行，且必须维持机构供养；这份凭据不授予地区科技的数值加成。'
        advances.append(f'''{key} = {{
 age = age_2_renaissance starting_technology_level = 99 research_cost = 1
 icon = hbe_civic_{g}_1 content_priority = 850
 potential = {{ has_variable = hbe_guest_{g} }}
 allow = {{ always = no }} requires = hbe_civic_common_2
 {' '.join(unlocks)}
}}''')
        sync.append(f'''if = {{ limit = {{ has_variable = hbe_guest_{g} has_advance = hbe_civic_common_2 NOT = {{ has_advance = {key} }} }}
 research_advance = advance_type:{key}
}}''')
    put('in_game/common/advances/hbe_guest_licenses.txt','\n'.join(advances))
    put('in_game/common/scripted_effects/hbe_guest_license_effects.txt','hbe_sync_guest_licenses = {\n'+'\n'.join(sync)+'\n}')
    put('in_game/common/on_action/hbe_guest_license_on_actions.txt','''on_game_start = { on_actions = { hbe_guest_license_start } }
hbe_guest_license_start = { effect = { every_country = { limit = { hbe_is_prince = yes } hbe_sync_guest_licenses = yes } } }
monthly_country_pulse = { on_actions = { hbe_guest_license_monthly } }
hbe_guest_license_monthly = { trigger = { hbe_is_prince = yes } effect = { hbe_sync_guest_licenses = yes } }
''')
    path=out/'in_game/common/decisions/hbe_civic_decisions.txt';text=path.read_text(encoding='utf-8-sig');edits=[]
    for k,_,s,e,_ in blocks(text,0):
        if k in {'hbe_guest_'+g for g in grouped}:
            body=text[s:e]
            # Grant immediately on signing, with a monthly/startup bridge for old saves.
            if 'hbe_sync_guest_licenses = yes' not in body:
                effect=next(x for x in blocks(body) if x[0]=='effect')
                body=apply_edits(body,[(effect[3],effect[3],' hbe_sync_guest_licenses = yes ')])
            edits.append((s,e,body))
    put('in_game/common/decisions/hbe_civic_decisions.txt',apply_edits(text,edits))

    # Only a voluntary, successful switch incurs this opinion change. Migration
    # and normal monthly faction synchronization do not disappoint former allies.
    put('in_game/common/biases/hbe_faction_departure.txt','hbe_left_feast_party = { value = -5 yearly_decay = 1 }')
    loc['hbe_left_feast_party']='离开会盟派系'
    path=out/'in_game/common/scripted_effects/hbe_banquet_effects.txt';text=path.read_text(encoding='utf-8-sig');edits=[]
    for i,old_party in [(1,'hbe_local_party'),(2,'hbe_common_party')]:
        key='hbe_choose_stance_'+str(i);entry=next(x for x in blocks(text,0) if x[0]==key)
        body=f'''if = {{ limit = {{ NOT = {{ var:hbe_stance = {i} }} NOT = {{ has_variable = hbe_stance_cooldown }} }}
 save_scope_as = hbe_party_departing
 if = {{ limit = {{ is_member_of_international_organization = international_organization:{old_party} }} international_organization:{old_party} = {{ every_international_organization_member = {{
  limit = {{ NOT = {{ this = scope:hbe_party_departing }} }}
  add_opinion = {{ modifier = hbe_left_feast_party target = scope:hbe_party_departing }}
 }} }} }}
 set_variable = {{ name = hbe_stance value = {i} }}
 set_variable = {{ name = hbe_stance_cooldown value = yes years = 5 }}
 hbe_feast_sync_party = yes
}}'''
        edits.append((entry[2],entry[3],body))
    put('in_game/common/scripted_effects/hbe_banquet_effects.txt',apply_edits(text,edits))

    # The two guarded operations cap legitimate round contributions at 3.
    # Tabulate ln(1+c), avoiding an unsupported engine logarithm operator.
    put('in_game/common/script_values/hbe_feast_dividend_values.txt','''hbe_feast_imperial_bonus = {
 value = monthly_income_trade_and_tax
 multiply = 0.5
 min = 8
 max = 64
}
hbe_feast_log_weight = {
 value = var:hbe_member_dividend_weight
}
hbe_feast_dividend_share = {
 value = var:hbe_member_dividend_weight
 divide = var:hbe_member_party_weight
 multiply = var:hbe_member_party_pool
}
hbe_feast_prestige_share = {
 value = var:hbe_member_dividend_weight
 divide = var:hbe_member_party_weight
 multiply = 3
}
''')
    dividend=[]
    for party in ('hbe_common_party','hbe_local_party'):
        dividend.append(f'''international_organization:{party} ?= {{
 set_variable = {{ name = hbe_party_dividend_pool value = 0 }}
 set_variable = {{ name = hbe_party_dividend_weight value = 0 }}
 every_international_organization_member = {{
  limit = {{ has_variable = hbe_feast_points var:hbe_feast_points > 0 }}
  if = {{ limit = {{ var:hbe_feast_points >= 3 }} set_variable = {{ name = hbe_member_dividend_weight value = 1.38629 }} }}
  else_if = {{ limit = {{ var:hbe_feast_points >= 2 }} set_variable = {{ name = hbe_member_dividend_weight value = 1.09861 }} }}
  else = {{ set_variable = {{ name = hbe_member_dividend_weight value = 0.69315 }} }}
  prev = {{ change_variable = {{ name = hbe_party_dividend_weight add = prev.var:hbe_member_dividend_weight }} }}
  set_variable = {{ name = hbe_member_imperial_bonus value = hbe_feast_imperial_bonus }}
  prev = {{ change_variable = {{ name = hbe_party_dividend_pool add = prev.var:hbe_member_imperial_bonus }} }}
  if = {{ limit = {{ has_variable = hbe_feast_paid }}
   prev = {{ change_variable = {{ name = hbe_party_dividend_pool add = {{ value = prev.var:hbe_feast_paid multiply = 0.25 }} }} }}
  }}
 }}
 every_international_organization_member = {{
  set_variable = {{ name = hbe_feast_last_dividend value = 0 }}
  set_variable = {{ name = hbe_feast_last_prestige value = 0 }}
 }}
 if = {{ limit = {{ var:hbe_party_dividend_weight > 0 }}
  every_international_organization_member = {{ limit = {{ has_variable = hbe_feast_points var:hbe_feast_points > 0 }}
   set_variable = {{ name = hbe_member_party_weight value = prev.var:hbe_party_dividend_weight }}
   set_variable = {{ name = hbe_member_party_pool value = prev.var:hbe_party_dividend_pool }}
   set_variable = {{ name = hbe_feast_last_dividend value = hbe_feast_dividend_share }}
   add_gold = var:hbe_feast_last_dividend
   set_variable = {{ name = hbe_feast_last_prestige value = hbe_feast_prestige_share }}
   add_prestige = var:hbe_feast_last_prestige
  }}
 }}
}}''')
    put('in_game/common/scripted_effects/hbe_feast_dividend_effects.txt','hbe_pay_feast_dividends = {\n'+'\n'.join(dividend)+'\n}')
    path=out/'in_game/common/scripted_effects/hbe_banquet_effects.txt';text=path.read_text(encoding='utf-8-sig');edits=[]
    for k,_,s,e,_ in blocks(text,0):
        body=text[s:e]
        if k=='hbe_fund_project' and 'name = hbe_feast_paid' not in body:
            body=body.replace('add_gold = { value = hbe_feast_fee multiply = -1 }','set_variable = { name = hbe_feast_paid value = hbe_feast_fee } add_gold = { value = hbe_feast_fee multiply = -1 }')
        if k=='hbe_open_accounts' and 'name = hbe_feast_paid' not in body:
            body=body.replace('set_variable = { name = hbe_feast_points value = 0 }','set_variable = { name = hbe_feast_points value = 0 } set_variable = { name = hbe_feast_paid value = 0 }')
        if k=='hbe_settle_accounts' and 'hbe_pay_feast_dividends = yes' not in body:
            body='\n hbe_pay_feast_dividends = yes\n'+body
        if body!=text[s:e]:edits.append((s,e,body))
    put('in_game/common/scripted_effects/hbe_banquet_effects.txt',apply_edits(text,edits))
    path=out/'in_game/common/scripted_effects/hbe_simple_banquet_effects.txt';text=path.read_text(encoding='utf-8-sig')
    entry=next(x for x in blocks(text,0) if x[0]=='hbe_feast_sync_party');body=text[entry[2]:entry[3]]
    for variable in ('hbe_feast_last_dividend','hbe_feast_last_prestige'):
        if 'has_variable = '+variable not in body:body+=f'\n if = {{ limit = {{ NOT = {{ has_variable = {variable} }} }} set_variable = {{ name = {variable} value = 0 }} }}\n'
    put('in_game/common/scripted_effects/hbe_simple_banquet_effects.txt',apply_edits(text,[(entry[2],entry[3],body)]))
    loc['hbe_feast_paid']='本届实际出资'
    loc['hbe_feast_last_dividend']='上届派内分红'
    loc['hbe_feast_last_prestige']='上届派内威望'
    loc['hbe_party_dividend_pool']='本届派内分红池'
    loc['hbe_party_dividend_weight']='本派分红权重'
    loc['hbe_member_dividend_weight']='个人分红权重'
    loc['hbe_member_imperial_bonus']='本府为派内奖池增加的帝国奖金'
    loc['HBE_FEAST_REWARDS']='参与：建设+15%、商人容量+15%（两年）。\n成功：6金币、3声望、5信誉；生产和粮食+15%（三年）。\n派内分红：每位贡献国增加半个月税贸收入的帝国奖金（8—64金币），加上实付出资的25%；另有每派3点威望。每两年按贡献的对数权重分配。'
    loc['HBE_FEAST_LAST_DIVIDEND']="本府上届分红：[Player.MakeScope.GetVariable('hbe_feast_last_dividend').GetValue|2]金币、[Player.MakeScope.GetVariable('hbe_feast_last_prestige').GetValue|2]威望"
    dc='hbe_term_feast_dividend';path=out/'main_menu/common/game_concepts/hbe_concepts.txt';text=path.read_text(encoding='utf-8-sig')
    if not any(x[0]==dc for x in blocks(text,0)):text+='\n'+dc+' = { }\n'
    put('main_menu/common/game_concepts/hbe_concepts.txt',text)
    loc['game_concept_'+dc]='派内分红'
    loc['game_concept_'+dc+'_desc']='#T 每两年结算的派内分红#!\n无论共同目标是否完成，有贡献的成员都参与派内分红。每位贡献国按结算时半个月税贸收入增加一笔帝国奖金，最低8、最高64金币；再加上这些成员本届实际出资的25%，组成派内金币奖池。帝国奖金直接生成，不额外扣取任何成员的国库。每派另有3点威望。\n\n分配权重为ln(1＋本届贡献)：1、2、3贡献分别约为0.693、1.099、1.386。三贡献约得一贡献的两倍。\n个人金币或威望＝本派对应奖励池×个人权重÷本派权重总和。零贡献既不增加帝国奖金，也不领取奖励；仅完成地方事业而未现金出资，仍可获得金币与威望。8—64金币限制的是每位贡献国加入奖池的金额，个人最终分红按权重计算。\n\n例如两国贡献1与3、各出资2金币，且均触发最低奖金，奖池共17金币，分别领取约5.67和11.33金币。按结算时所属派系分配；换派不重置出资记录。共同成功另有的3点声望奖励仍保留。'
    loc['HBE_FEAST_REWARDS']=loc['HBE_FEAST_REWARDS'].replace('派内分红',f"[Concept('{dc}', '派内分红')|e]")

    # A native concept link explains the actual seven timed country decisions.
    concept='hbe_term_local_service'
    path=out/'main_menu/common/game_concepts/hbe_concepts.txt';text=path.read_text(encoding='utf-8-sig')
    if not any(x[0]==concept for x in blocks(text,0)):text+='\n'+concept+' = { }\n'
    put('main_menu/common/game_concepts/hbe_concepts.txt',text)
    loc['game_concept_'+concept]='地方事业'
    projects=[loc['hbe_service_'+g+'.title'] for g in grouped]
    loc['game_concept_'+concept+'_desc']='#T 地方事业：本圈公共工程#!\n打开本国「内容 → 决议」，寻找本圈的事业决议：\n'+'\n'.join('• '+name for name in projects)+'\n\n完成本圈第一项科技后开放。基础费用4金币，办理三年；国家共享五年开工间隔，役负须低于70。乡社议办还需完成本圈公议并有至少5地区储备；行会雇办需另付雇办费。\n\n工期结束后的月初自动结算，增加本圈储备和信誉，并激活五年内完成事业的联动资格。大开席进行期间，完成时增加2点本届贡献，每国每届限一次；开始办理时不计贡献。\n\n建造普通或特色建筑、完成科技、为会盟出资，均不等于完成地方事业。建筑可以增强事业收益，但必须实际完成上述三年项目。'
    for k,v in list(loc.items()):
        if k in ('game_concept_'+concept,'game_concept_'+concept+'_desc') or k.endswith('.title'):continue
        loc[k]=''.join(chunk if chunk.startswith('[') else chunk.replace('地方事业',f"[Concept('{concept}', '地方事业')|e]") for chunk in re.split(r'(\[[^\]]*\])',v))

    path=out/'in_game/gui/panels/situation/hbe_banquet.gui';text=path.read_text(encoding='utf-8-sig')
    text=text.replace('size = { 480 64 } autoresize = no align = left|top text = "HBE_FEAST_REWARDS"','size = { 480 94 } autoresize = no align = left|top text = "HBE_FEAST_REWARDS"')
    if 'text = "HBE_FEAST_LAST_DIVIDEND"' not in text:
        marker='text = "HBE_FEAST_REWARDS" }'
        text=text.replace(marker,marker+'\n text_multi = { size = { 480 24 } autoresize = no visible = "[IsPlayerValid]" text = "HBE_FEAST_LAST_DIVIDEND" }')
    # The vanilla flag is 30 wide. Fixed positions keep the score inside the
    # content area and reserve 24 units for the scroll bar and its gutter.
    for party in ('hbe_common_party','hbe_local_party'):
        row=f'''scrollwidget = {{ fixedgridbox = {{
   size = {{ 210 -1 }} minimumsize = {{ 210 -1 }} maximumsize = {{ 210 -1 }}
   addrow = 30 addcolumn = 210 datamodel_reuse_widgets = yes
   datamodel = "[GetUniqueInternationalOrganization('{party}').GetMembers]"
   item = {{ widget = {{ size = {{ 210 30 }}
    background = {{ using = color_whiteish_texture alpha = 0.08 }}
    country_flag_very_small = {{ position = {{ 3 5 }} size = {{ 30 20 }} tooltipwidget = {{ using = CountryTooltip }} }}
    text_single = {{ position = {{ 37 2 }} size = {{ 137 26 }} maximumsize = {{ 137 26 }} autoresize = no align = left|nobaseline text = "[Country.GetName]" }}
    text_single = {{ position = {{ 178 2 }} size = {{ 28 26 }} maximumsize = {{ 28 26 }} autoresize = no align = right|nobaseline text = "[Country.MakeScope.GetVariable('hbe_feast_points').GetValue|0]" }}
   }} }}
  }} }}
'''
        # Prefer parser bounds over a regex for complete nested widget replacement.
        candidate=next((x for x in blocks(text) if x[0]=='scrollwidget' and f"GetUniqueInternationalOrganization('{party}').GetMembers" in text[x[2]:x[3]]),None)
        assert candidate,party
        text=apply_edits(text,[(candidate[1],candidate[4],row)])
    text=text.replace('hbox = { size = { 234 24 }\n  text_single = { size = { 175 24 } text = "HBE_FEAST_MEMBER_NAME" }\n  text_single = { size = { 45 24 } text = "HBE_FEAST_MEMBER_POINTS" }\n }','widget = { size = { 210 24 }\n  text_single = { position = { 37 0 } size = { 137 24 } autoresize = no align = left|nobaseline text = "HBE_FEAST_MEMBER_NAME" }\n  text_single = { position = { 178 0 } size = { 28 24 } autoresize = no align = right|nobaseline text = "HBE_FEAST_MEMBER_POINTS" }\n }')
    ts=tokens(text)
    ai=next(i for i,t in enumerate(ts) if t.value=='"situation_panel_main_actions"' and ts[i-1].value=='blockoverride')+1
    action_start,action_end=ts[ai].end,ts[close_index(ts,ai)].start
    buttons='\n vbox = { size = { 480 -1 } spacing = 5\n text_multi = { size = { 480 62 } autoresize = no align = left|top text = "HBE_FEAST_ACTION_HELP" }\n'
    for key in ('hbe_feast_fund_action','hbe_feast_common_action','hbe_feast_local_action'):
        buttons+=f'''targetted_button_regular = {{ size = {{ 480 32 }} text = "{key}"
 enabled = "[PdxGuiWidget.IsUberButtonEnabled]"
 scripted_action_tooltip = {{ click_type = left click_mode = single action_name = "{key}"
  actor = "[Player]" parameter = {{ parameter_name = "recipient" parameter_value = "[GetSituationByKey('hbe_banquet')]" }}
 }}
 tooltipwidget = {{ BasicFunctionalTooltip = {{}} }}
}}
'''
    buttons+=' }\n'
    text=apply_edits(text,[(action_start,action_end,buttons)])
    put('in_game/gui/panels/situation/hbe_banquet.gui',text)
    loc['HBE_FEAST_ACTION_HELP']='出资：每届一次，费用为0.35个月税贸收入（2—6金币）。\n换派：五年内限一次，原派成员对本府态度−5，五年内消退。\n当前派别、已出资或资金不足等限制可悬停按钮查看。'
    loc['hbe_feast_fund_action_desc']='为本届会盟出资，获得1贡献、2信誉与两年会盟相助。每届一次，费用为0.35个月税贸收入（最低2、最高6金币）；已出资或资金不足时不可再次办理。'
    for key,party in [('hbe_feast_common_action','共建派'),('hbe_feast_local_action','兴业派')]:
        loc[key+'_desc']='改为支持'+party+'。当前已支持该派或距上次换派不足五年时不可办理；换派不会重置本届出资次数。原派其他成员对本府态度−5，每年恢复1点，最长五年。'
    for i in (1,2):
        k='hbe_stance_change_'+str(i)
        for suffix in ('.desc','.desc.entry'):
            loc[k+suffix]=loc['hbe_feast_'+('common' if i==1 else 'local')+'_action_desc']
    concepts=(out/'main_menu/common/game_concepts/hbe_concepts.txt').read_text(encoding='utf-8-sig')
    guide_count=sum(k.startswith('hbe_term_') for k,*_ in blocks(concepts,0))
    report=dict(guest_licenses=len(grouped),audit_native_unlocks=0,member_row_width=222,explicit_player_actions=3,faction_switch_years=5,departure_opinion=-5,dividend_fraction=.25,imperial_bonus=dict(income_months=.5,minimum=8,maximum=64),party_prestige_pool=3,dividend_weight='ln(1+contribution)',service_hover=concept,moved_era_nodes=28,advance_layout=layout,vanilla_anchors=VANILLA_ANCHORS,improved_units=list(improved),mechanic_guide_count=guide_count)
    report['member_row_width']=210
    report['member_scrollbar_gutter']=24
    return report
