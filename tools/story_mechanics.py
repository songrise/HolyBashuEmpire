"""Authored mechanical choices: profiles describe concrete policies, not circle templates."""
PROFILES = {
'night_market': ('夜市开灯', {'global_merchant_capacity_modifier':.08,'tax_income_efficiency':-.04}),
'guild': ('行会旧规', {'burghers_estate_target_satisfaction':.04,'global_production_efficiency':.04,'global_merchant_capacity_modifier':-.04}),
'audit': ('公开核账', {'global_monthly_control':.01,'tax_income_efficiency':.04}),
'school': ('共同传习', {'global_monthly_literacy':.01,'research_speed_modifier':.06,'nobles_estate_target_satisfaction':-.02}),
'patron': ('府第供养', {'cultural_influence_modifier':.08,'nobles_estate_target_satisfaction':.04,'peasants_estate_target_satisfaction':-.02}),
'craft': ('作坊试制', {'global_production_efficiency':.06,'research_speed_modifier':.03}),
'contract': ('限期承包', {'global_production_efficiency':.08,'peasants_estate_target_satisfaction':-.03}),
'wages': ('足额雇工', {'peasants_estate_target_satisfaction':.04,'tax_income_efficiency':-.03}),
'relief': ('减租宽限', {'peasants_estate_target_satisfaction':.05,'tax_income_efficiency':-.05}),
'nature': ('保留山界', {'global_monthly_food_modifier':-.04,'cultural_influence_modifier':.08,'global_disease_resistance':.03}),
'survey': ('实地查验', {'global_institution_growth_modifier':.06,'research_speed_modifier':.05}),
'tribute': ('礼物采办', {'monthly_prestige':.08,'global_production_efficiency':.04,'burghers_estate_target_satisfaction':-.02}),
'medicine': ('共同诊治', {'global_disease_resistance':.08,'peasants_estate_target_satisfaction':.03}),
'quarantine': ('停市隔离', {'global_disease_resistance':.12,'global_merchant_capacity_modifier':-.06}),
'road': ('通行便道', {'global_road_building_time':-.08,'merchant_maintenance_efficiency':.06}),
'military': ('关军供养', {'global_supply_limit_modifier':.08,'army_maintenance_efficiency':.05,'peasants_estate_target_satisfaction':-.03}),
'levy': ('征役赶办', {'ship_build_speed':.10,'global_monthly_food_modifier':-.04,'peasants_estate_target_satisfaction':-.04}),
'justice': ('按证裁断', {'global_monthly_control':.015,'nobles_estate_target_satisfaction':-.03}),
'custom': ('旧礼作保', {'nobles_estate_target_satisfaction':.04,'global_monthly_control':-.005}),
'witness': ('共同见证', {'global_monthly_control':.01,'tribes_estate_target_satisfaction':.03,'global_merchant_capacity_modifier':.03}),
'public_land': ('共用地界', {'global_monthly_food_modifier':.06,'nobles_estate_target_satisfaction':-.03}),
'estate_land': ('承认田册', {'tax_income_efficiency':.06,'nobles_estate_target_satisfaction':.03,'peasants_estate_target_satisfaction':-.03}),
'grain': ('赈济口粮', {'global_food_decay':-.08,'peasants_estate_target_satisfaction':.04}),
'seed': ('试种留种', {'global_monthly_food_modifier':.08,'global_rice_output_modifier':.05}),
'festival': ('乡社开台', {'cultural_influence_modifier':.08,'peasants_estate_target_satisfaction':.03}),
'censor': ('官署礼序', {'nobles_estate_target_satisfaction':.04,'monthly_prestige':.05,'cultural_influence_modifier':-.04}),
'sponsor': ('商户供席', {'cultural_influence_modifier':.05,'burghers_estate_target_satisfaction':.03,'tax_income_efficiency':-.02}),
'temple': ('寺院主持', {'clergy_estate_target_satisfaction':.05,'monthly_prestige':.04}),
'public_art': ('匠人署名', {'cultural_influence_modifier':.10,'clergy_estate_target_satisfaction':-.02}),
'tolls': ('关桥收费', {'tax_income_efficiency':.08,'global_merchant_capacity_modifier':-.05}),
'translation': ('互译契纸', {'global_monthly_literacy':.008,'global_migration_attraction':.06,'tribes_estate_target_satisfaction':.03}),
'trade': ('公开验货', {'global_merchant_capacity_modifier':.08,'merchant_maintenance_efficiency':.05}),
'winter_pasture': ('轮牧养马', {'global_livestock_output_modifier':.08,'global_supply_limit_modifier':.05}),
'well': ('共用水井', {'global_disease_resistance':.06,'global_monthly_food_modifier':.04}),
'training': ('地方操练', {'monthly_army_tradition':.05,'army_maintenance_efficiency':-.03}),
'billet': ('守军办仓', {'global_supply_limit_modifier':.10,'navy_maintenance_efficiency':.04,'burghers_estate_target_satisfaction':-.03}),
'research_archive': ('公开图录', {'research_speed_modifier':.08,'global_monthly_literacy':.01,'clergy_estate_target_satisfaction':-.03}),
'exhibition': ('陈馆迎客', {'cultural_influence_modifier':.10,'global_merchant_capacity_modifier':.05,'research_speed_modifier':-.03}),
'price_control': ('官定收购', {'tax_income_efficiency':.05,'burghers_estate_target_satisfaction':.03,'global_production_efficiency':-.04}),
'work_damage': ('停工损失', {'global_production_efficiency':-.05}),
'village_repair': ('村寨养桥', {'merchant_maintenance_efficiency':.07,'tribes_estate_target_satisfaction':.04}),
'open_register': ('准许入籍', {'global_migration_attraction':.12,'global_migration_speed_modifier':.08,'nobles_estate_target_satisfaction':-.04}),
'settlement': ('新乡安置', {'global_population_capacity_modifier':.06,'global_migration_attraction':.08,'tax_income_efficiency':-.04}),
'closed_register': ('保留旧户', {'global_migration_attraction':-.10,'nobles_estate_target_satisfaction':.04,'peasants_estate_target_satisfaction':.02}),
'integration': ('乡里互认', {'global_pop_assimilation_speed_modifier':.08,'tribes_estate_target_satisfaction':.02,'global_monthly_literacy':.006}),
'arrival_pressure': ('安置争执', {'peasants_estate_target_satisfaction':-.03,'global_monthly_food_modifier':-.03}),
}

