"""Register a dedicated Hanzhou egret painting without changing event choices."""
from pathlib import Path
from PIL import Image,ImageOps
import re,json,hashlib
from pdxscript import blocks,apply_edits

def apply(out,root,game=None):
 out,root=Path(out),Path(root)
 source=root/'assets/event_expansion/hanzhou_egrets.png'
 target=out/'main_menu/gfx/interface/hbe/story_events/hanzhou_egrets.dds'
 with Image.open(source) as im:
  im.load();original=list(im.size);picture=ImageOps.fit(im.convert('RGB'),(1080,440),Image.Resampling.LANCZOS)
 target.parent.mkdir(parents=True,exist_ok=True);picture.convert('RGBA').save(target,pixel_format='DXT5')
 def put(rel,s):
  p=out/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(s.rstrip()+'\n',encoding='utf-8-sig')
 put('in_game/gfx/images/hbe_egret_background.txt','''hbe_egret_background = { tag = "hbe_egret_background" illustration_image = { texture_file = "gfx/interface/hbe/story_events/hanzhou_egrets.dds" priority = 100 scope = country trigger = { always = yes } } }''')
 text=(out/'in_game/gfx/scenes/hbe_story_scenes.txt').read_text(encoding='utf-8-sig')
 scene=next(text[a:b] for k,_,a,b,_ in blocks(text,0) if k=='hbe_story_scene_bamboo')
 scene=scene.replace('hbe_story_background_bamboo','hbe_egret_background')
 put('in_game/gfx/scenes/hbe_egret_scene.txt','hbe_egret_scene = {'+scene+'}')
 put('loading_screen/gfx/illustrations/database/hbe_egret_illustration.txt','hbe_egret_illustration = { scene = "hbe_egret_scene" tags = { 1000 = hbe_egret_art } }')
 p=out/'in_game/events/hbe_story_chengdu_plain.txt';text=p.read_text(encoding='utf-8-sig')
 block=next(b for b in blocks(text,0) if b[0]=='hbe_story_chengdu_plain.103')
 body=text[block[2]:block[3]];fixed=re.sub(r'illustration_tags\s*=\s*\{[^}]+\}','illustration_tags = { 1000 = hbe_egret_art }',body,count=1)
 assert fixed!=body or '1000 = hbe_egret_art' in body
 assert re.sub(r'illustration_tags\s*=\s*\{[^}]+\}','',body)==re.sub(r'illustration_tags\s*=\s*\{[^}]+\}','',fixed)
 put(p.relative_to(out),apply_edits(text,[(block[2],block[3],fixed)]))
 p=out/'build_manifest.json';m=json.loads(p.read_text(encoding='utf8'))
 m['egret_art_v032']={'event':'hbe_story_chengdu_plain.103','art':'hbe_egret_art','source':source.relative_to(root).as_posix(),'source_dimensions':original,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'runtime_dimensions':[1080,440],'gameplay_effects_changed':False}
 m['files']={p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and p.name!='build_manifest.json'}
 p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
 return m['egret_art_v032']
