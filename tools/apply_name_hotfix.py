"""Idempotent localization-only name correction; retain stable tags/dynasty IDs."""
import csv
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COUNTRY_BASE_NAME_OVERRIDES = {'BCB': '建昌'}
SURNAMES = [
    ('李','Li'),('陈','Chen'),('王','Wang'),('赵','Zhao'),('苏','Su'),
    ('杨','Yang'),('罗','Luo'),('黄','Huang'),('何','He'),('张','Zhang'),
    ('刘','Liu'),('周','Zhou'),('冯','Feng'),('杜','Du'),('彭','Peng'),
    ('吴','Wu'),('范','Fan'),('任','Ren'),('邓','Deng'),('蒲','Pu'),
    ('唐','Tang'),('钟','Zhong'),('曹','Cao'),('魏','Wei'),('袁','Yuan'),
    ('许','Xu'),('高','Gao'),('马','Ma'),('董','Dong'),('郭','Guo'),
    ('徐','Xu'),('秦','Qin'),('梁','Liang'),('沈','Shen'),('安','An'),('龙','Long')]

def apply(out, root=None):
    out = Path(out)
    root = Path(root) if root else out.parents[1]
    manifest_path = out/'build_manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    countries = manifest['countries']
    assert len(countries) == len(SURNAMES) == 36
    mapping = {}
    for country, (cn, en) in zip(countries, SURNAMES):
        base = COUNTRY_BASE_NAME_OVERRIDES.get(country['tag'], re.sub(r'(公国|侯国|商邦)$', '', country['name']))
        country['name'] = base
        mapping[country['tag']] = {'name': base, 'surname': cn, 'surname_english': en}
    changed = []
    for language in ('simp_chinese', 'english'):
        path = out/f'main_menu/localization/{language}/hbe_l_{language}.yml'
        text = path.read_text(encoding='utf-8-sig')
        for tag, values in mapping.items():
            # Country base names omit polity suffixes; the game's rank adds them.
            value = values['name']
            text, count = re.subn(r'(?m)^ '+tag+r':\s*"[^\n]*"$', lambda m:' '+tag+': '+json.dumps(value,ensure_ascii=False), text)
            assert count == 1, (language, tag, count)
            key = 'hbe_dynasty_'+tag.lower()
            surname = values['surname' if language == 'simp_chinese' else 'surname_english']
            text, count = re.subn(r'(?m)^ '+key+r':\s*"[^\n]*"$', lambda m:' '+key+': '+json.dumps(surname,ensure_ascii=False), text)
            assert count == 1, (language, key, count)
        text = re.sub(r'(?m)^( hbe_BCB_scenario:\s*")建昌共治', r'\1建昌', text)
        path.write_text(text, encoding='utf-8-sig', newline='\n')
        changed.append(path.relative_to(out).as_posix())
    # The roster is an authoring index; avoid changing mechanics or saved family identities.
    roster = root/'data/countries_v001.csv'
    if roster.exists():
        with roster.open(encoding='utf-8-sig',newline='') as file:
            rows = list(csv.DictReader(file))
        for row in rows:
            row['country'] = mapping[row['tag']]['name']
        with roster.open('w',encoding='utf-8-sig',newline='') as file:
            writer = csv.DictWriter(file,fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)
    manifest['name_hotfix'] = {'countries': mapping, 'version': '0.3.0', 'stable_dynasty_ids': True}
    manifest['files'].update({p:hashlib.sha256((out/p).read_bytes()).hexdigest() for p in changed})
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (root/'data/name_hotfix_v030.json').write_text(json.dumps(manifest['name_hotfix'],ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return mapping

if __name__ == '__main__':
    import sys
    root = Path(sys.argv[1])
    apply(root/'mod/holy_bashu_empire', root)
    print('Corrected 36 country base names and 36 fictional families with real surnames; version 0.3.0.')
