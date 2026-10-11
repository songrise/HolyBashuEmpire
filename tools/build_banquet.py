"""Generate the persistent native situation, linked projects and event catalogue."""
import json
from build_native_flags import build_flags

SIT='situation:hbe_banquet'
IO='international_organization:hbe_empire'
MEMBER=f'is_member_of_international_organization = {IO}'

def build_banquet(out,countries,regions,L,put,root,game):
    events=[];decisions=[];effects=[];event_catalog=[]
    flags=build_flags(out,countries,regions,root,put,game)
    def cv(name,n):
        return f'change_variable = {{ name = {name} {"add" if n>=0 else "subtract"} = {abs(n)} }}'
    def dispute(n): return f'{SIT} ?= {{ {cv("hbe_dispute",n)} hbe_banquet_clamp = yes }}'
    def pot(n): return f'{IO} ?= {{ {cv("hbe_guoqi",n)} hbe_clamp_guoqi = yes }}'
    def yiqi(n): return cv('hbe_yiqi',n)+' hbe_clamp_yiqi = yes'
    def event(eid,title,desc,options,trigger='',immediate='',category='shared'):
        key=f'hbe_banquet.{eid}'
        L(key+'.title',title);L(key+'.desc',desc)
        opts=[]
        for i,opt in enumerate(options):
            label,eff,*rest=opt;allow=rest[0] if rest else '';ai=rest[1] if len(rest)>1 else 100
            name=key+'.'+chr(97+i);L(name,label)
            opts.append(f'option = {{ name = {name} '+(f'trigger = {{ {allow} }} ' if allow else '')+f'ai_chance = {{ base = {ai} }} {eff} }}')
        events.append(f'''{key} = {{
    type = country_event title = {key}.title desc = {key}.desc outcome = neutral
    illustration_tags = {{ 10 = regular 10 = interior }}
    {'trigger = { '+MEMBER+' '+trigger+' }' if trigger else ''}
    {'immediate = { '+immediate+' }' if immediate else ''}
    {' '.join(opts)}
}}''')
        event_catalog.append(dict(id=key,title=title,category=category))
        return key
    def decision(key,title,desc,allow,eff,cost=0,ai=10,potential=''):
        L(key,title);L(key+'.desc',desc);L(key+'.a','执行')
        decisions.append(f'''{key} = {{
    decision_category = other_decisions image = "gfx/interface/hbe/placeholder.dds"
    potential = {{ {MEMBER} is_situation_active = {SIT} {potential} }}
    allow = {{ {allow} {'gold >= '+str(cost) if cost else ''} }}
    ai_will_do = {{ value = {ai} }}
    option = {{ name = {key}.a ai_chance = {{ value = 100 }} effect = {{ {'add_gold = -'+str(cost) if cost else ''} {eff} }} }}
}}''')

    # Every member, including subjects and electors, participates through native visibility.
    # No random roll: monthly_spawn_chance_unique is exactly 1 in the installed game.
    labels={'hbe_banquet':'巴蜀大开席','hbe_banquet_desc':'三十六家，一张账单。大元认可共同盐粮敕书，巴蜀诸侯必须学会分账、履约与共治。每三年举行分账会，跨圈事业与百年章程持续推进。',
        'HBE_DISPUTE_DISPLAY':'争席度：$VALUE|0$ / 100','HBE_CHAPTER_DISPLAY':'章程阶段：$VALUE|0$ / 5',
        'HBE_ROUND_DISPLAY':'分账会届次：$VALUE|0$','HBE_MONTH_DISPLAY':'本届月份：$VALUE|0$ / 36',
        'HBE_SUCCESSES_DISPLAY':'交付项目：$VALUE|0$','HBE_POT_DISPLAY':'锅气：$VALUE|0$ / 100',
        'hbe_stance_1':'共锅派','hbe_stance_2':'分锅派','hbe_stance_3':'账房派',
        'hbe_charter_1':'一锅巴蜀','hbe_charter_2':'万国茶会','hbe_charter_3':'各吃各的，账照样交',
        'hbe_banquet_map_tt':'本地诸侯参加巴蜀大开席；颜色显示共锅、分锅或账房立场。',
        'hbe_dispute':'争席度','hbe_round':'分账会届次','hbe_round_month':'本届月份','hbe_chapter':'章程阶段',
        'hbe_completed_projects':'已交付共同项目','hbe_stance':'茶会立场（1 共锅、2 分锅、3 账房）',
        'hbe_contribution':'个人履约记录','hbe_charter':'百年章程（0 未定、1 共锅、2 分锅、3 账房）',
        'hbe_project_kind':'公共项目（1 盐船共账、2 茶马过蜀道）',
        'hbe_role_1':'首项交付','hbe_role_2':'次项交付','hbe_role_3':'第三项交付',
        'hbe_pot_display':'帝国锅气','hbe_ballot_month':'章程议决计时','hbe_ballot_vote':'本国章程表决',
        'hbe_proposal':'待表决章程','hbe_ballot_circle_votes':'支持章程的帝国圈','hbe_ballot_seat_votes':'本圈府州赞成席位'}
    for k,v in labels.items():L(k,v)
    # Situation clamps also cover changes made by events/decisions outside on_monthly.
    effects.append('''hbe_clamp_guoqi = {
    if = { limit = { var:hbe_guoqi > 100 } set_variable = { name = hbe_guoqi value = 100 } }
    if = { limit = { var:hbe_guoqi < 0 } set_variable = { name = hbe_guoqi value = 0 } }
}
hbe_banquet_clamp = {
    if = { limit = { var:hbe_dispute > 100 } set_variable = { name = hbe_dispute value = 100 } }
    if = { limit = { var:hbe_dispute < 0 } set_variable = { name = hbe_dispute value = 0 } }
}
''')
    register=f'''hbe_banquet_register = {{
    if = {{ limit = {{ NOT = {{ has_variable = hbe_banquet_joined }} }}
        hbe_initialize = yes set_variable = hbe_banquet_joined
        set_variable = {{ name = hbe_stance value = 3 }}
        set_variable = {{ name = hbe_contribution value = 0 }}
        trigger_event_non_silently = {{ id = hbe_banquet.1 days = 1 }}
    }}
}}'''
    effects.append(register)
    for i in (1,2,3):
        effects.append(f'''hbe_choose_stance_{i} = {{
    set_variable = {{ name = hbe_stance value = {i} }}
    set_variable = {{ name = hbe_stance_cooldown value = yes years = 5 }}
}}''')
        decision(f'hbe_stance_change_{i}','转向'+labels[f'hbe_stance_{i}'],
                 '改变公共财政、地区自治和契约治理的立场；五年内不能再次改换。',
                 f'NOT = {{ var:hbe_stance = {i} }} NOT = {{ has_variable = hbe_stance_cooldown }}',f'hbe_choose_stance_{i} = yes',ai=0)
    event(1,'你这行省，怎么还选皇帝？',
        '大元使者前来查盐粮交割，却发现三十六家正在给第七位选侯挪椅子。使者答应按旧敕书维护巴蜀自治，但诸侯必须共同担保工程与交付。\n你已参加「巴蜀大开席」。分账会每三年召开，拒绝某项出资仍保有成员席位。选择一项政治立场；各派均可经营和竞选皇帝。',
        [('共锅派：公共事业，皇帝牵头。','hbe_choose_stance_1 = yes','',30),
         ('分锅派：各府自己管，圈里共同办。','hbe_choose_stance_2 = yes','',35),
         ('账房派：先看合同，再谈情义。','hbe_choose_stance_3 = yes','',35)],category='entry')

    # Native situation variables are the shared state; country variables hold personal contracts.
    base_vars=[('hbe_dispute','HBE_DISPUTE_DISPLAY',15,0,100),('hbe_chapter','HBE_CHAPTER_DISPLAY',1,1,5),
               ('hbe_round','HBE_ROUND_DISPLAY',1,1,9999),('hbe_round_month','HBE_MONTH_DISPLAY',0,0,36),
               ('hbe_completed_projects','HBE_SUCCESSES_DISPLAY',0,0,9999),('hbe_pot_display','HBE_POT_DISPLAY',40,0,100)]
    variables='\n'.join(f'{key} = {{ format = {fmt} change_format = VARIABLE_CHANGE_FORMAT start = {start} min = {lo} max = {hi} }}' for key,fmt,start,lo,hi in base_vars)
    situation=f'''hbe_banquet = {{
    international_organization_type = hbe_empire
    monthly_spawn_chance = monthly_spawn_chance_unique
    can_start = {{ game_is_initialized = yes current_date >= 1337.10.1 exists = {IO} }}
    can_end = {{ NOT = {{ exists = {IO} }} }}
    visible = {{ {MEMBER} }}
    variables = {{ {variables} }}
    on_start = {{
        set_variable = {{ name = hbe_project_kind value = 1 }}
        set_variable = {{ name = hbe_charter value = 0 }}
        {IO} = {{ every_international_organization_member = {{ hbe_banquet_register = yes }} }}
        hbe_open_accounts = yes
    }}
    on_monthly = {{ hbe_banquet_monthly = yes }}
    tooltip = {{ if = {{ limit = {{ owner ?= {{ {MEMBER} }} }} custom_tooltip = hbe_banquet_map_tt }} }}
    map_color = {{
        if = {{ limit = {{ owner ?= {{ {MEMBER} var:hbe_stance = 1 }} }} value = red }}
        else_if = {{ limit = {{ owner ?= {{ {MEMBER} var:hbe_stance = 2 }} }} value = blue }}
        else_if = {{ limit = {{ owner ?= {{ {MEMBER} }} }} value = yellow }}
        else = {{ value = define:NMapColors|DEFAULT_COLOR }}
    }}
    legend_key = {{ desc = hbe_stance_1 color = red require_color_on_map = yes }}
    legend_key = {{ desc = hbe_stance_2 color = blue require_color_on_map = yes }}
    legend_key = {{ desc = hbe_stance_3 color = yellow require_color_on_map = yes }}
}}'''
    put('in_game/common/situations/hbe_banquet.txt',situation)
    effects.append(f'''hbe_open_accounts = {{
    set_variable = {{ name = hbe_round_month value = 0 }}
    set_variable = {{ name = hbe_role_1 value = 0 }}
    set_variable = {{ name = hbe_role_2 value = 0 }}
    set_variable = {{ name = hbe_role_3 value = 0 }}
    {IO} ?= {{ every_international_organization_member = {{
        remove_variable = hbe_round_contributed remove_variable = hbe_round_delivered
        remove_variable = hbe_round_pledged remove_variable = hbe_project_pending
        remove_variable = hbe_project_timer remove_variable = hbe_fund_pledge
        remove_variable = hbe_declined_project
        trigger_event_non_silently = {{ id = hbe_banquet.2 days = 10 }}
    }} }}
}}''')
    # 6-month commitment window; funders cannot pretend to supply regional expertise.
    accept_window=f'{SIT} = {{ var:hbe_round_month < 6 }} NOT = {{ has_variable = hbe_round_contributed }} NOT = {{ has_variable = hbe_round_pledged }} NOT = {{ has_variable = hbe_declined_project }}'
    effects.append(f'''hbe_fund_project = {{
    add_gold = -3 set_variable = hbe_round_contributed set_variable = hbe_round_delivered
    {cv('hbe_contribution',1)} {yiqi(2)} {pot(1)}
}}''')
    effects.append('''hbe_pledge_project = {
    set_variable = hbe_round_pledged set_variable = hbe_fund_pledge
}''')
    decision('hbe_project_fund','分账会：出资三金','本届公共经费出资三金，取得个人履约一份。出资不替代地区专业交付；项目成功后才有共同收益。',accept_window+' gold >= 3','hbe_fund_project = yes',ai=10)
    decision('hbe_project_pledge','分账会：先认账，届中付款','先签四金承诺，第十二个月核账。届时国库不足会违约，争席度上升；不强制把国库扣成负数。',accept_window,'hbe_pledge_project = yes',ai=0)
    event(2,'三十六张椅子，第三十七张账单',
        '本届公共项目已经开账。盐船共账需要川南盐引、川东江运、川中核账；茶马过蜀道需要川西采购、川北驿路、山谷互市。\n前六个月可出资、认账或暂不参加。地区专业交付在决议中另行签约：支付二金与十点地区储备，半年后验收。本届第三十六个月统一结算。皇帝可以在前三个月改选工程。',
        [('这次出三金。','hbe_fund_project = yes','gold >= 3 '+accept_window,60),
         ('先认四金，届中兑付。','hbe_pledge_project = yes',accept_window,10),
         ('本届先保留意见。',f'if = {{ limit = {{ {accept_window} }} set_variable = hbe_declined_project }}','',15),
         ('留出额度，稍后签专业交付。','',accept_window+' gold >= 2 OR = { '+' '.join('has_variable = hbe_tech_'+r[0]+'_1' for r in regions)+' has_variable = hbe_tech_common_2 }',90)],category='accounts')
    # Reconsidering a declined project costs only the real contribution, no free benefit.
    decision('hbe_project_reconsider','分账会：撤回暂缓意见','在承诺期内重新参加，之后可以出资或签地区交付合同。',
             f'{SIT} = {{ var:hbe_round_month < 6 }} has_variable = hbe_declined_project','remove_variable = hbe_declined_project',ai=0)
    switch_window='var:hbe_round_month < 3 var:hbe_role_1 = 0 var:hbe_role_2 = 0 var:hbe_role_3 = 0 NOT = { any_country = { has_variable = hbe_project_pending } }'
    for kind,title in ((1,'盐船共账'),(2,'茶马过蜀道')):
        decision(f'hbe_project_select_{kind}','本届工程：'+title,
                 '皇帝在前三个月确定主工程，消耗三金。已有专业交付时不能改项；出资者和承诺保持有效。',
                 f'{SIT} = {{ {switch_window} NOT = {{ var:hbe_project_kind = {kind} }} }}',
                 f'{SIT} = {{ set_variable = {{ name = hbe_project_kind value = {kind} }} }}',cost=3,ai=0,
                 potential=f'is_leader_of_international_organization = {IO}')
    role_map={'southern_salt_wine':(1,1),'eastern_river':(1,2),'central_hills':(1,3),
              'western_tea_horse':(2,1),'northern_shudao':(2,2),'southwestern_valleys':(2,3)}
    role_titles={'chengdu_plain':'水粮担保','southern_salt_wine':'盐引承销','eastern_river':'江船转运','central_hills':'公账审计',
                 'western_tea_horse':'茶马采办','northern_shudao':'驿路轮戍','southwestern_valleys':'山谷互市'}
    for group,name,cap,label,counter,*_ in regions:
        # Research OR established local institutes: integrated historic seats remain useful.
        institution=f'OR = {{ has_variable = hbe_home_{group} any_owned_location = {{ is_in_scripted_geography = scripted_geography:hbe_geo_{group} }} }}'
        tech=f'OR = {{ has_variable = hbe_tech_{group}_1 AND = {{ has_variable = hbe_tech_common_2 any_owned_location = {{ is_in_scripted_geography = scripted_geography:hbe_geo_{group} }} }} }}'
        allow=f'{accept_window} {tech} OR = {{ var:{counter} >= 10 AND = {{ NOT = {{ has_variable = {counter} }} has_variable = hbe_tech_common_2 var:hbe_yiqi >= 10 }} }}'
        kind,role=role_map.get(group,(0,0))
        project_gate=f'{SIT} = {{ var:hbe_project_kind = {kind} }}' if kind else ''
        eff=f'''set_variable = hbe_round_contributed set_variable = hbe_project_pending
            set_variable = {{ name = hbe_project_timer value = yes months = 6 }}
            set_variable = {{ name = hbe_delivery_role value = {role} }}
            set_variable = {{ name = hbe_delivery_kind value = {kind} }}
            if = {{ limit = {{ has_variable = {counter} }} {cv(counter,-10)} }}
            else = {{ {yiqi(-10)} }}'''
        decision('hbe_role_'+group,'本届交付：'+role_titles[group],
                 f'{name}承担{role_titles[group]}，支付二金并消耗十点{label}，半年验收。同届只能参加一种交付或出资。研究地方第一项课题后开放；整合后的旧府州可由共同公账技术接办，没有本地储备时改用十点义气作担保。',
                 allow+' '+project_gate,eff,cost=2,ai=40,potential=institution)
    # Project completion is driven by the situation, not the number of country pulses.
    effects.append(f'''hbe_deliver_contract = {{
    remove_variable = hbe_project_pending remove_variable = hbe_project_timer
    set_variable = hbe_round_delivered {cv('hbe_contribution',2)} {yiqi(3)} add_prestige = 1
    {SIT} = {{
        if = {{ limit = {{ prev = {{ var:hbe_delivery_kind = 1 }} var:hbe_project_kind = 1 }}
            if = {{ limit = {{ prev = {{ var:hbe_delivery_role = 1 }} }} {cv('hbe_role_1',1)} }}
            else_if = {{ limit = {{ prev = {{ var:hbe_delivery_role = 2 }} }} {cv('hbe_role_2',1)} }}
            else = {{ {cv('hbe_role_3',1)} }}
        }}
        else_if = {{ limit = {{ prev = {{ var:hbe_delivery_kind = 2 }} var:hbe_project_kind = 2 }}
            if = {{ limit = {{ prev = {{ var:hbe_delivery_role = 1 }} }} {cv('hbe_role_1',1)} }}
            else_if = {{ limit = {{ prev = {{ var:hbe_delivery_role = 2 }} }} {cv('hbe_role_2',1)} }}
            else = {{ {cv('hbe_role_3',1)} }}
        }}
    }}
    if = {{ limit = {{ var:hbe_delivery_kind = 0 }} {pot(2)} {dispute(-1)} }}
    trigger_event_non_silently = {{ id = hbe_banquet.3 }}
}}''')
    event(3,'交付不是在纸上画个勾','盐货、驿路或公账的半年合同已经验收。专业交付已经记入本届项目，个人履约增加二份；水粮担保提高锅气。最终工程收益将在分账会结束时结算。',[('把货与签押一起收好。','')],category='delivery')
    event(4,'船到了，账也对上了','三个关键环节全部交付，本届公共项目结算成功。实际出资或交付的诸侯取得三年地方经营收益；未参加者保留自治与席位，下届再选。',[('这一届，总算没白忙。','')],category='delivery')
    event(5,'盐船没来，菜单先来了','本届项目缺少关键交付，或者争席度达到七十五，工程无法按期结清。锅气下降，争席度上升；履约诸侯保留个人记录，但没有成功工程收益。自治敕书仍然有效。',[('下届重开账，不撕敕书。','')],category='delivery')
    event(6,'签押还在，国库空了','你承诺的四金没有按期到账。本届履约取消，义气减少八，争席度增加五。未强行向国库追扣；下届可以以真实交付恢复信用。',[('欠的不是一张签名。','')],category='default')
    # Explicit subsidy pays for missing inputs after the commitment window, once per round.
    subsidy=f'''set_variable = hbe_subsidized_round
        {SIT} = {{
            if = {{ limit = {{ var:hbe_role_1 < 1 }} {cv('hbe_role_1',1)} }}
            else_if = {{ limit = {{ var:hbe_role_2 < 1 }} {cv('hbe_role_2',1)} }}
            else_if = {{ limit = {{ var:hbe_role_3 < 1 }} {cv('hbe_role_3',1)} }}
        }} {yiqi(2)}'''
    decision('hbe_project_subsidize','皇帝垫账：补一项缺口','支付十金聘请本地机构补交一个缺失环节。本届限一次；优先补第一项，再补第二、第三项。',
             f'{SIT} = {{ var:hbe_round_month >= 12 var:hbe_round_month < 30 OR = {{ var:hbe_role_1 < 1 var:hbe_role_2 < 1 var:hbe_role_3 < 1 }} }} NOT = {{ has_variable = hbe_subsidized_round }}',
             subsidy,cost=10,ai=20,potential=f'is_leader_of_international_organization = {IO}')
    decision('hbe_audit_accounts','公开公账：三金核账','支付三金，降低四点争席度并增加二点义气；两年可核账一次。',
             'NOT = { has_variable = hbe_audit_cooldown }',f'{dispute(-4)} {yiqi(2)} set_variable = {{ name = hbe_audit_cooldown value = yes years = 2 }}',cost=3,ai=10)
    decision('hbe_banquet_ledger','查看大开席账本','查看立场、本届交付、争席度、长期章程和个人履约。','always = yes','trigger_event_non_silently = { id = hbe_banquet.7 }',ai=0)
    status="""本国立场：[ROOT.GetVariable('hbe_stance').GetValue|0]（1 共锅、2 分锅、3 账房）。个人履约：[ROOT.GetVariable('hbe_contribution').GetValue|0]。
阶段：[GetSituationByKey('hbe_banquet').MakeScope.GetVariable('hbe_chapter').GetValue|0] / 5。争席度：[GetSituationByKey('hbe_banquet').MakeScope.GetVariable('hbe_dispute').GetValue|0] / 100。
届次：[GetSituationByKey('hbe_banquet').MakeScope.GetVariable('hbe_round').GetValue|0]；本届月份：[GetSituationByKey('hbe_banquet').MakeScope.GetVariable('hbe_round_month').GetValue|0] / 36。
主工程：[GetSituationByKey('hbe_banquet').MakeScope.GetVariable('hbe_project_kind').GetValue|0]（1 盐船共账、2 茶马过蜀道）。三项交付：[GetSituationByKey('hbe_banquet').MakeScope.GetVariable('hbe_role_1').GetValue|0] / [GetSituationByKey('hbe_banquet').MakeScope.GetVariable('hbe_role_2').GetValue|0] / [GetSituationByKey('hbe_banquet').MakeScope.GetVariable('hbe_role_3').GetValue|0]。
成功工程：[GetSituationByKey('hbe_banquet').MakeScope.GetVariable('hbe_completed_projects').GetValue|0]。章程：[GetSituationByKey('hbe_banquet').MakeScope.GetVariable('hbe_charter').GetValue|0]（0 未定、1 共锅、2 分锅、3 账房）。
百年章程至少在1437年、第五阶段与三十次成功工程后提案，由七圈授权表决。合并诸侯后，原府州首府仍构成固定代表席位。"""
    event(7,'席位、账目与锅底',status,[('账看完了，继续忙。','')],category='ledger')
    # Project settlement and chapter milestones retain a hundred-year calendar gate.
    effects.append(f'''hbe_settle_accounts = {{
    if = {{ limit = {{ var:hbe_role_1 >= 1 var:hbe_role_2 >= 1 var:hbe_role_3 >= 1 var:hbe_dispute < 75 }}
        {cv('hbe_completed_projects',1)} {cv('hbe_dispute',-5)} {pot(5)}
        {IO} ?= {{ every_international_organization_member = {{
            if = {{ limit = {{ has_variable = hbe_round_delivered }}
                every_owned_location = {{ limit = {{ is_in_scripted_geography = scripted_geography:hbe_domain }}
                    add_location_modifier = {{ modifier = hbe_banquet_success years = 3 mode = replace }} }}
                if = {{ limit = {{ {SIT} = {{ var:hbe_charter = 3 }} }} add_gold = 1 }}
                trigger_event_non_silently = {{ id = hbe_banquet.4 }}
            }}
        }} }}
    }}
    else = {{ {cv('hbe_dispute',8)} {pot(-4)}
        {IO} ?= {{ every_international_organization_member = {{ trigger_event_non_silently = {{ id = hbe_banquet.5 }} }} }}
    }}
    hbe_banquet_clamp = yes hbe_advance_chapter = yes
    {cv('hbe_round',1)}
    if = {{ limit = {{ var:hbe_project_kind = 1 }} set_variable = {{ name = hbe_project_kind value = 2 }} }}
    else = {{ set_variable = {{ name = hbe_project_kind value = 1 }} }}
    {IO} ?= {{ every_international_organization_member = {{ remove_variable = hbe_subsidized_round }} }}
    hbe_open_accounts = yes
}}''')
    chapter_effect=[]
    for chapter,year,completed,title,description in [
        (2,1352,3,'账单送到谁家','第一代合作已经验收，分账方式成为政治议题。公账、盐引与跨圈的技术路线开始影响履约。'),
        (3,1372,8,'祖宗坐过这个位置','旧约经历一代人。合并的旧府州仍通过原首府拥有固定代表席；释放小国不会平白增加票数。'),
        (4,1397,14,'换皇帝，还是换锅底','共同项目与旧债积累多年。中央财政、圈级自治和契约治理开始争夺下一代章程。'),
        (5,1422,22,'百年了，重新排座次','进入百年重审阶段；1437年以后且成功项目至少三十次，皇帝可以提请七圈授权。1457年以后分账与地方事件继续。')]:
        eid=10+chapter
        event(eid,title,description,[('旧约重认，事业续办。','')],category='chapter')
        chapter_effect.append(f'''if = {{ limit = {{ current_year >= {year} var:hbe_completed_projects >= {completed} var:hbe_chapter = {chapter-1} }}
            set_variable = {{ name = hbe_chapter value = {chapter} }}
            {IO} ?= {{ every_international_organization_member = {{ trigger_event_non_silently = {{ id = hbe_banquet.{eid} }} }} }}
        }}''')
    effects.append('hbe_advance_chapter = {\n'+'\n'.join(chapter_effect)+'\n}')
    # Three charters use fixed province seats and strict majorities in >=4 of 7 circles.
    ballot_start=f'''{SIT} = {{ set_variable = {{ name = hbe_ballot_month value = 0 }} set_variable = hbe_ballot_active }}
        {IO} = {{ every_international_organization_member = {{
            set_variable = {{ name = hbe_ballot_vote value = 0 }} trigger_event_non_silently = {{ id = hbe_banquet.20 days = 1 }}
        }} }}'''
    for i in (1,2,3):
        allow=f'current_year >= 1437 {SIT} = {{ var:hbe_chapter = 5 var:hbe_completed_projects >= 30 var:hbe_charter = 0 NOT = {{ has_variable = hbe_ballot_active }} NOT = {{ has_variable = hbe_ballot_cooldown }} }} {IO} = {{ var:hbe_guoqi >= 20 }}'
        decision(f'hbe_propose_charter_{i}','百年章程：'+labels[f'hbe_charter_{i}'],
                 '皇帝出五金、消耗二十锅气，开启六个月授权表决。每圈须有超过半数原府州席位赞成，七圈至少四圈支持。原三十六首府的当前帝国成员领主行使席位，释放小国不增加席位。失败后五年才能重提。',
                 allow+f' var:hbe_stance = {i}',f'{pot(-20)} {SIT} = {{ set_variable = {{ name = hbe_proposal value = {i} }} }} {ballot_start}',cost=5,ai=3,
                 potential=f'is_leader_of_international_organization = {IO}')
        decision(f'hbe_ballot_vote_{i}','章程授权：支持'+labels[f'hbe_charter_{i}'],
                 '明确支持这一份章程，替代本国上次表态；六个月议决期间可调整。本国拥有多个原首府时一并行使这些固定席位。',
                 f'{SIT} = {{ has_variable = hbe_ballot_active }}',f'set_variable = {{ name = hbe_ballot_vote value = {i} }}',ai=0)
    event(20,'皇帝递来一张百年合同','皇帝已提请百年章程授权。各圈以原府州首府为固定席位：本圈超过半数赞成才能授权，七圈至少四圈通过。\n你可以批准当前提案，或要求保持现约；六个月内也可在决议中改变表态。',
          [('同意本次提案。',f'set_variable = {{ name = hbe_ballot_vote value = {SIT}.var:hbe_proposal }}','',60),
           ('现约先留着，提案再改改。','set_variable = { name = hbe_ballot_vote value = 0 }','',40)],category='charter')
    # AI aligns support with its faction; weights use native trigger modifiers.
    events[-1]=events[-1].replace('ai_chance = { base = 60 }',f'ai_chance = {{ base = 20 modifier = {{ factor = 5 var:hbe_stance = {SIT}.var:hbe_proposal }} }}')
    effects.append(f'''hbe_tally_charter = {{
    set_variable = {{ name = hbe_ballot_circle_votes value = 0 }}
    '''+'\n'.join(f'''set_variable = {{ name = hbe_ballot_seat_votes value = 0 }}
    '''+'\n'.join(f'''location:{c['capital']}.owner ?= {{
        if = {{ limit = {{ {MEMBER} var:hbe_ballot_vote = {SIT}.var:hbe_proposal }}
            {SIT} = {{ {cv('hbe_ballot_seat_votes',1)} }}
        }}
    }}''' for c in countries if c['region']==r[0])+f'''
    if = {{ limit = {{ var:hbe_ballot_seat_votes > {sum(c['region']==r[0] for c in countries)/2:g} }} {cv('hbe_ballot_circle_votes',1)} }}'''
        for r in regions)+f'''
    if = {{ limit = {{ var:hbe_ballot_circle_votes >= 4 }}
        set_variable = {{ name = hbe_charter value = var:hbe_proposal }}
        {cv('hbe_dispute',-10)}
        {IO} = {{ every_international_organization_member = {{ hbe_apply_charter = yes trigger_event_non_silently = {{ id = hbe_banquet.21 }} }} }}
    }}
    else = {{ {cv('hbe_dispute',5)}
        {IO} = {{ every_international_organization_member = {{ trigger_event_non_silently = {{ id = hbe_banquet.22 }} }} }}
    }}
    remove_variable = hbe_ballot_active set_variable = {{ name = hbe_ballot_cooldown value = yes years = 5 }}
    hbe_banquet_clamp = yes
}}''')
    event(21,'这次盖章，真有七圈的印','至少四圈正式授权，百年章程生效。共锅章程提高本地建造速度，皇帝每年承担一金维护；分锅章程提高粮食产出，地区事业交付追加声望；契约章程各项提高少量，成功出资者取得合同返还。分账会和区域机构继续运行。',[('锅底换了，账还要记。','')],category='charter')
    event(22,'七圈的印，少了几枚','本次章程没有取得至少四圈授权。旧章继续，争席度增加五，五年后可重提；已完成的地区项目和个人履约保留。',[('皇帝可以提案，不能替圈盖章。','')],category='charter')
    effects.append(f'''hbe_apply_charter = {{
    every_owned_location = {{
        limit = {{ is_in_scripted_geography = scripted_geography:hbe_domain }}
        remove_location_modifier = hbe_charter_build remove_location_modifier = hbe_charter_food remove_location_modifier = hbe_charter_contract
        if = {{ limit = {{ {SIT} = {{ var:hbe_charter = 1 }} }} add_location_modifier = {{ modifier = hbe_charter_build years = -1 }} }}
        else_if = {{ limit = {{ {SIT} = {{ var:hbe_charter = 2 }} }} add_location_modifier = {{ modifier = hbe_charter_food years = -1 }} }}
        else_if = {{ limit = {{ {SIT} = {{ var:hbe_charter = 3 }} }} add_location_modifier = {{ modifier = hbe_charter_contract years = -1 }} }}
    }}
}}''')
    # Maintenance of new location owners is idempotent and removes benefits outside the IO.
    effects.append(f'''hbe_charter_maintenance = {{
    every_owned_location = {{
        limit = {{ is_in_scripted_geography = scripted_geography:hbe_domain }}
        if = {{ limit = {{ owner = {{ {MEMBER} }} {SIT} ?= {{ var:hbe_charter = 1 }} NOT = {{ has_location_modifier = hbe_charter_build }} }}
            add_location_modifier = {{ modifier = hbe_charter_build years = -1 }} }}
        else_if = {{ limit = {{ owner = {{ {MEMBER} }} {SIT} ?= {{ var:hbe_charter = 2 }} NOT = {{ has_location_modifier = hbe_charter_food }} }}
            add_location_modifier = {{ modifier = hbe_charter_food years = -1 }} }}
        else_if = {{ limit = {{ owner = {{ {MEMBER} }} {SIT} ?= {{ var:hbe_charter = 3 }} NOT = {{ has_location_modifier = hbe_charter_contract }} }}
            add_location_modifier = {{ modifier = hbe_charter_contract years = -1 }} }}
        else_if = {{ limit = {{ owner = {{ NOT = {{ {MEMBER} }} }} }}
            remove_location_modifier = hbe_charter_build remove_location_modifier = hbe_charter_food remove_location_modifier = hbe_charter_contract }}
    }}
}}''')
    # Long-term disputes give mediation decisions actual value, without removing isolation.
    event(23,'锅底都换了，欠条还在','争席度已到七十五。诸侯提出暂停公共项目结算，先清旧债与轮值主持权。可以共同出资核账、消耗积累的锅气和解，或坚持独立处理。外部自治敕书继续生效。',
        [('出五金，公开账簿。',f'add_gold = -5 {dispute(-6)} {yiqi(3)}','gold >= 5',60),
         ('以共同信用担保调停。',f'{pot(-5)} {dispute(-3)}',f'{IO} = {{ var:hbe_guoqi >= 5 }}',20),
         ('本府自理，先保留意见。',f'{yiqi(-2)}','',20)],category='crisis')
    # Monthly sequence is once per situation: register, deliver, pay, vote, settle.
    effects.append(f'''hbe_banquet_monthly = {{
    {IO} ?= {{ every_international_organization_member = {{ hbe_banquet_register = yes
        if = {{ limit = {{ has_variable = hbe_project_pending NOT = {{ has_variable = hbe_project_timer }} }} hbe_deliver_contract = yes }}
    }} }}
    {cv('hbe_round_month',1)}
    if = {{ limit = {{ var:hbe_round_month = 12 }}
        {IO} ?= {{ every_international_organization_member = {{
            if = {{ limit = {{ has_variable = hbe_fund_pledge }}
                remove_variable = hbe_fund_pledge remove_variable = hbe_round_pledged
                if = {{ limit = {{ gold >= 4 }} add_gold = -4 set_variable = hbe_round_contributed set_variable = hbe_round_delivered
                    {cv('hbe_contribution',1)} {yiqi(3)} {pot(1)} }}
                else = {{ {yiqi(-8)} {dispute(5)} trigger_event_non_silently = {{ id = hbe_banquet.6 }} }}
            }}
        }} }}
    }}
    if = {{ limit = {{ has_variable = hbe_ballot_active }} {cv('hbe_ballot_month',1)}
        if = {{ limit = {{ var:hbe_ballot_month >= 6 }} hbe_tally_charter = yes }} }}
    if = {{ limit = {{ var:hbe_dispute >= 75 NOT = {{ has_variable = hbe_crisis_cooldown }} }}
        set_variable = {{ name = hbe_crisis_cooldown value = yes years = 5 }}
        {IO} ?= {{ every_international_organization_member = {{ trigger_event_non_silently = {{ id = hbe_banquet.23 }} }} }}
    }}
    if = {{ limit = {{ var:hbe_round_month >= 36 }} hbe_settle_accounts = yes }}
    set_variable = {{ name = hbe_pot_display value = {IO}.var:hbe_guoqi }}
    hbe_banquet_clamp = yes
}}''')

    # Twenty-one researched regional events, each with its own concrete dilemma.
    regional_stories=[
        [('上游说修渠，下游说放水','新闸门刚装好，上游称蓄水是为了全圈，下游却拿着干田要求共同验收。'),('锦官城的座次图','成都官学绘制帝国座次图，把本城画在中央。其他府州要求把出资与水权一起写上去。'),('都江堰不认选票','百年旧闸需要换木梁，选侯争论谁能在新梁上刻名字；工匠只关心木料是否送到。')],
        [('皇帝点菜，盐商结账','宴席菜单写着盐商赞助，盐商的借据却写着全帝国担保。两张纸正在同桌流传。'),('盐引背面还有盐引','新式承销把旧债叠在新盐引下面，账面信用很好，仓里的盐却没有增加。'),('三代灶户，一张百年欠条','井灶换了三代人，旧工程欠条仍以祖父的名字追认。灶户要求重审而不是重抄。')],
        [('重庆说上席不在上游','重庆使者拒绝按河流方向排座次，称转运的关键是到港，不是离源头近。'),('过滩一次，收费三次','同一条盐船在三个辖境盖了四次章。江运互保允许核查哪一次确有护航。'),('码头换主，船牌不换','府州合并后，新领主把旧船牌当成外邦凭证。船主要求承认仍在帝国内的共同合同。')],
        [('祖传轮戍，轮到别人','各府都拿出祖上传下来的免轮戍书，关口的守军只能一人检查六份免役凭证。'),('驿马在账上跑得最快','驿路账簿显示一天百里，驿站却说马在去年就退休了。路政研究可以追查虚报的段落。'),('剑门借印，不借守军','新任主持请邻府借关印，好在茶会上证明轮值完成；邻府要求先见人再见印。')],
        [('义仓赈粮，亲戚先领','仓单上排在前面的姓氏过于整齐。核账官建议按受灾与库存重新排榜。'),('调停书比诉状还厚','两个府州争的原是三亩边田，契约见证处把三代账本都抬来了。裁决需要把旧功与新债分开。'),('丰收年也要翻旧仓','丰年里无人愿意承担义仓维护。粮政研究指出，公共储备不能只在歉收年记一次。')],
        [('茶价未涨，印章先涨','茶马采购仍按旧价收货，沿线却多了几个收盖章费的山门。'),('马认识路，诸侯不认账','商队已翻过山口，采购府州和运输府州都说另一方应付山门调停费。'),('山门茶会，谁算东道','调停寺院为两位领主各留一把主位，结果被要求再为旧府州保留第三把。')],
        [('谷口的敕书有两个译本','同一份共治条款在谷内表示轮值商谈，在府城表示统一征收。翻译已经成为财政问题。'),('互市赶集，不能只赶账','互市商贩按旧惯例以物换物，账房要求统一交割；地方共治可以协调两种凭证。'),('祖传路权也要登记','新主持想按地图收路费，谷口居民拿出比地图更早的共同通行约。')]
    ]
    random_ids=[]
    for ri,(group,name,_,label,counter,*_) in enumerate(regions):
        for j,(title,story) in enumerate(regional_stories[ri]):
            eid=100+ri*3+j;year=(1337,1352,1397)[j]
            tech_req=f'OR = {{ has_variable = hbe_tech_{group}_3 has_variable = hbe_tech_{group}_6 }}'
            event(eid,title,story+f'\n{label}与课题路线会影响处理办法；旧问题可以在下一代重新发生。',
                [('按共同合同处理，拨二金核验。',f'add_gold = -2 {cv(counter,5)} {yiqi(2)} {dispute(-1)}','gold >= 2',45),
                 ('以成熟地方技术公开凭据。',f'{cv(counter,-5)} {yiqi(3)} {dispute(-2)} add_prestige = 2',f'{tech_req} var:{counter} >= 5',40),
                 ('先顾本府，另开一本账。',f'{cv(counter,3)} {yiqi(-2)} {dispute(2)}','',15)],
                trigger=f'current_year >= {year} has_variable = hbe_home_{group} NOT = {{ has_variable = hbe_banquet_flavor_cooldown }}',
                immediate='set_variable = { name = hbe_banquet_flavor_cooldown value = yes years = 5 }',category=name)
            random_ids.append(eid)
    # Each of the 36 selectable states has a once-per-campaign personal identity event.
    personal=[
        ('锦官城想把主持做到世袭','成都认为首届皇帝既然主持水粮，就应永久主持茶会。'),
        ('汉州的渠首签押','汉州把渠首验收与帝国锅气绑定，要求签押必须有实际水量。'),
        ('彭州山门留座','彭州要求在分账会上给山门商路留席，不能只按平原亩数说话。'),
        ('邛州的新瓷旧账','邛州为茶会烧了一批新碗，账房发现碗底落款比总账还详细。'),
        ('眉州文章压过账本','眉州送来的分账意见写成了长诗，末尾押韵处正好漏掉金额。'),
        ('嘉定山门拒绝空签','嘉定要求凡以山门调停名义取信者，先把真正的争议写出来。'),
        ('叙州把盐引摆上主桌','叙州认为承担信用风险的人应该离皇帝更近，其他选侯要求先看欠条。'),
        ('泸州的宴席验收法','泸州提出宴席采购逐坛验收，酒商则要求不能把品酒算成免费劳动。'),
        ('长宁竹契不怕水','长宁推广耐潮竹契，盐船账房终于不用到港后猜纸上写了什么。'),
        ('昌州石刻永不撤回','昌州把出资承诺刻在石上，后来发现修正金额比原先出资还费工。'),
        ('山城升降不是座次','重庆要求按运力分担，共锅派却把码头阶梯画成了礼仪等级。'),
        ('涪州渡牌该认哪一岸','涪州为两岸渡口争取同一张凭证，避免转运双方各算一遍。'),
        ('合州三江，三份收据','合州把三个水口的收入分别记账，帝国审计询问它们是否属于同一条船。'),
        ('夔州峡口不收空气钱','夔州愿以实际护航换共同经费，但不能只因峡口狭窄就加价。'),
        ('酉阳的图册画得太直','酉阳发现府城互市图把曲折山路画成直线，运输额度因此高得离谱。'),
        ('忠州忠于哪本账','忠州要求每张账单注明届次，免得把本届义务追到三十年前。'),
        ('保宁选票只盖一次','保宁主持确认选侯印不得重复抵押，轮戍义务也不能随选票转卖。'),
        ('巴州关印有磨损','巴州新铸关印过于崭新，审计希望多看看真正守过关的交接文书。'),
        ('广元关口的回程账','广元认为驿路贡献应包括回程，主桌过去只计算送来货的一半路。'),
        ('剑州的路，比奏章短','剑州修直一段险路，请求用验收替代长篇功绩奏报。'),
        ('龙安山货折什么价','龙安以山货支付轮值费用，账房争论应按谷口价还是府城价折算。'),
        ('达州驿使带了两份餐票','达州驿使在圈际换马后又领一份餐票，公共驿路开始核对重复给付。'),
        ('顺庆把船和马写在一起','顺庆连接江运与驿路，要求跨圈功绩可以合记，费用不能重复。'),
        ('简州给合同加了封面','简州认为公账应易于查找，为每届合同编出目录。大家首次发现同一债有三个名字。'),
        ('遂宁义仓也收验收单','遂宁把赈粮实际出库作为信用依据，谢恩匾额暂不算交付。'),
        ('潼川的官印带编号','潼川愿用印号登记每一份共同契约，伪造旧合同忽然变得费劲。'),
        ('广安来了一车旧凭证','广安运来旧年凭证，要求承认此前仓粮出资，且不把它算作本届付款。'),
        ('雅州马票盖在茶票上','雅州商队为了省纸把茶与马记在一页，采购和运输却必须分清。'),
        ('茂州山门轮值名单','茂州要求山门调停按实际人员轮值，不能让同一名字代表所有府州。'),
        ('松潘的长路不止一行','松潘路线最长，府城预算却只留一行运输费。商队拿出沿线站点逐一解释。'),
        ('盐源互市用旧尺','盐源互市继续用旧量尺，共同合同需要登记换算，而不是突然换掉居民的买卖习惯。'),
        ('德昌的谷口轮签','德昌推行轮签凭证，请各谷共同确认之后再报府城。'),
        ('黎州路权先问同行人','黎州建议先确认使用同一山路的商队，再划分维护责任。'),
        ('马湖渡船没有纸上那么大','马湖核查渡船运力，纠正按理想船型制定的共同采购额度。'),
        ('建昌共治，不是共用一把印','建昌选侯要求地方代表参加议约，不能让一枚主印替代所有山谷的意见。'),
        ('永宁想把互市开在谷口','永宁提出让互市更靠近商队，财政官则担心自己要走更远的路。')]
    personal_ids=[]
    for i,c in enumerate(countries):
        eid=200+i;title,story=personal[i];key=f'hbe_personal_{c["tag"].lower()}'
        event(eid,title,story+'\n这是本府的第一次共同机构试办；选择会留下履约与信任记录。',
            [('出二金，把本府试办写成可验收的契约。',f'add_gold = -2 {yiqi(3)} {cv("hbe_contribution",1)} {pot(1)} every_owned_location = {{ limit = {{ is_in_scripted_geography = scripted_geography:hbe_domain }} add_location_modifier = {{ modifier = hbe_project_build years = 3 mode = replace }} }}','gold >= 2',75),
             ('守旧例，暂不承诺共担。',f'{yiqi(-2)} {dispute(1)}','',25)],
            trigger=f'has_or_had_tag = {c["tag"]} NOT = {{ has_variable = {key} }}',immediate=f'set_variable = {key}',category=c['name'])
        personal_ids.append((c['tag'],eid,key))
    # Shared flavor dilemmas refresh each generation, and late content has distinct year gates.
    shared=[
        (30,1337,'茶会主持带来自己的椅子','主持带来的椅子比别家的高出一寸。礼官认为是坐垫厚，诸侯认为是章程薄。'),
        (31,1352,'祖传选票，概不赊欠','选侯把一张祖传保证书当成公共贡献。盐商提醒：祖传的东西也要看现任是否认账。'),
        (32,1372,'皇帝换了，菜单没换','新皇帝继承旧宴席采购单，发现菜名改过，付款人却一直没改。'),
        (33,1397,'敕书装了新封皮','大元旧敕书换上新封皮，诸侯讨论名称时险些忘了自治与盐粮交割条款都还有效。'),
        (34,1422,'七圈地图少了一个圈','新印的圈图把一段山路盖在图例下面，沿线府州要求查图，也查分账额度。'),
        (35,1437,'百年合同的第一页','新章程已写了百页，第一页仍是谁付本届印刷费。百年治理从一张能兑现的账单开始。'),
        (36,1457,'一百二十年，茶还要续','上一代主持的名字已成为故事，但公共工程照常需要现任出资和交付。')]
    for eid,year,title,story in shared:
        event(eid,title,story,
            [('拨二金重审共同规则。',f'add_gold = -2 {dispute(-2)} {yiqi(2)}','gold >= 2',60),
             ('拿三点义气担保下一届。',f'{yiqi(-3)} {pot(2)}','var:hbe_yiqi >= 3',25),
             ('保留本府意见。',dispute(1),'',15)],
            trigger=f'current_year >= {year} NOT = {{ has_variable = hbe_banquet_flavor_cooldown }}',
            immediate='set_variable = { name = hbe_banquet_flavor_cooldown value = yes years = 5 }',category='generational')
        random_ids.append(eid)

    # Fixed dates for personal flavour and a bounded annual random pool.
    personal_pulse='\n'.join(f'''if = {{ limit = {{ current_year >= {1338+i%6} has_or_had_tag = {tag} NOT = {{ has_variable = {key} }} }} trigger_event_non_silently = {{ id = hbe_banquet.{eid} }} }}''' for i,(tag,eid,key) in enumerate(personal_ids))
    annual=f'''if = {{ limit = {{ {SIT} = {{ var:hbe_charter = 1 }} is_leader_of_international_organization = {IO} }}
        if = {{ limit = {{ gold >= 1 }} add_gold = -1 add_prestige = 1 }}
        else = {{ {dispute(5)} }}
    }}'''
    regional_bonus='\n'.join(f'''if = {{ limit = {{ has_variable = hbe_service_{r[0]}_pending NOT = {{ has_variable = hbe_service_{r[0]}_timer }} {SIT} = {{ var:hbe_charter = 2 }} }} add_prestige = 2 }}''' for r in regions)
    # Insert this bonus before the base handler consumes the pending flag.
    base=(out/'in_game/common/scripted_effects/hbe_effects.txt').read_text(encoding='utf-8-sig')
    base=base.replace('hbe_initialize = yes\n',f'hbe_initialize = yes\nif = {{ limit = {{ is_situation_active = {SIT} }} {regional_bonus} }}\n')
    put('in_game/common/scripted_effects/hbe_effects.txt',base)
    # IO re-entry uses actual members; new native rebel countries remain outside unless admitted.
    rejoin='\n'.join(f'''if = {{ limit = {{ OR = {{ {' '.join('has_or_had_tag = '+c['tag'] for c in countries if c['region']==r[0])} }} NOT = {{ is_member_of_international_organization = international_organization:hbe_circle_{r[0]} }} }}
        international_organization:hbe_circle_{r[0]} ?= {{ add_country_to_international_organization = prev }}
    }}''' for r in regions)
    on_action=f'''monthly_country_pulse = {{ on_actions = {{ hbe_banquet_country_maintenance }} }}
hbe_banquet_country_maintenance = {{ effect = {{
    if = {{ limit = {{ hbe_is_prince = yes NOT = {{ {MEMBER} }} }}
        {IO} ?= {{ add_country_to_international_organization = prev }}
        {rejoin}
    }}
    if = {{ limit = {{ is_situation_active = {SIT} {MEMBER} }} hbe_banquet_register = yes }}
    hbe_charter_maintenance = yes
}} }}
yearly_country_pulse = {{ on_actions = {{ hbe_banquet_yearly }} }}
hbe_banquet_yearly = {{ trigger = {{ is_situation_active = {SIT} {MEMBER} }} effect = {{ {annual} {personal_pulse} }}
    random_events = {{ chance_to_happen = 35 {' '.join('1 = hbe_banquet.'+str(eid) for eid in random_ids)} }}
}}'''
    put('in_game/common/on_action/hbe_banquet_on_actions.txt',on_action)
    put('in_game/common/scripted_effects/hbe_banquet_effects.txt','\n'.join(effects))
    put('in_game/common/decisions/hbe_banquet_decisions.txt','\n'.join(decisions))
    put('in_game/events/hbe_banquet_events.txt','namespace = hbe_banquet\n'+'\n'.join(events))
    statics=(out/'main_menu/common/static_modifiers/hbe_modifiers.txt').read_text(encoding='utf-8-sig')
    new_mods=[('hbe_banquet_success','共同工程结算','local_monthly_food_modifier = 0.05 local_construction_speed = 0.05'),
              ('hbe_charter_build','一锅巴蜀章程','local_construction_speed = 0.05'),
              ('hbe_charter_food','万国茶会章程','local_monthly_food_modifier = 0.05'),
              ('hbe_charter_contract','共同契约章程','local_monthly_food_modifier = 0.025 local_construction_speed = 0.025')]
    for key,title,mods in new_mods:
        statics+=f'\n{key} = {{ {mods} }}\n';L(key,title);L(key+'_desc',title+'带来的本地治理收益。');L('STATIC_MODIFIER_NAME_'+key,title)
    put('main_menu/common/static_modifiers/hbe_modifiers.txt',statics)
    # Native panel structure, with a functional ledger rather than a blank situation tab.
    L('HBE_BANQUET_PANEL_TITLE','三十六家，一张账单')
    L('HBE_BANQUET_PANEL_BODY',status.replace('ROOT.','Player.MakeScope.'))
    L('HBE_BANQUET_PANEL_HELP','前六个月在决议中出资或签专业合同；半年交付，第十二个月兑现承诺，第三十六个月统一结算。\n三份专业交付齐全且争席度低于75才算成功。1437年以后、第五阶段且至少30次成功项目，皇帝可提请百年章程。\n共锅、分锅、账房立场在局势地图上分别为红、蓝、黄。全部帝国成员参加；自治盟约一直有效。')
    gui='''situation_panel = {
    blockoverride "situation_panel_image" {
        background = { texture = "gfx/interface/hbe/placeholder.dds" }
    }
    blockoverride "situation_subheader_content" { }
    blockoverride "situation_panel_main_content" {
        text_multi = {
            layoutpolicy_horizontal = expanding autoresize = yes
            text = "HBE_BANQUET_PANEL_TITLE"
        }
        text_multi = {
            layoutpolicy_horizontal = expanding autoresize = yes
            text = "HBE_BANQUET_PANEL_BODY"
        }
        text_multi = {
            layoutpolicy_horizontal = expanding autoresize = yes
            text = "HBE_BANQUET_PANEL_HELP"
        }
    }
}'''
    put('in_game/gui/panels/situation/hbe_banquet.gui',gui)
    # Painted situation icon is exported by build_icon_assets after this stage.
    (root/'data/events_v002.json').write_text(json.dumps(event_catalog,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (root/'data/flags_v002.json').write_text(json.dumps(flags,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return dict(new_events=len(events),new_decisions=len(decisions),flags=flags,situation='hbe_banquet',
                start_date='1337.10.1',cycle_months=36,chapter_years=[1337,1352,1372,1397,1422],
                charter_not_before=1437,charter_projects_required=30,fixed_seats=36,
                external_isolation_preserved=True)