# Each line corresponds to the written options, in their existing order.
# Tokens: g gold, p prestige, s stability, r research; estate satisfaction is immediate.
SOLO_PLANS = {
'chengdu_plain': '''night_market g-6 p2 | guild burghers.03 peasants-.02 | sponsor burghers.02 peasants.02
school g-6 r.3 | custom p3 nobles.03 burghers-.02 | craft g-4 r.2
nature peasants.03 | survey g-4 r.25 | seed g-5 peasants-.02
craft g-7 r.3 | tribute p4 burghers-.02 | trade burghers.03 nobles-.02
trade p2 nobles-.02 | custom clergy.02 tribes-.03 | medicine g-3 r.15
school g-6 peasants.03 | guild p2 | contract g4 peasants-.02
craft g-7 r.3 | patron p4 | contract burghers.03
justice p2 nobles-.03 | custom p3 burghers-.03 | audit g-3 burghers.02
public_land g-5 peasants.03 | justice p2 nobles-.02 | witness g-2 clergy.02
public_art g-8 p3 | research_archive g-4 r.3 | sponsor p3
trade g-4 burghers.03 | guild p2 | school g-3 r.2
festival g-5 peasants.04 | censor p4 peasants-.03 | sponsor burghers.03
medicine g-7 r.25 | custom p3 clergy.03 | grain g-5 peasants.03''',
'southern_salt_wine': '''wages g-6 clergy-.02 | temple p3 peasants-.02 | public_art g-4 p3
public_land peasants.03 clergy-.03 | witness g-4 | temple peasants.02
relief g-9 p2 | audit g-3 burghers-.03 | contract g3 peasants-.04
festival p2 nobles-.03 | patron g-5 p4 | trade burghers.03
justice p2 burghers-.03 | audit g-5 | witness p1
well g-7 peasants.03 | survey g-6 r.25 | levy g3 peasants-.04
justice nobles-.02 peasants.03 | censor p3 peasants-.02 | audit burghers.02
public_land g-5 peasants.03 | relief nobles.02 | contract burghers.03
relief g-4 peasants.03 | craft g-6 p2 | price_control g5 burghers.03
grain g-6 peasants.03 | temple g-4 clergy.03 | audit g-3
wages g-6 peasants.03 | contract g2 peasants-.04 | craft g-7 r.2
justice p2 nobles-.03 | custom p4 peasants-.03 | witness burghers.02
school nobles-.03 r.2 | guild g-4 burghers.02 | craft g-6 r.3''',
'eastern_river': '''public_art g-6 p2 | temple g-4 p4 | witness clergy.02
road g-7 peasants.04 | witness burghers-.02 | tolls g6 peasants-.03
relief g-5 peasants.03 | survey g-4 r.25 | contract g3
justice p2 nobles-.02 | festival g-6 p3 | billet burghers-.02
trade tribes.03 | medicine g-4 r.25 | price_control g4 tribes-.02
craft g-8 r.3 | nature burghers-.03 | military g-4 p3
nature g-6 tribes.03 | research_archive g-5 r.35 | exhibition p4
public_land g-6 | audit g-4 | trade burghers.03
translation g-6 r.2 | custom p3 tribes-.03 | witness tribes.03
justice p2 nobles-.03 | censor p4 peasants-.03 | school g-4 r.15
seed g-6 peasants.02 | survey g-5 r.3 | tribute p4
festival g-5 burghers.02 | witness p2 | trade g-3 clergy-.03
school g-7 nobles-.03 | guild p3 | craft g-4 r.2''',
'northern_shudao': '''wages g-5 peasants.03 | military p3 | witness p1
medicine g-5 r.25 | custom clergy.03 | school g-4 peasants.02
relief g-5 peasants.03 | audit p2 | contract burghers.03
school g-7 r.3 | military p3 | craft burghers.03
public_land p2 nobles-.03 | custom g-6 p3 | road g-5
road g-5 r.15 | military p3 | guild burghers.03
relief g-5 p2 | military g-4 p4 | witness g-3 peasants.03
school g-6 r.3 | custom p3 nobles.04 | sponsor burghers.03
nature g-6 peasants.03 | survey g-4 r.2 | training g-5 p3
well burghers-.03 peasants.03 | craft g-7 r.2 | military g-4
trade g-4 | audit g-7 p2 | billet p3
witness p2 nobles-.03 | custom p3 burghers-.02 | audit g-4
justice p2 nobles-.03 | custom p4 peasants-.03 | audit burghers.02''',
'central_hills': '''relief g-6 peasants.03 | contract g-7 burghers.02 | guild p3 peasants-.03
justice p2 nobles-.02 | guild g-3 p3 | school g-6 r.25
public_land p2 nobles-.03 | road g-7 | relief g-3 peasants.03
grain g-5 peasants.03 | audit g-4 | guild burghers.03
public_art burghers.02 | research_archive g-7 r.3 | temple p4
trade peasants.03 | guild p3 | audit g-4
research_archive g-6 r.3 | patron p4 | witness r.15
public_land nobles-.03 | seed g-7 r.2 | wages g-4 peasants.02
trade burghers.02 | guild p3 | craft g-6 r.3
relief g-5 peasants.03 | audit g-3 | contract burghers.03
seed peasants.03 nobles-.02 | survey g-6 r.3 | custom g-4 p3
grain g-6 nobles-.03 | custom p3 | festival g-4
training g-6 peasants.03 | military p3 peasants-.03 | relief p-2 peasants.04''',
'western_tea_horse': '''trade tribes.03 burghers-.02 | contract p3 | witness g-4
craft g-7 r.3 | survey g-4 r.2 | guild g-3 p3
medicine g-6 peasants.03 | quarantine p2 burghers-.03 | contract burghers.03
public_art g-5 tribes.03 | craft g-6 r.2 | trade burghers.03
well g-8 tribes.02 | custom g-5 p3 | closed_register p4
medicine g-6 r.3 | custom p3 clergy.03 | winter_pasture g-4 r.2
relief p-2 peasants.03 | road g-6 | military g-5 p3
school g-5 tribes.03 | translation g-7 r.2 | guild burghers.03
public_land g-5 tribes.03 | survey g-4 r.25 | custom p4 tribes-.02
witness p2 nobles-.03 | patron g-4 p4 | justice g-3
festival p2 clergy-.03 | temple g-4 p4 | witness g-3 tribes.03
road g-4 p2 | audit p3 | tolls g5 tribes-.03
translation g-6 r.2 | military p3 | patron g-4 p4''',
'southwestern_valleys': '''wages g-6 peasants.03 | audit p2 | billet g-4 p3
seed g-5 peasants.03 | survey g-6 r.3 | price_control p3 peasants-.03
school g-6 r.25 | contract g3 | craft burghers.03
well g-6 burghers-.02 | medicine g-5 r.3 | tolls g5 peasants-.03
justice p2 nobles-.03 | custom p3 | witness g-4 tribes.03
trade tribes.03 | survey g-6 r.3 | tribute g-3 p4
festival g-6 tribes.03 | sponsor burghers.03 | military p3 clergy-.03
justice p2 nobles-.03 | guild p3 peasants-.03 | audit g-5
translation g-7 tribes.03 | witness p2 | custom p4 tribes-.03
public_art g-6 tribes.03 | witness g-7 p3 | tribute p4 tribes-.03
justice p2 nobles-.03 | relief g-4 | audit g-3
well g-8 peasants.03 | craft g-7 r.3 | contract g-4 peasants-.02
witness p2 nobles-.03 | patron p4 tribes-.03 | translation g-6 r.25'''
}

