"""Ensure the native action overrides retain original gameplay and scoring inputs."""
from pdxscript import blocks,tokens
from apply_red_turban_actions_v032 import WAR,WAR_FILE,ANNEX,ANNEX_FILE,FACTIONS,child
import re,hashlib

def validate(m,game,manifest,check):
    feature=manifest.get('red_turban_actions_v032')
    if not feature:return
    get=lambda p:p.read_text(encoding='utf-8-sig')
    values=get(m/'in_game/common/script_values/hbe_red_turban_actions.txt')
    trigger=get(m/'in_game/common/scripted_triggers/hbe_red_turban_actions.txt')
    event=get(game/'in_game/events/situations/red_turban_rebellions.txt')
    check('all native historical rebel factions covered',set(FACTIONS)==set(re.findall(r'rtr_release_warlord_tag\s*=\s*\{\s*tag\s*=\s*(\w+)',event)))
    check('Wu Han and dynamic successor predicates covered',all(x in trigger for x in ('has_or_had_tag = WUU','has_or_had_tag = CHE','has_variable = rtr_yuan_allegiance','has_variable = rtr_is_new_china')))
    check('actor must be outside HBE', 'NOT = { is_member_of_international_organization = international_organization:hbe_empire }' in trigger)
    check('unmarked dynamic warlords with native CB permission covered','modifier:can_create_red_turban_rebellions_cb = yes' in trigger)
    for rel,key,kind in ((WAR_FILE,WAR,'war'),(ANNEX_FILE,ANNEX,'annex')):
        old=get(game/rel);new=get(m/rel)
        check(kind+' native source hash pinned',hashlib.sha256((game/rel).read_bytes()).hexdigest()==feature['native_overrides'][rel])
        old_defs={b[0]:old[b[1]:b[4]] for b in blocks(old,0)};new_defs={b[0]:new[b[1]:b[4]] for b in blocks(new,0)}
        check(kind+' native definitions retained',old_defs.keys()==new_defs.keys())
        check(kind+' unrelated actions untouched',all(new_defs[k]==v for k,v in old_defs.items() if k!=key))
        nb=child(old,key,'ai_will_do');vb=next(b for b in blocks(values,0) if b[0]==f'hbe_rtr_native_{kind}_score')
        check(kind+' original score formula preserved',[t.value for t in tokens(old[nb[2]:nb[3]])]==[t.value for t in tokens(values[vb[2]:vb[3]])])
        for part in ('potential','allow','ai_prerequisite','effect','reject_effect','cooldown','enabled'):
            ob=[b for b in blocks(old_defs[key],1) if b[0]==part];nb=[b for b in blocks(new_defs[key],1) if b[0]==part]
            check(kind+' '+part+' retains native behavior',[old_defs[key][b[1]:b[4]] for b in ob]==[new_defs[key][b[1]:b[4]] for b in nb])
        check(kind+' negative scores retain native value',f'hbe_rtr_{kind}_targets_hbe = yes hbe_rtr_native_{kind}_score > 0' in values)
        check(kind+' positive score multiplier is 30%',f'hbe_rtr_{kind}_targets_hbe = yes hbe_rtr_native_{kind}_score > 0 }} multiply = 0.3' in values)
    old=get(game/ANNEX_FILE);new=get(m/ANNEX_FILE);ob=child(old,ANNEX,'accept');nb=child(new,ANNEX,'accept')
    check('native acceptance reasons preserved',new[nb[2]:nb[3]].lstrip().startswith(old[ob[2]:ob[3]].strip()))
    check('scoped acceptance penalty is minus 100','if = { limit = { hbe_rtr_annex_targets_hbe = yes } value = -100 }' in values)
