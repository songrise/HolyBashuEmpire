"""Reproducible, opt-in Seven Circles defensive treaty; no offensive calls."""
from pathlib import Path
import json, hashlib

TRIGGERS = '''hbe_common_defense_choice_valid = {
 is_member_of_international_organization = international_organization:hbe_empire
 is_leader_of_international_organization = international_organization:hbe_empire
 international_organization:hbe_empire = { NOT = { has_variable = hbe_common_defense_decided } }
}
hbe_common_defense_join_allowed = {
 is_member_of_international_organization = international_organization:hbe_empire
 international_organization:hbe_empire = { has_variable = hbe_common_defense_active }
 exists = scope:first_leader
 exists = scope:second_leader
 scope:first_leader = { is_member_of_international_organization = international_organization:hbe_empire }
 scope:second_leader = { NOT = { is_member_of_international_organization = international_organization:hbe_empire } }
 trigger_if = {
  limit = { exists = scope:war }
  scope:war = { defender_leader = scope:first_leader }
 }
}
'''

EFFECTS = '''hbe_common_defense_accept = {
 if = { limit = { hbe_common_defense_choice_valid = yes }
  international_organization:hbe_empire = {
   set_variable = hbe_common_defense_decided
   set_variable = hbe_common_defense_active
   every_international_organization_member = {
    every_current_war = {
     limit = {
      defender_leader = { is_member_of_international_organization = international_organization:hbe_empire }
      attacker_leader = { NOT = { is_member_of_international_organization = international_organization:hbe_empire } }
     }
     hbe_common_defense_gather = yes
    }
   }
  }
  hbe_common_defense_notify_members = yes
 }
 else = { remove_variable = hbe_common_defense_offer_seen }
}
hbe_common_defense_decline = {
 if = { limit = { hbe_common_defense_choice_valid = yes }
  international_organization:hbe_empire = { set_variable = hbe_common_defense_decided }
  hbe_common_defense_notify_members = yes
 }
 else = { remove_variable = hbe_common_defense_offer_seen }
}
# War scope. Native eligibility prevents joining both sides or conflicting wars.
hbe_common_defense_gather = {
 save_scope_as = hbe_common_defense_war
 international_organization:hbe_empire = {
  every_international_organization_member = {
   limit = {
    scope:hbe_common_defense_war = {
     NOT = { is_in_war = prev }
     can_join_as_defender = prev
    }
   }
   join_war_as_defender = { war = scope:hbe_common_defense_war }
  }
 }
}
hbe_common_defense_notify_members = {
 save_scope_as = hbe_common_defense_decider
 international_organization:hbe_empire = {
  every_international_organization_member = {
   limit = {
    NOT = { this = scope:hbe_common_defense_decider }
    NOT = { has_variable = hbe_common_defense_member_notified }
   }
   trigger_event_silently = { id = hbe_common_defense.2 days = 1 }
  }
 }
}
hbe_common_defense_monthly = {
 if = { limit = {
  is_situation_active = situation:red_turban_rebellions
  hbe_common_defense_choice_valid = yes
 }
  international_organization:hbe_empire = {
   if = { limit = { NOT = { has_variable = hbe_common_defense_months } }
    set_variable = { name = hbe_common_defense_months value = 0 }
   }
   change_variable = { name = hbe_common_defense_months add = 1 }
  }
  if = { limit = {
   international_organization:hbe_empire = { var:hbe_common_defense_months >= 3 }
   NOT = { has_variable = hbe_common_defense_offer_seen }
  }
   trigger_event_silently = { id = hbe_common_defense.1 days = 1 }
  }
 }
}
'''

