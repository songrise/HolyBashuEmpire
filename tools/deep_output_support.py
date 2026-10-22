from pathlib import Path
import re,json,sys,hashlib
from pdxscript import blocks,apply_edits
def apply(out,report):
 out=Path(out);path=out/'in_game/common/scripted_effects/hbe_output_support_effects.txt'
 helper=[]
 for kind in ('production','food'):
  helper.append(f'''hbe_grant_{kind}_support = {{
 if = {{ limit = {{ custom_tooltip = {{ text = hbe_output_support_available_tt
 OR = {{ NOT = {{ has_country_modifier = hbe_shared_{kind}_support }} var:hbe_{kind}_support_strength <= $strength$ }}
 }} }}
 hidden_effect = {{ set_variable = {{ name = hbe_{kind}_support_strength value = $strength$ }} }}
 add_country_modifier = {{ modifier = hbe_shared_{kind}_support size = $strength$ years = $years$ months = $months$ days = $days$ mode = replace }}
 }}
}}''')
 migrate=['hbe_migrate_legacy_output_supports = { if = { limit = { is_member_of_international_organization = international_organization:hbe_empire NOT = { has_variable = hbe_legacy_output_migrated } }']
 identities=set()
 for row in report['pooled_support']:
  if row['empty_original']:
   identities.add(row['modifier'])
  for typ,value in row['values'].items():
   kind='production' if typ=='global_production_efficiency' else 'food'
   migrate.append(f'if = {{ limit = {{ has_country_modifier = {row["modifier"]} NOT = {{ has_country_modifier = hbe_shared_{kind}_support }} }} hbe_grant_{kind}_support = {{ strength = {float(value)*100:g} years = 0 months = 3 days = 0 }} }}')
 p=out/'main_menu/common/static_modifiers/hbe_legacy_output_flags.txt'
 p.write_text(''.join(key+' = { } # Existing-save identity only.\n' for key in sorted(identities)),encoding='utf-8-sig')
 migrate+=['set_variable = hbe_legacy_output_migrated } }'];helper.append('\n'.join(migrate))
 path.write_text('\n\n'.join(helper)+'\n',encoding='utf-8-sig')
 # Use bounded refresh, not additive duration extension. Keep stronger existing arrangements.
 for folder in ('in_game/events','in_game/common/scripted_effects','in_game/common/decisions','in_game/common/on_action'):
  for p in (out/folder).glob('hbe*.txt'):
   if p==path:continue
   t=p.read_text(encoding='utf-8-sig');edits=[]
   for key,outer,a,z,end in blocks(t):
    if key!='add_country_modifier':continue
    body=t[a:z];m=re.search(r'modifier\s*=\s*hbe_shared_(production|food)_support',body)
    if not m:continue
    strength=re.search(r'size\s*=\s*(\S+)',body)[1]
    params={k:(re.search(r'\b'+k+r'\s*=\s*(\S+)',body)[1] if re.search(r'\b'+k+r'\s*=\s*(\S+)',body) else '0') for k in ('years','months','days')}
    new='hbe_grant_'+m[1]+'_support = { strength = '+strength+' '+' '.join(k+' = '+v for k,v in params.items())+' }'
    edits.append((outer,end,new))
   if edits:p.write_text(apply_edits(t,edits),encoding='utf-8-sig')
 p=out/'in_game/common/on_action/hbe_deep_balance_on_actions.txt';p.write_text('monthly_country_pulse = { on_actions = { hbe_deep_balance_monthly } }\nhbe_deep_balance_monthly = { trigger = { is_member_of_international_organization = international_organization:hbe_empire } effect = { hbe_migrate_legacy_output_supports = yes } }\n',encoding='utf-8-sig')
 for lang in ('simp_chinese','english'):
  p=out/f'main_menu/localization/{lang}/hbe_deep_balance_l_{lang}.yml';t=p.read_text(encoding='utf-8-sig')
  if lang=='simp_chinese':t=t.replace('取较强效果并延续期限','取较强效果；同强度的新安排刷新期限')
  else:t=t.replace('retain the strongest effect and extend its duration','retain the stronger effect and refresh the duration for equal-strength arrangements')
  more={'hbe_output_support_available_tt':'当前没有同类安排，或本次安排不弱于现有安排。' if lang=='simp_chinese' else 'No arrangement of this kind is active, or this arrangement is at least as strong.', 'hbe_legacy_output_migrated':'旧产能安排已衔接' if lang=='simp_chinese' else 'Legacy output arrangements migrated','hbe_production_support_strength':'当前生产筹备强度' if lang=='simp_chinese' else 'Current production arrangement strength','hbe_food_support_strength':'当前粮务协作强度' if lang=='simp_chinese' else 'Current food arrangement strength'}
  t+=''.join(' '+k+': '+json.dumps(v,ensure_ascii=False)+'\n' for k,v in more.items());p.write_text(t,encoding='utf-8-sig')
 report['support_duration_rule']='Higher/equal support replaces and refreshes the existing timed modifier. Weaker arrangements preserve it; durations never add.'
 report['existing_save_migration']='Empty legacy modifier IDs remain registered. At first monthly pulse, active old arrangements bridge to bounded support for three months; existing non-output effects and event-chain flags remain.'
 return report

