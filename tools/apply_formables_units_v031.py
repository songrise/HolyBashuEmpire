"""Native formation paths and differentiated specialty regiments; idempotent."""
from pathlib import Path
import json, hashlib, math, re
from PIL import Image
from pdxscript import blocks, apply_edits

UNIT_STATS = {
 'hbe_canal_crossbow': {'strength_damage_done':0.12},
 'hbe_salt_guard': {'flanking_ability':0.20,'strength_damage_taken':0.05,'morale_damage_taken':-0.08},
 'hbe_river_garrison': {'morale_damage_taken':-0.12,'supply_weight':0.10},
 'hbe_pass_rotation': {'strength_damage_taken':-0.12},
 'hbe_granary_militia': {'strength_damage_done':-0.08,'supply_weight':-0.20,'food_consumption_per_strength':-0.03},
 'hbe_tea_riders': {'flanking_ability':0.20,'strength_damage_done':-0.05,'movement_speed':0.15},
 'hbe_valley_soldiers': {'initiative':0.20,'strength_damage_taken':0.05},
 'hbe_trained_river': {'combat_power':0.20,'morale_damage_taken':-0.16,'strength_damage_done':0.12,'supply_weight':0.20},
 'hbe_permanent_pass': {'combat_power':0.15,'strength_damage_taken':-0.18,'morale_damage_taken':-0.10,'supply_weight':0.20},
}
TERRAIN = {'hbe_river_garrison':{'river':0.10},'hbe_trained_river':{'river':0.15},
 'hbe_pass_rotation':{'mountains':0.10},'hbe_permanent_pass':{'mountains':0.15},
 'hbe_valley_soldiers':{'mountains':0.15,'hills':0.10}}
FORMS = [('sichuan','HQS','蜀','Shu','hbe_sichuan_core',0.67,
          ['chengdu','yibin','langzhong','yandao'],2,'rank_kingdom',(50,101,67),'hbe_pine'),
         ('chongqing','HQC','渝','Yu','hbe_chongqing_core',0.67,
          ['baxian','fuzhou_sichuan','wanzhou'],2,'rank_kingdom',(151,64,48),'hbe_cinnabar'),
         ('bashu','HQB','巴蜀','Bashu','hbe_domain',0.90,
          ['chengdu','baxian','yibin','langzhong','yandao','jianchang_sichuan','suining'],4,'rank_empire',(98,60,135),'hbe_indigo')]

