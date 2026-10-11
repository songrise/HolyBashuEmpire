"""Fixtures deliberately grant research and money only inside an isolated profile."""
from pathlib import Path
import json,shutil,re,hashlib
base=Path(__file__).resolve().parent;root=base/'v020';profile=base/'eu5-v020-test';mod=profile/'mod/holy_bashu_empire'
shutil.copytree(root/'mod/holy_bashu_empire',mod,dirs_exist_ok=True)
release=root/'mod/holy_bashu_empire'
(profile/'hbe_release_under_test.json').write_text(json.dumps({'manifest_sha256':hashlib.sha256((release/'build_manifest.json').read_bytes()).hexdigest(),'script_files':{f.relative_to(release).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in release.rglob('*') if f.is_file() and f.suffix in ('.txt','.gui','.yml','.json') and f.name!='build_manifest.json'}},indent=2),encoding='utf-8')
def put(rel,s):
 p=mod/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s,encoding='utf-8-sig')
for p in (mod/'in_game/common/decisions').glob('hbe*decisions.txt'):
 s=p.read_text(encoding='utf-8-sig');s=re.sub(r'ai_will_do\s*=\s*\{\s*value\s*=\s*\d+\s*\}','ai_will_do = { value = 0 }',s);p.write_text(s,encoding='utf-8-sig')
# Exercise unit creation before 1352 only in this isolated fixture.
p=mod/'in_game/common/unit_types/hbe_civic_units.txt'
p.write_text(p.read_text(encoding='utf-8-sig').replace('current_year >= 1352','always = yes'),encoding='utf-8-sig')
put('in_game/common/on_action/hbe_civic_test.txt','''on_game_start = { on_actions = { hbe_civic_test_start } }
hbe_civic_test_start = { effect = { c:BAB = { trigger_event_silently = { id = hbe_civic_test.1 days = 5 } trigger_event_silently = { id = hbe_civic_test.2 days = 100 } trigger_event_silently = { id = hbe_civic_test.3 days = 150 } trigger_event_silently = { id = hbe_civic_test.4 days = 180 } trigger_event_silently = { id = hbe_civic_test.5 days = 181 } } } }''')
setup=[]
for tag,policy in [('BAB','hbe_levy_policy'),('BAE','hbe_communal_policy'),('BAF','hbe_paid_policy')]:
 setup.append(f'''c:{tag} = {{
 add_gold = 1000
 if = {{ limit = {{ NOT = {{ has_advance = hbe_civic_common_1 }} NOT = {{ has_advance = hbe_civic_common_2 }} }} set_variable = hbe_test_no_free_civic }}
 set_variable = {{ name = hbe_burden value = 150 }} hbe_clamp_burden = yes
 if = {{ limit = {{ var:hbe_burden = 100 }} set_variable = hbe_test_upper_clamp }}
 set_variable = {{ name = hbe_burden value = -5 }} hbe_clamp_burden = yes
 if = {{ limit = {{ var:hbe_burden = 0 }} set_variable = hbe_test_lower_clamp }}
 set_variable = {{ name = hbe_burden value = 20 }}
 research_advance = advance_type:hbe_tech_common_1
 research_advance = advance_type:hbe_tech_common_2
 research_advance = advance_type:hbe_tech_common_3
 research_advance = advance_type:hbe_civic_common_1
 research_advance = advance_type:hbe_civic_common_2
 research_advance = advance_type:hbe_tech_chengdu_plain_1
 research_advance = advance_type:hbe_tech_chengdu_plain_2
 research_advance = advance_type:hbe_tech_chengdu_plain_4
 research_advance = advance_type:hbe_tech_chengdu_plain_5
 research_advance = advance_type:hbe_civic_chengdu_plain_1
 add_policy = policy:{policy}
 if = {{ limit = {{ has_policy = {policy} has_variable = hbe_policy_lock }} set_variable = hbe_test_native_policy }}
 if = {{ limit = {{ can_build_building = building_type:hbe_canal_office }} set_variable = hbe_test_building_unlocked }}
 capital = {{ construct_building = {{ building_type = building_type:hbe_canal_office instant = yes cost_multiplier = 0 cost_multiplier_reason = "game_concept_event" }} }}
 set_variable = hbe_mission_chengdu_plain_2
 set_variable = {{ name = hbe_service_cooldown value = yes years = 5 }}
 set_variable = hbe_service_chengdu_plain_pending
 set_variable = {{ name = hbe_service_chengdu_plain_timer value = yes days = 3 }}
 }}''')
