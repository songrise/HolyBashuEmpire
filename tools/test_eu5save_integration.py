"""Opt-in regression against archived observations, without a second raw parser."""
import json,os,time,unittest
from pathlib import Path
from eu5save import load_snapshot,anomalies


@unittest.skipUnless(os.environ.get('EU5_SAVE_REFERENCE') and os.environ.get('EU5_SAVE_DIR'),
                     'Set EU5_SAVE_REFERENCE and EU5_SAVE_DIR to compare real checkpoints')
class ArchivedCheckpointTests(unittest.TestCase):
    def test_all_checkpoint_projections(self):
        root=Path(__file__).resolve().parents[1]
        reference=json.loads(Path(os.environ['EU5_SAVE_REFERENCE']).read_text(encoding='utf-8'))
        folder=Path(os.environ['EU5_SAVE_DIR']);rows=[]
        fields=['alive','locations','gold_median','gold_total','population_total','burden_mean','burden_max',
                'completed_all','completed_live','active','paused','buildings','building_levels',
                'operating_buildings','special_units','wars','missing_government_heads']
        for expected in reference['snapshots']:
            with self.subTest(date=expected['date']):
                start=time.perf_counter()
                actual,cache=load_snapshot(folder/expected['save'],manifest=root/'mod/holy_bashu_empire/build_manifest.json',cache_dir=root/'work/save-cache')
                self.assertEqual(actual['date'],expected['date'])
                self.assertEqual(actual['playthrough_id'],expected['playthrough_id'])
                for key in fields:
                    a,b=actual['summary'][key],expected['summary'][key]
                    if isinstance(b,(float,int)):self.assertAlmostEqual(a,b,delta=.0051,msg=key)
                    else:self.assertEqual(a,b,key)
                by_id={r['id']:r for r in actual['countries']}
                for old in expected['countries']:
                    self.assertIn(old['id'],by_id)
                    new=by_id[old['id']]
                    for key in ['tag','locations','gold','income','expense','population']:
                        if isinstance(old[key],(float,int)):self.assertAlmostEqual(new[key],old[key],places=5,msg=old['tag']+':'+key)
                        else:self.assertEqual(new[key],old[key])
                    for key,value in old['variables'].items():
                        self.assertIn(key,new['variables'])
                        measured=new['variables'][key]
                        if isinstance(measured,dict):measured=measured['id']
                        if isinstance(value,(float,int)):self.assertAlmostEqual(measured,value,places=5,msg=old['tag']+':'+key)
                        else:self.assertEqual(measured,value)
                self.assertEqual(anomalies(actual),[])
                elapsed=round(time.perf_counter()-start,4)
                rows.append(dict(date=actual['date'],cache_hit=cache['hit'],elapsed_seconds=elapsed,status='matched'))
                print('Verified semantic checkpoint '+actual['date']+' in '+str(elapsed)+'s',flush=True)
        target=root/'docs/testing/save-parser-v040.json'
        target.write_text(json.dumps(dict(status='passed',checkpoints=len(rows),projection_rows=rows,
            compared_summary_fields=fields,compared_country_fields=True,compared_hbe_variables=True,
            note='Existing observations are the oracle; the test reads raw saves only through the reusable parser.'),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':unittest.main()
