"""No-text Bashu heraldry: generated charges on native cloth flag fields."""
import hashlib
from collections import deque
from PIL import Image,ImageDraw,ImageFont
from build_flags import save_dds

COLORS={'hbe_indigo':(26,43,66),'hbe_cinnabar':(122,30,28),
        'hbe_pine':(23,60,39),'hbe_dark_red':(76,24,31),
        'hbe_russet':(89,44,30),'hbe_azure':(35,69,85),'hbe_gold':(191,157,80),'hbe_ivory':(225,215,186)}
FIELDS=['hbe_indigo','hbe_cinnabar','hbe_indigo','hbe_pine','hbe_dark_red','hbe_pine','hbe_russet']
PATTERNS=['pattern_fringe.dds','pattern_diagonal_split_01.dds','pattern_vertical_split_01.dds','pattern_horizontal_bar_01.dds','pattern_horizontal_split_01.dds','pattern_solid.dds','pattern_border_thin.dds']
def extract_charges(im,cols=6,rows=6,threshold=128):
    # Assign whole connected atlas objects by center, keeping tails across grid lines.
    w,h=im.size;alpha=im.getchannel('A').tobytes();seen=set();groups=[[] for _ in range(cols*rows)]
    for start,v in enumerate(alpha):
        if v<=threshold or start in seen:continue
        seen.add(start);q=deque([start]);points=[]
        while q:
            p=q.popleft();points.append(p);x=p%w;y=p//w
            for n in ((p-1 if x else -1),(p+1 if x<w-1 else -1),(p-w if y else -1),(p+w if y<h-1 else -1)):
                if n>=0 and n not in seen and alpha[n]>threshold:seen.add(n);q.append(n)
        xs=[p%w for p in points];ys=[p//w for p in points]
        if len(points)<35:continue
        b=(min(xs),min(ys),max(xs)+1,max(ys)+1)
        col=min(cols-1,int((b[0]+b[2])/2/w*cols));row=min(rows-1,int((b[1]+b[3])/2/h*rows))
        groups[row*cols+col].append((len(points),b,points))
    result=[]
    for parts in groups:
        if not parts:raise ValueError('Missing isolated heraldic cell '+str(len(result)))
        largest=max(p[0] for p in parts)
        selected=[(b,points) for area,b,points in parts if area>=max(35,largest*.02)]
        bounds=(max(0,min(b[0] for b,_ in selected)-1),max(0,min(b[1] for b,_ in selected)-1),min(w,max(b[2] for b,_ in selected)+1),min(h,max(b[3] for b,_ in selected)+1))
        x0,y0,x1,y1=bounds;bw,bh=x1-x0,y1-y0;mask=bytearray(bw*bh)
        for _,points in selected:
            for p in points:
                x=p%w;y=p//w
                for dy in (-1,0,1):
                    for dx in (-1,0,1):
                        xx,yy=x+dx,y+dy
                        if x0<=xx<x1 and y0<=yy<y1:mask[(yy-y0)*bw+xx-x0]=alpha[yy*w+xx]
        charge=im.crop(bounds);charge.putalpha(Image.frombytes('L',(bw,bh),bytes(mask)))
        result.append((charge,bounds))
    return result

def build_flags(out,countries,regions,root,put,game):
    atlas=Image.open(root/'assets/flag_redesign/heraldic_charges.png').convert('RGBA')
    if atlas.getchannel('A').getextrema()[0]!=0:raise ValueError('Heraldic charges need transparent gutters')
    charges=extract_charges(atlas)
    folder=root/'assets/flags';folder.mkdir(parents=True,exist_ok=True)
    proof=Image.new('RGB',(1800,1440),'#292722');draw=ImageDraw.Draw(proof)
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
    draw.text((20,15),'三十六府州旗样 · 无文字 / 原生旗底与独立纹章',font=font,fill='#d7ba7f')
    definitions=[];catalog=[];indices={r[0]:0 for r in regions}
    for i,c in enumerate(countries):
        ri=next(j for j,r in enumerate(regions) if r[0]==c['region']);j=indices[c['region']];indices[c['region']]+=1
        charge,box=charges[i];ratio=min(450/charge.width,450/charge.height)
        charge=charge.resize((round(charge.width*ratio),round(charge.height*ratio)),Image.Resampling.LANCZOS)
        sprite=Image.new('RGBA',(512,512));sprite.alpha_composite(charge,((512-charge.width)//2,(512-charge.height)//2))
        texture='te_hbe_crest_'+c['tag'].lower()+'.dds';path=out/'main_menu/gfx/coat_of_arms/textured_emblems'/texture;save_dds(path,sprite)
        field=FIELDS[ri];pattern=PATTERNS[(j+ri)%len(PATTERNS)]
        accent=('hbe_gold' if j%2==0 else 'hbe_ivory') if pattern in ('pattern_fringe.dds','pattern_border_thin.dds') else ['hbe_azure','hbe_cinnabar','hbe_pine','hbe_dark_red','hbe_indigo','hbe_russet'][(j+ri)%6]
        if accent==field:accent='hbe_azure' if field!='hbe_azure' else 'hbe_dark_red'
        definition=f'''{c['tag']} = {{
 pattern = "{pattern}" color1 = "{field}" color2 = "{accent}"
 textured_emblem = {{ texture = "{texture}" instance = {{ position = {{ 0.5 0.5 }} scale = {{ 0.72 0.95 }} }} }}
}}'''
        definitions.append(definition)
        for ref in (game/'main_menu/gfx/coat_of_arms/patterns'/pattern,):
            if not ref.is_file():raise FileNotFoundError(ref)
        native_pattern=Image.open(game/'main_menu/gfx/coat_of_arms/patterns'/pattern).convert('RGBA').resize((384,256))
        pixels=[]
        for _,g,_,_ in native_pattern.getdata():
            t=g/255;pixels.append(tuple(round(a*(1-t)+b*t) for a,b in zip(COLORS[field],COLORS[accent]))+(255,))
        field_art=Image.new('RGBA',(384,256));field_art.putdata(pixels)
        visual=sprite.resize((276,243),Image.Resampling.LANCZOS);field_art.alpha_composite(visual,(54,6));field_art.save(folder/(c['tag']+'.png'))
        (folder/(c['tag']+'.txt')).write_text(definition+'\n',encoding='utf-8')
        x=(i%6)*300+12;y=(i//6)*228+60
        proof.paste(field_art.convert('RGB').resize((276,184),Image.Resampling.LANCZOS),(x,y));draw.text((x,y+188),c['tag']+'  '+c['name'],font=font,fill='#dfd0ab')
        catalog.append(dict(tag=c['tag'],country=c['name'],region=c['region'],inscription='',font=None,
            texture=texture,texture_category='textured_emblems',nameplate=None,dimensions=[512,512],
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),definition_sha256=hashlib.sha256(definition.encode()).hexdigest(),
            source='assets/flag_redesign/heraldic_charges.png',cell=i,crop=list(box),
            native_assets=[{'category':'patterns','file':pattern}]))
    for category in ('colored_emblems','textured_emblems'):
        p=out/'main_menu/gfx/coat_of_arms'/category
        for f in p.glob('*hbe_name*.dds'):f.unlink()
    put('main_menu/common/coat_of_arms/coat_of_arms/hbe_placeholders.txt','\n'.join(definitions))
    put('main_menu/common/named_colors/hbe_flags.txt','colors = {\n'+'\n'.join(k+' = rgb { '+' '.join(map(str,v))+' }' for k,v in COLORS.items())+'\n}')
    proof.save(root/'assets/flags_preview.png')
    (root/'assets/flag_art_notes.md').write_text('已按用户要求撤去三十六国全部文字和白色铭牌。旗底与布料由原版渲染，36幅独立纹章使用内置 image_gen 生成并机械分格。校样显示配色与构图，非游戏截图。\n',encoding='utf-8')
    return catalog
