from pathlib import Path
import re
from pdxscript import blocks

def validate_annex_industry(mod,manifest,loc,check):
 if 'annex_industry_patch' not in manifest:return
 data=manifest['annex_industry_patch'];read=lambda rel:(mod/rel).read_text(encoding='utf-8-sig')
 hook=read('in_game/common/on_action/hbe_annex_industry_on_actions.txt')
 check('industry inheritance subscribes only to whole-country annex completion','on_annexed = {' in hook and all(k not in hook for k in ('on_game_start','monthly','on_location')))
 effects=read('in_game/common/scripted_effects/hbe_annex_industry_effects.txt')
 advances=read('in_game/common/advances/hbe_inherited_industry_licenses.txt')
 check('seven automatic civilian industry receipts are registered',len(blocks(advances,0))==7 and data['receipt_count']==7)
 check('inheritance grants fourteen buildings and eleven starter recipes',advances.count('unlock_building =')==14 and advances.count('unlock_production_method =')==11)
 check('inherited receipts grant no units advanced recipes or stat modifiers','unlock_unit' not in advances and '_advanced_production' not in advances and 'country_modifier' not in advances)
 check('inheritance does not require prior guest compact or common research','hbe_tech_common_4' not in effects and 'hbe_paid_bill' not in effects and 'hbe_yiqi' not in effects)
 check('inheritance only researches its seven receipt advances',set(re.findall(r'research_advance\s*=\s*advance_type:(\w+)',effects))=={r['advance'] for r in data['regions']})
 buildings=read('in_game/common/building_types/hbe_civic_buildings.txt');items={k:buildings[b:e] for k,_,b,e,_ in blocks(buildings,0)}
 for row in data['regions']:
  check(row['region']+' inherited permission localized',row['advance'] in loc and row['advance']+'_desc' in loc)
  for building in row['buildings']:
   body=items[building];check(building+' recognizes inherited permission in both potential and allow',body.count('has_advance = '+row['advance'])==2)
   check(building+' retains original geographic construction restriction','location_potential = { is_in_scripted_geography = scripted_geography:hbe_geo_'+row['region'] in body)
 forms=read('in_game/common/formable_countries/hbe_native_formables.txt');registered={k:forms[b:e] for k,_,b,e,_ in blocks(forms,0)}
 check('three real native formables are registered for the Formable tab',set(registered)=={'HQS_f','HQC_f','HQB_f'})
 for key,tag,region in [('HQS_f','HQS','sichuan'),('HQC_f','HQC','chongqing'),('HQB_f','HQB','bashu')]:
  check(key+' has native identity conditions effects and UI text',key in loc and all(v in registered[key] for v in ('tag = '+tag,'name = '+tag,'flag = '+tag,'hbe_can_form_'+region+' = yes','hbe_found_'+region+' = yes')))
  check(key+' flag texture registered',(mod/f'main_menu/gfx/coat_of_arms/textured_emblems/te_hbe_form_{region}.dds').is_file())
 decisions='\n'.join(p.read_text(encoding='utf-8-sig') for p in (mod/'in_game/common/decisions').glob('*.txt'))
 check('formed tags retain access to existing country-specific decisions',all(all(tag in m.split() for tag in ('HQS','HQC','HQB')) for m in re.findall(r'tags\s*=\s*\{([^{}]*)\}',decisions)))