LONG_PLANS = {
'chengdu_plain': '''nature g-5 peasants.02 | survey g-5 r.3 | exhibition g4 p2
medicine g-7 peasants.03 | survey g-6 r.25 | patron p4
public_land g-8 nobles-.03 | survey g-6 r.3 | estate_land p3
nature p-2 | research_archive g-5 r.3 | contract g5 p3
grain g-8 | survey g-7 r.4 | patron g-3 peasants-.03
witness p2 | research_archive g-6 r.4 | patron p5
wages g-7 peasants.03 | school g-8 r.4 | exhibition g3''',
'southern_salt_wine': '''wages g-6 | survey g-6 r.3 | contract g5
audit g-5 | research_archive g-6 r.4 | exhibition p4
medicine g-7 | survey g-6 r.3 | price_control g4
wages g-8 | research_archive g-8 r.4 | craft g-4
public_art g-8 p3 | survey g-6 r.3 | exhibition g-5 p4
witness clergy-.03 | research_archive g-7 r.4 | exhibition p5
school g-8 | research_archive g-7 r.4 | contract g5''',
'eastern_river': '''wages g-6 | survey g-6 r.3 | military p3
relief g-8 | survey g-7 r.4 | billet p3
witness p2 | justice p-2 r.2 | tolls g5
wages g-6 | school g-6 r.3 | military g3
public_land g-6 | craft g-8 r.3 | billet p3
trade g-5 | audit g-6 | tolls g7
sponsor g-4 | school g-8 r.4 | military g-4''',
'northern_shudao': '''wages g-5 | survey g-6 r.3 | military p3
wages g-6 | craft g-7 r.3 | military g-4
witness clergy-.03 | research_archive g-7 r.4 p-2 | temple g-5 p4
wages g-8 | survey g-10 r.4 | military g-6
school g-6 | research_archive g-7 r.4 | military p3
craft g-6 | survey g-8 r.4 | military g-5
relief g-6 | school g-8 r.4 nobles-.03 | military p4''',
'central_hills': '''relief g-6 | survey g-6 r.3 | estate_land g4
road g-8 | survey g-7 r.3 | estate_land p3
public_land g-5 | survey g-6 r.3 | estate_land g5
relief g-6 | seed g-8 r.3 | estate_land p3
grain g-7 | audit g-6 r.25 | estate_land g5
grain g-7 | survey g-8 r.4 | contract g4
witness nobles-.03 | audit g-7 | estate_land p4''',
'western_tea_horse': '''medicine g-6 tribes.03 | survey g-6 r.3 | military p3
trade g-5 tribes.03 | medicine g-8 r.3 | military g-4
public_land g-5 tribes.03 | winter_pasture g-7 r.25 | military g-5
quarantine g-8 | medicine g-8 r.4 | military burghers-.03
trade tribes.03 | survey g-7 r.3 | military p4
winter_pasture g-5 | survey g-7 r.4 | military p3
school g-7 tribes.03 | medicine g-8 r.4 | military g-5''',
'southwestern_valleys': '''village_repair g-6 tribes.03 | craft g-8 r.3 | tolls g5
witness p2 | translation g-6 r.3 | military p3
relief g-6 | survey g-7 r.3 | levy g3
village_repair g-5 | craft g-10 r.4 | contract g5
trade tribes.03 | audit g-6 | tolls g5
village_repair g-8 | survey g-7 r.3 | military p3
witness nobles-.03 | audit g-7 | estate_land p4'''
}

