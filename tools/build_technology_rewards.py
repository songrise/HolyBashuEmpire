"""Immediate native research rewards and distinct, supplied regional economies.

Post-processes the existing native conversion. Does not regenerate artwork or setup.
All bonuses live on advances, so the engine displays and applies them on completion.
"""
import json, re
from pathlib import Path
from pdxscript import blocks, apply_edits

M = lambda **kw: kw
REWARDS = {
 'common': [
  M(country_cabinet_efficiency=.10, global_monthly_control=.05),
  M(global_merchant_capacity_modifier=.15, merchant_maintenance_efficiency=.10),
  M(global_construction_speed=.20, global_build_buildings_efficiency=.10),
  M(global_institution_growth_modifier=.20),
  M(global_production_efficiency=.10, global_burghers_max_literacy=10),
  M(research_speed_modifier=.15, global_books_output_modifier=.20),
  M(global_road_building_time=-.15, build_gravel_road_cost_modifier=-.15),
  M(global_construction_speed=.15, global_trade_center_power=.15)],
 'chengdu_plain': [
  M(global_monthly_food_modifier=.15, global_rice_output_modifier=.15),
  M(global_fine_cloth_output_modifier=.25, global_silk_output_modifier=.15),
  M(global_food_decay=-.15, peasants_estate_target_satisfaction=.05),
  M(global_monthly_food_modifier=.20, global_rgo_build_time=-.20),
  M(global_rice_output_modifier=.30, global_devastation_recovery=.005),
  M(global_max_literacy=10, cultural_tradition_modifier=.15),
  M(diplomatic_capacity_modifier=.20, stability_cost_efficiency=.15),
  M(research_speed_modifier=.20, cultural_influence_modifier=.25)],
 'southern_salt_wine': [
  M(global_salt_output_modifier=.20, global_build_buildings_efficiency=.10),
  M(global_liquor_output_modifier=.25, global_pottery_output_modifier=.15),
  M(global_salt_output_modifier=.30, global_tools_output_modifier=.15),
  M(total_loan_capacity_modifier=.50, bank_interest=-.005),
  M(global_salt_output_modifier=.25, global_merchant_capacity_modifier=.25),
  M(global_liquor_output_modifier=.30, cultural_tradition_modifier=.10),
  M(merchant_maintenance_efficiency=.20, global_production_efficiency=.10),
  M(global_liquor_output_modifier=.25, cultural_influence_modifier=.25)],
 'eastern_river': [
  M(global_merchant_capacity_modifier=.20, merchant_maintenance_efficiency=.10),
  M(global_naval_supplies_output_modifier=.25, ship_build_speed=.20),
  M(global_trade_center_power=.20, merchant_maintenance_efficiency=.15),
  M(global_merchant_capacity_modifier=.25, global_food_decay=-.10),
  M(global_trade_center_power=.25, global_production_efficiency=.15),
  M(global_defensive=.20, fort_maintenance_efficiency=.20),
  M(army_maintenance_efficiency=.20, global_levy_recruitment_speed_modifier=.20),
  M(global_defensive=.25, army_initiative=.15)],
 'northern_shudao': [
  M(global_road_building_time=-.15, build_gravel_road_cost_modifier=-.15),
  M(global_supply_limit_modifier=.20, army_maintenance_efficiency=.10),
  M(global_defensive=.25, fort_maintenance_efficiency=.20),
  M(global_levy_recruitment_speed_modifier=.25, army_maintenance_efficiency=.20),
  M(global_defensive=.20, global_manpower_modifier=.20),
  M(global_merchant_capacity_modifier=.20, merchant_maintenance_efficiency=.15),
  M(global_road_building_time=-.15, diplomatic_capacity_modifier=.20),
  M(global_institution_growth_modifier=.30, global_monthly_control=.10)],
 'central_hills': [
  M(global_monthly_food_modifier=.15, global_max_rgo_size_modifier_in_rural=.15),
  M(global_trade_center_power=.15, global_monthly_control=.05),
  M(global_food_decay=-.25, food_purchase_efficiency=.20),
  M(stability_cost_efficiency=.20, peasants_estate_target_satisfaction=.08),
  M(global_monthly_food_modifier=.25, global_disease_resistance=.05),
  M(total_loan_capacity_modifier=.40, burghers_estate_target_satisfaction=.08),
  M(bank_interest=-.005, merchant_maintenance_efficiency=.20),
  M(global_merchant_capacity_modifier=.25, global_monthly_prosperity=.05)],
 'western_tea_horse': [
  M(global_tea_output_modifier=.25, global_merchant_capacity_modifier=.15),
  M(global_supply_limit_modifier=.20, merchant_maintenance_efficiency=.15),
  M(global_leather_output_modifier=.25, global_food_decay=-.10),
  M(global_merchant_capacity_modifier=.25, global_road_building_time=-.15),
  M(global_tea_output_modifier=.30, global_trade_center_power=.20),
  M(tolerance_heathen=1, global_disease_resistance=.05),
  M(diplomatic_capacity_modifier=.25, cultural_influence_modifier=.20),
  M(cultures_capacity=1, cultural_tradition_modifier=.25)],
 'southwestern_valleys': [
  M(global_production_efficiency=.10, global_trade_center_power=.15),
  M(tribes_estate_target_satisfaction=.10, peasants_estate_target_satisfaction=.05),
  M(global_tools_output_modifier=.25, global_road_building_time=-.15),
  M(global_production_efficiency=.15, global_merchant_capacity_modifier=.20),
  M(global_tools_output_modifier=.25, burghers_estate_target_satisfaction=.10),
  M(global_supply_limit_modifier=.25, global_levy_recruitment_speed_modifier=.15),
  M(army_maintenance_efficiency=.20, global_defensive=.15),
  M(global_manpower_modifier=.25, tribes_estate_target_satisfaction=.10)]}

