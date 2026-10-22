"""Reject custom variables that are written but never read anywhere."""
import re
from collections import defaultdict

WRITE = re.compile(r"(?:set|change)_variable\s*=\s*(?:\{\s*name\s*=\s*(hbe_[a-z0-9_]+)|(hbe_[a-z0-9_]+))")
READ = re.compile(r"(?:\bvar:|has_variable\s*=\s*|remove_variable\s*=\s*|has_or_had_variable\s*=\s*)(hbe_[a-z0-9_]+)")
GET = re.compile(r"GetVariable\(\s*[\'\"](hbe_[a-z0-9_]+)[\'\"]")

# A condition read decides whether a branch runs; remove_variable is only cleanup.
COND = re.compile(r"(?:\bvar:|has_variable\s*=\s*)(hbe_[a-z0-9_]*[a-z0-9])(?![\w$])")

# Read by a condition but written nowhere: the branch can never fire. These are the
# remaining known instances (documented in docs/patch_notes_v040.md); a new entry
# means a broken branch, not a whitelist candidate.
UNWRITTEN = ('hbe_declined_project', 'hbe_round_pledged', 'hbe_work_burst_cooldown')


# Writes kept deliberately for save compatibility; they carry no gameplay read.
ALLOWED = ('hbe_water', 'hbe_salt', 'hbe_river', 'hbe_roads', 'hbe_grain', 'hbe_tea', 'hbe_valleys')


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
    return sorted(n for n in writes if n not in reads and n not in ALLOWED)


def unwritten_in(writes, cond):
    return sorted(n for n in cond if n not in writes and n not in UNWRITTEN)


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
