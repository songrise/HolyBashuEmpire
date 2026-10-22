"""Native institutions, policies, special regiments and recurring civic affairs.

This runs after the 0.1.1 conversion, so inherited events and old-save bridges
remain authoritative. Research unlocks are real native database references.
"""
import hashlib,json,re
from collections import defaultdict
from PIL import Image,ImageDraw,ImageFont
from pdxscript import blocks,apply_edits
from build_flags import save_dds
from build_icon_assets import fit
from expansion_catalogue import BUILDINGS,TECHS,UNITS,OFFICES,INCIDENTS,POLITICAL_ART

MEMBER='is_member_of_international_organization = international_organization:hbe_empire'
def identity(group=None, *, negate=False):
    """Keep native-circle identity distinct from the shared HBE certificate."""
    if group is None:
        return 'hbe_is_prince_tag = yes'
    origin = f'hbe_research_origin_{group} = yes'
    if negate:
        return f'custom_tooltip = {{ text = hbe_not_origin_{group}_tt NOT = {{ {origin} }} }}'
    return origin
def tech(g,i):return f'hbe_civic_{g}_{i}'
def dv(k):return f"[ROOT.GetVariable('{k}').GetValue|0]"
CIVIC_INTRO = {
    'title': '地方事业待办',
    'body': '府署收到了几份新提议：有的希望招来商人、筹措工料，有的请求修路、清渠或安置农户。办这些事需要钱，也需要人手，由本府决定先办哪一项。\n\n点击屏幕右下角的「地方事业」，可查看全国和地方两个候选项目，每次选择一个。卡片上会列出金币、役负、预计收益和所需时间。开工后自动推进，完工时会弹窗告知实际收益；未选择的项目到期后会自动换新。',
    'button': '知道了。',
}


def burden(n):return f'change_variable = {{ name = hbe_burden add = {n} }} hbe_clamp_burden = yes'
def yiqi(n):return f'change_variable = {{ name = hbe_yiqi add = {n} }} hbe_clamp_yiqi = yes'
def pay(value='hbe_public_bill'):return f'add_gold = {{ value = {value} multiply = -1 }}'

