"""Native advances, country content registration, biographies and decision prose.

Existing timed research is retained only to settle pending v0.1 saves. New
research uses the native research queue; the monthly bridge grants each legacy
variable and its completion reward exactly once. DHE catalogue registration has
zero autonomous chance, so existing event dispatch and cooldowns stay authoritative.
"""
import hashlib,json,re
from build_support import save_png
from PIL import Image,ImageDraw,ImageFont
from pdxscript import blocks,apply_edits
from build_flags import save_dds
from build_icon_assets import fit

TECH_PROSE={
'common':[
'乡里的借券与府库的收支各有写法，一项事业往往留下几本相互矛盾的账。我们应使出资、交付与验收各有凭据，让继任者能够接续前人的责任。',
'山道隔开了市集，也使同名的斗斛有了不同的分量。若盐粮仍依各府旧尺交割，合作便免不了在秤前争执；共同认可的度量，是诸侯彼此信任的第一步。',
'一府可以修补自己的渠岸，却难以独力承担贯通数圈的工程。应将勘查、备料和验收分别登记，使主持者的名望建立在实际交付之上。',
'织机、井具和桥栈的诀窍，多藏在作坊口授的经验里。让匠人带着器样往来各府，彼此观摩而保有本业，远比将所有技艺锁在一处更有益于巴蜀。',
'一位巧匠的手艺未必能够传至下一代，行会的旧规也未必容得下后来者。我们应为学徒、师傅与主持采办的人留下可循的传习章程。',
'来自井灶、渠田与山路的经验，需要不同的器具，也需要共同的语言。若各圈愿意共同供养讲习之所，远道而来的匠人便不再只能在客舍中交换口传。',
'驿卒所记的里程，往往没有写下暴雨后的断栈与渡口的候船之苦。我们将派人重勘道路，把关隘、歇脚处与备料地点一并录入图册。',
'府界上的几幅旧图各自完整，拼在一起却遗漏了跨圈的桥栈。我们需要一份可供共同治事的总图，使主持工程的人看见通路，也看见沿途的责任。'],
'chengdu_plain':[
'渠水入田并不意味着每一乡都能及时受水。岁修所需的木石、人手和开口顺序，应由实际承担渠务的人共同议定，免使丰年留下的争执在旱年加倍。',
'蜀锦的声名来自织造，也来自染料、丝线与熟练人手的相互配合。锦户若能按工序相助，府库便可在采办时分清谁交付何物，而不只追求一匹成锦。',
'每一处渠口都有旧例，却未必有能够互相核对的记载。将水次与岁修之责写入同一簿册，才可使上游的便利与下游的生计一同进入公议。',
'相邻的沟渠并非各自孤立，修好一段也可能将水患推向另一乡。我们应以整条通水脉络安排备料与验收，让各府能够共同承担受益之地的维护。',
'平原的丰收若只留在各府私库，荒岁时仍会有人求粮无门。把入仓、出贷与补还的凭据相互核验，天府的富庶方能成为各乡能够依靠的常备。',
'蜀中兴学的旧事使人敬重书卷，但渠旁与作坊同样需要懂得治事的人。让讲会接纳实际主持地方事业者，使书院中的议论能够回到田亩与街市。',
'使者在堂上坐定之前，常已为议题的先后与签押的格式争论许久。我们应规定呈议、质问与记录的次序，给不同府州留下明白作答的机会。',
'巴蜀的公议不能只靠一代主持者的声望维系。将官学、议事与旧约的保存相联系，使后来的诸侯仍能查阅当初为何承诺，又应如何履约。'],
'southern_salt_wine':[
'井口的卤水、灶上的燃料与运盐的脚钱分由不同人掌握，一笔总价常掩去了各自承担的劳苦。我们应从井灶公账入手，令成本与交付都有可查的来处。',
'盐与酒都需器具、燃料和可靠的运送，却有不同的工序与候时。联合采办可以减少相互挤占，前提是商户愿意将所需之物与到货之期写得明白。',
'蜀中井盐的旧技并非一成不变，井架、绳具与汲卤办法仍有改进余地。投入器具和查验人手，既关乎产出，也关乎井户能否平安度过下一次作业。',
'一张盐引写下的是未来交付，而库吏眼前需要的却是今日的钱。若以盐业收益作保，借款、利息与偿还之期便须同时公开，免使担保变成无尽的拖欠。',
'各井各灶都能向邻府承诺供盐，却难以在丰歉之间承担共同责任。让总号协调有限的担保与交付，使它的信用始终有真实经营可以支撑。',
'酒坊的好坏不只在窖中，也在粮料、器皿与守时的工匠。分清酿造、储存与交付的责任，可以使宴席所需不再挤占其他地方事业的备料。',
'诸侯的会盟离不开待客，负责采办的人却常在散席后才收到催账的使者。我们应先议数量、价钱与交期，再以契约确认谁承担临时增添的费用。',
'一次盛会能使承办者扬名，也能留下多年未清的旧账。将席面、运送和核账分别验收，才可使庆典的荣誉与本府的经营相互成全。'],
'eastern_river':[
'船只到岸之后，货物仍要经过卸载、储放和再次装运。川江两岸的转运之所若无共同规矩，一段顺畅的水程也会在码头化作长久的等候。',
'险滩前的船工必须同声同力，岸上的出资者却未必懂得这份配合。把纤夫、船户与转运人手的责任写进互助约定，是可靠江运的根本。',
'每一道关卡都有自己的旧额，往来的商旅却承受着累积的盘查。各府若能认可彼此的券据，就可以减少重复征索，也让维护通路的费用更清楚。',
'一条船的损失可以使小商户多年经营付诸流水，单靠邻里的情面难以承担。互保需要事先认缴、出险查验与有限赔付，而非事故之后才临时求援。',
'江运通畅使盐粮与器物得以往来，所得却散在各段岸口。我们应将通行与共同维护写入长约，使上下游的承诺不会随一次换主而消失。',
'崖岸为守备提供便利，也限制了粮秣与人手的调集。依山筑垒之时，应一并察看取水、仓储和退守之路，免使险地成为困住守军的牢笼。',
'江面上的巡察与岸上的驻守各有职责，若互不通报，敌情与误报同样容易沿江传开。建立水陆交接的办法，才能使守备跟得上往来的船只。',
'山城的可靠不在某一段高墙，而在关口、岸仓与援兵能够彼此照应。将各处守备纳入同一调度，使保护通路成为诸侯共同维护的事业。'],
'northern_shudao':[
'蜀道的艰险既在山势，也在风雨之后无人查验的旧栈。勘绘须记录落脚处、木石来源与易损之段，不能只把两座城池之间画上一道直线。',
'驿站与堡垒各守一处，却共同依赖沿路送来的文书与粮料。我们应规定接递、候援与报损的次序，使路上的消息不再止于府界。',
'关门可以阻住来敌，也可能阻住本府急需的粮秣。守备的章程应同时安排驻守与通行，令山关的险固建立在能够长期维持的供给上。',
'轮戍之约最难处，在于当值之府是否真的送来了足额人手。把交接、补缺与逾期责任写明，才可避免诸侯在危急时又争论谁应先行。',
'一处山关失去供给，会使邻近的关堡同样陷入困境。总镇应先协调援粮与轮替，再议统摄之权，使共同防务得到各府实际承认。',
'商旅需要能够说明去向的券据，关市也需要维持驿路的经费。通行之券若能沿途核验，府州便可减少重征，也更易分辨无理盘索。',
'文书走得快，并不代表消息传得明白。不同驿站应保有一致的交接记录，让下一位收文者知道何时发出、由谁承递，又在何处耽搁。',
'驿传关系到征调、会盟与日常采办，不能只在战事紧急时才受重视。建立共同保管的程册，使诸侯的命令能够沿路送达，也能沿路追究责任。'],
'central_hills':[
'丘陵间的田亩依靠各自的塘堰，雨水稍有不同，邻乡便可能一丰一歉。整理坡田与水塘的维护办法，可以使日常蓄水不再只凭一家之力。',
'市集的往来比府库的账册更为频繁，口头约定却经不起多人转手。明确交割的地点、日期与见证人，是将地方经营纳入共同信用的起点。',
'仓粮集中一处便于掌管，却未必能及时送到远乡。分仓赈贷需要各乡保管、统一核账，使荒岁中的借粮能够到达真正需要的人手中。',
'借出的粮食既要救急，也要留有来年补还的办法。乡社若能共同见证借贷与歉收，府库便不必在宽纵旧欠和逼迫穷户之间反复摇摆。',
'各乡的义仓都有善举，也都有难以对外查明的旧账。联社应将入仓、赈借与回补相互核对，使相邻府州能够放心调剂有限的储备。',
'契约能够写下承诺，却还需要有人证明签押与交割。让见证者承担查验之责，可以减少权势之家以一句否认推翻乡民多年经营的风险。',
'票据在不同府州之间转手，真正应还之人有时已经难以辨认。清算应循券追查交付，明确受让与偿付的关系，使信用不至于脱离实际经营。',
'诸侯公信来自接受查验，而非仅在券面上盖下显赫的印。会馆若能保存争议与裁定的凭据，就可让今日受理的纠纷成为来日能够引用的规矩。'],
'western_tea_horse':[
'茶与马的交换跨越不同山地和生活习惯，双方对品质与价钱也各有判断。集市需要可靠的秤量和见证，使远来的商队愿意在此完成交割。',
'图册可以记下山口，却不能替代熟知季节与道路的向导。把带路、候宿与报险的责任议定，可以使远途的采办不再依赖临时寻找的熟人。',
'商队走出本府之后仍要依靠沿途的协助，一纸承诺不足以抵挡事故。互保应确认实际同行的人与货物，再议有限的救助与损失分担。',
'山路穿过不同府州，维护者与使用者未必是同一群人。通路会约应安排备料、候援与通行，不应只把所有费用都推给最远的关口。',
'茶马往来要有可信的交割之所，也要有能够持续维护的路程。公所的职责是保存券据、协调事故与受理争议，使远途合作不随掌事者更替而断绝。',
'山门对行旅的接济既是善举，也需要田产、人手与实际物资。将施济的责任与使用分明登记，才可使过路者的需求与地方的负担相互体谅。',
'跨地纠纷最难之处，往往是双方只认可自己的见证。调停应给不同乡里的代表作答之机，使裁定建立在愿意共同接受的程序之上。',
'诸山之间的公议必须承认不同旧俗，也须留下可以共同履行的约定。把互市、施济与调停汇成可查的章程，使各方在保有旧权时仍能维护通路。'],
'southwestern_valleys':[
'山谷中的集市规模虽小，却连接着不同乡寨的日常所需。让交割、歇脚与巡察有固定的安排，是使地方往来免受猜疑与临时征索侵扰的第一步。',
'一道府令未必能够说明各谷口的旧权与劳役。地方盟约须由实际承担维护的人共同签认，才可使主印之外的承诺同样为诸侯所知。',
'近路可以省下脚程，也可能使沿途的桥栈承受更多劳苦。换市应先查明使用与维护的关系，再议新的交割地点，免将便利建立在旁人的无偿付出上。',
'商盟的互保离不开谷口的见证，远处的总账难以察看每一次实际交付。把报险与赔补交由相互认可的人查验，可以使小商户也愿意加入共同经营。',
'分散的谷市各有长处，也有无法独力承担的缺口。商盟应协调有限的采办与维护，使各乡在参与共同事业时仍保有自己的经营与旧例。',
'山寨之间可以相互望见，却未必能够及时送出求援的消息。守望之约应包括报信、候援与避难的办法，而不是只约定危急时的一句相助。',
'驻防带来守备，也带来粮料与驻地的负担。将当值期限、供给与旧权写进议约，才能使外来的援守得到实际受其影响的乡寨认可。',
'共保盟府的权威应来自守约与受理争议，而非一味收走谷中的旧权。把驻守、互市与地方见证合在可查的盟约之内，才可能获得长久的支持。']}

