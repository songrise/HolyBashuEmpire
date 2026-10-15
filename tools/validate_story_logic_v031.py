"""Explore the generated scripts' chain states, including rejected and legacy paths.

This deliberately small interpreter covers sequencing only, not world economics.
The native engine fixture separately verifies the Jomini guards and callbacks.
"""
from pathlib import Path
import importlib.util,itertools,json,re,sys

def validate_story_logic(mod,root,manifest,loc,check):
 if 'story_logic_v031' not in manifest:return {}
 sys.path.insert(0,str(root/'data'));sys.path.insert(0,str(root/'tools'))
 from story_blueprints import LONG
 from short_stories import SHORT
 from shared_stories import SHORT as SHARED
 spec=importlib.util.spec_from_file_location('hbe_logic_catalog',root/'devtools/event-browser/catalog.py');cat=importlib.util.module_from_spec(spec);spec.loader.exec_module(cat)
 parse,field=cat.parse,cat.field
 events={}
 for p in (mod/'in_game/events').glob('*.txt'):
  events.update({n['key']:n['value'] for n in parse(p.read_text(encoding='utf-8-sig')) if re.fullmatch(r'hbe\w*\.\d+',n['key'])})
 scheduler=field(parse((mod/'in_game/common/scripted_effects/hbe_story_scheduler.txt').read_text(encoding='utf-8-sig')),'hbe_story_monthly')
 class State:
  def __init__(self,tag='BAB',year=1400):self.tag=tag;self.year=year;self.gold=1000000;self.v={};self.queue=[];self.timers={};self.mods=[]
  def clone(self):
   other=State(self.tag,self.year);other.gold=self.gold;other.v=self.v.copy();other.timers=self.timers.copy();other.queue=self.queue.copy();other.mods=self.mods.copy();return other
  def expire(self):
   elapsed=min(self.timers.values(),default=0)
   self.year+=elapsed/12
   for key,duration in list(self.timers.items()):
    if duration<=elapsed:self.v.pop(key,None);self.timers.pop(key)
    else:self.timers[key]=duration-elapsed
 def cond(nodes,s):
  if not isinstance(nodes,list):raise AssertionError(nodes)
  for n in nodes:
   k,v,op=n['key'],n['value'],n['op']
   if k in ('AND','limit','trigger'):ok=cond(v,s)
   elif k=='OR':ok=any(cond([x],s) for x in v)
   elif k=='NOT':ok=not any(cond([x],s) for x in v)
   elif k=='always':ok=v=='yes'
   elif k=='hbe_is_prince':ok=True
   elif k=='has_or_had_tag':ok=s.tag==v
   elif k=='has_variable':ok=v in s.v
   elif k=='custom_tooltip':ok=cond([x for x in v if x['key']!='text'],s)
   elif k=='text':continue
   elif k=='gold':
    # Fixed or dynamic charges must both fail at zero funds. Exact dynamic
    # pricing is outside this sequencing model and is unchanged by this patch.
    cost=float(v) if re.fullmatch(r'[\d.]+',v) else 1
    ok=s.gold>=cost
   elif k.startswith('var:') or k=='current_year':
    a=s.year if k=='current_year' else s.v.get(k[4:],0);b=float(v)
    ok={'=':lambda:a==b,'==':lambda:a==b,'>=':lambda:a>=b,'<=':lambda:a<=b,'>':lambda:a>b,'<':lambda:a<b,'!=':lambda:a!=b}[op]()
   else:raise AssertionError('Unsupported sequencing condition: '+k)
   if not ok:return False
  return True
 def effect(nodes,s):
  for n in nodes:
   k,v=n['key'],n['value']
   if k in ('hidden_effect','immediate'):effect(v,s)
   elif k=='if':
    if cond(field(v,'limit',[]),s):effect([x for x in v if x['key']!='limit'],s)
   elif k=='set_variable':
    if isinstance(v,list):
     key=field(v,'name');value=field(v,'value','yes');s.v[key]=True if value=='yes' else float(value)
     duration=float(field(v,'years',0))*12+float(field(v,'months',0))
     if duration:s.timers[key]=duration
    else:s.v[v]=True
   elif k=='remove_variable':s.v.pop(v,None);s.timers.pop(v,None)
   elif k=='change_variable':
    key=field(v,'name');s.v[key]=s.v.get(key,0)+float(field(v,'add',0))
   elif k in ('trigger_event_non_silently','trigger_event_silently'):s.queue.append(field(v,'id'))
   elif k=='add_country_modifier':s.mods.append(field(v,'modifier'))
   elif k in ('trigger','name','ai_chance','custom_tooltip','hbe_grant_food_support_years','hbe_grant_production_support_years') or k.startswith('add_'):pass
   else:raise AssertionError('Unsupported chain effect: '+k)
 def available(eid,s):return cond(field(events[eid],'trigger',[]),s)
 def options(eid):return [n['value'] for n in events[eid] if n['key']=='option']
 def select(eid,letter,s):
  opt=next(o for o in options(eid) if field(o,'name')==eid+'.'+letter)
  assert cond(field(opt,'trigger',[]),s),(eid,letter,s.v)
  effect(opt,s)
 def enter(eid,s):
  assert available(eid,s),(eid,s.v)
  effect(field(events[eid],'immediate',[]),s)
 totals={'regional_complete_paths':0,'migration_complete_paths':0,'short_complete_paths':0,'abort_cases':0,'scheduler_cases':0,'afterword_cases':0,'zero_gold_cases':0}
 def funds_escape(eid,s):
  poor=s.clone();poor.gold=0
  assert any(cond(field(o,'trigger',[]),poor) for o in options(eid)),eid
  totals['zero_gold_cases']+=1
 for region,story in LONG.items():
  p='hbe_story_'+region;tag=story['tags'].split()[0]
  seed=State(tag,story['start_year']);seed.v[p+'_phase']=0;seed.v[p+'_direction']=0
  early=seed.clone();early.year-=1;assert not available(p+'.1',early)
  endings=[p+'.201',p+'.202']
  def visit(i,s):
   eid=p+'.'+str(i+1);enter(eid,s);funds_escape(eid,s)
   # The same state cannot enter a later stage.
   if i<7:assert not available(p+'.'+str(i+2),s)
   abort=s.clone();select(eid,'d' if i<7 else 'c',abort)
   assert abort.v[p+'_closed'] and not any(available(e,abort) for e in endings)
   totals['abort_cases']+=1
   if i==7:
    choices=[o for o in options(eid) if field(o,'name').rsplit('.',1)[-1] in ('a','b') and cond(field(o,'trigger',[]),s)]
    assert len(choices)==1
    n=1 if s.v[p+'_direction']>=0 else 2
    finish=s.clone();select(eid,'ab'[n-1],finish)
    assert [e for e in endings if available(e,finish)]==[endings[n-1]]
    legacy=finish.clone();legacy.v.pop(p+'_selected_ending');assert [e for e in endings if available(e,legacy)]==[endings[n-1]]
    select(endings[n-1],'a',finish)
    assert not any(available(e,finish) for e in endings)
    assert len([m for m in finish.mods if m.startswith('hbe_story_ending_')])==1
    totals['regional_complete_paths']+=1;return
   for letter in 'abc':
    nxt=s.clone();select(eid,letter,nxt)
    assert not available(p+'.'+str(i+2),nxt)
    nxt.expire();visit(i+1,nxt)
  visit(0,seed)
  # Run the actual monthly scheduler twice: pending prevents duplicate dispatch.
  s=State(tag,story['start_year']);effect(scheduler,s)
  assert s.queue.count(p+'.1')==1
  effect(scheduler,s);assert s.queue.count(p+'.1')==1
  select(p+'.1','a',s);s.queue=[];effect(scheduler,s);assert p+'.2' not in s.queue
  s.expire();effect(scheduler,s);assert s.queue.count(p+'.2')==1
  totals['scheduler_cases']+=3
  check(region+' exhaustive chapter routes, stop paths, exclusive endings and pending lock',True)
 seed=State(year=1345);seed.v.update(hbe_migration_phase=0,hbe_migration_acceptance=0)
 def migrate(i,s):
  eid='hbe_migration.'+str(i+1);enter(eid,s);funds_escape(eid,s)
  if i==9:
   candidates=[o for o in options(eid)[:2] if cond(field(o,'trigger',[]),s)];assert len(candidates)==1
   n=1 if s.v['hbe_migration_acceptance']>=6 else 2
   done=s.clone();select(eid,'ab'[n-1],done)
   assert done.v['hbe_migration_closed'] and done.v['hbe_migration_phase']==10
   assert 'hbe_migration_ending_'+str(n) in done.mods
   assert not available(eid,done)
   abort=s.clone();select(eid,'c',abort);assert not any(m.startswith('hbe_migration_ending_') for m in abort.mods)
   totals['migration_complete_paths']+=1;totals['abort_cases']+=1;return
  for letter in 'abc':
   nxt=s.clone();select(eid,letter,nxt);assert not available('hbe_migration.'+str(i+2),nxt);nxt.expire();migrate(i+1,nxt)
 migrate(0,seed);check('migration all nine-decision permutations reach exactly one valid ending',True)
 variants=field(field(events['hbe_migration.2'],'desc'),'first_valid')
 for n,key in enumerate(('open','sponsored','transit'),1):
  s=State();s.v['hbe_migration_first_policy']=n
  selected=next(field(x['value'],'desc') for x in variants if cond(field(x['value'],'trigger',[]),s))
  expected='hbe_migration.2.desc.'+('after_'+'abc'[n-1] if 'story_narratives_v031' in manifest else key)
  assert selected==expected
 check('migration second chapter follows admission sponsorship or transit, with old-save fallback',bool(cat.scalar(field(events['hbe_migration.2'],'desc'))=='hbe_migration.2.desc'))
 counts={}
 for story in SHORT+SHARED:
  r=story['region'];index=counts.get(r,0);counts[r]=index+1;p=f'hbe_short_{r}_{index+1}'
  ids=[f'hbe_short_{r}.{index*10+c}' for c in (1,2,3)]
  for letters in itertools.product('abc',repeat=3):
   s=State(story['tags'].split()[0] if story['tags'] else 'BAB',1340)
   for i,eid in enumerate(ids):
    enter(eid,s);funds_escape(eid,s);abort=s.clone();select(eid,'d',abort)
    assert abort.v[p+'_phase']==3 and not any(available(e,abort) for e in ids)
    totals['abort_cases']+=1
    select(eid,letters[i],s)
    if i<2:assert not available(ids[i+1],s);s.expire()
   assert s.v[p+'_phase']==3 and not any(available(e,s) for e in ids)
   assert len([e for e in s.queue if e.startswith('hbe_ending.')])==1
   totals['short_complete_paths']+=1
  s=State(story['tags'].split()[0] if story['tags'] else 'BAB');enter(ids[0],s);select(ids[0],'a',s)
  s.queue=[];effect(scheduler,s);assert ids[1] not in s.queue
  s.expire();effect(scheduler,s);assert s.queue.count(ids[1])==1
  effect(scheduler,s);assert s.queue.count(ids[1])==1;totals['scheduler_cases']+=3
  check(story['name']+' all 27 completed paths, aborts and cooldown/pending locks',True)
 art=json.loads((root/'data/ending_art_v031.json').read_text(encoding='utf-8'));groups={}
 for row in art['hooks']:groups.setdefault(row['pending'].rsplit('_',1)[0],[]).append(row)
 from pdxscript import blocks
 raw={}
 for path in (mod/'in_game/events').glob('*.txt'):
  t=path.read_text(encoding='utf-8-sig');raw.update({k:t[b:e] for k,_,b,e,_ in blocks(t,0)})
 def hookcode(h):
  body=raw[h['source_option'].rsplit('.',1)[0]]
  choice=next(body[b:e] for k,_,b,e,_ in blocks(body,0) if k=='option' and re.search(r'\bname\s*=\s*'+re.escape(h['source_option'])+r'\b',body[b:e]))
  return parse(re.search(r'# HBE_ENDING_PRESENTATION_BEGIN\s*(.*?)\s*# HBE_ENDING_PRESENTATION_END',choice,re.S).group(1))
 for base,hooks in groups.items():
  for h in hooks:
   s=State();effect(hookcode(h),s)
   for other in hooks:effect(hookcode(other),s)
   assert s.queue==[h['event']]
   enter(h['event'],s)
   assert base+'_completed' in s.v and h['pending']+'_seen' in s.v
   assert not any(available(o['event'],s) for o in hooks)
   s.queue=[]
   for other in hooks:effect(hookcode(other),s)
   assert not s.queue
   legacy=State();legacy.v[h['pending']+'_seen']=True
   for other in hooks:effect(hookcode(other),legacy)
   assert not legacy.queue;totals['afterword_cases']+=1
 check('all 101 afterword routes execute once per chain, including legacy flags and competing hooks',totals['afterword_cases']==101)
 check('all generated event calls resolve',all(field(n['value'],'id') in events for body in events.values() for n in walk(body) if n['key'] in ('trigger_event_non_silently','trigger_event_silently')))
 check('complete path coverage matches 7x2187, 19683 and 33x27',totals['regional_complete_paths']==15309 and totals['migration_complete_paths']==19683 and totals['short_complete_paths']==891)
 return totals

def walk(nodes):
 for n in nodes:
  yield n
  if isinstance(n['value'],list):yield from walk(n['value'])

if __name__=='__main__':
 root=Path(__file__).resolve().parents[1];mod=root/'mod/holy_bashu_empire';checks=[]
 def check(name,ok):
  checks.append(dict(check=name,passed=bool(ok)))
  assert ok,name
 result=validate_story_logic(mod,root,json.loads((mod/'build_manifest.json').read_text()),None,check)
 print(json.dumps(dict(checks=len(checks),totals=result)))
