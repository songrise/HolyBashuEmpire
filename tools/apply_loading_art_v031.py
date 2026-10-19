"""Four static paintings and four sourced excerpts in the vanilla loading UI."""
from build_support import sha256_file as digest, snapshot_files
from pathlib import Path
import argparse, json
from PIL import Image,ImageOps,ImageDraw,ImageFont

SCENES={'craft':'坊中蜀绣','river':'峡江待渡','observatory':'山壁星历','panda_sanctuary':'竹林护养'}
QUOTES=[
 ('晓看红湿处，花重锦官城。','杜甫《春夜喜雨》',
  'At dawn, look where the flowers are wet and red; blossoms weigh upon the City of Brocade.',
  'Du Fu, A Welcome Rain on a Spring Night',
  'https://zh.wikisource.org/zh-hans/春夜喜雨'),
 ('朝辞白帝彩云间，千里江陵一日还。','李白《早发白帝城》',
  'At dawn I leave White Emperor City among bright clouds; a thousand li to Jiangling in a single day.',
  'Li Bai, Leaving White Emperor City at Dawn',
  'https://zh.wikisource.org/zh-hans/早發白帝城'),
 ('此身合是诗人未？细雨骑驴入剑门。','陆游《剑门道中遇微雨》',
  'Was I meant to be a poet? Through fine rain I ride a donkey into Sword Gate.',
  'Lu You, A Light Rain on the Road to Sword Gate',
  'https://zh.wikisource.org/zh-hans/劍門道中遇微雨'),
 ('时无荒年，天下谓之天府。','《华阳国志·蜀志》引《蜀记》',
  'The harvests do not fail; the world calls it the Heavenly Storehouse.',
  'Records of Shu, quoted in Chang Qu, Records of the Lands South of Mount Hua',
  'https://zh.wikisource.org/zh-hans/華陽國志/卷三'),
]

def export_quotes(out):
 def put(rel,t):
  p=out/rel;p.parent.mkdir(parents=True,exist_ok=True)
  p.write_text(t.rstrip()+"\n",encoding="utf-8-sig",newline="\r\n")
 # Four known native slots guarantee inclusion in GetLoadingScreenLoadTip. All
 # other vanilla quotations and the native GUI / progress / concept UI remain.
 for lang in ('simp_chinese','english'):
  lines=['l_'+lang+':']
  for n,(cn,by,en,eby,url) in enumerate(QUOTES):
   quote,author=(cn,by) if lang=='simp_chinese' else (en,eby)
   text=f' #T {quote}#! \\n #tooltip_subheading — {author}#!'
   lines.append(' LOADING_TIP_'+str(n)+': '+json.dumps(text,ensure_ascii=False).replace('\\\\n','\\n'))
  put(f'loading_screen/localization/{lang}/hbe_load_tips_l_{lang}.yml','\n'.join(lines))

