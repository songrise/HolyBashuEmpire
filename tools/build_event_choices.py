"""Authored incidents with explicit economic, social and political trade-offs."""
import json,re
from pdxscript import blocks,apply_edits

# Each circle's alternatives affect different systems; no generic three-button reward.
REGIONS=[
 ('chengdu_plain','hbe_water',[
  ('增派渠工，先保今年的收成。',{'global_monthly_food_modifier':.25,'global_rice_output_modifier':.20},0,8,-1),
  ('由府库出钱，雇工代役。',{'global_construction_speed':.15,'peasants_estate_target_satisfaction':.06},-6,-6,2),
  ('依乡约分水，官府不再包揽。',{'global_food_decay':-.15,'global_monthly_control':-.05},3,-3,-1)],[
  ('争水','上游乡民正在加高水口，以备夏日缺水。下游的庄户却来到府衙，声称新水口已让他们的田沟见底。双方都曾派人岁修，如今也都要求我们承认他们优先取水的权利。\n\n渠吏主张增调民夫，另开一道分水口。乡老愿按旧约自行安排，掌库官则提醒我们，雇工的钱只能从本府支出。'),
  ('绣坊的订单','锦江边的绣坊收到一批外地衣料订单，商人愿预付银钱，条件是如期交货。绣工们却正逢农忙，许多家庭已有人被征去修堰。\n\n坊主请求官府督促交货，并优先保障桑田用水。乡老希望准许工匠缓役；若让乡社自行分派，我们也就得接受他们对工期和税额的安排。'),
  ('重修堰口','春汛冲坏了旧堰的竹笼，渠吏建议趁农闲重修。下游的新田比祖辈时更多，旧有水口已无法照顾所有庄户。\n\n增征渠工可以早日保住收成，雇用工匠则能让乡民留在田里。几处乡社也愿接手工程，只是他们不肯再按官府原定的役额出人。')]),
 ('southern_salt_wine','hbe_salt',[
  ('让井灶昼夜开煎。',{'global_salt_output_modifier':.20,'global_hbe_well_salt_output_modifier':.30},6,10,-2),
  ('拨款修井，准灶户轮休。',{'global_production_efficiency':.15,'peasants_estate_target_satisfaction':.06},-7,-7,2),
  ('交给盐商承销，免去官府垫款。',{'global_merchant_capacity_modifier':.25,'burghers_estate_target_satisfaction':.05,'global_monthly_control':-.05},3,0,-2)],[
  ('井下与灶前','新打出的盐井卤味颇浓，井主请求添灶开煎。盐商已等在井口，愿按约收走头几批井盐。灶户却呈报，汲卤绳索磨损严重，轮班的工人也已多日没有休息。\n\n掌盐官希望趁高价加紧煎盐。我们也可以拨款整修井架，让灶户轮休，或将采办与承销交给商人处理。'),
  ('同一张盐引','几名盐商持同样编号的引券来到府衙，都说自己有权收取下一批盐货。账房承认转押时未及时注销旧券，如今井主无法按所有契纸交货。\n\n多开几灶可以赶交欠货，却要灶户承担额外劳作。修整井灶、重定工期需要府库垫款；商人也愿接下索偿，只要官府让出一部分承销权。'),
  ('祖父的盐井','一户灶主的后人继承了盐井，也收到祖父留下的欠款文书。他们声称井架年久失修，眼下的盐利不足以同时养家和还债。债主则要求官府兑现旧年担保。\n\n我们可以督促增产偿债，出钱整修并宽限劳作，或请盐商承销这口井的出货。每种办法都会改变井户今后依靠谁来维持生计。')]),
 ('eastern_river','hbe_river',[
  ('优先装运商货，收取加急费用。',{'global_merchant_capacity_modifier':.30,'global_food_decay':.10},6,4,-1),
  ('府库承担护航与修船开支。',{'ship_build_speed':.25,'merchant_maintenance_efficiency':.15},-6,-2,3),
  ('把船只留给江岸守军。',{'army_maintenance_efficiency':.20,'global_defensive':.20,'global_merchant_capacity_modifier':-.10},0,3,0)],[
  ('码头的船位','江水上涨后，数批商货一同抵达码头。船帮要求先装价高的货物，仓吏却担心粮船再等几日就会误了交割。江岸守军也在征用渡船，催促把兵员送到对岸。\n\n我们可以向商人出售优先装运的船位，出资扩充护航与修船，或先满足守军的调度。船只有限，今次无法同时照顾各方。'),
  ('峡口失船','一艘货船在峡口触礁，幸存船夫指称引水员未及时查看水势。船帮担心下一批商人改走别处，要求府库修补船只并增雇熟悉江道的人手。\n\n仓吏建议加收急运费，让商货尽快离岸。守军则认为应暂留渡船加强江防。商路与防务争用的人手，都要由本府安排。'),
  ('江防与转仓','沿江守军请求扩大船队，转运仓的商人却反对继续抽调货船。多年贸易带来的泊位已十分拥挤，新添的江防支出又要府库承担。\n\n若先照顾商运，我们能多收一笔费用；若出资修造，两方都可减轻眼下的困难。将现有船只留给守军，则能立即增强江岸防备。')]),
 ('northern_shudao','hbe_roads',[
  ('增调驿役，尽快接通栈道。',{'global_road_building_time':-.15,'global_supply_limit_modifier':.20},0,8,-1),
  ('出钱修造，编印驿券。',{'global_hbe_shu_paper_output_modifier':.30,'global_institution_growth_modifier':.20},-6,-4,2),
  ('准沿途商队自设驿站。',{'global_merchant_capacity_modifier':.20,'global_monthly_control':-.05},4,-2,-2)],[
  ('断了的栈道','山雨冲断了栈道，驿吏将积压的公文送到府衙。关口的守军尚有存粮，过路商人却无法继续等候。附近乡民已经出过一轮驿役，听说还要抽丁修路便起了争执。\n\n增征人手能尽快接通道路；由府库付工钱，并统一驿券，也许更适于长久经营。几支商队愿自行设站，只要求官吏不再逐处干预。'),
  ('驿券与纸坊','驿站领用的纸张参差不齐，有的券尾受潮后已无法辨认。关吏因此扣留几批商货，声称须待府衙核实印记才能放行。\n\n抄券人请求府库扶持附近纸坊，重订领用章程。我们也可增派驿役逐站查验，或准商队自行凭保任书通行。'),
  ('剑门的轮守','剑门守将呈报，轮戍名册仍沿用数十年前的丁额，几处山村已难按册出人。沿途商队则愿分担补给，以换取在驿站落脚的便利。\n\n继续征调能保住关道的工期与补给，出资整理簿券可以减少乡里的负担。接受商人设站的请求，则会让他们在山道上取得更多自主权。')]),
 ('central_hills','hbe_grain',[
  ('趁粮价尚高，售出余粮。',{'global_trade_center_power':.25,'global_food_decay':.10},8,0,-2),
  ('拨钱整仓，减免贫户欠粮。',{'global_food_decay':-.25,'peasants_estate_target_satisfaction':.08},-5,-5,3),
  ('粮食留下，供养乡兵。',{'global_manpower_modifier':.20,'army_maintenance_efficiency':.15,'global_monthly_food_modifier':-.10},0,4,0)],[
  ('仓中余粮','今年的秋收超过预料，仓吏却没有足够的人手翻晒新增粮食。粮商愿立即买走余粮，乡老希望宽免去年向义仓借粮的贫户，乡兵头领则要求留下口粮。\n\n出售粮食能充实府库；整修仓廒并减免旧欠需要另付费用。若把余粮拨给乡兵，我们在下一季也得供养更多人。'),
  ('借粮的归期','赈贷册上有许多尚未归还的粮食，出借者催促追偿，欠粮乡户却称近年的收成只够糊口。掌库官建议收回能收的部分，趁市价尚高售出。\n\n乡老请求减免欠粮并整修旧仓。乡兵也愿接手一部分仓储，条件是把这些粮食留作长期军粮。'),
  ('仓社换主','几座仓廒随田产转入了新的领主名下，原有乡社却坚持粮食仍由村中管理。仓吏发现旧仓已有漏雨之处，部分存粮不宜再久放。\n\n我们须决定售粮充库、出资重修并宽免旧欠，还是交给乡兵作为粮站。每个办法都能解决眼下的一部分问题，也会改变今后的供养。')]),
 ('western_tea_horse','hbe_tea',[
  ('向商隊出售独家茶货。',{'global_hbe_border_tea_output_modifier':.30,'global_tea_output_modifier':.15,'global_merchant_capacity_modifier':-.10},7,4,-2),
  ('府库分担护行，开放茶市。',{'global_merchant_capacity_modifier':.30,'merchant_maintenance_efficiency':.15},-6,-3,3),
  ('留茶待客，支持山门往来。',{'cultural_influence_modifier':.25,'tolerance_heathen':1,'global_production_efficiency':-.05},-2,-2,2)],[
  ('山外的茶客','来自山外的商人愿以较高价钱收走今年的边茶，要求茶坊不再向其他商队出售同样的货物。常年往来的驮户听闻此事，担心今后连采办都要仰人鼻息。\n\n独家承销能带来眼下的收益。若由府库分担护行，各家商队便可继续入市；附近山门也请求留出一部分茶货，供来往僧侣与使者使用。'),
  ('护行的价钱','山道上的向导要求提高报酬，几支商队因此停在茶市，不肯先行付款。茶坊等着发货，山门长者却提醒我们，近年的道路维护多由山民承担。\n\n一个大商队愿独家承销，以自己的护行费用抵偿差额。我们也可以分担费用开放互市，或留茶待客，借山门往来缓和争执。'),
  ('旧马与新茶','沿袭旧约的商人仍按祖辈的比例以马换茶，茶坊则认为如今的茶货更精细，旧价已不足以补偿采办。山地买家担心新价使互市难以继续。\n\n我们可以准许独家承销商另定价格，出资维持开放茶市，或将一部分茶货拨给山门供客。贸易的规模与山地诸家的信任，需要各付代价。')]),
 ('southwestern_valleys','hbe_valleys',[
  ('让铁木作坊加紧交货。',{'global_tools_output_modifier':.30,'global_production_efficiency':.15},5,8,-1),
  ('拨款修路，雇用谷中工匠。',{'global_construction_speed':.20,'tribes_estate_target_satisfaction':.08},-6,-5,2),
  ('承认乡寨自办互市的权利。',{'global_merchant_capacity_modifier':.25,'tribes_estate_target_satisfaction':.08,'global_monthly_control':-.05},2,-2,-1)],[
  ('谷市的农具','谷市的铁木作坊接到一批农具订单，匠人却在为运料争执。官吏要求按期出货，乡寨长者说山民还须照管自己的田地，不能总随官府调遣。\n\n我们可以督促作坊交货，拨款修路并雇用工匠，或承认乡寨自行安排互市。作坊的收益、乡里的负担与官府的权威，今次很难一并照顾。'),
  ('木契与印信','一桩铁料交易只有刻木为凭，府城书记不肯照约准运。谷中长者带来几名见证人，声称买卖早已成交，官吏此时扣料是在破坏乡约。\n\n我们可以要求作坊先交官府的货物，出资整修道路并请匠人重新签约，或准许乡寨沿用自己的互市凭证。'),
  ('乡寨的路钱','几处乡寨已合力修好入谷的小路，却不肯继续缴纳原定的路钱。掌事官担心别处也提出同样要求，作坊匠人则希望用这笔钱购买铁料。\n\n征调人手并督促交货可以增加眼下的产出。府库出资能让道路与工匠都受益；承认乡寨自办互市，则须让出一部分地方事务。')]),
]

