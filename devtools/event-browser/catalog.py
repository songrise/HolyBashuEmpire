"""Read-only EU5 event catalogue. No game runtime or third-party packages required."""
from __future__ import annotations
import json
import re
from datetime import datetime
from pathlib import Path

REGIONS = {
    'chengdu_plain': '成都平原', 'southern_salt_wine': '川南盐酒',
    'eastern_river': '川东江运', 'northern_shudao': '川北蜀道',
    'central_hills': '川中丘陵', 'western_tea_horse': '川西茶马',
    'southwestern_valleys': '西南山谷',
}
LEX = re.compile(r'\s+|#[^\n]*|"(?:\\.|[^"\\])*"|>=|<=|!=|\?=|==|[{}=<>]|[^\s{}=<>!?#]+')

def parse(text):
    """Preserve ordered, repeated keys, comparators, bare list members and source spans."""
    ts = [(m.group(), m.start(), m.end()) for m in LEX.finditer(text)
          if not m.group().isspace() and not m.group().startswith('#')]
    pos = 0
    def group(nested=False):
        nonlocal pos
        out = []
        while pos < len(ts):
            key, start, end = ts[pos]
            if key == '}':
                if not nested:
                    raise ValueError(f'Unexpected closing brace at {start}')
                pos += 1
                return out, end
            if key == '{':
                raise ValueError(f'Unexpected opening brace at {start}')
            pos += 1
            op, value = '', ''
            if pos < len(ts) and ts[pos][0] in ('=', '?=', '>=', '<=', '>', '<', '!=', '=='):
                op = ts[pos][0]
                pos += 1
                if pos >= len(ts):
                    raise ValueError(f'Missing value for {key}')
                if ts[pos][0] == '{':
                    pos += 1
                    value, end = group(True)
                else:
                    value, _, end = ts[pos]
                    pos += 1
                    if pos < len(ts) and ts[pos][0] == '{':
                        # Typed literal, e.g. color = rgb { 0.1 0.2 0.3 }.
                        prefix = value
                        pos += 1
                        members, end = group(True)
                        value = [{'key': prefix, 'op': '', 'value': members, 'start': start, 'end': end}]
            out.append({'key': key, 'op': op, 'value': value, 'start': start, 'end': end})
        if nested:
            raise ValueError('Unclosed block')
        return out, len(text)
    return group()[0]

def field(nodes, key, default=''):
    return next((x['value'] for x in nodes if x['key'] == key), default)

def scalar(value):
    if isinstance(value, list):
        # The browser has no live country state: show the native fallback text.
        first_valid = field(value, 'first_valid', None)
        if first_valid is not None:
            choices = [n['value'] for n in first_valid if n['key'] == 'triggered_desc']
            fallback = next((n for n in choices if not field(n, 'trigger', None)), choices[-1] if choices else [])
            return scalar(field(fallback, 'desc', ''))
        return scalar(field(value, 'text', field(value, 'desc', field(value, 'name', ''))))
    return str(value).strip('"')

def public(node):
    return {'key': node['key'], 'op': node['op'], 'value':
            [public(x) for x in node['value']] if isinstance(node['value'], list) else node['value']}

def pretty(nodes, depth=0):
    lines = []
    for n in nodes:
        head = '    ' * depth + n['key'] + (' ' + n['op'] + ' ' if n['op'] else '')
        if isinstance(n['value'], list):
            lines += [head + '{', pretty(n['value'], depth + 1), '    ' * depth + '}']
        else:
            lines.append(head + n['value'])
    return '\n'.join(lines)

def localization(mod):
    result, warnings = {}, []
    paths = sorted(mod.glob('**/localization/simp_chinese/*.yml'))
    for path in paths:
        for line_no, line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
            m = re.match(r'\s*([^:\s]+):\s*(?:\d+\s*)?("(?:\\.|[^"\\])*\")', line)
            if m:
                try:
                    value = json.loads(m[2])
                except json.JSONDecodeError:
                    value = m[2][1:-1].replace('\\n', '\n').replace('\\"', '"')
                if m[1] in result and result[m[1]] != value:
                    warnings.append(f'重复本地化：{m[1]} ({path.name}:{line_no})')
                result[m[1]] = value
    return result, warnings

