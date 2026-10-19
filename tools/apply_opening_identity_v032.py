"""Native marriage-law completion and display-name disambiguation for 1337 HBE setup."""
from build_support import snapshot_files
from pathlib import Path
import json, re
from pdxscript import blocks,tokens
from build_support import write_preserving_format as put

TEMPLATE='main_menu/setup/templates/hbe_monarchy.txt'
NAMES={
 'CGZ':('BAX','昌州旧部','Old Changzhou'),
 'YYG':('BBF','酉阳旧部','Old Youyang'),
 'SNP':('BBW','松潘诸部','Songpan Tribes'),
 'MHU':('BCA','马湖旧部','Old Mahu'),
 'YNG':('BCC','云南永宁','Yunnan Yongning'),
}

def country_records(out):
    text=(Path(out)/'main_menu/setup/1337/10_countries.txt').read_text(encoding='utf-8-sig')
    return {key:text[a:b] for key,_,a,b,_ in blocks(text,2)}

def possessions(body):
    result=[]
    for key,_,a,b,_ in blocks(body,0):
        if key.startswith('own_'):result.extend(t.value for t in tokens(body[a:b]))
    return result

def apply(out,root,game):
    out,root,game=map(Path,(out,root,game));path=out/TEMPLATE;text=path.read_text(encoding='utf-8-sig')
    laws=[(a,b) for key,_,a,b,_ in blocks(text) if key=='laws'];assert len(laws)==1
    a,b=laws[0];body=text[a:b];existing=re.findall(r'\bmarriage_law\s*=\s*(\w+)',body);assert len(existing)<=1
    if existing:body=re.sub(r'\bmarriage_law\s*=\s*\w+','marriage_law = monogamous_marriage',body)
    else:
        match=re.search(r'(?m)^([ \t]*)heir_religion_law\s*=',body);assert match
        body=body[:match.start()]+match[1]+'marriage_law = monogamous_marriage\n'+body[match.start():]
    put(path,text[:a]+body+text[b:])
    for lang,index in [('simp_chinese',1),('english',2)]:
        lines=['l_'+lang+':','# Distinguish native tags from the thirty-six HBE countries; no tag or territory changes.']
        lines.extend(' '+tag+': '+json.dumps(row[index],ensure_ascii=False) for tag,row in NAMES.items())
        put(out/f'main_menu/localization/{lang}/replace/hbe_native_country_names_l_{lang}.yml','\n'.join(lines)+'\n')
        p=out/f'main_menu/localization/{lang}/replace/hbe_native_country_names_l_{lang}.yml'
        if not p.read_bytes().startswith(b'\xef\xbb\xbf'):p.write_bytes(b'\xef\xbb\xbf'+p.read_bytes())
    records=country_records(out);mp=out/'build_manifest.json';m=json.loads(mp.read_text(encoding='utf-8'));tags=[r['tag'] for r in m['countries']]
    report={'marriage_law':'monogamous_marriage','native_reference':'main_menu/setup/templates/east_asia_monarchy.txt',
            'countries_using_shared_template':[tag for tag in tags if 'include = "hbe_monarchy"' in records[tag]],
            'heir_selection':'cognatic_primogeniture','heir_selection_changed':False,'new_campaign_setup_only':True,
            'no_runtime_law_effects':True,'native_name_disambiguation':[
                {'native_tag':tag,'hbe_tag':row[0],'name_simp_chinese':row[1],'name_english':row[2],
                 'native_owned_locations':possessions(records[tag]),'native_capital':re.search(r'\bcapital\s*=\s*(\w+)',records[tag])[1]}
                for tag,row in NAMES.items()],
            'country_tags_territory_and_cores_changed':False,'hbe_names_changed':False}
    assert len(report['countries_using_shared_template'])==36
    m['opening_identity_v032']=report;m['files']=snapshot_files(out)
    put(mp,json.dumps(m,ensure_ascii=False,indent=2)+'\n');return report

def validate(out,game,manifest,check):
    if 'opening_identity_v032' not in manifest:return
    out,game=map(Path,(out,game));text=(out/TEMPLATE).read_text(encoding='utf-8-sig')
    check('HBE shared government has exactly one native monogamous marriage policy',re.findall(r'\bmarriage_law\s*=\s*(\w+)',text)==['monogamous_marriage'])
    native=(game/'main_menu/setup/templates/east_asia_monarchy.txt').read_text(encoding='utf-8-sig')
    check('HBE marriage policy matches native general East Asian monarchy','marriage_law = monogamous_marriage' in native)
    check('existing male-preference primogeniture and heir-religion policy retained','heir_selection = cognatic_primogeniture' in text and 'heir_religion_law = heir_any_religion' in text)
    records=country_records(out);tags=[r['tag'] for r in manifest['countries']]
    for tag in tags:
        check(tag+' starts with shared HBE marriage policy','include = "hbe_monarchy"' in records[tag] and 'marriage_law' not in records[tag])
    for lang,index in [('simp_chinese',1),('english',2)]:
        p=out/f'main_menu/localization/{lang}/replace/hbe_native_country_names_l_{lang}.yml';t=p.read_text(encoding='utf-8-sig')
        entries={q[1]:json.loads(q[2]) for q in re.finditer(r'^[ \t]+(\w+):[ \t]*("(?:[^"\\]|\\.)*")',t,re.M)}
        check(lang+' five native names explicitly replaced',entries=={tag:row[index] for tag,row in NAMES.items()})
        check(lang+' replacement names do not contain rank suffixes',not any(word in v for v in entries.values() for word in ('公国','侯国','Duchy','Marquisate')))
    for row in manifest['opening_identity_v032']['native_name_disambiguation']:
        check(row['native_tag']+' retains all territories and capital',possessions(records[row['native_tag']])==row['native_owned_locations'] and re.search(r'\bcapital\s*=\s*(\w+)',records[row['native_tag']])[1]==row['native_capital'])
    check('surviving native Songpan and Yongning retain their possessions',len(possessions(records['SNP']))==1 and len(possessions(records['YNG']))==5)
    check('landless native Changzhou Youyang and Mahu are retained as defined tags',all(tag in records and not possessions(records[tag]) for tag in ('CGZ','YYG','MHU')))
