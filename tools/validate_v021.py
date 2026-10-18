"""Focused cross-reference and balance checks for technology, feast and AI changes."""
import json,re,hashlib
from pathlib import Path
from pdxscript import blocks

def validate(root):
 mod=root/'mod/holy_bashu_empire';manifest=json.loads((mod/'build_manifest.json').read_text(encoding='utf-8-sig'))
 rewards=manifest['technology_rewards'];checks=[]
 def check(name,condition):
  checks.append(dict(name=name,passed=bool(condition)))
  if not condition:raise AssertionError(name)
 def read(rel):return (mod/rel).read_text(encoding='utf-8-sig')
 adv=read('in_game/common/advances/hbe_advances.txt')+'\n'+read('in_game/common/advances/hbe_civic_advances.txt')
 nodes={k:adv[s:e] for k,_,s,e,_ in blocks(adv,0)}
 check('80 technologies retain 80 unique native IDs',len(nodes)==len(rewards['advances'])==80)
 for row in rewards['advances']:
  check(row['key']+' immediate fields',all(re.search(r'(?m)^\s*'+k+r'\s*=\s*'+re.escape(f'{v:g}')+r'\s*$',nodes[row['key']]) for k,v in row['modifiers'].items()))
 building=read('in_game/common/building_types/hbe_civic_buildings.txt')
 pms={k:building[s:e] for k,_,s,e,_ in blocks(building) if k.startswith('hbe_') and k.endswith('_production')}
 check('all real production methods resolve through native unlocks',len(pms)==len(rewards['production'])==(16 if 'special_goods' in manifest else 14) and all('unlock_production_method = '+r['key'] in nodes[r['advance']] for r in rewards['production']))
 check('all productions consume real goods and output into market',all(r['inputs'] and r['output']>0 and 'produced = '+r['goods'] in pms[r['key']] for r in rewards['production']))
 check('16 supplied buildings preserved with 7 extra production slots',len(blocks(building,0))==16 and building.count('category = building_maintenance')==16 and building.count('unique_production_methods =')==23)
 net=read('in_game/common/scripted_effects/hbe_technology_effects.txt')
 check('network bonuses depend on recent delivery, employment and manageable burden',len(rewards['networks'])==14 and all(r['requirements'] in net for r in rewards['networks']) and net.count('else = { remove_country_modifier')==14)
 common={r['key']:r for r in rewards['advances']}
 check('3 reported duplicate cards now have distinct modifiers',len({json.dumps(common[k]['modifiers'],sort_keys=True) for k in ['hbe_tech_common_4','hbe_tech_common_5','hbe_tech_common_7']})==3)
 # Guard against an actual zero/negative road build time on either legal branch.
 for branch in (range(1,6),[1,2,6,7,8]):
  total=sum(r['modifiers'].get('global_road_building_time',0) for r in rewards['advances'] if r['key'].startswith('hbe_tech_common_') or r['key'] in [f'hbe_tech_northern_shudao_{i}' for i in branch] or r['key']=='hbe_civic_northern_shudao_1')
  total+=min(r['modifiers'].get('global_road_building_time',0) for r in rewards['networks'] if r['key'].startswith('hbe_network_northern_shudao'))
  check('road time stays above 20 percent on branch '+str(list(branch)),total>-.80)
 ai=read('in_game/common/ai_scripted_expansion_score/hbe_internal_rivalry.txt')
 check('AI rival targets only internal neighboring princes',ai.count('hbe_is_prince = yes')==2 and 'is_neighbor_of = scope:attacker' in ai and 'is_allied_with' in ai)
 aifiles=[read('in_game/common/ai_scripted_expansion_target/hbe_neighbors.txt'),ai,read('in_game/common/scripted_effects/hbe_ai_effects.txt')]
 check('AI makes no forced wars or truce bypasses',not re.search(r'\b(declare_war|start_war|remove_truce|ignore_antagonism)\s*=', '\n'.join(aifiles)))
 party=read('in_game/common/international_organizations/hbe_feast_parties.txt')
 check('exactly two non-military parties',len(blocks(party,0))==2 and party.count('join_offensive_wars = Never')==2 and 'can_declare_war' not in party)
 feast=read('in_game/common/scripted_effects/hbe_banquet_effects.txt');helpers=read('in_game/common/scripted_effects/hbe_simple_banquet_effects.txt')
 fb={k:feast[s:e] for k,_,s,e,_ in blocks(feast,0)}
 check('funding has a once-per-round effect guard and real scaled payment','NOT = { has_variable = hbe_round_contributed } gold >= hbe_feast_fee' in fb['hbe_fund_project'] and 'multiply = -1' in fb['hbe_fund_project'])
 check('completed service cannot double count','NOT = { has_variable = hbe_feast_helped }' in helpers and 'name = hbe_feast_points add = 2' in helpers)
 check('only contributors receive end rewards','var:hbe_feast_points > 0' in fb['hbe_settle_accounts'] and 'add_gold = 6' in fb['hbe_settle_accounts'])
 check('ties reward both factions','hbe_common_party.var:hbe_party_points >= international_organization:hbe_local_party.var:hbe_party_points' in feast and 'hbe_local_party.var:hbe_party_points >= international_organization:hbe_common_party.var:hbe_party_points' in feast)
 check('failure keeps participation rewards without penalty','hbe_banquet.5' in fb['hbe_settle_accounts'] and 'subtract' not in fb['hbe_settle_accounts'])
 check('old third-party state migrates without restarting new campaigns','var:hbe_stance > 2' in helpers and 'set_variable = hbe_feast_v021' in read('in_game/common/situations/hbe_banquet.txt'))
 check('adaptive goal remains attainable after unification','name = hbe_feast_required value = 3' in helpers and 'var:hbe_feast_total >= var:hbe_feast_required' in feast)
 dec=read('in_game/common/decisions/hbe_banquet_decisions.txt')
 visible=[k for k,_,s,e,_ in blocks(dec,0) if 'potential = { always = no }' not in dec[s:e]]
 check('four visible feast decisions',set(visible)==set(manifest['simple_banquet']['visible_decisions']))
 check('three actions appear directly in native situation panel',len(blocks(read('in_game/common/generic_actions/hbe_feast_actions.txt'),0))==3)
 gui=read('in_game/gui/panels/situation/hbe_banquet.gui')
 check('native two-leader template and two country member lists', 'using = two_countries_header_template' in gui and gui.count('.GetMembers]')==2 and 'GagCountryItem.' not in gui)
 # Parse only affected scripts, never reload the game or scan all artwork.
 changed=[p for p in mod.rglob('*') if p.is_file() and (p.name in ['hbe_advances.txt','hbe_civic_advances.txt','hbe_civic_buildings.txt','hbe_civic_effects.txt','hbe_banquet_effects.txt','hbe_banquet_events.txt','hbe_banquet_decisions.txt','hbe_banquet.txt','hbe_banquet.gui'] or any(t in p.name for t in ['technology','feast','simple_banquet','hbe_ai','hbe_neighbors','hbe_internal_rivalry'])) and p.suffix in ['.txt','.gui']]
 for p in changed:blocks(p.read_text(encoding='utf-8-sig'))
 check('affected scripts have balanced nested syntax',bool(changed))
 for language in ['simp_chinese','english']:
  text=read(f'main_menu/localization/{language}/hbe_l_{language}.yml')
  entries={m[1]:json.loads(m[2]) for m in re.finditer(r'(?m)^\s+([^:\s]+):\s*(".*")$',text)}
  check(language+' complete technology effects',all(r['key']+'_effects' in entries and r['key']+'_desc' in entries for r in rewards['advances']))
  check(language+' specific card effects',len({entries[k+'_effects'] for k in ['hbe_tech_common_4','hbe_tech_common_5','hbe_tech_common_7']})==3)
  check(language+' effect lines appear once',all(len(entries[r['key']+'_effects'].splitlines())==len(set(entries[r['key']+'_effects'].splitlines())) for r in rewards['advances']))
  check(language+' flavor paragraph does not repeat mechanics table',all('解锁“' not in entries[r['key']+'_desc'] and '旧存档的履约记录' not in entries[r['key']+'_desc'] for r in rewards['advances']))
  check(language+' no old third-party choice in active entry',entries['hbe_banquet.1.a']!=entries['hbe_banquet.1.b'] and '账房' not in entries['hbe_banquet.1.desc'])
 check('manifest matches all built files',all(hashlib.sha256((mod/p).read_bytes()).hexdigest()==h for p,h in manifest['files'].items()))
 if 'special_goods' in manifest:
  from PIL import Image
  game=Path(r'D:\SteamLibrary\steamapps\common\Europa Universalis V\game')
  goods=manifest['special_goods']['goods'];goods_text=read('in_game/common/goods/hbe_special_goods.txt')
  check('four unique real premium goods',len(blocks(goods_text,0))==len(goods)==4)
  vanilla=(game/'in_game/common/goods_demand/pop_demands.txt').read_text(encoding='utf-8-sig')
  demand=read('in_game/common/goods_demand/pop_demands.txt')
  check('native population demand singleton registered once',len([k for k,*_ in blocks(demand,0) if k=='pop_demand'])==1)
  # Compare actual goods coefficients rather than comments or outer block text.
  base={m[1]:m[2] for m in re.finditer(r'(?m)^\s*([a-z_]+)\s*=\s*([0-9.]+)\s*$',vanilla)}
  extended={m[1]:m[2] for m in re.finditer(r'(?m)^\s*([a-z_]+)\s*=\s*([0-9.]+)\s*$',demand)}
  check('native demand coefficients preserved exactly',all(extended.get(k)==v for k,v in base.items()))
  for r in goods:
   key=r['key'];pm=f'hbe_{r["group"]}_advanced_production'
   check(key+' actual produced good and tech unlock','produced = '+key in pms[pm] and 'unlock_production_method = '+pm in nodes[f'hbe_tech_{r["group"]}_{r["advance"]}'])
   check(key+' population buys it',extended.get(key)=='1' and sum(r['demand'].values())>=.17)
   check(key+' unique original-style goods art',Image.open(mod/f'main_menu/gfx/interface/icons/trade_goods/icon_goods_{key}.dds').size==(128,128) and (mod/f'main_menu/gfx/interface/icons/trade_goods/illustrations/icon_goods_{key}.dds').exists())
   check(key+' production boosters visible natively',any('global_'+key+'_output_modifier' in body for body in nodes.values()) and 'local_'+key+'_output_modifier' in building)
  check('paper has optional downstream industrial demand',sum('hbe_shu_paper' in r['inputs'] for r in rewards['production'])==2 and all('hbe_shu_paper' not in r['inputs'] for r in goods))
  check('goods are neither gold grants nor renamed vanilla IDs',not re.search(r'\badd_gold\b',goods_text) and not {r['key'] for r in goods}&{'fine_cloth','salt','paper','tea'})
 if 'event_choices' in manifest:
  events='\n'.join(p.read_text(encoding='utf-8-sig') for p in (mod/'in_game/events').glob('hbe*events.txt'))
  eb={k:events[s:e] for k,_,s,e,_ in blocks(events,0)}
  catalogue=json.loads((root/'data/event_choices_v021.json').read_text(encoding='utf-8'))
  static=read('main_menu/common/static_modifiers/hbe_event_choice_modifiers.txt');sb={k:static[s:e] for k,_,s,e,_ in blocks(static,0)}
  check('44 affected events retain native IDs',len(catalogue)==44 and all(r['id'] in eb for r in catalogue))
  for r in catalogue:
   body=eb[r['id']];opts=[body[s:e] for k,_,s,e,_ in blocks(body,0) if k=='option']
   check(r['id']+' three distinct effect choices',len(opts)==3 and len({re.sub(r'name = \S+|ai_chance = \{[^}]*\}', '',x).strip() for x in opts})==3)
  check('21 regional arrangements and two spending bonuses resolve',len(sb)==23 and all(k in sb for k in re.findall(r'modifier = (hbe_choice_\w+|hbe_event_\w+)',events)))
  check('no negative gold choice lacks an affordability check',all('gold >=' in body for k,body in eb.items() if (k in {r['id'] for r in catalogue} and re.search(r'add_gold = -[1-9]',body))))
  check('long-term choices explicitly exclude each other',all(eb[f'hbe_banquet.{100+n}'].count('remove_country_modifier = hbe_choice_')==9 for n in range(21)))
  check('choice modifiers have balanced native syntax',bool(blocks(static)))
 if 'art_v021' in manifest:
  import struct
  artwork=manifest['art_v021']['exports']
  check('24 unique new icons and dedicated panel',len(artwork)==25 and len({r['sha256'] for r in artwork if r['kind']!='panel'})==24)
  for r in artwork:
   content=(mod/r['path']).read_bytes();w,h=r['dimensions']
   check('DDS size and hash '+r['key'],content[:4]==b'DDS ' and struct.unpack_from('<2I',content,12)==(h,w) and len(content)==128+w*h*4 and hashlib.sha256(content).hexdigest()==r['sha256'])
  check('two faction lists have independent clipped scrolling',gui.count('size = { 234 216 }')==2 and gui.count('scissor = yes')==2)
  check('panel width and action area are bounded','maximumsize = { 480 -1 }' in gui and 'blockoverride "situation_panel_main_actions"' in gui)
  check('new painterly background is connected','gfx/interface/hbe/panels/hbe_feast_two_parties_v021.dds' in gui)
  check('reduced AI pressure encoded','aggressiveness_modifier = 0.05' in read('main_menu/common/static_modifiers/hbe_ai_modifiers.txt') and 'months_since_war >= 144' in aifiles[0])
 report=dict(version=manifest['version'],checks=checks,passed=len(checks),engine_test='separate targeted fixture; not a full campaign')
 (root/'docs/validation_v021.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(f'{len(checks)} focused checks passed')
 return report

if __name__=='__main__':validate(Path(__file__).resolve().parents[1])
