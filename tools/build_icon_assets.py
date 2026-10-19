"""Mechanical sprite extraction and DDS export for ImageGen-painted assets."""
from build_support import sha256_file as sha
import json
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from build_flags import save_dds


def fit(im,size=256):
    im=im.convert('RGBA')
    bounds=im.getchannel('A').point(lambda x:255 if x>16 else 0).getbbox()
    if not bounds:raise ValueError('Empty generated sprite')
    im=im.crop(bounds)
    im.thumbnail((round(size*.86),round(size*.86)),Image.Resampling.LANCZOS)
    canvas=Image.new('RGBA',(size,size));canvas.alpha_composite(im,((size-im.width)//2,(size-im.height)//2))
    return canvas

def build_icon_assets(out,root,nodes,put,game):
    source=root/'assets/icon_generation.json'
    if not source.is_file():raise FileNotFoundError('ImageGen source manifest is required: '+str(source))
    registry=json.loads(source.read_text(encoding='utf-8'))
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',17)
    proof=Image.new('RGB',(1536,8*166+80),'#302a23');d=ImageDraw.Draw(proof)
    d.text((20,16),'神圣巴蜀帝国 · 64 项科技 / ImageGen 手绘器物图标',font=font,fill='#ead59b')
    exports=[];seen=set()
    for row,sheet in enumerate(registry['sheets']):
        path=root/sheet['source'];im=Image.open(path).convert('RGBA')
        if im.getchannel('A').getextrema()[0]!=0:raise ValueError('Sprite atlas must have real transparency: '+str(path))
        for i,cell in enumerate(sheet['cells']):
            key=cell['key'];seen.add(key);col=i%4;line=i//4
            box=(round(col*im.width/4),round(line*im.height/2),round((col+1)*im.width/4),round((line+1)*im.height/2))
            sprite=fit(im.crop(box));png=root/'assets/technology_icons'/f'{key}.png';png.parent.mkdir(parents=True,exist_ok=True);sprite.save(png)
            target=out/'main_menu/gfx/interface/hbe/technology'/f'{key}.dds';save_dds(target,sprite)
            save_dds(out/'main_menu/gfx/interface/advance'/f'{key}.dds',sprite)
            x=i*192+28;y=row*166+64;proof.paste(sprite.resize((128,128),Image.Resampling.LANCZOS),(x,y),sprite.resize((128,128),Image.Resampling.LANCZOS))
            d.text((i*192+9,y+132),cell['name'],font=font,fill='#e8dec0')
            exports.append(dict(key=key,name=cell['name'],group=sheet['group'],atlas=sheet['source'],cell=i,crop=list(box),image=str(target.relative_to(out)).replace('\\','/'),sha256=sha(target)))
    assert seen=={n['key'] for n in nodes},'Atlas node mapping differs from the research catalogue'
    assert len({e['sha256'] for e in exports})==64,'Repeated technology image'
    proof.save(root/'assets/technology_icons_preview.png')
    icons=[];textdefs=[]
    points=Image.new('RGB',(1100,220),'#302a23');pd=ImageDraw.Draw(points)
    for i,entry in enumerate(registry['icons']):
        key=entry['key'];sprite=fit(Image.open(root/entry['source']),128)
        target=out/'main_menu/gfx/interface/icons'/('situations' if entry['kind']=='situation' else 'text_icons')/f'{key}.dds'
        save_dds(target,sprite)
        icons.append(dict(key=key,name=entry['name'],kind=entry['kind'],image=str(target.relative_to(out)).replace('\\','/'),sha256=sha(target)))
        points.paste(sprite.resize((86,86),Image.Resampling.LANCZOS),(i*100+7,42),sprite.resize((86,86),Image.Resampling.LANCZOS));pd.text((i*100+7,136),entry['name'],font=font,fill='#ead59b')
        if entry['kind']=='point':
            textdefs.append(f'texticon = {{ icon = {key} iconsize = {{ texture = "gfx/interface/icons/text_icons/{key}.dds" size = {{ 24 24 }} offset = {{ 0 4 }} fontsize = 16 }} }}')
    put('main_menu/gui/shared/hbe_font_icons.gui','\n'.join(textdefs))
    points.save(root/'assets/point_icons_preview.png')
    result=dict(mode='built-in image_gen',atlases=8,technology_icons=exports,other_icons=icons,source_manifest='assets/icon_generation.json')
    (root/'data/icon_assets_v002.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result
