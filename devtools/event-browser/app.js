'use strict';
let catalog, selected, filtered = [];
const $ = s => document.querySelector(s);
const esc = x => String(x ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const labels = {
 add_gold:'金币', add_prestige:'威望', add_stability:'稳定度', add_legitimacy:'正统性', add_manpower:'人力',
 hbe_burden:'役负', hbe_yiqi:'义气', hbe_guoqi:'锅气', hbe_water:'水利', hbe_dispute:'争议',
 hbe_stance:'派系选择', hbe_ballot_vote:'表决选择', gold:'金币', current_year:'年份',
 hbe_round_contributed:'本轮已贡献', hbe_civic_council_done:'已完成地方事业',
 hbe_clamp_burden:'役负数值边界', hbe_clamp_yiqi:'义气数值边界', hbe_clamp_guoqi:'锅气数值边界',
 hbe_choose_stance_1:'支持共建派', hbe_choose_stance_2:'支持兴业派', hbe_fund_project:'为会盟事业出资',
 hbe_flavor_cooldown:'地方事件冷却', hbe_banquet_flavor_cooldown:'会盟地方事件冷却',
 hbe_civic_incident_cooldown:'社会事件冷却',
 global_monthly_food_modifier:'粮食产出', global_rice_output_modifier:'稻米产出', global_construction_speed:'建筑效率',
 global_salt_output_modifier:'盐产出', global_hbe_well_salt_output_modifier:'井盐产出',
 global_hbe_shu_paper_output_modifier:'蜀纸产出', global_hbe_border_tea_output_modifier:'边茶产出',
 global_production_efficiency:'生产效率', global_merchant_capacity_modifier:'商人容量',
 global_monthly_control:'每月控制力', global_food_decay:'食物腐坏', ship_build_speed:'造船速度',
 merchant_maintenance_efficiency:'商人维护效率', army_maintenance_efficiency:'军队维护效率',
 global_defensive:'要塞防御', global_road_building_time:'道路建造时间', global_supply_limit_modifier:'补给上限',
 global_institution_growth_modifier:'思潮增长', global_trade_center_power:'贸易中心影响力',
 global_manpower_modifier:'人力上限', global_tea_output_modifier:'茶叶产出',
 cultural_influence_modifier:'文化影响力', tolerance_heathen:'异教宽容', global_tools_output_modifier:'工具产出',
 peasants_estate_target_satisfaction:'农民阶层满意度均衡点', burghers_estate_target_satisfaction:'市民阶层满意度均衡点',
 tribes_estate_target_satisfaction:'部族阶层满意度均衡点', nobles_estate_target_satisfaction:'贵族阶层满意度均衡点',
 add_research_progress:'研究进度', add_estate_satisfaction:'阶层满意度', custom_tooltip:'抉择提示', research_speed_modifier:'研究速度', global_disease_resistance:'疾病抵抗', global_livestock_output_modifier:'牲畜产出', global_migration_attraction:'移民吸引力', global_migration_speed_modifier:'迁移速度', global_monthly_literacy:'每月识字率', global_population_capacity_modifier:'人口容量', global_pop_assimilation_speed_modifier:'同化速度', tax_income_efficiency:'税收效率', monthly_prestige:'每月威望', monthly_army_tradition:'每月陆军传统', navy_maintenance_efficiency:'海军维护效率', 'estate_type:peasants_estate':'农民阶层', 'estate_type:nobles_estate':'贵族阶层', 'estate_type:burghers_estate':'市民阶层', 'estate_type:clergy_estate':'教士阶层', 'estate_type:tribes_estate':'部族阶层', add_country_modifier:'添加国家修正', remove_country_modifier:'移除国家修正',
 every_owned_location:'每个符合条件的所属地点', every_country:'每个符合条件的国家',
 random_owned_location:'随机符合条件的所属地点', random_country:'随机符合条件的国家',
 ROOT:'事件接收者', root:'事件接收者', this:'当前作用域', owner:'所有者', ruler:'统治者',
 effect:'执行效果', hidden_effect:'隐藏效果', if:'满足条件时', else_if:'否则，满足条件时', else:'否则',
 trigger_event_non_silently:'触发事件', trigger_event_silently:'触发隐藏事件',
 has_or_had_tag:'当前或历史国家', is_member_of_international_organization:'属于组织',
 hbe_is_prince:'巴蜀诸侯', hbe_feast_fee:'会盟费用', hbe_public_bill:'地方事业费用',
};
const percentKeys = new Set(Object.keys(labels).filter(k => /modifier$|efficiency$|speed$|_defensive$|food_decay$|building_time$|target_satisfaction$|monthly_control$|trade_center_power$/.test(k)));
function resolveText(text, depth=0) {
 if(depth>3) return String(text??'');
 return String(text??'').replace(/\$([\w.]+)\$/g,(m,k)=>catalog?.localization[k] ? resolveText(catalog.localization[k],depth+1) : m);
}
function name(key) {if(String(key).startsWith('hbe_home_'))return (catalog.regions[String(key).slice(9)]||key)+'圈身份';return resolveText(labels[key] || catalog.localization[key] || catalog.definitions[key]?.name || key);}
function prose(text) {
 const hints=[];
 let value=resolveText(text);
 value=value.replace(/\[Concept\('([^']+)',\s*'([^']+)'\)(?:\|[^\]]+)?\]/g,(match,id,label)=>{
  const background=catalog?.localization['game_concept_'+id+'_desc'];
  if(!id.startsWith('hbe_history_')||!background)return label;
  const plain=resolveText(background).replace(/\[Concept\([^,]+,\s*'([^']+)'\)(?:\|[^\]]+)?\]/g,'$1').replace(/#[A-Za-z_]+\s?/g,'').replace(/#!/g,'');
  hints.push(`<abbr class="history-guide" title="${esc(plain)}">${esc(label)}</abbr>`);
  return '\uE000'+(hints.length-1)+'\uE001';
 });
 value=value.replace(/#[A-Za-z_]+\s?/g,'').replace(/#!/g,'').replace(/@([\w]+)!/g,'[$1]');
 return esc(value).replace(/\[([^\]]+)\]/g, '<span class="dynamic" title="游戏运行时计算的文本">[$1]</span>').replace(/\uE000(\d+)\uE001/g,(match,i)=>hints[Number(i)]||'');
}
function f(nodes,k,fallback=''){return nodes?.find(n=>n.key===k)?.value ?? fallback;}
function fmt(nodes,depth=0){return nodes.map(n=>'    '.repeat(depth)+n.key+(n.op?' '+n.op+' ':'')+(Array.isArray(n.value)?'{\n'+fmt(n.value,depth+1)+'\n'+'    '.repeat(depth)+'}':n.value)).join('\n');}
function code(text,title='脚本'){return text ? `<details><summary>${esc(title)}</summary><pre>${esc(text)}</pre></details>`:'';}
function valueText(v){return Array.isArray(v) ? fmt(v) : name(String(v).replace(/^var:/,''));}
function conditions(nodes){return nodes.map(n=>{
 if(['NOT','OR','AND','NOR'].includes(n.key))return ({NOT:'不满足',OR:'任一满足',AND:'全部满足',NOR:'全部不满足'}[n.key])+`（${conditions(n.value)}）`;
 if(n.key==='custom_tooltip')return name(f(n.value,'text'));
 if(n.key==='has_variable')return `已有「${name(n.value)}」`;
 if(n.key.startsWith('hbe_home_'))return `属于${catalog.regions[n.key.slice(9)]||n.key}圈`;
 if(n.key==='has_advance')return `已研究「${name(n.value)}」`;
 if(Array.isArray(n.value))return `${name(n.key)}：${conditions(n.value)}`;
 return `${name(n.key.replace(/^var:/,''))} ${n.op} ${valueText(n.value)}`;
 }).join('；');}
function delta(v, percentage=false){if(!Number.isFinite(Number(v)))return `<code>${esc(valueText(v))}</code>`;let x=Number(v)*(percentage?100:1);return `<span class="delta ${x<0?'minus':''}">${x>0?'+':''}${Number(x.toFixed(4))}${percentage?'%':''}</span>`;}
function duration(nodes){if(['years','months','days'].some(k=>Number(f(nodes,k))===-1))return '永久';return ['years','months','days'].map((k,i)=>f(nodes,k)?`${f(nodes,k)}${['年','个月','天'][i]}`:'').filter(Boolean).join(' ')||'未指定期限';}
function definition(key,depth=0,trail=[]){
 const d=catalog.definitions[key];if(!d)return '';
 if(depth>3||trail.includes(key))return code(d.script,`${name(key)} · 原始定义`);
 const contents=d.kind==='script_values'||d.kind==='scripted_triggers'?code(d.script,'查看定义'):effects(d.nodes,depth+1,[...trail,key]);
 return `<details class="definition"><summary>${name(key)===key?'调用脚本函数':esc(name(key))} <code>${esc(key)}</code></summary><div class="source">${esc(d.source)}:${d.line}</div>${contents}${d.kind==='script_values'||d.kind==='scripted_triggers'?'':code(d.script,'完整定义脚本')}</details>`;
}
function effects(nodes,depth=0,trail=[]){
 if(!nodes.length)return '<p class="note">没有直接执行的效果。</p>';
 const maintenance=nodes.filter(n=>/^hbe_clamp_|^remove_country_modifier$/.test(n.key));
 const meaningful=nodes.filter(n=>!maintenance.includes(n));
 return '<ul class="effect-list">'+meaningful.map(n=>{
 const v=n.value;let content='';
 if(['add_gold','add_prestige','add_stability','add_legitimacy','add_manpower','add_research_progress'].includes(n.key)){
 content=`${esc(name(n.key))} ${Array.isArray(v)?`<code>${esc(fmt(v))}</code>`:delta(v)}`;
 if(Array.isArray(v)){const amount=f(v,'value');if(catalog.definitions[amount])content+=definition(amount,depth,trail);}
 }else if(n.key==='add_estate_satisfaction'&&Array.isArray(v)){
 content=`${esc(name(f(v,'type')))}满意度 ${delta(f(v,'value'),true)}`;
 }else if(n.key==='custom_tooltip'){
 content=prose(Array.isArray(v)?name(f(v,'text')):name(v));
 }else if(n.key==='change_variable'&&Array.isArray(v)){
 let action=['add','subtract','multiply','divide','set'].find(k=>f(v,k)!=='');let val=f(v,action);
 if(action==='subtract'&&Number.isFinite(Number(val)))val=-Number(val);
 content=`${esc(name(f(v,'name')))} ${['add','subtract'].includes(action)?delta(val):esc(action+' '+val)}`;
 }else if(['add_country_modifier','add_location_modifier','add_character_modifier'].includes(n.key)&&Array.isArray(v)){
 const key=f(v,'modifier');const d=catalog.definitions[key];
 content=`<span class="effect-label">获得${n.key==='add_location_modifier'?'地点':n.key==='add_character_modifier'?'人物':'国家'}修正</span><br><span class="effect-name">${esc(name(key))}</span> <span class="note">· ${esc(duration(v))}</span>`;
 if(d)content+='<div class="modifier-values">'+d.nodes.map(m=>`<div><span title="${esc(m.key)}">${esc(name(m.key))}</span>${Array.isArray(m.value)?`<code>${esc(fmt(m.value))}</code>`:delta(m.value,percentKeys.has(m.key))}</div>`).join('')+'</div>';
 }else if(n.key==='remove_country_modifier'){
 content=`<span class="effect-label">移除</span> ${esc(name(v))}`;
 }else if(n.key==='set_variable'){
 content=Array.isArray(v)?`记录「${esc(name(f(v,'name')))}」 = ${esc(valueText(f(v,'value','yes')))}${['years','months','days'].some(k=>f(v,k))?` · ${duration(v)}`:''}`:`记录「${esc(name(v))}」`;
 }else if(catalog.definitions[n.key]&&!Array.isArray(v)){
 content=definition(n.key,depth,trail);
 }else if(['trigger_event_non_silently','trigger_event_silently'].includes(n.key)){
 content=`${esc(name(n.key))} <button class="event-link" data-event="${esc(f(v,'id',v))}">${esc(f(v,'id',v))}</button>`;
 }else if(Array.isArray(v)){
 const limits=f(v,'limit',[]);const kids=v.filter(k=>k.key!=='limit');
 content=`<div class="scope"><div class="scope-head">${esc(name(n.key))}</div>${limits.length?`<p class="note">${esc(conditions(limits))}</p>`:''}${depth<4?effects(kids,depth+1,trail):code(fmt(kids),'查看嵌套脚本')}</div>`;
 }else{content=`${esc(name(n.key))} <code>${esc(n.op+' '+v)}</code>`;}
 return '<li>'+content+'</li>';
 }).join('')+'</ul>'+ (maintenance.length?`<details><summary>替换旧修正与数值边界 · ${maintenance.length} 项</summary>${maintenance.map(n=>n.key==='remove_country_modifier'?`<div class="note">移除「${esc(name(n.value))}」</div>`:definition(n.key,depth,trail)).join('')}</details>`:'');
}
function showError(error){$('#error-message').textContent=String(error);$('#error-dialog').showModal();}
function selectEvent(id,focus=false){
 const e=catalog.events.find(e=>e.id===id);if(!e)return;
 selected=id;history.replaceState(null,'','#'+encodeURIComponent(id));
 document.querySelectorAll('.event-row').forEach(b=>{const active=b.dataset.event===id;b.classList.toggle('active',active);b.setAttribute('aria-current',String(active));});
 const source=e.status==='draft'?e.source:catalog.modPath.replace(/\\/g,'/')+'/'+e.source+':'+e.line;
 const tags=[e.category,...e.regions.map(r=>catalog.regions[r]),...e.countries.map(c=>c.name),e.hidden?'隐藏维护':'玩家可见',e.status==='draft'?'新增草稿':'已接入游戏'];
 $('#detail').innerHTML=`<div class="event-head"><div><div class="eyebrow">BASHU / EVENT ARCHIVE</div><h2>${prose(e.title)}</h2><div class="tags">${tags.map(t=>`<span class="tag ${t==='隐藏维护'?'hidden':''}">${esc(t)}</span>`).join('')}</div></div><div class="id-label">${esc(e.id)} <button id="copy-id">复制 ID</button></div></div>
 ${e.status==='draft'?`<section class="draft-notice"><strong>新增故事草稿 · 尚未接入游戏</strong><p>这里展示已写好的正文和选择。效果数值、触发脚本与奖励尚待实现，下面不显示游戏效果。</p>${e.chain?`<p>长线：${esc(e.chain)} · 首章最早 ${e.draftYear} 年 · 本章距首章 ${e.draftOffset} 年（计划时间）</p>`:''}${e.draftEndings?`<p>计划结局：${e.draftEndings.map(esc).join(' / ')} · 永久奖励尚待实现</p>`:''}</section>`:''}
 ${e.illustrationVariants?`<label class="art-preview-label">差分预览（实机按此前选择显示） <select id="art-variant">${e.illustrationVariants.map((a,i)=>`<option value="${i}">${esc(a.label)}</option>`).join('')}</select></label>`:''}
 ${e.illustration?`<img class="story-image" src="${esc(e.illustration)}" alt="事件配图" loading="lazy">`:''}
 <div class="overview"><div><span>选项</span>${e.options.length} 个${e.options.length>1?' · 有抉择':e.hidden?' · 自动执行':' · 通知'}</div><div><span>调用入口</span>${e.incoming.length} 处脚本引用</div><div><span>事件条件</span>${e.trigger?'设有接收条件':'由调用脚本决定'}</div></div>
 ${e.description?`<section class="story"><div class="eyebrow">事件正文</div><div class="prose">${prose(e.description)}</div>${code(e.description,'查看原始本地化文本')}</section>`:'<p class="note">此隐藏事件没有玩家可见正文。</p>'}
 ${e.trigger?`<details><summary>事件接收条件</summary><div class="condition">${esc(conditions(e.conditions))}</div><pre>${esc(e.trigger)}</pre></details>`:''}
 ${e.immediate.length?`<details><summary>预先执行 · 选择选项前已发生</summary>${effects(e.immediate)}</details>`:''}
 <div class="section-title"><h3>${e.options.length?'选项与取舍':'自动执行'}</h3><span>${e.status==='draft'?'选择文案草稿 · 效果待实现':'效果与条件读取自当前脚本'}</span></div>
 <section class="options">${e.options.map((o,i)=>`<article class="option"><div class="option-head"><span class="option-letter">${String.fromCharCode(65+i)}</span><h4>${prose(o.name)}</h4></div><div class="option-key">${esc(o.key)} ${o.aiBase?`<span class="ai"> · AI 基础权重 ${esc(o.aiBase)}</span>`:''}</div>${o.conditions.length?`<div class="condition"><strong>选择条件</strong>${esc(conditions(o.conditions))}${code(o.trigger,'原始条件')}</div>`:''}${o.draft?'<p class="note">此选项的数值效果尚待实现。</p>':o.effects.length?effects(o.effects):'<p class="note">此选项没有直接效果。可同时查看事件的预先执行。</p>'}${code(o.ai,'AI 权重规则（不是概率）')}${code(o.script,'完整选项脚本')}</article>`).join('')}</section>
 ${e.after.length?`<details><summary>结束后执行</summary>${effects(e.after)}</details>`:''}
 <div class="section-title"><h3>触发来源</h3><span>直接脚本引用 · 不等同于实际触发次数</span></div>
 <section class="callers">${e.incoming.map(r=>`<article class="caller"><div class="caller-head">${r.event?`<button class="event-link" data-event="${esc(r.event)}">${esc(r.event)}</button>`:esc(r.context)}</div><div class="source">${esc(r.source)}:${r.line}</div><div class="note">${esc(r.route)}</div>${code(r.conditions,'调用位置的 if 条件')}${code(r.script,'调用脚本与权重')}</article>`).join('')||'<p class="note">未找到直接脚本引用；仍可能通过引擎或间接入口触发。</p>'}</section>
 ${e.outgoing.length?`<div class="section-title"><h3>后续事件</h3></div>${e.outgoing.map(id=>`<button class="event-link" data-event="${esc(id)}">${esc(id)} · ${prose(catalog.events.find(x=>x.id===id)?.title)}</button>`).join('')}`:''}
 <div class="debug-row"><div class="source">${esc(source)}</div><button id="copy-source">复制路径</button></div>${code(e.script,'完整事件脚本')}${code(e.raw,'源文件原文')}`;
 $('#detail').scrollTop=0;
 if(e.illustrationVariants)$('#art-variant').onchange=ev=>{$('.story-image').src=e.illustrationVariants[Number(ev.target.value)].src;};
 $('#copy-id').onclick=()=>copy(e.id,$('#copy-id'));
 $('#copy-source').onclick=()=>copy(source,$('#copy-source'));
 if(focus)$('#detail').focus({preventScroll:true});
}
async function copy(text,button){try{await navigator.clipboard.writeText(text);button.textContent='已复制';setTimeout(()=>button.textContent=button.id==='copy-id'?'复制 ID':'复制路径',1200);}catch{showError('剪贴板不可用：'+text);}}
function filterEvents(){
 const q=$('#search').value.trim().toLowerCase();const implementation=$('#implementation').value,cat=$('#category').value,region=$('#region').value,visibility=$('#visibility').value,choices=$('#choices').value;
 filtered=catalog.events.filter(e=>(implementation==='all'||(e.status||'implemented')===implementation)&&(!cat||e.category===cat)&&(!region||e.regions.includes(region))&&(visibility==='all'||(visibility==='hidden')===e.hidden)&&(choices==='all'||(choices==='multi'?e.options.length>1:choices==='single'?e.options.length===1:e.options.length===0))&&(!q||e.search.includes(q)));
 $('#result-count').textContent=`${filtered.length} / ${catalog.events.length} 个事件`;
 $('#event-list').innerHTML=filtered.map(e=>`<button class="event-row ${e.id===selected?'active':''}" aria-current="${e.id===selected}" data-event="${esc(e.id)}"><strong>${prose(e.title)}</strong><div class="row-meta"><code>${esc(e.id)}</code><span>${e.options.length} 选项${e.status==='draft'?' · 草稿':''}${e.hidden?' · 隐藏':''}${e.regions.length?' · '+esc(e.regions.length>1?'跨圈':catalog.regions[e.regions[0]]):''}</span></div></button>`).join('')||'<div class="empty">没有匹配的事件<br><button id="empty-reset">清空筛选</button></div>';
 if($('#empty-reset'))$('#empty-reset').onclick=reset;
 if(filtered.length&&!filtered.some(e=>e.id===selected))selectEvent(filtered[0].id);
 if(!filtered.length)$('#detail').innerHTML='<div class="empty">没有匹配的事件。请调整筛选条件。</div>';
}
function reset(){['search','category','region'].forEach(id=>$('#'+id).value='');['visibility','choices','implementation'].forEach(id=>$('#'+id).value='all');filterEvents();}
async function load(refresh=false){
 $('#refresh').disabled=true;$('#status').textContent=refresh?'正在重新读取源码…':'正在读取事件…';
 try{
 const response=await fetch(refresh?'/api/refresh':'/api/catalog');const data=await response.json();if(!response.ok)throw Error(data.error||response.statusText);catalog=data;
 catalog.events.forEach(e=>e.search=resolveText([e.id,e.title,e.description,e.category,...e.regions.map(r=>catalog.regions[r]),...e.countries.map(c=>c.name+' '+c.tag),...e.options.flatMap(o=>[o.name,o.key,o.script])].join('\n')).toLowerCase());
 const oldCategory=$('#category').value,oldRegion=$('#region').value;
 $('#category').innerHTML='<option value="">全部系列</option>'+[...new Set(catalog.events.map(e=>e.category))].map(c=>`<option>${esc(c)}</option>`).join('');$('#category').value=oldCategory;
 $('#region').innerHTML='<option value="">全部地区</option>'+Object.entries(catalog.regions).map(([k,v])=>`<option value="${k}">${v}</option>`).join('');$('#region').value=oldRegion;
 selected=selected||decodeURIComponent(location.hash.slice(1))||'hbe.100'; if(selected.startsWith('hbe_draft_')&&catalog.events.some(e=>e.id===selected.replace('hbe_draft_','hbe_story_')))selected=selected.replace('hbe_draft_','hbe_story_');
 $('#status').textContent=`${data.stats.implemented} 已接入 / ${data.stats.drafts} 新增草稿 · ${data.stats.options} 选项${data.warnings.length?' · '+data.warnings.length+' 条校验提示':''}`;
 $('#status').title=`读取时间：${data.generatedAt}\n源码：${data.modPath}\n${data.warnings.join('\n')}`;
 $('#file-count').textContent=`${data.stats.files} 份事件脚本`;
 filterEvents();if(catalog.events.some(e=>e.id===selected))selectEvent(selected);
 }catch(e){$('#status').textContent='读取失败';showError(e.message);}finally{$('#refresh').disabled=false;}
}
document.addEventListener('click',e=>{const b=e.target.closest('[data-event]');if(b){const id=b.dataset.event;if(!filtered.some(x=>x.id===id))reset();selectEvent(id,b.classList.contains('event-link'));}});
$('#search').addEventListener('input',filterEvents);['category','region','visibility','choices','implementation'].forEach(id=>$('#'+id).addEventListener('change',filterEvents));
$('#reset').onclick=reset;$('#refresh').onclick=()=>load(true);$('#close-error').onclick=()=>$('#error-dialog').close();
$('#export').onclick=()=>{if(!catalog)return;const rows=catalog.events.map(({id,title,description,hidden,category,regions,options,source,line,status,chain,draftOffset})=>({id,title,description,hidden,category,regions,options,source,line,status,chain,draftOffset}));const blob=new Blob([JSON.stringify({generatedAt:catalog.generatedAt,modPath:catalog.modPath,events:rows},null,2)],{type:'application/json'});const link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download='bashu-events.json';link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000);};
document.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','SELECT','TEXTAREA'].includes(document.activeElement.tagName)){e.preventDefault();$('#search').focus();}if(['ArrowDown','ArrowUp'].includes(e.key)&&!['INPUT','SELECT','TEXTAREA'].includes(document.activeElement.tagName)){const i=filtered.findIndex(x=>x.id===selected);const n=filtered[i+(e.key==='ArrowDown'?1:-1)];if(n){e.preventDefault();selectEvent(n.id);document.querySelector('.event-row.active')?.scrollIntoView({block:'nearest'});}}});
load();
