"""Static preservation and scope checks. Never launches EU5."""
from pathlib import Path
import re,hashlib
from pdxscript import blocks,tokens
from apply_diplomacy_restraint_v032 import CB_FILE,PEACE_CB,VALUE_FILE,EMPIRE_FILE,ADJUSTMENT,peace_override,enable_member_tributaries

def validate(out,game,manifest,check):
    out,game=Path(out),Path(game)
    f=manifest.get('diplomacy_restraint_v032')
    if not f:return
    get=lambda rel:(out/rel).read_text(encoding='utf-8-sig')
    native=(game/CB_FILE).read_text(encoding='utf-8-sig');new=get(CB_FILE)
    check('diplomacy keeps native red war and annex action scores at 30 percent',f['war_action_score_multiplier']==f['annex_action_score_multiplier']==manifest['red_turban_actions_v032']['positive_action_score_multiplier']==.30)
    check('peace CB source hash pinned',f['native_cb_sha256']==hashlib.sha256((game/CB_FILE).read_bytes()).hexdigest())
    check('peace override changes only scoped attacker enthusiasm',new==peace_override(native)+'\n')
    olddefs={b[0]:native[b[1]:b[4]] for b in blocks(native,0)};newdefs={b[0]:new[b[1]:b[4]] for b in blocks(new,0)}
    check('all native Red Turban CB definitions retained',olddefs.keys()==newdefs.keys())
    check('Yuan rebellion and suppression CBs unchanged',all(newdefs[k]==v for k,v in olddefs.items() if k!=PEACE_CB))
    v=get(VALUE_FILE)
    check('peace nudge is only 0.05 enthusiasm', 'value = 0' in v and v.count('subtract = 0.05')==1 and f['peace_attacker_enthusiasm_delta']==-.05)
    check('peace adjustment excludes human and allied secondary attackers',all(s in v for s in ['is_ai = yes','this = scope:attacker','exists = scope:attacker','exists = scope:defender']))
    check('peace adjustment limited to outside Red Turbans attacking HBE',all(s in v for s in ['hbe_is_red_turban_successor = yes','NOT = { is_member_of_international_organization = international_organization:hbe_empire }','scope:defender = { is_member_of_international_organization = international_organization:hbe_empire }']))
    check('peace path uses native CB interface without forced treaties',f'additional_war_enthusiasm_attacker = {ADJUSTMENT}' in new and not re.search(r'\b(make_peace|white_peace|end_war|declare_war)\s*=',v))
    empire=get(EMPIRE_FILE);node=next(b for b in blocks(empire,0) if b[0]=='hbe_empire')
    membermods=[b for b in blocks(empire,1) if b[0]=='modifier' and node[2]<=b[1]<node[3]]
    check('native tributary permission is an HBE member modifier',len(membermods)==1 and 'allow_tributary_subject = yes' in empire[membermods[0][2]:membermods[0][3]])
    check('tributary permission has no country tag or government exception',not re.search(r'\b(HOR|BAB|GYE|NYA|CKL)\b',empire[membermods[0][2]:membermods[0][3]]) and not f['country_tag_exceptions'])
    check('member tributary capability patch is idempotent',enable_member_tributaries(empire)==empire)
    check('native tributary type is not overridden',not (out/'in_game/common/subject_types/tributary.txt').exists())
    ai=get('in_game/common/ai_scripted_expansion_score/hbe_internal_rivalry.txt')
    check('internal expansion pressure lowered to 0.85 or 0.86 and one bonus point',all(s in ai for s in ['value = 0.85','add = 0.01','score = { add = 1 }']) and manifest['internal_ai']['base_multiplier']==.85)
    target=get('in_game/common/ai_scripted_expansion_target/hbe_neighbors.txt')
    check('internal suggested targets require 15 or 10 years of peace','months_since_war >= 180' in target and 'months_since_war >= 120' in target)
    check('internal suggested target score reduced', 'score = { add = scope:target.country_tax_base multiply = 3 add = 2 }' in target)
    am=get('main_menu/common/static_modifiers/hbe_ai_modifiers.txt')
    check('internal AI boost reduced and war interval lengthened','aggressiveness_modifier = 0.02' in am and 'ai_months_between_wars = 3' in am)
    effects=get('in_game/common/scripted_effects/hbe_ai_effects.txt')
    check('internal AI modifier remains AI only and is cleaned up','is_ai = yes' in effects and 'months_since_war >= 120' in effects and 'else = { remove_country_modifier = hbe_ai_internal_ambition }' in effects)
    check('internal rules retain alliance and high burden guards','is_allied_with' in ai and 'var:hbe_burden >= 70' in ai)
    check('diplomacy tuning has no forced war or annexation',not re.search(r'\b(declare_war|start_war|remove_truce|annex_country)\s*=',ai+'\n'+target+'\n'+effects))
