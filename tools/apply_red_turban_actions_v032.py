"""Reduce Red Turban action scores only for external factions targeting HBE."""
from pathlib import Path
import hashlib,json,re
from pdxscript import blocks,apply_edits

WAR='rtr_declare_war_for_regional_supremacy'
WAR_FILE='in_game/common/generic_actions/red_turban_rebellions.txt'
ANNEX='rtr_demand_annexation'
ANNEX_FILE='in_game/common/country_interactions/rtr_demand_annexation.txt'
FACTIONS=('CSO','CTW','CHE','WUU','CFN','CMO','CXI','CGU','MNG','CNP','CDN','CSI','CKO','CNA')
SCALE=.30

def child(text,parent,key):
    outer=next(b for b in blocks(text,0) if b[0]==parent)
    matches=[b for b in blocks(text,1) if b[0]==key and outer[2]<=b[1]<outer[3]]
    assert len(matches)==1,(parent,key)
    return matches[0]

def apply(out,root,game):
    out,root,game=map(Path,(out,root,game));files={};values=[];native_hashes={}
    native_event=(game/'in_game/events/situations/red_turban_rebellions.txt').read_text(encoding='utf-8-sig')
    assert set(re.findall(r'rtr_release_warlord_tag\s*=\s*\{\s*tag\s*=\s*(\w+)',native_event))==set(FACTIONS),'Native faction roster changed; review coverage.'
    trigger='''hbe_is_red_turban_successor = {
 OR = {
  has_variable = rtr_yuan_allegiance
  has_variable = rtr_is_new_china
  is_member_of_international_organization = international_organization:red_turban_rebels
  modifier:can_create_red_turban_rebellions_cb = yes
'''+''.join(f'  has_or_had_tag = {tag}\n' for tag in FACTIONS)+''' }
}
hbe_rtr_external_actor = {
 exists = scope:actor
 scope:actor = {
  NOT = { is_member_of_international_organization = international_organization:hbe_empire }
  hbe_is_red_turban_successor = yes
 }
}
hbe_rtr_war_targets_hbe = {
 hbe_rtr_external_actor = yes
 exists = scope:target
 scope:target = { is_member_of_international_organization = international_organization:hbe_empire }
}
hbe_rtr_annex_targets_hbe = {
 hbe_rtr_external_actor = yes
 exists = scope:recipient
 scope:recipient = { is_member_of_international_organization = international_organization:hbe_empire }
}
'''
    files['in_game/common/scripted_triggers/hbe_red_turban_actions.txt']=trigger
    for rel,key,kind in ((WAR_FILE,WAR,'war'),(ANNEX_FILE,ANNEX,'annex')):
        native=(game/rel).read_text(encoding='utf-8-sig');native_hashes[rel]=hashlib.sha256((game/rel).read_bytes()).hexdigest()
        score=child(native,key,'ai_will_do');body=native[score[2]:score[3]]
        base=f'hbe_rtr_native_{kind}_score';final=f'hbe_rtr_{kind}_score'
        values.append(base+' = {\n'+body+'\n}\n')
        values.append(f'''{final} = {{
 value = {base}
 if = {{ limit = {{ hbe_rtr_{kind}_targets_hbe = yes {base} > 0 }} multiply = {SCALE} }}
}}
''')
        edits=[(score[2],score[3],f'\n\t\tvalue = {final}\n\t')]
        if kind=='annex':
            accept=child(native,key,'accept')
            extra='''
\t\tif = {
\t\t\tlimit = { hbe_rtr_annex_targets_hbe = yes }
\t\t\tadd = { desc = "hbe_rtr_sovereignty_reason" value = hbe_rtr_annex_acceptance_penalty }
\t\t}
\t'''
            edits.append((accept[3],accept[3],extra))
        modified=apply_edits(native,edits)
        # Retain every native definition and every action outside the two intended fields.
        assert [b[0] for b in blocks(modified,0)]==[b[0] for b in blocks(native,0)]
        files[rel]=modified
    values.append('''hbe_rtr_annex_acceptance_penalty = {
 value = 0
 if = { limit = { hbe_rtr_annex_targets_hbe = yes } value = -100 }
}
''')
    files['in_game/common/script_values/hbe_red_turban_actions.txt']='\n'.join(values)
    for lang,label in (('simp_chinese','帝国诸侯拒绝归并'),('english','Imperial sovereignty')):
        files[f'main_menu/localization/{lang}/hbe_red_turban_actions_l_{lang}.yml']=f'l_{lang}:\n hbe_rtr_sovereignty_reason: "{label}"\n'
    # Reuse the same faction predicate for the existing ordinary expansion multiplier.
    files['in_game/common/ai_scripted_expansion_score/hbe_red_turban_caution.txt']='''hbe_red_turban_caution = {
 attacker_potential = {
  NOT = { is_member_of_international_organization = international_organization:hbe_empire }
  hbe_is_red_turban_successor = yes
 }
 target_trigger = { is_member_of_international_organization = international_organization:hbe_empire }
 multiplier = { value = 0.65 }
}
'''
    for rel,text in files.items():
        p=out/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8-sig')
    report={'version':'0.3.2','release_channel':'0.3.2 hotfix','scope_revision':2,'positive_action_score_multiplier':SCALE,'negative_scores_unchanged':True,'annex_acceptance_penalty':-100,'historical_faction_tags':list(FACTIONS),'dynamic_factions':'Native Red Turban CB permission, rtr_yuan_allegiance, rtr_is_new_china or Red Turban organization membership','target':'Current HBE members; actor must be outside HBE','native_overrides':native_hashes,'files':list(files),'native_effects_and_eligibility_unchanged':True,'cooldown_added':False}
    p=out/'build_manifest.json';m=json.loads(p.read_text(encoding='utf-8-sig'));m['red_turban_actions_v032']=report
    m['files']={p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and p.name!='build_manifest.json'}
    p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return report

if __name__=='__main__':
    import sys
    root=Path(sys.argv[1]);print(json.dumps(apply(root/'mod/holy_bashu_empire',root,Path(sys.argv[2])/'game'),ensure_ascii=False))
