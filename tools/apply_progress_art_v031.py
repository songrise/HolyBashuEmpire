"""Select existing branch paintings during a story, without changing its rewards."""
from build_support import snapshot_files
from pathlib import Path
import argparse, json, re, sys
from pdxscript import blocks

def apply(out, root, game=None):
 out, root = Path(out), Path(root)
 sys.path[:0] = [str(root/'data'), str(root/'tools')]
 from ending_texts_v031 import LONG_ART, SHORT_ENDINGS
 from short_stories import SHORT
 from shared_stories import SHORT as SHARED
 images=[];scenes=[];database=[];changed=[];routes=[]
 shell=(out/'in_game/gfx/scenes/hbe_ending_scenes.txt').read_text(encoding='utf-8-sig')
 shell=next(shell[b:e] for k,_,b,e,_ in blocks(shell,0) if k=='hbe_ending_scene_panda_sanctuary')
 def put(rel,text):
  p=out/rel;p.parent.mkdir(parents=True,exist_ok=True)
  p.write_text(text.rstrip()+'\n',encoding='utf-8-sig',newline='\r\n');changed.append(rel)
 def event_patch(t,eid,fn):
  b,e=next((b,e) for k,_,b,e,_ in blocks(t,0) if k==eid)
  return t[:b]+fn(t[b:e])+t[e:]
 def change_tag(body,key):
  body,n=re.subn(r'illustration_tags\s*=\s*\{[^}]*\}',f'illustration_tags = {{ 1000 = hbe_progress_art_{key} }}',body,count=1)
  assert n==1;return body
 def choice(body,eid,letter,var,n):
  b,e=next((b,e) for k,_,b,e,_ in blocks(body,0) if k=='option' and re.search(r'\bname\s*=\s*'+re.escape(eid+'.'+letter)+r'\b',body[b:e]))
  old=re.sub(r'\s*# HBE_PROGRESS_ART_BEGIN.*?# HBE_PROGRESS_ART_END\s*','\n',body[b:e],flags=re.S)
  return body[:b]+old.rstrip()+f'\n # HBE_PROGRESS_ART_BEGIN\n hidden_effect = {{ set_variable = {{ name = {var} value = {n} }} }}\n # HBE_PROGRESS_ART_END\n '+body[e:]
 def register(key,base,variants):
  bg='hbe_progress_background_'+key
  candidates=[f'illustration_image = {{ texture_file = "gfx/interface/hbe/events/{base}.dds" priority = 1 scope = country trigger = {{ always = yes }} }}']
  # Use the already-exported paths; base images have a separate directory.
  source=(out/'in_game/gfx/images/hbe_story_backgrounds.txt').read_text(encoding='utf-8-sig')
  entry=next(source[b:e] for k,_,b,e,_ in blocks(source,0) if k=='hbe_story_background_'+base)
  base_texture=re.search(r'texture_file\s*=\s*"([^"]+)"',entry)[1]
  candidates[0]=candidates[0].replace(f'gfx/interface/hbe/events/{base}.dds',base_texture)
  for art,trigger in variants:
   texture=f'gfx/interface/hbe/ending_events/{art}.dds'
   if not (out/'main_menu'/texture).exists():
    existing=next(source[b:e] for k,_,b,e,_ in blocks(source,0) if k=='hbe_story_background_'+art)
    texture=re.search(r'texture_file\s*=\s*"([^"]+)"',existing)[1]
   candidates.append(f'illustration_image = {{ texture_file = "{texture}" priority = 100 scope = country trigger = {{ {trigger} }} }}')
  images.append(bg+' = { tag = "'+bg+'"\n '+'\n '.join(candidates)+'\n}')
  scenes.append('hbe_progress_scene_'+key+' = {'+shell.replace('hbe_ending_background_panda_sanctuary',bg)+'}')
  database.append(f'hbe_progress_illustration_{key} = {{ scene = "hbe_progress_scene_{key}" tags = {{ 1000 = hbe_progress_art_{key} }} }}')
 for region,pair in LONG_ART.items():
  key=region;rel=f'in_game/events/hbe_story_{region}.txt';t=(out/rel).read_text(encoding='utf-8-sig')
  base=re.search(r'illustration_tags\s*=\s*\{\s*1000\s*=\s*hbe_story_art_(\w+)',t)[1]
  var='hbe_story_'+region+'_direction'
  variants=[(pair[0],f'has_variable = {var} var:{var} > 0'),(pair[1],f'has_variable = {var} var:{var} < 0')]
  register(key,base,variants)
  for chapter in range(3,9):t=event_patch(t,f'hbe_story_{region}.{chapter}',lambda b:change_tag(b,key))
  put(rel,t);routes.append(dict(key=key,chain=key,start_chapter=3,through_chapter=8,neutral_fallback=base,variants=variants))
 counts={}
 for story in SHORT+SHARED:
  region=story['region'];idx=counts.get(region,0);counts[region]=idx+1
  key=f'short_{region}_{idx+1}';var='hbe_'+key+'_art_route'
  rel=f'in_game/events/hbe_short_{region}.txt';t=(out/rel).read_text(encoding='utf-8-sig')
  first=f'hbe_short_{region}.{idx*10+1}'
  b,e=next((b,e) for k,_,b,e,_ in blocks(t,0) if k==first)
  base=re.search(r'illustration_tags\s*=\s*\{\s*1000\s*=\s*hbe_story_art_(\w+)',t[b:e])[1]
  variants=[(art,f'has_variable = {var} var:{var} = {n}') for n,(art,_) in enumerate(SHORT_ENDINGS[story['name']],1)]
  register(key,base,variants)
  for chapter in (1,2):
   eid=f'hbe_short_{region}.{idx*10+chapter}'
   for n,letter in enumerate('abc',1):t=event_patch(t,eid,lambda b:choice(b,eid,letter,var,n))
  for chapter in (2,3):t=event_patch(t,f'hbe_short_{region}.{idx*10+chapter}',lambda b:change_tag(b,key))
  put(rel,t);routes.append(dict(key=key,chain=story['name'],start_chapter=2,through_chapter=3,neutral_fallback=base,presentation_variable=var,variants=variants))
 rel='in_game/events/hbe_migration_events.txt';t=(out/rel).read_text(encoding='utf-8-sig')
 variants=[('migration_open','has_variable = hbe_migration_acceptance var:hbe_migration_acceptance > 0'),('migration_sponsored','has_variable = hbe_migration_acceptance var:hbe_migration_acceptance < 0')]
 register('migration','migration_pact',variants)
 for chapter in range(4,11):t=event_patch(t,f'hbe_migration.{chapter}',lambda b:change_tag(b,'migration'))
 put(rel,t);routes.append(dict(key='migration',chain='湖广填四川',start_chapter=4,through_chapter=10,neutral_fallback='migration_pact',variants=variants))
 put('in_game/gfx/images/hbe_progress_backgrounds.txt','\n\n'.join(images))
 put('in_game/gfx/scenes/hbe_progress_scenes.txt','\n\n'.join(scenes))
 put('loading_screen/gfx/illustrations/database/hbe_progress_illustrations.txt','\n'.join(database))
 result=dict(regional_chains=7,short_chains=33,migration_chains=1,changed_stage_events=115,choice_art_markers=198,economic_rewards_changed=False,legacy_save_fallback=True,routes=routes,files=sorted(set(changed)))
 mp=out/'build_manifest.json';m=json.loads(mp.read_text(encoding='utf-8'));m['progress_art_v031']={k:v for k,v in result.items() if k!='routes'}
 m['files']=snapshot_files(out)
 mp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 (root/'data/progress_art_v031.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:v for k,v in result.items() if k not in ('routes','files')},ensure_ascii=False));return result

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);a=ap.parse_args();apply(a.root/'mod/holy_bashu_empire',a.root)