def apply(out,root,game):
 out,root,game=map(Path,(out,root,game))
 def put(rel,text):
  p=out/rel;p.parent.mkdir(parents=True,exist_ok=True)
  text='\n'.join(line.rstrip() for line in text.rstrip().splitlines())+'\n'
  p.write_text(text,encoding='utf-8-sig',newline='\r\n')
 unitpath=out/'in_game/common/unit_types/hbe_civic_units.txt'
 text=unitpath.read_text(encoding='utf-8-sig');edits=[]
 scalars=set(k for vals in UNIT_STATS.values() for k in vals)|{'movement_speed'}
 for key,start,b,e,finish in blocks(text,0):
  assert key in UNIT_STATS,key
  body=text[b:e]
  body=re.sub(r'custom_tooltip\s*=\s*\{\s*text\s*=\s*hbe_late_unit_year_requirement\s+current_year\s*>=\s*1457\s*\}','',body)
  body=re.sub(r'current_year\s*>=\s*\d+\s*','',body)
  for field in scalars:
   body=re.sub(r'\b'+field+r'\s*=\s*-?\d+(?:\.\d+)?','',body)
  # This module exclusively owns the specialty terrain block.
  body=re.sub(r'\bcombat\s*=\s*\{[^{}]*\}','',body)
  body='\n'.join(line.rstrip() for line in body.splitlines() if line.strip())
  body+='\n '+ ' '.join(f'{k} = {v:.2f}' for k,v in UNIT_STATS[key].items())+'\n'
  if key in TERRAIN:body+=' combat = { '+' '.join(f'{k} = {v:.2f}' for k,v in TERRAIN[key].items())+' }\n'
  edits.append((b,e,'\n'+body.strip('\n')+'\n'))
 put(unitpath.relative_to(out),apply_edits(text,edits))
 descriptions={
 'hbe_canal_crossbow':('渠乡弩手依托水利村社训练，以齐射杀伤见长。杀伤加成提高至12%，取消移速惩罚。','Canal crossbowmen draw on village irrigation networks. Their strength damage bonus is 12%, with no movement penalty.'),
 'hbe_salt_guard':('井灶护运兵沿盐路护送货队，侧翼能力提高至20%，士气损失降低8%；轻装护运仍承担5%的额外兵力损失。','Salt convoy guards gain 20% flanking ability and take 8% less morale damage. Their light protection still increases strength damage taken by 5%.'),
 'hbe_river_garrison':('川江寨兵依岸扎营，士气损失降低12%，河流战斗加成10%；补给负担增加10%。','River garrisons take 12% less morale damage and gain a 10% river combat bonus, at 10% greater supply weight.'),
 'hbe_pass_rotation':('关隘轮戍兵依山守险，兵力损失降低12%，山地战斗加成10%，取消移速惩罚。','Pass rotation troops take 12% less strength damage and gain a 10% mountain combat bonus, with no movement penalty.'),
 'hbe_granary_militia':('义仓团练擅长久驻与粮秣调度，补给负担修正−0.20，粮食消耗修正−0.03（较同类约低9%）；杀伤仍降低8%。','Granary militia gain -0.20 supply weight and -0.03 food consumption (about 9% below the category baseline), while dealing 8% less strength damage.'),
 'hbe_tea_riders':('茶路护骑以接应与包抄见长，侧翼能力加成提高至0.20，移速加成0.15；杀伤仍降低5%。','Tea-road riders gain 0.20 flanking ability and 0.15 movement speed, while dealing 5% less strength damage.'),
 'hbe_valley_soldiers':('联寨山卒熟悉山道，主动性加成提高至0.20，山地战斗加成15%、丘陵加成10%；轻装仍增加5%的兵力损失。','Valley soldiers gain 0.20 initiative, 15% mountain combat and 10% hills combat, while taking 5% more strength damage.'),
 'hbe_trained_river':('江防精练寨兵延续川江驻守军制，基础战斗力1.20，杀伤加成12%，士气损失降低16%，河流战斗加成15%；补给负担增加20%。','Trained river troops have 1.20 base combat power, 12% extra strength damage, 16% less morale damage taken and 15% river combat, at 20% greater supply weight.'),
 'hbe_permanent_pass':('关镇长值兵改轮戍为常备，基础战斗力1.15，兵力损失降低18%、士气损失降低10%，山地战斗加成15%；补给负担增加20%。','Permanent pass troops have 1.15 base combat power, 18% less strength damage taken, 10% less morale damage taken and 15% mountain combat, at 20% greater supply weight.'),
 }
 for lang,index in [('simp_chinese',0),('english',1)]:
  p=out/f'main_menu/localization/{lang}/hbe_l_{lang}.yml';t=p.read_text(encoding='utf-8-sig')
  for unit,d in descriptions.items():
   # Preserve the existing unlock instructions after the first paragraph.
   pattern=r'(?m)^ '+unit+r'_desc:\s*"([^\n]*)"$'
   match=re.search(pattern,t);assert match,(lang,unit)
   old=match.group(1);suffix=old.split(r'\n\n',1)[1] if r'\n\n' in old and unit not in ('hbe_trained_river','hbe_permanent_pass') else ('1457年后完成本圈续约课题和百年验收，并维持招募机构供养后可用，替代前身。' if lang=='simp_chinese' else 'Available after 1457 with the regional renewal advance, final mission and staffed recruitment institution; replaces its predecessor.')
   suffix=suffix.replace('1352年后开放，须','须').replace('1457年后完成','完成').replace('Available after 1457 with','Available with').replace('Available after 1352','Available with the required advance')
   value=d[index]+(' 每单位500人。' if lang=='simp_chinese' else ' Each regiment has 500 men.')+r'\n\n'+suffix
   t=re.sub(pattern,lambda m:' '+unit+'_desc: "'+value+'"',t)
  p.write_text(t,encoding='utf-8-sig',newline='\r\n')
 geo=(out/'in_game/common/scripted_geography/hbe_geography.txt').read_text(encoding='utf-8-sig')
 geos={k:re.search(r'location\s*=\s*\{([^}]+)',geo[b:e]).group(1).split() for k,_,b,e,_ in blocks(geo,0)}
 domain=geos['hbe_domain'];cq=geos['hbe_geo_eastern_river'];sc=sorted(set(domain)-set(cq))
 put('in_game/common/scripted_geography/hbe_formable_geography.txt',
     'hbe_sichuan_core = { location = { '+' '.join(sc)+' } }\n'+
     'hbe_chongqing_core = { location = { '+' '.join(cq)+' } }')
 geos.update(hbe_sichuan_core=sc,hbe_chongqing_core=cq)
 # Calendar locks are removed from all mod advances. Keep age, requires,
 # institutional qualification and mission conditions intact.
 date_free=[]
 for p in (out/'in_game/common/advances').glob('hbe*.txt'):
  t=p.read_text(encoding='utf-8-sig')
  t=re.sub(r'\bcurrent_(?:year|date)\s*(?:>=|>|=|<=|<)\s*\d+(?:\.\d+\.\d+)?\s*','',t)
  put(p.relative_to(out),t);date_free.extend(k for k,*_ in blocks(t,0))
 forms=[];effects=[];triggers=[];colors=[];coats=[];locales={'simp_chinese':{'hbe_late_unit_year_requirement':'当前年份达到1457年（精练常备军开放）'},'english':{'hbe_late_unit_year_requirement':'The current year is at least 1457 (trained standing regiments)'}};summary=[]
 for key,tag,cn,en,g,fraction,cities,level,rank,color,field in FORMS:
  form=f'hbe_form_{key}';trigger=f'hbe_can_form_{key}';n=len(geos[g]);minimum=math.ceil(n*fraction)
  allow=f'is_subject = no at_war = no any_owned_location = {{ count >= {minimum} is_in_scripted_geography = scripted_geography:{g} controller = root }}\n'+'\n'.join(f'location:{l} = {{ owner = root controller = root }}' for l in cities)
  triggers.append(f'{trigger} = {{\n {allow}\n}}')
  guard='NOT = { has_variable = hbe_formed_bashu }' if key=='bashu' else 'NOT = { has_variable = hbe_formed_regional_state } NOT = { has_variable = hbe_formed_bashu }'
  marker='' if key=='bashu' else 'set_variable = hbe_formed_regional_state'
  effects.append(f'''hbe_found_{key} = {{
 change_country_name = {tag}
 change_country_adjective = {tag}_ADJ
 change_country_flag = {tag}
 change_country_color = map_{tag}
 if = {{ limit = {{ country_rank_level < {3 if level==2 else 4} }} set_country_rank = country_rank:{rank} }}
 set_variable = hbe_formed_{key}
 {marker}
}}''')
  forms.append(f'''{form} = {{
 decision_category = country_specific_decisions
 image = "gfx/interface/hbe/formables/{key}.dds"
 potential = {{ {guard} any_owned_location = {{ is_in_scripted_geography = scripted_geography:{g} }} }}
 allow = {{ {trigger} = yes }}
 ai_will_do = {{ value = 1 }}
 option = {{ name = {form}.a ai_chance = {{ value = 100 }} effect = {{ hbe_found_{key} = yes }} }}
}}''')
  colors.append(f'map_{tag} = rgb {{ {" ".join(map(str,color))} }}')
  coats.append(f'{tag} = {{ pattern = "pattern_fringe.dds" color1 = "{field}" color2 = "hbe_gold" textured_emblem = {{ texture = "te_hbe_form_{key}.dds" instance = {{ position = {{ 0.5 0.5 }} scale = {{ 0.72 0.95 }} }} }} }}')
  source=root/f'assets/formable_flags/{key}.png'
  assert source.exists(),source
  im=Image.open(source).convert('RGBA');bbox=im.getchannel('A').getbbox();assert bbox
  sprite=im.crop(bbox);sprite.thumbnail((450,450),Image.Resampling.LANCZOS)
  target=Image.new('RGBA',(512,512));target.alpha_composite(sprite,((512-sprite.width)//2,(512-sprite.height)//2))
  dest=out/f'main_menu/gfx/coat_of_arms/textured_emblems/te_hbe_form_{key}.dds';dest.parent.mkdir(parents=True,exist_ok=True);target.save(dest,pixel_format='DXT5')
  card=Image.new('RGBA',(384,192),(*color,255));small=target.resize((176,176),Image.Resampling.LANCZOS);card.alpha_composite(small,(104,8))
  dest=out/f'main_menu/gfx/interface/hbe/formables/{key}.dds';dest.parent.mkdir(parents=True,exist_ok=True);card.save(dest,pixel_format='DXT5')
  for lang,display in [('simp_chinese',cn),('english',en)]:
   d=locales[lang];d[tag]=display;d[tag+'_ADJ']=display;d[tag+'_ADJ2']=display
   d[form]=('巴蜀帝国' if key=='bashu' else display) if lang=='simp_chinese' else ('Bashu Empire' if key=='bashu' else display)
   d[form]=('成立'+d[form]) if lang=='simp_chinese' else ('Form '+d[form])
   d[form+'.a']='合诸府之印，立山川之国。' if lang=='simp_chinese' else 'Unite the prefectures under one banner.'
   d[form+'.title']=d[form];d[form+'.title.entry']=d[form]
   d[g]=('四川核心地区' if key=='sichuan' else '重庆核心地区' if key=='chongqing' else '巴蜀原始疆域') if lang=='simp_chinese' else ('Sichuan heartland' if key=='sichuan' else 'Chongqing heartland' if key=='chongqing' else 'Original Bashu domain')
   citytext='、'.join(cities) if lang=='simp_chinese' else ', '.join(cities)
   d[form+'_desc']=(f'山川虽有旧界，府州终须同治。直属拥有并控制{n}处核心地区中的至少{minimum}处（{fraction:.0%}），并持有指定枢纽城市，即可统一旗号。成立后保留原有地区科技、议约与国家传承。' if lang=='simp_chinese' else f'Unite the prefectures beneath one banner. Directly own and control at least {minimum} of {n} heartland locations ({fraction:.0%}) and all named strategic cities. Your existing regional research, compacts and national history are retained.')
   d[form+'.desc']=d[form+'_desc'];d[form+'.desc.entry']=d[form+'_desc']
  summary.append(dict(key=form,tag=tag,geography=g,total=n,minimum=minimum,fraction=fraction,cities=cities,level=level,rank=rank))
 # These names are cosmetic country identities. Do not instantiate extra
 # landless countries: the original country remains the owner and IO member.
 stale=out/'in_game/setup/countries/hbe_formable_countries.txt'
 if stale.exists():stale.unlink()
 stale=out/'in_game/common/formable_countries/hbe_formables.txt'
 if stale.exists():stale.unlink()
 put('in_game/common/decisions/hbe_formable_decisions.txt','\n'.join(forms))
 put('in_game/common/scripted_effects/hbe_formation_effects.txt','\n'.join(effects))
 put('in_game/common/scripted_triggers/hbe_formation_triggers.txt','\n'.join(triggers))
 put('main_menu/common/named_colors/hbe_formable_colors.txt','colors = {\n'+'\n'.join(colors)+'\n}')
 put('main_menu/common/coat_of_arms/coat_of_arms/hbe_formables.txt','\n'.join(coats))
 for lang,d in locales.items():
  put(f'main_menu/localization/{lang}/hbe_formables_l_{lang}.yml',f'l_{lang}:\n'+'\n'.join(f' {k}: '+json.dumps(v,ensure_ascii=False) for k,v in d.items() if k!='hbe_domain'))
 result=dict(version='0.3.1',units=UNIT_STATS,terrain=TERRAIN,formations=summary,formation_method='National decisions using native name, adjective, flag, map color and rank effects. Preserve original tag and all regional eligibility.',unit_calendar_gates_removed=True,date_free_advances=date_free,flags='Built-in imagegen; three transparent gold emblems; native heraldic flag composition')
 manifestp=out/'build_manifest.json';m=json.loads(manifestp.read_text(encoding='utf-8'));m['formables_units_v031']=result
 m['decisions']=sum(len(blocks(p.read_text(encoding='utf-8-sig'),0)) for p in (out/'in_game/common/decisions').glob('*.txt'))
 meta=out/'.metadata/metadata.json';d=json.loads(meta.read_text(encoding='utf-8'));d['short_description']='七圈三十六府：405个事件、分支长线与湖广填四川；特色产业、政府改革及蜀、渝、巴蜀帝国成立路线。'
 meta.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 m['files']={p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and p.name!='build_manifest.json'}
 manifestp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 return result

if __name__=='__main__':
 import sys
 root=Path(sys.argv[1]);print(json.dumps(apply(root/'mod/holy_bashu_empire',root,Path('D:/SteamLibrary/steamapps/common/Europa Universalis V/game')),ensure_ascii=False))
