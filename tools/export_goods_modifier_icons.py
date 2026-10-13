"""Export existing approved goods artwork as native modifier icon aliases."""
import hashlib
import json
import re
from pathlib import Path
from PIL import Image

GOODS = ('hbe_shu_embroidery', 'hbe_well_salt', 'hbe_shu_paper', 'hbe_border_tea')

def apply(out, root):
    out, root = Path(out), Path(root)
    folder = out/'main_menu/gfx/interface/icons/modifier_types'
    folder.mkdir(parents=True, exist_ok=True)
    definitions = out/'main_menu/common/modifier_type_definitions'
    keys = []
    for name in ('hbe_goods_modifiers.txt', 'hbe_observer_goods_types.txt'):
        keys += re.findall(r'(?m)^([a-z_]+)\s*=\s*\{', (definitions/name).read_text(encoding='utf-8-sig'))
    assert len(set(keys)) == 40
    files = []
    for good in GOODS:
        # Reuse the approved goods sprite, mechanically resize and encode DXT5.
        image = Image.open(out/f'main_menu/gfx/interface/icons/trade_goods/icon_goods_{good}.dds').convert('RGBA')
        image = image.resize((64,64), Image.Resampling.LANCZOS)
        assert image.getchannel('A').getextrema()[1] > 0
        aliases = [key for key in keys if good in key] + [good+'_positive', good+'_negative']
        for alias in aliases:
            path = folder/(alias+'.dds')
            image.save(path, format='DDS', pixel_format='DXT5')
            with Image.open(path) as check:
                assert check.size == (64,64) and check.getchannel('A').getextrema()[1] > 0
            files.append(path.relative_to(out).as_posix())
    assert len(files) == 48
    path = out/'build_manifest.json'
    manifest = json.loads(path.read_text(encoding='utf-8-sig'))
    manifest['files'].update({p:hashlib.sha256((out/p).read_bytes()).hexdigest() for p in files})
    manifest['goods_modifier_icons'] = {'registered_modifier_types':40, 'files':48, 'size':[64,64],
                                        'source':'Existing approved specialty goods sprites', 'version':'0.3.0'}
    path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Exported 48 compact DDS icons covering all 40 specialty goods modifier types.')

if __name__ == '__main__':
    import sys
    root = Path(sys.argv[1])
    apply(root/'mod/holy_bashu_empire', root)
