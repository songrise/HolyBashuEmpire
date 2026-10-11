"""Original vector heraldry, rasterized to EU5 textured-emblem DDS files.

Pillow is only used for rendering newly authored geometric vector art. No stock
art is copied. Editable SVG sources and a labelled proof sheet are retained.
"""
import hashlib, math, struct
from pathlib import Path
from xml.sax.saxutils import escape
from PIL import Image, ImageDraw, ImageFont

PALETTES = [('#173f3c','#76b8a4'),('#681f32','#e38c63'),('#163855','#79aecf'),
            ('#353554','#a7a0d2'),('#4c4528','#b8b875'),('#235039','#92bd88'),
            ('#583428','#d8a779')]
GOLD='#ead59b'

def save_dds(path, image):
    w,h=image.size
    header=struct.pack('<7I',124,0x100F,h,w,w*4,0,0)+bytes(44)
    header+=struct.pack('<8I',32,0x41,0,32,0x00FF0000,0x0000FF00,0x000000FF,0xFF000000)
    header+=struct.pack('<5I',0x1000,0,0,0,0)
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(b'DDS '+header+image.convert('RGBA').tobytes('raw','BGRA'))

def build_flags(out,countries,regions,root,put):
    font_path=Path('C:/Windows/Fonts/msyh.ttc')
    if not font_path.exists(): raise RuntimeError('Microsoft YaHei is required to render the Chinese heraldic seals.')
    scale=3
    label_font=ImageFont.truetype(str(font_path),22*scale)
    seal_font=ImageFont.truetype(str(font_path),25*scale)
    small_font=ImageFont.truetype(str(font_path),18)
    preview=Image.new('RGB',(6*300,6*236),'#131c22');proof=ImageDraw.Draw(preview)
    source=root/'assets/flags';source.mkdir(parents=True,exist_ok=True)
    definitions=[];catalog=[]
    for i,c in enumerate(countries):
        ri=next(j for j,r in enumerate(regions) if r[0]==c['region'])
        bg,accent=PALETTES[ri];im=Image.new('RGBA',(384*scale,256*scale),bg);d=ImageDraw.Draw(im)
        svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="384" height="256" viewBox="0 0 384 256"><rect width="384" height="256" fill="{bg}"/>']
        def rect(box,fill,outline=None,width=1):
            d.rectangle(tuple(round(v*scale) for v in box),fill=fill,outline=outline,width=width*scale)
            x,y,x2,y2=box;svg.append(f'<rect x="{x}" y="{y}" width="{x2-x}" height="{y2-y}" fill="{fill or "none"}" stroke="{outline or "none"}" stroke-width="{width}"/>')
        def line(points,fill=GOLD,width=5):
            d.line([(int(x*scale),int(y*scale)) for x,y in points],fill=fill,width=width*scale,joint='curve')
            svg.append(f'<polyline points="'+ ' '.join(f'{x},{y}' for x,y in points)+f'" fill="none" stroke="{fill}" stroke-width="{width}" stroke-linejoin="round"/>')
        def poly(points,fill=GOLD):
            d.polygon([(int(x*scale),int(y*scale)) for x,y in points],fill=fill)
            svg.append('<polygon points="'+' '.join(f'{x},{y}' for x,y in points)+f'" fill="{fill}"/>')
        def ellipse(box,fill=None,outline=GOLD,width=4):
            d.ellipse(tuple(round(v*scale) for v in box),fill=fill,outline=outline,width=width*scale)
            x,y,x2,y2=box;svg.append(f'<ellipse cx="{(x+x2)/2}" cy="{(y+y2)/2}" rx="{(x2-x)/2}" ry="{(y2-y)/2}" fill="{fill or "none"}" stroke="{outline or "none"}" stroke-width="{width}"/>')
        # Common imperial border and seven-point coronet; distinct field treatments.
        rect((5,5,379,251),None,GOLD,3)
        if i%3==0:
            poly([(12,12),(94,12),(372,202),(372,242),(312,242),(12,40)],accent)
        elif i%3==1:
            rect((12,12,62,244),accent);rect((322,12,372,244),accent)
        else:
            rect((12,186,372,244),accent)
            poly([(12,12),(60,12),(12,60)],accent);poly([(372,12),(324,12),(372,60)],accent)
        ellipse((106,46,278,216),bg,GOLD,4)
        # Coronet, inspired by seven electors; wheat leaves connect to Tianfu.
        poly([(155,48),(150,29),(166,39),(176,22),(187,39),(197,19),(208,39),(220,22),(228,39),(244,29),(238,48)])
        for side in (-1,1):
            for n in range(5):
                x=192+side*(91-7*n);y=182-22*n
                line([(x,y+12),(x+side*11,y)],GOLD,3)
                poly([(x,y),(x+side*10,y-11),(x+side*11,y+1),(x,y+11)])
        # Seven intentionally different motifs.
        if ri==0: # Irrigation gates and three channels.
            rect((155,85,165,157),GOLD);rect((219,85,229,157),GOLD);rect((151,86,233,98),GOLD)
            for y in (145,163,181):line([(140,y),(156,y-6),(175,y),(192,y-6),(210,y),(228,y-6),(244,y)],accent,6)
            line([(192,101),(192,129)],GOLD,6)
        elif ri==1: # Salt well derrick and wine jar.
            line([(153,174),(175,84),(197,174)],GOLD,6);line([(160,136),(191,136)],GOLD,4)
            line([(164,117),(186,117)],GOLD,4);line([(175,84),(215,84)],GOLD,5)
            line([(207,85),(207,130)],accent,4);ellipse((195,137,232,177),GOLD,None);rect((202,127,225,145),GOLD)
        elif ri==2: # River junk, mountain and port.
            poly([(135,156),(247,156),(233,176),(153,176)])
            line([(193,90),(193,155)],GOLD,5)
            poly([(186,94),(151,144),(186,144)],accent);poly([(200,101),(229,144),(200,144)])
            line([(143,184),(165,180),(186,184),(207,180),(229,184),(244,180)],accent,5)
        elif ri==3: # Mountain pass, crenellated gate and road.
            poly([(135,151),(162,93),(189,151)],accent);poly([(193,151),(223,84),(251,151)],accent)
            rect((173,117,216,171),GOLD);rect((179,140,209,171),bg)
            for x in (171,184,197,210):rect((x,108,x+8,123),GOLD)
            line([(193,159),(183,180),(195,193)],GOLD,5)
        elif ri==4: # Granary and three stalks of grain.
            poly([(144,121),(192,88),(240,121)]);rect((151,124,233,171),GOLD);rect((173,136,211,171),bg)
            for x in (165,192,219):
                line([(x,178),(x,196)],GOLD,3)
                poly([(x,178),(x-7,184),(x,191),(x+7,184)],accent)
        elif ri==5: # Tea leaves above a caravan horseshoe.
            line([(192,90),(192,132)],GOLD,4)
            ellipse((162,86,191,107),accent,None);ellipse((192,99,222,120),accent,None)
            line([(164,137),(154,160),(159,179),(175,189),(186,188)],GOLD,8)
            line([(220,137),(230,160),(225,179),(209,189),(198,188)],GOLD,8)
        else: # Three valleys linked by a shared council bridge.
            poly([(138,156),(158,101),(178,156)],accent);poly([(174,156),(192,86),(213,156)],GOLD);poly([(209,156),(228,104),(248,156)],accent)
            line([(145,170),(161,155),(224,155),(240,170)],GOLD,6)
            for x in (167,193,219):line([(x,157),(x,180)],GOLD,4)
        # Individual府州 seal and different sets of heraldic lozenges.
        rect((30,81,79,133),bg,GOLD,2)
        seal=c['group'][0]
        d.text((54*scale,104*scale),seal,font=seal_font,fill=GOLD,anchor='mm')
        svg.append(f'<text x="54" y="104" text-anchor="middle" dominant-baseline="central" font-family="Microsoft YaHei" font-size="25" fill="{GOLD}">{escape(seal)}</text>')
        for k in range(1+i%6):
            x=310;y=74+k*20;poly([(x,y-6),(x+6,y),(x,y+6),(x-6,y)])
        d.text((192*scale,228*scale),c['group'],font=label_font,fill=GOLD,anchor='mm')
        svg.append(f'<text x="192" y="228" text-anchor="middle" dominant-baseline="central" font-family="Microsoft YaHei" font-size="22" fill="{GOLD}">{escape(c["group"])}</text></svg>')
        im=im.resize((384,256),Image.Resampling.LANCZOS)
        tag=c['tag'];name=f'te_hbe_{tag.lower()}.dds'
        texture=out/'main_menu/gfx/coat_of_arms/textured_emblems'/name;save_dds(texture,im)
        (source/(tag+'.svg')).write_text(''.join(svg)+'\n',encoding='utf-8')
        im.save(source/(tag+'.png'))
        definitions.append(f'''{tag} = {{
    pattern = "pattern_solid.dds" color1 = "black" color2 = "gold"
    textured_emblem = {{ texture = "{name}" instance = {{ position = {{ 0.5 0.5 }} scale = {{ 1.0 1.0 }} }} }}
}}''')
        x=(i%6)*300+12;y=(i//6)*236+10
        preview.paste(im.convert('RGB').resize((276,184),Image.Resampling.LANCZOS),(x,y))
        proof.text((x,y+190),tag+'  '+c['name'],font=small_font,fill=GOLD)
        catalog.append(dict(tag=tag,country=c['name'],region=c['region'],texture=name,sha256=hashlib.sha256(texture.read_bytes()).hexdigest()))
    # Overwrite the original prototype definitions to avoid duplicate tag keys.
    put('main_menu/common/coat_of_arms/coat_of_arms/hbe_placeholders.txt','\n'.join(definitions))
    preview.save(root/'assets/flags_preview.png')
    return catalog
