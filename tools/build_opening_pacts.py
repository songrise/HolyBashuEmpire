"""Opening-only truces, circle mutual defence and random legitimate families."""
from itertools import combinations
from pdxscript import blocks,apply_edits
def build_opening_pacts(out,countries,loc,put):
 path=out/'in_game/common/international_organizations/hbe_empire.txt';text=path.read_text(encoding='utf-8-sig');edits=[]
 for k,_,s,e,_ in blocks(text,0):
  if not k.startswith('hbe_circle_'):continue
  body=text[s:e].replace('join_defensive_wars = Never join_offensive_wars = Never','')
  if 'join_defensive_wars_always' not in body:body+='''
 join_defensive_wars_always = { scope:recipient = { NOT = { this = scope:target } } }
 join_defensive_wars_can_call = { always = yes }
 join_offensive_wars_always = { always = no }
 join_offensive_wars_auto_call = { always = no }
 join_offensive_wars_can_call = { always = no }
 joins_defensive_wars_as_co_belligerent = no
'''
  edits.append((s,e,body))
  desc=loc[k+'_desc'].split('\n\n圈内共同防卫')[0]
  loc[k+'_desc']=desc+'\n\n圈内共同防卫：成员受到攻击时，同圈其他国家自动参加防御战争。主动进攻不自动召集同圈；侵略国本身不会被召来保卫受害者。共同防卫不改变帝国的外围隔离协议。'
 put('in_game/common/international_organizations/hbe_empire.txt',apply_edits(text,edits))
 pairs=list(combinations([c['tag'] for c in countries],2))
 truces='\n'.join(f'c:{a} ?= {{ add_truce_with = {{ target = c:{b} mutual = yes years = 1 }} }}' for a,b in pairs)
 child='''dynasty = scope:hbe_start_father.dynasty culture = scope:hbe_start_father.culture religion = scope:hbe_start_father.religion
 father = scope:hbe_start_father mother = scope:hbe_start_mother female = scope:hbe_start_child_female
 adm = { 20 70 } dip = { 20 70 } mil = { 20 70 } trait_category = none'''
 effects='''hbe_generate_opening_child = {
 random_list = {
  50 = { save_scope_value_as = { name = hbe_start_child_female value = yes } }
  50 = { save_scope_value_as = { name = hbe_start_child_female value = no } }
 }
'''
 for prefix,condition,upper in [('if','scope:hbe_start_father = { character_age >= 40 } scope:hbe_start_mother = { character_age >= 40 }',24),('else_if','scope:hbe_start_father = { character_age >= 36 } scope:hbe_start_mother = { character_age >= 36 }',20),('else','',16)]:
  effects+=f'{prefix} = {{ '+(f'limit = {{ {condition} }} ' if condition else '')+f'create_character = {{ age = {{ 0 {upper} }} {child} }} }}\n'
 effects+='''}
hbe_generate_opening_family = {
 ruler = { save_scope_as = hbe_start_father }
 if = { limit = { ruler = { is_married = no } }
  create_character = {
   age = { 38 44 } female = yes culture = scope:hbe_start_father.culture religion = scope:hbe_start_father.religion
   trait_category = none save_scope_as = hbe_start_mother
  }
  ruler = { marry_character_ignore_blocks = scope:hbe_start_mother }
 } else = { ruler = { every_spouse = { save_scope_as = hbe_start_mother } } }
 random_list = {
  25 = { set_variable = { name = hbe_opening_children value = 0 } }
  25 = { set_variable = { name = hbe_opening_children value = 1 } hbe_generate_opening_child = yes }
  25 = { set_variable = { name = hbe_opening_children value = 2 } hbe_generate_opening_child = yes hbe_generate_opening_child = yes }
  25 = { set_variable = { name = hbe_opening_children value = 3 } hbe_generate_opening_child = yes hbe_generate_opening_child = yes hbe_generate_opening_child = yes }
 }
 set_variable = hbe_opening_family_done
 set_variable = hbe_opening_abilities_fixed
}
hbe_repair_opening_child_abilities = {
 if = { limit = { has_variable = hbe_opening_family_done NOT = { has_variable = hbe_opening_abilities_fixed } has_ruler = yes }
  ruler = { every_child = {
   limit = { is_alive = yes adm <= 0 dip <= 0 mil <= 0 }
   set_to_limited_random_stats = { min_adm = 20 max_adm = 70 min_dip = 20 max_dip = 70 min_mil = 20 max_mil = 70 }
   if = { limit = { adm > 70 } add_adm = { value = 70 subtract = adm } }
   if = { limit = { dip > 70 } add_dip = { value = 70 subtract = dip } }
   if = { limit = { mil > 70 } add_mil = { value = 70 subtract = mil } }
  } }
  set_variable = hbe_opening_abilities_fixed
 }
}
hbe_apply_opening_pacts = {
 if = { limit = { current_date >= 1337.4.1 current_date < 1337.4.3 }
  if = { limit = { c:BAB = { NOT = { has_variable = hbe_opening_truce_done } } }
'''+truces+'''
   every_country = { limit = { hbe_is_prince = yes } set_variable = hbe_opening_truce_done }
  }
  every_country = { limit = { hbe_is_prince = yes has_ruler = yes NOT = { has_variable = hbe_opening_family_done } }
   hbe_generate_opening_family = yes
  }
 }
}
'''
 put('in_game/common/scripted_effects/hbe_opening_pacts_effects.txt',effects)
 put('in_game/common/on_action/hbe_opening_pacts_on_actions.txt','''on_game_start = { on_actions = { hbe_opening_pacts_start } }
hbe_opening_pacts_start = { effect = { c:BAB ?= { trigger_event_silently = { id = hbe_opening_family.1 days = 1 } } } }
monthly_country_pulse = { on_actions = { hbe_opening_abilities_monthly } }
hbe_opening_abilities_monthly = { trigger = { hbe_is_prince = yes } effect = { hbe_repair_opening_child_abilities = yes } }
''')
 put('in_game/events/hbe_opening_family_events.txt','''namespace = hbe_opening_family
hbe_opening_family.1 = { type = country_event hidden = yes immediate = { hbe_apply_opening_pacts = yes every_country = { limit = { hbe_is_prince = yes } hbe_repair_opening_child_abilities = yes } } }
''')
 loc['hbe_opening_children']='开局随机后代数'
 return dict(truce_pairs=len(pairs),truce_years=1,circle_defence=7,spouses=36,children_per_ruler='0–3',child_age_ranges=[[0,16],[0,20],[0,24]],child_ability_range=[20,70],old_zero_stat_children_repair_once=True,minimum_parent_age_at_birth=16,opening_only=True)
