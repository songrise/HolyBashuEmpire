"""Final art provenance, semantic reuse guide and focused asset checks."""
import hashlib
import json
import sys
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / ('assets/event_expansion' if (ROOT / 'assets/event_expansion').is_dir() else 'assets/event_illustrations')
MOD = ROOT / 'mod/holy_bashu_empire'

spec = json.loads((SRC / 'final-scenes.prompt.json').read_text(encoding='utf-8'))
spec['status'] = 'complete: 11 new scenes plus 2 user-selected reference paintings retained'
spec['scenes'][6]['scene'] = 'Sichuan embroidery: a working embroiderer and a female master teaching an apprentice at a stretched wooden embroidery frame.'
spec['scenes'][6]['custom_prompt_file'] = 'craft-redraw.prompt.json'
(SRC / 'final-scenes.prompt.json').write_text(json.dumps(spec, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

catalog = json.loads((ROOT / 'data/event_art_expansion.json').read_text(encoding='utf-8'))
defaults = dict(chengdu_plain='bamboo', southern_salt_wine='fossils', eastern_river='river', northern_shudao='observatory', central_hills='terraces', western_tea_horse='veterinary', southwestern_valleys='bridge')
catalog['regional_long_chains'] = defaults
catalog['shared_migration_chain'] = ['migration_journey', 'settlement', 'council']
catalog['reuse_policy'] = 'Select by actual event subject, not merely circle or home tag. Existing salt, roads, academy and ledger paintings remain available where more semantically appropriate.'

# This guide records art selection for authored story seeds, not a claim that
# their eventual native event definitions are already installed in the game.
sys.path.insert(0, str(ROOT / 'data'))
from independent_stories import SOLO
from story_blueprints import LONG

def choose(row):
    title, theme = row['title'], row['theme']
    if any(w in title for w in ('绣', '织', '染', '锦')):
        return 'craft'
    if any(w in title for w in ('纸', '书', '字', '诗', '拓片', '族谱')):
        return 'existing:academy'
    if any(w in title for w in ('桥', '绳', '索', '纤路')):
        return 'bridge'
    if any(w in title for w in ('马', '牧', '草场')):
        return 'veterinary'
    if any(w in title for w in ('药', '医', '病')):
        return 'medicine'
    if any(w in title for w in ('盐', '井', '灶', '酒', '窖')):
        return 'existing:salt'
    if any(w in title for w in ('坟', '葬', '棺', '兽患')):
        return 'existing:crisis'
    return dict(land='settlement', labor='settlement', agriculture='terraces', food='existing:grain', water='river', navigation='river', justice='council', education='existing:academy', literature='existing:academy', military='existing:civic_training', commerce='existing:civic_market', tax='existing:ledger', culture='festival', festival='festival', faith='festival', ecology='terraces', craft='existing:academy', medicine='medicine', caravan='veterinary').get(theme, 'council')

catalog['authored_event_seeds'] = [dict(region=region, title=row['title'], scene=choose(row)) for region, rows in SOLO.items() for row in rows]
catalog['long_chain_stages'] = [dict(region=region, chapter=n+1, title=step[0], scene=defaults[region]) for region, chain in LONG.items() for n, step in enumerate(chain['steps'])]
# Use different parts of the art set where a chapter leaves its initial setting.
for row in catalog['long_chain_stages']:
    if row['region'] == 'chengdu_plain' and row['chapter'] in (2, 5): row['scene'] = 'medicine'
    if row['region'] == 'chengdu_plain' and row['chapter'] in (4, 6, 7, 8): row['scene'] = 'council'
    if row['region'] == 'southern_salt_wine' and row['chapter'] == 3: row['scene'] = 'medicine'
    if row['region'] == 'southern_salt_wine' and row['chapter'] in (6, 7, 8): row['scene'] = 'council'
    if row['region'] == 'western_tea_horse' and row['chapter'] in (7, 8): row['scene'] = 'council'
    if row['region'] == 'southwestern_valleys' and row['chapter'] in (2, 5, 7, 8): row['scene'] = 'council'
available = {a['key'] for a in catalog['assets']}
checks = []
def check(name, ok):
    checks.append(dict(name=name, passed=bool(ok)))
    if not ok: raise RuntimeError(name)

from pdxscript import blocks
tables = {}
for relative in ('in_game/gfx/images/hbe_story_backgrounds.txt', 'in_game/gfx/scenes/hbe_story_scenes.txt', 'loading_screen/gfx/illustrations/database/hbe_story_illustrations.txt'):
    text = (MOD / relative).read_text(encoding='utf-8-sig')
    blocks(text)
    tables[relative] = text
    check(relative + ': balanced native definitions', True)
images, scenes, db = tables.values()
for a in catalog['assets']:
    p = MOD / a['texture']
    check(a['key'] + ': texture exists and hash matches', hashlib.sha256(p.read_bytes()).hexdigest() == a['sha256'])
    with Image.open(p) as im:
        im.load()
        check(a['key'] + ': decoded dimensions', list(im.size) == a['dimensions'])
    check(a['key'] + ': compressed DDS', p.read_bytes()[84:88] == b'DXT5')
    check(a['key'] + ': scene/texture registration', a['scene'] + ' = {' in scenes and a['texture'].removeprefix('main_menu/') in images and a['illustration_tag'] in db)
    check(a['key'] + ': source preserved', (ROOT / a['source']).is_file())
for row in catalog['authored_event_seeds'] + catalog['long_chain_stages']:
    check(row['title'] + ': selected art available', row['scene'] in available or (row['scene'].startswith('existing:') and (MOD / ('main_menu/gfx/interface/hbe/events/' + row['scene'].split(':')[1] + '.dds')).is_file()))
catalog['review'] = dict(status='13 source paintings visually inspected; panoramic crop reviewed', engine_runtime_test=False, note='Asset-only focused checks; no new long campaign run.')
(ROOT / 'data/event_art_expansion.json').write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(ROOT / 'docs/testing/event-art-expansion-checks.json').write_text(json.dumps(dict(checks=checks, passed=len(checks), failed=0), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'{len(catalog["assets"])} scenes, {len(catalog["authored_event_seeds"])} independent seeds, {len(catalog["long_chain_stages"])} long-chain chapters, {len(checks)} focused checks passed.')
