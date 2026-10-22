"""Use plain canonical names for gameplay concepts; preserve historical prose."""
import json
import re

from build_support import write_preserving_format

CALL = re.compile(r'''Concept\(\s*(['"])(.*?)\1\s*,\s*(['"])(.*?)\3\s*\)''')
ENTRY = re.compile(r'^(\s+)(\S+?):(?:\d+)?\s*(".*")\s*$')
NESTED = re.compile(r'''\[Concept\(\s*(['"])(.*?)\1\s*,\s*(['"])(.*?)\3\s*\)\|\w+\]''')


def names(values):
    result={}
    for key,value in values.items():
        if not key.startswith('game_concept_hbe_term_') or key.endswith('_desc'):continue
        # A title must not contain another hyperlink. Its rendered display text is
        # the canonical name; formatting syntax is not a different player term.
        result[key.removeprefix('game_concept_')]=NESTED.sub(lambda m:m[4],value)
    return result


def normalize(value, canonical):
    return CALL.sub(lambda m:('Concept('+m[1]+m[2]+m[1]+', '+m[3]+canonical[m[2]]+m[3]+')')
                    if m[2] in canonical else m[0],value)


def read_entries(path):
    for number,line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(),1):
        match=ENTRY.match(line)
        if match:yield number,match[2],json.loads(match[3])


def dedicated_labels_override_fallbacks(paths, core):
    """Dedicated feature files own their labels; core may contain old fallbacks."""
    owned={key for path in paths if path!=core for _,key,_ in read_entries(path)}
    if not core.exists():return 0
    rows=[];removed=0
    for line in core.read_text(encoding='utf-8-sig').splitlines():
        match=ENTRY.match(line)
        if match and match[2] in owned:
            removed+=1
        else:
            rows.append(line)
    write_preserving_format(core,'\n'.join(rows)+'\n')
    return removed


def apply(out):
    languages=out/'main_menu/localization'
    fallback=names({k:v for p in sorted((languages/'simp_chinese').glob('*.yml')) for _,k,v in read_entries(p)})
    report={}
    for directory in sorted(languages.iterdir()):
        if not directory.is_dir():continue
        paths=sorted(directory.glob('hbe*.yml'))
        removed=dedicated_labels_override_fallbacks(paths,directory/('hbe_l_'+directory.name+'.yml'))
        canonical=fallback|names({k:v for p in paths for _,k,v in read_entries(p)})
        labels=titles=0
        for path in paths:
            rows=[]
            for line in path.read_text(encoding='utf-8-sig').splitlines():
                match=ENTRY.match(line)
                if match:
                    key,value=match[2],json.loads(match[3])
                    title=key.removeprefix('game_concept_')
                    if title in canonical:
                        updated=canonical[title];titles+=updated!=value
                    else:
                        labels+=sum(m[2] in canonical and m[4]!=canonical[m[2]] for m in CALL.finditer(value))
                        updated=normalize(value,canonical)
                    if updated!=value:line=match[1]+key+': '+json.dumps(updated,ensure_ascii=False)
                rows.append(line)
            write_preserving_format(path,'\n'.join(rows)+'\n')
        report[directory.name]={'labels_normalized':labels,'titles_flattened':titles,'duplicate_fallbacks_removed':removed}
    return report


def validate(out,check):
    for directory in sorted((out/'main_menu/localization').iterdir()):
        if not directory.is_dir():continue
        values={k:v for p in sorted(directory.glob('hbe*.yml')) for _,k,v in read_entries(p)}
        canonical=names(values)
        if not canonical:continue
        mismatch=[(key,m[2],m[4]) for key,value in values.items() for m in CALL.finditer(value)
                  if m[2] in canonical and m[4]!=canonical[m[2]]]
        check(directory.name+' gameplay concept labels use canonical names',not mismatch)
        check(directory.name+' gameplay concept titles contain no nested links',all('Concept(' not in values['game_concept_'+key] for key in canonical))