BIOGRAPHIES={
'成都':'锦官城的织机与平原的渠田，使成都在巴蜀诸府之中享有声望。都江堰留下的治水传统、蜀锦的经营与文翁兴学的旧事，提供了不同的治国道路。\n\n如今本府掌握平原圈的选侯席位，也主持帝国最初的公议。邻府认可成都的名望，却未必愿意长期承担由成都决定的费用。皇位可以带来主持之权；能否使渠旁的人同样受益，才决定这种权威能维持多久。',
'汉州':'汉州居于平原北部，受水的田亩与连接邻府的通路同样重要。城中的库吏关注交割，乡里的掌事者则关心何时开渠、何处备料，两者未必总能在同一本账上作答。\n\n成都近在一旁，给本府带来市场与议事的便利，也使汉州必须争取自己的声音。以真实渠务办成本圈地方事业，再将交付写入共同账册，本府便能用稳妥的交付换取比疆域更广的影响。',
'彭州':'彭州位于平原与山地相接之处，田亩的受水、山口的通行与地方采办相互牵连。一项看似只关渠口的决定，往往也改变了沿路乡里的负担。\n\n本府疆域有限，难以单靠兵势左右成都的公议，却可以在修渠与讲会之间选择自己的长处。让旧水次得到清楚记录，或以官学联络各府，都能使彭州成为平原圈不能轻易忽略的一员。',
'邛州':'邛州的城郭与作坊连着平原西缘的行旅，器物的流转也连着乡里的日常生计。邛窑旧日的声名提醒掌事者：地方巧技只有得到可靠采办与传习，才能超出一时的好奇。\n\n在新的会盟中，邛州无需与大府争夺每一次主持权。修渠保产、组织作坊与参加匠人互访，都能为本府积累履约信誉。如何使工匠的长处成为诸侯共同需要的事业，将决定这座小国的前途。',
'眉州':'眉州的乡田与市集养育了自己的地方社会，三苏留下的文章与声名又使它在蜀中文脉中有一席之地。书卷可以传得很远，乡里的渠务与借券却仍须有人逐件办理。\n\n本府可以沿渠务之路维持粮政，也可以在官学讲会中争取主持之誉。若以议论代替交付，声望终究会被邻府的账册质问；若让公议回应地方生计，眉州便能将文化之名化为长久的会盟信用。',
'嘉定':'嘉定的山门、河谷与往来行旅，使此地同时面对施济、渡运和采办的需要。峨眉山周边不同生活习惯并存，府库的安排必须得到实际承担事务的人理解。\n\n本府属于川南盐酒圈，却不必只凭井盐经营立足。盐酒协作的宴席支线给嘉定留下了待客与采办的道路；清楚的契约和可靠的交割，可以使山门与市集成为本府参与帝国事业的根基。',
'叙州':'叙州的水程与城中的采办相互依赖，盐酒、粮料和行旅在此需要可信的交割安排。沿江便利带来了商机，也使一笔拖延的款项能够牵动不止一家经营。\n\n作为川南盐酒圈最初的选侯，叙州可以沿井灶担保走向共同融资，也可以以席面采购赢得诸侯的委托。总号的印信不会自行生出信用；本府必须在借款的便利与偿还的责任之间守住自己的分寸。',
'泸州':'泸州的城郭面对江运，酒坊与沿岸采办又各有自己的守时办法。府库既希望集中采购，也不得不依赖船户、作坊与乡里的实际供给。\n\n叙州拥有本圈最初的主持名望，泸州则可凭稳定的供应争取更多份额。井灶公账与窖坊分工是两条不同的道路：前者重在信用担保，后者重在采办契约；本府的选择将决定它在共同事业中承担何种责任。',
'长宁':'长宁的山地与邻近通路，使货物出产和送达不能分开筹划。对本府而言，一份已经收下的订单，只有经过备料、候运与核账，才算真正完成。\n\n在川南盐酒圈中，长宁没有天然属于自己的总号或选侯席位，却能从可靠的小规模交付起业。先办成盐业项目，再选择担保或宴席经营，可以使偏处的府州逐步参与更大的跨圈事业。',
'昌州':'昌州的地方经营介于丘陵与江路之间，市集的货物并不能凭一张水运图便自动抵达码头。沿路转运和府界上的查验，是本府每天都要处理的事务。\n\n重庆掌握圈中的选侯席位，昌州则可在通行公约中为自己的商户争取便利。若选择崖岸守备，本府又须将驻守与供给同时办好。以小国的实务参与大圈的规则，是昌州扩张影响的可行之路。',
'重庆':'重庆的山城与川江相互依存，崖岸提供险固，江路带来物资，两者都需要持续维护。船户、岸仓与守备各有自己的账，也都希望主持者先听见本方的需要。\n\n本府是川东圈最初的选侯，可以推动通商总约，也可以整合山城江防。地形的便利并不能代替可靠的供给；能够让船帮与守军共同认账的重庆，才有资格向其他诸侯要求更大的主持之权。',
'涪州':'涪州的沿江往来依靠码头与岸上的转运，货物在此停留时需要储放，人手在此交接时需要凭据。一次看似微小的延误，便可能沿水程传至远处的采办方。\n\n本府可以以船帮协作办成转运项目，加入各关认可的通行公约；也可以为崖岸守备准备供给。疆域虽小，若每届都能承担一份可靠的交付，涪州在会盟中的声音便不会只取决于版图。',
'合州':'合州以山城守备的旧事为地方记忆，钓鱼城的遗址又使人明白险固与粮秣必须相互支撑。高处的城壁令人仰望，守住它的人却仍要依靠田亩、仓粮与援路。\n\n在新的府州会盟中，合州可将旧日守备经验转为水陆协防，也可投身江运项目，让运输保护与共同经营相互成全。如何维持供给而不耗尽地方财力，是本府必须反复回答的题目。',
'夔州':'夔州辖境较广，山峡间的水程与分散的地方事务需要不同的掌事者。府库看到的是一项总额，船户看到的却是沿途每一次停泊、候援与交接。\n\n重庆的主持权不能自动说明夔州的所有负担。本府可以凭通行公约协调分散岸口，也可以沿江防之路整合守备。用能够查验的共同事业维护广阔辖境，是夔州取得圈内影响的根本。',
'酉阳':'酉阳的山地使行旅不能只依赖一条水程，市集与渡运还要由沿途乡里接续。地方见证在此尤其重要，因为远处的账房难以看见每一次实际交割。\n\n本府属于川东圈，却有自己的山地负担。借江运项目安排可靠的转运，或以水陆协防保护通路，都需要先取得地方的认可。酉阳若能使谷中的旧例与圈内公约彼此说明，便能在会盟中争得独特的位置。',
'忠州':'忠州的岸口与腹地田亩相互依赖，江上的通商便利必须由乡里的道路和仓储接住。船到岸后的责任若无人认领，一次顺利的运输仍可能以争执收场。\n\n本府可以从码头转运与船帮协作起步，用稳定交付积累江运项目。较大的诸侯或许能够左右议题，忠州却可用公账与通行契约争取自己的利益，让沿江经营成为不易被取代的会盟职责。',
'保宁':'保宁的城郭连着川北往来的驿路，地方仓储与接递的文书都要按时到达。守备希望优先取得粮料，行旅则希望关市早日放行，两种需要常在同一条路上相遇。\n\n本府是蜀道圈最初的选侯，可以以轮戍互援统筹关防，也可以以驿传总局协调通路。主持之权必须由当值与接递的记录支撑；若只令邻府承差而不说明分担，保宁的名望终会遭到质问。',
'巴州':'巴州的山路联系着分散乡里，也使府库难以用一份统一程册说明沿途的劳苦。桥栈、候宿与地方供给，都需要近处的人逐段承担。\n\n本府可选择蜀道的守备支线，将轮戍的责任讲清；也可推动驿券与分驿，减少通路上的重复征索。保宁拥有圈中的席位，巴州若能以可靠的接力与援助建立信用，便能让自己的路程成为议事中的依据。',
'广元':'广元连接蜀道沿线的转运与行旅，金牛道的旧路线说明它与山外交通之间的关系。进入巴蜀的路并非只是一处关门，而是连续的驿站、桥栈与供给。\n\n会盟敕书维护外部隔离，广元仍需经营境内的通行与守备。本府可以从驿堡联络起业，在轮戍或关市之间选择长处；维护关键路段的实际贡献，将使这座小国在川北公议中拥有分量。',
'剑州':'剑州的地方名望与蜀道、剑门的历史记忆相联系，山势的险峻令人重视守备，也容易使人忽略维持守备所需的日常劳力。木石、粮料与接递之人，同样属于关防。\n\n本府可以沿山关防务建立轮戍互援，也可以转向驿券与公文分驿。险固不必只服务征战：让各府能够通行、让当值之人得到补给，同样是剑州争取圈内主持权的办法。',
'龙安':'龙安的山地与沿路乡里，需要把报险、修栈和送粮合在一起筹划。府令到达之后，真正承担事务的人仍要依据季节与道路决定如何履行。\n\n龙安无需在开局便与大府争夺长久统摄之权。以栈道勘绘和驿堡联络建立自己的程册，再选择守备或驿传，可以使本府的地方经验成为蜀道圈共同规则的一部分。',
'达州':'达州的地方往来分散在不同路程之间，市集、乡田与沿路堡驿各有需要。府库若只追求一次征调的总额，便难以说明哪个乡里承担了额外的接递。\n\n本府可以以轮戍之约协调人手，也可以用关市驿券降低通路摩擦。达州的影响未必来自最险的关口，而可以来自能够让邻府放心接续的交付与文书，使道路成为长期协作的纽带。',
'顺庆':'顺庆的城郭与沿途经营需要稳定接递，田亩的出产也要经由道路送往更远的采办方。守备、行旅与府库之间的责任，不能只在危急时才临时商议。\n\n本府可以从驿堡联络兴办关驿项目，再选择关防或驿传的长处。圈中的选侯位于保宁，顺庆若愿保存清楚的交割与当值记录，便可使自己的规模与经营转化为公议中可核验的贡献。',
'简州':'简州的丘陵田亩与市集相互支撑，塘堰所蓄的水和乡社所存的粮都与年景紧密相连。地方经营需要的不只是丰年多收，还包括歉岁仍能按约相助的安排。\n\n本府可走分仓赈贷的道路，经营可调剂的仓廪项目；也可沿契约见证与票据清算建立公信。面对较大的诸侯，简州的长处在于把日常小事做成可查的共同责任。',
'遂宁':'遂宁的地方事业以乡田、市集与仓粮为根，丰歉之间的调剂决定了许多家庭能否继续经营。仓门的开闭看似属于府库，却会同时影响乡社信用与邻府的借贷。\n\n作为丘陵圈最初的选侯，本府可主持义仓联社，也可发展诸侯公信会馆。替人保管粮食与替人裁定契约，都要求主持者接受查验；遂宁必须使自身的公议权与实际承担的责任相称。',
'潼川':'潼川的乡里需要在分散田亩之间调剂粮水，城中的券据又常与这些地方交付相联系。纸上的一笔清算，可能关系到哪一乡来年还能补足种粮。\n\n本府可以以分仓赈贷保障地方生计，也可以以契约见证明确偿付。义仓与公信是不同的经营道路，前者要保有真实储备，后者要保存真实交割；潼川必须选择自己最能长期承担的职责。',
'广安':'广安的辖境连接不同乡里的市集与田亩，一项地方安排往往有多处受益，也有多处承担维护。府库若不能说明这些差别，账面上的整齐便可能掩去实际不平。\n\n本府可以凭规模建立分仓互济，也可以用票据清算协调跨地交易。遂宁主持圈中的初始公议，广安则能够以连续交付争取更大的影响，让乡社的凭据进入诸侯之间的议约。',
'雅州':'雅州的茶与往来商队连着山地互市，宋代茶马经营留下的旧事使本地重视秤量、交割与通路。离开市集之后，山程上的候宿与报险又要依靠沿途各方。\n\n本府是茶马圈最初的选侯，可以兴办商队项目与通商公所，也可以以山门施济与跨地调停取得支持。商业主持和公议主持各有责任；雅州必须让自己的券据在山外与山内同样得到认可。',
'茂州':'茂州的山地使不同乡里各有通路与旧俗，远来的府令需要经过见证与说明，才能成为实际可行的安排。向导、歇脚之所与地方调停，是往来经营的一部分。\n\n雅州的茶马市集给本府提供合作机会，却不能替茂州解决每一处山程的负担。本府可沿商队项目争取订单，也可沿山门与调停支线保存地方认可，让自己的旧例与共同通路相互成全。',
'松潘':'松潘的辖境分散在广阔山地，府库与各乡之间的距离使报险、候援和采办都需要可靠接续。一个看似充足的总数，未必代表每一段道路都有人维护。\n\n本府可以沿通路会约协调商队项目，也可以以跨地调停加强地方见证。规模带来经营机会，也带来更多无法轻忽的负担；松潘若能把分散的承诺整理成可查的约定，便能取得茶马圈中独特的影响。',
'盐源':'盐源的谷市连接附近乡里，地方经营需要将道路、供给与交割一并商议。一处市集的便利若由另一处谷口无偿承担，旧例便很容易转为新的争执。\n\n本府属于山谷圈，可以沿小路换市与商盟互保发展经营，也可以以联寨守望维持地方议约。盐源的前途不必只由国力大小决定；让实际使用道路的人认同维护之约，便能逐步积累可靠的会盟信用。',
'德昌':'德昌的谷地与往来通路相互依靠，市集的货物需要经过乡里接续，府库的征调也需要得到掌事者认可。守备与经营在此并不是两项互不相关的事务。\n\n本府可以发展山谷互市，用商盟之约扩大合作；也可以沿议约驻防明确援守的粮料与期限。建昌主持圈中的最初公议，德昌若能把自身负担写入凭据，便可争取与贡献相称的声音。',
'黎州':'黎州的山程连接互市与地方生活，宋代雅州、黎州茶马往来的旧事，为今日的行旅留下了可资援引的背景。旧券记得谁能通行，却未必说明谁应修桥与候援。\n\n本府在山谷圈中可以以换市与互保建立经营，也可以以地方议约保护旧权。让实际维护道路的人共同见证通行之约，是黎州把历史通路转化为长久会盟职责的起点。',
'马湖':'马湖的地方往来需要考虑渡运与沿岸乡里的实际承载。府库可以在券面列出额度，船户与转运之人却必须根据现有器具和人手完成它。\n\n本府可借商盟互保协调交割，也可沿共治守备支线明确沿途责任。无论选择哪条道路，马湖都应让真实运力进入公议，避免以无法兑现的承诺换取一时声望，使小国的可靠成为自身的长处。',
'建昌':'建昌辖内各谷的生活与旧例并不完全相同，主印所代表的总数也不能说明每处乡寨的实际负担。互市与驻守都需要取得本地承担者的见证。\n\n本府是山谷圈最初的选侯，既可主持商盟，也可沿议约驻防建立共保盟府。集中的主持权与分散的地方认可必须相互支撑；能够令各谷真正愿意履约的建昌，才可能获得超出名号的权威。',
'永宁':'永宁的乡寨与互市场所，需要在行旅便利和地方巡察之间取得平衡。把市集移得更近通路，可以减少脚程，却也可能改变周边居民承担的维护。\n\n本府可以沿山谷商盟发展有限的共同采办，也可以以联寨守望维持共治。比起只在纸上扩大经营，永宁更需要让交割、驻守与旧权彼此说明；这样的地方约定，才有机会被更大的诸侯接受。'}

