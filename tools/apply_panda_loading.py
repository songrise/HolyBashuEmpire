"""Export approved two-plane loading art using the native near and far meshes."""
from pathlib import Path
import json, re
from PIL import Image
from build_support import sha256_file, snapshot_files, write_preserving_format
from pdxscript import blocks

CONFIG = 'data/panda_loading.json'
SCENE = 'loading_screen_scene_hbe_panda_discovery'
SCENE_FILE = 'loading_screen/gfx/scenes/hbe_panda_discovery.txt'
IMAGE_FILE = 'loading_screen/gfx/images/hbe_panda_discovery.txt'


def export_scene(out, root, config, stem):
    from apply_loading_art_v031 import QUOTES
    scene_name = 'loading_screen_scene_' + stem
    records, image_defs, components = [], [], []
    for layer in ('near', 'far'):
        source = root / config['sources'][layer]
        image = Image.open(source).convert('RGBA')
        assert image.size == (3840, 2160), source
        alpha = image.getchannel('A')
        assert alpha.getextrema() == ((0, 255) if layer == 'near' else (255, 255))
        mesh = 'layer_1_mesh' if layer == 'near' else 'layer_8_mesh'
        rel = f'loading_screen/gfx/loading_screen_assets/{stem}/{layer}_metadata_os3840x2160_d0x0.dds'
        target = out / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        image.save(target, pixel_format='DXT5')
        key = stem + '_' + layer
        image_defs.append(f'{key} = {{ illustration_image = {{ texture_file = "{rel.removeprefix("loading_screen/")}" priority = 1 weight = 1 }} tag = "{key}" }}')
        components.append(f'ecs_illustration_image = {{ list = "{key}" pdxmesh = "{mesh}" name = "illustration_override_anims" }}')
        records.append(dict(layer=layer, source=config['sources'][layer], source_sha256=sha256_file(source), texture=rel, sha256=sha256_file(target), mesh=mesh))
    def put(relative, text):
        p = out / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text.rstrip() + '\n', encoding='utf-8-sig', newline='\r\n')
    put(f'loading_screen/gfx/images/{stem}.txt', '\n'.join(image_defs))
    put(f'loading_screen/gfx/scenes/{stem}.txt', scene_name + ' = {\n' + '\n'.join(components) + '''
    gfx_environment_file = "gfx/illustrations/environment2.txt"
    camera = {
        camera_near_far = { 0.11 100000 }
        camera_fov_y_degrees = 37.5
        camera_position = { 0 0 -125 }
        camera_look_at = { 0 0 1000 }
    }
}
''')
    return dict(enabled=True, mode='native_two_plane_parallax', scene=scene_name,
                  canvas=[3840, 2160], planes_per_scene=2, assets=records,
                  native_animation_binding='illustration_override_anims',
                  flavor_tips_enabled=True, quote_slots=list(range(len(QUOTES))),
                  game_visual_verified=False, legacy_four_paintings_enabled=False)


def apply(out, root, game=None):
    out, root = Path(out), Path(root)
    p = out / 'build_manifest.json'
    manifest = json.loads(p.read_text(encoding='utf-8-sig'))
    for key, filename, stem in [('panda_loading', CONFIG, 'hbe_panda_discovery'),
                                ('saltworks_loading', 'data/saltworks_loading.json', 'hbe_saltworks')]:
        if (root / filename).is_file():
            config = json.loads((root / filename).read_text(encoding='utf-8'))
            manifest[key] = export_scene(out, root, config, stem)
    manifest.setdefault('current_release', {})['loading_art_enabled'] = True
    manifest['files'] = snapshot_files(out)
    write_preserving_format(p, json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    return manifest['panda_loading']


def validate_scene(out, root, game, info, stem, check):
    scene = (out / f'loading_screen/gfx/scenes/{stem}.txt').read_text(encoding='utf-8-sig')
    images = (out / f'loading_screen/gfx/images/{stem}.txt').read_text(encoding='utf-8-sig')
    check(stem+' enabled with two native planes', info.get('enabled') and info.get('planes_per_scene') == 2)
    check(stem+' discovered with native loading prefix', [k for k, *_ in blocks(scene, 0)] == ['loading_screen_scene_' + stem])
    check('panda native animated meshes and camera retained', scene.count('ecs_illustration_image') == 2 and all(x in scene for x in ('layer_1_mesh', 'layer_8_mesh', 'camera_fov_y_degrees = 37.5', 'camera_position = { 0 0 -125 }')) and scene.count('illustration_override_anims') == 2)
    for row in info['assets']:
        with Image.open(out / row['texture']) as im:
            check('panda '+row['layer']+' native canvas and alpha', im.size == (3840, 2160) and im.convert('RGBA').getchannel('A').getextrema() == ((0, 255) if row['layer'] == 'near' else (255, 255)))
        check('panda '+row['layer']+' native BC3', (out / row['texture']).read_bytes()[84:88] == b'DXT5')
        check('panda '+row['layer']+' texture and approved source match', sha256_file(out / row['texture']) == row['sha256'] and sha256_file(root / row['source']) == row['source_sha256'])
        check('panda '+row['layer']+' image link resolves', row['texture'].removeprefix('loading_screen/') in images and (game / 'loading_screen/gfx/models/loading_screen_assets/00' / (row['mesh'].removesuffix('_mesh') + '.asset')).is_file())


def validate(out, root, game, manifest, check):
    from apply_loading_art_v031 import QUOTES
    out, root, game = Path(out), Path(root), Path(game)
    for key, filename, stem in [('panda_loading', CONFIG, 'hbe_panda_discovery'),
                                ('saltworks_loading', 'data/saltworks_loading.json', 'hbe_saltworks')]:
        if (root / filename).is_file():
            validate_scene(out, root, game, manifest[key], stem, check)
            check(stem+' flavor quote catalogue matches', manifest[key]['quote_slots'] == list(range(len(QUOTES))))
    for lang in ('simp_chinese', 'english'):
        old = out / f'loading_screen/localization/{lang}/hbe_load_tips_l_{lang}.yml'
        new = out / f'loading_screen/localization/{lang}/replace/hbe_load_tips_l_{lang}.yml'
        text = new.read_text(encoding='utf-8-sig')
        check('Bashu '+lang+' flavor tips override native quote slots', not old.exists() and set(re.findall(r'LOADING_TIP_(\d+):', text)) == {str(n) for n in range(len(QUOTES))} and text.count('#tooltip_subheading') == len(QUOTES))
    check('panda loading keeps native GUI and old four paintings disabled', not (out / 'loading_screen/gui/loading_screen.gui').exists() and not (out / 'loading_screen/gfx/scenes/hbe_loading_scenes.txt').exists())