CIVIC = {
 'common':[M(stability_cost_efficiency=.15, global_estate_target_satisfaction=.05),
           M(country_cabinet_efficiency=.20, global_build_buildings_efficiency=.15)],
 'chengdu_plain':[M(global_monthly_food_modifier=.15, global_fine_cloth_output_modifier=.15),
                  M(global_books_output_modifier=.30, cultural_tradition_modifier=.20)],
 'southern_salt_wine':[M(global_salt_output_modifier=.20, burghers_estate_target_satisfaction=.10),
                      M(bank_interest=-.005, total_loan_capacity_modifier=.50)],
 'eastern_river':[M(global_merchant_capacity_modifier=.20, fort_maintenance_efficiency=.15),
                 M(army_initiative=.20, army_maintenance_efficiency=.15)],
 'northern_shudao':[M(global_supply_limit_modifier=.25, global_road_building_time=-.10),
                   M(global_defensive=.25, global_manpower_modifier=.15)],
 'central_hills':[M(global_food_decay=-.15, peasants_estate_target_satisfaction=.10),
                 M(global_monthly_prosperity=.08, global_estate_target_satisfaction=.08)],
 'western_tea_horse':[M(global_tea_output_modifier=.20, merchant_maintenance_efficiency=.15),
                     M(tolerance_heathen=1, diplomatic_capacity_modifier=.20)],
 'southwestern_valleys':[M(global_supply_limit_modifier=.20, tribes_estate_target_satisfaction=.10),
                        M(cultures_capacity=1, global_production_efficiency=.15)]}

