from pathlib import Path
import mmap,re,json,hashlib
base=Path(__file__).resolve().parent;root=base/'v020';profile=base/'eu5-v020-test'
manifest_path=root/'mod/holy_bashu_empire/build_manifest.json'
manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
p=profile/'save games/scheduled_save_DESKTOP-L1LK2TH_1338_01_01.eu5'
required={
 'BAB':['native_policy','building_unlocked','policy_settlement','settlement_idempotent','operating_institution','office_appointed','office_expired','no_free_civic','upper_clamp','lower_clamp','supported_capacity','regiment_pressure','over_capacity_preserves_army','orphan_office_cleared'],
 'BAE':['policy_settlement','vacancy_respected','successor'],
 'BAF':['policy_settlement','paid_charge']}
countries={};checks={};missing=[]
with p.open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as m:
 starts=list(re.finditer(rb'\n([0-9]+)=\{\r?\n\tcountry_name="([^"\r\n]+)"',m));tags={c['tag'] for c in manifest['countries']}
 for i,match in enumerate(starts):
  tag=match[2].decode('utf-8','replace')
  if tag not in tags:continue
  b=m[match.start():starts[i+1].start()]
  flags={v.decode() for v in re.findall(rb'flag=(hbe_[a-z_0-9]+)',b)}
  countries[tag]={'id':int(match[1]),'joined':b'hbe_banquet_joined' in b}
  if tag in required:
   for key in required[tag]:
    ok='hbe_test_'+key in flags;checks[tag+'.'+key]=ok
    if not ok:missing.append(tag+'.'+key)
   values={key.decode():int(v)/100000 for key,v in re.findall(rb'flag=(hbe_test_burden_once|hbe_test_effective_institution)\s+data=\{\s+type=value\s+identity=(\d+)',b)}
   countries[tag]['fixture_values']=values
 index=m.find(b'hbe_banquet={');situation=m[index:index+5000]
 checks['36_princes_joined']=len(countries)==36 and all(v['joined'] for v in countries.values())
 checks['situation_active_from_1337_10_1']=b'status=active' in situation and b'start=1337.10.1' in situation
 checks['native_special_regiment_saved']=re.search(rb'owner='+str(countries['BAB']['id']).encode()+rb'[^}]{0,350}type=hbe_canal_crossbow',m) is not None
checks['no_fixture_files_shipped']=not any('test' in f.name for f in (root/'mod/holy_bashu_empire/in_game').rglob('hbe_civic_test*'))
tested=json.loads((profile/'hbe_release_under_test.json').read_text(encoding='utf-8'))
changed=[k for k,v in tested['script_files'].items() if not (root/'mod/holy_bashu_empire'/k).is_file() or hashlib.sha256((root/'mod/holy_bashu_empire'/k).read_bytes()).hexdigest()!=v]
allowed=['in_game/common/building_types/hbe_civic_buildings.txt']+[f'main_menu/localization/{lang}/hbe_l_{lang}.yml' for lang in ('english','simp_chinese')]
checks['tested_core_scripts_unchanged']=set(changed)==set(allowed)
targeted=True
for k in allowed:
 original=(profile/'mod/holy_bashu_empire'/k).read_text(encoding='utf-8-sig')
 final=(root/'mod/holy_bashu_empire'/k).read_text(encoding='utf-8-sig')
 if 'building_types' in k:
  expected=original.replace('local_manpower = 0.005','local_manpower = 0.0015')
  targeted &= original.count('local_manpower = 0.005')==4 and 0.0015/0.15<=0.0125
 else:expected=original+' hbe_institution_construction: "巴蜀机构营建物资"\n'
 targeted &= final==expected
checks['post_test_numeric_and_localization_fix_verified']=bool(targeted)
debug=(profile/'logs/debug.log').read_text(encoding='utf-8-sig',errors='replace')
errors=(profile/'logs/error.log').read_text(encoding='utf-8-sig',errors='replace')
unexpected=[line for line in errors.splitlines() if re.search(r'\bhbe_|\bHBE',line) and not any(s in line for s in ('Variable ','Possible match:'))]
parse=[line for line in debug.splitlines() if re.search(r'Unknown (?:effect|trigger)|Error:|Invalid scope|PostValidate',line) and re.search(r'\bhbe_|\bHBE',line)]
known=[line for line in unexpected if 'hbe_institution_construction:' in line or 'has a too high efficiency for manpower' in line and any(k in line for k in ('hbe_cliff_stockade','hbe_plank_fort','hbe_guide_station','hbe_covenant_stockade'))]
checks['no_new_custom_parse_errors']=not parse and not [line for line in unexpected if line not in known]
checks['logged_warnings_addressed_by_targeted_fix']=bool(targeted) and len(known)==5
missing+= [k for k,v in checks.items() if not v and k not in missing]
report=dict(version='0.2.0',status='passed' if not missing else 'failed',checks=checks,missing=missing,countries=countries,save_date='1338.1.1',save_path=str(p),source_manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),tested_manifest_sha256=tested['manifest_sha256'],post_test_changes=changed,post_test_validation='Exact diff verification: four manpower coefficients reduced from 0.005 to 0.0015 within the native 0.0125-per-employee cap; one missing construction localization added in both languages. No second full engine run after these small changes, as requested.',art_scope='Final DDS resources and flag composition proofs verified separately. Actual GUI rendering is not covered by the headless run.',addressed_custom_diagnostics=known,unexpected_custom_diagnostics=[line for line in unexpected if line not in known]+parse,scope='Isolated 1337 observer run to 1338. Fixture grants research and funding, instant-builds native institutions and relaxes only the test unit year gate. Confirms policy settlement, operating employment, office succession/expiry, unit count pressure, supply cap and regiment survival. Not a century simulation or live GUI verification.')
(root/'docs/runtime_v020.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'status':report['status'],'missing':missing,'custom_errors':unexpected+parse},ensure_ascii=False))
if missing:raise SystemExit(1)
