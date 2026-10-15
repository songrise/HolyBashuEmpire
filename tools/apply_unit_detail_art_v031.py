"""Separate full unit scenes from the native recruitment portrait sprite sheet."""
from pathlib import Path
import argparse
import hashlib
import json

from PIL import Image, ImageDraw, ImageFont, ImageOps
from apply_local_ui_patch import source_cell
from build_flags import save_dds
from pdxscript import blocks


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scene_path(key):
    return f'gfx/interface/hbe/unit_banners/{key}.dds'


def thumbnail_path(key):
    return f'gfx/interface/illustrations/units/{key}.dds'


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


def route_scene(getter, keys):
    # Use the already resolved native illustration path; no guessed unit getters
    # or culture/context triggers. Every other unit keeps the vanilla binding.
    expression = getter
    for key in reversed(keys):
        expression = (
            f"Select_CString(EqualTo_string({getter}, '{thumbnail_path(key)}'), "
            f"'{scene_path(key)}', {expression})"
        )
    return expression


def apply(out, root, game):
    out, root, game = Path(out), Path(root), Path(game)
    registry = json.loads((root/'assets/social_art_generation.json').read_text(encoding='utf8'))
    atlas_path = root/registry['units']['source']
    atlas = Image.open(atlas_path).convert('RGBA')
    definitions = (out/'in_game/common/unit_types/hbe_civic_units.txt').read_text(encoding='utf-8-sig')
    keys = [b[0] for b in blocks(definitions, 0)]
    assert len(keys) == 9 and len(set(keys)) == 9
    preview = Image.new('RGB', (1080, 9*300), '#272822')
    draw = ImageDraw.Draw(preview)
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 18)
    assets = []
    for index, key in enumerate(keys):
        thumbnail = out/'main_menu'/thumbnail_path(key)
        before = sha(thumbnail)
        cell = source_cell(atlas, index)
        bounds = opaque_rectangle(cell)
        # One coherent original painting fills the complete 1080x440 banner.
        # Drop only the atlas's transparent gutters; no tiling or portrait crop.
        scene = ImageOps.fit(cell.crop(bounds).convert('RGB'), (1080, 440), Image.Resampling.LANCZOS)
        target = out/'main_menu'/scene_path(key)
        save_dds(target, scene)
        with Image.open(target) as decoded:
            assert decoded.size == (1080, 440)
            assert decoded.getchannel('A').getextrema() == (255, 255)
            assert decoded.crop((0, 0, 360, 440)).tobytes() != decoded.crop((360, 0, 720, 440)).tobytes()
        assert before == sha(thumbnail)
        # Keep the original opaque black native mask for both image contexts.
        mask = out/'main_menu/gfx/interface/illustrations/units/masks'/f'{key}.dds'
        with Image.open(mask) as decoded:
            assert decoded.size == (1080, 440)
            assert decoded.getextrema() == ((0,0), (0,0), (0,0), (255,255))
        preview.paste(scene.resize((648, 264), Image.Resampling.LANCZOS), (5, index*300+30))
        with Image.open(thumbnail) as decoded:
            portrait = decoded.crop((0, 0, 360, 440)).resize((180, 220), Image.Resampling.LANCZOS)
        preview.paste(portrait, (700, index*300+44))
        draw.text((12, index*300+4), key+'   /   full scene + unchanged portrait', font=font, fill='#e4d9b5')
        assets.append(dict(unit=key, source_cell=index, source_bounds=list(bounds),
                           texture=target.relative_to(out).as_posix(), dimensions=[1080,440],
                           sha256=sha(target), thumbnail=thumbnail.relative_to(out).as_posix(),
                           thumbnail_sha256=before))
    # This is the only native wide player-facing consumer. Do not override the
    # recruitment/tooltip/advance GUIs, which deliberately read a portrait frame.
    relative = 'in_game/gui/unit_type_lateralview.gui'
    native = game/relative
    text = native.read_text(encoding='utf-8-sig')
    getter = 'GetSubunitTypeIllustration(UnitTypeLateralView.GetUnitType, UnitTypeLateralView.GetPlayer.GetCulture)'
    old = 'texture = "['+getter+']"'
    new = 'texture = "['+route_scene(getter, keys)+']"'
    assert text.count(old) == 1, 'Vanilla unit detail GUI changed; inspect before patching'
    patched = text.replace(old, new)
    assert patched.replace(new, old) == text
    target = out/relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(patched, encoding='utf-8-sig', newline='\r\n')
    preview_path = root/'assets/unit_detail_alignment_preview.jpg'
    preview.save(preview_path, quality=94)
    report = dict(version='0.3.1', units=len(keys), dimensions=[1080,440],
                  thumbnail_sheets_preserved=True, native_fallback=True,
                  gui_override=relative, native_gui_sha256=sha(native),
                  changed_native_bindings=1, atlas=atlas_path.relative_to(root).as_posix(),
                  atlas_sha256=sha(atlas_path), assets=assets)
    mp = out/'build_manifest.json'
    manifest = json.loads(mp.read_text(encoding='utf8'))
    manifest['unit_detail_art_v031'] = report
    manifest['files'] = {p.relative_to(out).as_posix():sha(p) for p in out.rglob('*')
                         if p.is_file() and p.name != 'build_manifest.json'}
    mp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    return report


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--game', type=Path, required=True, help='Installed EU5 game resource directory')
    a = ap.parse_args()
    report = apply(a.root/'mod/holy_bashu_empire', a.root, a.game)
    print(json.dumps({k:v for k,v in report.items() if k != 'assets'}, ensure_ascii=False))
