"""Reject custom variables that are written but never read anywhere."""
import re
from collections import defaultdict

NAME = r'hbe_[A-Za-z0-9_]*[A-Za-z0-9](?![\w$])'
WRITE = re.compile(r"(?:set|change)_variable\s*=\s*(?:\{\s*name\s*=\s*("+NAME+r")|("+NAME+r"))")
READ = re.compile(r"(?:\bvar:|has_variable\s*=\s*|has_or_had_variable\s*=\s*)("+NAME+r")")
GET = re.compile(r"GetVariable\(\s*[\'\"](hbe_[a-z0-9_]+)[\'\"]")

# A condition read decides whether a branch runs; remove_variable is only cleanup.
COND = READ


def collect(root):
    writes, reads, cond = defaultdict(set), defaultdict(set), defaultdict(set)
    for path in root.rglob('*'):
        if path.suffix not in ('.txt', '.yml', '.gui'):
            continue
        text = path.read_text(encoding='utf-8-sig', errors='replace')
        if path.suffix == '.txt':
            for m in WRITE.finditer(text):
                writes[m.group(1) or m.group(2)].add(path.name)
        for m in READ.finditer(text):
            reads[m.group(1)].add(path.name)
        for m in GET.finditer(text):
            reads[m.group(1)].add(path.name)
        for m in COND.finditer(text):
            cond[m.group(1)].add(path.name)
    return writes, reads, cond


def orphans_in(writes, reads):
    return sorted(n for n in writes if n not in reads)


def unwritten_in(writes, cond):
    return sorted(n for n in cond if n not in writes)


def validate(m, root, game, manifest, check):
    writes, reads, cond = collect(m)
    orphan = orphans_in(writes, reads)
    for name in orphan[:10]:
        print('  variable-hygiene: ' + name + ' written by ' + sorted(writes[name])[0])
    check('no custom variable is written without any read', not orphan)
    unwritten = unwritten_in(writes, cond)
    for name in unwritten[:10]:
        print('  variable-hygiene: ' + name + ' read by ' + sorted(cond[name])[0])
    check('no custom variable is read by a condition that nothing sets', not unwritten)
