"""Native EU5 heraldry with two-character LiSu inscriptions.

Flag scripts reference the game's own heraldic art. Only the new inscription
masks are shipped. The engine supplies cloth materials and final shading.
"""
import hashlib
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from build_flags import save_dds

FAMILIES=[
    ('hbe_ochre','hbe_ink','hbe_cinnabar',[
        ('te_dragon_flaming_pearl_clouds_gold_red_variant.dds','textured'),
        ('ce_fish_naiant.dds','colored'),('ce_chinese_white_tiger.dds','colored'),
        ('ce_chinese_double_phoenix.dds','colored'),('ce_chinese_vermilion_bird.dds','colored')]),
    ('hbe_cinnabar','hbe_old_gold','hbe_ink',[
        ('ce_lotus_throne.dds','colored'),('ce_chinese_vermilion_bird.dds','colored'),
        ('ce_chinese_double_phoenix.dds','colored'),('ce_chinese_blessing_prosperity.dds','colored')]),
    ('hbe_indigo','hbe_ivory','hbe_cinnabar',[
        ('ce_chinese_azure_dragon.dds','colored'),
        ('te_dragon_flaming_pearl_clouds_gold_azure_variant.dds','textured'),
        ('ce_fishes_pandya.dds','colored'),('ce_chinese_black_turtle.dds','colored'),
        ('ce_boathooks_saltire.dds','colored'),('ce_chinese_qilin.dds','colored'),
        ('ce_chinese_double_phoenix.dds','colored')]),
    ('hbe_ivory','hbe_ink','hbe_cinnabar',[
        ('ce_chinese_white_tiger.dds','colored'),('ce_chinese_qilin.dds','colored'),
        ('ce_chinese_black_turtle.dds','colored'),('ce_mountains_landscape_chitral.dds','colored'),
        ('ce_chinese_azure_dragon.dds','colored'),('ce_horse_courant.dds','colored'),
        ('ce_chinese_double_phoenix.dds','colored')]),
    ('hbe_dark_red','hbe_ivory','hbe_old_gold',[
        ('ce_wheat_ear.dds','colored'),('ce_wheat_garb.dds','colored'),
        ('ce_tree_fruit_simple.dds','colored'),('ce_heron_wide.dds','colored')]),
    ('hbe_pine','hbe_old_gold','hbe_ivory',[
        ('te_wind_horse.dds','textured'),('ce_chinese_auspicious_conch_shell.dds','colored'),
        ('te_tibetan_garuda.dds','textured')]),
    ('hbe_russet','hbe_ivory','hbe_old_gold',[
        ('ce_lotus_chakra.dds','colored'),('ce_chinese_auspicious_conch_shell.dds','colored'),
        ('ce_lotus_flower_02.dds','colored'),('ce_mountains_hunza.dds','colored'),
        ('ce_chinese_crossed_vajra_taijitu.dds','colored'),('te_tibetan_flaming_jewels.dds','textured')])
]
COLORS={
    'hbe_ochre':(182,137,49),'hbe_cinnabar':(141,36,34),'hbe_dark_red':(91,28,29),
    'hbe_old_gold':(216,180,91),'hbe_ink':(30,30,28),'hbe_indigo':(31,51,80),
    'hbe_ivory':(232,222,192),'hbe_white':(250,248,242),'hbe_pine':(31,77,49),'hbe_russet':(99,52,38)
}

