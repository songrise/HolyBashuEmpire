"""Remove the retired service loop after legacy content generators have run."""
import json
import re

from build_support import write_preserving_format
from pdxscript import blocks, apply_edits


def apply(out, put, regions):
    groups = [r[0] for r in regions]
    obsolete = ['hbe_service_cooldown', 'hbe_project_pending', 'hbe_project_timer']
    for group in groups:
        obsolete += [f'hbe_service_{group}_pending', f'hbe_service_{group}_timer', f'hbe_recent_delivery_{group}']

    # Drop only if branches whose own limit tests an obsolete pending order.
    # Enclosing monthly country/organization logic remains intact.
    pending = re.compile(r'\bhas_variable\s*=\s*(?:hbe_service_\w+_pending|hbe_project_pending)\b')
    for rel in ('in_game/common/scripted_effects/hbe_effects.txt',
                'in_game/common/on_action/hbe_simple_banquet_on_actions.txt'):
        path = out/rel
        text = path.read_text(encoding='utf-8-sig')
        edits = []
        for key, start, a, b, end in blocks(text):
            if key != 'if': continue
            body = text[a:b]
            limit = next((body[x:y] for k, _, x, y, _ in blocks(body, 0) if k == 'limit'), '')
            if pending.search(limit): edits.append((start, end, ''))
        write_preserving_format(path, apply_edits(text, edits))

    for path in (out/'in_game').rglob('*.txt'):
        if path.name.startswith('hbe_af_'): continue
        text = path.read_text(encoding='utf-8-sig')
        original = text
        if path.name == 'hbe_decisions.txt':
            edits = []
            for key, _, a, b, _ in blocks(text, 0):
                if not key.startswith('hbe_service_'): continue
                body = text[a:b]
                patches = []
                for field, start, x, y, end in blocks(body, 0):
                    if field in ('potential', 'allow'):
                        patches.append((x,y,' always = no '))
                    elif field == 'option':
                        patches.append((x,y,f' name = {key}.a ai_chance = {{ value = 100 }} effect = {{ }} '))
                edits.append((a,b,apply_edits(body,patches)))
            text = apply_edits(text, edits)
        if path.name == 'hbe_civic_decisions.txt':
            edits = []
            for key, _, a, b, _ in blocks(text, 0):
                if not key.startswith('hbe_coordinate_'): continue
                body = text[a:b]
                potential = next(x for x in blocks(body, 0) if x[0] == 'potential')
                body = apply_edits(body, [(potential[2],potential[3],' always = no ')])
                edits.append((a,b,body))
            text = apply_edits(text, edits)
        if path.name == 'hbe_civic_effects.txt':
            edits = [(start,end,'') for key,start,_,_,end in blocks(text,0)
                     if key.startswith(('hbe_record_service_', 'hbe_pay_service_'))]
            text = apply_edits(text, edits)
        if path.name == 'hbe_civic_advances.txt':
            text = re.sub(r'\bpure_tooltip_entry\s*=\s*hbe_civic_(?:'+'|'.join(groups)+r')_[12]_effects\b','',text)
        if path.name in ('hbe_simple_banquet_effects.txt','hbe_banquet_effects.txt'):
            edits=[]
            for key,_,a,b,_ in blocks(text,0):
                if key in ('hbe_feast_help','hbe_deliver_contract'):
                    edits.append((a,b,''))
            text=apply_edits(text,edits)
        # Retired hidden feast proposals must not depend on, or recreate, old orders.
        text=re.sub(r'\bNOT\s*=\s*\{\s*any_country\s*=\s*\{\s*has_variable\s*=\s*hbe_project_pending\s*\}\s*\}', '', text)
        obsolete_names = set(obsolete)
        edits=[]
        for key,start,a,b,end in blocks(text):
            if key != 'set_variable': continue
            name=re.search(r'\bname\s*=\s*(\w+)',text[a:b])
            if name and name[1] in obsolete_names: edits.append((start,end,''))
        text=apply_edits(text,edits)
        # Remove obsolete requirements outright; do not substitute another grind.
        old = r'(?:hbe_recent_delivery_\w+|hbe_service_cooldown)'
        text = re.sub(r'\bNOT\s*=\s*\{\s*has_variable\s*=\s*'+old+r'\s*\}', '', text)
        text = re.sub(r'\bhas_variable\s*=\s*'+old+r'\b', '', text)
        if text != original: write_preserving_format(path,text)

    replacements = {
        'hbe_levy_policy_desc': '按府额征集人手。地方事业役负投入提高25%；政令带来营建便利，也增加乡里负担。',
        'hbe_communal_policy_desc': '由乡社见证分摊与期限，按项目列示承担役负；驻防粮额沿用议约。',
        'hbe_paid_policy_desc': '由行会承办项目，地方事业役负投入降低50%；金币费用按项目面板列示。',
        'hbe_banquet_ledger.desc': '查看两派成员、本届贡献与收益。成员悬浮列示出资及项目贡献。',
        'hbe_banquet_ledger.desc.entry': '查看两派成员、本届贡献与收益。成员悬浮列示出资及项目贡献。',
        'game_concept_hbe_term_regional_desc': '本圈机构、产业与项目成果共同构成地方经营。具体资格由相关科技、建筑与决议列示。',
        'game_concept_hbe_term_service_desc': '在地方事业面板选择全国或地方事业，确定投入后自动施工。费用、工期与预计成果由项目列示；完工发放实际成果并计入本届贡献。',
        'game_concept_hbe_term_mission_desc': '每圈五个验收阶段。满足前置阶段、研究及列示的经营条件后，支付金币并承担2点役负。验收增加义气、共同信用与威望，各阶段只能完成一次。',
        'game_concept_hbe_term_delivery_desc': '项目完工后的实际成果记入本届贡献；各国记录可在大开席成员行悬浮查看。',
        'game_concept_hbe_term_civic_office_desc': '须满足委任科技、成长验收及机构运转等列示条件。每圈同时一位主持，每国至多两任，任期五年；断供、退盟或役负达到70会提前退任。',
    }
    old_resource = r'@hbe_(?:water|salt|river|roads|grain|tea|valleys)!\s*\[Concept\([^\]]*\)\|e\]'
    for path in (out/'main_menu/localization').rglob('hbe_l_*.yml'):
        lines=[]
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            match=re.match(r'\s*([^:]+):',line)
            key=match[1] if match else ''
            value=None
            if key in replacements: value=replacements[key]
            elif re.fullmatch(r'hbe_service_\w+\.desc(?:\.entry)?',key):
                value='请在地方事业面板选择项目并筹办。'
            elif re.fullmatch(r'hbe_civic_(?:'+ '|'.join(groups)+r')_[12]_effects',key):
                continue # Their only hook described retired completion rewards.
            if value is not None: line=' '+key+': "'+value+'"'
            if key.startswith('hbe_mission_'):
                line=re.sub(r'消耗\s*10\s*点'+old_resource+r'和\s*\d+\s*金币', '支付列示金币并承担2点役负',line)
                line=line.replace('需要研究、持续交付与真实出资','需要研究与本圈经营资格')
            if key.startswith(('hbe_coordinate_','hbe_seek_')):
                line=line.replace('本届地方储备与','本府财力与').replace('五年内完成本圈事业','本圈机构正常运转')
            if key in ('hbe_term_burden_desc','game_concept_hbe_term_burden_desc'):
                line=line.replace('事业征办+6、议办+2、雇办不增加','地方事业役负按投入档次列示，征办提高25%，雇办降低50%')
            if key == 'game_concept_hbe_term_charter_divided_desc':
                line=re.sub(r'；地区\[Concept\([^\]]+\)\|e\]交付追加2声望','',line)
                line=re.sub(r'\\n\\n它不会免费提供.*?(?="$)','',line)
            if key.endswith('_desc') and key.startswith(('hbe_village_witnesses','hbe_guild_payment_guarantee')):
                line=re.sub(r'撤销前必须降低乡里压力，并终止尚未结算的(?:\[Concept\([^\]]+\)\|e\]|地方事业)','撤销时役负须低于40',line)
            lines.append(line)
        write_preserving_format(path,'\n'.join(lines)+'\n')
    clean_descriptions(out)
    strip_orphan_writes(out)


