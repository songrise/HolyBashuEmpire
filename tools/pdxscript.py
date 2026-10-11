"""Small lossless tokenizer for Clausewitz/Jomini setup patching and validation."""
from dataclasses import dataclass
import re

LEX = re.compile(r'\s+|#[^\n]*|"(?:\\.|[^"\\])*"|[{}=]|[^\s{}=#]+')

@dataclass
class Token:
    value: str
    start: int
    end: int

def tokens(text):
    return [Token(m.group(), m.start(), m.end()) for m in LEX.finditer(text)
            if not m.group().isspace() and not m.group().startswith('#')]

def close_index(ts, start):
    assert ts[start].value == '{'
    depth = 1
    for i in range(start + 1, len(ts)):
        depth += (ts[i].value == '{') - (ts[i].value == '}')
        if not depth:
            return i
    raise ValueError(f'Unclosed brace at {ts[start].start}')

def blocks(text, depth_wanted=None):
    ts = tokens(text)
    depth = 0
    result = []
    for i, t in enumerate(ts):
        if t.value == '{':
            if i >= 2 and ts[i-1].value == '=':
                if depth_wanted is None or depth == depth_wanted:
                    end = close_index(ts, i)
                    result.append((ts[i-2].value, ts[i-2].start, t.end, ts[end].start, ts[end].end))
            depth += 1
        elif t.value == '}':
            depth -= 1
            if depth < 0:
                raise ValueError(f'Unexpected closing brace at {t.start}')
    if depth:
        raise ValueError('Unclosed braces')
    return result

def apply_edits(text, edits):
    last = len(text)
    for start, end, replacement in sorted(edits, reverse=True):
        if end > last:
            raise ValueError('Overlapping edits')
        text = text[:start] + replacement + text[end:]
        last = start
    return text
