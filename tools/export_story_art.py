"""Mechanical export only: preserve generated paintings, register native EU5 scenes.

No filters, recolouring, sharpening or creative editing. PNG sources stay in the
development assets folder; runtime contains only cropped DDS textures and tables.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / ('assets/event_expansion' if (ROOT / 'assets/event_expansion').is_dir() else 'assets/event_illustrations')
OUT = ROOT / 'mod/holy_bashu_empire'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(relative, text):
    path = OUT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + '\n', encoding='utf-8-sig')


def export():
    spec = json.loads((SOURCES / 'final-scenes.prompt.json').read_text(encoding='utf-8'))
    jobs = spec['scenes']
    missing = [j['key'] for j in jobs if not (SOURCES / (j['key'] + '.png')).is_file()]
    if missing:
        raise RuntimeError('Generation incomplete: ' + ', '.join(missing))
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 23)
    cols = 3
    cell_w, cell_h = 600, 298
    rows = (len(jobs) + cols - 1) // cols
    proof = Image.new('RGB', (cols * cell_w, rows * cell_h), '#252b2d')
    draw = ImageDraw.Draw(proof)
    original_proof = Image.new('RGB', (cols * cell_w, rows * 369), '#252b2d')
    original_draw = ImageDraw.Draw(original_proof)
    imgs, scenes, registrations, exports = [], [], [], []
    # Private empty country layer: no random stock portrait or unrelated prop can
    # be drawn on top of figures already painted into these complete backgrounds.
    imgs.append('hbe_story_empty = { tag = "hbe_story_empty" illustration_image = { texture_file = "gfx/interface/illustrations/event/characters/empty.dds" priority = 100 scope = country trigger = { always = yes } } }')
    template_path = OUT / 'in_game/gfx/scenes/hbe_event_scenes.txt'
    template = template_path.read_text(encoding='utf-8-sig')
    from pdxscript import blocks
    shell = next(template[s:e] for name, _, s, e, _ in blocks(template, 0) if name == 'hbe_event_scene_council')
    for i, job in enumerate(jobs):
        key = job['key']
        src = SOURCES / (key + '.png')
        with Image.open(src) as im:
            im.load()
            raw = im.convert('RGB')
        if raw.width < 1000 or raw.height < 600:
            raise RuntimeError('Unexpected low-resolution source: ' + key)
        # The astronomy reference places the target star near the top of frame.
        # This source-specific crop preserves it rather than centring blindly.
        center = {'observatory': (.5, .15), 'terraces': (.5, 0)}.get(key, (.5, .5))
        cropped = ImageOps.fit(raw, (1080, 440), Image.Resampling.LANCZOS, centering=center)
        target = OUT / 'main_menu/gfx/interface/hbe/story_events' / (key + '.dds')
        target.parent.mkdir(parents=True, exist_ok=True)
        cropped.convert('RGBA').save(target, pixel_format='DXT5')
        with Image.open(target) as check:
            check.load()
            assert check.size == (1080, 440)
        texture = f'gfx/interface/hbe/story_events/{key}.dds'
        background = f'hbe_story_background_{key}'
        scene = f'hbe_story_scene_{key}'
        tag = f'hbe_story_art_{key}'
        imgs.append(f'{background} = {{ tag = "{background}" illustration_image = {{ texture_file = "{texture}" priority = 100 scope = country trigger = {{ always = yes }} }} }}')
        content = re.sub(r'list = "[^"]+"', 'list = "hbe_story_empty"', shell)
        # Keep EU5's native layered scene meshes and camera; only the painted
        # background is visible. All stock character/vfx layers are transparent.
        content = content.replace('list = "hbe_story_empty"\n    }\n    gfx_environment_file', f'list = "{background}"\n    }}\n    gfx_environment_file', 1)
        if f'list = "{background}"' not in content:
            raise RuntimeError('Could not replace background layer: ' + key)
        scenes.append(scene + ' = {' + content + '}')
        registrations.append(f'hbe_story_illustration_{key} = {{ scene = "{scene}" tags = {{ 1000 = {tag} }} }}')
        x, y = i % cols * cell_w, i // cols * cell_h
        thumb = cropped.resize((600, 244), Image.Resampling.LANCZOS)
        proof.paste(thumb, (x, y))
        draw.text((x + 15, y + 256), job['title'], font=font, fill='#dfd4bf')
        oy = i // cols * 369
        original_proof.paste(ImageOps.fit(raw, (600, 337), Image.Resampling.LANCZOS), (x, oy))
        original_draw.text((x + 15, oy + 340), job['title'], font=font, fill='#dfd4bf')
        exports.append(dict(key=key, title=job['title'], themes=job['themes'], source=src.relative_to(ROOT).as_posix(), source_dimensions=list(raw.size), source_sha256=sha(src), texture=target.relative_to(OUT).as_posix(), dimensions=[1080, 440], compression='DXT5', bytes=target.stat().st_size, sha256=sha(target), scene=scene, illustration_tag=tag, crop_center=list(center), retained_reference=key in ('fossils', 'observatory')))
    write('in_game/gfx/images/hbe_story_backgrounds.txt', '\n'.join(imgs))
    write('in_game/gfx/scenes/hbe_story_scenes.txt', '\n'.join(scenes))
    write('loading_screen/gfx/illustrations/database/hbe_story_illustrations.txt', '\n'.join(registrations))
    proof.save(SOURCES / 'runtime_preview.jpg', quality=92)
    original_proof.save(SOURCES / 'originals_preview.jpg', quality=92)
    (ROOT / 'data/event_art_expansion.json').write_text(json.dumps(dict(mode='built-in image_gen; mechanical DDS export', style='natural painterly realism, latest user-selected references', assets=exports, runtime_bytes=sum(e['bytes'] for e in exports)), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(scenes=len(exports), runtime_megabytes=round(sum(e['bytes'] for e in exports)/1024**2, 2), preview=str(SOURCES / 'runtime_preview.jpg')), ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--assets-dir', type=Path, help='Development PNG/prompt folder; does not change runtime destination')
    args = parser.parse_args()
    if args.assets_dir:
        SOURCES = args.assets_dir.resolve()
    export()
