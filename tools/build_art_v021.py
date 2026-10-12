"""Mechanical export of ImageGen sprites and the two-party painted backdrop."""
import hashlib,json,re
from PIL import Image,ImageOps,ImageDraw,ImageFont
from pdxscript import blocks,apply_edits
from build_flags import save_dds
from build_icon_assets import fit
from build_native_flags import extract_charges

ICONS=[
 ('hbe_common_party','共建派','organization'),('hbe_local_party','兴业派','organization'),
 ('hbe_feast_cooperation','会盟相助','modifier'),('hbe_feast_success','盛会余泽','modifier'),
 ('hbe_feast_common_reward','共同兴建','modifier'),('hbe_feast_local_reward','百业争荣','modifier'),
 ('hbe_network_chengdu_plain_4','渠田共济','modifier'),('hbe_network_southern_salt_wine_4','井盐担保','modifier'),
 ('hbe_network_eastern_river_4','川江互保','modifier'),('hbe_network_northern_shudao_4','关隘轮守','modifier'),
 ('hbe_network_central_hills_4','义仓相济','modifier'),('hbe_network_western_tea_horse_4','茶马通路','modifier'),
 ('hbe_network_southwestern_valleys_4','诸谷换市','modifier'),('hbe_network_chengdu_plain_7','锦江讲会','modifier'),
 ('hbe_network_southern_salt_wine_7','盐酒席面','modifier'),('hbe_network_eastern_river_7','江岸会防','modifier'),
 ('hbe_network_northern_shudao_7','蜀道接递','modifier'),('hbe_network_central_hills_7','乡社清算','modifier'),
 ('hbe_network_western_tea_horse_7','山门公议','modifier'),('hbe_network_southwestern_valleys_7','乡寨共保','modifier'),
 ('hbe_feast_fund_action','为会盟出资','action'),('hbe_feast_common_action','支持共建派','action'),
 ('hbe_feast_local_action','支持兴业派','action'),('hbe_ai_internal_ambition','府州竞逐','modifier')]