MISSION_PHASES=[
'共同事业初立，乡里的旧例仍各有写法。我们应先把本府承担的一项实务交付清楚，让圈中诸侯看见可以查验的成果。',
'最初的试办已有人接续，下一步却不能只沿用主持者个人的情面。让承担者、使用者与府库共同认可凭据，地方经营才能逐步成为常例。',
'早年的约定已经经历数次换主，当初认可的人手与供给也有所变化。重审旧约，需要说明哪些责任仍可履行，哪些分担必须重新取得认同。',
'地方事业渐有规模，分散的经营却开始争夺同样的备料与主持权。我们应先整理交接与查验，再将原本各自为政的事务纳入可靠的协作。',
'百年前的开创者已经不在，今日的乡里仍在使用他们留下的道路与规矩。把实际交付写入新的章程，是让后来的主持者能够继续治事，而非只诵读先人的名号。']

DECISION_PROSE={
'hbe_status':'府臣呈上各处事业的簿册，想知道我们在诸侯间的声望究竟依托何物。名号可以在典礼上宣读，履约却须逐笔说明。\n\n查阅本府的义气、地方储备与未结事项，下一次采办和议约便有了可以核对的依据。',
'hbe_assembly':'各府使者带着不同的账册来到议事堂，有人请求共修，有人坚持旧权。皇帝的主持并不能使这些差别自行消失，却能给各方留下当堂说明的机会。\n\n本府愿出资召开茶议，使共同经费与自治之责得到明确作答；堂上今日认可的安排，终须回到渠旁、仓场与关驿接受查验。',
'hbe_salt_loan':'盐业的交付还在来年，工程所需的钱却已经到了眼前。井灶掌事愿以预期收入作保，库吏也提醒我们，一枚盐引的便利将伴随此后逐年的利息。\n\n借来的钱可以使事业早日动工，偿还的责任却不能交给尚未到来的丰年。我们应让担保、欠额与还款同时入册。',
'hbe_salt_repay':'库中已有可以调度的钱，旧盐引仍写着本府的承诺。将债额减去一份，不仅使往后的担保更有余地，也让出借者看见诸侯的印信能够对应真实偿付。\n\n府臣将重核旧券，按实际还款注销相应欠额，并将这次履约记入会盟公账。',
'hbe_project_fund':'各圈所承的工程不同，共同采办却都需要有人先拿出钱。今日的出资不能替代井灶、船帮与乡社的专业交付，但可以使这些承担者不必独力垫付所有费用。\n\n我们愿在本届账册上认下一份实款，让自己的支持在散席之后仍有凭据可查。',
'hbe_project_pledge':'库中暂不便调度现钱，府臣却不愿因此错过本届共同事业。先签一份承诺，可以使主持者知道我们愿意分担，也把届中付款之日明白写定。\n\n印信并不能替代金币。核账之时若无款可交，本府便须承担违约的声望与公议后果。',
'hbe_project_reconsider':'此前的暂缓之议已经传到各府，新的采办安排却使我们有了重新参与的余地。旧意见可以撤回，后来作出的承诺仍须与其他诸侯一样接受查验。\n\n在承诺期内改明立场，可以重新出资或认领专业交付，让本府的改变有实际事业可以支撑。',
'hbe_project_select_1':'井灶可以供盐，江岸可以转运，乡社可以核验粮数；三者若各自为政，货物便可能停在彼此的交接之间。\n\n皇帝将本届共同事业定为盐船运粮，先约定所需环节，再请有能力的府州认领交付。工程的名目由主持者提出，成果则必须由各圈实际完成。',
'hbe_project_select_2':'茶马互市不能只停留在集市的秤前。山路的接递、谷口的见证与采办的凭据同样决定一趟远行是否可靠。\n\n本届共同事业将围绕茶路展开，把远途交割与沿途维护一并记入公账，令不同山地的承诺能够在同一次验收中相互说明。',
'hbe_project_subsidize':'验收的日子渐近，账册中仍有一项无人交足。若任其空缺，已出资与已交货的府州也将失去共同事业的回报。\n\n皇帝可以出钱聘请本地机构补办，但补缺并不免去原有查验。本届仅能这样垫付一次，主持者须慎重选择何时动用府库。',
'hbe_audit_accounts':'诸侯各自保存的凭据已经到了堂上，争执却仍在于同一笔交付究竟由谁认领。继续争论名望，只会使下届采办同样受阻。\n\n我们愿拨款公开核账，使出资、货物与未履行的责任逐项相对。经得起查验的公账，才能让不同府州继续合作。',
'hbe_banquet_ledger':'届次的账册已经展开，主持者请各府先察看本届工程，再确认自己曾作出的承诺。共同的成功不能由某一家的声望代替，个人的出资也不能抹去尚缺的专业环节。\n\n查阅交付、争席与百年章程的进展，使本府接下来的决定能够回应眼前的公账。'}

