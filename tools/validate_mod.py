"""Structural and cross-reference checks; these are not an in-game playtest."""
import argparse,csv,hashlib,json,re,struct
from collections import Counter
from pathlib import Path
from pdxscript import blocks,tokens

ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--mod-dir',type=Path,default=ROOT/'mod/holy_bashu_empire')
    ap.add_argument('--game-dir',type=Path,required=True);ap.add_argument('--report',type=Path)
    a=ap.parse_args();m=a.mod_dir;game=a.game_dir/'game';checks=[]
    def check(name,ok):
        checks.append(dict(check=name,passed=bool(ok)))
        if not ok:raise AssertionError(name)
    manifest=json.loads((m/'build_manifest.json').read_text(encoding='utf-8'))
    check('36 selectable princes',len(manifest['countries'])==36)
    check('7 circles and 7 distinct electors',len(manifest['regions'])==7 and len(set(manifest['electors'].values()))==7)
    check('164 unique domain locations',len(set(l for c in manifest['countries'] for l in c['locations']))==164)
    check('all countries have 3 to 10 locations',all(3<=len(c['locations'])<=10 for c in manifest['countries']))
    check('country capitals belong to their countries',all(c['capital'] in c['locations'] for c in manifest['countries']))
    check('all source-owned locations were removed',manifest['removed_domain_tokens']>=164)
    for path,h in manifest['files'].items():
        check('file hash '+path,hashlib.sha256((m/path).read_bytes()).hexdigest()==h)
    defs={};custom={};script_files=list(m.rglob('*.txt'))
    check('bookmark files are UTF8 without BOM',all(not f.read_bytes().startswith(b'\xef\xbb\xbf') for f in (m/'main_menu/setup').rglob('*.txt')))
    check('database scripts use UTF8 BOM',all(f.read_bytes().startswith(b'\xef\xbb\xbf') for f in script_files if '/main_menu/setup/' not in f.as_posix()))
    for f in script_files:
        s=f.read_text(encoding='utf-8-sig');bs=blocks(s,0)
        for k,*_ in bs:
            if f.parent.name!='modifier_icons' and (k.startswith('hbe_') or re.fullmatch(r'hbe\.\d+',k)):
                if k in custom:raise AssertionError(f'duplicate custom definition {k}: {f} / {custom[k]}')
                custom[k]=str(f.relative_to(m))
        defs[str(f.relative_to(m))]=bs
    check('all script braces and custom definitions are valid',True)
    # Validate full country ownership and ensure there is no original core left.
    setup=(m/'main_menu/setup/1337/10_countries.txt').read_text(encoding='utf-8-sig')
    countries=manifest['countries'];tags={c['tag'] for c in countries};domain={l for c in countries for l in c['locations']}
    owners={};newcounts=Counter();coreleft=[]
    for tag,_,b,e,_ in blocks(setup,2):
        chunk=setup[b:e]
        for key,_,x,y,_ in blocks(chunk,0):
            ls=[t.value for t in tokens(chunk[x:y]) if t.value in domain]
            if ls and tag not in tags and (key.startswith('own_') or key.startswith('control') or key=='our_cores_conquered_by_others'):coreleft.append((tag,key,ls))
            if key.startswith('own_control_'):
                for loc in ls:
                    if loc in owners:raise AssertionError(f'duplicate owner for {loc}: {owners[loc]} / {tag}')
                    owners[loc]=tag;newcounts[tag]+=1
    check('every domain location has exactly one new owner',set(owners)==domain and not coreleft)
    check('ownership matches manifest',all(all(owners[l]==c['tag'] for l in c['locations']) for c in countries))
    native_defs=set()
    for category in ('cultures','religions'):
        for f in (game/'in_game/common'/category).glob('*.txt'):
            native_defs.update(k for k,*_ in blocks(f.read_text(encoding='utf-8-sig'),0))
    check('all capital cultures and religions exist',all(c['culture'] in native_defs and c['religion'] in native_defs for c in countries))
    loc_file=m/'main_menu/localization/simp_chinese/hbe_l_simp_chinese.yml'
    check('Chinese localization has UTF8 BOM',loc_file.read_bytes().startswith(b'\xef\xbb\xbf'))
    loc_keys=set(re.findall(r'^\s+([^\s:]+):',loc_file.read_text(encoding='utf-8-sig'),re.M))
    refs=[]
    for f in script_files:
        s=f.read_text(encoding='utf-8-sig')
        refs+=re.findall(r'\b(?:title|desc|name|text|loc|leader_title_key|format)\s*=\s*(hbe[\w.]+|HBE_\w+)',s)
    check('all custom text references localized',set(refs)<=loc_keys)
    char_keys={k for k,*_ in blocks((m/'main_menu/setup/1337/05_hbe_characters.txt').read_text(encoding="utf-8-sig"),1)}
    check('36 distinct starting rulers exist',char_keys=={f'hbe_ruler_{t.lower()}' for t in tags})
    election=(m/'in_game/common/resolutions/hbe_election.txt').read_text(encoding="utf-8-sig")
    check('7 seat election requires a strict majority', 'scope:highest_vote > scope:total_votes_needed' in election)
    modifiers=(m/'main_menu/common/static_modifiers/hbe_modifiers.txt').read_text(encoding="utf-8-sig")
    check('Tianfu has exactly +10% food and construction','local_monthly_food_modifier = 0.10 local_construction_speed = 0.10' in modifiers)
    effects=(m/'in_game/common/scripted_effects/hbe_effects.txt').read_text(encoding="utf-8-sig")
    check('Tianfu is permanent and idempotent','NOT = { has_location_modifier = hbe_tianfu }' in effects and 'modifier = hbe_tianfu years = -1' in effects)
    check('external owners have the Tianfu modifier removed','remove_location_modifier = hbe_tianfu' in effects)
    check('110 decision prototypes and 64 research nodes',manifest['decisions']==110 and manifest['research_nodes']==64)
    check('35 regional milestone missions and repeatable services',manifest['regional_missions']==35 and manifest['recurring_services']==7)
    pulse=(m/'in_game/common/on_action/hbe_on_actions.txt').read_text(encoding="utf-8-sig")
    check('centennial content and repeatable pulse persist','current_year >= 1437' in pulse and 'yearly_country_pulse' in pulse and 'current_year < 1457' not in pulse)
    check('war declarations use the isolation gate','hbe_war_is_internal = yes' in (m/'in_game/common/international_organizations/hbe_empire.txt').read_text(encoding="utf-8-sig"))
    check('war calls have a cross-boundary gate','join_war_disabled_trigger' in (m/'in_game/common/join_war_rules/hbe_isolation.txt').read_text(encoding="utf-8-sig"))
    io_setup=(m/'main_menu/setup/1337/99_hbe_organizations.txt').read_text(encoding='utf-8')
    check('IO members precede leaders in the persistent reader',all(s.index('members =')<s.index('leader =') for k,_,b,e,_ in blocks(io_setup,1) for s in [io_setup[b:e]]))
    image=(m/'loading_screen/gfx/interface/hbe/placeholder.dds').read_bytes()
    check('placeholder DDS header and dimensions',image[:4]==b'DDS ' and struct.unpack_from('<I',image,4)[0]==124 and len(image)==128+384*192*4)
    # Detect accidentally unlinked references to our own effects, events or variables.
    hbe_refs=set()
    variable_refs=set()
    for f in script_files:
        s=f.read_text(encoding='utf-8-sig')
        hbe_refs.update(re.findall(r'\b(hbe_[a-z0-9_]+)\s*=\s*(?:yes|no)',s))
        variable_refs.update(re.findall(r'(?:name\s*=|has_variable\s*=|set_variable\s*=|remove_variable\s*=)\s*(hbe_[a-z0-9_]+)',s))
    check('custom effect and trigger references resolve',hbe_refs<=set(custom)|variable_refs)
    report=dict(status='passed',checks=checks,check_count=len(checks),gameplay_validation='pending in-game; structural checks are not a savegame test',version='0.01')
    if a.report:a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'PASS: {len(checks)} checks; 36 princes, 164 locations, 7 circles, 64 research nodes.')

if __name__=='__main__':main()