def build_social_expansion(out,root,countries,regions,loc,put):
    tags=[c['tag'] for c in countries];bygroup={r[0]:[c['tag'] for c in countries if c['region']==r[0]] for r in regions}
    R={r[0]:r for r in regions};allid=identity();unlocks=defaultdict(list);effects=[];triggers=[];events=[];decisions=[];eventdata=[];decisiondata=[]
    def licensed(g):return f'OR = {{ {identity(g)} has_variable = hbe_guest_{g} }}'
    def active(k):return f'hbe_operating_{k.removeprefix("hbe_")} = yes'
    def regional_active(g):return 'OR = { '+ ' '.join(active(b[0]) for b in BUILDINGS if b[2]==g)+' }'
    def event(eid,title,body,opts,scene='council',immediate='',hidden=False):
        key=f'hbe_civic.{eid}';loc[key+'.title']=title;loc[key+'.title.entry']=title;loc[key+'.desc']=body
        options=[]
        for i,(name,eff,allow,weight) in enumerate(opts):
            ok=f'{key}.{chr(97+i)}';loc[ok]=name
            options.append(f'option = {{ name = {ok} '+(f'trigger = {{ {allow} }} ' if allow else '')+f'ai_chance = {{ base = {weight} }} {eff} }}')
        events.append(f'{key} = {{ type = country_event '+('hidden = yes ' if hidden else '')+f'title = {key}.title desc = {key}.desc illustration_tags = {{ 1000 = hbe_event_art_{scene} }} '+(f'immediate = {{ {immediate} }} ' if immediate else '')+' '.join(options)+' }')
        eventdata.append(dict(id=key,title=title,body=body,scene=scene,recurring=True))
    def decision(key,title,body,allow,eff,art='hbe_council',potential='',group=None,ai=0):
        dtags=bygroup[group] if group else tags
        for suffix in ('.title','.title.entry'):loc[key+suffix]=title
        loc[key+'.desc']=body;loc[key+'.desc.entry']=body;loc[key+'.a']='办理此事'
        decisions.append(f'''{key} = {{
 tags = {{ {' '.join(dtags)} }} decision_category = country_specific_decisions
 image = "gfx/interface/hbe/civic/decisions/{art}.dds"
 potential = {{ {MEMBER} {allid} {potential} }}
 allow = {{ {allow} }} ai_will_do = {{ value = {ai} }}
 option = {{ name = {key}.a ai_chance = {{ value = 100 }} effect = {{ {eff} }} }}
}}''')
        decisiondata.append(dict(key=key,title=title,body=body,art=art,tags=dtags))

    # Native building maintenance affects modifiers and total_effective_building_levels.
    buildings=[];buildingdata=[]
    for k,name,g,index,category,pop,inputs,mods,unique in BUILDINGS:
        t=f'hbe_tech_{g}_{index}';unlock=(f'OR = {{ has_advance = {t} AND = {{ has_advance = {tech("common",2)} has_variable = hbe_guest_{g} }} }}' if g!='common' else f'has_advance = {t}')
        geo='scripted_geography:hbe_domain' if g=='common' else f'scripted_geography:hbe_geo_{g}'
        loc[k]=name;loc[k+'_desc']=f'{name}保存本地事业的凭据，也承担相应的人手与材料。机构能够发挥多少作用，取决于实际就业和维护投入。\n\n'+('全国同类最多一所；失去会盟资格后，建筑仍在，公议权益暂停。' if unique else '每个适用地块一级；地区权益须由本府实际供养，不能凭空支领。')
        loc[k+'_maintenance']=name+'日常供养';loc[k+'_maintenance_desc']='消耗所列材料，维持机构运行。'
        allowance=unlock+(f' country_has_no_other_copy_of_building = {{ type = {k} }}' if unique else '')
        geolimit=f'is_in_scripted_geography = {geo}'
        if k=='hbe_river_warehouse':geolimit+=' OR = { has_river = yes is_coastal = yes }'
        if k=='hbe_cliff_stockade':geolimit+=' OR = { topography = mountains topography = hills topography = plateau }'
        buildings.append(f'''{k} = {{
 is_special = yes is_foreign = no forbidden_for_estates = yes
 category = {category} pop_type = {pop} employment_size = 0.15 max_levels = 1
 build_time = 540 construction_demand = hbe_institution_construction
 rural_settlement = yes town = yes city = yes megalopolis = yes
 country_potential = {{ {MEMBER} {allid} }}
 location_potential = {{ {geolimit} }}
 allow = {{ scope:actor = {{ {unlock} }} {('country_has_no_other_copy_of_building = { type = '+k+' }') if unique else ''} }}
 modifier = {{ {mods} {('can_recruit_regiment_in_this_location = yes max_regiments_trained_at_same_time = 1') if g!='common' else ''} }}
 unique_production_methods = {{ {k}_maintenance = {{ icon_type = building_type icon = {k} {inputs} category = building_maintenance }} }}
 ai_construct_weight = {{ value = 0.7 }}
}}''')
        trig=active(k).split(' = ')[0]
        triggers.append(f'{trig} = {{ {MEMBER} total_effective_building_levels:{k} >= 0.25 any_owned_location = {{ any_buildings_in_location = {{ building_type = building_type:{k} building_employed_amount >= 0.05 }} }} }}')
        unlocks[t].append('unlock_building = '+k)
        buildingdata.append(dict(key=k,name=name,group=g,advance=t,maintenance=inputs,unique_country=unique,employment=150,build_days=540))
    put('in_game/common/building_types/hbe_civic_buildings.txt','\n'.join(buildings))
    put('in_game/common/goods_demand/hbe_civic_construction.txt','hbe_institution_construction = { lumber = 0.6 masonry = 0.4 tools = 0.1 category = building_construction }')
    loc['hbe_institution_construction']='巴蜀机构营建物资'
    # Effective capacity counts all special regiments in ONE family, including upgrades.
    institution_sum=' '.join('add = total_effective_building_levels:'+b[0] for b in BUILDINGS if b[2]!='common')
    vals=f'''hbe_public_bill = {{ value = monthly_income_trade_and_tax multiply = 0.5 min = 2 }}
hbe_paid_bill = {{ value = monthly_income_trade_and_tax multiply = 0.75 min = 3 }}
hbe_civic_special_count = {{ {' '.join('add = total_sub_unit_type_count:'+u[0] for u in UNITS)} }}
hbe_civic_institution_capacity = {{ {institution_sum} floor = yes }}
hbe_civic_special_limit = {{
 value = 0
 if = {{ limit = {{ {MEMBER} potential_army_size >= 0.5 var:hbe_burden < 70 }}
 value = potential_army_size multiply = 0.2 divide = 0.5 floor = yes min = 1
 max = hbe_civic_institution_capacity }}
}}
'''
    put('in_game/common/script_values/hbe_civic_values.txt',vals)
    loc['hbe_civic_special_family']='巴蜀议约军';loc['hbe_civic_special_family_desc']='九种特色军共用同一容量，受实际机构供养和陆军容量20%约束。'
    put('in_game/common/unit_families/hbe_civic_families.txt','hbe_civic_special_family = { limit = hbe_civic_special_limit }')
    units=[];unitdata=[]
    for k,name,g,base,bld,mods,gfx,late in UNITS:
        prerequisite=tech(g,2) if late else f'hbe_tech_{g}_2';additional=''
        if k=='hbe_salt_guard':additional='var:hbe_yiqi >= 20'
        if k in ('hbe_valley_soldiers','hbe_granary_militia'):additional+=' has_variable = hbe_garrison_compact'
        earlydeny='NOT = { has_advance = '+tech(g,2)+' }' if g in ('eastern_river','northern_shudao') and not late else ''
        upkeep='cavalry_maintenance' if base=='light_cavalry' else 'early_infantry_maintenance'
        construction='cavalry_construction' if base=='light_cavalry' else 'early_infantry_construction'
        nativeage=2 if late else 1;agename='renaissance' if late else 'traditions'
        alternates=[bld]
        if g in ('southern_salt_wine','eastern_river','central_hills'):alternates=[b[0] for b in BUILDINGS if b[2]==g]
        local_building='OR = { '+ ' '.join('has_building_with_at_least_one_level = '+b for b in alternates)+' }'
        local_jobs='any_buildings_in_location = { OR = { '+ ' '.join('building_type = building_type:'+b for b in alternates)+' } building_employed_amount >= 0.05 }'
        extra=''
        if k=='hbe_river_garrison':extra='upgrades_to = hbe_trained_river'
        if k=='hbe_pass_rotation':extra='upgrades_to = hbe_permanent_pass'
        loc[k]=name;loc[k+'_desc']=f'{name}从本地经营和议约中获得可靠人手，沿用本地区的训练办法。它的优势建立在固定职责之上，也保留相应弱点。\n\n'+('1457年后，以续约课题和百年验收解锁；替代原有兵种。' if late else '1352年后开放，须完成本圈第二项课题并维持招募机构；由原版招募系统提供兵员和物资。')+'\n所有议约军共用一个容量，役负过高暂停新募。'
        units.append(f'''{k} = {{
 copy_from = a_age_{nativeage}_{agename}_{base}
 hide = no buildable = yes levy = no is_special = yes family = hbe_civic_special_family
 max_strength = 0.5 {extra} {mods}
 construction_demand = {construction} maintenance_demand = {upkeep}
 country_potential = {{ {allid} {licensed(g)} }}
 location_potential = {{ is_in_scripted_geography = scripted_geography:hbe_geo_{g} }}
 location_trigger = {{ {local_building} {local_jobs}
 owner = {{ {MEMBER} current_year >= {1457 if late else 1352} {regional_active(g)} var:hbe_burden < 70 {additional} {earlydeny}
 OR = {{ has_advance = {prerequisite} AND = {{ has_variable = hbe_guest_{g} has_advance = {tech('common',2)} }} }}
 {('has_variable = hbe_mission_'+g+'_5') if late else ''} }} }}
 gfx_tags = {{ {gfx} }}
}}''')
        unlocks[prerequisite].append('unlock_unit = '+k)
        unitdata.append(dict(key=k,name=name,group=g,advance=prerequisite,building=bld,alternate_buildings=alternates,year=1457 if late else 1352,late=late,shared_family='hbe_civic_special_family'))
    put('in_game/common/unit_types/hbe_civic_units.txt','\n'.join(units))

    # Native law: policy callbacks own the lock, UI and variable never select separately.
    policies=[]
    for i,(key,name,mod,estate) in enumerate([
      ('hbe_levy_policy','府额征办','peasants_estate_target_satisfaction = -0.03','nobles_estate'),
      ('hbe_communal_policy','乡社议办','peasants_estate_target_satisfaction = 0.03','peasants_estate'),
      ('hbe_paid_policy','行会雇办','burghers_estate_target_satisfaction = 0.03','burghers_estate')],1):
        loc[key]=name;loc[key+'_desc']=[
         '按府额征集地方事业人手。每次地方事业结算役负+6；获得有限期工程便利，连续催办将引起请愿。',
         '由乡社见证分摊与期限。事业结算役负+2、义气额外+1；开工须有本圈储备至少5，驻防粮额沿用议约。',
         '从府库付费采购人手。事业开工须另付雇办费（0.75个月税贸收入，至少3金）；结算役负不增加，拖欠将暂停新办。'][i-1]
        policies.append(f'''{key} = {{
 potential = {{ {MEMBER} {allid} has_advance = {tech('common',1)} }}
 country_modifier = {{ {mod} }} estate_preferences = {{ {estate} }}
 on_activate = {{ set_variable = {{ name = hbe_policy_lock value = yes years = 5 }} }}
}}''')
    loc['hbe_civil_service_law']='民役议约';loc['hbe_civil_service_law_desc']='全国择一民役政策，选择后五年不得改换。地方事业、请愿与驻防均依本约办理。'
    put('in_game/common/laws/hbe_civic_law.txt',f'''hbe_civil_service_law = {{ type = country unique = yes law_category = administrative
 potential = {{ {MEMBER} {allid} has_advance = {tech('common',1)} }}
 allow = {{ always = yes }} locked = {{ has_variable = hbe_policy_lock }}
 {' '.join(policies)} }}''')
    unlocks[tech('common',1)]+=['unlock_law = hbe_civil_service_law']+['unlock_policy = '+p for p in ('hbe_levy_policy','hbe_communal_policy','hbe_paid_policy')]
    privileges=[]
    for k,name,estate,mods,extra in [
      ('hbe_village_witnesses','乡社见证权','peasants_estate','peasants_estate_target_satisfaction = 0.04 global_peasants_estate_power = 0.05','has_policy = hbe_communal_policy'),
      ('hbe_guild_payment_guarantee','行会雇价保任','burghers_estate','burghers_estate_target_satisfaction = 0.04 global_burghers_estate_power = 0.05','has_policy = hbe_paid_policy')]:
        loc[k]=name;loc[k+'_desc']='认可承担者的见证与议价权，使地方事业有可追究的签押。满意度提高，也使该阶层保有更多政治影响。撤销前必须降低乡里压力，并终止尚未结算的地方事业。'
        privileges.append(f'{k} = {{ estate = {estate} potential = {{ {MEMBER} {allid} has_advance = {tech("common",1)} }} allow = {{ {extra} }} can_revoke = {{ var:hbe_burden < 40 NOT = {{ has_variable = hbe_service_cooldown }} }} country_modifier = {{ {mods} }} }}')
    put('in_game/common/estate_privileges/hbe_civic_privileges.txt','\n'.join(privileges))

    # Additional research: visible connections are not mutually-exclusive A+B requirements.
    advances=[];advancedata=[]
    for g,one,two in TECHS:
        for i,name in enumerate((one,two),1):
            k=tech(g,i);year=(1352 if i==1 else 1437) if g=='common' else (1397 if i==1 else 1457)
            logical_parent=f'hbe_tech_common_{1 if i==1 else 3}' if g=='common' else f'hbe_tech_{g}_2' if i==1 else tech(g,1)
            parent=logical_parent if year<1437 else 'renaissance_development' if g=='common' else tech('common',2)
            gate='' if g=='common' else f'has_variable = hbe_mission_{g}_{2 if i==1 else 5} OR = {{ has_advance = hbe_tech_{g}_{4 if i==1 else 5} has_advance = hbe_tech_{g}_{7 if i==1 else 8} }}'
            if year>=1437:gate+=' has_advance = '+logical_parent
            desc=('使乡社、行会与府库分别认下办理地方事业的责任，避免在工成之后才向乡里追征。' if g=='common' and i==1 else '前人的签押留下了权利与责任；后来的主持者应能核对凭据，延续其仍然有效的承诺。')
            unlock=('解锁三种民役政策、两项阶层特权、府议与驻防粮额；役负影响事业与招募。' if i==1 else '解锁公账审计、客籍议约与1457年的修约议事。') if g=='common' else ('解锁'+OFFICES[list(R).index(g)]+'五年委任与本圈协调事务。' if i==1 else '解锁本圈续约协调与传习减役；川东、蜀道另解锁升级兵种。')
            loc[k]=name;loc[k+'_desc']=desc+'\n\n'+unlock;loc[k+'_effects']=unlock
            advances.append(f'''{k} = {{ age = {'age_1_traditions' if year<1437 else 'age_2_renaissance'} starting_technology_level = 99
 icon = {k} content_priority = 880
 potential = {{ hbe_research_origin_{g} = yes }}
 allow = {{ {MEMBER} current_year >= {year} {gate} }}
 requires = {parent} pure_tooltip_entry = {k}_effects {' '.join(unlocks[k])} }}''')
            advancedata.append(dict(key=k,name=name,group=g,year=year,parent=parent,logical_parent=logical_parent,allow=gate,unlocks=unlocks[k]))
    put('in_game/common/advances/hbe_civic_advances.txt','\n'.join(advances))
    oldpath=out/'in_game/common/advances/hbe_advances.txt';s=oldpath.read_text(encoding='utf-8-sig');edits=[]
    for k,_,a,b,_ in blocks(s,0):
        if unlocks[k]:edits.append((b,b,'\n    '+'\n    '.join(unlocks[k])+'\n'))
        if unlocks[k]:loc[k+'_effects']+=' 新增机构／军制：'+ '、'.join(loc.get(v.split(' = ')[1],v) for v in unlocks[k])+'。'
    put(oldpath.relative_to(out).as_posix(),apply_edits(s,edits))

    effects.append('''hbe_clamp_burden = { if = { limit = { var:hbe_burden < 0 } set_variable = { name = hbe_burden value = 0 } } if = { limit = { var:hbe_burden > 100 } set_variable = { name = hbe_burden value = 100 } } }
hbe_civic_initialize = {
 if = { limit = { NOT = { has_variable = hbe_civic_initialized } }
 set_variable = hbe_civic_initialized set_variable = { name = hbe_burden value = 20 }
 set_variable = { name = hbe_office_count value = 0 }
 set_variable = { name = hbe_special_record value = hbe_civic_special_count }
 trigger_event_non_silently = { id = hbe_civic.1 days = 30 } }
}
''')
    loc['hbe_burden']='役负';loc['hbe_labor_policy']='民役议约';loc['hbe_office_count']='有效委任数'
    event(1,CIVIC_INTRO['title'],CIVIC_INTRO['body'],[(CIVIC_INTRO['button'],'', '',100)],scene='civic_council')
    ledgerbody='府议簿不只记录完成了什么，也记载由谁承办、由谁付费，以及未能随一次交付清除的负担。历任主持者应在旧约旁留下新签押，使乡里不必在每次换任后重新证明自己的责任。\n\n'+f"#T 本府公账#!\n@hbe_burden! [Concept('hbe_term_burden','役负')|e]：{dv('hbe_burden')} / 100。民役政策：{dv('hbe_labor_policy')}（0未立、1征办、2议办、3雇办）。\n有效圈署委任：{dv('hbe_office_count')} / 2。特色军现额：{dv('hbe_special_record')}。\n"+'\n'.join(OFFICES[i]+'：'+dv('hbe_office_'+r[0])+'（1在任、0未任）' for i,r in enumerate(regions))+'\n原版招募列表显示当前有效军额；役负70以上暂停新募。'
    event(2,'本府民役与委任簿',ledgerbody,[('合上簿册。','', '',100)],scene='civic_council')
    decision('hbe_civic_ledger','查看民役与委任簿',ledgerbody,'always = yes','trigger_event_non_silently = { id = hbe_civic.2 }',art='hbe_civil_ledger')
    decision('hbe_civic_council','召开本府府议','各乡与承办者已将旧约带到公所。府库愿先核对尚未解决的分摊，再决定下一轮事业的办理方式。\n\n每五年召开一次，依本圈选择出资、储备分摊或追加征办；拥有维护中的府议公所可降低事后负担，小国亦可借官署办理。',f'has_advance = {tech("common",1)} NOT = {{ has_variable = hbe_council_cooldown }}','set_variable = { name = hbe_council_cooldown value = yes years = 5 } hbe_open_local_council = yes',art='hbe_council',ai=12)
    decision('hbe_civic_relief','议定减役与补偿','征令送到乡里时，耕作与供养不会因此停止。我们应以府库承担部分支出，让先前因急征留下的责任逐步减轻。\n\n支付0.5个月税贸收入（至少2金），役负降低10；三年内不得再次办理。',f'has_advance = {tech("common",1)} var:hbe_burden >= 10 NOT = {{ has_variable = hbe_relief_cooldown }} gold >= hbe_public_bill',pay()+' '+burden(-10)+' set_variable = { name = hbe_relief_cooldown value = yes years = 3 }',art='hbe_burden',ai=10)
    decision('hbe_civic_garrison','签认驻防粮额','士卒须有固定粮额，驻地也须知道本府愿驻守多久。乡社见证人提出，把供给、轮替与查验写在同一纸约上，免使临时援守化作无期旧役。\n\n支付0.5个月税贸收入（至少2金），五年取得议约驻防资格，允许义仓团练与联寨山卒招募；到期需续办。',f'has_advance = {tech("common",1)} NOT = {{ has_variable = hbe_garrison_compact }} gold >= hbe_public_bill',pay()+' set_variable = { name = hbe_garrison_compact value = yes years = 5 } '+burden(2),art='hbe_guest_compact',ai=8)
    issues=[];open_council=[];monthly=[];yearly=[]
    for j,r in enumerate(regions):
        g,region,_,label,counter,*_=r;bld=next(b[0] for b in BUILDINGS if b[2]==g);home=f'has_variable = hbe_home_{g}'
        k='hbe_fuyi_'+g;loc[k]=['渠工分水','盐引担保','江岸通行','关驿轮役','义仓赈借','商队互保','乡寨驻防'][j];loc[k+'_desc']='将本圈的分摊与维护提交原版议会；通过后进入地方府议事件，沿用五年议事间隔。'
        issues.append(f'''{k} = {{ estate = {'burghers_estate' if j in (1,2,5) else 'peasants_estate'}
 allow = {{ {MEMBER} {identity(g)} has_advance = {tech('common',1)} NOT = {{ has_variable = hbe_council_cooldown }} }}
 modifier_when_in_debate = {{ peasants_estate_target_satisfaction = 0.01 }}
 on_debate_passed = {{ set_variable = {{ name = hbe_council_cooldown value = yes years = 5 }} trigger_event_non_silently = {{ id = hbe_civic.{100+j*2} }} }}
 on_debate_failed = {{ {burden(3)} }} chance = 20 }}''')
        open_council.append(f'if = {{ limit = {{ {home} }} trigger_event_non_silently = {{ id = hbe_civic.{100+j*2} }} }}')
        for n in range(2):
            title,body,a,b,c=INCIDENTS[j*2+n];eid=100+j*2+n
            shared=f'set_variable = {{ name = hbe_civic_council_done value = yes years = 5 }} change_variable = {{ name = {counter} subtract = 8 }} {burden(-4)} {yiqi(1)}'
            paid=f'{pay()} {burden(-5)} {yiqi(1)} set_variable = {{ name = hbe_civic_council_done value = yes years = 5 }}'
            force=f'{burden(8)} {yiqi(-3)} every_owned_location = {{ limit = {{ is_in_scripted_geography = scripted_geography:hbe_geo_{g} }} add_location_modifier = {{ modifier = hbe_civic_fast_work years = 2 mode = replace }} }}'
            event(eid,title,body+'\n\n这项责任须由本府明确承担；现钱、地方储备与乡里急征各有代价，处置将记入役负和本府信用。',[(a,paid,'gold >= hbe_public_bill',55),(b,shared,f'var:{counter} >= 8',35),(c,force,'',10)],scene=['water','civic_market','salt','civic_market','river','civic_training','roads','roads','grain','civic_council','tea','civic_market','valleys','civic_council'][j*2+n],immediate='set_variable = { name = hbe_civic_incident_cooldown value = yes years = 5 }')
        # Real delivery marker is added at settlement, never at commitment.
        effects.append(f'''hbe_record_service_{g} = {{
 set_variable = {{ name = hbe_recent_delivery_{g} value = yes years = 5 }}
 if = {{ limit = {{ has_policy = hbe_levy_policy }} {burden(6)}
 if = {{ limit = {{ NOT = {{ has_variable = hbe_work_burst_cooldown }} }} add_country_modifier = {{ modifier = hbe_civic_work_burst years = 2 mode = replace }} set_variable = {{ name = hbe_work_burst_cooldown value = yes years = 5 }} }} }}
 else_if = {{ limit = {{ has_policy = hbe_communal_policy }} {burden(2)} {yiqi(1)} }}
 else_if = {{ limit = {{ NOT = {{ has_policy = hbe_paid_policy }} }} {burden(4)} }}
}}''')
        effects.append(f'''hbe_pay_service_{g} = {{ if = {{ limit = {{ has_policy = hbe_paid_policy }} {pay('hbe_paid_bill')} }} }}''')
        vacant=f'international_organization:hbe_circle_{g} = {{ NOT = {{ has_variable = hbe_civic_holder }} }}'
        qualify=f'OR = {{ AND = {{ has_advance = {tech(g,1)} has_variable = hbe_mission_{g}_2 }} AND = {{ has_variable = hbe_guest_{g} has_advance = {tech("common",2)} }} }} {regional_active(g)} has_variable = hbe_recent_delivery_{g} var:hbe_burden < 70 var:hbe_office_count < 2'
        office=OFFICES[j];ok='hbe_office_'+g
        decision('hbe_seek_'+g,'请任'+office,region+'的公账载明近期交付，圈署尚缺能够主持维护的人。我们愿将本府已经承担的事业作为凭据，申请这一届委任。\n\n须完成成长验收、本圈委任科技，维持机构，最近五年真实交付；任期五年，每国至多两项委任。',qualify+' '+vacant,f'{ok}_appoint = yes',art='hbe_office_'+str(j),potential=licensed(g),ai=15)
        effects.append(f'''{ok}_appoint = {{ if = {{ limit = {{ {qualify} {vacant} }}
 set_variable = {{ name = {ok} value = 1 }} set_variable = {{ name = {ok}_term value = yes years = 5 }}
 change_variable = {{ name = hbe_office_count add = 1 }}
 international_organization:hbe_circle_{g} = {{ set_variable = {{ name = hbe_civic_holder value = prev }} }}
 trigger_event_non_silently = {{ id = hbe_civic.3 }} }} }}''')
        relinquish=f'set_variable = {{ name = {ok} value = 0 }} remove_variable = {ok}_term international_organization:hbe_circle_{g} ?= {{ if = {{ limit = {{ var:hbe_civic_holder = prev }} remove_variable = hbe_civic_holder }} }}'
        monthly.append(f'''international_organization:hbe_circle_{g} ?= {{
 if = {{ limit = {{ has_variable = hbe_civic_holder NOT = {{ exists = var:hbe_civic_holder }} }} remove_variable = hbe_civic_holder }}
 else_if = {{ limit = {{ exists = var:hbe_civic_holder }} if = {{ limit = {{ var:hbe_civic_holder = {{ OR = {{ num_locations = 0 NOT = {{ has_variable = {ok}_term }} }} }} }} remove_variable = hbe_civic_holder }} }} }}''')
        monthly.append(f'''if = {{ limit = {{ var:{ok} = 1 OR = {{ NOT = {{ has_variable = {ok}_term }} NOT = {{ {MEMBER} }} NOT = {{ {regional_active(g)} }} NOT = {{ international_organization:hbe_circle_{g} = {{ var:hbe_civic_holder = prev }} }} var:hbe_burden >= 70 }} }} {relinquish} trigger_event_non_silently = {{ id = hbe_civic.4 }} }}''')
        monthly.append(f'if = {{ limit = {{ var:{ok} = 1 }} change_variable = {{ name = hbe_office_count add = 1 }} }}')
        decision('hbe_coordinate_'+g,office+'：主持本圈协调',region+'的维护不能全由主持者决定，却可以由他先认下一份费用。我们愿将本届地方储备与会盟信用用于此事，公布分摊，留下后续可查的凭据。\n\n在任且机构正常时，出资办理一次本圈协调，降低役负、取得履约；三年间隔，续约科技可再减轻负担。',f'var:{ok} = 1 {regional_active(g)} NOT = {{ has_variable = {ok}_action_cooldown }} gold >= hbe_public_bill var:{counter} >= 5',pay()+f' change_variable = {{ name = {counter} subtract = 5 }} '+burden(-6)+' '+yiqi(2)+f' change_variable = {{ name = hbe_contribution add = 1 }} set_variable = {{ name = {ok}_action_cooldown value = yes years = 3 }} if = {{ limit = {{ has_advance = {tech(g,2)} }} {burden(-3)} }}',art='hbe_office_'+str(j),potential=licensed(g),ai=15)
        decision('hbe_guest_'+g,'订立'+region+'客籍议约','整合一处旧府州，并不等于掌握当地所有技艺。本府愿认可旧日见证，承担机构维护，并请当地承办者依原约保留本业。\n\n1437年后，公账审计、共同度量、乡社议办及义气60允许有限客籍资格；支付雇办费并消耗10义气。只开放本圈机构与基础军制，仍须实际建造和供养，不复制全圈科技。',f'has_advance = {tech("common",2)} has_advance = hbe_tech_common_2 has_policy = hbe_communal_policy var:hbe_yiqi >= 60 gold >= hbe_paid_bill any_owned_location = {{ is_in_scripted_geography = scripted_geography:hbe_geo_{g} }} NOT = {{ has_variable = hbe_guest_{g} }}',pay('hbe_paid_bill')+' '+yiqi(-10)+f' set_variable = hbe_guest_{g}',art='hbe_guest_compact',potential=identity(g, negate=True),ai=3)
        yearly.append(f'''if = {{ limit = {{ {home} current_year >= 1352 NOT = {{ has_variable = hbe_civic_incident_cooldown }} has_advance = {tech('common',1)} OR = {{ var:hbe_burden >= 40 var:{ok} = 1 }} }}
 if = {{ limit = {{ has_variable = hbe_civic_alternate }} remove_variable = hbe_civic_alternate trigger_event_non_silently = {{ id = hbe_civic.{100+j*2} }} }}
 else = {{ set_variable = hbe_civic_alternate trigger_event_non_silently = {{ id = hbe_civic.{101+j*2} }} }} }}''')
    put('in_game/common/parliament_issues/hbe_civic_issues.txt','\n'.join(issues))
    effects[0]=effects[0].replace('set_variable = hbe_civic_initialized', 'set_variable = hbe_civic_initialized '+ ' '.join('set_variable = { name = hbe_office_'+r[0]+' value = 0 }' for r in regions))
    effects.append('hbe_open_local_council = { '+' '.join(open_council)+' }')
    event(3,'圈署委任落印','公账中的交付已经得到查验，圈中同意由本府暂任一项维护之责。落印不是对旧役的免除，也不是将其他诸侯的储备划入本府；它要求我们先能交代自己的承诺，再主持共同议题。\n\n这届委任为期五年。若机构失去供养，或役负已经妨碍履约，委任便须提前交还；每个国家至多同时承担两项。',[('按簿履任，待期复核。','', '',100)],scene='civic_council')
    event(4,'将印信交还圈中','这一届维护委任已经到期，或其所依靠的机构无法再承担责任。掌事者将印信和旧簿一并带到案房，使下一位主持者知道尚有哪些未清之约。\n\n过去交付的功绩仍然保存在会盟公账中，退任不会抹去其记录；本府若恢复机构供养，并完成新的地方事业，仍可争取下一届委任。',[('保存旧簿，明白交接。','', '',100)],scene='civic_council')
    event(5,'乡里呈上减役之请','征调的文书接连到来，乡里已经很难在田亩、修路与驻守之间安排人手。府臣仍能列出每道命令的理由，却无法解释为何它们合在一起，就应由同一批人无休止地承担。\n\n见证者请求重新议定期限。我们可以用现钱替代部分劳役，也可以暂缓急办；若继续维持旧额，本府的信用和阶层支持将一并受损。',[('出资补偿，并承诺复核。',pay('hbe_paid_bill')+' '+burden(-15),'gold >= hbe_paid_bill',65),('放缓办理，给乡里留下耕作时日。',burden(-10)+' add_country_modifier = { modifier = hbe_civic_slow_work years = 3 mode = replace }','',30),('仍依旧额，命各乡按期到场。',burden(5)+' '+yiqi(-5)+' add_estate_satisfaction = { type = estate_type:peasants_estate value = -0.05 }','',5)],scene='civic_council',immediate='set_variable = { name = hbe_petition_cooldown value = yes years = 5 }')
    event(6,'共役公账的复核','案房把近年的付费、雇价与轮役分别抄列。旧簿中的总数尚能相合，却有一些支出只记承办人，有些征调只记乡名，继任者难以查明同一份责任是否被记了两次。\n\n复核将花费府库和书记的人手，能使未清的分摊得到处理，也为1457年之后的续约留下可循的凭据。',[('出资复核，公布承担与交付。',pay()+' '+burden(-8)+' '+yiqi(3)+' set_variable = { name = hbe_audit_ready value = yes years = 10 }','gold >= hbe_public_bill',100),('将未清的部分暂存，日后再查。','', '',0)],scene='civic_council')
    decision('hbe_civic_audit','复核共役公账','旧账不应仅因更换主持者就成为无人认领的支出。我们请案房查明实际出资、供养与验收，留下一份各乡能够重新核对的册籍。\n\n完成公账审计课题，维护共役案房；五年一次，出资后役负-8、义气+3，取得十年修约凭据。',f'has_advance = {tech("common",2)} {active("hbe_works_archive")} NOT = {{ has_variable = hbe_civic_audit_cooldown }} gold >= hbe_public_bill','set_variable = { name = hbe_civic_audit_cooldown value = yes years = 5 } trigger_event_non_silently = { id = hbe_civic.6 }',art='hbe_audit',ai=8)
    event(7,'修约之后，仍须履约','百年章程早已确定了诸侯合作的方式，却没有使每一代人的负担自动相同。新的作坊、岸仓和驻守要用新的粮料，乡社和行会也应有机会指出旧额难以接续之处。\n\n今天的修约沿用已经承认的章程，不另造帝国代表席位。我们将依共建、兴业或契约安排，明确未来五年的维护与分摊。',[('按现行章程续订维护。',pay()+' '+burden(-8)+' '+yiqi(2)+' if = { limit = { situation:hbe_banquet = { var:hbe_charter = 1 } } international_organization:hbe_empire = { change_variable = { name = hbe_guoqi add = 2 } } } else_if = { limit = { situation:hbe_banquet = { var:hbe_charter = 2 } } '+burden(-2)+' } else = { '+yiqi(1)+' }','gold >= hbe_public_bill',100),('保留旧约，下一届再议。','', '',0)],scene='civic_council')
    decision('hbe_civic_revision','续订维护与驻守之约','旧章程之下的新责任仍须有人出资，也须得到实际承担者认可。我们愿依最近的公账复核，重新签认未来五年的维护，免使长期合作只剩下最初的名号。\n\n1457年后、已有百年章程与公账审计凭据可办理；三种章程均能续约，五年间隔，不改变三十六旧席。',f'current_year >= 1457 has_advance = {tech("common",2)} has_variable = hbe_audit_ready NOT = {{ has_variable = hbe_revision_cooldown }} situation:hbe_banquet = {{ var:hbe_charter > 0 }} gold >= hbe_public_bill','set_variable = { name = hbe_revision_cooldown value = yes years = 5 } trigger_event_non_silently = { id = hbe_civic.7 }',art='hbe_revision',ai=10)

    effects.append('''hbe_civic_monthly = {
 hbe_civic_initialize = yes
 set_variable = { name = hbe_office_count value = 0 }
 '''+'\n'.join(monthly)+'''
 if = { limit = { hbe_civic_special_count > var:hbe_special_record }
 set_variable = { name = hbe_new_special value = hbe_civic_special_count } change_variable = { name = hbe_new_special subtract = var:hbe_special_record }
 change_variable = { name = hbe_burden add = { value = var:hbe_new_special multiply = 2 } } hbe_clamp_burden = yes }
 set_variable = { name = hbe_special_record value = hbe_civic_special_count }
 if = { limit = { hbe_civic_special_count > hbe_civic_special_limit } add_country_modifier = { modifier = hbe_civic_over_supply months = 2 mode = replace } }
 else = { remove_country_modifier = hbe_civic_over_supply }
 if = { limit = { var:hbe_burden >= 70 } remove_country_modifier = hbe_civic_strained add_country_modifier = { modifier = hbe_civic_exhausted months = 2 mode = replace } }
 else_if = { limit = { var:hbe_burden >= 40 } remove_country_modifier = hbe_civic_exhausted add_country_modifier = { modifier = hbe_civic_strained months = 2 mode = replace } }
 else = { remove_country_modifier = hbe_civic_strained remove_country_modifier = hbe_civic_exhausted }
 if = { limit = { var:hbe_burden >= 70 NOT = { has_variable = hbe_petition_cooldown } } trigger_event_non_silently = { id = hbe_civic.5 } }
}''')
    recovery='NOT = { at_war = yes }'
    effects.append('hbe_civic_yearly = { if = { limit = { '+recovery+' } '+burden(-3)+' } '+' '.join(yearly)+' }')
    put('in_game/common/scripted_effects/hbe_civic_effects.txt','\n'.join(effects))
    put('in_game/common/scripted_triggers/hbe_civic_triggers.txt','\n'.join(triggers))
    put('in_game/common/on_action/hbe_civic_on_actions.txt',f'''on_game_start = {{ on_actions = {{ hbe_civic_start }} }}
hbe_civic_start = {{ effect = {{ every_country = {{ limit = {{ {allid} {MEMBER} }} hbe_civic_initialize = yes }} }} }}
monthly_country_pulse = {{ on_actions = {{ hbe_civic_pulse }} }}
hbe_civic_pulse = {{ trigger = {{ {allid} }} effect = {{ hbe_civic_monthly = yes }} }}
yearly_country_pulse = {{ on_actions = {{ hbe_civic_year }} }}
hbe_civic_year = {{ trigger = {{ {allid} {MEMBER} }} effect = {{ hbe_civic_yearly = yes }} }}''')
    put('in_game/events/hbe_civic_events.txt','namespace = hbe_civic\n'+'\n'.join(events))
    put('in_game/common/decisions/hbe_civic_decisions.txt','\n'.join(decisions))
    # Patch the old service start and settlement; leave its original rewards and timer.
    path=out/'in_game/common/decisions/hbe_decisions.txt';s=path.read_text(encoding='utf-8-sig');edits=[]
    for k,_,a,b,_ in blocks(s,0):
        if not k.startswith('hbe_service_'):continue
        g=k.removeprefix('hbe_service_');body=s[a:b]
        ab=next(v for v in blocks(body,0) if v[0]=='allow')
        gate=f' var:hbe_burden < 70 trigger_if = {{ limit = {{ has_policy = hbe_paid_policy }} gold >= {{ value = hbe_paid_bill add = 4 }} }} trigger_if = {{ limit = {{ has_policy = hbe_communal_policy }} has_variable = hbe_civic_council_done var:{R[g][4]} >= 5 }} '
        edits.append((a+ab[3],a+ab[3],gate))
        match=re.search(r'effect\s*=\s*\{',body);edits.append((a+match.end(),a+match.end(),f' hbe_pay_service_{g} = yes '))
        for suf in ('.desc','.desc.entry'):loc[k+suf]+='\n\n#T 民役与供养#!\n役负70以上暂停新办。府额征办结算+6役负；乡社议办结算+2并额外+1义气，开工储备须5并有五年内府议认约；行会雇办另付按税贸收入计的雇价，结算不加役负。'
    put(path.relative_to(out).as_posix(),apply_edits(s,edits))
    path=out/'in_game/common/scripted_effects/hbe_effects.txt';s=path.read_text(encoding='utf-8-sig')
    for r in regions:
        g=r[0];needle='remove_variable = hbe_service_'+g+'_pending'
        assert s.count(needle)==1,g;s=s.replace(needle,'hbe_record_service_'+g+' = yes '+needle)
    put(path.relative_to(out).as_posix(),s)
    path=out/'in_game/common/scripted_effects/hbe_banquet_effects.txt';s=path.read_text(encoding='utf-8-sig')
    # Track which circle actually undertook each new professional contract.
    rolespath=out/'in_game/common/decisions/hbe_banquet_decisions.txt'
    roles=rolespath.read_text(encoding='utf-8-sig');role_edits=[]
    for key,_,aa,bb,_ in blocks(roles,0):
        if key.startswith('hbe_role_'):
            g=key.removeprefix('hbe_role_');pos=re.search(r'effect\s*=\s*\{',roles[aa:bb]).end()
            role_edits.append((aa+pos,aa+pos,f' set_variable = {{ name = hbe_delivery_circle value = {list(R).index(g)+1} }} '))
    put(rolespath.relative_to(out).as_posix(),apply_edits(roles,role_edits))
    # One recent-delivery marker, not a credit for every circle merely owned.
    a=next(v for v in blocks(s,0) if v[0]=='hbe_deliver_contract')[2]
    hook='\n'+'\n'.join(f'if = {{ limit = {{ OR = {{ var:hbe_delivery_circle = {i+1} AND = {{ NOT = {{ has_variable = hbe_delivery_circle }} has_variable = hbe_home_{r[0]} }} }} }} set_variable = {{ name = hbe_recent_delivery_{r[0]} value = yes years = 5 }} }}' for i,r in enumerate(regions))+'\nremove_variable = hbe_delivery_circle\n'
    s=s[:a]+hook+s[a:]
    guard=next(v for v in blocks(s,0) if v[0]=='hbe_charter_maintenance')
    s=s[:guard[2]]+'\n if = { limit = { is_situation_active = situation:hbe_banquet }\n'+s[guard[2]:guard[3]]+'\n }\n'+s[guard[3]:]
    put(path.relative_to(out).as_posix(),s)
    # Only country and location modifier keys already present in the base game.
    mods={'hbe_civic_work_burst':('限期共役筹备','global_construction_speed = 0.05'),
      'hbe_civic_fast_work':('追加征办','local_construction_speed = 0.03'),
      'hbe_civic_slow_work':('减役缓办','global_construction_speed = -0.05'),
      'hbe_civic_strained':('乡里役负渐重','peasants_estate_target_satisfaction = -0.03'),
      'hbe_civic_exhausted':('乡里役负过重','peasants_estate_target_satisfaction = -0.08 global_construction_speed = -0.05'),
      'hbe_civic_over_supply':('议约军供养不足','army_maintenance_efficiency = -0.10')}
    for k,(name,_) in mods.items():loc['STATIC_MODIFIER_NAME_'+k]=name;loc[k]=name;loc[k+'_desc']=name+'持续期间按所列数值生效；重复维护只替换期限，不叠加。'
    put('main_menu/common/static_modifiers/hbe_civic_modifiers.txt','\n'.join(k+' = { '+v[1]+' }' for k,v in mods.items()))
    concepts={
      'hbe_term_burden':('役负','全国0—100的徭役和驻地压力，初始20。事业征办+6、议办+2、雇办不增加；议约军按月度净增结算，每队役负+2。和平且近年无急征时每年-3，付费减役可另降10。40起影响农民支持，70起暂停事业和新募，并触发有五年间隔的请愿。'),
      'hbe_term_civic_office':('圈署委任','须委任科技、成长验收、有效机构与最近五年真实交付。一个圈同时一位主持，每国至多两任，任期五年；断供、失去会盟或役负70以上提前退任。请任按空缺和明确资格办理，不增加皇帝选票或帝国旧席。'),
      'hbe_term_operating':('机构供养','本府拥有机构，有效建筑等级至少0.25，且有同类机构实际雇用至少50人。原版有效等级随供养变化；不满足则暂停相应招募和委任。原版建筑本身的效果亦依就业与商品获取缩放。'),
      'hbe_term_civic_army':('议约军额','九种军种共用一个原版unit family。以潜在陆军人数20%折算500人单位，并以有效地区机构总等级取较小值；能供养500人时至少容许一队，前提是机构容量达一队。役负70时容量归零，新募停止；现有部队不删除，超过容量时全军维护效率-10%。'),
      'hbe_term_civic_policy':('民役议约','原版民役法律内择一政策，选择后五年锁定。征办承受役负，议办保留地方见证，雇办付现钱。它与大开席的三种章程分别治理国内办理方式和跨府合作，不共用投票。')}
    for k,(name,text) in concepts.items():loc[k]=name;loc[k+'_desc']=text
    # Concepts join the existing native guide catalogue below.
    # Readable player catalogue and UI guide, kept alongside machine data.
    result=dict(buildings=buildingdata,units=unitdata,advances=advancedata,decisions=decisiondata,events=eventdata,policies=3,privileges=2,parliament_issues=7,shared_unit_family=True,office_limit=2,office_term_years=5,concepts=concepts)
    (root/'data/social_expansion_v020.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    export_art(out,root,result,put)
    guide=['# 0.2 府议与地方供养','', '已实装：3民役政策、役负、7圈五年委任、16机构、9军种、16新增课题、14循环地区题材。原有三十六旧席及对外隔离保留。','', '## 入口','', '国家科技树研究“府议与民役簿”（1352）；政府的民役议约选择政策。内容页办理府议、查看民役簿、减役、驻防粮额、委任、协调和后期审计。原版议会另有7个本圈议题。建筑在原版建造列表，兵种在原版招募列表；不是决议生成军队。','', '## 供养与长期节奏','',concepts['hbe_term_burden'][1], '',concepts['hbe_term_civic_office'][1], '',concepts['hbe_term_civic_army'][1],'', '1397开放圈署科技，1437开放审计，1457开放各圈续约课题及川东／蜀道升级军。任务A/B互斥路线均有资格。客籍议约只授有限机构与基础军种资格，不授他圈全树。','', '## 建筑与解锁','']
    guide+=['- '+b['name']+'：'+loc[b['advance']]+'；'+b['maintenance'] for b in buildingdata]
    guide+=['','## 特殊兵种','']+['- '+u['name']+'：'+str(u['year'])+'年，'+loc[u['advance']]+'，'+loc[u['building']] for u in unitdata]
    guide+=['','## 新课题','']+['- '+a['name']+'：'+str(a['year'])+'年；前置'+loc.get(a['parent'],a['parent']) for a in advancedata]
    guide+=['','## 美术','', 'imagegen生成独立精灵图；建筑128×128，课题256×256，单位插画按原版贴图比例输出并用原版unit_illustrations登记。3D建筑和兵员使用原版模型；并未制作新的3D模型。']
    (root/'docs/social_expansion_v020.md').write_text('\n'.join(guide)+'\n',encoding='utf-8')
    return result

def export_art(out,root,catalogue,put):
    """Mechanical extraction/export only; visual changes are made with imagegen."""
    registry=json.loads((root/'assets/social_art_generation.json').read_text(encoding='utf-8'));exports=[]
    sheets=[('buildings',[b['key'] for b in catalogue['buildings']],4,4,128,'main_menu/gfx/interface/icons/buildings'),
      ('advances',[a['key'] for a in catalogue['advances']],4,4,256,'main_menu/gfx/interface/advance'),
      ('units',[u['key'] for u in catalogue['units']],3,3,512,'main_menu/gfx/interface/illustrations/units'),
      ('politics',POLITICAL_ART,4,4,128,'main_menu/gfx/interface/icons/hbe_civic')]
    names={e['key']:e['name'] for kind in ('buildings','units','advances') for e in catalogue[kind]}
    proof=Image.new('RGB',(1600,4*240+60),'#2e2a23');draw=ImageDraw.Draw(proof);font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',17)
    illustration=[]
    for kind,keys,cols,rows,size,target in sheets:
        atlas=Image.open(root/registry[kind]['source']).convert('RGBA');assert atlas.getchannel('A').getextrema()[0]==0,kind
        for i,k in enumerate(keys):
            box=(round(i%cols*atlas.width/cols),round(i//cols*atlas.height/rows),round((i%cols+1)*atlas.width/cols),round((i//cols+1)*atlas.height/rows))
            sprite=fit(atlas.crop(box),size)
            if kind=='units':
                from PIL import ImageOps
                from apply_local_ui_patch import framed_portrait, source_cell
                sprite=framed_portrait(source_cell(atlas,i))
                # Unit icons keep the whole authored cell: the framed banner crop is
                # zoomed for 1080x440 and loses the surrounding camp at 128 px.
                cell=atlas.crop(box);bounds=cell.getchannel('A').point(lambda x:255 if x>16 else 0).getbbox()
                icon_sprite=ImageOps.fit(cell.crop(bounds),(1080,440),Image.Resampling.LANCZOS)
            png=root/'assets/civic_icons'/f'{k}.png';png.parent.mkdir(parents=True,exist_ok=True);sprite.save(png)
            p=out/target/f'{k}.dds';save_dds(p,sprite);exports.append(dict(key=k,kind=kind,path=p.relative_to(out).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),source=registry[kind]['source'],cell=i,dimensions=list(sprite.size)))
            if kind=='buildings':
                x=(i%8)*200;y=i//8*240;proof.paste(sprite,(x+36,y+30),sprite);draw.text((x+12,y+174),names[k],font=font,fill='#ead59b')
            if kind=='advances':
                x=(i%8)*200;y=480+i//8*240;thumb=sprite.resize((128,128));proof.paste(thumb,(x+36,y+30),thumb);draw.text((x+6,y+174),names[k],font=font,fill='#ead59b')
            if kind=='politics':
                card=Image.new('RGBA',(1080,440));large=sprite.resize((320,320),Image.Resampling.LANCZOS);card.alpha_composite(large,(380,60));save_dds(out/'main_menu/gfx/interface/hbe/civic/decisions'/f'{k}.dds',card)
                save_dds(out/'main_menu/gfx/interface/icons/policies'/f'{k}.dds',sprite)
                if k=='hbe_council':
                    save_dds(out/'main_menu/gfx/interface/icons/laws/hbe_civil_service_law.dds',sprite)
                if k in ('hbe_communal_policy','hbe_paid_policy'):
                    save_dds(out/'main_menu/gfx/interface/icons/privileges'/('hbe_village_witnesses.dds' if k=='hbe_communal_policy' else 'hbe_guild_payment_guarantee.dds'),sprite)
                if k=='hbe_burden':
                    save_dds(out/'main_menu/gfx/interface/icons/text_icons/hbe_burden.dds',sprite)
                    put('main_menu/gui/shared/hbe_civic_font_icons.gui','texticon = { icon = hbe_burden iconsize = { texture = "gfx/interface/icons/text_icons/hbe_burden.dds" size = { 24 24 } offset = { 0 4 } fontsize = 16 } }')
            if kind=='units':
                # Unit selection is explicit, not guessed from the illustration filename.
                illustration.append(f'{k}_illustration = {{ texture = "gfx/interface/illustrations/units/{k}.dds" priority = 950000 trigger = {{ is_unit_type = {k} }} }}')
                save_dds(out/'main_menu/gfx/interface/illustrations/units/masks'/f'{k}.dds',Image.new('RGBA',(1080,440),(0,0,0,255)))
                save_dds(out/'main_menu/gfx/interface/icons/unit_types'/f'{k}.dds',fit(icon_sprite,128))
    put('in_game/gfx/unit_illustrations/hbe_civic_illustrations.txt','\n'.join(illustration))
    proof.save(root/'assets/civic_buildings_tech_preview.png')
    # Three new scene backgrounds reuse the original portrait, lighting and scene shell.
    from PIL import ImageOps
    sc=out/'in_game/gfx/scenes/hbe_event_scenes.txt';template=sc.read_text(encoding='utf-8-sig');defs=[];imgs=[];ills=[]
    b=next(v for v in blocks(template,0) if v[0]=='hbe_event_scene_council');shell=template[b[2]:b[3]]
    for name in ('civic_council','civic_training','civic_market'):
        im=ImageOps.fit(Image.open(root/registry[name]['source']).convert('RGBA'),(1080,440),Image.Resampling.LANCZOS);p=out/'main_menu/gfx/interface/hbe/events'/f'{name}.dds';save_dds(p,im)
        exports.append(dict(key=name,kind='scene',path=p.relative_to(out).as_posix(),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),dimensions=[1080,440]))
        defs.append('hbe_event_scene_'+name+' = {'+shell.replace('hbe_event_background_council','hbe_event_background_'+name)+'}')
        imgs.append(f'hbe_event_background_{name} = {{ tag = "hbe_event_background_{name}" illustration_image = {{ texture_file = "gfx/interface/hbe/events/{name}.dds" priority = 100 scope = country trigger = {{ always = yes }} }} }}')
        ills.append(f'hbe_event_illustration_{name} = {{ scene = "hbe_event_scene_{name}" tags = {{ 1000 = hbe_event_art_{name} }} }}')
    put('in_game/gfx/scenes/hbe_civic_scenes.txt','\n'.join(defs));put('in_game/gfx/images/hbe_civic_backgrounds.txt','\n'.join(imgs));put('loading_screen/gfx/illustrations/database/hbe_civic_illustrations.txt','\n'.join(ills))
    (root/'data/social_art_v020.json').write_text(json.dumps(dict(mode='built-in image_gen',source_manifest='assets/social_art_generation.json',exports=exports),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
