"""Mechanical unit-sheet framing and localized permanent disease resistance."""
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw,ImageFont
import json,re,hashlib
from pdxscript import blocks,apply_edits
from build_flags import save_dds

def source_cell(atlas,index):
    # Authored sheet has uneven row gutters: equal thirds pick up the next row.
    xs=[(22,652),(665,1297),(1312,1940)]
    ys=[(30,272),(285,516),(523,768)]
    assert atlas.size==(1962,801)
    x0,x1=xs[index%3];y0,y1=ys[index//3]
    return atlas.crop((x0,y0,x1,y1))

def opaque_rectangle(cell):
    """Largest solid rectangle inside the source sheet's irregular alpha edge.

    The authored painting interiors have alpha around 250-253, rather than 255.
    A 245 cutoff removes only their feathered atlas border before RGB export.
    """
    width, height = cell.size
    alpha = cell.getchannel('A').load()
    heights = [0]*width
    best_area, best = 0, None
    for y in range(height):
        heights = [heights[x]+1 if alpha[x,y] >= 245 else 0 for x in range(width)]
        stack = []
        for x, h in enumerate(heights+[0]):
            left = x
            while stack and stack[-1][1] > h:
                start, previous = stack.pop()
                area = previous*(x-start)
                if area > best_area:
                    best_area, best = area, (start, y+1-previous, x, y+1)
                left = start
            if h and (not stack or stack[-1][1] < h):
                stack.append((left,h))
    assert best and best_area > width*height*.6
    assert cell.crop(best).getchannel('A').getextrema()[0] >= 245
    return best


def framed_portrait(cell):
    """Native continuous painting; infantry portrait reads its left third.

    Reframe the original scene, never repeat a portrait across the banner.
    Keep the top of the painting so hats and faces remain inside the crop.
    """
    scene=ImageOps.fit(cell.crop(opaque_rectangle(cell)).convert('RGB'),
                       (1080,440),Image.Resampling.LANCZOS)
    scene=scene.crop((259,0,1080,334))
    return scene.resize((1080,440),Image.Resampling.LANCZOS).convert('RGBA')

def apply(out,root):
    out,root=Path(out),Path(root);registry=json.loads((root/'assets/social_art_generation.json').read_text(encoding='utf-8'))
    atlas=Image.open(root/registry['units']['source']).convert('RGBA')
    definitions=(out/'in_game/common/unit_types/hbe_civic_units.txt').read_text(encoding='utf-8-sig')
    keys=[b[0] for b in blocks(definitions,0)];assert len(keys)==9
    preview=Image.new('RGB',(9*150,270),'#2d2b28');draw=ImageDraw.Draw(preview);font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',13)
    rows=[]
    for i,key in enumerate(keys):
        box=(round(i%3*atlas.width/3),round(i//3*atlas.height/3),round((i%3+1)*atlas.width/3),round((i//3+1)*atlas.height/3))
        cell=source_cell(atlas,i);sheet=framed_portrait(cell)
        p=out/'main_menu/gfx/interface/illustrations/units'/f'{key}.dds';save_dds(p,sheet)
        # RGB black means no unit-color replacement; alpha remains opaque.
        save_dds(out/'main_menu/gfx/interface/illustrations/units/masks'/f'{key}.dds',Image.new('RGBA',sheet.size,(0,0,0,255)))
        sheet.save(root/'assets/civic_icons'/f'{key}.png')
        thumb=sheet.crop((0,0,360,440)).resize((100,156),Image.Resampling.LANCZOS)
        preview.paste(thumb,(i*150+25,28),thumb);draw.rectangle((i*150+22,25,i*150+127,187),outline='#b9a061',width=3)
        draw.text((i*150+5,200),key.replace('hbe_','').replace('_','\n'),font=font,fill='#eee0b4')
        with Image.open(p) as decoded:assert decoded.size==(1080,440);assert len({decoded.crop((x,0,x+360,440)).tobytes() for x in (0,360,720)})==3
        rows.append(dict(unit=key,dimensions=[1080,440],grid=[3,1],portrait=[360,440],layout='continuous native scene',sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    preview_path=root/'assets/unit_thumbnail_alignment_preview.png';preview.save(preview_path)
    p=out/'main_menu/common/static_modifiers/hbe_modifiers.txt';t=p.read_text(encoding='utf-8-sig');b=next(b for b in blocks(t,0) if b[0]=='hbe_tianfu');body=t[b[2]:b[3]]
    if 'local_disease_resistance' not in body:body+=' local_disease_resistance = 0.05 '
    p.write_text(apply_edits(t,[(b[2],b[3],body)]),encoding='utf-8-sig')
    for lang in ('simp_chinese','english'):
        for p in (out/f'main_menu/localization/{lang}').glob('hbe*.yml'):
            t=p.read_text(encoding='utf-8-sig');old=t
            def text(m):
                if m[1] not in ('hbe_tianfu_desc','game_concept_hbe_term_tianfu_desc'):return m[0]
                line=m[0].replace('+10%','+7%').replace('+10％','+7％')
                disease='本地疾病抗性 +5%。' if lang=='simp_chinese' else 'Local disease resistance +5%.'
                if disease not in line:line=line[:-1]+'\\n'+disease+'"'
                return line
            t=re.sub(r'(?m)^ (\S+):[^\n]*$',text,t)
            if t!=old:p.write_text(t,encoding='utf-8-sig')
    return dict(version='0.3.1',local_only=True,unit_frames=rows,tianfu_local_disease_resistance=.05,preview=str(preview_path))