EVENT = '''namespace = hbe_common_defense
hbe_common_defense.1 = {
 type = country_event
 outcome = neutral
 title = hbe_common_defense.1.title
 desc = hbe_common_defense.1.desc
 illustration_tags = { 1000 = hbe_story_art_council }
 trigger = { hbe_common_defense_choice_valid = yes }
 immediate = { set_variable = hbe_common_defense_offer_seen }
 option = {
  name = hbe_common_defense.1.a
  ai_chance = { base = 100 }
  custom_tooltip = hbe_common_defense_accept_tt
  hidden_effect = { hbe_common_defense_accept = yes }
 }
 option = {
  name = hbe_common_defense.1.b
  ai_chance = { base = 0 }
  custom_tooltip = hbe_common_defense_decline_tt
  hidden_effect = { hbe_common_defense_decline = yes }
 }
}
hbe_common_defense.2 = {
 type = country_event
 outcome = neutral
 title = hbe_common_defense.2.title
 desc = { first_valid = {
  triggered_desc = {
   trigger = { international_organization:hbe_empire = { has_variable = hbe_common_defense_active } }
   desc = hbe_common_defense.2.desc.accepted
  }
  triggered_desc = { desc = hbe_common_defense.2.desc.declined }
 } }
 illustration_tags = { 1000 = hbe_story_art_council }
 trigger = {
  is_member_of_international_organization = international_organization:hbe_empire
  international_organization:hbe_empire = { has_variable = hbe_common_defense_decided }
  NOT = { has_variable = hbe_common_defense_member_notified }
 }
 immediate = { set_variable = hbe_common_defense_member_notified }
 option = {
  name = hbe_common_defense.2.a
  ai_chance = { base = 100 }
  hidden_effect = { set_variable = hbe_common_defense_notice_acknowledged }
 }
}
'''

DEFENSE = '''    only_leader_country_joins_defensive_wars = no
    joins_defensive_wars_as_co_belligerent = no
    join_defensive_wars_always = {
        has_variable = hbe_common_defense_active
        exists = scope:target
        scope:actor = { is_member_of_international_organization = international_organization:hbe_empire }
        scope:recipient = {
            is_member_of_international_organization = international_organization:hbe_empire
            NOT = { this = scope:actor }
            NOT = { this = scope:target }
        }
        scope:target = { NOT = { is_member_of_international_organization = international_organization:hbe_empire } }
    }
    join_defensive_wars_can_call = {
        has_variable = hbe_common_defense_active
        exists = scope:target
        scope:target = { NOT = { is_member_of_international_organization = international_organization:hbe_empire } }
    }
    join_offensive_wars_always = { always = no }
    join_offensive_wars_auto_call = { always = no }
    join_offensive_wars_can_call = { always = no }
'''

JOIN = '''hbe_isolation_join_rule = {
 join_war_disabled_trigger = {
  OR = {
   AND = {
    hbe_is_domain_polity = yes
    NOT = { hbe_common_defense_join_allowed = yes }
    OR = {
     scope:first_leader = { hbe_is_domain_polity = no }
     scope:second_leader = { hbe_is_domain_polity = no }
    }
   }
   AND = {
    hbe_is_domain_polity = no
    OR = {
     scope:first_leader = { hbe_is_domain_polity = yes }
     scope:second_leader = { hbe_is_domain_polity = yes }
    }
   }
  }
 }
}
'''

