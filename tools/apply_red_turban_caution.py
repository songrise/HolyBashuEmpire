from build_support import snapshot_files
from pathlib import Path
import json, sys
def apply(out,root):
    out=Path(out);p=out/'in_game/common/ai_scripted_expansion_score/hbe_red_turban_caution.txt'
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text('''# Native released-country setup retains rtr_yuan_allegiance even at value 0.
# This covers historical and dynamically generated factions after the crisis,
# including a faction that later forms China. It affects only HBE targets.
hbe_red_turban_caution = {
 attacker_potential = {
  NOT = { is_member_of_international_organization = international_organization:hbe_empire }
  OR = {
   has_variable = rtr_yuan_allegiance
   has_variable = rtr_is_new_china
   is_member_of_international_organization = international_organization:red_turban_rebels
  }
 }
 target_trigger = { is_member_of_international_organization = international_organization:hbe_empire }
 multiplier = { value = 0.65 }
}
''',encoding='utf-8-sig')
    return dict(version='0.3.1',file=p.relative_to(out).as_posix(),multiplier=.65,combined_with_existing_external_caution=.585,scope='Released Red Turban factions, including dynamic cultural countries and later China-formers; targets must currently be HBE members. No war prohibition or global aggression change. Score multiplier is not a direct probability.')
if __name__=='__main__':
    root=Path(sys.argv[1]);out=root/'mod/holy_bashu_empire';r=apply(out,root)
    (root/'docs/testing/red-turban-caution-v031.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    p=out/'build_manifest.json';m=json.loads(p.read_text(encoding='utf-8-sig'));m['red_turban_caution_patch']=r;m['files']=snapshot_files(out);p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Red Turban factions receive an additional 0.65 expansion score multiplier against HBE members only.')
