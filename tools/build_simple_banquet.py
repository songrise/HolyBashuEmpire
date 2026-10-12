"""Two factions, two-year cooperative feasts and a vanilla two-leader UI.

Existing event IDs and obsolete decisions remain registered for save/reference safety.
Only four core decisions remain visible; real regional service completion contributes.
"""
import re, json, shutil
from pdxscript import blocks, apply_edits

MEMBER='is_member_of_international_organization = international_organization:hbe_empire'
SIT='situation:hbe_banquet'

def replace_bodies(text,values):
 return apply_edits(text,[(s,e,values[k]) for k,_,s,e,_ in blocks(text,0) if k in values])

def build_simple_banquet(out,root,countries,loc,put,game):
 names={1:('hbe_common_party','共建派'),2:('hbe_local_party','兴业派')}
 titles={'hbe_banquet':'巴蜀大开席','hbe_stance_1':'共建派','hbe_stance_2':'兴业派','hbe_stance_3':'兴业派',
  'hbe_common_party':'共建派','hbe_local_party':'兴业派','HBE_COMMON_LEADER':'共建派领袖','HBE_LOCAL_LEADER':'兴业派领袖',
  'HBE_FEAST_MEMBER_COLUMNS':'成员　　　　　　　　本届贡献',
  'hbe_feast_cooperation':'会盟相助','hbe_feast_success':'盛会余泽','hbe_feast_common_reward':'共同兴建','hbe_feast_local_reward':'百业争荣',
  'hbe_feast_fee':'本届出资','hbe_feast_points':'本届贡献','hbe_feast_total':'共同进度','hbe_party_points':'本派贡献',
  'HBE_FEAST_MONTH_DISPLAY':'本届月份：$VALUE|0$ / 24','HBE_FEAST_TOTAL_DISPLAY':'共同贡献：$VALUE|0$ / 12',
  'hbe_banquet_desc':'各府围绕两种主张聚在一席：共建派重视一起修路建仓，兴业派重视商贸与地方经营。每两年办一届，出资或完成地方事业都能贡献。参与立即获益，合作成功再领回报。',
  'hbe_banquet_map_tt':'红色为共建派，蓝色为兴业派。两派都能参加公共事业，均保有各府自治和原有选票。',
  'HBE_FEAST_GUIDE':'#T 两派同席，共享收益#!\n选派 → 出资或完成地方事业 → 每两年领取回报。\n出资记1贡献，地方事业完成记2贡献；每国每届各限一次。两派合计达到12贡献，本届成功。\n贡献最多的派取得额外奖励，平局两派都获奖；没有完成目标也保留参与收益。',
  'HBE_FEAST_STATUS':"第[GetSituationByKey('hbe_banquet').MakeScope.GetVariable('hbe_round').GetValue|0]届 · 第[GetSituationByKey('hbe_banquet').MakeScope.GetVariable('hbe_round_month').GetValue|0] / 24个月\n共同贡献：[GetSituationByKey('hbe_banquet').MakeScope.GetVariable('hbe_feast_total').GetValue|0] / [GetSituationByKey('hbe_banquet').MakeScope.GetVariable('hbe_feast_required').GetValue|0] · 已成功[GetSituationByKey('hbe_banquet').MakeScope.GetVariable('hbe_completed_projects').GetValue|0]届",
  'HBE_FEAST_COMMON':"共建派 · [GetUniqueInternationalOrganization('hbe_common_party').MakeScope.GetVariable('hbe_party_points').GetValue|0]贡献\n参与即享建设速度+15%、商人容量+15%。胜出另得建设速度+20%、粮食生产+15%。",
  'HBE_FEAST_LOCAL':"兴业派 · [GetUniqueInternationalOrganization('hbe_local_party').MakeScope.GetVariable('hbe_party_points').GetValue|0]贡献\n参与即享建设速度+15%、商人容量+15%。胜出另得商人容量+25%、文化影响力+20%。",
  'HBE_FEAST_REWARDS':'#T 本届收益#!\n贡献国：立即获得两年的会盟相助。\n共同成功：贡献国获得6金币、3声望、5信誉，以及三年的生产效率+15%、粮食生产+15%。\n胜出派的贡献国另获三年派别奖励；未贡献的成员没有结算奖励。',
  'hbe_feast_cooperation_desc':'本府参与了跨府合作，两年内建设与商贸得到会盟帮助。',
  'hbe_feast_success_desc':'各府完成了本届共同目标，产业与粮食经营分享盛会收益。',
  'hbe_feast_common_reward_desc':'共建派贡献居前，本府参与的道路、仓廪与渠田得到额外支持。',
  'hbe_feast_local_reward_desc':'兴业派贡献居前，本府的商贸与文化事业得到额外支持。'}
 loc.update(titles)
 loc['HBE_FEAST_GUIDE']=loc['HBE_FEAST_GUIDE'].replace('两派合计达到12贡献','两派合计达到界面显示的目标（开局12贡献）')
 loc['HBE_FEAST_TOTAL_DISPLAY']='共同贡献：$VALUE|0$'
 loc['HBE_FEAST_MEMBER_NAME']='成员'
 loc['HBE_FEAST_MEMBER_POINTS']='贡献'
 loc['HBE_FEAST_GUIDE']='出资记1贡献，完成地方事业记2贡献，每届各限一次。\n每两年结算，达到共同目标，两派参与国均获奖励；领先派再获专属支持。'
 loc['HBE_FEAST_REWARDS']='参与：建设+15%、商人容量+15%（两年）。\n成功：6金币、3声望、5信誉；生产和粮食+15%（三年）。'
 loc['HBE_FEAST_COMMON']="共建派 · [GetUniqueInternationalOrganization('hbe_common_party').MakeScope.GetVariable('hbe_party_points').GetValue|0]贡献\n领先奖励：建设+20%、粮食+15%。"
 loc['HBE_FEAST_LOCAL']="兴业派 · [GetUniqueInternationalOrganization('hbe_local_party').MakeScope.GetVariable('hbe_party_points').GetValue|0]贡献\n领先奖励：商人容量+25%、文化影响力+20%。"
 # Plain words in the main feast surfaces; internal keys and old save variables survive.
 for k,v in list(loc.items()):
  if k.startswith(('hbe_banquet','hbe_project','hbe_stance','HBE_BANQUET','HBE_DISPUTE')):
   for old,new in [('共锅派','共建派'),('分锅派','兴业派'),('账房派','兴业派'),('争席度','分歧'),('个人履约','个人贡献'),('专业交付','地方援助'),('锅气','合作信心'),('义气','信誉')]:v=v.replace(old,new)
   loc[k]=v
 organizations=[]
 for i,(key,name) in names.items():
  loc[key+'_desc']=name+'主张以共同事业维护巴蜀旧盟；各府保有自治，两派不自动参加成员战争。'
  loc['diplomatic_status_'+key+'_name']=name+'成员'
  loc['diplomatic_status_'+key+'_tooltip']='参与'+name+'的会盟事业。'
  loc[key+'_list_who_tt']='本派的府州诸侯。'
  loc['io_opinion_'+key]='同属'+name
  organizations.append(f'''{key} = {{
 unique = yes has_target = no has_leader_country = yes leader_type = country
 leader_change_method = score leader_change_trigger_type = timed months_between_leader_changes = 1
 leader_score = {{ add = {{ value = var:hbe_feast_points multiply = 100 }} add = country_tax_base }}
 disband_if_no_leader = no disband_minimum_member_count = 0 expel_members_who_are_targets_of_other_members = no
 create_visible_trigger = {{ always = no }} invite_visible_trigger = {{ always = no }}
 can_join_trigger = {{ hbe_is_prince = yes {MEMBER} }}
 can_leave_trigger = {{ always = no }} auto_leave_trigger = {{ OR = {{ hbe_is_prince = no NOT = {{ {MEMBER} }} }} }}
 auto_disband_trigger = {{ always = no }} can_lead_trigger = {{ hbe_is_prince = yes is_subject = no has_ruler = yes }}
 join_defensive_wars = Never join_offensive_wars = Never can_declare_war = {{ hbe_war_is_internal = yes }}
 variables = {{ hbe_party_points = {{ format = HBE_FEAST_TOTAL_DISPLAY change_format = VARIABLE_CHANGE_FORMAT start = 0 min = 0 max = 9999 }} }}
}}''')
 put('in_game/common/international_organizations/hbe_feast_parties.txt','\n'.join(organizations))
 put('in_game/common/biases/hbe_feast_opinions.txt','\n'.join('io_opinion_'+key+' = { value = 3 }' for key,_ in names.values()))
 # Two faction emblems reuse the already finished organization art; no checkerboard.
 icon=out/'main_menu/gfx/interface/icons/international_organizations'
 for key,source in [('hbe_common_party','hbe_circle_chengdu_plain'),('hbe_local_party','hbe_circle_southern_salt_wine')]:
  target=icon/(key+'.dds');original=icon/(source+'.dds');assert original.exists(),original
  shutil.copyfile(original,target)
 majority={c['tag'] for n,c in enumerate(countries) if n%2==0}
 initial='OR = { '+' '.join('has_or_had_tag = '+t for t in sorted(majority))+' }'
 sync='''
 if = { limit = { OR = { NOT = { has_variable = hbe_stance } var:hbe_stance > 2 } } set_variable = { name = hbe_stance value = 2 } }
 if = { limit = { NOT = { has_variable = hbe_feast_points } } set_variable = { name = hbe_feast_points value = 0 } }
'''
 for i,(key,name) in names.items():
  other=names[3-i][0]
  sync+=f'''if = {{ limit = {{ var:hbe_stance = {i} }}
   if = {{ limit = {{ is_member_of_international_organization = international_organization:{other} }} international_organization:{other} = {{ remove_country_from_international_organization = prev }} }}
   if = {{ limit = {{ NOT = {{ exists = international_organization:{key} }} }} create_international_organization = {{ type = international_organization_type:{key} add_country_to_international_organization = prev set_leader_country = prev }} }}
   else_if = {{ limit = {{ NOT = {{ is_member_of_international_organization = international_organization:{key} }} }} international_organization:{key} = {{ add_country_to_international_organization = prev }} }}
 }}\n'''
 replacements={}
 replacements['hbe_banquet_register']=f'''
 if = {{ limit = {{ NOT = {{ has_variable = hbe_banquet_joined }} }}
  hbe_initialize = yes set_variable = hbe_banquet_joined set_variable = {{ name = hbe_contribution value = 0 }}
  if = {{ limit = {{ {initial} }} set_variable = {{ name = hbe_stance value = 1 }} }} else = {{ set_variable = {{ name = hbe_stance value = 2 }} }}
  trigger_event_non_silently = {{ id = hbe_banquet.1 days = 1 }}
 }} hbe_feast_sync_party = yes
'''
 for i in (1,2):replacements[f'hbe_choose_stance_{i}']=f'set_variable = {{ name = hbe_stance value = {i} }} set_variable = {{ name = hbe_stance_cooldown value = yes years = 5 }} hbe_feast_sync_party = yes'
 replacements['hbe_choose_stance_3']='hbe_choose_stance_2 = yes'
 replacements['hbe_fund_project']='''
 if = { limit = { is_situation_active = situation:hbe_banquet NOT = { has_variable = hbe_round_contributed } gold >= hbe_feast_fee }
  hbe_banquet_register = yes
  add_gold = { value = hbe_feast_fee multiply = -1 } set_variable = hbe_round_contributed set_variable = hbe_round_delivered
  change_variable = { name = hbe_feast_points add = 1 } change_variable = { name = hbe_contribution add = 1 }
  change_variable = { name = hbe_yiqi add = 2 } hbe_clamp_yiqi = yes
  add_country_modifier = { modifier = hbe_feast_cooperation years = 2 mode = replace }
  hbe_feast_recount = yes
 }
'''
 replacements['hbe_pledge_project']='hbe_fund_project = yes'
 replacements['hbe_open_accounts']='''
 set_variable = { name = hbe_round_month value = 0 } set_variable = { name = hbe_feast_total value = 0 }
 international_organization:hbe_empire ?= { every_international_organization_member = {
  hbe_banquet_register = yes set_variable = { name = hbe_feast_points value = 0 }
  remove_variable = hbe_round_contributed remove_variable = hbe_round_delivered remove_variable = hbe_feast_helped
  remove_variable = hbe_round_pledged remove_variable = hbe_fund_pledge remove_variable = hbe_declined_project
  if = { limit = { is_ai = no situation:hbe_banquet = { var:hbe_round > 1 } } trigger_event_non_silently = { id = hbe_banquet.2 days = 1 } }
 } } hbe_feast_recount = yes
'''
 replacements['hbe_settle_accounts']='''
 hbe_feast_recount = yes
 if = { limit = { var:hbe_feast_total >= var:hbe_feast_required }
  change_variable = { name = hbe_completed_projects add = 1 }
  international_organization:hbe_empire ?= { change_variable = { name = hbe_guoqi add = 5 } hbe_clamp_guoqi = yes }
  international_organization:hbe_empire ?= { every_international_organization_member = {
   if = { limit = { var:hbe_feast_points > 0 }
    add_gold = 6 add_prestige = 3 change_variable = { name = hbe_yiqi add = 5 } hbe_clamp_yiqi = yes
    add_country_modifier = { modifier = hbe_feast_success years = 3 mode = replace }
    if = { limit = { var:hbe_stance = 1 international_organization:hbe_common_party.var:hbe_party_points >= international_organization:hbe_local_party.var:hbe_party_points }
     add_country_modifier = { modifier = hbe_feast_common_reward years = 3 mode = replace } }
    else_if = { limit = { var:hbe_stance = 2 international_organization:hbe_local_party.var:hbe_party_points >= international_organization:hbe_common_party.var:hbe_party_points }
     add_country_modifier = { modifier = hbe_feast_local_reward years = 3 mode = replace } }
    trigger_event_non_silently = { id = hbe_banquet.4 }
   }
  } }
  if = { limit = { current_year >= 1437 var:hbe_completed_projects >= 6 var:hbe_charter = 0 }
   if = { limit = { international_organization:hbe_common_party.var:hbe_party_points >= international_organization:hbe_local_party.var:hbe_party_points } set_variable = { name = hbe_charter value = 1 } }
   else = { set_variable = { name = hbe_charter value = 2 } }
   international_organization:hbe_empire ?= { every_international_organization_member = { hbe_apply_charter = yes } }
  }
 } else = { international_organization:hbe_empire ?= { every_international_organization_member = { if = { limit = { var:hbe_feast_points > 0 } trigger_event_non_silently = { id = hbe_banquet.5 } } } } }
 change_variable = { name = hbe_round add = 1 }
 # Keep long-campaign milestone variables for existing civic and history events.
 if = { limit = { current_year >= 1352 } set_variable = { name = hbe_chapter value = 2 } }
 if = { limit = { current_year >= 1372 } set_variable = { name = hbe_chapter value = 3 } }
 if = { limit = { current_year >= 1397 } set_variable = { name = hbe_chapter value = 4 } }
 if = { limit = { current_year >= 1437 } set_variable = { name = hbe_chapter value = 5 } }
 hbe_open_accounts = yes
'''
 replacements['hbe_banquet_monthly']='''
 if = { limit = { NOT = { has_variable = hbe_feast_v021 } }
  set_variable = hbe_feast_v021 remove_variable = hbe_ballot_active
  if = { limit = { var:hbe_charter = 3 } set_variable = { name = hbe_charter value = 2 } }
  hbe_open_accounts = yes
 }
 international_organization:hbe_empire ?= { every_international_organization_member = { hbe_banquet_register = yes } }
 change_variable = { name = hbe_round_month add = 1 } hbe_feast_recount = yes
 if = { limit = { var:hbe_round_month >= 24 } hbe_settle_accounts = yes }
 set_variable = { name = hbe_pot_display value = international_organization:hbe_empire.var:hbe_guoqi }
'''
 path=out/'in_game/common/scripted_effects/hbe_banquet_effects.txt';txt=path.read_text(encoding='utf-8-sig')
 txt=replace_bodies(txt,replacements)
 # Migration: finish old outstanding deliveries once; no newly exposed promises.
 txt=replace_bodies(txt,{'hbe_deliver_contract':'''remove_variable = hbe_project_pending remove_variable = hbe_project_timer hbe_feast_help = yes'''})
 put('in_game/common/scripted_effects/hbe_banquet_effects.txt',txt)
 extra='hbe_feast_sync_party = {\n'+sync+'\n}\n'
 extra+='''hbe_feast_recount = {
 situation:hbe_banquet ?= { set_variable = { name = hbe_feast_total value = 0 } set_variable = { name = hbe_feast_required value = 0 } }
 international_organization:hbe_common_party ?= { set_variable = { name = hbe_party_points value = 0 } }
 international_organization:hbe_local_party ?= { set_variable = { name = hbe_party_points value = 0 } }
 international_organization:hbe_empire ?= { every_international_organization_member = {
  if = { limit = { has_variable = hbe_feast_points } situation:hbe_banquet ?= { change_variable = { name = hbe_feast_total add = prev.var:hbe_feast_points } } }
  situation:hbe_banquet ?= { change_variable = { name = hbe_feast_required add = 1 } }
  if = { limit = { has_variable = hbe_feast_points var:hbe_stance = 1 } international_organization:hbe_common_party ?= { change_variable = { name = hbe_party_points add = prev.var:hbe_feast_points } } }
  else_if = { limit = { has_variable = hbe_feast_points var:hbe_stance = 2 } international_organization:hbe_local_party ?= { change_variable = { name = hbe_party_points add = prev.var:hbe_feast_points } } }
 } }
 situation:hbe_banquet ?= {
  if = { limit = { var:hbe_feast_required > 12 } set_variable = { name = hbe_feast_required value = 12 } }
  if = { limit = { var:hbe_feast_required < 3 } set_variable = { name = hbe_feast_required value = 3 } }
 }
}
hbe_feast_help = {
 if = { limit = { is_situation_active = situation:hbe_banquet NOT = { has_variable = hbe_feast_helped } }
  hbe_banquet_register = yes
  set_variable = hbe_feast_helped set_variable = hbe_round_delivered
  change_variable = { name = hbe_feast_points add = 2 } change_variable = { name = hbe_contribution add = 2 }
  add_country_modifier = { modifier = hbe_feast_cooperation years = 2 mode = replace }
  hbe_feast_recount = yes
 }
}
'''
 put('in_game/common/scripted_effects/hbe_simple_banquet_effects.txt',extra)
 put('in_game/common/script_values/hbe_feast_values.txt','hbe_feast_fee = { value = monthly_income_trade_and_tax multiply = 0.35 min = 2 max = 6 }')
 put('main_menu/common/static_modifiers/hbe_feast_modifiers.txt','''hbe_feast_cooperation = { global_construction_speed = 0.15 global_merchant_capacity_modifier = 0.15 }
hbe_feast_success = { global_production_efficiency = 0.15 global_monthly_food_modifier = 0.15 }
hbe_feast_common_reward = { global_construction_speed = 0.20 global_monthly_food_modifier = 0.15 }
hbe_feast_local_reward = { global_merchant_capacity_modifier = 0.25 cultural_influence_modifier = 0.20 }
''')
 for key in ['hbe_feast_cooperation','hbe_feast_success','hbe_feast_common_reward','hbe_feast_local_reward']:
  loc['STATIC_MODIFIER_NAME_'+key]=loc[key];loc['STATIC_MODIFIER_DESC_'+key]=loc[key+'_desc']
 # Join after empire initialization and recover old outstanding paid deliveries.
 put('in_game/common/on_action/hbe_simple_banquet_on_actions.txt','''monthly_country_pulse = { on_actions = { hbe_simple_feast_country } }
hbe_simple_feast_country = { trigger = { hbe_is_prince = yes } effect = {
 if = { limit = { is_situation_active = situation:hbe_banquet is_member_of_international_organization = international_organization:hbe_empire }
  hbe_banquet_register = yes
  if = { limit = { has_variable = hbe_project_pending NOT = { has_variable = hbe_project_timer } } hbe_deliver_contract = yes }
 } else = {
  international_organization:hbe_common_party ?= { remove_country_from_international_organization = prev }
  international_organization:hbe_local_party ?= { remove_country_from_international_organization = prev }
 }
} }
''')
 path=out/'in_game/common/scripted_effects/hbe_civic_effects.txt';txt=path.read_text(encoding='utf-8-sig')
 txt=apply_edits(txt,[(e,e,'\n hbe_feast_help = yes\n') for k,_,s,e,_ in blocks(txt,0) if k.startswith('hbe_record_service_') and 'hbe_feast_help = yes' not in txt[s:e]])
 put('in_game/common/scripted_effects/hbe_civic_effects.txt',txt)
 # Hide legacy pledges, roles, audits and three-way ballots, retaining their definitions.
 path=out/'in_game/common/decisions/hbe_banquet_decisions.txt';txt=path.read_text(encoding='utf-8-sig');edits=[]
 keep={'hbe_stance_change_1','hbe_stance_change_2','hbe_project_fund','hbe_banquet_ledger'}
 for key,_,s,e,_ in blocks(txt,0):
  body=txt[s:e]
  if key not in keep:
   pb=next(x for x in blocks(body,0) if x[0]=='potential');body=apply_edits(body,[(pb[2],pb[3],' always = no ')])
  if key=='hbe_project_fund':
   ab=next(x for x in blocks(body,0) if x[0]=='allow');body=apply_edits(body,[(ab[2],ab[3],' NOT = { has_variable = hbe_round_contributed } gold >= hbe_feast_fee ')])
   body=body.replace('ai_will_do = { value = 10 }','ai_will_do = { value = 12 }')
  edits.append((s,e,body))
 put('in_game/common/decisions/hbe_banquet_decisions.txt',apply_edits(txt,edits))
 # Native situation actions make the same guarded operations available in-panel.
 actions=[]
 for key,label,allow,effect in [
  ('hbe_feast_fund_action','为会盟出资','NOT = { has_variable = hbe_round_contributed } gold >= hbe_feast_fee','hbe_fund_project = yes'),
  ('hbe_feast_common_action','支持共建派','NOT = { var:hbe_stance = 1 } NOT = { has_variable = hbe_stance_cooldown }','hbe_choose_stance_1 = yes'),
  ('hbe_feast_local_action','支持兴业派','NOT = { var:hbe_stance = 2 } NOT = { has_variable = hbe_stance_cooldown }','hbe_choose_stance_2 = yes')]:
  loc[key]=label;loc[key+'_desc']='在大开席中'+label+'。与国家内容页共用次数限制，不会重复领奖。'
  actions.append(f'''{key} = {{ type = situation ai_tick = never automation_tick = never
   potential = {{ scope:actor = {{ hbe_is_prince = yes {MEMBER} is_situation_active = situation:hbe_banquet }} }}
   allow = {{ scope:actor = {{ {allow} }} }}
   select_trigger = {{ looking_for_a = situation target_flag = recipient name = "choose_situation" column = {{ data = name }} visible = {{ situation:hbe_banquet = this situation_is_active = yes }} }}
   effect = {{ scope:actor = {{ {effect} }} }} ai_will_do = {{ value = 0 }}
  }}''')
 put('in_game/common/generic_actions/hbe_feast_actions.txt','\n'.join(actions))
 messages=out/'main_menu/gui/messagetypes.txt';msgtext=messages.read_text(encoding='utf-8-sig')
 for key in ['hbe_feast_fund_action','hbe_feast_common_action','hbe_feast_local_action']:
  for prefix in ['PERFORM_','WE_PERFORM_','OTHER_PERFORMS_']:
   m=prefix+key+'_ACTION'
   if m+' = {' not in msgtext:msgtext+='\n'+m+' = { log = yes onmap = no popup = no idle = no option = no pausepopup = no message_category = government }\n'
   loc[m]=loc[key];loc[m+'_DESC']='本府在会盟中'+loc[key]+'。'
 put('main_menu/gui/messagetypes.txt',msgtext)
 for key,title,desc in [
  ('hbe_stance_change_1','支持共建派','各府共修道路、渠堰与仓廪。共建派在本届贡献领先时，参与国额外获得三年建设速度+20%、粮食生产+15%。\n\n改派有五年间隔；本届已有贡献会计入新派，但不会重领参与或结算奖励。'),
  ('hbe_stance_change_2','支持兴业派','让各府的商路、作坊与文化事业互相成就。兴业派在本届贡献领先时，参与国额外获得三年商人容量+25%、文化影响力+20%。\n\n改派有五年间隔；本届已有贡献会计入新派，但不会重领参与或结算奖励。'),
  ('hbe_project_fund','为会盟出资','邻府的道路修好，本府的货物也能少走远路。我们可以拿出一笔钱，共同筹办这一届的地方事业。\n\n费用为月度贸易与税收收入的35%，最低2、最高6金币；每国每届一次。立即获得2信誉、1贡献和两年建设速度+15%、商人容量+15%。两派合计12贡献便能在本届结束时领取额外收益。'),
  ('hbe_banquet_ledger','查看两派与本届收益','查看两派成员、本届贡献和奖励。\n\n出资记1贡献，完成地方事业记2贡献。每两年结算，达到共同目标后，两派参与国都能获益；贡献领先的派另有奖励。')]:
  loc[key+'.title']=title;loc[key+'.title.entry']=title;loc[key+'.desc']=desc;loc[key+'.desc.entry']=desc
 # Four concise events replace the operational tutorial/ledger; historical flavor stays.
 evpath=out/'in_game/events/hbe_banquet_events.txt';txt=evpath.read_text(encoding='utf-8-sig');ev={}
 def event(n,title,body,options):
  k=f'hbe_banquet.{n}';loc[k+'.title']=title;loc[k+'.title.entry']=title;loc[k+'.desc']=body
  opts=[]
  for j,(label,eff,weight,trigger) in enumerate(options):
   name=k+'.'+chr(97+j);loc[name]=label
   opts.append(f'option = {{ name = {name} ai_chance = {{ base = {weight} }} '+(f'trigger = {{ {trigger} }} ' if trigger else '')+eff+' }')
  ev[k]=f' type = country_event title = {k}.title desc = {k}.desc illustration_tags = {{ 1000 = hbe_event_art_council }} '+' '.join(opts)
 event(1,'两派同席','各府使者又在锦江边坐定。有人主张先修贯通诸府的道路和仓廪，也有人认为应先扶持各地作坊与商路。两派都愿意维护旧盟，只是盼望钱粮用在不同地方。\n\n选择一派后，可以出资，或照常完成本圈地方事业。参与立即获益，每两年共同结算；成功时两派都能分享收益。',[
  ('共建派：先修路、建仓。','hbe_choose_stance_1 = yes',50,''),('兴业派：先兴商、养业。','hbe_choose_stance_2 = yes',50,'')])
 event(2,'再开一席','各府带来上一届的成果，也带来下一届的打算。修成的道路不会因堂上的争论消失，守时的商户也值得继续得到支持。\n\n本届为期两年。出资或完成地方事业即可参与，不必另办交付合同。',[
  ('拿出本府的一份。','hbe_fund_project = yes',60,'NOT = { has_variable = hbe_round_contributed } gold >= hbe_feast_fee'),('我们先办好地方事业。','',40,'')])
 event(4,'席散而百业兴','两派终于带来了足够的成果。路上的行旅少了一段绕行，作坊的采办也能按约抵达。与会者看见，堂上的主张虽有不同，办成的事业却可以使彼此受益。\n\n本府已领取本届金币、声望、信誉与产业奖励。贡献领先的一派另得专属支持，下一届仍可继续合作。', [('让成果留在田亩与街市。','',100,'')])
 event(5,'留待下一届','本届的共同目标尚未办齐，使者却也没有空手而归。已经修补的桥栈仍可通行，曾经相助的邻府也记下了本府的心意。\n\n参与收益保留，本届没有额外结算奖励。下一届重新计数，不追缴出资，也不扣减信誉。', [('下次再把事情办齐。','',100,'')])
 event(7,'两派与会盟',loc['HBE_FEAST_STATUS']+'\n\n'+loc['HBE_FEAST_GUIDE']+'\n\n'+loc['HBE_FEAST_REWARDS'],[('回到本府治事。','',100,'')])
 put('in_game/events/hbe_banquet_events.txt',replace_bodies(txt,ev))
 # Remove obsolete operational random events (30-36), keep region and prince stories.
 path=out/'in_game/common/on_action/hbe_banquet_on_actions.txt';txt=path.read_text(encoding='utf-8-sig')
 txt=re.sub(r'\s+1 = hbe_banquet\.3[0-6]\b','',txt)
 put('in_game/common/on_action/hbe_banquet_on_actions.txt',txt)
 path=out/'in_game/common/situations/hbe_banquet.txt';txt=path.read_text(encoding='utf-8-sig')
 vb=next(x for x in blocks(txt,1) if x[0]=='variables')
 txt=apply_edits(txt,[(vb[2],vb[3],'''hbe_round = { format = HBE_ROUND_DISPLAY change_format = VARIABLE_CHANGE_FORMAT start = 1 min = 1 max = 9999 }
 hbe_round_month = { format = HBE_FEAST_MONTH_DISPLAY change_format = VARIABLE_CHANGE_FORMAT start = 0 min = 0 max = 24 }
 hbe_feast_total = { format = HBE_FEAST_TOTAL_DISPLAY change_format = VARIABLE_CHANGE_FORMAT start = 0 min = 0 max = 9999 }
 hbe_completed_projects = { format = HBE_SUCCESSES_DISPLAY change_format = VARIABLE_CHANGE_FORMAT start = 0 min = 0 max = 9999 }''')])
 txt=re.sub(r'\s*legend_key = \{ desc = hbe_stance_3[^}]*\}','',txt)
 txt=txt.replace('value = yellow','value = blue')
 # Fresh campaigns must not reset the first month's contributions as if migrating.
 sb=next(x for x in blocks(txt,1) if x[0]=='on_start')
 startbody=txt[sb[2]:sb[3]]
 if 'set_variable = hbe_feast_v021' not in startbody:txt=apply_edits(txt,[(sb[2],sb[2],' set_variable = hbe_feast_v021 set_variable = { name = hbe_chapter value = 1 } ')])
 put('in_game/common/situations/hbe_banquet.txt',txt)
 gui='''# Reuses vanilla situation blocks and two_countries_header_template.
# No GetGagMemberItems/GetCountryGuelphsProgress: those are engine-bound to Italy.
situation_panel = {
 blockoverride "situation_header_left" {
  vbox = { text_single = { text = "HBE_COMMON_LEADER" }
   hbox = { datacontext = "[GetUniqueInternationalOrganization('hbe_common_party').GetLeaderCountry]" spacing = 4
    country_flag_small = {} text_single = { text = "[Country.GetName]" } }
  }
 }
 blockoverride "situation_header_right" {
  vbox = { text_single = { text = "HBE_LOCAL_LEADER" }
   hbox = { datacontext = "[GetUniqueInternationalOrganization('hbe_local_party').GetLeaderCountry]" spacing = 4
    country_flag_small = {} text_single = { text = "[Country.GetName]" } }
  }
 }
 blockoverride "situation_panel_image" {
  using = two_countries_header_template
  blockoverride "two_countries_header_image" { background = { texture = "gfx/interface/hbe/panels/hbe_banquet.dds" texture_density = 2 spriteType = stretched spriteborder = { 0 0 } } }
  blockoverride "FirstCountryContext" { datacontext = "[GetUniqueInternationalOrganization('hbe_common_party').GetLeaderCountry]" }
  blockoverride "SecondCountryContext" { datacontext = "[GetUniqueInternationalOrganization('hbe_local_party').GetLeaderCountry]" }
  blockoverride "first_character_portrait_anchor" { parentanchor = bottom|left }
  blockoverride "second_character_portrait_anchor" { parentanchor = bottom|right }
  blockoverride "character_religion_visibility" { visible = no }
  blockoverride "character_name_maximumsize" { maximumsize = { 270 -1 } }
  blockoverride "character_role" { datacontext = "[Character.GetRuledCountry]" country_flag_small = {} }
 }
 blockoverride "situation_subheader_content" {}
 blockoverride "situation_panel_main_maximumsize" { minimumsize = { -1 320 } }
 blockoverride "situation_panel_main_actions" {
  vbox = { minimumsize = { 480 -1 } maximumsize = { 480 -1 } using = situations_actions }
 }
 blockoverride "situation_panel_main_content" {
  vbox = { minimumsize = { 480 -1 } maximumsize = { 480 -1 } spacing = 8
  text_multi = { size = { 480 46 } autoresize = no align = left|top text = "HBE_FEAST_STATUS" }
  widget = { size = { 480 18 }
   barchart = { size = { 480 16 }
    barslice = { texture = "gfx/interface/progressbars/progress_bar_whiteish.dds" color = { 0.60 0.22 0.16 1 }
     value = "[FixedPointToFloat(GetUniqueInternationalOrganization('hbe_common_party').MakeScope.GetVariable('hbe_party_points').GetValue)]" }
    barslice = { texture = "gfx/interface/progressbars/progress_bar_whiteish.dds" color = { 0.18 0.38 0.56 1 }
     value = "[FixedPointToFloat(GetUniqueInternationalOrganization('hbe_local_party').MakeScope.GetVariable('hbe_party_points').GetValue)]" }
   }
  }
  text_multi = { size = { 480 64 } autoresize = no align = left|top text = "HBE_FEAST_GUIDE" }
  text_multi = { size = { 480 64 } autoresize = no align = left|top text = "HBE_FEAST_REWARDS" }
'''
 # Ordinary Country data models retain working flags/tooltips and score readings.
 gui+='  hbox = { size = { 480 312 } spacing = 12\n'
 for i,(key,name) in names.items():
  title='HBE_FEAST_COMMON' if i==1 else 'HBE_FEAST_LOCAL'
  gui+=f'''vbox = {{ size = {{ 234 312 }} minimumsize = {{ 234 312 }} maximumsize = {{ 234 312 }} spacing = 4
 text_multi = {{ size = {{ 234 64 }} autoresize = no align = left|top text = "{title}" }}
 hbox = {{ size = {{ 234 24 }}
  text_single = {{ size = {{ 175 24 }} text = "HBE_FEAST_MEMBER_NAME" }}
  text_single = {{ size = {{ 45 24 }} text = "HBE_FEAST_MEMBER_POINTS" }}
 }}
 scrollarea = {{ size = {{ 234 216 }} scrollbarpolicy_horizontal = always_off autoresizeviewport = yes
  viewportwidget = {{ widget = {{ scissor = yes }} }}
  scrollbar_vertical = {{ using = Scrollbar_Vertical }}
  scrollwidget = {{ fixedgridbox = {{ addrow = 30 addcolumn = 100% datamodel = "[GetUniqueInternationalOrganization('{key}').GetMembers]"
  item = {{ hbox = {{ spacing = 4 using = bg_paper_card size = {{ 222 30 }}
   country_flag_small = {{ tooltipwidget = {{ using = CountryTooltip }} }}
   text_single = {{ size = {{ 145 30 }} maximumsize = {{ 145 30 }} text = "[Country.GetName]" }}
   text_single = {{ size = {{ 32 30 }} align = right text = "[Country.MakeScope.GetVariable('hbe_feast_points').GetValue|0]" }}
  }} }}
  }} }}
 }}
}}\n'''
 gui+='  }\n  }\n }\n}\n'
 put('in_game/gui/panels/situation/hbe_banquet.gui',gui)
 (root/'docs/simple_banquet_v021.md').write_text('''# 大开席：两派同席

共建派侧重道路、仓廪和粮政；兴业派侧重商贸、作坊和文化。两派不自动参战，不改变皇帝选票。

每届两年。每国出资一次记1贡献，完成地方事业一次记2贡献；两派共同达到12贡献即可成功。出资按月度贸易税收收入35%计，最低2、最高6金币。参与立即获得两年建设速度+15%、商人容量+15%。成功后，参与国得到6金币、3声望、5信誉，以及三年生产效率+15%、粮食生产+15%。

领先派的参与国额外得到三年派别奖励：共建派建设+20%、粮食+15%；兴业派商人容量+25%、文化影响力+20%。平局两派都获奖；未达标只是不发结算奖励，不扣信誉，不追债。相同修正刷新时长，不逐届无限叠层。

每国五年可改派一次。换派搬移本届贡献，不重领奖励。领袖按本届贡献优先、税基其次，原版每月择领袖。原有地区任务、科技分支、五年委任与百年故事继续运行。

界面复用原版two_countries_header_template、双侧页头、旗帜与Country成员列表，并显示贡献条。归尔甫专用GagCountryItem和GetCountryGuelphsProgress依赖意大利局势，故替换为自己的国家变量和组织成员。原版文件不覆盖。

旧存档的第三派转为兴业派，旧三选一章程的第三项转为第二项。过渡时重新开始一届；旧已付的援助完成后计入新合作，旧自主地方事业计时保留。旧决议键保留但隐藏复杂入口，未更换地图和国家编号。
''',encoding='utf-8')
 return dict(factions=2,round_months=24,target=12,funding_points=1,service_points=2,visible_decisions=sorted(keep),native_ui_template='two_countries_header_template')
