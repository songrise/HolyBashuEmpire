"""Native EU5 game concepts and contextual, recursively hoverable guide links."""
import json,re

SOURCES={
'dujiangyan':('都江堰与青城山','https://whc.unesco.org/en/list/1001','联合国教科文组织世界遗产中心','战国时期兴建；历代改扩修；鱼嘴、飞沙堰与宝瓶口共同分水排沙。'),
'shujin':('《蜀锦谱》','https://ctext.org/wiki.pl?chapter=736601&if=gb&remap=gb','中国哲学书电子化计划，古籍正文','记载成都锦院及宋代茶马用锦；使用文献所载背景，不安排作者在特定开局年份出场。'),
'salt':('卓筒井遗址','https://zhuanti.mct.gov.cn/sc_detail/302.html','文化和旅游部','北宋庆历年间的绳式顿钻取卤制盐遗存。'),
'tea':('雅州茶马贸易','https://www.yaan.gov.cn/gongkai/show/04025851f3f4a16fb2c81c0dcf99fa03.html','雅安市人民政府','宋代雅州、黎州茶马贸易与名山茶；不用后来的清代打箭炉制度解释1337年。'),
'shudao':('元代金牛道走向','https://nyncj.cngy.gov.cn/new/show/20240814093312628.html','广元市农业农村局','汉中、七盘关、朝天、广元与昭化等路径；沿线故事中的轮役争端为架空。'),
'jianmen':('剑门古蜀道','https://swglj.cngy.gov.cn/mshow/39cee7646a844d6485346ab591e25a44.html','广元市文化广电旅游局','蜀道交通及剑门关；不采信页面中的唯一通道等绝对化说法。'),
'diaoyu':('钓鱼城遗址','https://whlyw.cq.gov.cn/zjwl/yzq/cqwlzy/zqwwzy/202405/t20240507_13182059.html','重庆市文化和旅游发展委员会','南宋山城防御与宋元战争背景；不复述蒙哥死因的争议细节。'),
'qiong':('宋代四川省油灯','https://www.gzszx.gov.cn/wstd/wsmb/35613.shtml','贵州省政协','邛窑所制省油灯，晚唐开始生产、宋代流行。'),
'sansu':('眉州三苏文化','https://www.sc.gov.cn/10462/10464/10465/10595/2019/4/26/350aec3ade6f490f82bac0289c843c8b.shtml','四川省人民政府','苏洵、苏轼、苏辙与眉山；不在1337年设置洪武以后重建的祠宇。'),
'wenweng':('文翁兴学','https://www.luan.gov.cn/zjla/lasq/rwp/2638491.html','六安市人民政府','西汉蜀郡守文翁兴学；不引用出生年份和连续办学等有争议的附加断言。'),
'river':('川江号子与水运环境','https://ghzrzyj.cq.gov.cn/bsfw_186/dtfw/mzyt/202301/t20230106_11466437_wap.html','重庆市规划和自然资源局','川江水急滩多、劳动号子协调船工；不将近代机械绞滩站置入中世纪。')}