def build_event_choices(out,root,loc,put,game):
 static=[];catalog=[]
 def guided(prose,group):
  term,words={'chengdu_plain':('water',['渠工','分水','岁修']), 'southern_salt_wine':('salt',['盐井','盐引','井灶']), 'eastern_river':('river',['船帮','江防','商运']), 'northern_shudao':('roads',['驿役','驿站','轮戍']), 'central_hills':('grain',['粮食','义仓','仓廒']), 'western_tea_horse':('tea',['茶市','护行','互市']), 'southwestern_valleys':('valleys',['乡寨','乡约','谷市'])}[group]
  word=next((w for w in words if w in prose),None)
  if word is None:
   word=next(w for w in ['工期','粮船','驿券','盐商','茶货','仓储','道路','绣工'] if w in prose)
  return prose.replace(word,"[Concept('hbe_term_"+term+"', '"+word+"')|e]",1)
 def option(event,letter,label,effects,trigger='',weight=33):
  loc[event+'.'+letter]=label
  return f'option = {{ name = {event}.{letter} '+(f'trigger = {{ {trigger} }} ' if trigger else '')+f'ai_chance = {{ base = {weight} }} {effects} }}'
 def edit_events(path,replacements):
  text=(out/path).read_text(encoding='utf-8-sig');edits=[]
  for k,_,s,e,_ in blocks(text,0):
   if k in replacements:
    body=text[s:e];opts=[(a,b,'') for t,a,_,_,b in blocks(body,0) if t=='option']
    body=apply_edits(body,opts).rstrip()+'\n'+'\n'.join(replacements[k])+'\n'
    edits.append((s,e,body))
  put(path,apply_edits(text,edits))
 changes={};base_changes={};social_changes={}
 for n,(group,res,choices,stories) in enumerate(REGIONS):
  for stage,(title,prose) in enumerate(stories):
   event=f'hbe_banquet.{100+n*3+stage}';loc[event+'.title']=title;loc[event+'.desc']=guided(prose,group)
   opts=[]
   for ci,(label,mods,gold,burden,credit) in enumerate(choices):
    key=f'hbe_choice_{group}_{ci+1}'
    if stage==0:
     static.append(key+' = { '+' '.join(f'{k} = {v:g}' for k,v in mods.items())+' }')
     loc[key]=['官府督办','府库出资','地方自理'][ci]+'：'+title
     loc['STATIC_MODIFIER_NAME_'+key]=loc[key];loc['STATIC_MODIFIER_DESC_'+key]='此项安排维持三年，同名效果刷新期限。'
    effects=f'add_gold = {gold} change_variable = {{ name = hbe_burden add = {burden} }} hbe_clamp_burden = yes change_variable = {{ name = hbe_yiqi add = {credit} }} hbe_clamp_yiqi = yes add_country_modifier = {{ modifier = {key} years = 3 mode = replace }}'
    # Switching arrangements replaces the earlier choice, preventing parallel stacking.
    effects=' '.join(f'remove_country_modifier = hbe_choice_{group}_{x}' for x in range(1,4))+ ' '+effects
    opts.append(option(event,chr(97+ci),label,effects,'gold >= '+str(-gold) if gold<0 else '',[35,40,25][ci]))
   changes[event]=opts;catalog.append(dict(id=event,title=title,choices=[dict(label=c[0],modifiers=c[1],gold=c[2],burden=c[3],credit=c[4],years=3) for c in choices]))
  # Seven recurrent regional incidents now offer the same region's full policy
  # alternatives instead of two ways of purchasing the same credit reward.
  event=f'hbe.{100+n}';loc[event+'.title']=stories[0][0];loc[event+'.desc']=guided(stories[0][1],group)
  base_changes[event]=[o.replace(f'hbe_banquet.{100+n*3}.',event+'.') for o in changes[f'hbe_banquet.{100+n*3}']]
  for ci,c in enumerate(choices):loc[event+'.'+chr(97+ci)]=c[0]
  catalog.append(dict(id=event,title=stories[0][0],regional_choices=True))
  # Civic incidents retain council completion and existing bill/reserve guards,
  # but gain regional consequences on top of paid relief / reserve spending / levy.
  for stage in range(2):
   event=f'hbe_civic.{100+n*2+stage}';title=stories[stage][0]+'：府议'
   loc[event+'.title']=title;loc[event+'.desc']=guided(stories[stage][1],group)+'\n\n府议已将争议送到我们面前。公款、地方储备与民役都有人提出，各方希望我们明确今后由谁承担费用。'
   # Preserve original guarded effects instead of fabricating completion flags.
   path=out/'in_game/events/hbe_civic_events.txt';text=path.read_text(encoding='utf-8-sig')
   body=next(text[s:e] for k,_,s,e,_ in blocks(text,0) if k==event)
   opts=[]
   for ci,(k,_,s,e,_) in enumerate(z for z in blocks(body,0) if z[0]=='option'):
    original=body[s:e];key=f'hbe_choice_{group}_{[2,3,1][ci]}'
    # Remove only the previous generated part when rebuilding.
    original=re.sub(r'remove_country_modifier = hbe_choice_\w+|add_country_modifier = \{ modifier = hbe_choice_\w+ years = 3 mode = replace \}','',original)
    extra=' '.join(f'remove_country_modifier = hbe_choice_{group}_{x}' for x in range(1,4))+f' add_country_modifier = {{ modifier = {key} years = 3 mode = replace }}'
    opts.append('option = {'+original.strip()+' '+extra+' }')
    loc[event+'.'+chr(97+ci)]=['府库付钱，给乡里减役。','动用地方储备，由乡社主持。','增征民役，加紧办完。'][ci]
   social_changes[event]=opts;catalog.append(dict(id=event,title=title,council_guards_preserved=True))
 edit_events('in_game/events/hbe_events.txt',base_changes)
 edit_events('in_game/events/hbe_banquet_events.txt',changes)
 edit_events('in_game/events/hbe_civic_events.txt',social_changes)
 # Success grants its core rewards before the event. A discretionary reinvestment
 # therefore pays out of the awarded money; retaining cash remains a valid choice.
 feast={}
 loc['hbe_banquet.1.desc']='诸府使者齐聚锦江，商议新一年的钱粮用途。共建派要求先修道路、仓廪与水渠，兴业派则希望扶持作坊、茶市与江运。两方都已备好文书，等待我们决定本府今后支持哪一种主张。'
 loc['hbe_banquet.2.desc']='上一届的使者离席后，新任掌事官将修桥与采办的清单送来。若府库愿先付一份费用，本府便可在共同事业中占有一席；乡老却希望留住现钱，待本地工程办成后再带着成果赴会。'
 loc['hbe_banquet.4.desc']='各府承办的工程终于按期告成。商旅沿新修的道路抵达市镇，粮仓与作坊也收到所需材料。会盟已经拨下本府应得的赏金。\n\n掌库官希望将钱留下备用，乡老请求从中支付一部分民夫工钱。商人也提出，可用这笔钱举办一场货会，招徕下一季的买家。'
 loc['hbe_banquet.5.desc']='约定的期限到了，几处工程却仍缺人手。出席的使者只好将未完事项留给下一届。\n\n掌事官请求拨一笔钱安顿已经出工的乡民，以免下次难以招募。府库不愿再付费用；另有官员主张公开追查失期之责，借此维护本府的名望。'
 for event in ['hbe_banquet.1','hbe_banquet.2','hbe_banquet.4','hbe_banquet.5']:
  text=loc[event+'.desc']
  if '会盟' not in text:text=text.replace('新任掌事官','会盟的新任掌事官',1) if event.endswith('.2') else '会盟'+text
  loc[event+'.desc']=text.replace('会盟',"[Concept('hbe_term_alliance', '会盟')|e]",1)
 for key,title,mods in [('hbe_event_workers_paid','民夫领酬',{'peasants_estate_target_satisfaction':.08,'global_construction_speed':.10}),('hbe_event_goods_fair','巴蜀货会',{'global_merchant_capacity_modifier':.25,'cultural_influence_modifier':.15})]:
  static.append(key+' = { '+' '.join(f'{k} = {v:g}' for k,v in mods.items())+' }');loc[key]=title;loc['STATIC_MODIFIER_NAME_'+key]=title;loc['STATIC_MODIFIER_DESC_'+key]='本届结余支持的地方安排。'
 feast['hbe_banquet.4']=[option('hbe_banquet.4','a','把赏金存入府库。',''),option('hbe_banquet.4','b','拿出三金，给民夫付酬。','add_gold = -3 change_variable = { name = hbe_burden add = -5 } hbe_clamp_burden = yes add_country_modifier = { modifier = hbe_event_workers_paid years = 2 mode = replace }','gold >= 3',40),option('hbe_banquet.4','c','拿出四金，招集各地商人。','add_gold = -4 add_country_modifier = { modifier = hbe_event_goods_fair years = 2 mode = replace }','gold >= 4',30)]
 feast['hbe_banquet.5']=[option('hbe_banquet.5','a','先付两金，安顿出工的乡民。','add_gold = -2 change_variable = { name = hbe_burden add = -5 } hbe_clamp_burden = yes change_variable = { name = hbe_yiqi add = 2 } hbe_clamp_yiqi = yes','gold >= 2',40),option('hbe_banquet.5','b','追查失期之责。','add_prestige = 3 change_variable = { name = hbe_burden add = 4 } hbe_clamp_burden = yes',weight=25),option('hbe_banquet.5','c','等下一届再议，留下这笔钱。','',weight=35)]
 edit_events('in_game/events/hbe_banquet_events.txt',feast)
 loc['hbe_banquet.7.desc']=loc['hbe_banquet.7.desc'].replace('共同贡献',"[Concept('hbe_term_alliance', '共同贡献')|e]",1)
 catalog.extend([dict(id=k,settlement_rewards_preserved=True) for k in feast])
 put('main_menu/common/static_modifiers/hbe_event_choice_modifiers.txt','\n'.join(static))
 (root/'data/event_choices_v021.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
 (root/'docs/event_choices_v021.md').write_text('# 事件抉择 0.3.0\n\n对照原版 flavor_chi 的具体情势、宫廷分歧与简短立场选项，重写开局及两派核心叙述。正文采用独立创作，数值由引擎效果提示显示。\n\n44个事件新增或强化实际取舍：7个地区常见事件、21个跨年代地区事件、14个府议事件，以及成功与失期两项结算事件。保留117个事件定义。\n\n七圈分别围绕灌溉与绣坊、盐井与承销、江运与江防、驿路与纸坊、义仓与乡兵、茶市与山门、谷市与自治作出选择。各圈有三种相斥的三年安排，切换时移除其他安排，不能把多次选择叠成三套收益。金钱、役负、信誉以及产业、补给、粮损或地方控制的代价均落在实际脚本中。\n\n府议保留原付款、储备与议事完成条件。成功结算的基础奖励照常发放，玩家另选保留现金、付民夫酬劳或举办货会。失败结算不自动扣款或处罚，玩家可选择自愿补贴、追查责任或保留现钱。状态账册与通知不额外提供可反复领取的奖励。\n',encoding='utf-8',newline='\n')
 return dict(reworked_events=len(catalog),regional=28,civic=14,settlement=2,style_reference='main_menu/localization/simp_chinese/events/DHE/flavor_chi_l_simp_chinese.yml',mutually_exclusive_arrangements=21)