ORPHAN_VARIABLES = (
    'hbe_ballot_month', 'hbe_delivery_circle', 'hbe_delivery_kind', 'hbe_delivery_role',
    'hbe_pot_display', 'hbe_common_defense_notice_acknowledged',
    'hbe_formed_chongqing', 'hbe_formed_sichuan',
    'hbe_opening_children', 'hbe_opening_expiry_completed',
    'hbe_af_last_project', 'hbe_af_round_completions', 'hbe_civic_council_done',
)


def strip_orphan_writes(out):
    """Drop writes to variables nothing reads any more (kept for old saves)."""
    names = set(ORPHAN_VARIABLES)
    touched = 0
    for path in (out / 'in_game').rglob('*.txt'):
        text = path.read_text(encoding='utf-8-sig')
        if not any(n in text for n in names):
            continue
        edits = []
        for key, start, a, b, end in blocks(text):
            if key not in ('set_variable', 'change_variable'):
                continue
            name = re.search(r'\bname\s*=\s*(\w+)', text[a:b])
            short = re.fullmatch(r'\s*(hbe_\w+)\s*', text[a:b])
            target = name[1] if name else (short[1] if short else None)
            if target in names:
                edits.append((start, end, ''))
        if edits:
            write_preserving_format(path, apply_edits(text, edits))
            touched += len(edits)
        text = path.read_text(encoding='utf-8-sig')
        cleaned = text
        for name in names:
            cleaned = re.sub(r'\b(?:set|change)_variable\s*=\s*' + name + r'\b', '', cleaned)
        if cleaned != text:
            write_preserving_format(path, cleaned)
            touched += 1
    return touched


