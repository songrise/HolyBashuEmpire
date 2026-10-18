from pathlib import Path
import re
from pdxscript import blocks

def validate(out,manifest,check):
 out=Path(out)
 def read(p):return (out/p).read_text(encoding='utf-8-sig')
 t=read('in_game/common/scripted_triggers/hbe_common_defense.txt')
 e=read('in_game/common/scripted_effects/hbe_common_defense.txt')
 io=read('in_game/common/international_organizations/hbe_empire.txt')
 empire=next(io[a:b] for k,_,a,b,_ in blocks(io,0) if k=='hbe_empire')
 event=read('in_game/events/hbe_common_defense.txt')
 gate=read('in_game/common/join_war_rules/hbe_isolation.txt')
 check('common defense waits for active Red Turbans and three monthly checks',all(s in e for s in ['is_situation_active = situation:red_turban_rebellions','var:hbe_common_defense_months >= 3','id = hbe_common_defense.1 days = 1']))
 check('common defense proposal belongs to current member emperor',all(s in t for s in ['is_leader_of_international_organization = international_organization:hbe_empire','NOT = { has_variable = hbe_common_defense_decided }']) and event.count('hbe_common_defense_choice_valid = yes')==1 and e.count('hbe_common_defense_choice_valid = yes')==3)
 check('common defense decision and clock belong to organization',e.count('international_organization:hbe_empire = {')>=4 and 'set_variable = hbe_common_defense_active' in e and 'remove_variable = hbe_common_defense_active' not in e)
 check('common defense keeps human choices and AI accepts by default',all(s in event for s in ['hbe_common_defense_accept = yes','hbe_common_defense_decline = yes','base = 100','base = 0']) and not re.search(r'add_(?:gold|prestige|country_modifier)',e+event))
 check('common defense reuses registered council illustration', '1000 = hbe_story_art_council' in event and 'hbe_story_art_council' in read('loading_screen/gfx/illustrations/database/hbe_story_illustrations.txt'))
 check('common defense uses native all-member defensive call and no automatic cobelligerency',all(s in empire for s in ['only_leader_country_joins_defensive_wars = no','joins_defensive_wars_as_co_belligerent = no','join_defensive_wars_always = {','has_variable = hbe_common_defense_active','scope:target = { NOT = { is_member_of_international_organization = international_organization:hbe_empire } }']))
 check('common defense does not enable offensive calls',all('join_offensive_wars_'+s+' = { always = no }' in empire for s in ['always','auto_call','can_call']))
 check('common defense needs no border exception after diplomacy opens', 'join_war_disabled_trigger = { always = no }' in gate and 'hbe_common_defense_join_allowed' not in t and 'scope:recipient = {' in empire)
 keys=[]
 for lang in ['simp_chinese','english']:
  loc=read(f'main_menu/localization/{lang}/hbe_common_defense_l_{lang}.yml');keys.append(set(re.findall(r'^ ([^ :]+):',loc,re.M)))
 check('common defense Chinese and English keys match',keys[0]==keys[1] and len(keys[0])==16)
 check('common defense notifies other members after either decision', e.count('hbe_common_defense_notify_members = yes')==2 and 'NOT = { this = scope:hbe_common_defense_decider }' in e and 'id = hbe_common_defense.2 days = 1' in e)
 check('common defense notice is once per member and shows both outcomes',all(s in event for s in ['hbe_common_defense.2 = {','NOT = { has_variable = hbe_common_defense_member_notified }','set_variable = hbe_common_defense_member_notified','hbe_common_defense.2.desc.accepted','hbe_common_defense.2.desc.declined']))
 check('common defense counted once in manifest and release metadata',manifest['common_defense_v032']['visible_events']==2 and manifest['release_v032']['visible_events']==508)