def export_loading_art(out,root,game=None):
 out,root=Path(out),Path(root);src=root/'assets/event_expansion'
 image_defs=[];scene_defs=[];assets=[]
 def put(rel,t):
  p=out/rel;p.parent.mkdir(parents=True,exist_ok=True)
  p.write_text(t.rstrip()+'\n',encoding='utf-8-sig',newline='\r\n')
 preview=Image.new('RGB',(1600,980),'#20282c');draw=ImageDraw.Draw(preview)
 font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',24)
 for i,(key,title) in enumerate(SCENES.items()):
  source=(root/'assets/event_endings_v031' if key=='panda_sanctuary' else src)/(key+'.png')
  with Image.open(source) as original:
   original_size=list(original.size)
   im=ImageOps.fit(original.convert('RGB'),(3840,2160),Image.Resampling.LANCZOS)
  rel=f'loading_screen/gfx/loading_screen_assets/hbe/{key}_metadata_os3840x2160_d0x0.dds'
  dest=out/rel;dest.parent.mkdir(parents=True,exist_ok=True);im.convert('RGBA').save(dest,pixel_format='DXT5')
  name=f'hbe_loading_{key}'
  image_defs.append(f'{name} = {{ illustration_image = {{ texture_file = "{rel.removeprefix("loading_screen/")}" priority = 1 weight = 1 }} tag = "{name}" }}')
  # The vanilla rear 16:9 quad has the same camera/canvas geometry as its loading
  # scenes. The static schematic has no animation binding or UV drift.
  component=f'ecs_illustration_image = {{ list = "{name}" pdxmesh = "layer_8_mesh" name = "illustration_override" }}'
  scene_defs.append('loading_screen_scene_hbe_'+key+' = {\n '+component+'\n gfx_environment_file = "gfx/illustrations/environment2.txt"\n camera = { camera_near_far = { 0.11 100000 } camera_fov_y_degrees = 37.5 camera_position = { 0 0 -125 } camera_look_at = { 0 0 1000 } }\n}')
  assets.append(dict(key=key,title=title,texture=rel,source=source.relative_to(root).as_posix(),source_dimensions=original_size,dimensions=[3840,2160],mesh='layer_8_mesh',sha256=digest(dest),source_sha256=digest(source)))
  preview.paste(im.resize((800,450),Image.Resampling.LANCZOS),(i%2*800,i//2*490))
  draw.text((i%2*800+18,i//2*490+455),title,font=font,fill='#e7dcc5')
 put('loading_screen/gfx/images/hbe_loading_images.txt','\n\n'.join(image_defs))
 put('loading_screen/gfx/scenes/hbe_loading_scenes.txt','\n\n'.join(scene_defs))
 export_quotes(out)
 preview_path=root/'assets/loading_art_v031/preview.jpg';preview_path.parent.mkdir(parents=True,exist_ok=True);preview.save(preview_path,quality=93)
 result=dict(mode='static',canvas=[3840,2160],aspect_ratio='16:9',scenes=4,planes_per_scene=1,native_animation_binding='illustration_override',parallax=False,loading_scene_prefix='loading_screen_scene_',native_text_binding='GetLoadingScreenLoadTip',native_quote_slots=list(range(4)),quote_sources=[dict(quote=q[0],author=q[1],url=q[4]) for q in QUOTES],assets=assets,source_resolution_note='Approved original paintings mechanically fitted and resampled to the exact vanilla 3840x2160 canvas; no style change or generated detail.')
 mp=out/'build_manifest.json';m=json.loads(mp.read_text(encoding='utf-8'));m['loading_art_v031']={k:v for k,v in result.items() if k!='assets'}
 m['files']=snapshot_files(out)
 mp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');(root/'data/loading_art_v031.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps({k:v for k,v in result.items() if k not in ('assets','quote_sources')},ensure_ascii=False));return result


def apply(out,root,game=None,enabled=False):
 """Keep custom loading paintings off until explicitly re-enabled."""
 if enabled:return export_loading_art(out,root,game)
 out,root=Path(out),Path(root)
 owned=['loading_screen/gfx/images/hbe_loading_images.txt',
        'loading_screen/gfx/scenes/hbe_loading_scenes.txt']
 owned += [f'loading_screen/gfx/loading_screen_assets/hbe/{key}_metadata_os3840x2160_d0x0.dds' for key in SCENES]
 for rel in owned:
  p=(out/rel).resolve()
  assert p.is_relative_to(out.resolve()),'Unsafe loading-art target'
  p.unlink(missing_ok=True)
 export_quotes(out)
 result=dict(enabled=False,mode='vanilla',scenes=0,staged_scenes=len(SCENES),
             native_text_binding='GetLoadingScreenLoadTip',native_quote_slots=list(range(4)),
             source_catalog='data/loading_art_v031.json')
 mp=out/'build_manifest.json';m=json.loads(mp.read_text(encoding='utf-8'))
 m['loading_art_v031']=result
 m['files']=snapshot_files(out)
 mp.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False));return result

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);a=ap.parse_args();apply(a.root/'mod/holy_bashu_empire',a.root)
