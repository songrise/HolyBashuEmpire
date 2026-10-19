"""Retire the unsafe global advance GUI override and omit generic tooltip filler."""
from build_support import write_preserving_format as put, snapshot_files
from pathlib import Path
import hashlib,json,re

GUI = 'main_menu/gui/shared/advances_tooltips.gui'
KEYS = ('hbe_tech_chengdu_plain_4', 'hbe_transmission_embroidery',
        'hbe_transmission_well_salt', 'hbe_transmission_paper', 'hbe_transmission_border_tea')
FILLER = '本课题的永久加成立即生效，并推进后续地区课题与验收。'
PATTERN = r'\[GetAdvanceIcon\(([^()]+)\)\]'

def restore_native_gui(out, game):
    """Remove only our retired override; use the engine's native icon resolver."""
    path = Path(out) / GUI
    if not path.exists():
        return
    native = (Path(game) / GUI).read_text(encoding='utf-8-sig')
    current = path.read_text(encoding='utf-8-sig')
    recovered = re.sub(
        r"\[Select_CString\(EqualTo_string\([^\n\"]+GetAdvanceIcon\(([^()]+)\)\)+\]",
        lambda match: '[GetAdvanceIcon(' + match[1] + ')]', current)
    if recovered != native:
        raise ValueError('Advance GUI contains changes outside the retired HBE icon override: ' + str(path))
    path.unlink()



def apply(out, root, game):
    out, root, game = map(Path, (out, root, game))
    native = (game / GUI).read_text(encoding='utf-8-sig')
    assert len(re.findall(PATTERN, native)) == 3
    restore_native_gui(out, game)
    languages = {}; empty = set()
    for language in ('simp_chinese', 'english'):
        p = out / f'main_menu/localization/{language}/hbe_l_{language}.yml'
        text = p.read_text(encoding='utf-8-sig'); changed=[]
        def clean(match):
            key, value = match[1], json.loads(match[2])
            if not key.startswith(('hbe_tech_', 'hbe_civic_')):
                return match[0]
            if not value and key.endswith('_effects'): empty.add(key)
            if FILLER not in value: return match[0]
            value = value.replace(FILLER, '').strip('\n ')
            changed.append(key)
            if not value: empty.add(key)
            return ' ' + key + ': ' + json.dumps(value, ensure_ascii=False)
        text = re.sub(r'^[ \t]+(\w+):[ \t]*("(?:[^"\\]|\\.)*")[ \t]*$', clean, text, flags=re.M)
        put(p,text); languages[language]=changed
    catalogue = root / 'data/technology_rewards_v021.json'
    if catalogue.exists():
        data=json.loads(catalogue.read_text(encoding='utf-8'))
        for row in data.get('advances', []):
            row['link']=row['link'].replace(FILLER, '').strip('\n ')
        put(catalogue,json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    removed=[]
    for p in (out / 'in_game/common/advances').glob('hbe*.txt'):
        text=p.read_text(encoding='utf-8-sig')
        def omit(match):
            if match[1] not in empty: return match[0]
            removed.append(match[1]); return ''
        text=re.sub(r'\bpure_tooltip_entry[ \t]*=[ \t]*(\w+)',omit,text,flags=re.M)
        text=re.sub(r'(?m)^[ \t]+$', '', text)
        if text!=p.read_text(encoding='utf-8-sig'):put(p,text)
    report=dict(gui_file=GUI,explicit_picture_keys=list(KEYS),native_gui_sha256=hashlib.sha256((game/GUI).read_bytes()).hexdigest(),
                patched_bindings=0,global_gui_override=False,icon_resolver='native GetAdvanceIcon',
                retired_override='Localized-name conditional texture bindings caused runtime FetchData failures.',
                localized_name_match_uses_native_functions=False,unchanged_vanilla_fallback=True,
                tooltip_filler_removed=languages,empty_tooltip_entries_removed=sorted(empty),gameplay_changed=False)
    mp=out/'build_manifest.json';m=json.loads(mp.read_text(encoding='utf-8-sig'));m['advance_display_v032']=report
    m['files']=snapshot_files(out)
    put(mp,json.dumps(m,ensure_ascii=False,indent=2)+'\n')
    return report

def validate(out, game, manifest, check):
    if 'advance_display_v032' not in manifest:return
    out,game=map(Path,(out,game));native=(game/GUI).read_text(encoding='utf-8-sig')
    check('advance icons use the unmodified native shared GUI',not (out/GUI).exists())
    check('native shared GUI retains all three original icon bindings',len(re.findall(PATTERN,native))==3)
    check('advance display metadata does not enable global conditional texture bindings',manifest['advance_display_v032']['patched_bindings']==0 and not manifest['advance_display_v032']['global_gui_override'])
    for key in KEYS:
        check(key+' explicit picture exists',(out/f'main_menu/gfx/interface/advance/{key}.dds').is_file())
        for lang in ('simp_chinese','english'):
            text='\n'.join(p.read_text(encoding='utf-8-sig') for p in (out/f'main_menu/localization/{lang}').glob('hbe*.yml'))
            names=re.findall(r'^\s+'+re.escape(key)+r':\s*("(?:[^"\\]|\\.)*")',text,re.M)
            check(key+' unique localized advance name '+lang,len(names)==1)
    for lang in ('simp_chinese','english'):
        text=(out/f'main_menu/localization/{lang}/hbe_l_{lang}.yml').read_text(encoding='utf-8-sig')
        check(lang+' no generic permanent-reward filler',FILLER not in text)
    advances='\n'.join(p.read_text(encoding='utf-8-sig') for p in (out/'in_game/common/advances').glob('hbe*.txt'))
    check('empty generic tooltip entries omitted from advances',all(not re.search(r'pure_tooltip_entry\s*=\s*'+re.escape(key)+r'\b',advances) for key in manifest['advance_display_v032']['empty_tooltip_entries_removed']))