# key, display label, aliases, concise actionable native hover text, optional painted icon.
GUIDES=[
('guoqi','锅气',[],'#T 共同信用与公款余力#!\n帝国共有，范围0–100；各府看到的是同一份数值。成功的分账项目、地方课题和阶段验收可增加锅气；失败工程会损失锅气。\n\n皇帝茶议、争端调停和百年章程会消耗它。提出章程需至少20点。它不是粮食库存，也不自动兑换金币。','hbe_guoqi'),
 ('yiqi','义气',[],'#T 本国的履约信誉#!\n每国独立，范围0—100，开局40。完成课题、地方事业交付与部分事件会增加；违约与部分自行其是的处理会降低。\n\n它用于部分政治、产业合作与跨圈经营资格，具体增减与门槛以行动卡片列示为准。',None),
('dispute','争席度',[],'#T 会盟内的共同争端#!\n局势共有，范围0–100，开局15。未结清项目、违约与部分争端选择会提高；成功结算、公开公账和调停可以降低。\n\n本届第三十六个月结算时必须低于75，即使三项交付齐全也一样。达到75会触发争端事件，该事件有五年间隔。','hbe_dispute'),
('tianfu','天府之国',['天府加成'],'域内每个地块永久获得粮食产出+10%、本地建造速度+10%。同一地块不重复叠加；它随帝国成员对域内地块的治理维持，域外非成员接掌后移除。\n\n与百年章程和限时工程收益分别计算，无须每届重新申请。',None),
('isolation','自治盟约',['自治敕书'],'本模组的架空自治背景与外交规则：会盟依共同盐粮交割保持区域自治。帝国境内与域外之间的宣战和战争召集受边界门槛限制；内部诸侯战争和本地叛乱仍可发生。\n\n拒绝某届工程、发生争席危机或未通过百年章程，都不会使盟约因计时而失效。',None),
 ('circle','帝国圈',['七圈'],'七个圈级协作组织，各自关联地方课题与产业建筑。开局每圈推一席选侯。\n\n章程议决时每圈只提供一份授权，须先取得该圈原首府席位的严格过半支持；总计至少四圈授权才能通过。',None),
('elector','选侯',['七席选侯'],'皇帝选举的七个投票席位，开局每圈一席，走原生组织选举界面。选举须取得严格多数；经营实力与诸侯关系会影响AI选择。\n\n它与百年章程的固定代表席位是两套规则：不是只有选侯才能参与章程授权。',None),
('research','地方课题',['地区研究'],'通过研究决议资助，付费后等待该项研究的年数，完成时由月度维护结算。每国同时只能研究一项，须满足年代与前置条件。\n\n共64项：共同知识8项，各圈8项。研究结果保存在国家上，不随统治者更替丢失；它们仍以决议作为入口。',None),
('specialization','互斥专精',['课题路线'],'每圈的第三项与第六项课题开启两条互斥路线；研究其中一项后，另一项不能再开始。后续节点沿各自前置推进。\n\n第三、四、五阶段的地区验收接受任一路线的对应成熟节点，无须两条路线同时完成。',None),
 ('service','地方事业',['地方事业','地方事业'],'在地方事业面板选择全国或地方事业，确定投入档次后自动施工。费用、工期与成果由卡片列示；完工发放实际成果并计入本届贡献。\n\n全国项目与地方事业各有候选；空闲时可更换地方候选，每两年一次。',None),
('mission','阶段验收',['地区验收'],'每圈五阶段，最早分别在1337、1352、1372、1397、1437年开放。须完成前一阶段、对应课题并持有至少10点本圈储备。\n\n消耗10点储备与2/4/6/8/10金，增加5点义气、2点锅气及2点声望。各阶段只能验收一次。',None),
('round','分账会',['本届分账会'],'局势的36个月循环。前6个月接受本国出资或合同，第12个月核付承诺，第36个月检查三个专业环节并结算。\n\n成功须三个环节各至少一次有效交付且争席度低于75。下一届会清除本届参加状态，保留长期个人履约与成功项目总数。',None),
('commitment','承诺期',['前六个月'],'每届第0至第5个月可以出资、认账或签专业合同。每国每届只参加一种；暂缓后可在期内撤回意见再参加。\n\n皇帝仅在前三个月、尚无专业承接时改选主工程。过了承诺期，皇帝补缺仍有自己的时间门槛。',None),
('funding','出资',['实际出资'],'本届承诺期内支付3金，立即获得1份个人履约、2点义气与1点锅气。它提供公款，不补齐主工程的专业环节。\n\n同届不能再认账或承接专业合同；共同收益仍需本届项目最终成功。',None),
('pledge','认账',['付款承诺'],'在承诺期签下4金承诺，第12个月检查国库并实际付款。付清后获得1份个人履约、3点义气与1点锅气。\n\n届时不足4金不会强扣国库，改为违约：义气-8、争席度+5，本次不能算作有效交付。',None),
 ('delivery','项目交付',['地区交付'],'项目完工即完成一次交付，实际成果与工期以卡片列示。交付计入本届会盟贡献，并可在会盟成员行查看。\n\n交付不消耗额外储备；同届重复办理按卡片费用正常结算。',None),
('contribution','本届贡献',['履约记录'],'国家长期累计的履约次数，开局0，不随每届清账或领主更替归零。真实出资计1，半年专业交付计2，府州试办也可增加。\n\n它用于记录本国贡献，不等同于局势的成功工程总数；仅有个人记录不能替代章程所需的30次共同成功。',None),
('saltproject','盐船共账',[],'三项专业环节：川南盐引承销、川东江船转运、川中公账审计。各环节至少一次有效交付且争席度低于75，届末才成功。\n\n成都水粮担保、现金出资和付款承诺均不代替这三项。皇帝补缺可在限定时间内补一个缺失环节。',None),
('teaproject','茶马过蜀道',[],'三项专业环节：川西茶马采办、川北驿路轮戍、川西南山谷互市。每项至少一次交付且争席度低于75，届末才成功。\n\n会盟每届默认与盐船共账轮换；皇帝可在早期满足条件时改选。现金出资不能代替专业交付。',None),
('subsidy','皇帝补缺',['皇帝垫账'],'本届第12至第29个月，皇帝可付10金补一个缺失的专业环节；依第一、第二、第三项的顺序补缺。每届限一次。\n\n它不能单次替代三个环节，也不降低争席度。是否能够成功仍由第36个月统一检查。',None),
('audit','公开公账',['三金核账'],'支付3金，争席度-4、义气+2，每两年可执行一次。它用于缓和共有争端，不直接增加成功工程，也不填补专业交付。',None),
('chapter','章程阶段',['第五阶段'],'局势按时间与已成功项目共同推进：1352年且3次、1372年且8次、1397年且14次、1422年且22次，分别进入第二至第五阶段。\n\n仅等待年份不会自动推进。第五阶段也仍须等到1437年、成功30次，并满足其他提案条件，才能议百年章程。',None),
('charter','百年章程',[],'最早1437年，局势第五阶段且共同成功项目至少30次。皇帝立场须与提案一致，付5金、消耗20锅气，启动六个月议决。\n\n每圈原首府席位严格过半赞成，七圈至少四圈授权才能通过。失败后五年可重提；通过后仍继续循环工程。',None),
('seat','固定代表席位',['固定席位','原首府席位'],'章程议决固定使用开局36个原府州首府。首府的当前帝国成员领主代表该席；一国整合多个首府时，其表态用于这些席位。\n\n分封不会新增席位；非成员持有的首府不计赞成，但圈内通过仍须越过原有席位总数的一半。',None),
('common','共建派',['共建'],'倾向由皇帝主持共同财政与公共事业。各派都能经营、交付和竞选；五年内只能改换一次立场，地图显示为红。\n\n共建派皇帝可提出一锅巴蜀章程，但仍需各圈正式授权，选择立场本身不会直接颁行章程。',None),
('divided','兴业派',['兴业'],'重视府州自治与圈级协作。地图显示为蓝，立场改换有五年间隔。\n\n对应万国茶会章程。它与所有成员一样须参与实际出资或交付才能取得成功工程的参与者收益，并不自动免去合同责任。',None),
('ledger','账房派',['账房立场'],'倾向以明确合同、核验与履约记录协调诸府。地图显示为黄，立场改换有五年间隔。\n\n对应契约共治章程。仅选此派不会自动得到返还，仍须章程通过与本届真实交付后成功结算。',None),
('debt','盐债',[],'川南盐引贷款的独立债务数值。成熟盐引课题完成后，发行一次取得15金、增加10盐债，五年间隔，债务上限30。\n\n有欠债时每年扣1金利息。支付10金可归还10盐债并恢复信用。盐债与义气分别记账；贷款不改变自治盟约。',None),
('charter_common','一锅巴蜀',[],'共建章程通过后，域内成员地块本地建造速度额外+5%。皇帝每年承担1金维护；不足支付时增加5争席度。\n\n它叠加在天府之国之上，亦不终止两年会盟结算。',None),
('charter_divided','万国茶会',[],'兴业章程通过后，域内成员地块粮食产出额外+5%；地区公共事业交付追加2声望。\n\n它不会免费提供项目经费，也不取消地方事业的课题与钱粮要求。',None),
('charter_contract','契约共治',['各吃各的，账照样交'],'契约章程通过后，域内成员地块粮食产出与本地建造速度各额外+2.5%。本届真实出资或交付且共同项目成功者，另返还1金。\n\n返还来自成功结算，认账未付款或未参加本届者不获返还。',None)]

