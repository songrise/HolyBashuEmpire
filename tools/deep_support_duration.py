from pathlib import Path
import sys,json,re,hashlib
from pdxscript import blocks,apply_edits
def repair(out,report):
 out=Path(out);p=out/'in_game/common/scripted_effects/hbe_output_support_effects.txt'
 t=p.read_text(encoding='utf-8-sig');helpers=[]
 for kind in ('production','food'):
  for unit in ('years','months','days'):
   helpers.append(f'''hbe_grant_{kind}_support_{unit} = {{
 if = {{ limit = {{ custom_tooltip = {{ text = hbe_output_support_available_tt
 OR = {{ NOT = {{ has_country_modifier = hbe_shared_{kind}_support }} var:hbe_{kind}_support_strength <= $strength$ }} }} }}
 hidden_effect = {{ set_variable = {{ name = hbe_{kind}_support_strength value = $strength$ }} }}
 add_country_modifier = {{ modifier = hbe_shared_{kind}_support size = $strength$ {unit} = $duration$ mode = replace }}
 }}
}}''')
 migration=next(t[outer:end] for k,outer,a,z,end in blocks(t,0) if k=='hbe_migrate_legacy_output_supports')
 # Compare all existing legacy arrangements, not only the first row encountered.
 marker='hbe_migrate_legacy_output_supports = { if = { limit = { is_member_of_international_organization = international_organization:hbe_empire NOT = { has_variable = hbe_legacy_output_migrated } }'
 migration=migration.replace(marker,marker+' if = { limit = { NOT = { has_country_modifier = hbe_shared_production_support } } set_variable = hbe_migrate_production_needed } if = { limit = { NOT = { has_country_modifier = hbe_shared_food_support } } set_variable = hbe_migrate_food_needed }')
 migration=migration.replace('NOT = { has_country_modifier = hbe_shared_production_support } } hbe_grant','has_variable = hbe_migrate_production_needed } hbe_grant').replace('NOT = { has_country_modifier = hbe_shared_food_support } } hbe_grant','has_variable = hbe_migrate_food_needed } hbe_grant')
 migration=migration.replace('set_variable = hbe_legacy_output_migrated','remove_variable = hbe_migrate_production_needed remove_variable = hbe_migrate_food_needed set_variable = hbe_legacy_output_migrated')
 helpers.append(migration);p.write_text('\n\n'.join(helpers)+'\n',encoding='utf-8-sig')
 for folder in ('in_game/events','in_game/common/scripted_effects','in_game/common/decisions','in_game/common/on_action'):
  for p in (out/folder).glob('hbe*.txt'):
   t=p.read_text(encoding='utf-8-sig');edits=[]
   for key,outer,a,z,end in blocks(t):
    m=re.fullmatch(r'hbe_grant_(production|food)_support',key)
    if not m:continue
    b=t[a:z];strength=re.search(r'\bstrength\s*=\s*(\S+)',b)[1];periods={k:float(re.search(r'\b'+k+r'\s*=\s*(\S+)',b)[1]) for k in ('years','months','days')}
    active=[k for k,v in periods.items() if v>0];assert len(active)==1,(key,periods)
    unit=active[0];duration=f'{periods[unit]:g}'
    edits.append((outer,end,f'hbe_grant_{m[1]}_support_{unit} = {{ strength = {strength} duration = {duration} }}'))
   if edits:p.write_text(apply_edits(t,edits),encoding='utf-8-sig')
 report['support_duration_rule']='Single-unit duration only. Stronger/equal arrangements replace and refresh; weaker arrangements preserve the active effect. Duration does not add.'
 for lang in ('simp_chinese','english'):
  for p in (out/f'main_menu/localization/{lang}').glob('hbe*.yml'):
   t=p.read_text(encoding='utf-8-sig');old=t
   t=t.replace('最高6金币','最高64金币').replace('最多6金币','最多64金币').replace('最大6金币','最大64金币')
   # Participation was already 11%, but old guide lines still said 15%.
   t=t.replace('两年建设速度+15%、商人容量+15%','两年建设速度+11%、商人容量+11%')
   if t!=old:p.write_text(t,encoding='utf-8-sig')
 return report
