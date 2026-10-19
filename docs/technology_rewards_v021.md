# 0.3.2 科技与地区产业

当前共91项科技：原64项共有与地区科技、16项政制科技、4项产业副产科技及7项军制科技。产业、民役与军制分别研究，详见[早期科技调整](early_research_v032.md)。下表保留原80项课题的有效数值。

## 科技表

|课题|即时加成（原版字段）|联动与解锁|
|---|---|---|
|乡约与账簿|global_monthly_control = 0.01|开放本府府议；民役政策与军制分别研究。|
|统一度量|global_merchant_capacity_modifier = 0.08|开放乡社见证权；整合其他旧府州后，地方援助可以使用10点义气作替代担保。|
|帝国工程署|global_institution_growth_modifier = 0.16 global_max_literacy = 4||
|匠人互访|global_institution_growth_modifier = 0.16 hbe_can_cross_circle_industry = yes|开放跨圈经营：满足条件并签订客籍议约后，可在目标圈建造机构并经营基础产业。|
|行会传习|global_burghers_max_literacy = 4|开放行会雇价保任；仍须采用行会雇办。|
|跨区工艺学堂|research_speed_modifier = 0.12 global_books_output_modifier = 0.16 global_hbe_shu_paper_output_modifier = 0.16||
|驿路勘绘|global_road_building_time = -0.12 build_gravel_road_cost_modifier = -0.12|；降低原版道路工期与碎石路成本；可与蜀道接递叠加。|
|山河交通总图|burghers_estate_target_satisfaction = 0.048 global_trade_center_power = 0.12||
|渠田协作|global_monthly_food_modifier = 0.05|解锁本圈三年地方事业与地方援助资格。|
|蜀锦作坊分工|global_hbe_shu_embroidery_output_modifier = 0.1|取得本圈成长验收的课题资格。；解锁机构生产方式：锦坊试织。|
|水权簿册|global_food_decay = -0.12 peasants_estate_target_satisfaction = 0.04||
|联渠灌溉|global_monthly_food_modifier = 0.16 global_rgo_build_time = -0.16|取得本圈旧约重审验收的课题资格。；；；解锁“渠田共济”：运行渠务所、近五年完成本圈事业、役负低于70，且水权储备至少30时获得额外联动收益；条件不满足时暂停。|
|天府粮仓|global_rice_output_modifier = 0.24 global_devastation_recovery = 0.004|取得本圈地区重组及百年章程验收的课题资格。|
|官学讲会|global_max_literacy = 8 cultural_tradition_modifier = 0.12||
|茶会章程|diplomatic_capacity_modifier = 0.16 stability_cost_efficiency = 0.12|取得本圈旧约重审验收的课题资格。；解锁“锦江讲会”：运行锦户讲习院、近五年完成本圈事业、役负低于70，且义气至少60时获得额外联动收益；条件不满足时暂停。|
|盖碗公议学宫|research_speed_modifier = 0.16 cultural_influence_modifier = 0.2 global_hbe_shu_embroidery_output_modifier = 0.24|取得本圈地区重组及百年章程验收的课题资格。|
|井灶公账|global_hbe_well_salt_output_modifier = 0.1|解锁本圈三年地方事业与地方援助资格。；解锁机构生产方式：井灶汲卤。|
|盐酒作坊协作|global_liquor_output_modifier = 0.1|取得本圈成长验收的课题资格。|
|井灶改良|global_salt_output_modifier = 0.24 global_tools_output_modifier = 0.12 global_hbe_well_salt_output_modifier = 0.24||
|盐引担保|total_loan_capacity_modifier = 0.4 bank_interest = -0.004|解锁盐引贷款，并取得本圈旧约重审验收资格。；解锁“井盐担保”：运行井灶公廨、近五年完成本圈事业、役负低于70，且盐债不超过20时获得额外联动收益；条件不满足时暂停。|
|巴蜀盐业总号|global_salt_output_modifier = 0.2 global_merchant_capacity_modifier = 0.2 global_hbe_well_salt_output_modifier = 0.2|取得本圈地区重组及百年章程验收的课题资格。|
|窖坊分工|global_liquor_output_modifier = 0.24 cultural_tradition_modifier = 0.08||
|宴席采购契约|merchant_maintenance_efficiency = 0.16 global_production_efficiency = 0.08|取得本圈旧约重审验收的课题资格。；解锁“盐酒席面”：运行盐酒契券所、近五年完成本圈事业、役负低于70，且盐引信用至少30时获得额外联动收益；条件不满足时暂停。|
|帝国席面承办局|global_liquor_output_modifier = 0.2 cultural_influence_modifier = 0.2|取得本圈地区重组及百年章程验收的课题资格。|
|码头转运|global_merchant_capacity_modifier = 0.08|解锁本圈三年地方事业与地方援助资格。|
|纤夫船帮|global_naval_supplies_output_modifier = 0.1|取得本圈成长验收的课题资格。；解锁机构生产方式：江船备料。|
|关卡通行公约|global_trade_center_power = 0.16 merchant_maintenance_efficiency = 0.12||
|江运互保|global_merchant_capacity_modifier = 0.2 global_food_decay = -0.08|取得本圈旧约重审验收的课题资格。；解锁机构生产方式：船帮联作。；解锁“川江互保”：运行江岸转运仓、近五年完成本圈事业、役负低于70，且江运互保至少30时获得额外联动收益；条件不满足时暂停。|
|川江通商总约|global_trade_center_power = 0.2 global_production_efficiency = 0.12|取得本圈地区重组及百年章程验收的课题资格。|
|崖岸壁垒|global_defensive = 0.16 fort_maintenance_efficiency = 0.16||
|水陆协防|global_monthly_control = 0.08 global_levy_recruitment_speed_modifier = 0.16|取得本圈旧约重审验收的课题资格。；解锁“江岸会防”：运行山城联防寨、近五年完成本圈事业、役负低于70，且完成本圈成长验收时获得额外联动收益；条件不满足时暂停。|
|山城江防枢纽|global_defensive = 0.2 army_initiative = 0.12|取得本圈地区重组及百年章程验收的课题资格。|
|栈道勘绘|global_road_building_time = -0.12 build_gravel_road_cost_modifier = -0.12|解锁本圈三年地方事业与地方援助资格。|
|驿堡联络|merchant_maintenance_efficiency = 0.05 global_road_building_time = -0.05|取得本圈成长验收的课题资格。|
|山关防务|global_defensive = 0.2 fort_maintenance_efficiency = 0.16||
|轮戍互援|global_levy_recruitment_speed_modifier = 0.2 army_maintenance_efficiency = 0.16|取得本圈旧约重审验收的课题资格。；解锁“关隘轮守”：运行栈道驿堡、近五年完成本圈事业、役负低于70，且轮戍履约至少30时获得额外联动收益；条件不满足时暂停。|
|蜀道联防总镇|global_defensive = 0.16 global_manpower_modifier = 0.16|取得本圈地区重组及百年章程验收的课题资格。|
|关市驿券|global_books_output_modifier = 0.16 global_monthly_literacy = 0.02|解锁机构生产方式：关驿抄券。|
|公文分驿|global_road_building_time = -0.12 diplomatic_capacity_modifier = 0.16 global_hbe_shu_paper_output_modifier = 0.2|取得本圈旧约重审验收的课题资格。；；解锁“蜀道接递”：运行关市券所、近五年完成本圈事业、役负低于70，且完成本圈成长验收时获得额外联动收益；条件不满足时暂停。|
|蜀道驿传总局|global_institution_growth_modifier = 0.24 global_monthly_control = 0.08|取得本圈地区重组及百年章程验收的课题资格。|
|坡田水塘|global_monthly_food_modifier = 0.05|开放分仓义廪基础建造与维护；农业生产方式仍由第二时代后续科技解锁。|
|市集公账|global_merchant_capacity_modifier = 0.05 global_monthly_control = 0.01|取得本圈成长验收的课题资格。|
|分仓赈贷|global_food_decay = -0.2 food_purchase_efficiency = 0.16|解锁机构生产方式：仓社附田。|
|乡社借粮|stability_cost_efficiency = 0.16 peasants_estate_target_satisfaction = 0.064|取得本圈旧约重审验收的课题资格。；解锁机构生产方式：塘堰轮作。；解锁“义仓相济”：运行分仓义廪、近五年完成本圈事业、役负低于70，且义仓储备至少30时获得额外联动收益；条件不满足时暂停。|
|丘陵义仓联社|global_monthly_food_modifier = 0.2 global_disease_resistance = 0.04|取得本圈地区重组及百年章程验收的课题资格。|
|契约见证|total_loan_capacity_modifier = 0.32 burghers_estate_target_satisfaction = 0.064||
|票据清算|bank_interest = -0.004 merchant_maintenance_efficiency = 0.16|取得本圈旧约重审验收的课题资格。；解锁“乡社清算”：运行公信券馆、近五年完成本圈事业、役负低于70，且义气至少60时获得额外联动收益；条件不满足时暂停。|
|诸侯公信会馆|global_merchant_capacity_modifier = 0.2 global_monthly_prosperity = 0.04|取得本圈地区重组及百年章程验收的课题资格。|
|茶马集市|global_hbe_border_tea_output_modifier = 0.1|解锁本圈三年地方事业与地方援助资格。；解锁机构生产方式：驮具修造。|
|山地向导|global_supply_limit_modifier = 0.05 merchant_maintenance_efficiency = 0.05|取得本圈成长验收的课题资格。|
|商队互保|global_leather_output_modifier = 0.2 global_food_decay = -0.08 global_hbe_border_tea_output_modifier = 0.2|；|
|通路会约|global_merchant_capacity_modifier = 0.2 global_institution_growth_modifier = 0.16|取得本圈旧约重审验收的课题资格。；解锁“茶马通路”：运行茶马交割场、近五年完成本圈事业、役负低于70，且商队互保至少30时获得额外联动收益；条件不满足时暂停。|
|茶马通商公所|global_tea_output_modifier = 0.24 global_trade_center_power = 0.16 global_hbe_border_tea_output_modifier = 0.24|取得本圈地区重组及百年章程验收的课题资格。|
|山门施济|tolerance_heathen = 0.8 global_disease_resistance = 0.04||
|跨地调停|diplomatic_capacity_modifier = 0.2 cultural_influence_modifier = 0.16|取得本圈旧约重审验收的课题资格。；解锁“山门公议”：运行山程护行所、近五年完成本圈事业、役负低于70，且义气至少60时获得额外联动收益；条件不满足时暂停。|
|雪山公议会|cultures_capacity_modifier = 0.16 cultural_tradition_modifier = 0.2|取得本圈地区重组及百年章程验收的课题资格。|
|山谷市集|global_trade_center_power = 0.08|解锁本圈三年地方事业与地方援助资格。；解锁机构生产方式：谷市农具。|
|地方盟约|tribes_estate_target_satisfaction = 0.03 peasants_estate_target_satisfaction = 0.02|取得本圈成长验收的课题资格。|
|小路换市|global_tools_output_modifier = 0.2 tribes_estate_target_satisfaction = 0.048||
|商盟互保|global_production_efficiency = 0.12 tolerance_heathen = 0.8|取得本圈旧约重审验收的课题资格。；解锁机构生产方式：诸谷铁木联作。；解锁“诸谷换市”：运行谷市盟栈、近五年完成本圈事业、役负低于70，且地方共治至少30时获得额外联动收益；条件不满足时暂停。|
|川西南山谷商盟|global_tools_output_modifier = 0.2 burghers_estate_target_satisfaction = 0.08|取得本圈地区重组及百年章程验收的课题资格。|
|联寨守望|global_supply_limit_modifier = 0.2 global_levy_recruitment_speed_modifier = 0.12||
|议约驻防|army_maintenance_efficiency = 0.16 global_defensive = 0.12|取得本圈旧约重审验收的课题资格。；解锁“乡寨共保”：运行乡寨议约寨、近五年完成本圈事业、役负低于70，且完成本圈成长验收时获得额外联动收益；条件不满足时暂停。|
|山地共保盟府|global_manpower_modifier = 0.2 tribes_estate_target_satisfaction = 0.08|取得本圈地区重组及百年章程验收的课题资格。|
|府议与民役簿|无被动数值加成|开放三种互斥的民役政策与减役补偿；驻防粮额与阶层特权分别开放。|
|修约与公账审计|country_cabinet_efficiency = 0.16 global_monthly_literacy = 0.02|开放公账审计与逐圈客籍议约。签订某圈议约后授予该圈机构及基础兵种资格；仍需当地领土和实际供养，不一次开放全部七圈。|
|岁修与分水公议|global_monthly_food_modifier = 0.12 global_fine_cloth_output_modifier = 0.12 global_hbe_shu_embroidery_output_modifier = 0.16|运行渠务所时，完成本圈地方事业额外获得6.4地区储备，役负降低3.2。|
|渠学传习规程|global_books_output_modifier = 0.24 cultural_tradition_modifier = 0.16|续办地方事业时额外获得1.6义气；须维持本圈机构运行。|
|井灶保任章程|global_salt_output_modifier = 0.16 burghers_estate_target_satisfaction = 0.08 global_hbe_well_salt_output_modifier = 0.16|运行井灶公廨时，完成本圈地方事业额外获得8地区储备。|
|契券清偿总约|bank_interest = -0.004 total_loan_capacity_modifier = 0.4|续办地方事业时额外获得1.6义气；须维持本圈机构运行。|
|江岸会防约|burghers_estate_target_satisfaction = 0.064 global_monthly_control = 0.08|运行江岸转运仓时，完成本圈地方事业额外获得6.4地区储备，役负降低1.6。|
|寨兵常训章程|army_initiative = 0.16 army_maintenance_efficiency = 0.12|续办地方事业时额外获得1.6义气；须维持本圈机构运行。|
|关驿轮役册|global_supply_limit_modifier = 0.2 global_institution_growth_modifier = 0.12|运行栈道驿堡时，完成本圈地方事业额外获得4.8地区储备，役负降低4。|
|关镇养兵法|global_defensive = 0.2 global_manpower_modifier = 0.12|续办地方事业时额外获得1.6义气；须维持本圈机构运行。|
|仓社赈借则|global_food_decay = -0.12 peasants_estate_target_satisfaction = 0.08|运行分仓义廪时，完成本圈地方事业额外获得8地区储备，役负降低2.4。|
|公信复核章程|global_monthly_prosperity = 0.064 global_estate_target_satisfaction = 0.064|续办地方事业时额外获得1.6义气；须维持本圈机构运行。|
|山程互保册|global_tea_output_modifier = 0.16 merchant_maintenance_efficiency = 0.12|运行山程护行所时，完成本圈地方事业额外获得8地区储备，役负降低0.8。|
|山门与商路公议|tolerance_heathen = 0.8 diplomatic_capacity_modifier = 0.16|续办地方事业时额外获得1.6义气；须维持本圈机构运行。|
|驻防粮额约|global_supply_limit_modifier = 0.16 tribes_estate_target_satisfaction = 0.08|运行乡寨议约寨时，完成本圈地方事业额外获得6.4地区储备，役负降低3.2。|
|诸谷共保续约|cultures_capacity_modifier = 0.16 tribes_estate_target_satisfaction = 0.08|续办地方事业时额外获得1.6义气；须维持本圈机构运行。|