# Broad narrative words must not inherit a single decision's numeric cost.
PRECISE={'research':('地方课题',['地区研究','课题']),
         'guoqi':('锅气',['共同信用']),
         'isolation':('自治盟约',['自治敕书','旧敕书']),
         'funding':('现金出资',['本届出资','出资三金']),
         'pledge':('付款承诺',['分账会认账','先认账','先认四金']),
         'charter_contract':('契约共治',['共同契约章程','各吃各的，账照样交'])}
GUIDES=[(key,*PRECISE.get(key,(name,aliases)),desc,icon) for key,name,aliases,desc,icon in GUIDES]
GUIDES += [
 ('regional','地方事业交付',['地方事业','本圈交付'],'地方事业以项目办理：在右下角面板选择全国或地方事业，投入金币与役负，按期完工后发放卡片列示的实际成果，并计入本届贡献。\n\n项目分为民政、商贸、工程、聚落四类，各有少量与大量两档；资格、费用与工期以卡片为准。',None),
('contract','共同契约',['共同合同','旧约','旧契','契书'],'共同事务须同时有明确责任、实际交割和各方认可的凭据。地方公共事业、府州试办和本届专业交付分别按各自规则验收。\n\n叙事中的契约用于表达地方权利与承诺；支付金额、等待时间和效果以所选行动的条件与结果提示为准。',None),
('trial','府州试办',['出资试办','资助试办','资助这项试办','出资试行'],'每个原府州有一次专属试办事件，通常在1338–1343年间到来。支付2金可增加3义气、1份个人履约和1锅气，并给域内所辖地块三年的工程收益。\n\n此记录长期保留，但不代替本届主工程的三个专业环节。守旧选择会降低义气并增加争席度。',None)]

