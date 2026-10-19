"""Full-country annexation inherits civilian industrial licenses; native formation UI."""
from build_support import snapshot_files
from pathlib import Path
import re, json, math
from pdxscript import blocks,apply_edits

def apply(out,root,game):
 out,root,game=map(Path,(out,root,game));mp=out/'build_manifest.json';manifest=json.loads(mp.read_text(encoding='utf-8-sig'))
 def put(rel,text):
  p=out/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('\n'.join(l.rstrip() for l in text.rstrip().splitlines())+'\n',encoding='utf-8-sig',newline='\r\n')
 guest=(out/'in_game/common/advances/hbe_guest_licenses.txt').read_text(encoding='utf-8-sig')
 industrial=[];dispatch=[];table=[];building_map={};loc={'simp_chinese':{},'english':{}}
 for key,_,b,e,_ in blocks(guest,0):
  region=key.removeprefix('hbe_guest_license_');body=guest[b:e]
  receipt='hbe_inherited_industry_license_'+region;marker='hbe_inherited_industry_'+region
  buildings=re.findall(r'\bunlock_building\s*=\s*(\w+)',body);recipes=re.findall(r'\bunlock_production_method\s*=\s*(\w+)',body)
  assert len(buildings)==2 and recipes and all('_advanced_' not in r for r in recipes)
  icon=re.search(r'icon\s*=\s*(\w+)',body).group(1)
  industrial.append(f'''{receipt} = {{
 age = age_1_traditions starting_technology_level = 99 research_cost = 1 content_priority = 850 icon = {icon}
 potential = {{ has_variable = {marker} }} allow = {{ always = no }}
 {' '.join('unlock_building = '+x for x in buildings)}
 {' '.join('unlock_production_method = '+x for x in recipes)}
}}''')
  native_tags=[c['tag'] for c in manifest['countries'] if c['region']==region]
  source='OR = { '+' '.join('has_or_had_tag = '+x for x in native_tags)+f' has_advance = {key} has_advance = {receipt} has_variable = {marker} '+'}'
  dispatch.append(f'''if = {{
 limit = {{ scope:target = {{ {source} }} }}
 set_variable = {marker}
 if = {{ limit = {{ NOT = {{ has_advance = {receipt} }} }} research_advance = advance_type:{receipt} }}
}}''')
  for building in buildings:building_map[building]=receipt
  cn=next(r[1] for r in manifest['regions'] if r[0]==region)
  for lang in loc:
   title=cn+'产业接管资格' if lang=='simp_chinese' else region.replace('_',' ').title()+' Industrial Inheritance'
   loc[lang][receipt]=title;loc[lang][marker]=title
   loc[lang][receipt+'_desc']=('完整吞并当地国家后，接续其工坊与基础产业制度。自动取得该圈基础生产方式及建筑资格，无须另签客籍议约。营建仍限当地土地，高级工艺与特色军制仍须另行取得。' if lang=='simp_chinese' else 'A complete national annexation passes on local workshops and basic industrial institutions. Starter recipes and building permissions are inherited automatically, without a guest compact. Geographic construction limits remain. Advanced crafts and specialty military access retain their own requirements.')
  table.append(dict(region=region,advance=receipt,marker=marker,buildings=buildings,recipes=recipes,native_tags=native_tags))
 put('in_game/common/advances/hbe_inherited_industry_licenses.txt','\n'.join(industrial))
 put('in_game/common/scripted_effects/hbe_annex_industry_effects.txt','hbe_inherit_annexed_industry = {\n'+'\n'.join(dispatch)+'\n}')
 # The engine documents this hook as AFTER a complete national annexation.
 # Do not subscribe to location transfers, game start, or monthly territorial scans.
 put('in_game/common/on_action/hbe_annex_industry_on_actions.txt','''on_annexed = { on_actions = { hbe_annex_industry_completed } }
hbe_annex_industry_completed = { effect = { hbe_inherit_annexed_industry = yes } }''')
 p=out/'in_game/common/building_types/hbe_civic_buildings.txt';text=p.read_text(encoding='utf-8-sig');edits=[]
 for building,_,b,e,_ in blocks(text,0):
  if building not in building_map:continue
  receipt=building_map[building];body=text[b:e];inner=[]
  for k,_,x,y,_ in blocks(body,0):
   content=body[x:y]
   if k=='country_potential' and receipt not in content:
    inner.append((x,y,' OR = { AND = { '+content.strip()+' } has_advance = '+receipt+' } '))
   if k=='allow':
    for actor,_,a,z,_ in blocks(content,0):
     if actor=='scope:actor' and receipt not in content[a:z]:
      inner.append((x+a,x+z,' OR = { AND = { '+content[a:z].strip()+' } has_advance = '+receipt+' } '))
  if inner:edits.append((b,e,apply_edits(body,inner)))
 put(p.relative_to(out),apply_edits(text,edits))
 # Keep formal guest compacts for their distinct military/cooperation rights.
 for lang in loc:
  p=out/f'main_menu/localization/{lang}/hbe_l_{lang}.yml';t=p.read_text(encoding='utf-8-sig')
  suffix='完整吞并整个国家后，其基础生产与建造资格自动继承；正式客籍议约仍可另行办理，取得原有军制及合作事务资格。' if lang=='simp_chinese' else 'Complete national annexation automatically transfers starter production and building permissions. A formal guest compact can still be signed for its separate military and cooperation rights.'
  for row in table:
   for key in ('hbe_guest_'+row['region']+'.desc','hbe_guest_'+row['region']+'.desc.entry'):
    pattern=r'(?m)^ '+re.escape(key)+r':\s*"([^\n]*)"$';match=re.search(pattern,t);assert match,key
    if suffix not in match.group(1):t=re.sub(pattern,lambda m:' '+key+': "'+m.group(1)+r'\n\n'+suffix+'"',t)
  put(p.relative_to(out),t)
 # A native tag formation may change the current tag. Keep the mod's existing
 # country-specific decisions registered for all three formed identities too.
 for p in (out/'in_game/common/decisions').glob('hbe*decisions.txt'):
  t=p.read_text(encoding='utf-8-sig')
  def formed_tags(match):
   values=match.group(1).split()
   return 'tags = { '+' '.join(values+[v for v in ('HQS','HQC','HQB') if v not in values])+' }'
  t=re.sub(r'tags\s*=\s*\{([^{}]*)\}',formed_tags,t)
  put(p.relative_to(out),t)
 # Register actual native formables for the user's Formable tab, retaining the
 # already-working decision/effect route as an alternative entry point.
 geography='\n'.join(p.read_text(encoding='utf-8-sig') for p in (out/'in_game/common/scripted_geography').glob('*.txt'))
 from apply_formables_units_v031 import FORMS
 geos={k:re.search(r'location\s*=\s*\{([^}]+)',geography[b:e]).group(1).split() for k,_,b,e,_ in blocks(geography,0)}
 native_forms=[]
 for key,tag,cn,en,g,fraction,cities,level,rank,color,field in FORMS:
  loc['simp_chinese'][tag+'_f']='巴蜀帝国' if key=='bashu' else cn
  loc['english'][tag+'_f']='Bashu Empire' if key=='bashu' else en
  guard='NOT = { has_variable = hbe_formed_bashu }' if key=='bashu' else 'NOT = { has_variable = hbe_formed_regional_state } NOT = { has_variable = hbe_formed_bashu }'
  native_forms.append(f'''{tag}_f = {{
 level = {level} required_locations_fraction = {fraction:.2f} rule = historical potential_requires_own = no
 potential = {{ {guard} any_owned_location = {{ is_in_scripted_geography = scripted_geography:hbe_domain }} }}
 allow = {{ hbe_can_form_{key} = yes }}
 name = {tag} flag = {tag} adjective = {tag}_ADJ tag = {tag} color = map_{tag}
 locations = {{ {' '.join(geos[g])} }}
 form_effect = {{ hbe_found_{key} = yes }}
}}''')
 put('in_game/common/formable_countries/hbe_native_formables.txt','\n'.join(native_forms))
 for lang,d in loc.items():
  put(f'main_menu/localization/{lang}/hbe_annex_industry_l_{lang}.yml',f'l_{lang}:\n'+'\n'.join(' '+k+': '+json.dumps(v,ensure_ascii=False) for k,v in d.items()))
 result=dict(version='0.3.1',trigger='on_annexed: complete national annexation only',receipt_count=7,starter_recipe_unlocks=sum(len(r['recipes']) for r in table),building_unlocks=len(building_map),regions=table,native_formables=['HQS_f','HQC_f','HQB_f'],recipient_scope='Any annexer; inherited civilian institutions retain geographic constraints.',no_unit_or_advanced_recipe_grants=True,no_partial_or_startup_grants=True)
 manifest['annex_industry_patch']=result
 manifest['formables_units_v031']['date_free_advances']=[k for p in (out/'in_game/common/advances').glob('hbe*.txt') for k,*_ in blocks(p.read_text(encoding='utf-8-sig'),0)]
 manifest['files']=snapshot_files(out)
 mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 return result

if __name__=='__main__':
 import sys
 root=Path(sys.argv[1]);r=apply(root/'mod/holy_bashu_empire',root,Path('D:/SteamLibrary/steamapps/common/Europa Universalis V/game'));print(json.dumps({k:v for k,v in r.items() if k!='regions'},ensure_ascii=False))
