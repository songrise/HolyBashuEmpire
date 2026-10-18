"""Export continuous native unit paintings for both banners and frame-1 portraits."""
from pathlib import Path
import argparse
import hashlib
import json
from PIL import Image, ImageDraw, ImageFont
from apply_local_ui_patch import source_cell, framed_portrait
from build_flags import save_dds
from pdxscript import blocks

GUI_OVERRIDES = ('in_game/gui/unit_type_lateralview.gui', 'in_game/gui/unit_overview.gui')

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def thumbnail_path(key):
    return f'gfx/interface/illustrations/units/{key}.dds'

def apply(out, root, game):
    out, root, game = Path(out), Path(root), Path(game)
    registry = json.loads((root/'assets/social_art_generation.json').read_text(encoding='utf8'))
    atlas_path = root/registry['units']['source']
    atlas = Image.open(atlas_path).convert('RGBA')
    definitions = (out/'in_game/common/unit_types/hbe_civic_units.txt').read_text(encoding='utf-8-sig')
    keys = [b[0] for b in blocks(definitions, 0)]
    assert len(keys) == len(set(keys)) == 9
    preview = Image.new('RGB', (880, 9*250), '#272822')
    draw = ImageDraw.Draw(preview)
    font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 17)
    assets = []
    for index, key in enumerate(keys):
        scene = framed_portrait(source_cell(atlas, index))
        target = out/'main_menu'/thumbnail_path(key)
        save_dds(target, scene)
        mask = out/'main_menu/gfx/interface/illustrations/units/masks'/f'{key}.dds'
        save_dds(mask, Image.new('RGBA', scene.size, (0,0,0,255)))
        png = root/'assets/civic_icons'/f'{key}.png'
        png.parent.mkdir(parents=True, exist_ok=True)
        scene.save(png)
        preview.paste(scene.resize((540,220), Image.Resampling.LANCZOS), (8,index*250+27))
        preview.paste(scene.crop((0,0,360,440)).resize((180,220), Image.Resampling.LANCZOS), (610,index*250+27))
        draw.text((8,index*250+3),key+' / native banner + frame 1',font=font,fill='#e4d9b5')
        assets.append(dict(unit=key, source_cell=index, texture=target.relative_to(out).as_posix(),
                           dimensions=[1080,440], sha256=sha(target), portrait_frame=1))
        # Retire only this unit's previous separate overlay texture.
        obsolete = out/f'main_menu/gfx/interface/hbe/unit_banners/{key}.dds'
        obsolete.unlink(missing_ok=True)
    for relative in GUI_OVERRIDES:
        target = out/relative
        if target.exists():
            text = target.read_text(encoding='utf-8-sig')
            assert 'gfx/interface/hbe/unit_banners/' in text, f'Unexpected GUI override: {target}'
            target.unlink()
    preview_path = root/'assets/unit_detail_alignment_preview.jpg'
    preview.save(preview_path, quality=94)
    report = dict(version='0.3.2',units=len(keys),dimensions=[1080,440],
                  native_rendering=True,gui_overrides=[],
                  routing='native continuous texture; native frame_grid selects portrait',
                  atlas=atlas_path.relative_to(root).as_posix(),atlas_sha256=sha(atlas_path),assets=assets,
                  native_gui_sha256={p:sha(game/p) for p in GUI_OVERRIDES})
    mp = out/'build_manifest.json'
    manifest = json.loads(mp.read_text(encoding='utf8'))
    manifest['unit_detail_art_v031'] = report
    # Keep earlier export metadata consistent with the final canonical texture.
    updates = {r['unit']:r for r in assets}
    def refresh(value):
        if isinstance(value, dict):
            key = value.get('unit') or value.get('key')
            path = value.get('path') or value.get('texture') or value.get('file')
            if key not in updates and isinstance(path,str):
                key = Path(path).stem if '/illustrations/units/' in path and '/masks/' not in path else None
            if key in updates and 'sha256' in value:
                value['sha256'] = updates[key]['sha256']
                if 'grid' in value: value['layout'] = 'continuous native scene'
            for child in value.values(): refresh(child)
        elif isinstance(value,list):
            for child in value: refresh(child)
    refresh(manifest)
    manifest['files'] = {p.relative_to(out).as_posix():sha(p) for p in out.rglob('*')
                         if p.is_file() and p.name != 'build_manifest.json'}
    mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return report

if __name__ == '__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--game',type=Path,required=True)
    a=ap.parse_args()
    print(json.dumps(apply(a.root/'mod/holy_bashu_empire',a.root,a.game),ensure_ascii=False))