# A second production slot on existing institutions: maintenance remains mandatory.
# One basic and one research-unlocked improved method per circle, using vanilla goods icons.
PRODUCTION = [
 ('chengdu_plain','hbe_brocade_school','锦坊试织','分工织锦','fine_cloth',{'silk':.45,'dyes':.08},.65,{'silk':.60,'dyes':.12,'tools':.06},1.05,2,4),
 ('southern_salt_wine','hbe_salt_office','井灶汲卤','井架联灶','salt',{'lumber':.35,'tools':.08},.80,{'lumber':.45,'tools':.15},1.50,1,3),
 ('eastern_river','hbe_river_warehouse','江船备料','船帮联作','naval_supplies',{'lumber':.40,'cloth':.15},.65,{'lumber':.55,'cloth':.20,'tools':.06},1.10,2,4),
 ('northern_shudao','hbe_gate_registry','关驿抄券','驿券纸坊','paper',{'lumber':.40,'tools':.05},.55,{'lumber':.60,'tools':.08},1.00,6,7),
 ('central_hills','hbe_community_granary','仓社附田','塘堰轮作','rice',{'lumber':.20,'tools':.06},.70,{'lumber':.30,'tools':.10},1.25,3,4),
 ('western_tea_horse','hbe_tea_exchange','驮具修造','商队皮作','leather',{'livestock':.50,'tools':.05},.65,{'livestock':.65,'tools':.10},1.05,1,3),
 ('southwestern_valleys','hbe_valley_inn','谷市农具','诸谷铁木联作','tools',{'iron':.25,'lumber':.20},.50,{'iron':.40,'lumber':.25},.85,1,4)]

# Tech -> supplied institution -> recent completed service -> maintained network.
# These are mutually exclusive regional specialisations, not another generic +production.
NETWORKS = [
 ('chengdu_plain',4,'hbe_canal_office','渠田共济',M(global_monthly_food_modifier=.25,global_rice_output_modifier=.20),'水权储备至少30', 'var:hbe_water >= 30'),
 ('chengdu_plain',7,'hbe_brocade_school','锦江讲会',M(research_speed_modifier=.20,cultural_influence_modifier=.25),'义气至少60','var:hbe_yiqi >= 60'),
 ('southern_salt_wine',4,'hbe_salt_office','井盐担保',M(global_salt_output_modifier=.30,global_merchant_capacity_modifier=.20),'盐债不超过20','OR = { NOT = { has_variable = hbe_salt_debt } var:hbe_salt_debt <= 20 }'),
 ('southern_salt_wine',7,'hbe_salt_contract_house','盐酒席面',M(global_liquor_output_modifier=.30,cultural_tradition_modifier=.20),'盐引信用至少30','var:hbe_salt >= 30'),
 ('eastern_river',4,'hbe_river_warehouse','川江互保',M(global_merchant_capacity_modifier=.30,merchant_maintenance_efficiency=.20),'江运互保至少30','var:hbe_river >= 30'),
 ('eastern_river',7,'hbe_cliff_stockade','江岸会防',M(global_defensive=.25,army_maintenance_efficiency=.20),'完成本圈成长验收','has_variable = hbe_mission_eastern_river_2'),
 ('northern_shudao',4,'hbe_plank_fort','关隘轮守',M(global_supply_limit_modifier=.30,fort_maintenance_efficiency=.25),'轮戍履约至少30','var:hbe_roads >= 30'),
 ('northern_shudao',7,'hbe_gate_registry','蜀道接递',M(global_road_building_time=-.10,global_institution_growth_modifier=.25),'完成本圈成长验收','has_variable = hbe_mission_northern_shudao_2'),
 ('central_hills',4,'hbe_community_granary','义仓相济',M(global_monthly_food_modifier=.25,global_food_decay=-.20),'义仓储备至少30','var:hbe_grain >= 30'),
 ('central_hills',7,'hbe_witness_house','乡社清算',M(bank_interest=-.005,total_loan_capacity_modifier=.60),'义气至少60','var:hbe_yiqi >= 60'),
 ('western_tea_horse',4,'hbe_tea_exchange','茶马通路',M(global_tea_output_modifier=.30,global_merchant_capacity_modifier=.25),'商队互保至少30','var:hbe_tea >= 30'),
 ('western_tea_horse',7,'hbe_guide_station','山门公议',M(cultural_influence_modifier=.25,diplomatic_capacity_modifier=.25),'义气至少60','var:hbe_yiqi >= 60'),
 ('southwestern_valleys',4,'hbe_valley_inn','诸谷换市',M(global_tools_output_modifier=.30,global_production_efficiency=.15),'地方共治至少30','var:hbe_valleys >= 30'),
 ('southwestern_valleys',7,'hbe_covenant_stockade','乡寨共保',M(army_maintenance_efficiency=.25,tribes_estate_target_satisfaction=.10),'完成本圈成长验收','has_variable = hbe_mission_southwestern_valleys_2')]

