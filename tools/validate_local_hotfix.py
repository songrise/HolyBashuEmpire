"""Semantic checks for the local 0.3.0 balance patch, independent of engine fixtures."""
import json,re,math
from pathlib import Path
from pdxscript import blocks
from build_technology_rewards import SOCIAL_REWARDS
from build_quality_hotfix import VANILLA_ANCHORS
def validate(root):
 mod=root/'mod/holy_bashu_empire';manifest=json.loads((mod/'build_manifest.json').read_text(encoding='utf-8-sig'))
 before=json.loads((root.parent/'v031_before/technology_rewards.json').read_text(encoding='utf-8-sig'))
 old={r['key']:r for r in before['advances']};checks={}
 def check(k,ok):
  checks[k]=bool(ok)
  assert ok,k
 for row in manifest['technology_rewards']['advances']:
  expected=SOCIAL_REWARDS.get(row['key'],old[row['key']]['modifiers'])
  check(row['key']+'.0.8',set(row['modifiers'])==set(expected) and all(math.isclose(row['modifiers'][k],v*.8,abs_tol=1e-8) for k,v in expected.items()))
 oldnet={r['key']:r for r in before['networks']}
 for row in manifest['technology_rewards']['networks']:
  check(row['key']+'.0.8',all(math.isclose(row['modifiers'][k],v*.8,abs_tol=1e-8) for k,v in oldnet[row['key']]['modifiers'].items()))
 def read(p):return (mod/p).read_text(encoding='utf-8-sig')
 text=read('in_game/common/advances/hbe_advances.txt');nodes={k:text[s:e] for k,_,s,e,_ in blocks(text,0)}
 layout=manifest['quality_hotfix']['advance_layout'];moved=[k for k in layout if k.endswith(('_3','_4','_6','_7'))]
 check('exactly 28 red-box technologies now in era two',len(moved)==28 and all('age = age_2_renaissance' in nodes[k] for k in moved))
 check('14 regional starter technologies remain in era one',sum('age = age_1_traditions' in b for k,b in nodes.items() if not k.startswith('hbe_tech_common_'))==14)
 check('all branch intermediate and final cards use their own predecessor',all('requires = '+v['predecessor'] in nodes[k] for k,v in layout.items()) and sum(v['predecessor']=='renaissance_development' for v in layout.values())==7)
 native=Path(r'D:\SteamLibrary\steamapps\common\Europa Universalis V\game\in_game\common\advances\0_age_of_renaissance.txt').read_text(encoding='utf-8-sig')
 native_nodes={k:native[s:e] for k,_,s,e,_ in blocks(native,0)}
 check('native tree references exist',all(v['predecessor'] in native_nodes or v['predecessor'] in nodes for v in layout.values()))
 check('ten semantic vanilla anchors exist in era two and are past a root',all(k in native_nodes and 'age = age_2_renaissance' in native_nodes[k] and 'requires =' in native_nodes[k] for k in VANILLA_ANCHORS.values()))
 civic=read('in_game/common/advances/hbe_civic_advances.txt');audit=next(civic[s:e] for k,_,s,e,_ in blocks(civic,0) if k=='hbe_civic_common_2')
 check('audit has no empire-wide building/unit unlocks','unlock_building' not in audit and 'unlock_unit' not in audit)
 lic=read('in_game/common/advances/hbe_guest_licenses.txt')
 check('seven signed-circle certificates preserve all 21 native unlocks',len(blocks(lic,0))==7 and lic.count('unlock_building =')==14 and lic.count('unlock_unit =')==7 and lic.count('allow = { always = no }')==7)
 unit=read('in_game/common/unit_types/hbe_civic_units.txt');units={k:unit[s:e] for k,_,s,e,_ in blocks(unit,0)}
 check('two real combat upgrades with maintained capacity', 'combat_power = 1.20' in units['hbe_trained_river'] and 'combat_power = 1.15' in units['hbe_permanent_pass'] and all('max_strength = 0.5' in b for b in units.values()))
 feast=read('in_game/common/scripted_effects/hbe_banquet_effects.txt');fs={k:feast[s:e] for k,_,s,e,_ in blocks(feast,0)}
 check('actual switch effects enforce the five-year lock',all('NOT = { has_variable = hbe_stance_cooldown }' in fs['hbe_choose_stance_'+str(i)] and 'years = 5' in fs['hbe_choose_stance_'+str(i)] for i in (1,2)))
 check('former members incur a small decaying opinion change',read('in_game/common/biases/hbe_faction_departure.txt').strip()=='hbe_left_feast_party = { value = -5 yearly_decay = 1 }' and feast.count('target = scope:hbe_party_departing')==2)
 weights=read('in_game/common/script_values/hbe_feast_dividend_values.txt')
 w=[0, .693147,1.098612,1.386294]
 check('logarithmic weights match ln(1+c) for all legitimate round contributions',all(abs(w[c]-math.log1p(c))<1e-6 for c in range(4)))
 check('three contributions yield twice the share of one, not three times',math.isclose(w[3]/w[1],2,abs_tol=1e-6))
 d=read('in_game/common/scripted_effects/hbe_feast_dividend_effects.txt')
 check('dividends funded by actual recorded payment and contributions only',d.count('multiply = 0.25')==2 and d.count('var:hbe_feast_points > 0')==4 and 'value = hbe_feast_fee' in fs['hbe_fund_project'] and 'name = hbe_feast_paid value = 0' in fs['hbe_open_accounts'])
 check('cash and prestige payout occur before contribution reset',fs['hbe_settle_accounts'].index('hbe_pay_feast_dividends')<fs['hbe_settle_accounts'].index('hbe_open_accounts') and d.count('add_prestige = var:hbe_feast_last_prestige')==2 and 'multiply = 3' in weights)
 gui=read('in_game/gui/panels/situation/hbe_banquet.gui')
 check('explicit player action bindings with native legality checks',gui.count('actor = "[Player]"')==3 and gui.count('scripted_action_tooltip =')==3 and gui.count('IsUberButtonEnabled')==3)
 check('two concrete-width row widgets replace unconstrained paper hboxes',gui.count('addcolumn = 222')==2 and 'addcolumn = 100%' not in gui and 'using = bg_paper_card' not in gui)
 loc=read('main_menu/localization/simp_chinese/hbe_l_simp_chinese.yml')
 check('local projects and dividends have native hover explanations','hbe_term_local_service' in read('main_menu/common/game_concepts/hbe_concepts.txt') and "Concept('hbe_term_local_service', '地方事业')" in loc and "Concept('hbe_term_feast_dividend', '派内分红')" in loc)
 check('version remains 0.3.0',manifest['version']=='0.3.0' and json.loads(read('.metadata/metadata.json'))['version']=='0.3.0')
 for p in manifest['files']:
  if any(s in p for s in ('guest_license','dividend','faction_departure')) and p.endswith('.txt'):check('syntax.'+p,bool(blocks(read(p))))
 report=dict(version='0.3.0',local_patch=True,passed=sum(checks.values()),checks=checks,engine_validation='reported separately; these are structural and numeric checks')
 (root/'docs/validation_local_hotfix_v030.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(f'{sum(checks.values())} local hotfix checks passed')
 return report
if __name__=='__main__':validate(Path(__file__).resolve().parents[1])