setup.append('''c:BAF = {
 set_variable = { name = hbe_test_expected_gold value = gold }
 change_variable = { name = hbe_test_expected_gold subtract = hbe_paid_bill }
 hbe_pay_service_chengdu_plain = yes
 if = { limit = { gold = var:hbe_test_expected_gold } set_variable = hbe_test_paid_charge }
}''')
test2=[]
for tag,amount in [('BAB',26),('BAE',22),('BAF',20)]:
 test2.append(f'''c:{tag} = {{
 if = {{ limit = {{ var:hbe_burden = {amount} NOT = {{ has_variable = hbe_service_chengdu_plain_pending }} has_variable = hbe_recent_delivery_chengdu_plain }} set_variable = hbe_test_policy_settlement }}
 set_variable = {{ name = hbe_test_burden_once value = var:hbe_burden }}
 hbe_country_monthly = yes hbe_country_monthly = yes
 if = {{ limit = {{ var:hbe_burden = var:hbe_test_burden_once }} set_variable = hbe_test_settlement_idempotent }}
 set_variable = {{ name = hbe_test_effective_institution value = total_effective_building_levels:hbe_canal_office }}
 if = {{ limit = {{ hbe_operating_canal_office = yes }} set_variable = hbe_test_operating_institution }}
 }}''')
test3='''
c:BAB = {
 hbe_office_chengdu_plain_appoint = yes
 if = { limit = { var:hbe_office_chengdu_plain = 1 var:hbe_office_count = 1 international_organization:hbe_circle_chengdu_plain = { var:hbe_civic_holder = prev } } set_variable = hbe_test_office_appointed }
}
c:BAE = { hbe_office_chengdu_plain_appoint = yes if = { limit = { var:hbe_office_chengdu_plain = 0 } set_variable = hbe_test_vacancy_respected } }
c:BAB = {
 remove_variable = hbe_office_chengdu_plain_term hbe_civic_monthly = yes hbe_civic_monthly = yes
 if = { limit = { var:hbe_office_chengdu_plain = 0 var:hbe_office_count = 0 international_organization:hbe_circle_chengdu_plain = { NOT = { has_variable = hbe_civic_holder } } } set_variable = hbe_test_office_expired }
}
c:BAE = { hbe_office_chengdu_plain_appoint = yes if = { limit = { var:hbe_office_chengdu_plain = 1 } set_variable = hbe_test_successor } }
c:BAB = {
 set_variable = { name = hbe_burden value = 20 }
 if = { limit = { hbe_civic_special_limit >= 1 } set_variable = hbe_test_supported_capacity }
 capital = { create_sub_unit = unit_type:hbe_canal_crossbow }
}
'''
test4='''c:BAB = {
 hbe_civic_monthly = yes
 if = { limit = { total_sub_unit_type_count:hbe_canal_crossbow >= 1 var:hbe_burden = 21 } set_variable = hbe_test_regiment_pressure }
 set_variable = { name = hbe_petition_cooldown value = yes years = 5 }
 set_variable = { name = hbe_burden value = 70 }
}'''
test5='''c:BAB = { hbe_civic_monthly = yes
 if = { limit = { hbe_civic_special_limit = 0 total_sub_unit_type_count:hbe_canal_crossbow >= 1 has_country_modifier = hbe_civic_over_supply } set_variable = hbe_test_over_capacity_preserves_army }
 set_variable = { name = hbe_burden value = 20 }
 international_organization:hbe_circle_chengdu_plain = { set_variable = { name = hbe_civic_holder value = c:CHI } }
 hbe_civic_monthly = yes
 if = { limit = { international_organization:hbe_circle_chengdu_plain = { NOT = { has_variable = hbe_civic_holder } } } set_variable = hbe_test_orphan_office_cleared }
}'''
put('in_game/events/hbe_civic_test.txt','namespace = hbe_civic_test\n'+ '\n'.join(f'hbe_civic_test.{i} = {{ type = country_event hidden = yes immediate = {{ {body} }} }}' for i,body in [(1,' '.join(setup)),(2,' '.join(test2)),(3,test3),(4,test4),(5,test5)]))
put('in_game/common/tests/hbe_civic_runtime.txt','''hbe_civic_runtime = {
 year = 1337 end_year = 1339 fail_on_end_year = yes
 success = {
 c:BAB = { has_variable = hbe_test_native_policy has_variable = hbe_test_building_unlocked has_variable = hbe_test_policy_settlement has_variable = hbe_test_settlement_idempotent has_variable = hbe_test_operating_institution has_variable = hbe_test_office_appointed has_variable = hbe_test_office_expired has_variable = hbe_test_no_free_civic has_variable = hbe_test_upper_clamp has_variable = hbe_test_lower_clamp has_variable = hbe_test_supported_capacity has_variable = hbe_test_regiment_pressure has_variable = hbe_test_over_capacity_preserves_army }
 c:BAE = { has_variable = hbe_test_policy_settlement has_variable = hbe_test_vacancy_respected has_variable = hbe_test_successor }
 c:BAF = { has_variable = hbe_test_policy_settlement has_variable = hbe_test_paid_charge }
 is_situation_active = situation:hbe_banquet
 }
 success_effect = { test_log = HBE_CIVIC_RUNTIME_PASS }
}''')
print('Prepared real native research/building/policy/settlement/office tests; AI decisions disabled only in fixtures.')
