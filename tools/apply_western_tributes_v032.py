"""Seed four western tributaries in 1337 setup, without runtime transfer events."""
from build_support import snapshot_files
from pathlib import Path
import hashlib
import json
import re
from pdxscript import blocks, apply_edits

RELATIVE = 'main_menu/setup/1337/12_diplomacy.txt'
ASSIGNMENTS = {'GYE': 'BAB', 'HOR': 'BAB', 'NYA': 'BBW', 'CKL': 'BBU'}


def dependencies(text):
    result = []
    for name, start, begin, close, end in blocks(text, 1):
        if name == 'dependency':
            fields = dict(re.findall(r'\b(first|second|subject_type)\s*=\s*(\w+)', text[begin:close]))
            assert set(fields) == {'first', 'second', 'subject_type'}
            result.append((fields, start, end))
    return result


def patch(text):
    edits = []
    entries = dependencies(text)
    for tag, overlord in ASSIGNMENTS.items():
        matches = [(fields, start, end) for fields, start, end in entries if fields['second'] == tag]
        assert len(matches) == 1, (tag, 'expected exactly one existing overlord')
        fields, start, end = matches[0]
        assert (fields['first'], fields['subject_type']) in [('CHI', 'tusi'), (overlord, 'tributary')], fields
        original = text[start:end]
        updated = re.sub(r'\bfirst\s*=\s*'+fields['first']+r'\b', 'first = '+overlord, original, count=1)
        updated = re.sub(r'\bsubject_type\s*=\s*'+fields['subject_type']+r'\b', 'subject_type = tributary', updated, count=1)
        edits.append((start, end, updated))
    return apply_edits(text, edits)


def apply(out, root=None, game=None):
    out, game = Path(out), Path(game)
    native = game/RELATIVE
    target = out/RELATIVE
    baseline = target.read_text(encoding='utf-8-sig') if target.exists() else native.read_text(encoding='utf-8-sig')
    modified = patch(baseline)
    assert patch(modified) == modified
    # This setup override changes only the four existing dependency entries.
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(modified, encoding='utf8', newline='\n')
    report = {
        'version': '0.3.2', 'source_only': True, 'new_campaign_only': True,
        'setup_file': RELATIVE, 'subject_type': 'tributary',
        'assignments': dict(ASSIGNMENTS), 'countries': 4, 'locations': 17,
        'liang_and_its_subjects_unchanged': True, 'hbe_membership_unchanged': True,
        'native_tributary_rules_unchanged': True, 'runtime_transfer_events': False,
        'native_diplomacy_sha256': hashlib.sha256(native.read_bytes()).hexdigest(),
    }
    mp = out/'build_manifest.json'
    manifest = json.loads(mp.read_text(encoding='utf8'))
    manifest['western_tributes_v032'] = report
    manifest['files'] = snapshot_files(out)
    mp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    return report
