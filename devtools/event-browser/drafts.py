"""Expose authored story seeds for review; never pretend they are engine events."""
import importlib.util
import sys
from pathlib import Path

ART = {'ecology': 'bamboo', 'archaeology': 'fossils', 'navigation': 'river',
       'astronomy': 'observatory', 'agronomy': 'terraces', 'veterinary': 'veterinary',
       'bridge': 'bridge', 'craft': 'craft', 'medicine': 'medicine', 'festival': 'festival',
       'caravan': 'veterinary', 'military': 'bridge', 'education': 'observatory',
       'literature': 'craft', 'commerce': 'river', 'justice': 'council',
       'labor': 'craft', 'land': 'settlement', 'food': 'terraces', 'migration': 'migration_journey'}
LONG_ART = {'chengdu_plain': 'bamboo', 'southern_salt_wine': 'fossils',
            'eastern_river': 'river', 'northern_shudao': 'observatory',
            'central_hills': 'terraces', 'western_tea_horse': 'veterinary',
            'southwestern_valleys': 'bridge'}

def add_drafts(data, root):
    root = Path(root)
    implemented_ids = {e['id'] for e in data['events']}
    if 'hbe_story_chengdu_plain.1' in implemented_ids:
        for event in data['events']:
            event['status'] = 'implemented'
        data['stats'].update(implemented=len(data['events']),drafts=0)
        return data
    path = root / 'data/story_blueprints.py'
    if not path.exists():
        data['stats']['implemented'] = len(data['events'])
        data['stats']['drafts'] = 0
        return data
    def load(name, filename):
        spec = importlib.util.spec_from_file_location(name, root / 'data' / filename)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    long = load('story_blueprints', 'story_blueprints.py')
    previous = sys.modules.get('story_blueprints')
    sys.modules['story_blueprints'] = long
    try:
        solo = load('hbe_viewer_solo', 'independent_stories.py')
    finally:
        if previous is None:
            sys.modules.pop('story_blueprints', None)
        else:
            sys.modules['story_blueprints'] = previous
    installed = len(data['events'])
    for event in data['events']:
        event['status'] = 'implemented'
    def entry(region, index, title, body, choices, tags, source, chain='', year=None, offset=None, art='council'):
        event_id = f'hbe_draft_{region}.{index}'
        event = dict(id=event_id, namespace=f'hbe_draft_{region}', category='新增长线草稿' if chain else '新增独立草稿',
                     title=title, description=body, titleKey='', descriptionKey='', hidden=False, type='draft',
                     status='draft', regions=[region], countries=[{'tag': t, 'name': data['localization'].get(t, t)} for t in tags.split()],
                     source=str(root / 'data' / source), line=1, trigger='', conditions=[], immediate=[], after=[],
                     options=[dict(key=f'{event_id}.{chr(97+i)}', name=name, trigger='', conditions=[], ai='', aiBase='',
                                   effects=[], script='', draft=True) for i, name in enumerate(choices)],
                     script='', raw='', incoming=[], outgoing=[], chain=chain, draftYear=year, draftOffset=offset,
                     illustration=f'/art/{art}.png')
        data['events'].append(event)
        return event
    for region, story in long.LONG.items():
        chapters = []
        for i, (title, body, choices) in enumerate(story['steps']):
            chapters.append(entry(region, i+1, title, body, choices.split('|'), story['tags'], 'story_blueprints.py',
                                  story['name'], story['start_year'], story['offsets'][i], LONG_ART[region]))
        for i, chapter in enumerate(chapters):
            if i + 1 < len(chapters):
                chapter['outgoing'] = [chapters[i+1]['id']]
        chapters[-1]['draftEndings'] = story['endings']
    for region, stories in solo.SOLO.items():
        for i, story in enumerate(stories):
            entry(region, 101+i, story['title'], story['body'], story['choices'], ' '.join(story['tags']),
                  'independent_stories.py', year=story['year'], art=ART.get(story['theme'], 'council'))
    data['stats'].update(implemented=installed, drafts=len(data['events'])-installed,
                         events=len(data['events']), visible=sum(not e['hidden'] for e in data['events']),
                         options=sum(len(e['options']) for e in data['events']))
    return data
