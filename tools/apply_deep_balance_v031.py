"""Vanilla-calibrated dynamic financial values and bounded national output support."""
from pathlib import Path
from decimal import Decimal,ROUND_HALF_UP
import json,re,hashlib,shutil
from pdxscript import blocks,apply_edits,tokens
D=Decimal
def fmt(v):return f'{D(str(v)).normalize():f}'
def flats(t):
 ts=tokens(t);depth=0;out={}
 for i,x in enumerate(ts):
  if x.value=='{':depth+=1
  elif x.value=='}':depth-=1
  elif depth==0 and i+2<len(ts) and ts[i+1].value=='=' and ts[i+2].value!='{':out[x.value]=ts[i+2].value
 return out

def apply(out,root):
 out,root=Path(out),Path(root);report=dict(version='0.3.1',local_only=True,decision_prices=[],event_receipts=[],modifier_changes=[],pooled_support=[],excluded_transactions=[],reforms=[])
 values='# Uses the vanilla scaled_gold_for_effect economic base; payment and affordability share one value.\n'
 # Repeatable administration starts close to its old cost at an opening economic base of 4.
 for old in (2,3,4,5,6,8,10):
  scale=D(old)/4;values+=f'hbe_decision_bill_{old} = {{ value = hbe_event_economic_base multiply = {fmt(scale)} min = {fmt(D(old)/2)} max = {{ value = 5000 multiply = {fmt(scale)} }} }}\n'
 for coins in range(1,16):
  scale=D(coins)/4;values+=f'hbe_event_receipt_{coins} = {{ value = hbe_event_economic_base multiply = {fmt(scale)} min = {fmt(scale)} max = {{ value = 5000 multiply = {fmt(scale)} }} }}\n'
 values+='hbe_feast_success_receipt = { value = hbe_event_economic_base min = 1 max = 5000 }\n'
 (out/'in_game/common/script_values/hbe_deep_balance_values.txt').write_text(values,encoding='utf-8-sig')
 for p in (out/'in_game/common/decisions').glob('hbe*.txt'):
  t=p.read_text(encoding='utf-8-sig');edits=[]
  for key,_,s,e,_ in blocks(t,0):
   body=t[s:e];pot=next((b for b in blocks(body,0) if b[0]=='potential'),None)
   if pot and re.fullmatch(r'\s*always\s*=\s*no\s*',body[pot[2]:pot[3]]):continue
   m=re.findall(r'\badd_gold\s*=\s*-(\d+(?:\.\d+)?)',body)
   if not m:continue
   if key=='hbe_salt_repay':
    report['excluded_transactions'].append(dict(key=key,reason='Exact gold/debt repayment; do not change one side of a monetary contract.'));continue
   assert len(m)==1,key;old=D(m[0]);sv='hbe_decision_bill_'+fmt(old);assert int(old) in (2,3,4,5,6,8,10)
   body=re.sub(r'\badd_gold\s*=\s*-'+re.escape(m[0])+r'\b','add_gold = { value = '+sv+' multiply = -1 }',body)
   body=re.sub(r'\bgold\s*>=\s*'+re.escape(m[0])+r'\b','gold >= '+sv,body)
   # The paid labor policy additionally pays wages. Preserve the combined gate.
   body=re.sub(r'(value\s*=\s*hbe_paid_bill\s+add\s*=\s*)'+re.escape(m[0])+r'\b',lambda m:m[1]+sv,body)
   assert 'gold >= '+sv in body,key
   edits.append((s,e,body));report['decision_prices'].append(dict(decision=key,old=fmt(old),value=sv,scale=fmt(old/4),wages_extra=key.startswith('hbe_service_')))
  if edits:p.write_text(apply_edits(t,edits),encoding='utf-8-sig')
 # Sale proceeds/fines become economic-scale receipts; explicit debt/escrow stays nominal.
 changed_labels=set()
 for p in (out/'in_game/events').glob('hbe*.txt'):
  t=p.read_text(encoding='utf-8-sig');edits=[]
  for event,_,s,e,_ in blocks(t,0):
   if '.' not in event:continue
   b=t[s:e];oe=[]
   for _,_,a,z,_ in [x for x in blocks(b,0) if x[0]=='option']:
    o=b[a:z];name=flats(o).get('name','?')
    if re.search(r'hbe_salt_debt|hbe_feast_paid|hbe_project_funds',o):continue
    def receipt(m):
     value=D(m[1])
     if value<=0:return m[0]
     assert value==int(value) and value<=15,(name,value)
     sv='hbe_event_receipt_'+fmt(value);report['event_receipts'].append(dict(option=name,old=fmt(value),value=sv));changed_labels.add(name)
     return 'add_gold = { value = '+sv+' }'
    new=re.sub(r'\badd_gold\s*=\s*(\d+(?:\.\d+)?)',receipt,o)
    if new!=o:oe.append((a,z,new))
   if oe:edits.append((s,e,apply_edits(b,oe)))
  if edits:p.write_text(apply_edits(t,edits),encoding='utf-8-sig')
 # Grow the feast fee with income rather than freezing rich countries at six gold.
 p=out/'in_game/common/script_values/hbe_feast_values.txt';t=p.read_text(encoding='utf-8-sig');t=t.replace('max = 6','max = 64');p.write_text(t,encoding='utf-8-sig')
 # National production and food reference magnitudes: 2.5% and 5%. Hard ceilings 5%, 10%.
 changes_by_mod={}
 for folder in ('main_menu/common/static_modifiers','in_game/common/advances'):
  for p in (out/folder).glob('hbe*.txt'):
   t=p.read_text(encoding='utf-8-sig');edits=[]
   for key,_,s,e,_ in blocks(t,0):
    body=t[s:e];d=flats(body);change=[]
    for typ,cap in [('global_production_efficiency',D('.05')),('global_monthly_food_modifier',D('.10'))]:
     if typ not in d:continue
     try:old=D(d[typ])
     except:continue
     if old<=0:continue
     new=min(old,cap)
     if folder.endswith('advances') and typ=='global_production_efficiency':new=D('.04') if old<=D('.08') else cap
     if folder.endswith('advances') and typ=='global_monthly_food_modifier':new=D('.08') if old<=D('.12') else cap
     if key in ('hbe_feast_success','hbe_feast_common_reward') and typ=='global_monthly_food_modifier':new=D('.08')
     if new!=old:
      body=re.sub(r'\b'+typ+r'\s*=\s*'+re.escape(d[typ])+r'\b',typ+' = '+fmt(new),body,count=1)
      change.append(dict(type=typ,before=fmt(old),after=fmt(new),vanilla_reference='.025' if typ=='global_production_efficiency' else '.05'))
    # Previously unscaled feast leadership rewards are also brought to the 0.7 pass.
    extras={'hbe_feast_common_reward':{'global_construction_speed':'.14'},'hbe_feast_local_reward':{'global_merchant_capacity_modifier':'.18','cultural_influence_modifier':'.14'}}.get(key,{})
    for typ,new in extras.items():
     if typ in d and D(d[typ])>D(new):
      body=re.sub(r'\b'+typ+r'\s*=\s*'+re.escape(d[typ])+r'\b',typ+' = '+new,body,count=1);change.append(dict(type=typ,before=d[typ],after=new))
    if change:edits.append((s,e,body));report['modifier_changes'].append(dict(definition=key,file=p.relative_to(out).as_posix(),changes=change))
   if edits:p.write_text(apply_edits(t,edits),encoding='utf-8-sig')
 # Temporary national output arrangements share a native strongest-value slot,
 # preventing unrelated story IDs from stacking the same efficiency indefinitely.
 paths=[p for folder in ('in_game/events','in_game/common/scripted_effects','in_game/common/decisions','in_game/common/on_action') for p in (out/folder).glob('hbe*.txt')]
 usages={}
 for p in paths:
  t=p.read_text(encoding='utf-8-sig')
  for k,_,s,e,_ in blocks(t):
   if k=='add_country_modifier':
    d=flats(t[s:e]);key=d.get('modifier')
    if key:usages.setdefault(key,[]).append(d)
 pooled={};empty=set()
 for p in (out/'main_menu/common/static_modifiers').glob('hbe*.txt'):
  t=p.read_text(encoding='utf-8-sig');edits=[]
  for key,outer,s,e,end in blocks(t,0):
   if key not in usages:continue
   use=usages[key]
   if not all(any(k in u and re.fullmatch(r'\d+(?:\.\d+)?',u[k]) and D(u[k])>0 for k in ('years','months','days')) for u in use):continue
   body=t[s:e];d=flats(body);parts={typ:D(d[typ]) for typ in ('global_production_efficiency','global_monthly_food_modifier') if typ in d and D(d[typ])>0}
   if not parts:continue
   for typ in parts:body=re.sub(r'\b'+typ+r'\s*=\s*-?\d+(?:\.\d+)?','',body)
   pooled[key]=parts
   if not tokens(body):empty.add(key);edits.append((outer,end,''))
   else:edits.append((s,e,body))
   report['pooled_support'].append(dict(modifier=key,values={k:fmt(v) for k,v in parts.items()},empty_original=key in empty))
  if edits:p.write_text(apply_edits(t,edits),encoding='utf-8-sig')
 for p in paths:
  t=p.read_text(encoding='utf-8-sig');edits=[]
  for kind,outer,s,e,end in blocks(t):
   if kind!='add_country_modifier':continue
   d=flats(t[s:e]);key=d.get('modifier')
   if key not in pooled:continue
   duration=' '.join(k+' = '+d[k] for k in ('years','months','days') if k in d)
   extra=[]
   for typ,value in pooled[key].items():
    shared='hbe_shared_production_support' if typ=='global_production_efficiency' else 'hbe_shared_food_support'
    extra.append('add_country_modifier = { modifier = '+shared+' size = '+fmt(value*100)+' '+duration+' mode = set_to_largest_and_extend }')
   text=('' if key in empty else t[outer:end]+' ')+' '.join(extra)
   edits.append((outer,end,text))
  # Deleted empty definitions must not leave meaningless removals or dangling refs.
  if edits:t=apply_edits(t,edits)
  for key in empty:t=re.sub(r'\bremove_country_modifier\s*=\s*'+re.escape(key)+r'\b','',t)
  if edits or any(k in p.read_text(encoding='utf-8-sig') for k in empty):p.write_text(t,encoding='utf-8-sig')
 p=out/'main_menu/common/static_modifiers/hbe_deep_support_modifiers.txt';p.write_text('hbe_shared_production_support = { global_production_efficiency = 0.01 }\nhbe_shared_food_support = { global_monthly_food_modifier = 0.01 }\n',encoding='utf-8-sig')
 # Success still pays rewards, but gold is economic-scale and prestige/credit are moderate.
 p=out/'in_game/common/scripted_effects/hbe_banquet_effects.txt';t=p.read_text(encoding='utf-8-sig');t=t.replace('add_gold = 6 add_prestige = 3 change_variable = { name = hbe_yiqi add = 5 }','add_gold = { value = hbe_feast_success_receipt } add_prestige = 2 change_variable = { name = hbe_yiqi add = 4 }');p.write_text(t,encoding='utf-8-sig')
 # copy_from already supplies combat_power=1 for these two age-2 types.
 p=out/'in_game/common/unit_types/hbe_civic_units.txt';t=p.read_text(encoding='utf-8-sig');edits=[]
 for key,_,s,e,_ in blocks(t,0):
  if key not in ('hbe_trained_river','hbe_permanent_pass'):continue
  body=t[s:e];old=flats(body)['combat_power'];new='.20' if key=='hbe_trained_river' else '.15';body=re.sub(r'\bcombat_power\s*=\s*\S+','combat_power = '+new,body);edits.append((s,e,body))
  report.setdefault('units',[]).append(dict(unit=key,old_added_power=old,new_added_power=new,inherited_power=1,effective_power=1+float(new)))
 if edits:p.write_text(apply_edits(t,edits),encoding='utf-8-sig')
 # Two complementary minor reforms, offered through the native reform UI.
 reforms='''hbe_prefectural_council = {
 age = age_1_traditions major = no unique = yes block_for_rebel = yes
 potential = { is_member_of_international_organization = international_organization:hbe_empire }
 allow = { has_advance = hbe_tech_common_1 }
 years = 5
 country_modifier = {
  potential_trigger = { is_member_of_international_organization = international_organization:hbe_empire }
  global_monthly_control = 0.01 global_monthly_literacy = 0.005
  burghers_estate_target_satisfaction = 0.02 nobles_estate_target_satisfaction = -0.02
 }
 ai_will_do = { value = 4 }
}
hbe_mountain_river_dispatch = {
 age = age_1_traditions major = no unique = yes block_for_rebel = yes
 potential = { is_member_of_international_organization = international_organization:hbe_empire }
 allow = { has_advance = hbe_tech_common_2 }
 years = 5
 country_modifier = {
  potential_trigger = { is_member_of_international_organization = international_organization:hbe_empire }
  global_merchant_capacity_modifier = 0.10 merchant_maintenance_efficiency = 0.05 tax_income_efficiency = -0.02
 }
 ai_will_do = { value = 3 }
}
'''
 p=out/'in_game/common/government_reforms/hbe_shared_reforms.txt';p.parent.mkdir(parents=True,exist_ok=True);p.write_text(reforms,encoding='utf-8-sig')
 for reform,source in [('hbe_prefectural_council','hbe_assembly_hall'),('hbe_mountain_river_dispatch','hbe_river_warehouse')]:
  p=out/'main_menu/gfx/interface/icons/government_reforms'/f'{reform}.dds';p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(out/'main_menu/gfx/interface/icons/buildings'/f'{source}.dds',p)
  report['reforms'].append(dict(reform=reform,years_to_implement=5,major=False,government_restriction=None))
 for lang in ('simp_chinese','english'):
  zh=lang=='simp_chinese';loc={
   'hbe_shared_production_support': '作坊生产筹备' if zh else 'Manufacturing Arrangements',
   'hbe_shared_food_support': '粮务协作' if zh else 'Food Supply Arrangements',
   'hbe_shared_production_support_desc': '同类短期生产筹备取较强效果并延续期限，不重复叠加。合计最多提高全局生产效率5%。' if zh else 'Temporary production arrangements retain the strongest effect and extend its duration; they do not stack. Maximum production efficiency bonus: 5%.',
   'hbe_shared_food_support_desc': '同类短期粮务协作取较强效果并延续期限，不重复叠加。合计最多提高全局粮食产出10%。' if zh else 'Temporary food arrangements retain the strongest effect and extend its duration; they do not stack. Maximum food output bonus: 10%.',
   'hbe_prefectural_council':'府州公议' if zh else 'Prefectural Councils',
   'hbe_prefectural_council_desc': '各府的水口、田界与工役，不再只凭一封官札处置。市镇与乡里的代表轮流入府，书吏将旧契与新议编成簿册，主持者须向实际承担钱粮的人说明缘由。公议使政令与传习更有根基，也收回了一部分旧门第独断的权力。' if zh else 'Representatives from towns and villages bring water rights, land boundaries and labor obligations before the prefecture. Clerks keep old contracts beside the new decisions, and officials answer to those who supply money and labor. Public deliberation strengthens administration and learning while curbing noble discretion.',
   'hbe_mountain_river_dispatch':'山川转运' if zh else 'Mountain and River Dispatch',
   'hbe_mountain_river_dispatch_desc': '沿江的仓站与越岭的驿铺共用货簿，船期、马程和交割凭券得以互相衔接。诸侯仍掌各自的商路，却须按同一份约定接济过境货队。转运使商人少走冤路，也要府库长期拨出一份钱粮，承担仓站与护行的责任。' if zh else 'River warehouses and mountain relay stations share cargo records, linking sailing dates, caravan stages and delivery warrants. Each prince retains control of local routes while supporting through traffic under a common agreement. Merchants gain a more reliable network, financed by a continuing claim on tax revenue.'}
  for key in ('hbe_shared_production_support','hbe_shared_food_support'):loc['STATIC_MODIFIER_NAME_'+key]=loc[key]
  p=out/f'main_menu/localization/{lang}/hbe_deep_balance_l_{lang}.yml';p.write_text('l_'+lang+':\n'+'\n'.join(' '+k+': '+json.dumps(v,ensure_ascii=False) for k,v in loc.items())+'\n',encoding='utf-8-sig')
  # Update old fixed numerical guides from the actual current implementation.
  for p in (out/f'main_menu/localization/{lang}').glob('hbe*.yml'):
   t=p.read_text(encoding='utf-8-sig');old=t
   def labels(m):
    if m[1] not in changed_labels:return m[0]
    v=re.sub(r'(?:\d+(?:\.\d+)?|[零一二三四五六七八九十百两]+)\s*(?:金币|金)','款项',m[0])
    return re.sub(r'\b\d+(?:\.\d+)?\s+(?:gold|ducats)\b','funds',v,flags=re.I)
   t=re.sub(r'(?m)^ (\S+):[^\n]*$',labels,t)
   if p.name=='hbe_l_'+lang+'.yml':
    replacement='参与：建设+11%、商人容量+11%（两年）。\\n成功：依经济规模发放金币、2威望、4义气；生产效率最多+5%、粮食最多+8%（三年）。\\n领先派额外：共建派建设+14%，兴业派商人容量+18%、文化影响力+14%。同类短期生产和粮食安排取较强效果，不叠加。\\n派内金币与威望分红另计，奖金池规则不变。' if zh else 'Participation: construction and merchant capacity +11% for two years. Success: economy-scaled gold, 2 prestige and 4 fraternity; up to +5% production efficiency and +8% food output for three years. Leading party: Common Works adds +14% construction; Enterprise adds +18% merchant capacity and +14% cultural influence. Same-kind temporary output arrangements do not stack. Party dividends remain separate.'
    replacement=replacement.replace(r'\\n','\n').replace(r'\n','\n')
    t=re.sub(r'(?m)^ HBE_FEAST_REWARDS:.*$',lambda m:' HBE_FEAST_REWARDS: '+json.dumps(replacement,ensure_ascii=False),t)
    t=t.replace('建设+20%','建设+14%').replace('粮食+15%','粮食+8%').replace('商人容量+25%','商人容量+18%').replace('文化影响力+20%','文化影响力+14%')
   if t!=old:p.write_text(t,encoding='utf-8-sig')
 report['national_output_caps']=dict(global_production_efficiency=.05,global_monthly_food_modifier=.10,vanilla_references=dict(global_production_efficiency=.025,global_monthly_food_modifier=.05),max_ratio=2)
 report['kept']=dict(prestige='Existing event magnitudes 1-5 match native minor rewards.',literacy='Monthly 0.02 matches native upper technology examples; max-literacy uses already_percent, not fraction.',goods='Global pop demand and premium reference prices retained; reference margins are not realized profits.',dividends='Per-contributor virtual bonus 8-64 and logarithmic 1/2/3 weights retained; 64 is a pool contribution cap, not a payout cap.',burden='Existing threshold penalties, policy tradeoffs and conditional peacetime recovery retained.',loan_repayment='Fixed monetary debt transactions retain matching nominal amounts.')
 from deep_output_support import apply as refine_supports
 from deep_support_duration import repair as repair_support_durations
 refine_supports(out,report)
 repair_support_durations(out,report)
 return report