def build_flags(out,countries,regions,root,put,game):
    art=game/'main_menu/gfx/coat_of_arms'
    font=Path('C:/Windows/Fonts/SIMLI.TTF')
    if not font.is_file():raise RuntimeError('LiSu font SIMLI.TTF is required; no substitute is allowed.')
    li=ImageFont.truetype(str(font),240)
    label=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
    title=ImageFont.truetype(str(font),36)
    assets=root/'assets/flags';assets.mkdir(parents=True,exist_ok=True)
    # An independent white nameplate keeps LiSu readable under engine cloth shading.
    plate=Image.new('RGBA',(384,128),(255,0,0,255))
    save_dds(out/'main_menu/gfx/coat_of_arms/colored_emblems/ce_hbe_nameplate.dds',plate)
    proof=Image.new('RGB',(1800,1450),'#312a22');pd=ImageDraw.Draw(proof)
    pd.text((26,17),'神圣巴蜀帝国 · 府州旗样',font=title,fill=COLORS['hbe_old_gold'])
    pd.text((26,60),'原生纹章构件 / 隶书两字题旗 · 配色校样（布面材质由游戏渲染）',font=label,fill=COLORS['hbe_ivory'])
    definitions=[];catalog=[];indices={r[0]:0 for r in regions}
    def recolor(src,color):
        src=src.convert('RGBA');rgb=Image.new('RGBA',src.size);pixels=[]
        for r,g,b,a in src.getdata():
            v=max(r,g,b)/255
            col=(14,12,10) if v<0.015 else tuple(int(c*(.52+.48*min(1,v*2))) for c in color)
            pixels.append((*col,a))
        rgb.putdata(pixels);return rgb
    for i,c in enumerate(countries):
        ri=next(j for j,r in enumerate(regions) if r[0]==c['region'])
        j=indices[c['region']];indices[c['region']]+=1
        field,metal,trim,charges=FAMILIES[ri];texture,kind=charges[j]
        pattern='pattern_fringe.dds' if j%3==0 else 'pattern_solid.dds'
        border=None
        if j%3==2:field,trim=trim,field
        if field in ('hbe_ivory','hbe_old_gold','hbe_ochre'):metal='hbe_ink'
        elif metal=='hbe_ink':metal='hbe_ivory'
        name=c['group'];assert len(name)==2,name
        filename=f'ce_hbe_name_{c["tag"].lower()}.dds'
        alpha=Image.new('L',(768,256),0);ad=ImageDraw.Draw(alpha)
        ad.text((384,128),name,font=li,fill=255,anchor='mm',stroke_width=1)
        alpha=alpha.resize((384,128),Image.Resampling.LANCZOS)
        glyph=Image.new('RGBA',(384,128),(255,0,0,0));glyph.putalpha(alpha)
        glyphpath=out/'main_menu/gfx/coat_of_arms/colored_emblems'/filename;save_dds(glyphpath,glyph)
        layers=[];dependencies=[('patterns',pattern)]
        category='textured_emblems' if kind=='textured' else 'colored_emblems'
        dependencies.append((category,texture))
        scale=(.62,.55) if kind=='textured' else (.60,.55)
        if texture=='te_wind_horse.dds':scale=(.52,.55)
        if kind=='textured':
            layers.append(f'textured_emblem = {{ texture = "{texture}" instance = {{ position = {{ 0.5 0.33 }} scale = {{ {scale[0]} {scale[1]} }} }} }}')
        else:
            layers.append(f'colored_emblem = {{ texture = "{texture}" color1 = "{metal}" color2 = "{metal}" color3 = "{metal}" instance = {{ position = {{ 0.5 0.33 }} scale = {{ {scale[0]} {scale[1]} }} }} }}')
        if border:
            dependencies.append(('colored_emblems',border))
            layers.insert(0,f'colored_emblem = {{ texture = "{border}" color1 = "{metal}" color2 = "{metal}" color3 = "{metal}" instance = {{ position = {{ 0.5 0.5 }} scale = {{ 0.94 0.93 }} }} }}')
        layers.append('colored_emblem = { texture = "ce_hbe_nameplate.dds" color1 = "hbe_white" color2 = "hbe_white" color3 = "hbe_white" instance = { position = { 0.5 0.77 } scale = { 0.69 0.31 } } }')
        layers.append(f'colored_emblem = {{ texture = "{filename}" color1 = "hbe_ink" color2 = "hbe_ink" color3 = "hbe_ink" instance = {{ position = {{ 0.5 0.77 }} scale = {{ 0.60 0.28 }} }} }}')
        definition=f'''{c['tag']} = {{
    pattern = "{pattern}" color1 = "{field}" color2 = "{trim}"
    {' '.join(layers)}
}}''';definitions.append(definition)
        for category,asset in dependencies:
            if not (art/category/asset).is_file():raise FileNotFoundError(art/category/asset)
        im=Image.new('RGBA',(768,512),COLORS[field])
        if pattern=='pattern_fringe.dds':
            d=ImageDraw.Draw(im);d.rectangle((0,0,767,511),outline=COLORS[trim],width=27)
        if border:
            layer=recolor(Image.open(art/'colored_emblems'/border),COLORS[metal]).resize((722,476),Image.Resampling.LANCZOS)
            im.alpha_composite(layer,(23,18))
        charge=Image.open(art/('textured_emblems' if kind=='textured' else 'colored_emblems')/texture).convert('RGBA')
        if kind!='textured':charge=recolor(charge,COLORS[metal])
        cw,ch=round(768*scale[0]),round(512*scale[1])
        im.alpha_composite(charge.resize((cw,ch),Image.Resampling.LANCZOS),(round(384-cw/2),round(512*.33-ch/2)))
        ImageDraw.Draw(im).rectangle((119,315,649,474),fill=COLORS['hbe_white'])
        lettering=Image.new('RGBA',alpha.size,COLORS['hbe_ink']);lettering.putalpha(alpha)
        tw,th=round(768*.60),round(512*.28)
        im.alpha_composite(lettering.resize((tw,th),Image.Resampling.LANCZOS),(round(384-tw/2),round(512*.77-th/2)))
        im=im.resize((384,256),Image.Resampling.LANCZOS);im.save(assets/(c['tag']+'.png'))
        (assets/(c['tag']+'.txt')).write_text(definition+'\n',encoding='utf-8')
        x=(i%6)*300+12;y=(i//6)*224+106
        proof.paste(im.convert('RGB').resize((276,184),Image.Resampling.LANCZOS),(x,y))
        pd.text((x,y+188),c['tag']+'  '+c['name'],font=label,fill=COLORS['hbe_ivory'])
        catalog.append(dict(tag=c['tag'],country=c['name'],region=c['region'],inscription=name,
            font='LiSu / 隶书 (SIMLI.TTF)',nameplate='white field / black inscription',texture=filename,sha256=hashlib.sha256(glyphpath.read_bytes()).hexdigest(),
            definition_sha256=hashlib.sha256(definition.encode()).hexdigest(),
            native_assets=[{'category':cat,'file':f} for cat,f in dependencies]))
    # Only superseded generated files with known country tags are removed.
    for c in countries:
        old=out/'main_menu/gfx/coat_of_arms/textured_emblems'/f'te_hbe_{c["tag"].lower()}.dds'
        if old.is_file():old.unlink()
        oldsvg=assets/(c['tag']+'.svg')
        if oldsvg.is_file():oldsvg.unlink()
    put('main_menu/common/coat_of_arms/coat_of_arms/hbe_placeholders.txt','\n'.join(definitions))
    put('main_menu/common/named_colors/hbe_flags.txt','colors = {\n'+'\n'.join(f'{k} = rgb {{ '+' '.join(str(v) for v in rgb)+' }' for k,rgb in COLORS.items())+'\n}')
    proof.save(root/'assets/flags_preview.png')
    (root/'assets/flag_art_notes.md').write_text('旗面采用 EU5 原生纹章构件与引擎布面渲染，发行包不复制原版纹章贴图。\n各国两字简称用本机 SIMLI.TTF（隶书）栅格化为独立纹章遮罩，字体文件不打包。\n校样仅演示构图和配色，不是游戏截图。\n',encoding='utf-8')
    return catalog
