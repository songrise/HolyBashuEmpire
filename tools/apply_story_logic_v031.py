"""Guard authored chain transitions and preserve the first migration decision in prose."""
from build_support import snapshot_files
from pathlib import Path
import argparse, json, re, sys
from pdxscript import blocks

def apply(out, root, game=None):
 out,root=Path(out),Path(root)
 sys.path[:0]=[str(root/'data'),str(root/'tools')]
 from story_logic_v031 import REPLACEMENTS,MIGRATION_LAND
 from story_blueprints import LONG
 from short_stories import SHORT
 from shared_stories import SHORT as SHARED
 counts={};changed=[]
 def put(rel,t):
  p=out/rel;p.write_text(t.rstrip()+'\n',encoding='utf-8-sig',newline='\n' if 'hbe_story_l_' in rel else '\r\n');changed.append(rel)
 def event_patch(t,eid,fn):
  b,e=next((b,e) for k,_,b,e,_ in blocks(t,0) if k==eid)
  return t[:b]+fn(t[b:e])+t[e:]
 def extra(body,key,script):
  marker='# HBE_CHAIN_LOGIC_'+key.upper()
  script=re.sub(r'\s+',' ',script).strip()
  span=next(((b,e) for k,_,b,e,_ in blocks(body,0) if k==key),None)
  if span:
   b,e=span;old=body[b:e]
   old=re.sub(r'\s*'+re.escape(marker)+r'_BEGIN.*?'+re.escape(marker)+r'_END\s*','\n',old,flags=re.S)
   replacement=old.rstrip()+'\n '+marker+'_BEGIN\n '+script+'\n '+marker+'_END\n '
   return body[:b]+replacement+body[e:]
  return body+'\n '+key+' = { '+script+' }\n'
 def option_extra(body,eid,letter,script):
  b,e=next((b,e) for k,_,b,e,_ in blocks(body,0) if k=='option' and re.search(r'\bname\s*=\s*'+re.escape(eid+'.'+letter)+r'\b',body[b:e]))
  old=body[b:e]
  old=re.sub(r'\s*# HBE_CHAIN_CHOICE_BEGIN.*?# HBE_CHAIN_CHOICE_END\s*','\n',old,flags=re.S)
  return body[:b]+old.rstrip()+'\n # HBE_CHAIN_CHOICE_BEGIN\n hidden_effect = { '+script+' }\n # HBE_CHAIN_CHOICE_END\n '+body[e:]
 for region,story in LONG.items():
  rel=f'in_game/events/hbe_story_{region}.txt';t=(out/rel).read_text(encoding='utf-8-sig');p='hbe_story_'+region
  for i in range(1,9):
   eid=p+'.'+str(i)
   guard=f'NOT = {{ has_variable = {p}_clock }}'+(f' current_year >= {story["start_year"]}' if i==1 else '')
   t=event_patch(t,eid,lambda b:extra(b,'trigger',guard))
  for n,sign in ((1,'>= 0'),(2,'< 0')):
   t=event_patch(t,p+'.8',lambda b:option_extra(b,p+'.8',chr(96+n),f'set_variable = {{ name = {p}_selected_ending value = {n} }}'))
   guard=f'var:{p}_phase = 8 NOT = {{ has_variable = {p}_abandoned }} OR = {{ var:{p}_selected_ending = {n} AND = {{ NOT = {{ has_variable = {p}_selected_ending }} var:{p}_direction {sign} }} }}'
   t=event_patch(t,p+'.'+str(200+n),lambda b:extra(b,'trigger',guard))
  t=event_patch(t,p+'.8',lambda b:option_extra(b,p+'.8','c',f'set_variable = {p}_abandoned'))
  put(rel,t)
 for story in SHORT+SHARED:
  r=story['region'];index=counts.get(r,0);counts[r]=index+1;p=f'hbe_short_{r}_{index+1}'
  rel=f'in_game/events/hbe_short_{r}.txt';t=(out/rel).read_text(encoding='utf-8-sig')
  for chapter in (2,3):
   t=event_patch(t,f'hbe_short_{r}.{index*10+chapter}',lambda b:extra(b,'trigger',f'has_variable = {p}_seen'))
  put(rel,t)
 rel='in_game/events/hbe_migration_events.txt';t=(out/rel).read_text(encoding='utf-8-sig')
 for chapter in range(1,11):
  t=event_patch(t,f'hbe_migration.{chapter}',lambda b:extra(b,'trigger','NOT = { has_variable = hbe_migration_clock }'))
 for n in (1,2,3):t=event_patch(t,'hbe_migration.1',lambda b:option_extra(b,'hbe_migration.1',chr(96+n),f'set_variable = {{ name = hbe_migration_first_policy value = {n} }}'))
 desc='desc = { first_valid = { '+' '.join(f'triggered_desc = {{ trigger = {{ var:hbe_migration_first_policy = {n} }} desc = hbe_migration.2.desc.{key} }}' for n,key in enumerate(('open','sponsored','transit'),1))+' triggered_desc = { desc = hbe_migration.2.desc } } }'
 def dynamic(b):
  # Handle either a fresh scalar description or this pass's existing block.
  span=next(((start,end) for key,start,_,_,end in blocks(b,0) if key=='desc'),None)
  if span:return b[:span[0]]+desc+b[span[1]:]
  b,n=re.subn(r'\bdesc\s*=\s*hbe_migration\.2\.desc\b',lambda m:desc,b,count=1);assert n==1
  return b
 t=event_patch(t,'hbe_migration.2',dynamic);put(rel,t)
 # Same edits in generated localization; original authoring text is updated alongside this pass.
 replacements=[x for pairs in REPLACEMENTS.values() for x in pairs]
 loc_count=0
 for lang in ('simp_chinese','english'):
  rel=f'main_menu/localization/{lang}/hbe_story_l_{lang}.yml';t=(out/rel).read_text(encoding='utf-8-sig')
  for old,new in replacements:t=t.replace(old,new)
  rows=t.splitlines();loc={}
  for line in rows:
   m=re.match(r'\s*(\S+):\s*(".*")$',line)
   if m:loc[m[1]]=json.loads(m[2])
  key='hbe_migration.2.desc';old=loc[key];tail=old[old.index('\n\n我们若'):]
  for suffix,opening in MIGRATION_LAND.items():
   k=key if suffix=='legacy' else key+'.'+suffix;loc[k]=opening+tail
  # Final chapter must not imply that every branch already granted temporary residence.
  loc['hbe_migration.10.desc']=loc['hbe_migration.10.desc'].replace('发现当年那行“暂准居留”还没有人改过。','看见早年的过境凭记、担保字据与临时居留批语仍夹在一起，没有一份办法适用于所有后来的人。')
  t='l_'+lang+':\n'+'\n'.join(' '+k+': '+json.dumps(v,ensure_ascii=False) for k,v in loc.items())
  put(rel,t);loc_count+=len(replacements)+4
 mp=out/'build_manifest.json';m=json.loads(mp.read_text(encoding='utf-8'))
 result=dict(regional_chains=7,migration_chains=1,short_chains=33,guarded_chapters=132,guarded_regional_endings=14,legacy_ending_fallback=True,migration_first_policy_variants=3,narrative_replacements=len(replacements),economic_rewards_changed=False,files=sorted(set(changed)))
 m['story_logic_v031']=result
 m['files']=snapshot_files(out)
 mp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 (root/'data/story_logic_v031.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False));return result

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--root',required=True,type=Path);a=ap.parse_args();apply(a.root/'mod/holy_bashu_empire',a.root)