def build_art_v021(out,root,loc,put,game):
 cover=root/'assets/workshop/cover_v030.png'
 if cover.exists():
  thumbnail=ImageOps.fit(Image.open(cover).convert('RGB'),(1280,720),Image.Resampling.LANCZOS)
  thumbnail.quantize(colors=256,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE).save(out/'.metadata/thumbnail.png',optimize=True)
 source=root/'assets/art_v021/icons.png';panel_source=root/'assets/art_v021/feast_two_parties.png'
 atlas=Image.open(source).convert('RGBA');assert atlas.size==(1536,1024) and atlas.getchannel('A').getextrema()[0]==0
 sprites=extract_charges(atlas,cols=6,rows=4,threshold=64)
 exports=[];proof=Image.new('RGB',(1200,880),'#292a26');draw=ImageDraw.Draw(proof)
 font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
 draw.text((24,15),'神圣巴蜀帝国 0.2.1 · 两派与地区合作',font=font,fill='#dfd0b2')
 dirs={'organization':'international_organizations','modifier':'modifiers','action':'generic_actions'}
 for n,(key,name,kind) in enumerate(ICONS):
  raw_sprite,box=sprites[n]
  sprite=fit(raw_sprite,128)
  png=root/'assets/art_v021/icons'/f'{key}.png';png.parent.mkdir(parents=True,exist_ok=True);sprite.save(png)
  target=out/'main_menu/gfx/interface/icons'/dirs[kind]/f'{key}.dds';save_dds(target,sprite)
  exports.append(dict(key=key,name=name,kind=kind,path=target.relative_to(out).as_posix(),source='assets/art_v021/icons.png',cell=n,crop=list(box),dimensions=[128,128],sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
  x=n%6*200;y=50+n//6*204;proof.paste(sprite,(x+36,y+14),sprite);draw.text((x+20,y+153),name,font=font,fill='#dfd0b2')
  # Existing country decisions share the new action pictures and remain registered.
  decision={'hbe_feast_fund_action':'hbe_project_fund','hbe_feast_common_action':'hbe_stance_change_1','hbe_feast_local_action':'hbe_stance_change_2'}.get(key)
  if decision:
   card=Image.new('RGBA',(1080,440));large=sprite.resize((320,320),Image.Resampling.LANCZOS);card.alpha_composite(large,(380,60))
   save_dds(out/'main_menu/gfx/interface/hbe/v021/decisions'/f'{decision}.dds',card)
 proof.save(root/'assets/art_v021/art_preview.png')
 scene=ImageOps.fit(Image.open(panel_source).convert('RGBA'),(1080,440),Image.Resampling.LANCZOS)
 panel=out/'main_menu/gfx/interface/hbe/panels/hbe_feast_two_parties_v021.dds';save_dds(panel,scene)
 event=out/'main_menu/gfx/interface/hbe/events/feast_two_parties_v021.dds';save_dds(event,scene)
 exports.append(dict(key='hbe_feast_two_parties_v021',kind='panel',path=panel.relative_to(out).as_posix(),event_path=event.relative_to(out).as_posix(),source='assets/art_v021/feast_two_parties.png',dimensions=[1080,440],sha256=hashlib.sha256(panel.read_bytes()).hexdigest()))
 gui_path=out/'in_game/gui/panels/situation/hbe_banquet.gui';gui=gui_path.read_text(encoding='utf-8-sig')
 gui=gui.replace('gfx/interface/hbe/panels/hbe_banquet.dds','gfx/interface/hbe/panels/hbe_feast_two_parties_v021.dds')
 for key,label in [('hbe_common_party','HBE_COMMON_LEADER'),('hbe_local_party','HBE_LOCAL_LEADER')]:
  old='text_single = { text = "'+label+'" }'
  new='hbox = { spacing = 5 icon = { size = { 28 28 } texture = "gfx/interface/icons/international_organizations/'+key+'.dds" } text_single = { text = "'+label+'" } }'
  gui=gui.replace(old,new)
 put('in_game/gui/panels/situation/hbe_banquet.gui',gui)
 decisions=out/'in_game/common/decisions/hbe_banquet_decisions.txt';text=decisions.read_text(encoding='utf-8-sig');edits=[]
 for k,_,s,e,_ in blocks(text,0):
  if k in ['hbe_project_fund','hbe_stance_change_1','hbe_stance_change_2']:
   body=re.sub(r'image = "[^"]+"',f'image = "gfx/interface/hbe/v021/decisions/{k}.dds"',text[s:e]);edits.append((s,e,body))
 put('in_game/common/decisions/hbe_banquet_decisions.txt',apply_edits(text,edits))
 template=(out/'in_game/gfx/scenes/hbe_event_scenes.txt').read_text(encoding='utf-8-sig')
 shell=next(template[s:e] for k,_,s,e,_ in blocks(template,0) if k=='hbe_event_scene_council')
 put('in_game/gfx/scenes/hbe_v021_scenes.txt','hbe_event_scene_feast_two_parties = {'+shell.replace('hbe_event_background_council','hbe_event_background_feast_two_parties')+'}')
 put('in_game/gfx/images/hbe_v021_backgrounds.txt','hbe_event_background_feast_two_parties = { tag = "hbe_event_background_feast_two_parties" illustration_image = { texture_file = "gfx/interface/hbe/events/feast_two_parties_v021.dds" priority = 100 scope = country trigger = { always = yes } } }')
 put('loading_screen/gfx/illustrations/database/hbe_v021_illustrations.txt','hbe_event_illustration_feast_two_parties = { scene = "hbe_event_scene_feast_two_parties" tags = { 1000 = hbe_event_art_feast_two_parties } }')
 path=out/'in_game/events/hbe_banquet_events.txt';text=path.read_text(encoding='utf-8-sig');edits=[]
 for k,_,s,e,_ in blocks(text,0):
  if k in ['hbe_banquet.1','hbe_banquet.2','hbe_banquet.4','hbe_banquet.5','hbe_banquet.7']:
   edits.append((s,e,text[s:e].replace('hbe_event_art_council','hbe_event_art_feast_two_parties')))
 put('in_game/events/hbe_banquet_events.txt',apply_edits(text,edits))
 result=dict(mode='built-in image_gen',version='0.2.1',exports=exports,prompts='docs/art_prompts_v021.md',source_sha256={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,panel_source]})
 (root/'data/art_v021.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
 return result