SERVICE = {
 'chengdu_plain':('渠学减役', 'hbe_canal_office','hbe_water',8,4,'岁修与分水公议完成后，运行渠务所的地方事业额外获得8水权储备，役负降低4。'),
 'southern_salt_wine':('井灶保任','hbe_salt_office','hbe_salt',10,0,'井灶保任章程完成后，运行井灶公廨的地方事业额外获得10盐引信用。'),
 'eastern_river':('船帮联保','hbe_river_warehouse','hbe_river',8,2,'江岸会防约完成后，运行转运仓的地方事业额外获得8江运互保，役负降低2。'),
 'northern_shudao':('驿役轮替','hbe_plank_fort','hbe_roads',6,5,'关驿轮役册完成后，运行驿堡的地方事业额外获得6轮戍履约，役负降低5。'),
 'central_hills':('仓社宽役','hbe_community_granary','hbe_grain',10,3,'仓社赈借则完成后，运行义廪的地方事业额外获得10义仓储备，役负降低3。'),
 'western_tea_horse':('护行回报','hbe_guide_station','hbe_tea',10,1,'山程互保册完成后，运行护行所的地方事业额外获得10商队互保，役负降低1。'),
 'southwestern_valleys':('诸谷轮粮','hbe_covenant_stockade','hbe_valleys',8,4,'驻防粮额约完成后，运行议约寨的地方事业额外获得8地方共治，役负降低4。')}

BUILDING_BUFFS = {
 'hbe_assembly_hall':M(local_monthly_control=.10,local_burghers_max_literacy=5),
 'hbe_works_archive':M(local_construction_speed=.15,local_monthly_literacy=.02),
 'hbe_canal_office':M(local_monthly_food_modifier=.15,local_rice_output_modifier=.15),
 'hbe_brocade_school':M(local_fine_cloth_output_modifier=.20,local_burghers_max_literacy=10),
 'hbe_salt_office':M(local_salt_output_modifier=.20,local_construction_speed=.10),
 'hbe_salt_contract_house':M(local_liquor_output_modifier=.20,local_burghers_max_literacy=6),
 'hbe_river_warehouse':M(local_food_decay=-.25,local_construction_speed=.10),
 'hbe_cliff_stockade':M(local_manpower=.0015,local_defensive=.20),
 'hbe_plank_fort':M(local_manpower=.0015,local_defensive=.20),
 'hbe_gate_registry':M(local_monthly_control=.15,local_burghers_max_literacy=8),
 'hbe_community_granary':M(local_monthly_food_modifier=.20,local_food_decay=-.25),
 'hbe_witness_house':M(local_monthly_prosperity=.10,local_burghers_max_literacy=10),
 'hbe_tea_exchange':M(local_tea_output_modifier=.20,local_leather_output_modifier=.15),
 'hbe_guide_station':M(local_construction_speed=.15,local_food_decay=-.15),
 'hbe_valley_inn':M(local_tools_output_modifier=.20,local_monthly_prosperity=.08),
 'hbe_covenant_stockade':M(local_manpower=.0015,local_defensive=.15)}

def script_mods(mods):
 return ' '.join(f'{k} = {v:g}' for k,v in mods.items())