ENDINGS = {
'chengdu_plain': [('山林护兽约', {'peasants_estate_target_satisfaction':.03,'global_disease_resistance':.05,'cultural_influence_modifier':.08,'global_monthly_food_modifier':-.02}), ('锦城瑞兽馆', {'monthly_prestige':.08,'cultural_influence_modifier':.10,'global_merchant_capacity_modifier':.04,'tax_income_efficiency':-.02})],
'southern_salt_wine': [('巨骨公藏与井谱', {'research_speed_modifier':.08,'global_monthly_literacy':.008,'global_institution_growth_modifier':.06}), ('盐城龙骨陈馆', {'cultural_influence_modifier':.10,'global_hbe_well_salt_output_modifier':.08,'monthly_prestige':.06,'research_speed_modifier':-.02})],
'eastern_river': [('百滩共用船约', {'merchant_maintenance_efficiency':.08,'global_merchant_capacity_modifier':.06,'burghers_estate_target_satisfaction':.02}), ('川江护航总署', {'navy_maintenance_efficiency':.08,'global_supply_limit_modifier':.08,'tax_income_efficiency':.03,'burghers_estate_target_satisfaction':-.02})],
'northern_shudao': [('山地测候公课', {'research_speed_modifier':.08,'global_institution_growth_modifier':.06,'global_monthly_literacy':.008}), ('关军传时网', {'global_defensive':.08,'global_supply_limit_modifier':.08,'monthly_army_tradition':.03,'research_speed_modifier':-.02})],
'central_hills': [('坡田共护章程', {'global_monthly_food_modifier':.08,'global_food_decay':-.05,'peasants_estate_target_satisfaction':.03}), ('坡田统一田册', {'tax_income_efficiency':.06,'global_monthly_control':.01,'global_monthly_food_modifier':.04,'peasants_estate_target_satisfaction':-.02})],
'western_tea_horse': [('茶路医马学舍', {'global_disease_resistance':.06,'merchant_maintenance_efficiency':.06,'global_livestock_output_modifier':.08,'tribes_estate_target_satisfaction':.02}), ('良马官苑', {'army_maintenance_efficiency':.06,'global_supply_limit_modifier':.08,'monthly_army_tradition':.03,'tax_income_efficiency':-.02})],
'southwestern_valleys': [('诸谷共桥约', {'merchant_maintenance_efficiency':.08,'global_merchant_capacity_modifier':.04,'tribes_estate_target_satisfaction':.03}), ('关桥总署', {'tax_income_efficiency':.06,'global_monthly_control':.01,'global_defensive':.06,'tribes_estate_target_satisfaction':-.02})]
}