def clean_descriptions(out):
    """Current rules only: no retired resource, timed-service or decision research guide."""
    from build_technology_rewards import NETWORKS
    replacements = {
        'hbe_tech_common_5_effects': '可授予行会雇价保任；须采用行会雇办。',
        'hbe_civic_common_2_effects': '可取得其他圈的产业建筑及基础兵种资格；须在目标圈拥有土地，满足政策、义气与费用条件，再分别办理准入。',
        'game_concept_hbe_term_research_desc': '在革新树中选择科技并投入研究进度。前置科技与时代要求由科技卡列示；建筑、兵种、生产方式和经营权限以卡片实际效果为准。',
        'game_concept_hbe_term_contribution_desc': '本国对会盟的累计贡献，不随领主更替清零。每届出资计1分；地方事业完工按投入、工期和实际成果计入小数贡献，每届项目贡献至多2分。大开席成员行悬浮显示本届构成。',
        'game_concept_hbe_term_contract_desc': '共同事务应写明谁承担钱粮、如何交割以及所得成果。地方事业在右下角面板筹办，政治合作在大开席面板办理；具体费用、工期和收益以对应行动列示为准。',
        'game_concept_hbe_term_saltproject_desc': '诸府围绕盐货与江运开展合作，会盟按实际出资和地方事业完工贡献结算。',
        'game_concept_hbe_term_teaproject_desc': '诸府围绕茶货、商路与山谷贸易开展合作，会盟按实际出资和地方事业完工贡献结算。',
        'game_concept_hbe_term_subsidy_desc': '会盟出资在大开席面板办理，每国每届一次，实际费用与贡献由按钮列示。',
        'game_concept_hbe_term_audit_desc': '当前地方事业的费用与实际成果在项目卡和完工通知列示，本届贡献可在大开席面板查看。',
        'game_concept_hbe_term_yiqi_desc': '本国合作信誉，范围0—100。用于部分政治、产业合作与经营资格；具体增减以行动效果列示为准。',
        'game_concept_hbe_term_civic_policy_desc': '全国选择一种民役政策，五年内不能改换。地方事业按卡片费用办理：征办使役负增加25%，雇办使役负减少50%，议办按原数承担。',
        'hbe.4.desc': '本府的义气：[ROOT.GetVariable(\'hbe_yiqi\').GetValue|0] / 100。\n帝国锅气：[GetUniqueInternationalOrganization(\'hbe_empire\').MakeScope.GetVariable(\'hbe_guoqi\').GetValue|0] / 100。\n\n地方事业请在右下角地方事业面板查看；会盟贡献与奖励在大开席面板查看，科技在革新树中研究。',
        'hbe_civic.4.desc': '本届圈署委任已经到期，或本府不再满足机构运转、成员身份与役负条件。恢复相关条件后，可按委任决议列示的要求重新申请。',
        'hbe_civic_audit.desc': '役负与工法整理可通过地方事业项目办理。',
        'hbe_civic_revision.desc': '地方事业统一在地方事业面板筹办。',
    }
    replacements.update({
        'hbe.3.desc': '三年工期已满，掌事者带着领料簿、交接凭据与乡里签押来到府衙。曾经在图上细如一线的渠道和道路，如今已有百姓沿它往来；曾经空着的仓位，也终于能够按册交割。\n\n验收官确认本府完成了所承[Concept(\'hbe_term_service\', \'地方事业\')|e]，交付因此有了新的凭据。各家自然都愿将功劳写得长些，然而明年的维护与下一次续办，才会决定这番投入能留下多久。',
        'hbe_banquet.34.desc': '新修的圈际图册已经送来，谷中代表却指出，一条常用的山路在图上被缩成了不起眼的支线。沿途需修的桥栈与安置的转运人手，因此未列入共同费用。\n\n纸上的远近与行旅实际所费并不总是相同。若愿重勘道路，[Concept(\'hbe_term_service\', \'地方事业\')|e]与驿路的经验便能成为依据；若只据现有图册拨款，被漏下的地方将不得不自行补足缺口。',
        'hbe_civic.5.desc': '征调的文书接连到来，乡里已经很难在田亩、修路与驻守之间安排人手。府臣仍能列出每道命令的理由，却无法解释为何它们合在一起，就应由同一批人无休止地承担。\n\n见证者请求重新议定期限。我们可以用现钱替代部分劳役，也可以暂缓急办；若继续维持旧额，本府的[Concept(\'hbe_term_yiqi\', \'信用\')|e]和阶层支持将一并受损。',
        'hbe_civic.6.desc': '案房把近年的付费、雇价与轮役分别抄列。旧簿中的总数尚能相合，却有一些支出只记承办人，有些征调只记乡名，继任者难以查明同一份责任是否被记了两次。\n\n复核将花费府库和书记的人手，能使未清的分摊得到处理，也为1457年之后的[Concept(\'hbe_term_charter\', \'续约\')|e]留下可循的凭据。',
    })
    for group,index,building,title,_,requirement,trigger in NETWORKS:
        if re.search(r'var:hbe_(?:water|salt|river|roads|grain|tea|valleys)\b',trigger):
            requirement='拥有运转中的本圈机构，或已完成本圈地方事业'
        replacements[f'hbe_network_{group}_{index}_desc'] = f'{title}由本圈机构维持，须满足相关科技、机构运转、役负及卡片所列经营条件。'
        # Replace just the network sentence, preserving unrelated unlocks and caps.
        replacements[f'NETWORK:{group}:{index}'] = f'解锁“{title}”：${building}$正常运转、役负低于70，且{requirement}时生效；条件不满足时暂停。'
    legacy_terms = {'water':'水利经营','salt':'盐业经营','river':'江运经营','roads':'关驿经营','grain':'仓粮经营','tea':'茶马经营','valleys':'山谷经营'}
    replacements['hbe.4.desc']=replacements['hbe.4.desc'].replace('义气',"[Concept('hbe_term_yiqi', '义气')|e]",1)
    replacements['hbe_civic.4.desc']=replacements['hbe_civic.4.desc'].replace('圈署委任',"[Concept('hbe_term_civic_office', '圈署委任')|e]",1)
    total=0
    for path in (out/'main_menu/localization').rglob('hbe*.yml'):
        lines=[]
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            m=re.match(r' (\S+):\s*(".*")\s*$',line)
            if not m:lines.append(line);continue
            key=m[1]
            try:value=json.loads(m[2])
            except ValueError:lines.append(line);continue
            before=value
            for term,label in legacy_terms.items():
                value=re.sub(r"\[Concept\('hbe_term_"+term+r"',\s*'[^']+'\)\|e\]","[Concept('hbe_term_service', '地方事业')|e]",value)
                value=re.sub(r'@hbe_'+term+r'!','',value)
            base=key.removesuffix('.entry')
            if base in replacements:value=replacements[base]
            if key.startswith('hbe_tech_') and key.endswith('_effects'):
                value=re.sub(r'解锁本圈三年(?:\[Concept\([^\]]*\)\|e\]|地方事业)与地方援助资格。\n?', '',value)
                match=re.match(r'hbe_tech_(\w+)_([47])_effects',key)
                if match:
                    sentence=replacements.get('NETWORK:'+match[1]+':'+match[2])
                    if sentence:value=re.sub(r'解锁“[^”]+”：[^\n]+',lambda _:sentence,value)
            if re.fullmatch(r'hbe_tech_\w+(?:_desc|\.desc)(?:\.entry)?',key):
                value=re.sub(r'\n费用[^\n]+研究[^\n]+年[^\n]*','',value)
            if key.endswith('_scenario_desc') or key.startswith(('country_history_','country_description_category_desc_')):
                value=re.sub(r'@hbe_(?:water|salt|river|roads|grain|tea|valleys)!','',value)
                for term,label in legacy_terms.items():
                    value=re.sub(r"\[Concept\('hbe_term_"+term+r"',\s*'[^']+'\)\|e\]","[Concept('hbe_term_service', '地方事业')|e]",value)
                    for old_name,label2 in (('水权储备',label),('盐引信用',label),('江运互保',label),('轮戍履约',label),('义仓储备',label),('商队互保',label),('地方共治',label)):
                        value=value.replace(old_name,label2)
            if key in ('hbe_term_'+t for t in legacy_terms) or key in ('game_concept_hbe_term_'+t for t in legacy_terms):
                term=key.rsplit('_',1)[1];value=legacy_terms[term]
            value=value.replace('近五年完成本圈事业、','').replace('三年分账循环','两年会盟结算')
            if key.startswith(('hbe_service_','hbe_coordinate_')) and '.desc' in key:value='地方事业统一在右下角地方事业面板筹办。'
            if key.startswith(('hbe_role_','hbe_project_pledge','hbe_project_reconsider','hbe_project_subsidize','hbe_audit_accounts')) and '.desc' in key:
                value='请在大开席面板查看本届出资与地方事业贡献，并办理相关操作。'
            if key.endswith('_desc') and '全国同类最多一所' in value:
                value=value.replace('全国同类最多一所','全国同类总等级上限3（含在建），每地点上限1')
            if value!=before:line=' '+key+': '+json.dumps(value,ensure_ascii=False);total+=1
            lines.append(line)
        write_preserving_format(path,'\n'.join(lines)+'\n')
    clarify_booleans(out)
    return total


