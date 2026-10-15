"""Regression checks for wide unit banners and preserved recruitment portraits."""
import hashlib
import json
from PIL import Image
from apply_unit_detail_art_v031 import route_scene, scene_path, thumbnail_path


def validate_unit_detail_art(mod, root, game, manifest, check):
    report = manifest['unit_detail_art_v031']
    previous = json.loads((root/'docs/testing/unit-thumbnail-tianfu-local-v031.json').read_text(encoding='utf8'))
    expected = {r['unit']:r['sha256'] for r in previous['unit_frames']}
    keys = [a['unit'] for a in report['assets']]
    check('nine distinct unit banners preserve the original unit roster', len(keys) == 9 and set(keys) == set(expected))
    for row in report['assets']:
        key = row['unit']
        portrait = mod/'main_menu'/thumbnail_path(key)
        check('unchanged recruitment portrait '+key, hashlib.sha256(portrait.read_bytes()).hexdigest() == expected[key] == row['thumbnail_sha256'])
        with Image.open(mod/'main_menu'/scene_path(key)) as banner:
            check('opaque 1080x440 full banner '+key, banner.size == (1080,440) and banner.getchannel('A').getextrema() == (255,255))
            check('full scene is not three repeated portraits '+key, len({banner.crop((x,0,x+360,440)).tobytes() for x in (0,360,720)}) == 3)
    relative = report['gui_override']
    native = (game/relative).read_text(encoding='utf-8-sig')
    modified = (mod/relative).read_text(encoding='utf-8-sig')
    getter = 'GetSubunitTypeIllustration(UnitTypeLateralView.GetUnitType, UnitTypeLateralView.GetPlayer.GetCulture)'
    old = 'texture = "['+getter+']"'
    new = 'texture = "['+route_scene(getter, keys)+']"'
    check('detail GUI changes exactly one native texture binding', native.count(old) == modified.count(new) == 1 and modified.replace(new,old) == native)
    check('all nine detail textures and native fallback are selected explicitly', new.count('Select_CString(') == 9 and new.endswith(getter+')'*9+']"'))
    check('native army builder is not overridden', not (mod/'in_game/gui/army_builder.gui').exists())