# Keep source values unscaled, so repeated builds do not apply a second nerf.
SOCIAL_REWARDS = {
 'hbe_tech_common_1': M(global_monthly_literacy=.025, global_monthly_control=.05),
 'hbe_tech_common_3': M(global_institution_growth_modifier=.20, global_max_literacy=5),
 'hbe_tech_common_8': M(burghers_estate_target_satisfaction=.06, global_trade_center_power=.15),
 'hbe_tech_southern_salt_wine_1': M(global_salt_output_modifier=.20, burghers_estate_target_satisfaction=.06),
 'hbe_tech_eastern_river_7': M(global_monthly_control=.10, global_levy_recruitment_speed_modifier=.20),
 'hbe_tech_northern_shudao_6': M(global_books_output_modifier=.20, global_monthly_literacy=.025),
 'hbe_tech_central_hills_2': M(stability_cost_efficiency=.15, global_monthly_control=.05),
 'hbe_tech_western_tea_horse_4': M(global_merchant_capacity_modifier=.25, global_institution_growth_modifier=.20),
 'hbe_tech_western_tea_horse_8': M(cultures_capacity_modifier=.20, cultural_tradition_modifier=.25),
 'hbe_tech_southwestern_valleys_3': M(global_tools_output_modifier=.25, tribes_estate_target_satisfaction=.06),
 'hbe_tech_southwestern_valleys_4': M(global_production_efficiency=.15, tolerance_heathen=1),
 'hbe_civic_common_2': M(country_cabinet_efficiency=.20, global_monthly_literacy=.025),
 'hbe_civic_eastern_river_1': M(burghers_estate_target_satisfaction=.08, global_monthly_control=.10),
 'hbe_civic_northern_shudao_1': M(global_supply_limit_modifier=.25, global_institution_growth_modifier=.15),
 'hbe_civic_southwestern_valleys_2': M(cultures_capacity_modifier=.20, tribes_estate_target_satisfaction=.10),
}
TECHNOLOGY_STRENGTH = .8
def balanced_mods(mods):
 return {k:round(v*TECHNOLOGY_STRENGTH, 8) for k,v in mods.items()}