def build_catalog(mod):
    mod = Path(mod).resolve()
    loc, warnings = localization(mod)
    events, definitions, documents = [], {}, []
    event_paths = sorted((mod / 'in_game/events').glob('*.txt'))
    if not event_paths:
        raise ValueError(f'No event files in {mod / "in_game/events"}')
    source_paths = sorted(set(event_paths + list((mod / 'in_game/common').rglob('*.txt'))
                             + list((mod / 'main_menu/common/static_modifiers').glob('*.txt'))))
    for path in source_paths:
        text = path.read_text(encoding='utf-8-sig')
        try:
            roots = parse(text)
        except ValueError as exc:
            raise ValueError(f'{path}: {exc}') from exc
        relative = path.relative_to(mod).as_posix()
        documents.append((relative, text, roots))
        kind = next((x for x in ('scripted_effects', 'scripted_triggers', 'script_values', 'static_modifiers')
                     if x in path.parts), None)
        if kind:
            for root in roots:
                if isinstance(root['value'], list):
                    definitions[root['key']] = {
                        'kind': kind, 'name': loc.get(root['key'], loc.get('STATIC_MODIFIER_NAME_' + root['key'], root['key'])),
                        'description': loc.get('STATIC_MODIFIER_DESC_' + root['key'], ''),
                        'nodes': [public(n) for n in root['value']], 'script': pretty(root['value']),
                        'source': relative, 'line': text.count('\n', 0, root['start']) + 1,
                    }
        if path in event_paths:
            for root in roots:
                if not isinstance(root['value'], list) or not re.fullmatch(r'[\w]+\.\d+', root['key']):
                    continue
                body = root['value']
                event_id = root['key']
                hidden = field(body, 'hidden') == 'yes'
                title_key = scalar(field(body, 'title'))
                desc_key = scalar(field(body, 'desc'))
                for key in [title_key, desc_key]:
                    if key and key not in loc:
                        warnings.append(f'缺失本地化：{event_id} → {key}')
                options = []
                for node in body:
                    if node['key'] != 'option' or not isinstance(node['value'], list):
                        continue
                    children = node['value']
                    name_key = scalar(field(children, 'name'))
                    if name_key and name_key not in loc:
                        warnings.append(f'缺失选项本地化：{event_id} → {name_key}')
                    effects = [x for x in children if x['key'] not in
                               ('name', 'trigger', 'ai_chance', 'highlight', 'default_option', 'exclusive')]
                    options.append({
                        'key': name_key, 'name': loc.get(name_key, name_key or '未命名选项'),
                        'trigger': pretty(field(children, 'trigger', [])),
                        'conditions': [public(n) for n in field(children, 'trigger', [])],
                        'ai': pretty(field(children, 'ai_chance', [])),
                        'aiBase': scalar(field(field(children, 'ai_chance', []), 'base')),
                        'effects': [public(n) for n in effects], 'script': pretty(children),
                    })
                raw = text[root['start']:root['end']]
                regions = [key for key in REGIONS if key in raw]
                tags = sorted(set(re.findall(r'\b(?:has_or_had_tag|tag)\s*=\s*(B[A-Z]{2})\b', raw)))
                category = {'hbe': '帝国与开局', 'hbe_banquet': '大开席',
                            'hbe_civic': '政治与社会', 'hbe_opening_family': '开局维护'}.get(event_id.split('.')[0], '其他')
                if event_id.startswith('hbe_story_'):
                    category = '地区结局' if int(event_id.rsplit('.',1)[1]) >= 200 else '地区长线' if int(event_id.rsplit('.',1)[1]) < 100 else '地区独立事件'
                elif event_id.startswith('hbe_short_'):
                    category = '共享独立事件' if int(event_id.rsplit('.',1)[1]) >= 200 else '共享短链' if event_id.startswith('hbe_short_shared') else '地区短链'
                elif event_id.startswith('hbe_migration.'):
                    category = '湖广填四川'
                events.append({
                    'id': event_id, 'namespace': event_id.split('.')[0], 'category': category,
                    'title': loc.get(title_key, title_key or ('开局协议与子女能力修复' if hidden else event_id)),
                    'description': loc.get(desc_key, desc_key), 'titleKey': title_key, 'descriptionKey': desc_key,
                    'hidden': hidden, 'type': scalar(field(body, 'type')),
                    'regions': regions, 'countries': [{'tag': t, 'name': loc.get(t, t)} for t in tags],
                    'source': relative, 'line': text.count('\n', 0, root['start']) + 1,
                    'trigger': pretty(field(body, 'trigger', [])),
                    'conditions': [public(n) for n in field(body, 'trigger', [])],
                    'immediate': [public(n) for n in field(body, 'immediate', [])],
                    'after': [public(n) for n in field(body, 'after', [])],
                    'options': options, 'script': pretty([root]), 'raw': raw,
                    'incoming': [], 'outgoing': [],
                })
    by_id = {e['id']: e for e in events}
    if len(by_id) != len(events):
        raise ValueError('Duplicate event identifiers')
    # Traverse actual script tokens rather than prose or localization-key substrings.
    def refs(nodes, context, parent_event, source, text, ancestors):
        for node in nodes:
            if isinstance(node['value'], list):
                refs(node['value'], context, parent_event, source, text, ancestors + [node])
            elif node['value'] in by_id or (not node['op'] and node['key'] in by_id):
                target = node['value'] if node['value'] in by_id else node['key']
                if node['key'] in ('title', 'desc', 'name'):
                    continue
                conditions = []
                for a in ancestors:
                    if a['key'] in ('if', 'else_if'):
                        conditions.extend(field(a['value'], 'limit', []))
                entry = {'source': source, 'line': text.count('\n', 0, node['start']) + 1,
                         'context': context, 'event': parent_event,
                         'route': ' → '.join(a['key'] for a in ancestors),
                         'conditions': pretty(conditions),
                         'script': pretty([ancestors[-1]]) if ancestors else pretty([node])}
                if entry not in by_id[target]['incoming']:
                    by_id[target]['incoming'].append(entry)
                if parent_event and target not in by_id[parent_event]['outgoing']:
                    by_id[parent_event]['outgoing'].append(target)
    for source, text, roots in documents:
        for root in roots:
            if isinstance(root['value'], list):
                refs(root['value'], root['key'], root['key'] if root['key'] in by_id else None,
                     source, text, [root])
    for event in events:
        related = '\n'.join(x['conditions'] for x in event['incoming'])
        for key in REGIONS:
            if key in related and key not in event['regions']:
                event['regions'].append(key)
        tags = re.findall(r'\b(?:has_or_had_tag|tag)\s*=\s*(B[A-Z]{2})\b', related)
        for tag in sorted(set(tags)):
            if not any(c['tag'] == tag for c in event['countries']):
                event['countries'].append({'tag': tag, 'name': loc.get(tag, tag)})
    for event in events:
        match=re.search(r'hbe_story_art_(\w+)',event['raw'])
        if match:event['illustration']='/art/'+match[1]+'.png'
        ending=re.search(r'hbe_ending_art_(\w+)',event['raw'])
        if ending:event['illustration']='/ending-art/'+ending[1]+'.png'
        if event['namespace'].startswith('hbe_story_') and 1 <= int(event['id'].rsplit('.',1)[1]) < 8:
            target=event['namespace']+'.'+str(int(event['id'].rsplit('.',1)[1])+1)
            if target in by_id and target not in event['outgoing']:event['outgoing'].append(target)
        elif event['namespace']=='hbe_migration' and int(event['id'].rsplit('.',1)[1]) < 10:
            target='hbe_migration.'+str(int(event['id'].rsplit('.',1)[1])+1)
            if target in by_id:event['outgoing'].append(target)
        elif event['namespace'].startswith('hbe_short_') and int(event['id'].rsplit('.',1)[1]) < 200 and int(event['id'].rsplit('.',1)[1])%10 in (1,2):
            target=event['namespace']+'.'+str(int(event['id'].rsplit('.',1)[1])+1)
            if target in by_id:event['outgoing'].append(target)
    manifest_path = mod / 'build_manifest.json'
    if manifest_path.exists():
        country_regions = {c['tag']: c.get('region') for c in
                           json.loads(manifest_path.read_text(encoding='utf-8-sig')).get('countries', [])}
        for event in events:
            for country in event['countries']:
                region = country_regions.get(country['tag'])
                if region in REGIONS and region not in event['regions']:
                    event['regions'].append(region)
    events.sort(key=lambda e: (e['namespace'], int(e['id'].rsplit('.', 1)[1])))
    return {'events': events, 'definitions': definitions, 'localization': loc, 'regions': REGIONS,
            'warnings': warnings, 'modPath': str(mod), 'generatedAt': datetime.now().isoformat(timespec='seconds'),
            'stats': {'events': len(events), 'visible': sum(not e['hidden'] for e in events),
                      'hidden': sum(e['hidden'] for e in events),
                      'options': sum(len(e['options']) for e in events), 'files': len(event_paths)}}
