"""Static native-material HUD proof; this does not simulate the game's GUI renderer."""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageChops
from build_local_affairs_hud import ICONS, COLORS


def preview(mod, game, destination):
    native = Path(game)/'game/main_menu/gfx/interface'
    def texture(path, size):
        with Image.open(native/path) as source:
            return source.convert('RGBA').resize((size,size),Image.Resampling.LANCZOS)
    def tint(image, color):
        layer=Image.new('RGBA',image.size,tuple(round(c*255) for c in color)+(255,))
        layer.putalpha(image.getchannel('A'))
        return layer
    def circle(state, size, ratio):
        image=tint(texture('component_tiles/hud_corners/circle_background.dds',size),(0.10,0.16,0.19))
        image.alpha_composite(texture('component_tiles/hud_corners/circle_progress_bg.dds',size))
        if ratio:
            n=round(size*.89); ring=texture('pie_charts/pie_chart_blue_progress.dds',n)
            mask=Image.new('L',(n,n));ImageDraw.Draw(mask).pieslice((0,0,n-1,n-1),-90,-90+360*ratio,fill=255)
            ring.putalpha(ImageChops.multiply(ring.getchannel('A'),mask))
            image.alpha_composite(ring,((size-n)//2,)*2)
        n=round(size*.70)
        image.alpha_composite(tint(texture('component_tiles/hud_corners/circle_background.dds',n),COLORS[state]),((size-n)//2,)*2)
        with Image.open(Path(mod)/'main_menu'/ICONS[state]) as source:
            n=round(size*.65); icon=source.convert('RGBA').resize((n,n),Image.Resampling.LANCZOS)
        image.alpha_composite(icon,((size-n)//2,)*2)
        image.alpha_composite(texture('component_tiles/hud_corners/graphical_culture/circle_frame_east_asian_gfx.dds',size))
        return image
    proof=Image.new('RGB',(720,388),'#1c2629');draw=ImageDraw.Draw(proof)
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',21)
    small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',15)
    for i,(state,label) in enumerate((('idle','闲置 · 灰蓝'),('local','地方 · 灰绿'),('national','中央 · 暗朱'))):
        center=120+240*i;ratio=(0,.4,.72)[i]
        draw.text((center,14),label,font=font,fill='#e5d6b5',anchor='mt')
        for size,y in ((128,52),(64,218),(48,308)):
            image=circle(state,size,ratio);proof.paste(image,(center-size//2,y),image)
    for size,y in ((128,108),(64,240),(48,324)):
        draw.text((9,y),str(size)+'px',font=small,fill='#b6bcb9')
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True);proof.save(destination)


if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game-dir',type=Path,required=True)
    parser.add_argument('--mod-dir',type=Path,default=root/'mod/holy_bashu_empire')
    parser.add_argument('--output',type=Path,default=root/'assets/local_affairs_hud_v2/preview.png')
    args=parser.parse_args();preview(args.mod_dir,args.game_dir,args.output)