REGION_CONTEXT={
'chengdu_plain':'渠田、作坊与官学', 'southern_salt_wine':'井灶、窖坊与采办',
'eastern_river':'码头、船帮与岸仓','northern_shudao':'关堡、驿站与桥栈',
'central_hills':'塘堰、义仓与券据','western_tea_horse':'茶市、商队与山门',
'southwestern_valleys':'谷市、乡寨与地方见证'}

def build_native_content(out,root,countries,regions,nodes,loc,put,full_art,game):
    all_tags=[c['tag'] for c in countries]
    region_tags={r[0]:[c['tag'] for c in countries if c['region']==r[0]] for r in regions}
    region_names={r[0]:r[1] for r in regions}
    region_by_name={c['name']:c['region'] for c in countries}
    event_catalog={e['id']:e for e in json.loads((root/'data/events_v002.json').read_text(encoding='utf-8'))}
    # Native advances are the only visible research entry point.
    advances=[];bridge=[];tech_text=[]
    for n in nodes:
        key=n['key'];group=n['group'];idx=n['index'];tags=all_tags if group=='common' else region_tags[group]
        prose=TECH_PROSE[group][idx]
        branch=''
        if group!='common' and idx>=2:
            opposite=f'hbe_tech_{group}_{6 if idx<5 else 3}'
            branch=f'NOT = {{ has_advance = {opposite} }} NOT = {{ has_variable = {opposite} }}'
        unlock='完成记录用于本府的地区事件与事业资格；每项课题首次结算时义气增加3、帝国锅气增加1。'
        if group!='common' and idx==0:unlock='解锁本圈三年地方事业与本地专业交付资格；首次结算时义气增加3、帝国锅气增加1。'
        if group=='southern_salt_wine' and idx==3:unlock='解锁盐引贷款，并作为本圈旧约重审资格；首次结算时义气增加3、帝国锅气增加1。'
        if group=='common' and idx==1:unlock='整合其他旧府州后，专业交付可按现有规则使用10点义气作替代担保；首次结算时义气增加3、帝国锅气增加1。'
        if group!='common' and idx==1:unlock='取得本圈成长验收的课题资格；首次结算时义气增加3、帝国锅气增加1。'
        if group!='common' and idx in (3,6) and not(group=='southern_salt_wine' and idx==3):unlock='取得本圈旧约重审验收的课题资格；首次结算时义气增加3、帝国锅气增加1。'
        if group!='common' and idx in (4,7):unlock='取得本圈地区重组及百年章程验收的课题资格；首次结算时义气增加3、帝国锅气增加1。'
        loc[key]=n['name'];loc[key+'_desc']=prose+'\n\n'+unlock+'研究完成后的地区记录于月初结算。'
        loc[key+'_effects']=unlock
        parent=n['predecessor'] or ('written_alphabet' if key=='hbe_tech_common_1' else 'hbe_tech_common_1')
        def node_age(row):
            late=row['index'] in ((2,5,7) if row['group']=='common' else (2,3,4,5,6,7))
            return 'age_2_renaissance' if late else 'age_1_traditions'
        age=node_age(n)
        logical_parent=parent
        node_lookup={row['key']:row for row in nodes}
        cross_age=age=='age_2_renaissance' and (parent not in node_lookup or node_age(node_lookup[parent])!=age)
        if cross_age:
            branch+=' has_advance = '+logical_parent
            parent='renaissance_development'
        # Only the eighth node of each of the eight trees keeps a premium.
        cost_line='    research_cost = 0.5\n' if idx==7 else ''
        advances.append(f'''{key} = {{
    age = {age}
    starting_technology_level = 99
    icon = {key}
    content_priority = {900-idx*10}
{cost_line}
    potential = {{ hbe_research_origin_{group} = yes }}
    allow = {{ is_member_of_international_organization = international_organization:hbe_empire current_year >= {n['year']} {branch} }}
    requires = {parent}
    pure_tooltip_entry = {key}_effects
}}''')
        bridge.append(f'''if = {{ limit = {{ has_variable = {key} NOT = {{ has_advance = {key} }} }} research_advance = advance_type:{key} }}
    if = {{ limit = {{ has_advance = {key} NOT = {{ has_variable = {key} }} }} set_variable = {key} hbe_add_credit = yes trigger_event_non_silently = {{ id = hbe.2 }} }}''')
        tech_text.append(dict(key=key,name=n['name'],body=prose,unlock=unlock,year=n['year'],native_research_cost=0.5 if idx==7 else 0.0,predecessor=parent,logical_predecessor=logical_parent,age=age,tags=tags))
    put('in_game/common/advances/hbe_advances.txt','\n'.join(advances))
    put('in_game/common/scripted_effects/hbe_native_content_effects.txt','hbe_sync_native_research = {\n'+'\n'.join(bridge)+'\n}')
    put('in_game/common/on_action/hbe_native_content_on_actions.txt','''on_game_start = { on_actions = { hbe_native_content_start } }
hbe_native_content_start = { effect = { every_country = { limit = { hbe_is_prince = yes } hbe_sync_native_research = yes } } }
monthly_country_pulse = { on_actions = { hbe_native_content_monthly } }
hbe_native_content_monthly = { trigger = { hbe_is_prince = yes } effect = { hbe_sync_native_research = yes } }''')
    # Register concrete tags, not just runtime variable predicates, for native discovery.
    decision_text=[];registered_decisions=[]
    # Later-stage formables may already exist during a repeated build; their
    # localization is not available until their owning generator runs.
    for name in ('hbe_banquet_decisions.txt', 'hbe_decisions.txt'):
        path = out/'in_game/common/decisions'/name
        s=path.read_text(encoding='utf-8-sig');edits=[]
        for key,start,a,b,end in blocks(s,0):
            if key.startswith('hbe_tech_'):
                edits.append((start,end,''));continue
            body=s[a:b];match=re.search(r'hbe_(?:home|geo)_([a-z_]+)',body)
            group=match[1] if match and match[1] in region_tags else None
            tags=region_tags[group] if group else all_tags
            if key.startswith('hbe_role_'):tags=all_tags # integrated owners can use regional services
            body=body.replace('decision_category = other_decisions','decision_category = country_specific_decisions',1)
            body='\n    tags = { '+' '.join(tags)+' }'+body
            old=loc[key+'.desc'];title=loc[key]
            if key in DECISION_PROSE:prose=DECISION_PROSE[key]
            elif key.startswith('hbe_mission_'):
                group=re.fullmatch(r'hbe_mission_([a-z_]+)_([1-5])',key)[1];stage=int(key[-1])-1
                prose=region_names[group]+'的'+REGION_CONTEXT[group]+'仍须由实际承担者接续。'+MISSION_PHASES[stage]+'\n\n我们将呈上本府的交付凭据，请圈中查验这项事业是否已经能够承担下一阶段的责任。'
            elif key.startswith('hbe_service_'):
                group=key.removeprefix('hbe_service_')
                prose=region_names[group]+'的'+REGION_CONTEXT[group]+'不能只在会盟之时才受重视。府臣请将备料、主持与查验分别入册，使日常经营有持续的接续。\n\n本府愿出资试办三年，验收后再将成果与地方储备一并登记；只有真实完成的事业，才值得要求邻府认可。'
            elif key.startswith('hbe_role_'):
                group=key.removeprefix('hbe_role_')
                prose=REGION_CONTEXT[group]+'各有熟悉事务的掌事者，共同工程却需要他们的交付在同一期限内得到认可。\n\n我们愿认领这项专业合同，出钱备办并以地方储备作保。半年后的查验，将决定这份承诺能否成为本届工程真正齐备的一环。'
            elif key.startswith('hbe_stance_change_'):
                i=int(key[-1]);prose=[
                    '各府分头出资，仍有许多工程难以贯通府界。我们愿以共同主持协调这些事业，也接受由此而来的经费与维护之责。\n\n转向共建之议，是让集中筹办得到更多支持；它不会使旧欠自行消失，也不能免去诸侯对公账的质问。',
                    '乡里的旧例由当地承担者维持，过远的主持者未必能够看见每处实际负担。我们愿让各府保有更大的地方安排，再以共同认可的验收相互联系。\n\n转向兴业之议，是选择以自治维护协作。独立的府库仍须兑现自己签下的承诺，地方的便利也需要持续交付。',
                    '名望可以让一份承诺容易被接纳，却不能说明货物何时送达。我们愿以公账和凭据衡量共同事业，使出资者与承担者按实际交付取得回报。\n\n转向账房之议，是请诸侯将情面之外的责任写明。规矩越清楚，主持者也越须接受同样的查验。'][i-1]
            elif key.startswith(('hbe_propose_charter_','hbe_ballot_vote_')):
                i=int(key[-1]);choice=['集中主持共同工程，并由皇帝承担持续维护','保留各府自治经营，以地方事业与粮政相互扶助','按实际交付核定共同收益，以契约保存彼此责任'][i-1]
                prose='百年的共同事业已留下许多可查的凭据，今日的诸侯却仍要选择今后怎样继续。此份章程主张'+choice+'。\n\n'+('皇帝将呈上草案，请旧府州的席位逐一授权；提出章程只开启议约，不能代替各圈的同意。' if 'propose' in key else '本府将以所掌握的旧席签认此案。每圈须取得本圈席位的严格多数，至少四圈同意，章程方能成为共同认可的安排。')
            else:raise ValueError('Unwritten decision '+key)
            loc[key+'.title']=title;loc[key+'.title.entry']=title
            loc[key+'.desc']=prose+'\n\n#T 办理与验收#!\n'+old
            loc[key+'.desc.entry']=prose
            if key!='hbe_banquet_ledger' and key!='hbe_status':loc[key+'.a']='依议办理。'
            decision_text.append(dict(key=key,title=title,body=prose,rules=old,tags=tags))
            edits.append((a,b,body));registered_decisions.append(dict(key=key,tags=tags))
        put(path.relative_to(out).as_posix(),apply_edits(s,edits))
    assert len(decision_text)==70
    # The native DHE catalogue requires global fire_only_once. Register only the
    # 36 genuinely single-country, single-use stories; recurring settlement and
    # region/era events must never inherit that global restriction.
    event_index=[];recurring_events=[]
    for path in sorted((out/'in_game/events').glob('hbe*events.txt')):
        s=path.read_text(encoding='utf-8-sig');edits=[]
        for key,_,a,b,_ in blocks(s,0):
            if not re.fullmatch(r'hbe(?:_banquet)?\.\d+',key):continue
            entry=event_catalog.get(key);group=None;tags=all_tags;year=1337
            loc[key+'.entry']=loc[key+'.title']
            if not(entry and entry['category'] in region_by_name):
                recurring_events.append(key);continue
            if entry:
                category=entry['category']
                if category in region_names.values():group=next(g for g,n in region_names.items() if n==category)
                if category in region_by_name:
                    tags=[c['tag'] for c in countries if c['name']==category]
                    year=1338+(int(key.split('.')[1])-200)%6
                if category=='generational':year=[1337,1352,1372,1397,1422,1437,1457][int(key.split('.')[1])-30]
            elif key.startswith('hbe.') and 100<=int(key.split('.')[1])<=106:group=regions[int(key.split('.')[1])-100][0]
            if group:tags=region_tags[group]
            header='\n    fire_only_once = yes\n    dynamic_historical_event = { '+' '.join('tag = '+t for t in tags)+f' from = {year}.1.1 to = 1837.1.1 monthly_chance = 0 '+'}\n'
            edits.append((a,a,header));event_index.append(dict(id=key,tags=tags,from_year=year,autonomous_monthly_chance=0))
        put(path.relative_to(out).as_posix(),apply_edits(s,edits))
    assert len(event_index)==36 and len(recurring_events)==60
    # Engine country description tab reads country_history_TAG. Lobby category is separate.
    categories=[];biographies=[]
    for c in countries:
        key='hbe_profile_'+c['tag'].lower();categories.append(key+' = {}');body=BIOGRAPHIES[c['group']]
        loc['country_history_'+c['tag']]=body
        loc['country_description_category_name_'+key]=c['group']+'：'+REGION_CONTEXT[c['region']]
        loc['country_description_category_desc_'+key]=body
        loc['hbe_'+c['tag']+'_scenario_desc']=body
        biographies.append(dict(tag=c['tag'],country=c['name'],body=body,circle=c['region']))
    put('in_game/common/country_description_categories/hbe_profiles.txt','\n'.join(categories))
    # GetHistoryDesc uses this ordered selector, not merely country_history_TAG.
    history=(root/'data/bashu_history_v020.json')
    contextual=json.loads(history.read_text(encoding='utf-8')) if history.exists() else {}
    original_history=(game/'in_game/common/customizable_localization/country_history.txt').read_text(encoding='utf-8-sig')
    registration='\n'.join('text = { localization_key = country_history_'+c['tag']+' trigger = { has_or_had_tag = '+c['tag']+' } }' for c in countries)
    original_history=original_history.replace('type = country','type = country\n'+registration,1)
    put('in_game/common/customizable_localization/country_history.txt',original_history)
    for c in countries:
        if contextual: loc['country_history_'+c['tag']]=contextual['common']+'\n\n'+contextual['circles'][c['region']]+'\n\n'+BIOGRAPHIES[c['group']]
    path=out/'in_game/setup/countries/hbe_countries.txt';s=path.read_text(encoding='utf-8-sig');edits=[]
    for tag,_,a,b,_ in blocks(s,0):edits.append((a,b,s[a:b].replace('description_category = administrative','description_category = hbe_profile_'+tag.lower())))
    put(path.relative_to(out).as_posix(),apply_edits(s,edits))
    # Native event/decision image widget is 540x220, not a square or a 2:1 card.
    picture_rows=[];proof=Image.new('RGB',(1800,7*210+65),'#302a23');d=ImageDraw.Draw(proof);font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
    d.text((15,10),'70 项决议配图 · 原版 540:220 比例 / 科技图标仅用于科技树',font=font,fill='#ead59b')
    for i,e in enumerate(full_art['decision_pictures']):
        # Close the PNG input before replacing that same generated source file on Windows.
        with Image.open(root/'assets/decision_pictures'/f'{e["key"]}.png') as source:
            sprite=fit(source,380).copy()
        card=Image.new('RGBA',(1080,440));card.alpha_composite(sprite,((1080-380)//2,(440-380)//2))
        target=out/e['image'];save_dds(target,card);save_png(root/'assets/decision_pictures'/f'{e["key"]}.png',card)
        e['sha256']=hashlib.sha256(target.read_bytes()).hexdigest();e['dimensions']=[1080,440]
        thumb=card.resize((180,74),Image.Resampling.LANCZOS);x=(i%10)*180;y=(i//10)*210+55
        proof.paste(thumb,(x,y),thumb);d.text((x+3,y+90),e['name'][:10],font=font,fill='#ead59b')
        picture_rows.append(e)
    proof.save(root/'assets/decision_pictures_preview.png')
    (root/'data/art_v01.json').write_text(json.dumps(full_art,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    catalogue=dict(version='0.1.1',advances=tech_text,decisions=registered_decisions,events=event_index,non_dhe_event_ids=recurring_events,country_biographies=biographies,decision_pictures=picture_rows,native_image_dimensions=[1080,440])
    (root/'data/native_content_v011.json').write_text(json.dumps(catalogue,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (root/'data/decision_texts_v011.json').write_text(json.dumps(decision_text,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for filename,title,entries,namekey in [('country_biographies_v011.md','三十六府州背景介绍',biographies,'country'),('decision_prose_v011.md','七十项决议风味正文',decision_text,'title')]:
        doc=['# '+title,'','0.1.1；国家、会盟制度与政治处境为架空设定，历史传统沿用本模组已核对的史料背景。','']
        for e in entries:doc+=['## '+e[namekey],'',e['body'],'']
        (root/'docs'/filename).write_text('\n'.join(doc)+'\n',encoding='utf-8')
    return dict(native_advances=64,registered_decisions=70,registered_events=36,total_events=96,non_dhe_events=60,country_biographies=36,catalogue='data/native_content_v011.json',pending_v01_research='retired 0.4.0: decision research and timers removed',new_research='native research queue; monthly idempotent variable bridge')