def clarify_booleans(out):
    """Give every mod-defined boolean one concrete, authoritative description."""
    keys=[]
    for path in (out/'main_menu/common/modifier_type_definitions').glob('hbe*.txt'):
        text=path.read_text(encoding='utf-8-sig')
        keys += [key for key,_,a,b,_ in blocks(text,0) if re.search(r'\bboolean\s*=\s*yes',text[a:b])]
    fixed={
        'hbe_can_cross_circle_industry': ('可在本圈之外的直属领土建造对应产业建筑，生产当地特色产物。须先在目标圈拥有土地，采用乡社议办，义气达到60，再支付金币和10点义气办理准入；各建筑仍受当地地域和数量限制。', 'Allows regional industry buildings and specialty production outside the home circle. Own land in that circle, use communal labor policy, reach 60 fraternity, then pay the listed gold and 10 fraternity to establish access. Local geography and building caps still apply.'),
        'hbe_af_allow_large_investment': ('地方事业可选择大量投入，支付更多金币与役负，获得该档列示的收益；工期以卡片为准。切换投入档次会同时更新两张候选卡。', 'Enables the large-investment tier in local affairs. Pay its listed gold and labor burden for its listed rewards and duration. Switching tiers updates both candidate cards.'),
        'hbe_af_allow_local_refresh': ('空闲时可点击地方事业卡右上角的圆形按钮，更换这张候选卡。每两年一次；全国候选和正在施工的项目不变。', 'While idle, use the round button at the upper right of the local project card to replace that offer. Available once every two years; the national offer and active construction stay unchanged.'),
        'hbe_af_allow_guild_projects': ('地方事业可抽到整理工法、准备工料、验货定样、招收学徒、扩建作坊和试作新法六类项目。正常运转的特色产业机构可使这些项目役负减少20%；本地项目须由目标地点的机构承办。', 'Adds six guild project roles to local affairs: craft records, materials, quality standards, apprentices, workshops and trial production. Operating specialty institutions reduce their labor burden by 20%; local projects require an institution at the target location.'),
        'hbe_elector_can_participate_in_parliament': ('允许本组织选侯参与议会事务；具体可用操作仍由组织规则和议会条件决定。', 'Allows this organization’s electors to participate in parliament, subject to the organization rules and parliament requirements.'),
    }
    goods={'hbe_shu_embroidery':('蜀绣','Shu embroidery'),'hbe_well_salt':('井盐','well salt'),'hbe_shu_paper':('蜀纸','Shu paper'),'hbe_border_tea':('边茶','border tea')}
    for good,(cn,en) in goods.items():
        fixed[good+'_used_for_minting']=(f'允许把{cn}用于铸币；实际铸币收入及通胀影响仍按原版规则计算。',f'Allows {en} to be used for minting. Minting income and inflation follow the base-game rules.')
        fixed['ban_exports_of_'+good]=(f'禁止从本国市场出口{cn}。',f'Bans exports of {en} from the country’s markets.')
        fixed['ban_imports_of_'+good]=(f'禁止向本国市场进口{cn}。',f'Bans imports of {en} into the country’s markets.')
        fixed['can_extract_'+good]=(f'允许在具备{cn}原料产地的地点开采该货物；不会凭空增加产地，也不替代特色建筑和生产方式的解锁要求。',f'Allows extraction where a location already has {en} as its raw material. Does not create deposits or unlock specialty buildings and production methods.')
    assert set(keys)<=fixed.keys(),set(keys)-fixed.keys()
    for lang in ('simp_chinese','english','traditional_chinese'):
        directory=out/'main_menu/localization'/lang
        for path in directory.glob('hbe*.yml'):
            text=path.read_text(encoding='utf-8-sig')
            text=re.sub(r'(?m)^ (?:'+'|'.join(re.escape('MODIFIER_TYPE_DESC_'+key) for key in keys)+r'):.*\n?', '',text)
            write_preserving_format(path,text)
        directory.mkdir(parents=True, exist_ok=True)
        path=directory/f'hbe_permission_descriptions_l_{lang}.yml'
        text='l_'+lang+':\n'+'\n'.join(' MODIFIER_TYPE_DESC_'+key+': '+json.dumps(fixed[key][lang=='english'],ensure_ascii=False) for key in sorted(keys))+'\n'
        if path.exists():write_preserving_format(path,text)
        else:path.write_text(text,encoding='utf-8-sig')
