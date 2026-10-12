"""Four native market goods, with real population demand and regional production."""
import json,re
from pdxscript import blocks,apply_edits

GOODS = [
 dict(key='hbe_shu_embroidery',name='蜀绣',base='fine_cloth',price=9,transport=.35,development=10,wealth=1.0,demand={'nobles':.22,'burghers':.10,'clergy':.08},group='chengdu_plain',building='hbe_brocade_school',advance=4,inputs={'silk':.60,'dyes':.12,'tools':.06,'paper':.04},output=1.20,method='锦坊绣作',boosts=[('hbe_tech_chengdu_plain_2',.25),('hbe_tech_chengdu_plain_8',.30)],network=('chengdu_plain',7),desc='锦江两岸的织坊以丝为底，以彩线施针，山水花鸟遂能随衣冠远行。府第陈设与礼物往来，为绣工提供了比寻常布帛更丰厚的订单。'),
 dict(key='hbe_well_salt',name='井盐',base='salt',price=5,transport=.40,development=0,wealth=.7,demand={'nobles':.08,'burghers':.07,'clergy':.05,'peasants':.02},group='southern_salt_wine',building='hbe_salt_office',advance=3,inputs={'lumber':.45,'tools':.15},output=1.80,method='井灶精煎',boosts=[('hbe_tech_southern_salt_wine_3',.30),('hbe_tech_southern_salt_wine_5',.25)],network=('southern_salt_wine',4),desc='深井取卤，灶火成盐。川南井户将地底的咸水煎成洁净细盐，装入盐袋，沿江运向城镇与山地；食用、腌藏与长途备粮使它有着广泛的买家。'),
 dict(key='hbe_shu_paper',name='蜀纸',base='paper',price=4,transport=.25,development=5,wealth=.8,demand={'nobles':.10,'burghers':.09,'clergy':.12},group='northern_shudao',building='hbe_gate_registry',advance=7,inputs={'lumber':.60,'tools':.08},output=1.25,method='蜀纸精抄',boosts=[('hbe_tech_northern_shudao_7',.25),('hbe_tech_common_6',.20)],network=('northern_shudao',7),desc='竹麻入槽，纤维成帘。蜀地纸坊供应驿券、契书与经卷，轻而便运的纸张又成为锦坊描样和茶商包装所需的材料，商旅与读书人的订单遂汇到同一座纸坊。'),
 dict(key='hbe_border_tea',name='边茶',base='tea',price=5,transport=.25,development=0,wealth=.7,demand={'nobles':.08,'burghers':.12,'clergy':.10,'tribesmen':.05},group='western_tea_horse',building='hbe_tea_exchange',advance=3,inputs={'tea':.65,'tools':.08,'paper':.03},output=1.20,method='边茶压砖',boosts=[('hbe_tech_western_tea_horse_3',.25),('hbe_tech_western_tea_horse_5',.30)],network=('western_tea_horse',4),desc='散茶筛拣、蒸压成砖，再用竹篾束紧。商队需要经得起山程与风雨的茶货，山地聚落、寺院与市镇的持续购买，使护行与茶坊经营成为同一条商路上的事业。'),
]

def prepare_special_goods(out,root,loc,put,game):
 from build_technology_rewards import REWARDS,CIVIC,NETWORKS,BUILDING_BUFFS
 definitions=[];modifier_definitions=[]
 for r in GOODS:
  k=r['key'];loc[k]=r['name'];loc[k+'_desc']=r['desc'];loc['goods_'+k]=r['name']
  demand=' '.join(f'{p} = {v:g}' for p,v in r['demand'].items())
  colors={'hbe_shu_embroidery':'0.13 0.52 0.57','hbe_well_salt':'0.86 0.78 0.59','hbe_shu_paper':'0.89 0.90 0.77','hbe_border_tea':'0.24 0.40 0.15'}
  definitions.append(f"{k} = {{ category = produced color = rgb {{ {colors[k]} }} default_market_price = {r['price']:g} transport_cost = {r['transport']:g} development_threshold = {r['development']} demand_add = {{ {demand} }} wealth_impact_threshold = {{ all = {r['wealth']:g} }} }}")
  for scope,category in [('global','country'),('local','location')]:
   modifier=f'{scope}_{k}_output_modifier'
   modifier_definitions.append(f'{modifier} = {{ percent = yes game_data = {{ category = {category} }} }}')
   loc['MODIFIER_TYPE_NAME_'+modifier]=('本地' if scope=='local' else '')+r['name']+'产出'
   loc['MODIFIER_TYPE_DESC_'+modifier]='调整'+r['name']+'的实际商品产量。'
  for node,value in r['boosts']:
   group,index=node.removeprefix('hbe_tech_').rsplit('_',1)
   REWARDS[group][int(index)-1]['global_'+k+'_output_modifier']=value
  BUILDING_BUFFS[r['building']]['local_'+k+'_output_modifier']=.25
  for group,idx,b,title,mods,req,trigger in NETWORKS:
   if (group,idx)==r['network']:mods['global_'+k+'_output_modifier']=.30
  # Civic production synergies remain distinct, rather than a blanket gold grant.
  if r['group']=='chengdu_plain':CIVIC[r['group']][0]['global_'+k+'_output_modifier']=.20
  if r['group']=='southern_salt_wine':CIVIC[r['group']][0]['global_'+k+'_output_modifier']=.20
 put('in_game/common/goods/hbe_special_goods.txt','\n'.join(definitions))
 put('main_menu/common/modifier_type_definitions/hbe_goods_modifiers.txt','\n'.join(modifier_definitions))
 # pop_demand is a hardcoded singleton. Preserve its complete vanilla body and
 # append these four keys, rather than replacing it with a partial demand block.
 original=(game/'in_game/common/goods_demand/pop_demands.txt').read_text(encoding='utf-8-sig')
 p=next(x for x in blocks(original,0) if x[0]=='pop_demand')
 original=apply_edits(original,[(p[2],p[3],original[p[2]:p[3]]+'\n # Holy Bashu Empire: population demand for regional finished goods.\n'+'\n'.join(r['key']+' = 1' for r in GOODS)+'\n')])
 put('in_game/common/goods_demand/pop_demands.txt',original)
 return dict(version='0.3.0',goods=GOODS,demand_registration='Full native pop_demand preserved with four appended keys; conflicts with other mods replacing this singleton.',balance='Demand-driven premium goods; reference price is not guaranteed sale income.')

