"""Modest internal expansion pressure through vanilla AI evaluation, never forced wars."""
def build_bashu_ai(out,root,loc,put,game):
 put('in_game/common/ai_scripted_expansion_target/hbe_neighbors.txt','''hbe_internal_neighbors = {
 attacker_potential = {
  hbe_is_prince = yes is_member_of_international_organization = international_organization:hbe_empire
  current_year >= 1342 at_war = no var:hbe_burden < 70
  OR = { months_since_war >= 96 AND = { months_since_war >= 48 OR = { ai_personality = ai_personality:ai_aggressive ai_personality = ai_personality:ai_expansionist } } }
 }
 candidate_list = { every_neighbor_country = { limit = { hbe_is_prince = yes is_member_of_international_organization = international_organization:hbe_empire NOT = { this = root } } add_to_list = source } }
 score = { add = scope:target.country_tax_base multiply = 8 add = 8 }
}''')
 put('in_game/common/ai_scripted_expansion_score/hbe_internal_rivalry.txt','''hbe_internal_rivalry = {
 attacker_potential = { hbe_is_prince = yes is_member_of_international_organization = international_organization:hbe_empire current_year >= 1342 at_war = no var:hbe_burden < 70 }
 target_trigger = { hbe_is_prince = yes is_member_of_international_organization = international_organization:hbe_empire is_neighbor_of = scope:attacker }
 score = { add = 6 }
 multiplier = {
  add = 0.10
  if = { limit = { OR = { AND = { scope:attacker = { var:hbe_stance = 1 } scope:target = { var:hbe_stance = 2 } } AND = { scope:attacker = { var:hbe_stance = 2 } scope:target = { var:hbe_stance = 1 } } } } add = 0.10 }
 }
 never_attack = { OR = { scope:attacker = { var:hbe_burden >= 70 } scope:target = { is_allied_with = { target = scope:attacker } } } }
}''')
 # Applied only to eligible AI princes; regular military-risk and CB checks remain native.
 put('main_menu/common/static_modifiers/hbe_ai_modifiers.txt','hbe_ai_internal_ambition = { aggressiveness_modifier = 0.15 ai_months_between_wars = -6 }')
 loc['hbe_ai_internal_ambition']='府州竞逐'
 loc['hbe_ai_internal_ambition_desc']='休养充足的巴蜀诸侯更愿意争取邻府权益；原版宣战理由、实力判断、盟约与停战仍有效。'
 loc['STATIC_MODIFIER_NAME_hbe_ai_internal_ambition']=loc['hbe_ai_internal_ambition']
 loc['STATIC_MODIFIER_DESC_hbe_ai_internal_ambition']=loc['hbe_ai_internal_ambition_desc']
 put('in_game/common/scripted_effects/hbe_ai_effects.txt','''hbe_ai_internal_update = {
 if = { limit = { is_ai = yes hbe_is_prince = yes is_member_of_international_organization = international_organization:hbe_empire current_year >= 1342 at_war = no var:hbe_burden < 70 months_since_war >= 48 }
  if = { limit = { NOT = { has_country_modifier = hbe_ai_internal_ambition } } add_country_modifier = { modifier = hbe_ai_internal_ambition years = -1 } }
 } else = { remove_country_modifier = hbe_ai_internal_ambition }
}''')
 put('in_game/common/on_action/hbe_ai_on_actions.txt','''monthly_country_pulse = { on_actions = { hbe_ai_pulse } }
hbe_ai_pulse = { trigger = { OR = { hbe_is_prince = yes has_country_modifier = hbe_ai_internal_ambition } } effect = { hbe_ai_internal_update = yes } }
''')
 (root/'docs/ai_internal_wars_v021.md').write_text('''# 0.2.1 帝国内部 AI

1342年起，已休养的AI更容易选择邻府为扩张目标。一般国家须和平八年，扩张/好战性格须四年；正常宣战理由、实力评估、停战与盟友关系继续由原版处理。

内部目标评估加6分、总分加权+10%；异派相邻国家额外+10%。和平四年以上、役负低于70的AI获得15%进取倾向，原版战争间隔缩短6个月。处于战争、役负过高、退盟或玩家控制时撤销。

没有自动宣战事件，没有移除停战、盟约或外围军事隔离，也没有全局改动原版AI性格。两派不组成自动参战的军事集团。

依据原版ai_scripted_expansion_target/attack_neighbors.txt及ai_scripted_expansion_score/readme.txt。
''',encoding='utf-8')
 return dict(start_year=1342,score_bonus=6,base_multiplier=.10,opposed_faction_extra=.10,aggressiveness=.15,war_interval_months=-6)
