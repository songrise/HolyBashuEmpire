"""Export approved paintings and add presentation-only choice afterwords."""
from build_support import sha256_file as digest, snapshot_files
from pathlib import Path
import argparse,hashlib,json,re,sys
from PIL import Image,ImageOps,ImageDraw,ImageFont
from pdxscript import blocks,tokens

def normalized(text): return re.sub(r'\s+',' ',text).strip()

def apply(out,root,game=None):
 out,root=Path(out),Path(root)
 sys.path.insert(0,str(root/'data'))
 from ending_texts_v031 import LONG_ART,SHORT_ENDINGS
 from short_stories import SHORT
 from shared_stories import SHORT as SHARED
 src=root/'assets/event_endings_v031'
 records=json.loads((src/'generation_records.json').read_text(encoding='utf-8'))
 images=[];scenes=[];db=[];assets=[]
 base=(out/'in_game/gfx/scenes/hbe_story_scenes.txt').read_text(encoding='utf-8-sig')
 shell=next(base[b:e] for key,_,b,e,_ in blocks(base,0) if key=='hbe_story_scene_fossils')
 def put(relative,text):
  p=out/relative;p.parent.mkdir(parents=True,exist_ok=True)
  p.write_text(text.rstrip()+'\n',encoding='utf-8-sig',newline='\r\n')
 font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
 paint=[r for r in records if not r['key'].startswith('reform_')]
 sheets=[Image.new('RGB',(1080,8*250),'#252b2d') for _ in range(2)]
 for i,row in enumerate(paint):
  key=row['key'];source=src/(key+'.png')
  with Image.open(source) as im:original=im.convert('RGB')
  crop=ImageOps.fit(original,(1080,440),Image.Resampling.LANCZOS,centering=(.5,.5))
  relative=f'main_menu/gfx/interface/hbe/ending_events/{key}.dds'
  target=out/relative;target.parent.mkdir(parents=True,exist_ok=True)
  crop.convert('RGBA').save(target,pixel_format='DXT5')
  bg='hbe_ending_background_'+key;scene='hbe_ending_scene_'+key;tag='hbe_ending_art_'+key
  images.append(f'{bg} = {{ tag = "{bg}" illustration_image = {{ texture_file = "{relative.removeprefix("main_menu/")}" priority = 100 scope = country trigger = {{ always = yes }} }} }}')
  body=shell.replace('list = "hbe_story_background_fossils"',f'list = "{bg}"')
  assert f'list = "{bg}"' in body
  scenes.append(scene+' = {'+body+'}')
  db.append(f'hbe_ending_illustration_{key} = {{ scene = "{scene}" tags = {{ 1000 = {tag} }} }}')
  assets.append(dict(key=key,source=source.relative_to(root).as_posix(),source_sha256=digest(source),texture=relative,sha256=digest(target),dimensions=[1080,440],scene=scene,tag=tag))
  sheet=sheets[i//16];j=i%16;x=j%2*540;y=j//2*250
  sheet.paste(crop.resize((540,220),Image.Resampling.LANCZOS),(x,y));ImageDraw.Draw(sheet).text((x+8,y+224),key,font=font,fill='#ddd2bc')
 for n,sheet in enumerate(sheets):sheet.save(src/f'panoramic-preview-{n+1}.jpg',quality=91)
 put('in_game/gfx/images/hbe_ending_backgrounds.txt','\n'.join(images))
 put('in_game/gfx/scenes/hbe_ending_scenes.txt','\n'.join(scenes))
 put('loading_screen/gfx/illustrations/database/hbe_ending_illustrations.txt','\n'.join(db))
 icons=[]
 for row in records:
  if not row['key'].startswith('reform_'):continue
  key='hbe_'+row['key'].removeprefix('reform_');source=src/(row['key']+'.png')
  im=ImageOps.fit(Image.open(source).convert('RGB'),(64,90),Image.Resampling.LANCZOS)
  rel=f'main_menu/gfx/interface/icons/government_reforms/illustrations/{key}.dds'
  p=out/rel;p.parent.mkdir(parents=True,exist_ok=True);im.convert('RGBA').save(p,pixel_format='DXT5')
  icons.append(dict(key=key,source=source.relative_to(root).as_posix(),texture=rel,dimensions=[64,90],sha256=digest(p)))
 reforms='in_game/common/government_reforms/hbe_shared_reforms.txt'
 t=(out/reforms).read_text(encoding='utf-8-sig')
 for row in icons:
  key=row['key']
  if not re.search(r'\bicon\s*=\s*'+key+r'\b',t):t=t.replace(key+' = {',key+' = {\n icon = '+key,1)
 put(reforms,t)
 epilogues=[];hooks=[];loc={};seen_names=set()
 def tag_for(art):return ('hbe_ending_art_' if art in {a['key'] for a in assets} else 'hbe_story_art_')+art
 def group_flags(flag):
  base=flag.rsplit('_',1)[0]
  branches=[base+'_'+str(n) for n in range(1,3 if base=='hbe_afterword_migration' else 4)]
  return base+'_completed',branches
 def fresh_guard(flag,include_pending=False):
  complete,branches=group_flags(flag)
  keys=[complete]+[b+'_seen' for b in branches]+(branches if include_pending else [])
  return 'NOT = { OR = { '+' '.join('has_variable = '+k for k in keys)+' } }'
 def epilogue(event_id,title,context,aftermath,art,flag):
  complete,branches=group_flags(flag)
  cleanup=' '.join('remove_variable = '+b for b in branches)
  loc[event_id+'.title']=title
  loc[event_id+'.desc']=context+'\n\n'+aftermath
  loc[event_id+'.a']='让这段往事留在本府的记忆里。'
  return f'''{event_id} = {{
 type = country_event title = {event_id}.title desc = {event_id}.desc outcome = neutral
 illustration_tags = {{ 1000 = {tag_for(art)} }}
 trigger = {{ has_variable = {flag} {fresh_guard(flag)} }}
 immediate = {{ hidden_effect = {{ {cleanup} set_variable = {complete} set_variable = {flag}_seen }} }}
 option = {{ name = {event_id}.a ai_chance = {{ base = 100 }} }}
}}'''
 def append_hook(event,option_name,follow,flag):
  # A delimited hidden block is the only addition to original choice effects.
  begin='# HBE_ENDING_PRESENTATION_BEGIN';end='# HBE_ENDING_PRESENTATION_END'
  options=[(b,e) for key,level,b,e,_ in blocks(event,0) if key=='option']
  match=next((b,e) for b,e in options if re.search(r'\bname\s*=\s*'+re.escape(option_name)+r'\b',event[b:e]))
  b,e=match;before=event[b:e]
  clean=re.sub(r'\n?\s*'+re.escape(begin)+r'.*?'+re.escape(end)+r'\s*','\n',before,flags=re.S)
  hook='\n '+begin+'\n hidden_effect = { if = { limit = { '+fresh_guard(flag,True)+' } set_variable = '+flag+' trigger_event_non_silently = { id = '+follow+' days = 1 } } }\n '+end+'\n'
  after=clean.rstrip()+hook
  hooks.append(dict(source_option=option_name,event=follow,pending=flag,original_option_sha256=hashlib.sha256(normalized(clean).encode()).hexdigest()))
  return event[:b]+after+event[e:]
 # Art-only replacement of fourteen already-existing permanent outcome events.
 for region,pair in LONG_ART.items():
  rel=f'in_game/events/hbe_story_{region}.txt';text=(out/rel).read_text(encoding='utf-8-sig')
  for n,art in enumerate(pair):
   key=f'hbe_story_{region}.{201+n}';entry=next((b,e) for k,_,b,e,_ in blocks(text,0) if k==key);b,e=entry
   body=text[b:e];body,count=re.subn(r'illustration_tags\s*=\s*\{[^}]*\}',f'illustration_tags = {{ 1000 = {tag_for(art)} }}',body,count=1);assert count==1
   text=text[:b]+body+text[e:]
  put(rel,text)
 # One neutral afterword per completed choice. Stop/delay options get none.
 counts={};new_events=[]
 for story in SHORT+SHARED:
  region=story['region'];index=counts.get(region,0);counts[region]=index+1
  name=story['name'];assert name not in seen_names;seen_names.add(name)
  endings=SHORT_ENDINGS[name];assert len(endings)==3 and len({a for a,_ in endings})==3
  source=f'hbe_short_{region}.{index*10+3}';rel=f'in_game/events/hbe_short_{region}.txt'
  text=(out/rel).read_text(encoding='utf-8-sig');b,e=next((b,e) for k,_,b,e,_ in blocks(text,0) if k==source);event=text[b:e]
  final_labels=story['chapters'][-1][2].split('|')
  for n,(art,aftermath) in enumerate(endings):
   follow=f'hbe_ending.{1001+len(new_events)}';flag=f'hbe_afterword_{region}_{index+1}_{n+1}'
   title=name+' · '+final_labels[n].rstrip('。')
   event=append_hook(event,source+'.'+chr(97+n),follow,flag)
   new_events.append(epilogue(follow,title,story['context'],aftermath,art,flag))
   epilogues.append(dict(id=follow,source=source,option=chr(97+n),chain=name,art=art,title=title,category='短链结局回顾'))
  put(rel,text[:b]+event+text[e:])
 assert len(seen_names)==33 and len(new_events)==99
 # Migration's final decision already owns all rewards; its new images show only aftermath.
 rel='in_game/events/hbe_migration_events.txt';text=(out/rel).read_text(encoding='utf-8-sig');b,e=next((b,e) for k,_,b,e,_ in blocks(text,0) if k=='hbe_migration.10');event=text[b:e]
 migrations=[('migration_open','新乡共籍约','最早入蜀的船已换过几代船板，旧乡的口音也在孩子嘴里变了模样。新簿把长住、劳作与共同出资的人列在一起，旧户不再独守承认新邻的名额。有人仍怀念旧日的次序，院里的几户人却已能拿着同一份凭记商量下一年的田水。'),('migration_sponsored','旧户担保制','堂前登记仍先由旧户出面担保，来人按各家承诺分批落脚。旧族保住主持与体面，得到引荐的人也多了一处可以求援的门。那些没有担保的人还在等，最后留下的新乡便沿着这些熟悉的门户慢慢展开。')]
 for n,(art,name,prose) in enumerate(migrations):
  follow=f'hbe_ending.{2001+n}';flag=f'hbe_afterword_migration_{n+1}'
  event=append_hook(event,'hbe_migration.10.'+chr(97+n),follow,flag)
  new_events.append(epilogue(follow,'湖广填四川 · '+name,'旧簿与新册收进同一只木箱。几十年来关于田地、工钱、礼期与入籍的争论，终于留下了本府将要沿用的办法。',prose,art,flag))
  epilogues.append(dict(id=follow,source='hbe_migration.10',option=chr(97+n),chain='湖广填四川',art=art,title='湖广填四川 · '+name,category='移民结局回顾'))
 put(rel,text[:b]+event+text[e:])
 put('in_game/events/hbe_ending_afterwords.txt','namespace = hbe_ending\n\n'+'\n\n'.join(new_events))
 # Preserve the existing batch's documented Chinese fallback in English mode.
 for lang in ('simp_chinese','english'):
  put(f'main_menu/localization/{lang}/hbe_ending_l_{lang}.yml','l_'+lang+':\n'+'\n'.join(' '+k+': '+json.dumps(v,ensure_ascii=False) for k,v in loc.items()))
 mp=out/'build_manifest.json';manifest=json.loads(mp.read_text(encoding='utf-8'))
 result=dict(version=manifest['version'],mode='built-in image_gen; new paintings, mechanical crop and DDS export',new_scenes=len(assets),reform_icons=icons,assets=assets,long_branches=LONG_ART,short_chains=33,new_afterwords=len(new_events),hooks=hooks,epilogues=epilogues,english_status='Complete Chinese fallback, consistent with existing authored story batch',gameplay_effects_changed=False)
 manifest['ending_art_v031']={k:v for k,v in result.items() if k not in ('assets','epilogues','hooks')}
 manifest['events']=117+manifest['playable_stories']['event_count']+len(new_events)
 manifest['files']=snapshot_files(out)
 mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 (root/'data/ending_art_v031.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(dict(scenes=len(assets),icons=len(icons),afterwords=len(new_events),gameplay_effects_changed=False)))
 return result

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);a=ap.parse_args()
 apply(a.root/'mod/holy_bashu_empire',a.root)