def finish_special_goods(out,root,loc,put,game,summary):
 from PIL import Image,ImageDraw,ImageFont
 from build_native_flags import extract_charges
 from build_icon_assets import fit
 from build_flags import save_dds
 source=root/'assets/art_v021/special_goods.png'
 atlas=Image.open(source).convert('RGBA');sprites=extract_charges(atlas,cols=2,rows=2,threshold=64)
 preview=Image.new('RGB',(800,235),'#20272b');draw=ImageDraw.Draw(preview);font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',20)
 for n,r in enumerate(GOODS):
  icon=fit(sprites[n][0],128);k=r['key']
  png=root/'assets/art_v021/goods'/f'{k}.png';png.parent.mkdir(parents=True,exist_ok=True);icon.save(png)
  save_dds(out/f'main_menu/gfx/interface/icons/trade_goods/icon_goods_{k}.dds',icon)
  # Vanilla market detail illustrations match the original goods category.
  target=out/f'main_menu/gfx/interface/icons/trade_goods/illustrations/icon_goods_{k}.dds'
  import shutil
  target.parent.mkdir(parents=True,exist_ok=True)
  shutil.copyfile(game/f'main_menu/gfx/interface/icons/trade_goods/illustrations/icon_goods_{r["base"]}.dds',target)
  preview.paste(icon,(n*200+36,28),icon);draw.text((n*200+74,174),r['name'],font=font,fill='#dfd0b2')
 preview.save(root/'assets/art_v021/goods_preview.png')
 (root/'data/special_goods_v021.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
 lines=['# 巴蜀特色商品 0.3.0','','四种独立市场商品，供需、雇工、原料和运输参与原版价格与收益计算。基础价仅是参考价，不是固定收入。','','|商品|产出建筑|科技|输入|每级满额基础产出|参考价|人口需求系数|','|---|---|---|---|---|---|---|']
 for r in GOODS:
  lines.append('|'+r['name']+'|'+loc[r['building']]+'|'+loc['hbe_tech_'+r['group']+'_'+str(r['advance'])]+'|'+', '.join(loc.get(k,k)+f' {v:g}' for k,v in r['inputs'].items())+f'|{r["output"]}|{r["price"]}|'+', '.join(f'{p} {v:g}' for p,v in r['demand'].items())+'|')
 lines+=['','基础生产方式仍供应普通商品；高阶方式改产名贵成品，在同一生产槽中二选一。锦坊绣作、井灶精煎、蜀纸精抄和边茶压砖保留原科技门槛。绣坊与茶坊另可选用蜀纸描样和蜀纸包茶，须先完成公共印刷课题，基础产出再提高25%；蜀纸缺货时可退回普通纸生产。生产科技提供25–30%特色产出，建筑提供25%，满足地区合作条件后再获30%；盛会的生产效率奖励也会提高实际经营收益。','','贵族、市民、教士是名贵品主要买家；井盐另有农民需求，边茶另有部落居民需求。蜀纸还是绣坊描样和边茶包装的生产投入，需求不只来自人口。需求过低、缺工或缺料仍会影响利润。','','新增商品与人口需求定义建议新开存档。覆盖完整原版pop_demand以追加四项，其他修改同一人口需求定义的模组需合并兼容。商品小图标由内置ImageGen制作，商品详情背景沿用对应原版商品插画，维持游戏风格。']
 (root/'docs/special_goods_v021.md').write_text('\n'.join(lines)+'\n',encoding='utf-8',newline='\n')
 return summary