ZH = {
 'hbe_common_defense.1.title': '七圈共防',
 'hbe_common_defense.1.desc': '红巾兵起的消息传入蜀中，已有数月。起初只是商旅说东面关津换了旗号，如今送到府署的军报，却已写明各路兵马的去向。沿江诸府催问援军，山中诸府仍在清点自家的粮仓。七圈各有守土之约，越过圈界，调兵的公文便少了一道印。\n\n今日会席上，各圈使者将边报铺在同一张案上。有人主张外敌入境时不再分圈，各府共同应援；也有人担心，远处一座城池失守，便要本府的子弟离田出征。帝国首领须在议约上落印：从此共守蜀中，还是仍由各圈自行守备。',
 'hbe_common_defense.1.a': '外敌入境，七圈同援。',
 'hbe_common_defense.1.b': '仍循旧约，各守本圈。',
 'hbe_common_defense_accept_tt': '若我们仍为帝国首领且议约尚未裁定，永久启用七圈共防。帝国外部国家进攻任一成员时，其他符合参战条件的现有成员自动参加防御；同时应援正在进行的对外防御战争。不用于内部战争或对外进攻。各府须实际出兵并承担军费，无额外数值加成。',
 'hbe_common_defense_decline_tt': '若我们仍为帝国首领且议约尚未裁定，不启用帝国共同防卫，保留现有圈内规则。本次议案不再提出。',
 'hbe_common_defense_decided': '七圈共防议案已裁定',
 'hbe_common_defense_active': '七圈共防条约生效',
 'hbe_common_defense_months': '红巾局势后的议事月数',
 'hbe_common_defense_offer_seen': '已收到七圈共防议案',
 'hbe_common_defense.2.title': '七圈共防议定',
 'hbe_common_defense.2.desc.accepted': '送回本府的议约上，帝国首领已经落印。会席争论的粮额与行程另附一册，各圈使者带着相同的副本归去。以往越过圈界便须重问援军的关吏，如今可以照着这份议约传递军报。\n\n七圈共防条约已生效。帝国外敌进攻成员时，本府与其他符合参战条件的诸侯共同应援；签约时尚未结束的对外防御战争，也列入援助之中。各府仍须自备军粮、承担军费，内部争端与对外进攻不在此约之内。',
 'hbe_common_defense.2.desc.declined': '使者带回了会席的议定：帝国首领没有签下七圈共防条约。案上的边报各自收起，诸府仍按旧约清点守军与粮仓；来自别圈的求援，尚不能凭一纸帝国公文调走本府的人马。\n\n本次议案已经裁定，帝国没有新增共同防卫义务。各圈保留原有守备安排，本府仍须依现有盟约处理战事。关津的军报照常递送，越过圈界的援军却仍须另行商议。',
 'hbe_common_defense.2.a': '将议定知会各署。',
 'hbe_common_defense_member_notified': '已收到七圈共防议定通知',
 'hbe_common_defense_notice_acknowledged': '已阅七圈共防议定',
}
EN = {
 'hbe_common_defense.1.title': 'The Seven Circles Stand Together',
 'hbe_common_defense.1.desc': 'Several months have passed since news of the Red Turban rising reached Shu. At first, merchants merely reported new banners at the eastern crossings. Now the dispatches arriving at the prefectural offices name the armies and their routes. The river prefectures ask for reinforcements; those in the mountains are still counting their own grain. Each circle has a pact to defend its lands. Beyond its boundary, the orders for troops lack the necessary seal.\n\nToday, the envoys lay their reports on one table. Some would have every prefecture answer an invasion, regardless of circle. Others ask why a distant siege should take their sons away from the fields. The emperor must decide which compact to seal: a common defense of Shu, or the separate obligations of the old circles.',
 'hbe_common_defense.1.a': 'When outsiders invade, all seven circles shall answer.',
 'hbe_common_defense.1.b': 'Keep the old pacts. Each circle shall guard its own.',
 'hbe_common_defense_accept_tt': 'If we remain emperor and the proposal is undecided, permanently enact the common defense treaty. An outside attack on any member automatically brings eligible current members into its defense, including ongoing defensive wars when the treaty is signed. Internal wars and foreign offensives are excluded. Members bear their own military costs; the treaty grants no extra numerical bonuses.',
 'hbe_common_defense_decline_tt': 'If we remain emperor and the proposal is undecided, retain the existing circle rules without imperial collective defense. This proposal will not be raised again.',
 'hbe_common_defense_decided': 'Common defense proposal resolved',
 'hbe_common_defense_active': 'Seven Circles common defense treaty active',
 'hbe_common_defense_months': 'Months of deliberation after the Red Turban rising',
 'hbe_common_defense_offer_seen': 'Common defense proposal received',
 'hbe_common_defense.2.title': 'The Common Defense Decision',
 'hbe_common_defense.2.desc.accepted': 'The compact returned to our prefecture bears the emperor\'s seal. A separate register lists the grain and routes debated at the assembly, and each circle\'s envoy carries the same copy home. Wardens who once had to negotiate reinforcements across each boundary can now send their dispatches under this agreement.\n\nThe Seven Circles common defense treaty is in force. When an outside power attacks a member, we and the other eligible principalities shall answer. Ongoing defensive wars also receive aid when the treaty is signed. Each country supplies its own troops and pays their costs; internal disputes and foreign offensives fall outside the compact.',
 'hbe_common_defense.2.desc.declined': 'Our envoy brings the assembly\'s decision: the emperor has declined to sign the common defense treaty. The reports have been gathered from the table, and the prefectures will count their troops and stores under the old agreements. A request from another circle still carries no imperial authority to summon our soldiers.\n\nThe proposal is settled. No new imperial defense obligation has been established, and each circle retains its existing arrangements. Our prefecture must handle its wars under the alliances already in place. Dispatches will continue to cross the passes; reinforcements across circle boundaries must still be negotiated.',
 'hbe_common_defense.2.a': 'Send the decision to our offices.',
 'hbe_common_defense_member_notified': 'Common defense decision received',
 'hbe_common_defense_notice_acknowledged': 'Common defense decision acknowledged',
}

