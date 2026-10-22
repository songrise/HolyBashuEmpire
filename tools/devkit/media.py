"""Shared poster compositing primitives, extracted without changing rendering.

The versioned poster script retains its editorial layout and source artwork.
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageChops, ImageFilter

INK = (13, 32, 47)
FONT = Path('C:/Windows/Fonts/NotoSerifSC-VF.ttf')


def font(size, path=None):
    result = ImageFont.truetype(str(path or FONT), size)
    result.set_variation_by_axes([900])
    return result


def paper_fill(image, box, tile):
    # An existing clean paper swatch, not newly generated art or a flat white patch.
    layer = Image.new('RGB', (box[2]-box[0], box[3]-box[1]))
    for y in range(0, layer.height, tile.height):
        for x in range(0, layer.width, tile.width):
            layer.paste(tile, (x, y))
    image.paste(layer, box[:2])


def label(image, box, text, size, tile, *, font_path=None):
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
    f = font(size, font_path)
    while f.getbbox(text)[2] > box[2]-box[0]-8 or f.getbbox(text)[3]-f.getbbox(text)[1] > box[3]-box[1]-6:
        size -= 1
        if size < 8:
            raise ValueError('Label does not fit its box at a readable size')
        f = font(size, font_path)
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
    if diff.getbbox() is not None:
        raise ValueError('Artwork outside authorized edit regions changed')


def compose(template, output):
    """Code-only screenshot/text edits in declared boxes; retain all other pixels."""
    from .common import read_json
    template, output = Path(template).resolve(), Path(output).resolve()
    spec = read_json(template)
    if spec.get('schema_version') != 1:
        raise ValueError('Unsupported media template')
    def source(name):
        return (template.parent / name).resolve()
    if output.with_suffix('.png').exists() or output.with_suffix('.jpg').exists():
        raise FileExistsError('Choose a new media output stem')
    with Image.open(source(spec['base'])) as original:
        image = original.convert('RGB')
    if list(image.size) != spec['size']:
        raise ValueError('Base dimensions changed; recheck declared boxes')
    before = image.copy()
    boxes = []
    for operation in spec['operations']:
        box = operation['box']
        if len(box) != 4 or not (0 <= box[0] < box[2] <= image.width and 0 <= box[1] < box[3] <= image.height):
            raise ValueError('Edit box is outside the base image')
        boxes.append(box)
        if operation['type'] == 'inset':
            with Image.open(source(operation['source'])) as screenshot:
                if 'source_size' in operation and list(screenshot.size) != operation['source_size']:
                    raise ValueError('Screenshot dimensions changed; recheck crop')
                screenshot = screenshot.copy()
            crop = operation.get('crop')
            if crop:
                if not (0 <= crop[0] < crop[2] <= screenshot.width and 0 <= crop[1] < crop[3] <= screenshot.height):
                    raise ValueError('Crop is outside the screenshot')
                screenshot = screenshot.crop(crop)
            inset(image, screenshot, box, tuple(operation.get('background', [20, 25, 30])))
        elif operation['type'] == 'label':
            with Image.open(source(operation['paper'])) as paper:
                tile = paper.convert('RGB').crop(operation['paper_crop'])
            label(image, box, operation['text'], operation['size'], tile,
                  font_path=source(spec['font']) if spec.get('font') else None)
        else:
            raise ValueError('Unknown media operation: ' + operation['type'])
    check_preserved(before, image, boxes)
    output.parent.mkdir(parents=True, exist_ok=True)
    export(image, output)
    return dict(template=str(template), png=str(output.with_suffix('.png')),
                jpg=str(output.with_suffix('.jpg')), outside_regions_pixel_identical=True)
