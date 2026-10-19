"""Source-only diplomacy tuning through native CB and organization interfaces."""
from build_support import snapshot_files
from pathlib import Path
import hashlib,json
from pdxscript import blocks,apply_edits
from apply_red_turban_actions_v032 import SCALE
from build_bashu_ai import build_bashu_ai

CB_FILE='in_game/common/casus_belli/red_turban_rebellions.txt'
PEACE_CB='cb_red_turban_rebellions_against_other_rebels'
VALUE_FILE='in_game/common/script_values/hbe_diplomacy_restraint.txt'
EMPIRE_FILE='in_game/common/international_organizations/hbe_empire.txt'
ADJUSTMENT='hbe_rtr_hbe_attacker_enthusiasm_adjustment'

def peace_override(native):
    node=next(b for b in blocks(native,0) if b[0]==PEACE_CB)
    assert not any(b[0]=='additional_war_enthusiasm_attacker' for b in blocks(native,1) if node[2]<=b[1]<node[3]), 'Native CB changed: review enthusiasm before replacing it.'
    return apply_edits(native,[(node[3],node[3],f'\tadditional_war_enthusiasm_attacker = {ADJUSTMENT}\n')])

def enable_member_tributaries(text):
    node=next(b for b in blocks(text,0) if b[0]=='hbe_empire')
    children=[b for b in blocks(text,1) if b[0]=='modifier' and node[2]<=b[1]<node[3]]
    assert len(children)<=1
    if children:
        child=children[0]
        if 'allow_tributary_subject' in text[child[2]:child[3]]:
            assert 'allow_tributary_subject = yes' in text[child[2]:child[3]]
            return text
        return apply_edits(text,[(child[3],child[3],' allow_tributary_subject = yes ')])
    return apply_edits(text,[(node[3],node[3],'    modifier = { allow_tributary_subject = yes }\n')])

def apply(out,root,game):
    out,root,game=map(Path,(out,root,game))
    assert SCALE==.30, 'The user explicitly retained the 30% action score.'
    def put(rel,text):
        p=out/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text+'\n',encoding='utf-8-sig')
    native=(game/CB_FILE).read_text(encoding='utf-8-sig')
    put(CB_FILE,peace_override(native))
    put(VALUE_FILE,f'''{ADJUSTMENT} = {{
 value = 0
 if = {{
  limit = {{
   exists = scope:attacker
   exists = scope:defender
   is_ai = yes
   this = scope:attacker
   hbe_is_red_turban_successor = yes
   NOT = {{ is_member_of_international_organization = international_organization:hbe_empire }}
   scope:defender = {{ is_member_of_international_organization = international_organization:hbe_empire }}
  }}
  subtract = 0.05
 }}
}}''')
    p=out/EMPIRE_FILE;old=p.read_text(encoding='utf-8-sig');new=enable_member_tributaries(old)
    assert enable_member_tributaries(new)==new
    p.write_text(new,encoding='utf-8-sig')
    ai=build_bashu_ai(out,root,{},put,game)
    mp=out/'build_manifest.json';m=json.loads(mp.read_text(encoding='utf-8-sig'))
    m['internal_ai']=ai
    report={'version':'0.3.2','source_only':True,'runtime_verified':False,'war_action_score_multiplier':SCALE,'annex_action_score_multiplier':SCALE,'peace_cb':PEACE_CB,'peace_attacker_enthusiasm_delta':-.05,'peace_only_ai_external_rtr_vs_hbe':True,'native_cb_sha256':hashlib.sha256((game/CB_FILE).read_bytes()).hexdigest(),'member_tributary_permission':'allow_tributary_subject','country_tag_exceptions':False,'native_tributary_definition_untouched':True,'internal_ai':ai,'forced_peace':False,'forced_wars':False}
    m['diplomacy_restraint_v032']=report
    if 'western_tributes_v032' in m:m['western_tributes_v032']['overlord_eligibility']='Native allow_tributary_subject permission from HBE member modifier'
    m['files']=snapshot_files(out)
    mp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return report

if __name__=='__main__':
    import sys
    root=Path(sys.argv[1]);print(json.dumps(apply(root/'mod/holy_bashu_empire',root,Path(sys.argv[2])/'game'),ensure_ascii=False))
