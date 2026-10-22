"""Replace supplied screenshot insets and text, retaining existing poster artwork.

Local media only. Does not build the mod, contact Steam, publish, or commit.
"""
from pathlib import Path
import argparse
import json
import shutil

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageChops, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
INK = (13, 32, 47)
FONT = Path('C:/Windows/Fonts/NotoSerifSC-VF.ttf')


def font(size):
    result = ImageFont.truetype(str(FONT), size)
    result.set_variation_by_axes([900])
    return result


def paper_fill(image, box, tile):
    # An existing clean paper swatch, not newly generated art or a flat white patch.
    layer = Image.new('RGB', (box[2]-box[0], box[3]-box[1]))
    for y in range(0, layer.height, tile.height):
        for x in range(0, layer.width, tile.width):
            layer.paste(tile, (x, y))
    image.paste(layer, box[:2])


def label(image, box, text, size, tile):
    old = image.crop(box)
    # Match the local paper tone and soften the join so a new label is not a pasted rectangle.
    pixels = [p for p in old.get_flattened_data() if p[0]>170 and p[1]>150 and p[2]>110]
    target = [sorted(p[c] for p in pixels)[len(pixels)//2] for c in range(3)]
    source = list(tile.get_flattened_data())
    channels = []
    for c in range(3):
        median = sorted(p[c] for p in source)[len(source)//2]
        channels.append(tile.getchannel(c).point([max(0,min(255,x+target[c]-median)) for x in range(256)]))
    paper_fill(image, box, Image.merge('RGB', channels))
    mask = Image.new('L', old.size, 0)
    ImageDraw.Draw(mask).rectangle((3,3,old.width-4,old.height-4), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(1))
    image.paste(Image.composite(image.crop(box), old, mask), box[:2])
    f = font(size)
    while f.getbbox(text)[2] > box[2]-box[0]-8 or f.getbbox(text)[3]-f.getbbox(text)[1] > box[3]-box[1]-6:
        size -= 1
        f = font(size)
    layer = image.crop(box)
    draw = ImageDraw.Draw(layer)
    x = layer.width/2
    y = layer.height/2
    draw.text((x, y), text, font=f, fill=INK, anchor='mm')
    image.paste(layer, box[:2])


def inset(image, source, box, background):
    fitted = ImageOps.contain(source.convert('RGB'), (box[2]-box[0], box[3]-box[1]), Image.Resampling.LANCZOS)
    paper_fill(image, box, background) if isinstance(background, Image.Image) else ImageDraw.Draw(image).rectangle((box[0], box[1], box[2]-1, box[3]-1), fill=background)
    xy = (box[0]+(box[2]-box[0]-fitted.width)//2, box[1]+(box[3]-box[1]-fitted.height)//2)
    image.paste(fitted, xy)
    return [*xy, xy[0]+fitted.width, xy[1]+fitted.height]


def export(image, path):
    image.save(path.with_suffix('.png'), optimize=True)
    for quality in (94, 92, 90, 88, 86):
        image.save(path.with_suffix('.jpg'), quality=quality, optimize=True, subsampling=0)
        if path.with_suffix('.jpg').stat().st_size < 1_000_000:
            break
    assert path.with_suffix('.jpg').stat().st_size < 1_000_000


def check_preserved(before, after, boxes):
    diff = ImageChops.difference(before, after)
    for box in boxes:
        ImageDraw.Draw(diff).rectangle((box[0], box[1], box[2]-1, box[3]-1), fill=(0, 0, 0))
    assert diff.getbbox() is None, 'Artwork outside authorized edit regions changed'


def apply(technology, map_image, output):
    assets = ROOT/'assets/workshop/unified'
    output.mkdir(parents=True, exist_ok=True)
    # Keep authoritative screenshots beside project assets rather than in OS temp.
    for source, name in ((technology, '科技原始截图.png'), (map_image, '地图原始截图.png')):
        destination = assets/name
        if source.resolve() != destination.resolve():
            shutil.copyfile(source, destination)
    with Image.open(assets/'七圈地图.png') as source:
        paper = source.convert('RGB').crop((1290, 230, 1550, 253))
    rows = []
    for name in ('科技分支', '七圈地图'):
        image = Image.open(assets/(name+'.png')).convert('RGB')
        before = image.copy()
        assert image.size == (1672, 941)
        if name == '科技分支':
            boxes = [(34,118,850,864), (534,0,1142,103), (486,887,1178,931)]
            screenshot_box = inset(image, Image.open(technology), boxes[0], (23, 29, 37))
            label(image, boxes[1], '地方各有成法', 88, paper)
            label(image, boxes[2], '地区科技 · 产业传习 · 文化与军制联动', 28, paper)
        else:
            boxes = [(50,114,994,820), (467,0,1213,103), (1050,145,1616,208), (385,845,1297,897)]
            # The supplied wide capture includes the full HBE footprint; trim surrounding countries.
            full_map = Image.open(map_image)
            assert full_map.size == (1203,867), 'Recheck the HBE crop for a different source screenshot'
            crop = (260,40,1200,743)
            screenshot_box = inset(image, full_map.crop(crop), boxes[0], paper)
            label(image, boxes[1], '山川之间，择府而治', 84, paper)
            label(image, boxes[2], '山川分治 · 诸府共盟', 40, paper)
            label(image, boxes[3], '经营产业，缔结盟约，写下蜀地的兴衰', 31, paper)
        check_preserved(before, image, boxes)
        export(image, assets/name)
        shutil.copyfile(assets/(name+'.jpg'), output/(name+'.jpg'))
        rows.append(dict(name=name, dimensions=list(image.size), screenshot_box=screenshot_box,
                         mode='code-only screenshot and text replacement', outside_regions_pixel_identical=True))
    (output/'code_edit_report.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    return rows


def affairs(frame, screenshot, output):
    assets = ROOT/'assets/workshop/unified'
    assets.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    raw = assets/'地方事业底图.png'
    source = assets/'地方事业原始截图.png'
    if frame.resolve() != raw.resolve():
        shutil.copyfile(frame, raw)
    if screenshot.resolve() != source.resolve():
        shutil.copyfile(screenshot, source)
    image = Image.open(raw).convert('RGB')
    assert image.size == (1672,941)
    before = image.copy()
    box = (34,118,850,864)
    screenshot_box = inset(image, Image.open(source), box, (20,25,30))
    check_preserved(before, image, [box])
    export(image, assets/'地方事业')
    shutil.copyfile(assets/'地方事业.jpg', output/'地方事业.jpg')
    return dict(name='地方事业', dimensions=list(image.size), screenshot_box=screenshot_box,
                mode='ImageGen artwork with exact user screenshot inset',
                outside_regions_pixel_identical=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--technology', type=Path)
    p.add_argument('--map', type=Path)
    p.add_argument('--affairs-frame', type=Path)
    p.add_argument('--affairs-screenshot', type=Path)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    rows = []
    if args.technology and args.map:
        rows += apply(args.technology, args.map, args.output)
    if args.affairs_frame and args.affairs_screenshot:
        rows.append(affairs(args.affairs_frame, args.affairs_screenshot, args.output))
    if not rows:
        p.error('Provide the technology/map pair or the affairs frame/screenshot pair')
    print(json.dumps(rows, ensure_ascii=False, indent=2))
