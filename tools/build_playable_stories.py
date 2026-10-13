"""Native events from authored narratives and individually assigned choice plans."""
import hashlib, importlib.util, json, re, sys
from pathlib import Path
from story_mechanics import PROFILES, SOLO_PLANS, LONG_PLANS, ENDINGS
from migration_stories import CHAPTERS, OFFSETS
from short_stories import SHORT as REGIONAL_SHORT
from shared_stories import SHORT as SHARED_SHORT, SOLO as SHARED_SOLO

ART = {'ecology':'bamboo','archaeology':'fossils','navigation':'river','astronomy':'observatory',
       'agriculture':'terraces','veterinary':'veterinary','bridge':'bridge','craft':'craft','medicine':'medicine',
       'festival':'festival','caravan':'bridge','military':'bridge','education':'observatory','literature':'craft',
       'commerce':'river','justice':'council','labor':'craft','land':'settlement','food':'terraces',
       'culture':'festival','faith':'council','water':'terraces','tax':'council'}

END_PROSE = {
'chengdu_plain': ('巡山的人带来最后一册记录。山民的柴路、竹农的供养和白熊往来的兽径，终于被写在同一张图上。府城使者仍想把珍兽送进城苑，村寨却已经能说清哪些山地须留下，哪些田可继续耕作。护育不再只是一次放归，而是每年都要履行的共同约定。', '城苑的竹院已经换过几代养兽人，来访者能够看见活兽，也能够读到它们的饮食与习性。巡山人担心远离山林的供养越来越贵，商人则愿承担一部分费用。府署选择把这些年的成果留在瑞兽馆中，声名与访客将伴着一笔持续的开支。'),
'southern_salt_wine': ('一块块巨骨按井口与石层排列起来，师生终于能够辨认旧图中混在一起的残片。井工的姓名写在出土记录里，访学者可以借阅井谱而不必先购买药商的旧说。盐井仍要出卤，巨骨却有了独立于盐价的价值：后来的查验者可以从这些材料继续追问。', '龙骨陈馆的门打开了，盐场来客在巨骨前停步，商人也愿为修井出钱。陈列保留了许多让人惊叹的形状，却没有解决师生争论的每一个疑点。府署把奇观与盐业连在一起，今后的主持者须同时面对宾客的期待和井户的账目。'),
'eastern_river': ('船夫们把水势谱摊在码头，按江段重新推举领航人。村寨的夜号和船帮的复测记录都能进入下一版，不必再等某一家人的旧牌。船约给过滩者留下了共同使用的办法，也把维护的责任留给真正走这条江的人。', '护航船队接过统一的通行券，江岸各站不再各收一遍。军府能够把领航、运输与守备一起安排，商船也须接受船队的行期和费用。多年争论留下的水势谱，最后成为总署调度江道的凭据。'),
'northern_shudao': ('山口各站把记录送进测候台，旧仪器与新历书被放在同一张案上。主持者可以更换，查验的方法却不能随家世改变。学舍每年招收能够读簿和修器的年轻人，蜀道的晨昏从此有了一份可供后来者复核的共同记录。', '关城的更鼓依同一套时刻响起，测候人和守望兵把仪器编入轮戍。公开讲读让位于军用传时，驿刻却比从前整齐。府署将几十年的积累交给关军，换来更可靠的山路防务与供给。'),
'central_hills': ('新修的埂没有在地图上变成一条笔直的线。村落仍按坡势和来水安排维修，仓中也为无力修埂的人留下一份种粮。田主不能只凭家世免去分担，乡民也不能借共同田地逃避照料。共护章程把丰年和旱年的责任一同留下。', '统一田册列明田界、水口和修埂份额，府署终于能把过去分散的租额核在一起。旧村长请求保留几处按乡约供粮的例外，掌册官答应另附一页。国家得到更清楚的收入与控制，乡民也将面对更整齐的征收。'),
'western_tea_horse': ('医马人的学生沿茶路分到各站，药方、繁育簿和草场记录不再只由一座官苑保管。牧户能够送病马来舍中，也能按用途出售驮马。学舍不能替每一支商队免去山路的风险，却给沿途的人留下了持续照料牲畜的办法。', '官苑把良马与照料者的姓名记在同一册中，军府可以按轮戍与征调安排供养。普通驮马仍由牧户经营，最好的马却先满足官用。多年医治与繁育积累变成稳定的军马来源，也变成府库须长期承担的责任。'),
'southwestern_valleys': ('桥上的绳结、铁索和旧木契被收入共同桥约。不同村寨仍保留自己的说法，却能够按使用与维修记录重新分担。过路的商队只须面对一套共用办法，养桥的人也能在下一次议约时说出自己的贡献。', '关桥总署在各谷设下统一的票牌，税费与维修钱进入同一公账。村寨不再各自收取桥钱，守军却可以更快地调动铁匠和人手。诸谷得到了贯通的道路，也把对通行权的部分主持交给了府署。')
}