GUIDES += [
('success','成功工程',['共同项目'],'两类主工程在第三十六个月结算成功时，局势的共同成功总数增加1。三个专业环节各至少一次交付、争席度低于75，缺一不可。\n\n参与且真实履约者得到三年本地收益，锅气+5、争席度-5。章程阶段及百年章程使用此总数，府州试办和单次地方交付不单独计入。',None),
('alliance','巴蜀会盟',['会盟'],'神圣巴蜀帝国组织及七圈协作的共同体。开局36个府州诸侯；全部帝国成员在1337年10月的大开席启动后自动参加。\n\n成员可以选择立场、参与循环工程、经营地方事业并授权章程。皇帝主持议事，选侯推举帝位；天府之国与自治盟约维持域内治理。',None)]

HISTORY=[
('dujiangyan','都江堰',['李冰'],'#T 历史背景#!\n都江堰始建于战国时期，利用地势与水流分水、排沙和灌溉；唐宋元明均有改扩修。鱼嘴、飞沙堰与宝瓶口是其核心构件。\n\n它与青城山共同构成平原水利和山门文化的历史背景。水权与岁修需要受益各地持续合作。','dujiangyan'),
('qingcheng','青城山',[],'#T 历史背景#!\n青城山与早期道教传统紧密相连，与成都平原水利景观共同形成重要历史文化环境。\n\n山门、地方文教与乡里见证，可由这些既有传统取得声望。','dujiangyan'),
('shujin','蜀锦',['锦院'],'#T 历史背景#!\n成都织锦长期为蜀地著名产业。《蜀锦谱》记载锦院与宋代茶马用锦，显示织造、官府采办和互市之间的联系。\n\n作坊分工、采购与交割，因而同时牵动匠户和地方府库。','shujin'),
('salt','卓筒井',[],'#T 历史背景#!\n北宋庆历年间，蜀地已有以绳式顿钻取得深处卤水的卓筒井技术。井盐的生产需要钻井、取卤与煎盐等环节配合。\n\n从井灶到承运，再到盐引交割，各环节须使实物与担保相互衔接。','salt'),
('tea','雅州茶马司',['茶马司'],'#T 历史背景#!\n宋代雅州、黎州是西南茶马贸易的重要地方，名山茶用于以茶易马，官府设置机构组织交易。\n\n采办、运送与互市各有承担者，统一凭据能使不同地方承认同一份交割。','tea'),
('shudao','蜀道',['金牛道'],'#T 历史背景#!\n连接关中、汉中与蜀地的道路体系长期承担行旅、军需与驿传。元代金牛道经七盘关、朝天与广元等处进入蜀地。\n\n险路与关驿需要接力维护，人马、粮料和交接凭据缺一不可。','shudao'),
('jianmen','剑门关',[],'#T 历史背景#!\n剑门关位于蜀道要段，险峻地势使其长期具有守备与交通价值。\n\n地势之险可以助守，关役仍须依靠真实的人马、粮料与沿路维护。','jianmen'),
('diaoyu','钓鱼城',[],'#T 历史背景#!\n合州钓鱼城是南宋山城防御体系的重要节点，宋元攻防持续至十三世纪后期。其守备兼顾山城、水路与屯粮。\n\n这段旧事为合州的跨水口协作与公共粮政提供历史记忆。','diaoyu'),
('qiong','邛窑',['省油灯'],'#T 历史背景#!\n邛窑所制省油灯在晚唐出现、宋代流行，是蜀地器用与工匠经验的一例。\n\n匠师的成法既可由师徒传习，也可借实物、图样和验收记录传给更多作坊。','qiong'),
('sansu','三苏',[],'#T 历史背景#!\n北宋苏洵、苏轼、苏辙与眉州文脉密切相连，其文章成为后世蜀地士人可以援引的传统。\n\n议疏能使治事主张传得更远，具体的钱粮与责任仍须另有清楚的记录。','sansu'),
('wenweng','文翁石室',['文翁'],'#T 历史背景#!\n西汉蜀郡守文翁兴学、培养郡县人才，成为成都官学传统的重要历史来源。\n\n地方课题与官学讲会借这一文脉，为匠师经验和治事簿册寻找共同的表达。','wenweng'),
('river','川江',[],'#T 历史背景#!\n川江水急滩多，航运依靠熟悉水程的船工及沿途协作。劳动号子用于协调动作，险滩与水位也影响实际交割。\n\n转运与护航的价值应由经过的水程、人手和到货记录相互核验。','river')]