def apply(out, root=None, game=None):
 out=Path(out)
 def put(rel,text):
  p=out/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text.rstrip()+'\n',encoding='utf-8-sig')
 put('in_game/common/scripted_triggers/hbe_common_defense.txt',TRIGGERS)
 put('in_game/common/scripted_effects/hbe_common_defense.txt',EFFECTS)
 put('in_game/common/on_action/hbe_common_defense.txt','''monthly_country_pulse = { on_actions = { hbe_common_defense_pulse } }
on_war_declared = { on_actions = { hbe_common_defense_war_declared } }
hbe_common_defense_pulse = {
 trigger = { is_leader_of_international_organization = international_organization:hbe_empire }
 effect = { hbe_common_defense_monthly = yes }
}
hbe_common_defense_war_declared = {
 trigger = {
  exists = scope:war
  exists = scope:actor
  exists = scope:recipient
  international_organization:hbe_empire = { has_variable = hbe_common_defense_active }
  scope:recipient = { is_member_of_international_organization = international_organization:hbe_empire }
  scope:actor = { NOT = { is_member_of_international_organization = international_organization:hbe_empire } }
  scope:war = { defender_leader = scope:recipient attacker_leader = scope:actor }
 }
 effect = { scope:war = { hbe_common_defense_gather = yes } }
}''')
 put('in_game/events/hbe_common_defense.txt',EVENT)
 put('in_game/common/join_war_rules/hbe_isolation.txt',JOIN)
 p=out/'in_game/common/international_organizations/hbe_empire.txt';s=p.read_text(encoding='utf-8-sig')
 old='    join_defensive_wars = Never join_offensive_wars = Never\n'
 if old in s:s=s.replace(old,DEFENSE,1)
 else:assert DEFENSE in s,'Review changed imperial war participation rules'
 put(p.relative_to(out),s)
 for language,loc in [('simp_chinese',ZH),('english',EN)]:
  put(f'main_menu/localization/{language}/hbe_common_defense_l_{language}.yml',f'l_{language}:\n'+'\n'.join(' '+k+': '+json.dumps(v,ensure_ascii=False) for k,v in loc.items()))
 p=out/'build_manifest.json';m=json.loads(p.read_text(encoding='utf8'))
 old=m.get('common_defense_v032',{}).get('visible_events',0)
 m['events']+=2-old
 m['common_defense_v032']={'visible_events':2,'proposal_after_monthly_checks':3,'permanent_if_accepted':True,'art':'hbe_story_art_council','native_io_defensive_calls':True,'offensive_calls':False,'ai_accept_weight':100,'ai_decline_weight':0,'member_notice':'hbe_common_defense.2','notify_both_outcomes':True,'notice_excludes_decider':True}
 m['files']={p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and p.name!='build_manifest.json'}
 p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 return m['common_defense_v032']