def build(out, root):
    out, root = Path(out), Path(root)
    sys.path.insert(0, str(root/'data'))
    from story_blueprints import LONG
    from independent_stories import SOLO
    loc = {}; files = []; events = []; modifiers = {}; option_catalog = []; schedulers=[]; solos=[]
    def put(relative, text):
        path=out/relative; path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(text.rstrip()+'\n',encoding='utf-8-sig',newline='\n'); files.append(relative)
    def L(k,v):
        if k in loc: assert loc[k]==v,k
        loc[k]=v
    def var(key,value): return f'set_variable = {{ name = {key} value = {value} }}'
    def timer(key,years): return f'set_variable = {{ name = {key} value = yes years = {years} }}'
    def mod(key, title, values, permanent=False):
        modifiers[key]=dict(values)
        L('STATIC_MODIFIER_NAME_'+key,title)
        L('STATIC_MODIFIER_DESC_'+key,('长期章程。' if permanent else '由这次抉择形成的短期安排。')+'具体影响见下列数值。')
    def plan(script, key, title, years=3):
        if key=='hbe_story_choice_eastern_river_6_3':key='hbe_story_choice_eastern_river_toll_6_3'
        values={}; effects=[]; cost=0
        for token in script.split():
            if token in PROFILES:
                _, profile=PROFILES[token]
                for name,value in profile.items():values[name]=values.get(name,0)+value
            else:
                match=re.fullmatch(r'(g|p|s|r|peasants|nobles|burghers|clergy|tribes)([-+]?[\d.]+)',token)
                if not match:raise ValueError(('Unknown choice token',token))
                resource, value=match.groups(); value=float(value)
                if resource in ('g','p','s','r'):
                    effect={'g':'add_gold','p':'add_prestige','s':'add_stability','r':'add_research_progress'}[resource]
                    effects.append(f'{effect} = {value:g}')
                    if resource=='g' and value<0:cost-=value
                else:effects.append(f'add_estate_satisfaction = {{ type = estate_type:{resource}_estate value = {value:g} }}')
        if values:
            names=[PROFILES[t][0] for t in script.split() if t in PROFILES]
            mod(key,' · '.join(names),values)
            effects.append(f'add_country_modifier = {{ modifier = {key} years = {years} mode = replace }}')
        return effects, (f'gold >= {cost:g}' if cost else ''), values
    def emit_option(event_id, letter, label, body, condition='', weight=30, profile='', years=3):
        key=event_id+'.'+letter;L(key,label)
        effects=body if isinstance(body,list) else [body]
        option_catalog.append(dict(event=event_id,letter=letter,label=label,effects='\n'.join(effects),condition=condition,profile=profile,years=years))
        return f'option = {{ name = {key} '+(f'trigger = {{ {condition} }} ' if condition else '')+f'ai_chance = {{ base = {weight} }} '+'\n'.join(effects)+' }'
    def emit(event_id,title,body,trigger,immediate,options,art,category):
        L(event_id+'.title',title);L(event_id+'.desc',body)
        events.append(dict(id=event_id,title=title,art=art,category=category,trigger=trigger,options=len(options)))
        return f'''{event_id} = {{
 type = country_event title = {event_id}.title desc = {event_id}.desc outcome = neutral
 illustration_tags = {{ 1000 = hbe_story_art_{art} }}
 trigger = {{ hbe_is_prince = yes {trigger} }}
 immediate = {{ {immediate} }}
 {' '.join(options)}
}}'''
    def tags_condition(tags):return 'OR = { '+' '.join('has_or_had_tag = '+t for t in tags.split())+' }'
    for region, story in LONG.items():
        namespace='hbe_story_'+region; chunks=['namespace = '+namespace]
        phase='hbe_story_'+region+'_phase';score='hbe_story_'+region+'_direction';clock='hbe_story_'+region+'_clock'
        pending='hbe_story_'+region+'_pending';done='hbe_story_'+region+'_closed'
        for n,(ending,_) in enumerate(ENDINGS[region]):
            L(f'hbe_story_{region}_branch_{n+1}_tt',f'这项安排使本国更倾向“{ending}”的道路。')
            L(f'hbe_story_{region}_ready_{n+1}_tt',f'历次选择已经支持“{ending}”的道路。')
        L(f'hbe_story_{region}_stop_tt','本国停止后续投入；这条事件链到此结束，不获得永久结局章程。')
        route=tags_condition(story['tags']); art=ART[story['theme']]
        schedules=[]
        authored=[line.split('|') for line in LONG_PLANS[region].splitlines()]
        assert len(authored)==7
        for i,(title,body,labels) in enumerate(story['steps']):
            event_id=f'{namespace}.{i+1}';opts=[]
            header=route+f' var:{phase} = {i} NOT = {{ has_variable = {done} }}'
            scheduling=f'NOT = {{ has_variable = {pending} }} NOT = {{ has_variable = {clock} }} {header}'
            if i==0:scheduling+=f' current_year >= {story["start_year"]}'
            schedules.append(f'if = {{ limit = {{ {scheduling} }} set_variable = {pending} trigger_event_non_silently = {{ id = {event_id} }} }}')
            labels=labels.split('|')
            body+='\n\n'+(f'本篇是“{story["name"]}”的第{i+1}章。前面的选择将决定最后保留哪一种长期章程。' if i<7 else '历年的选择已经留下方向；最后的章程只能从已经得到支持的道路中确定。')
            if i<7:
                for n,script in enumerate(authored[i]):
                    key=f'hbe_story_choice_{region}_{i+1}_{n+1}'
                    effects,condition,values=plan(script.strip(),key,title)
                    direction=(2,1,-2)[n]
                    delay=story['offsets'][i+1]-story['offsets'][i]
                    L(f'hbe_story_next_{delay}_tt',f'下一章将在约{delay}年后继续。')
                    effects += [f'custom_tooltip = hbe_story_{region}_branch_{1 if n<2 else 2}_tt',f'custom_tooltip = hbe_story_next_{delay}_tt', 'hidden_effect = { '+f'change_variable = {{ name = {score} add = {direction} }} '+var(phase,i+1)+' '+timer(clock,delay)+f' remove_variable = {pending}'+' }']
                    if n==0:effects+=['add_prestige = 1']
                    opts.append(emit_option(event_id,chr(97+n),labels[n],effects,condition,35,script.strip()))
                abort=[f'custom_tooltip = hbe_story_{region}_stop_tt','hidden_effect = { '+f'set_variable = {done} set_variable = hbe_story_{region}_abandoned remove_variable = {pending}'+' }','add_prestige = -2']
                opts.append(emit_option(event_id,'d','到此为止，不再投入后续事业。',abort,weight=4))
            else:
                for n,(ending,values) in enumerate(ENDINGS[region]):
                    end_id=f'{namespace}.{201+n}'
                    reward=f'hbe_story_ending_{region}_{n+1}'
                    mod(reward,ending,values,True)
                    direction=('>= 0','< 0')[n]
                    opts.append(emit_option(event_id,chr(97+n),ending+'。',['hidden_effect = { '+f'set_variable = {done} '+var(phase,8)+f' remove_variable = {pending} '+'}',f'trigger_event_non_silently = {{ id = {end_id} days = 1 }}'],f'custom_tooltip = {{ text = hbe_story_{region}_ready_{n+1}_tt var:{score} {direction} }}',50))
                    finalbody=END_PROSE[region][n]+'\n\n几十年的笔记、工钱与争执没有凭空消失。它们被保存进新的章程，成为后来主持者必须继续履行的责任。至此，这段事业已经收束，获得的长期收益将随国家延续。'
                    finaloption=emit_option(end_id,'a','把章程留给后来者。',['add_prestige = 6',f'add_country_modifier = {{ modifier = {reward} years = -1 mode = replace }}',f'set_variable = hbe_story_{region}_ending_{n+1}'],weight=100,years=0)
                    chunks.append(emit(end_id,ending,finalbody,route+f' has_variable = {done} NOT = {{ has_variable = hbe_story_{region}_ending_1 }} NOT = {{ has_variable = hbe_story_{region}_ending_2 }}','',[finaloption],art,'地区结局'))
                opts.append(emit_option(event_id,'c','封存旧案，不另立长期章程。',[f'custom_tooltip = hbe_story_{region}_stop_tt','hidden_effect = { '+f'set_variable = {done} '+var(phase,8)+f' remove_variable = {pending}'+' }','add_prestige = -2'],weight=0))
            chunks.append(emit(event_id,title,body,header,'',opts,art,'地区长线'))
        schedulers.append(f'if = {{ limit = {{ {route} NOT = {{ has_variable = {done} }} }} if = {{ limit = {{ NOT = {{ has_variable = {phase} }} }} {var(phase,0)} {var(score,0)} }} '+ '\n'.join(schedules)+' }')
        solo_authored=[line.split('|') for line in SOLO_PLANS[region].splitlines()]
        assert len(solo_authored)==len(SOLO[region])==13
        for i,(seed,plans) in enumerate(zip(SOLO[region],solo_authored)):
            event_id=f'{namespace}.{101+i}';opts=[];conditions=[]
            for n,script in enumerate(plans):
                effects,condition,values=plan(script.strip(),f'hbe_story_choice_{region}_{101+i}_{n+1}',seed['title'],years=(2,3,4)[(i+n)%3])
                conditions.append(condition)
                opts.append(emit_option(event_id,chr(97+n),seed['choices'][n],effects,condition,weight=30,profile=script.strip(),years=(2,3,4)[(i+n)%3]))
            if all(conditions):
                opts.append(emit_option(event_id,'d','暂缓裁定，不再从府库拨款。',['add_prestige = -1'],weight=2))
            seen=f'hbe_story_seen_{region}_{101+i}'
            trigger=tags_condition(' '.join(seed['tags']))+f' current_year >= {seed["year"]} NOT = {{ has_variable = {seen} }} NOT = {{ has_variable = hbe_story_solo_cooldown }}'
            chunks.append(emit(event_id,seed['title'],seed['body'],trigger,f'set_variable = {seen} '+timer('hbe_story_solo_cooldown',2),opts,ART[seed['theme']],'地方独立'))
            solos.append(event_id)
        put(f'in_game/events/{namespace}.txt','\n\n'.join(chunks))
    # All princes receive their own shared arc; acceptance is not a forced AI-only grant.
    namespace='hbe_migration';chunks=['namespace = '+namespace]
    phase='hbe_migration_phase';score='hbe_migration_acceptance';clock='hbe_migration_clock';pending='hbe_migration_pending';done='hbe_migration_closed'
    L('hbe_migration_accept_tt','更愿意接纳来人；这会支持最后的新乡共籍章程。')
    L('hbe_migration_limit_tt','保留旧户名额；这会支持最后的担保入籍章程。')
    L('hbe_migration_ready_open_tt','历次安排已经给共同入籍留下足够支持。')
    L('hbe_migration_ready_closed_tt','历次安排更倾向由旧户担保接纳来人。')
    schedules=[]
    for i,(title,body,labels,plans,art) in enumerate(CHAPTERS):
        event_id=f'{namespace}.{i+1}';opts=[];labels=labels.split('|')
        header=f'var:{phase} = {i} NOT = {{ has_variable = {done} }}'
        if i==0:header+=' current_year >= 1345'
        scheduling=header+f' NOT = {{ has_variable = {pending} }} NOT = {{ has_variable = {clock} }}'
        if i==0:scheduling+=' current_year >= 1345'
        schedules.append(f'if = {{ limit = {{ {scheduling} }} set_variable = {pending} trigger_event_non_silently = {{ id = {event_id} }} }}')
        if i<9:
            for n,script in enumerate(plans.split('|')):
                effects,condition,_=plan(script.strip(),f'hbe_migration_choice_{i+1}_{n+1}',title,years=(3,3,4)[n])
                delay=OFFSETS[i+1]-OFFSETS[i]; L(f'hbe_story_next_{delay}_tt',f'下一章将在约{delay}年后继续。')
                effects += [f'custom_tooltip = hbe_migration_{"accept" if n<2 else "limit"}_tt',f'custom_tooltip = hbe_story_next_{delay}_tt','hidden_effect = { '+f'change_variable = {{ name = {score} add = {(2,1,-1)[n]} }} '+var(phase,i+1)+' '+timer(clock,delay)+f' remove_variable = {pending}'+' }']
                opts.append(emit_option(event_id,chr(97+n),labels[n],effects,condition,35,script.strip()))
        else:
            rewards=[('新乡共籍约',{'global_migration_attraction':.10,'global_population_capacity_modifier':.06,'global_pop_assimilation_speed_modifier':.06,'nobles_estate_target_satisfaction':-.02}),('旧户担保制',{'global_monthly_control':.01,'tax_income_efficiency':.04,'nobles_estate_target_satisfaction':.03,'global_migration_attraction':-.05})]
            for n,(name,values) in enumerate(rewards):
                key=f'hbe_migration_ending_{n+1}';mod(key,name,values,True)
                opts.append(emit_option(event_id,chr(97+n),labels[n],[f'add_country_modifier = {{ modifier = {key} years = -1 mode = replace }}','add_prestige = 5','hidden_effect = { '+f'set_variable = {done} '+var(phase,10)+f' remove_variable = {pending}'+' }'],f'custom_tooltip = {{ text = hbe_migration_ready_{"open" if n==0 else "closed"}_tt var:{score} '+('>= 6','< 6')[n]+' }',50,years=0))
            opts.append(emit_option(event_id,'c',labels[2],['hidden_effect = { '+f'set_variable = {done} '+var(phase,10)+f' remove_variable = {pending}'+' }','add_prestige = -1'],weight=0))
        body+='\n\n'+f'“湖广填四川”第{i+1}章。'+'入籍、工牌与乡约的历次决定，会影响最后留下的共同章程。'
        chunks.append(emit(event_id,title,body,header,'',opts,art,'共同移民长线'))
    put('in_game/events/hbe_migration_events.txt','\n\n'.join(chunks))
    schedulers.append(f'if = {{ limit = {{ NOT = {{ has_variable = {done} }} }} if = {{ limit = {{ NOT = {{ has_variable = {phase} }} }} {var(phase,0)} {var(score,0)} }} '+'\n'.join(schedules)+' }')
    short_groups={}; counts={}
    for story in REGIONAL_SHORT+SHARED_SHORT:
        region=story['region']; namespace='hbe_short_'+region
        index=counts.get(region,0);counts[region]=index+1
        chunks=short_groups.setdefault(region,['namespace = '+namespace])
        phase=f'hbe_short_{region}_{index+1}_phase';clock=f'hbe_short_{region}_{index+1}_clock'
        pending=f'hbe_short_{region}_{index+1}_pending';seen=f'hbe_short_{region}_{index+1}_seen'
        route=tags_condition(story['tags']) if story['tags'] else 'always = yes'
        for i,((title,body,choices),plans) in enumerate(zip(story['chapters'],story['plans'])):
            event_id=f'{namespace}.{index*10+i+1}';opts=[]
            for n,(label,script) in enumerate(zip(choices.split('|'),plans.split('|'))):
                effects,condition,_=plan(script.strip(),f'hbe_short_choice_{region}_{index+1}_{i+1}_{n+1}',title,years=2+i)
                effects += [var(phase,i+1),f'remove_variable = {pending}']
                if i<2:effects+=[f'set_variable = {{ name = {clock} value = yes months = {(6,12)[i]} }}']
                if i==2:effects+=['add_prestige = 2']
                opts.append(emit_option(event_id,chr(97+n),label,effects,condition,30,script.strip(),2+i))
            opts.append(emit_option(event_id,'d','停止后续办理，到此结束。',[var(phase,3),f'remove_variable = {pending}','add_prestige = -1'],weight=3))
            trigger=route+(' NOT = { has_variable = '+seen+' } NOT = { has_variable = hbe_story_solo_cooldown } current_year >= 1339' if i==0 else f' var:{phase} = {i} NOT = {{ has_variable = {clock} }}')
            immediate=(f'set_variable = {seen} '+timer('hbe_story_solo_cooldown',2)) if i==0 else ''
            fullbody=story['context']+'\n\n'+body+'\n\n'+f'“{story["name"]}”第{i+1}篇。'
            chunks.append(emit(event_id,title,fullbody,trigger,immediate,opts,ART[story['theme']],'移民短链' if region=='shared' else '地区短链'))
            if i==0:solos.append(event_id)
            else:
                schedulers.append(f'if = {{ limit = {{ has_variable = {phase} var:{phase} = {i} {route} NOT = {{ has_variable = {clock} }} NOT = {{ has_variable = {pending} }} }} set_variable = {pending} trigger_event_non_silently = {{ id = {event_id} }} }}')
    chunks=short_groups['shared']
    for i,seed in enumerate(SHARED_SOLO):
        event_id=f'hbe_short_shared.{201+i}';opts=[]
        for n,script in enumerate(seed['plans']):
            effects,condition,_=plan(script.strip(),f'hbe_shared_choice_{201+i}_{n+1}',seed['title'],3)
            opts.append(emit_option(event_id,chr(97+n),seed['choices'][n],effects,condition,30,script.strip()))
        opts.append(emit_option(event_id,'d','暂缓裁定，不再由府库出资。',['add_prestige = -1'],weight=2))
        seen=f'hbe_shared_seen_{201+i}'
        chunks.append(emit(event_id,seed['title'],seed['body'],f'current_year >= 1340 NOT = {{ has_variable = {seen} }} NOT = {{ has_variable = hbe_story_solo_cooldown }}',f'set_variable = {seen} '+timer('hbe_story_solo_cooldown',2),opts,ART[seed['theme']],'共同独立'))
        solos.append(event_id)
    for region,chunks in short_groups.items():put(f'in_game/events/hbe_short_{region}.txt','\n\n'.join(chunks))
    put('in_game/common/scripted_effects/hbe_story_scheduler.txt','hbe_story_monthly = { if = { limit = { hbe_is_prince = yes } '+'\n'.join(schedulers)+' } }')
    put('in_game/common/on_action/hbe_story_on_actions.txt','monthly_country_pulse = { on_actions = { hbe_story_monthly_pulse } }\nhbe_story_monthly_pulse = { effect = { hbe_story_monthly = yes } }\nyearly_country_pulse = { on_actions = { hbe_story_local_pulse } }\nhbe_story_local_pulse = { trigger = { hbe_is_prince = yes NOT = { has_variable = hbe_story_solo_cooldown } } random_events = { chance_to_happen = 55 '+' '.join('1 = '+eid for eid in solos)+' } }')
    put('main_menu/common/static_modifiers/hbe_story_modifiers.txt','\n'.join(k+' = { '+' '.join(name+' = '+format(value,'.6g') for name,value in values.items())+' }' for k,values in modifiers.items()))
    for language in ('simp_chinese','english'):
        # English safely falls back to complete authored Chinese text for this new batch.
        # Full literary English translation remains a separate pass, never fabricated.
        put(f'main_menu/localization/{language}/hbe_story_l_{language}.yml','l_'+language+':\n'+'\n'.join(' '+k+': '+json.dumps(v,ensure_ascii=False) for k,v in loc.items()))
    manifest_path=out/'build_manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    result=dict(version=manifest['version'],event_count=len(events),regions={r:32 for r in LONG},shared_chapters=10,
                region_chapters=8,region_endings=2,regional_duration_years=45,shared_duration_years=49,
                country_modifiers=len(modifiers),events=events,options=option_catalog,files=files,
                english_status='Chinese fallback for the newly authored batch; existing English localization retained')
    result['regions']={r:32 for r in LONG}
    result.update(regional_short_chains=21,shared_short_chains=12,shared_independent_events=18)
    manifest['playable_stories']={k:v for k,v in result.items() if k not in ('events','options')}
    manifest['files'].update({p:hashlib.sha256((out/p).read_bytes()).hexdigest() for p in files})
    manifest['event_definitions']=sum(len(re.findall(r'(?m)^hbe\w*\.\d+\s*=\s*\{',p.read_text(encoding='utf-8-sig'))) for p in (out/'in_game/events').glob('*.txt'))
    manifest['events']=manifest['event_definitions']-1
    manifest['hidden_events']=1
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (root/'data/playable_stories_v030.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'new_events':len(events),'new_options':len(option_catalog),'modifiers':len(modifiers),'total_events':manifest['events']},ensure_ascii=False))
    return result

if __name__=='__main__':
    root=Path(sys.argv[1]);build(root/'mod/holy_bashu_empire',root)
