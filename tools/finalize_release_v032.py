"""Set public release metadata after all reproducible feature patches."""
from pathlib import Path
import hashlib,json

def apply(out, root=None, game=None):
    out=Path(out);p=out/'.metadata/metadata.json'
    metadata=json.loads(p.read_text(encoding='utf-8-sig'))
    metadata['version']='0.3.2'
    metadata['short_description']='七圈三十六府：506个可见事件、分支故事与湖广填四川；特色产业、府州改革、九种特色兵及蜀、渝、巴蜀帝国成立路线。'
    p.write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    p=out/'build_manifest.json';m=json.loads(p.read_text(encoding='utf8'));m['version']='0.3.2'
    # Retain the 36 existing personal-event trigger labels in independent builds.
    for language in ('simp_chinese','english'):
        target=out/f'main_menu/localization/{language}/hbe_personal_tooltips_l_{language}.yml'
        if not target.exists():
            lines=[f'l_{language}:']
            for index,country in enumerate(m['countries'],200):
                key='hbe_personal_'+country['tag'].lower()+'_not_seen_tt'
                label=(f'本府尚未经历「$hbe_banquet.{index}.title$」' if language=='simp_chinese' else f'This country has not yet experienced “$hbe_banquet.{index}.title$”.')
                lines.append(' '+key+': '+json.dumps(label,ensure_ascii=False))
            target.write_text('\n'.join(lines)+'\n',encoding='utf-8-sig')
    m['release_v032']={'version':'0.3.2','visible_events':506,'capital_recruitment_fallback':True,'special_regiment_strength':500,'burden_per_net_new_special_regiment':2,'loading_art_enabled':False}
    m['files']={p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and p.name!='build_manifest.json'}
    p.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return m['release_v032']