def build_player_guides(root,loc,L,put):
    definitions=[];terms=[];lookup={};icon_by_key={}
    for key,name,aliases,desc,icon in GUIDES:
        if key=='contract':aliases=aliases+['契约','旧责']
        cid='hbe_term_'+key
        definitions.append(cid+' = { '+(f'texture = "text_icons/{icon}" ' if icon else '')+'}')
        L('game_concept_'+cid,name);L('game_concept_'+cid+'_desc',desc)
        terms.append(dict(key=cid,name=name,kind='mechanic',description=desc))
        if icon:icon_by_key[cid]=icon
        for label in [name]+aliases:lookup[label]=cid
    for key,name,aliases,desc,source in HISTORY:
        cid='hbe_history_'+key;definitions.append(cid+' = { }')
        L('game_concept_'+cid,name);L('game_concept_'+cid+'_desc',desc)
        terms.append(dict(key=cid,name=name,kind='history',description=desc,source=source))
        for label in [name]+aliases:lookup[label]=cid
    put('main_menu/common/game_concepts/hbe_concepts.txt','\n'.join(definitions))
    pattern=re.compile('|'.join(re.escape(s) for s in sorted(lookup,key=len,reverse=True)))
    def enrich(text,own=None):
        def replacement(match):
            label=match[0];cid=lookup[label]
            if cid==own:return label
            icon=('@'+icon_by_key[cid]+'!') if cid in icon_by_key else ''
            return icon+f"[Concept('{cid}', '{label}')|e]"
        return ''.join(chunk if chunk.startswith('[') else pattern.sub(replacement,chunk) for chunk in re.split(r'(\[[^\]]*\])',text))
    # Concept display names and event titles stay plain. Existing data functions stay intact.
    linked=0
    for key,value in list(loc.items()):
        if key.startswith('game_concept_') and not key.endswith('_desc'):continue
        if key.endswith('.title'):continue
        own=key.removeprefix('game_concept_').removesuffix('_desc') if key.startswith('game_concept_') else None
        updated=enrich(value,own);linked+=updated!=value;loc[key]=updated
    # Give generic generated variable labels a concrete meaning in runtime effect tooltips.
    accurate={'hbe_delivery_role':'本届交付环节','hbe_delivery_kind':'本届交付工程类型','hbe_banquet_flavor_cooldown':'地区及代际事件间隔','hbe_project_timer':'专业交付验收计时','hbe_audit_cooldown':'公开公账间隔','hbe_stance_cooldown':'立场改换间隔','hbe_ballot_cooldown':'章程重提间隔','hbe_crisis_cooldown':'争端事件间隔'}
    for key,value in accurate.items():loc[key]=enrich(value)
    (root/'data/player_guides_v01.json').write_text(json.dumps(dict(concepts=terms,sources=SOURCES,linked_localization_entries=linked),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    doc=['# 巴蜀机制与历史名词指南','',f'本版包含 {len(GUIDES)} 个机制概念与 {len(HISTORY)} 个历史概念。事件、决议、局势说明里的着色术语可悬停查阅；仍使用 EU5 原生提示窗与概念系统。','',
    '事件以1337年以前的地方背景和此后架空会盟治理为题材。诸侯、七圈组织、局势合同与章程不是真实历史制度；公开史料仅用于地理、生产和既有历史传统。','']
    for term in terms:
        doc+=['## '+term['name'],'',term['description'].replace('#T ','').replace('#!',''),'']
        if term['kind']=='history':
            title,url,author,fact=SOURCES[term['source']];doc+=[f'史料：[{author}：{title}]({url})。','']
    doc+=['## 出处核对说明','']
    for title,url,author,fact in SOURCES.values():doc+=[f'- [{author}：{title}]({url}) — {fact}']
    (root/'docs/player_guide_v01.md').write_text('\n'.join(doc)+'\n',encoding='utf-8')
    return dict(mechanic_concepts=len(GUIDES),history_concepts=len(HISTORY),linked_localization_entries=linked,source_registry='data/player_guides_v01.json')