def build_technology_rewards(out,root,loc,put,game):
 from build_special_goods import GOODS
 specialty={r['group']:r for r in GOODS}
 summary={'version':'0.3.0','advances':[],'production':[],'networks':[]}
 pm_unlocks={}
 for g,b,bn,an,good,bi,bo,ai,ao,bt,at in PRODUCTION:
  for suffix,title,inputs,output,index in [('basic',bn,bi,bo,bt),('advanced',an,ai,ao,at)]:
   produced=good
   if suffix=='advanced' and g in specialty:
    r=specialty[g];title=r['method'];inputs=r['inputs'];output=r['output'];produced=r['key']
   p=f'hbe_{g}_{suffix}_production'
   pm_unlocks.setdefault(f'hbe_tech_{g}_{index}',[]).append(p)
   loc[p]=title
   loc[p+'_desc']=f'{title}利用机构雇员与市场材料生产商品；缺工或缺料会降低实际产出。'
   summary['production'].append(dict(key=p,building=b,goods=produced,inputs=inputs,output=output,advance=f'hbe_tech_{g}_{index}'))
   if suffix=='advanced' and g in ['chengdu_plain','western_tea_horse']:
    premium=p.replace('_advanced_','_paper_');premium_inputs={('hbe_shu_paper' if k=='paper' else k):v for k,v in inputs.items()}
    pm_unlocks.setdefault(f'hbe_tech_{g}_{index}',[]).append(premium)
    loc[premium]='蜀纸描样' if g=='chengdu_plain' else '蜀纸包茶'
    loc[premium+'_desc']='选用蜀纸提高成品质量，满额基础产出提高25%；缺货时可改回普通纸生产。'
    summary['production'].append(dict(key=premium,building=b,goods=produced,inputs=premium_inputs,output=output*1.25,advance=f'hbe_tech_{g}_{index}'))
 # Vanilla country modifier names also include dynamically generated goods outputs.
 definitions=(game/'main_menu/common/modifier_type_definitions/00_modifier_types.txt').read_text(encoding='utf-8-sig')
 defined={k for k,*_ in blocks(definitions,0)}
 goods={k for f in (game/'in_game/common/goods').glob('*.txt') for k,*_ in blocks(f.read_text(encoding='utf-8-sig'),0)}
 goods|={r['key'] for r in GOODS}
 allmods={k for rows in [*REWARDS.values(),*CIVIC.values()] for row in rows for k in row}
 allmods|={k for mods in SOCIAL_REWARDS.values() for k in mods}
 allmods|={k for *_,mods,req,trigger in NETWORKS for k in mods}
 allmods|={k for mods in BUILDING_BUFFS.values() for k in mods}
 defined|={k for f in (out/'main_menu/common/modifier_type_definitions').glob('*.txt') for k,*_ in blocks(f.read_text(encoding='utf-8-sig'),0)}
 assert allmods <= defined, sorted(allmods-defined)
 for filename,catalog in [('hbe_advances.txt',REWARDS),('hbe_civic_advances.txt',CIVIC)]:
  path=out/'in_game/common/advances'/filename;txt=path.read_text(encoding='utf-8-sig');edits=[]
  for key,_,start,end,_ in blocks(txt,0):
   prefix='hbe_tech_' if key.startswith('hbe_tech_') else 'hbe_civic_'
   group,index=key.removeprefix(prefix).rsplit('_',1);base_mods=catalog[group][int(index)-1]
   mods=balanced_mods(SOCIAL_REWARDS.get(key,base_mods))
   body=txt[start:end]
   # A rebuild may reapply this pass: remove only fields owned by this catalogue.
   for m in set(base_mods)|set(mods):body=re.sub(r'(?m)^\s*'+re.escape(m)+r'\s*=\s*[-\d.]+\s*$', '',body)
   body=re.sub(r'(?m)^\s*unlock_production_method\s*=\s*hbe_\w+\s*$','',body)
   body=re.sub(r'(?m)^\s*# 0\.\d+\.\d+: immediate native rewards, rendered by the vanilla technology UI\.\s*$','',body).rstrip()
   body+='\n    # 0.3.0: immediate native rewards, rendered by the vanilla technology UI.\n'
   body+=''.join(f'    {m} = {v:g}\n' for m,v in mods.items())
   body+=''.join(f'    unlock_production_method = {p}\n' for p in pm_unlocks.get(key,[]))
   edits.append((start,end,body))
   prose=loc[key+'_desc'].split('\n\n')[0]
   # Generate from authoritative rules. Never feed previous generated prose back in.
   old=''
   node_index=int(index)
   if prefix=='hbe_tech_':
    if group!='common' and node_index==1:old='解锁本圈三年地方事业与地方援助资格'
    elif group!='common' and node_index==2:old='取得本圈成长验收的课题资格'
    elif group!='common' and node_index in (4,7):old='取得本圈旧约重审验收的课题资格'
    elif group!='common' and node_index in (5,8):old='取得本圈地区重组及百年章程验收的课题资格'
    if key=='hbe_tech_southern_salt_wine_4':old='解锁盐引贷款，并取得本圈旧约重审验收资格'
    if key=='hbe_tech_common_2':old='整合其他旧府州后，地方援助可以使用10点义气作替代担保'
   effects=[]
   if old:effects.append(old+'。')
   for p in pm_unlocks.get(key,[]):effects.append('解锁机构生产方式：'+loc[p]+'。')
   for g,idx,b,title,networkmods,req,trigger in NETWORKS:
    if key==f'hbe_tech_{g}_{idx}':
     effects.append(f'解锁“{title}”：运行{loc[b]}、近五年完成本圈事业、役负低于70，且{req}时获得额外联动收益；条件不满足时暂停。')
   if prefix=='hbe_civic_' and group!='common':
    if index=='1':
     _,b,counter,amount,relief,_=SERVICE[group]
     effects.append(f'运行{loc[b]}时，完成本圈地方事业额外获得{amount*.8:g}地区储备'+(f'，役负降低{relief*.8:g}' if relief else '')+'。')
    else:effects.append('续办地方事业时额外获得1.6义气；须维持本圈机构运行。')
   if key=='hbe_civic_common_2':effects.append('开放公账审计与逐圈客籍议约。签订某圈议约后授予该圈机构及基础兵种资格；仍需当地领土和实际供养，不一次开放全部七圈。')
   if not effects:effects.append('本课题的永久加成立即生效，并推进后续地区课题与验收。')
   if key=='hbe_tech_common_4':effects=['开放跨圈经营：满足条件并签订客籍议约后，可在目标圈建造机构并经营基础产业。']
   if key=='hbe_tech_common_5':effects.append('提高锦坊、井灶和诸谷作坊的实际产出，支持新生产方式。')
   if key=='hbe_tech_common_7':effects.append('降低原版道路工期与碎石路成本；可与蜀道接递叠加。')
   text='\n'.join(dict.fromkeys(effects))
   loc[key+'_effects']=text
   # The vanilla card already lists modifiers, native unlocks and pure_tooltip_entry.
   # Flavor descriptions must not repeat this entire mechanics table below it.
   loc[key+'_desc']=prose
   summary['advances'].append(dict(key=key,name=loc[key],modifiers=mods,unlocks=pm_unlocks.get(key,[]),link=text))
  put('in_game/common/advances/'+filename,apply_edits(txt,edits))
 # Existing sixteen institutions gain distinct local effects, fully supply-scaled.
 path=out/'in_game/common/building_types/hbe_civic_buildings.txt';txt=path.read_text(encoding='utf-8-sig');edits=[]
 for key,_,start,end,_ in blocks(txt,0):
  body=txt[start:end];mods=BUILDING_BUFFS[key]
  mb=next((z for z in blocks(body,0) if z[0]=='modifier'),None);assert mb,key
  old=body[mb[2]:mb[3]]
  for m in mods:old=re.sub(r'\b'+re.escape(m)+r'\s*=\s*[-\d.]+','',old)
  body=apply_edits(body,[(mb[2],mb[3],old+' '+script_mods(mods)+' ')])
  # Replace generated production slot while preserving original maintenance slot.
  prod=next((x for x in PRODUCTION if x[1]==key),None)
  if prod:
   for _,a,s,e,b in blocks(body,0):
    if 'hbe_'+prod[0]+'_basic_production' in body[s:e]:
     body=apply_edits(body,[(a,b,'')]);break
   g,b,bn,an,good,bi,bo,ai,ao,bt,at=prod
   methods=[]
   for suffix,inputs,output in [('basic',bi,bo),('advanced',ai,ao)]:
    produced=good
    if suffix=='advanced' and g in specialty:
     r=specialty[g];inputs=r['inputs'];output=r['output'];produced=r['key']
    methods.append(f'hbe_{g}_{suffix}_production = {{ icon_type = goods icon = {produced} {script_mods(inputs)} produced = {produced} output = {output:g} category = guild_input }}')
    if suffix=='advanced' and g in ['chengdu_plain','western_tea_horse']:
     premium_inputs={('hbe_shu_paper' if k=='paper' else k):v for k,v in inputs.items()}
     methods.append(f'hbe_{g}_paper_production = {{ icon_type = goods icon = {produced} allow = {{ has_advance = hbe_tech_common_6 }} {script_mods(premium_inputs)} produced = {produced} output = {output*1.25:g} category = guild_input }}')
   body+='\n unique_production_methods = { '+' '.join(methods)+' }\n'
   desc='\n\n本机构另设生产槽：'+bn+'，升级为'+an+'。生产消耗市场材料，产出进入原版市场；日常供养槽仍须维持。'
   loc[key+'_desc']=loc[key+'_desc'].split('\n\n本机构另设生产槽：')[0]+desc.replace(an,specialty[g]['method'] if g in specialty else an)
   loc[key+'_slot_0']='日常供养'
   loc[key+'_slot_1']='地方生产'
  edits.append((start,end,body))
 put('in_game/common/building_types/hbe_civic_buildings.txt',apply_edits(txt,edits))
 effects=[];static=[]
 for g,idx,b,title,mods,req,trigger in NETWORKS:
  mods=balanced_mods(mods)
  key=f'hbe_network_{g}_{idx}';loc[key]=title;loc[key+'_desc']=f'本圈科技、机构与近年事业共同维持的{title}。断供、役负过高或五年未交付后暂停。'
  loc['STATIC_MODIFIER_NAME_'+key]=title;loc['STATIC_MODIFIER_DESC_'+key]=loc[key+'_desc']
  static.append(f'{key} = {{ {script_mods(mods)} }}')
  cond=f'hbe_is_prince = yes is_member_of_international_organization = international_organization:hbe_empire has_advance = hbe_tech_{g}_{idx} hbe_operating_{b.removeprefix("hbe_")} = yes has_variable = hbe_recent_delivery_{g} var:hbe_burden < 70 {trigger}'
  effects.append(f'if = {{ limit = {{ {cond} }} if = {{ limit = {{ NOT = {{ has_country_modifier = {key} }} }} add_country_modifier = {{ modifier = {key} years = -1 }} }} }} else = {{ remove_country_modifier = {key} }}')
  summary['networks'].append(dict(key=key,name=title,advance=f'hbe_tech_{g}_{idx}',building=b,requirements=cond,modifiers=mods))
 put('main_menu/common/static_modifiers/hbe_technology_modifiers.txt','\n'.join(static))
 put('in_game/common/scripted_effects/hbe_technology_effects.txt','hbe_technology_networks = {\n'+'\n'.join(effects)+'\n}')
 put('in_game/common/on_action/hbe_technology_on_actions.txt','''on_game_start = { on_actions = { hbe_technology_start } }
hbe_technology_start = { effect = { every_country = { limit = { hbe_is_prince = yes } hbe_technology_networks = yes } } }
monthly_country_pulse = { on_actions = { hbe_technology_monthly } }
 hbe_technology_monthly = { trigger = { hbe_is_prince = yes } effect = { hbe_technology_networks = yes } }
''')
 # Additional rewards attach to actual completion, not a decision click or a monthly grant.
 path=out/'in_game/common/scripted_effects/hbe_civic_effects.txt';txt=path.read_text(encoding='utf-8-sig');edits=[]
 for key,_,start,end,_ in blocks(txt,0):
  if key.startswith('hbe_record_service_'):
   g=key.removeprefix('hbe_record_service_');_,b,counter,amount,relief,_=SERVICE[g]
   amount=round(amount*.8,8);relief=round(relief*.8,8)
   body=txt[start:end];body=re.sub(r'(?s)\n\s*# TECHNOLOGY_SERVICE_BEGIN.*?# TECHNOLOGY_SERVICE_END\n','\n',body)
   body+=f'\n # TECHNOLOGY_SERVICE_BEGIN\n if = {{ limit = {{ has_advance = hbe_civic_{g}_1 hbe_operating_{b.removeprefix("hbe_")} = yes }} change_variable = {{ name = {counter} add = {amount} }}'
   if relief:body+=f' change_variable = {{ name = hbe_burden add = -{relief} }} hbe_clamp_burden = yes'
   body+=f' if = {{ limit = {{ has_advance = hbe_civic_{g}_2 }} change_variable = {{ name = hbe_yiqi add = 1.6 }} hbe_clamp_yiqi = yes }} }}\n # TECHNOLOGY_SERVICE_END\n'
   edits.append((start,end,body))
 put('in_game/common/scripted_effects/hbe_civic_effects.txt',apply_edits(txt,edits))
 (root/'data/technology_rewards_v021.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 # All existing images are retained; production methods use vanilla goods icons.
 lines=['# 0.3.0 科技与地区产业','', '80项课题均有即时原版加成；16种机构强化，新增14种机构生产方式和14种条件联动。', '', '数值采用强势地区风味定位。永久加成与机构运营收益可叠加，地区A/B分支仍互斥。', '', '## 科技表','', '|课题|即时加成（原版字段）|联动与解锁|','|---|---|---|']
 for row in summary['advances']:lines.append('|'+row['name']+'|'+script_mods(row['modifiers'])+'|'+row['link'].replace('\n','；')+'|')
 lines+=['','## 机构生产','', '|机构|生产方式|原料|基础产出/级|解锁科技|','|---|---|---|---|---|']
 for row in summary['production']:lines.append(f'|{loc[row["building"]]}|{loc[row["key"]]}|{script_mods(row["inputs"])}|{row["goods"]} {row["output"]}|{loc[row["advance"]]}|')
 lines+=['','## 条件联动','', '需维持有效机构和雇员，近五年完成本圈地方事业，役负低于70。月初检查并撤销失效收益；旧存档科技即时加成由引擎自动识别。','', '原版参考：advances/readme.txt、building_types/readme.txt、production_fine_cloth.txt；所有原料与加成名对照当前安装的EU5数据库。']
 (root/'docs/technology_rewards_v021.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 return summary



