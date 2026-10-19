"""Check the native shared banner/portrait texture contract for all HBE units."""
import hashlib
import re
from PIL import Image
from pdxscript import blocks
from apply_unit_detail_art_v031 import GUI_OVERRIDES, thumbnail_path

def validate_unit_detail_art(mod,root,game,manifest,check):
    report=manifest['unit_detail_art_v031']
    definitions=(mod/'in_game/common/unit_types/hbe_civic_units.txt').read_text(encoding='utf-8-sig')
    expected={b[0] for b in blocks(definitions,0)}
    keys=[a['unit'] for a in report['assets']]
    registry=(mod/'in_game/gfx/unit_illustrations/hbe_civic_illustrations.txt').read_text(encoding='utf-8-sig')
    check('all unit definitions have native continuous artwork',len(keys)==len(expected) and set(keys)==expected)
    for row in report['assets']:
        key=row['unit']; relative=row['texture'].removeprefix('main_menu/');path=mod/'main_menu'/relative
        check('unit registry resolves canonical art '+key,relative in registry and 'is_unit_type = '+key in registry)
        check('canonical art digest '+key,hashlib.sha256(path.read_bytes()).hexdigest()==row['sha256'])
        with Image.open(path) as im:
            check('opaque native 1080x440 texture '+key,im.size==(1080,440) and im.getchannel('A').getextrema()==(255,255))
            check('three distinct scene thirds '+key,len({im.crop((x,0,x+360,440)).tobytes() for x in (0,360,720)})==3)
        with Image.open(mod/'main_menu/gfx/interface/illustrations/units/masks'/f'{path.stem}.dds') as mask:
            check('native opaque no-recolor mask '+key,mask.size==(1080,440) and mask.getextrema()==((0,0),(0,0),(0,0),(255,255)))
    check('native rendering without scripted overlays',report['native_rendering'] and report['gui_overrides']==[])
    for relative in (*GUI_OVERRIDES,'in_game/gui/army_builder.gui'):
        check('native GUI remains unmodified '+relative,not (mod/relative).exists() and (game/relative).is_file())
    native=(game/'in_game/gui/army_builder.gui').read_text(encoding='utf-8-sig')
    check('installed native builder uses three-column portrait cropping',bool(re.search(r'frame_grid\s*=\s*\{\s*3\s+1\s*\}',native)))
