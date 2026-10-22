"""Focused invariants: preserve balance, era gates and existing event payloads."""
import json
import re
from pathlib import Path
from pdxscript import blocks

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / 'mod/holy_bashu_empire'
BASELINE = Path('C:/github/holy-bashu-empire/mod/holy_bashu_empire')
checks = []
def check(name, ok):
    checks.append(dict(name=name, passed=bool(ok)))
    if not ok: raise AssertionError(name)

def definitions(path):
    text = path.read_text(encoding='utf-8-sig')
    return {k:text[s:e] for k,_,s,e,_ in blocks(text,0)}

OLD = 'hbe_tech_central_hills_8'
NEW = 'hbe_tech_central_hills_witness_8'
active = definitions(MOD / 'in_game/common/advances/hbe_advances.txt')
old = definitions(BASELINE / 'in_game/common/advances/hbe_advances.txt')
check('Active advance count unchanged', len(active) == len(old))
for name, body in old.items():
    key = name.replace(OLD, NEW)
    check(key + ': remains registered', key in active)
    current = active[key]
    for field in ('age',):
        pattern = r'\b'+field+r'\s*=\s*(\S+)'
        check(key + ': ' + field + ' unchanged', re.search(pattern, body)[1] == re.search(pattern,current)[1])
    for field in ('requires', 'allow', 'potential'):
        if field == 'requires':
            expected = re.findall(r'\brequires\s*=\s*(\S+)', body)
            actual = re.findall(r'\brequires\s*=\s*(\S+)', current)
            check(key + ': parent gate unchanged', [v.replace(OLD,NEW) for v in expected] == actual)
        else:
            a = next(body[s:e] for k,_,s,e,_ in blocks(body,0) if k==field)
            b = next(current[s:e] for k,_,s,e,_ in blocks(current,0) if k==field)
            check(key + ': ' + field + ' unchanged', re.sub(r'\s+',' ',a.replace(OLD,NEW)).strip() == re.sub(r'\s+',' ',b).strip())
    # All immediate scalar technology rewards (including negative cost/time
    # modifiers) must stay at the previously requested 0.8x values.
    scalar = lambda t: dict(re.findall(r'(?m)^\s*(\w+)\s*=\s*(-?\d+(?:\.\d+)?)\s*$',t))
    check(key + ': existing scalar rewards unchanged', scalar(body) == scalar(current))

goods = definitions(MOD / 'main_menu/common/modifier_type_definitions/hbe_observer_goods_types.txt')
check('All 32 required goods types registered', len(goods)==32)
for name, body in goods.items():
    check(name + ': correct kind', ('boolean = yes' if name.endswith('used_for_minting') or name.startswith(('ban_', 'can_extract_')) else 'percent = yes') in body)
for lang in ('simp_chinese','english'):
    data = '\n'.join(p.read_text(encoding='utf-8-sig') for p in (MOD/'main_menu/localization'/lang).glob('*.yml'))
    check(lang + ': colliding description key absent', not re.search(r'(?m)^\s*'+OLD+r'_desc:',data))
    for key in ('hbe_party_points_desc','hbe_round_desc','hbe_round_month_desc','hbe_feast_total_desc','hbe_completed_projects_desc',NEW+'_desc','hbe_opening_family.1.title'):
        check(lang + ': ' + key, re.search(r'(?m)^\s*'+re.escape(key)+r':',data) is not None)
count=0
for path in (MOD/'in_game/events').glob('hbe*events.txt'):
    for name,body in definitions(path).items():
        if not re.fullmatch(r'hbe\w*\.\d+',name): continue
        count+=1
        check(name + ': title and outcome registered', bool(re.search(r'\btitle\s*=',body)) and bool(re.search(r'\boutcome\s*=',body)))
check('Existing event count preserved', count==118)

from apply_observer_hotfix import PRODUCERS
buildings=definitions(MOD/'in_game/common/building_types/hbe_civic_buildings.txt')
baseline_buildings=definitions(BASELINE/'in_game/common/building_types/hbe_civic_buildings.txt')
for region,building,good,amount,tier,_,_ in PRODUCERS:
    body=buildings[building]
    prod=next(body[s:e] for k,_,s,e,_ in blocks(body,0) if k=='unique_production_methods')
    methods={k:prod[s:e] for k,_,s,e,_ in blocks(prod,0)}
    check(building + ': one production-method definition', len([b for b in blocks(body,0) if b[0]=='unique_production_methods'])==1)
    basic='hbe_'+region+'_basic_production'
    check(building + ': real specialty output', 'produced = '+good in methods[basic] and abs(float(re.search(r'output\s*=\s*([\d.]+)',methods[basic])[1])-amount)<1e-9)
    check(building + ': ordinary fallback kept', 'hbe_'+region+'_ordinary_production' in methods)
    original=baseline_buildings[building]
    original_prod='\n'.join(original[s:e] for k,_,s,e,_ in blocks(original,0) if k=='unique_production_methods')
    for name,_,s,e,_ in blocks(original_prod,0):
        if 'advanced_production' in name or 'paper_production' in name:
            check(name + ': advanced recipe unchanged', re.sub(r'\s+',' ',original_prod[s:e]).strip() == re.sub(r'\s+',' ',methods[name]).strip())
    node='hbe_tech_'+region+'_'+str(tier)
    check(basic + ': original unlock at expected tier', 'unlock_production_method = '+basic in active[node])
    check(building + ': potential/allow untouched', all(re.sub(r'\s+',' ',next(original[s:e] for k,_,s,e,_ in blocks(original,0) if k==f)).strip() == re.sub(r'\s+',' ',next(body[s:e] for k,_,s,e,_ in blocks(body,0) if k==f)).strip() for f in ('country_potential','location_potential','allow')))
check('Paper institution remains second era', 'age = age_2_renaissance' in active['hbe_tech_northern_shudao_6'])
check('Unit statistics and recruitment gates untouched', (MOD/'in_game/common/unit_types/hbe_civic_units.txt').read_bytes() == (BASELINE/'in_game/common/unit_types/hbe_civic_units.txt').read_bytes())
score=(MOD/'in_game/common/ai_scripted_expansion_score/hbe_external_caution.txt').read_text(encoding='utf-8-sig')
check('Only external target score adjusted', 'value = 0.90' in score and 'attacker_potential = { NOT = {' in score and 'target_trigger = { is_member' in score and 'never_attack' not in score)
out=ROOT/'docs/testing/observer-hotfix-static.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(dict(checks=checks,passed=len(checks),failed=0),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(f'{len(checks)} focused observer-hotfix invariants passed.')