## 机构生产

|机构|生产方式|原料|基础产出/级|解锁科技|
|---|---|---|---|---|
|锦户讲习院|锦坊试织|silk = 0.45 dyes = 0.08|fine_cloth 0.65|蜀锦作坊分工|
|锦户讲习院|锦坊绣作|silk = 0.6 dyes = 0.12 tools = 0.06 paper = 0.04|hbe_shu_embroidery 1.2|锦样分授|
|锦户讲习院|蜀纸描样|silk = 0.6 dyes = 0.12 tools = 0.06 hbe_shu_paper = 0.04|hbe_shu_embroidery 1.5|锦样分授|
|井灶公廨|井灶汲卤|lumber = 0.35 tools = 0.08|salt 0.8|井灶公账|
|井灶公廨|井灶精煎|lumber = 0.45 tools = 0.15|hbe_well_salt 1.8|井灶合煎|
|江岸转运仓|江船备料|lumber = 0.4 cloth = 0.15|naval_supplies 0.65|纤夫船帮|
|江岸转运仓|船帮联作|lumber = 0.55 cloth = 0.2 tools = 0.06|naval_supplies 1.1|江运互保|
|关市券所|关驿抄券|lumber = 0.4 tools = 0.05|paper 0.55|关市驿券|
|关市券所|蜀纸精抄|lumber = 0.6 tools = 0.08|hbe_shu_paper 1.25|槽帘传习|
|分仓义廪|仓社附田|lumber = 0.2 tools = 0.06|rice 0.7|分仓赈贷|
|分仓义廪|塘堰轮作|lumber = 0.3 tools = 0.1|rice 1.25|乡社借粮|
|茶马交割场|驮具修造|livestock = 0.5 tools = 0.05|leather 0.65|茶马集市|
|茶马交割场|边茶压砖|tea = 0.65 tools = 0.08 paper = 0.03|hbe_border_tea 1.2|商队互保|
|茶马交割场|蜀纸包茶|tea = 0.65 tools = 0.08 hbe_shu_paper = 0.03|hbe_border_tea 1.5|商队互保|
|谷市盟栈|谷市农具|iron = 0.25 lumber = 0.2|tools 0.5|山谷市集|
|谷市盟栈|诸谷铁木联作|iron = 0.4 lumber = 0.25|tools 0.85|商盟互保|

## 条件联动

需维持有效机构和雇员，近五年完成本圈地方事业，役负低于70。月初检查并撤销失效收益；旧存档科技即时加成由引擎自动识别。

原版参考：advances/readme.txt、building_types/readme.txt、production_fine_cloth.txt；所有原料与加成名对照当前安装的EU5数据库。
