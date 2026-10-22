from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from eu5save import (EU5Save,SaveSource,Syntax,Block,Tagged,GameDate,read_variables,
                     load_snapshot,SaveSyntaxError,UnsupportedFormat,AmbiguousKey,SchemaError,SourceChanged)
from eu5save.hbe import snapshot,project_summary,anomalies


FIXTURE=b'''SAV0300-test-header
metadata={date=1377.4.1 playthrough_id="test-run"}
countries={ tags={1=BAB 2=OTHER} database={
1={definition=BAB owned_locations={10 11} ruler=7
currency_data={gold=42.125 prestige=2} economy={income=3 expense=1}
last_months_population=12.5 researched_advances={hbe_af_public_funding=yes}
variables={data={
{flag=hbe_burden data={type=value identity=2512345}}
{flag=hbe_af_initialized data={type=boolean identity=1}}
{flag=hbe_af_completed data={type=value identity=300000}}
{flag=hbe_af_target data={type=location identity=10}}
{flag=hbe_zero data={type=value}}
{flag=hbe_negative data={type=value identity=18446744073709501616}}
}} }
2={definition=OTHER owned_locations={} currency_data={}} }}
character_db={database={7={first_name="A"}}}
international_organization_manager={database={5={type=hbe_empire all_members={1} variables={data={}}}}}
building_manager={database={8={type=hbe_teahouse owner=1 location=10 level=2 employed=0.1}}}
subunit_manager={database={9={type=hbe_special owner=1}}}
market_manager={produced_goods={hbe_shu_paper=1.25 grain=5}}
war_manager={database={12={start_date=1376.1.1 attackers={{country=1}} defenders={{country=2}}}}}
'''
MANIFEST={'countries':[dict(tag='BAB',name='Chengdu',region='plain')]}


class SyntaxTests(unittest.TestCase):
    def parse(self,text,**kwargs):return Syntax(SaveSource.from_bytes(text),**kwargs).root

    def test_comments_escaped_quotes_and_braces(self):
        root=self.parse(b'a={s="a \\\" } # literal" # } ignored\n n=1}')
        self.assertEqual(root.block('a').scalar('s'),'a \\" } # literal'.replace('\\"','"'))
        self.assertEqual(root.block('a').scalar('n'),1)

    def test_duplicate_order_is_preserved(self):
        root=self.parse(b'k=1 k=2 items={3 4}')
        self.assertEqual([v.value for v in root.all('k')],[1,2])
        with self.assertRaises(AmbiguousKey):root.scalar('k')
        self.assertEqual([v.value for v in root.block('items').list_values()],[3,4])

    def test_tagged_color_and_operators(self):
        root=self.parse(b'color=rgb {1 2 3} n>=2')
        self.assertIsInstance(root.one('color'),Tagged)
        self.assertEqual(root.one('color').tag,'rgb')
        self.assertEqual(root.entries[-1].operator,'>=')

    def test_types_dates_and_unicode(self):
        root=self.parse('d=1337.4.1 n=-1.250 e=2e3 yes_quoted="yes" city="成都"'.encode())
        self.assertEqual(root.scalar('d'),GameDate(1337,4,1))
        self.assertEqual(root.scalar('n'),Decimal('-1.250'))
        self.assertEqual(root.scalar('e'),Decimal('2000'))
        self.assertEqual(root.scalar('yes_quoted'),'yes')
        self.assertEqual(root.scalar('city'),'成都')

    def test_truncated_blocks_and_quotes_fail(self):
        for text in [b'a={x=1',b'a={x="unterminated}',b'a=',b'}',b'a="bad']:
            with self.subTest(text=text),self.assertRaises(SaveSyntaxError):self.parse(text).validate()

    def test_max_depth_and_atom_limit(self):
        with self.assertRaises(SaveSyntaxError):self.parse(b'a={b={c={d=1}}}',max_depth=2).validate()
        with self.assertRaises(SaveSyntaxError):self.parse(b'a=abcdef',max_scalar_bytes=3).validate()

    def test_mixed_blocks_do_not_coerce_to_lists(self):
        block=self.parse(b'a={1 x=2 {n=3}}').block('a')
        self.assertEqual(len(block.entries),3)
        with self.assertRaises(SchemaError):block.list_values()

    def test_unknown_escapes_retained(self):
        self.assertEqual(self.parse(b'x="a\\q"').scalar('x'),'a\\q')

    def test_crlf_bom_and_cr_only_comments(self):
        root=self.parse(b'\xef\xbb\xbfSAV0300-test\r\na={# ignored }\r x=1\r}\r\n')
        self.assertEqual(root.block('a').scalar('x'),1)
        self.assertEqual(self.parse(b'SAV0300-test\ra=2\r').scalar('a'),2)

    def test_binary_control_in_scalar_rejected(self):
        with self.assertRaises((SaveSyntaxError,UnsupportedFormat)):
            self.parse(b'a="x\0y"').validate()


class SchemaTests(unittest.TestCase):
    def test_native_variables_and_implicit_zero(self):
        with EU5Save.from_bytes(FIXTURE) as game:
            row=next(game.countries({1}))
            self.assertEqual(row['variables']['hbe_burden'],25.12345)
            self.assertEqual(row['variables']['hbe_negative'],-.5)
            self.assertEqual(row['variables']['hbe_zero'],0)
            self.assertEqual(row['variables']['hbe_af_target'],dict(type='location',id=10))
            self.assertIs(row['variables']['hbe_af_initialized'],True)
            self.assertTrue(read_variables(game.records('countries')[1])['hbe_zero'].implicit_zero)

    def test_projection_and_missing_fields(self):
        with EU5Save.from_bytes(FIXTURE) as game:
            data=snapshot(game,MANIFEST)
            self.assertEqual(data['summary']['completed_all'],3)
            self.assertEqual(data['summary']['alive'],1)
            self.assertEqual(data['summary']['gold_median'],42.125)
            self.assertEqual(data['summary']['building_levels'],2)
            self.assertEqual(data['summary']['special_units'],1)
            self.assertEqual(data['summary']['wars'],1)
            self.assertEqual(anomalies(data),[])
            other=next(game.countries({2}))
            self.assertIsNone(other['income'])
            self.assertEqual(other['gold'],0)

    def test_missing_telemetry_is_not_zero(self):
        data=project_summary({'counters':{}},{'projects':[dict(id=1,name='x')]})
        self.assertFalse(data['telemetry_available'])
        self.assertIsNone(data['projects'][0]['starts_small'])

    def test_participation_expectation_comes_from_catalogue(self):
        catalogue={'ai_participation':{'personalities':[{'key':'active','chance':35}]}}
        data=project_summary({'counters':{'hbe_probe_eligible_active':10,'hbe_probe_accepted_active':3}},catalogue)
        self.assertEqual(data['personalities']['active']['configured_rate'],.35)
        self.assertEqual(data['personalities']['active']['rate'],.3)

    def test_duplicate_record_ids_rejected(self):
        with EU5Save.from_bytes(b'countries={database={1={} 1={}}}') as game:
            with self.assertRaises(SchemaError):game.records('countries')

    def test_native_database_tombstones(self):
        with EU5Save.from_bytes(b'countries={database={1=none 2={}}}') as game:
            self.assertEqual(set(game.records('countries')),{2})
            self.assertEqual(game.root.block('countries').block('database').scalar('1'),'none')
        with EU5Save.from_bytes(b'countries={database={1=none 1={}}}') as game:
            with self.assertRaises(SchemaError):game.records('countries')

    def test_government_nested_ruler(self):
        b=FIXTURE.replace(b'ruler=7',b'government={ruler=7}')
        with EU5Save.from_bytes(b) as game:
            data=snapshot(game,MANIFEST)
            self.assertEqual(data['summary']['missing_government_heads'],[])

    def test_invalid_variable_type_rejected(self):
        b=FIXTURE.replace(b'type=boolean identity=1',b'type=boolean identity=2')
        with EU5Save.from_bytes(b) as game:
            with self.assertRaises(SchemaError):list(game.countries({1}))

    def test_duplicate_variable_rejected(self):
        b=FIXTURE.replace(b'{flag=hbe_zero data={type=value}}',b'{flag=hbe_burden data={type=value}}')
        with EU5Save.from_bytes(b) as game:
            with self.assertRaises(SchemaError):list(game.countries({1}))

    def test_empty_native_variable_is_not_numeric_zero(self):
        b=FIXTURE.replace(b'{flag=hbe_zero data={type=value}}',b'{flag=hbe_zero data={}}')
        with EU5Save.from_bytes(b) as game:
            row=next(game.countries({1}))
            self.assertIsNone(row['variables']['hbe_zero'])
            self.assertEqual(row['variable_types']['hbe_zero'],'none')


class SourceCacheTests(unittest.TestCase):
    def test_binary_empty_and_size_limit(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'a.eu5';p.write_bytes(b'SAV0300\n\0binary')
            with self.assertRaises(UnsupportedFormat):EU5Save(p)
            p.write_bytes(b'')
            with self.assertRaises(SaveSyntaxError):EU5Save(p)
            p.write_bytes(FIXTURE)
            with self.assertRaises(UnsupportedFormat):EU5Save(p,max_bytes=10)

    def test_zip_text_no_extraction(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'a.eu5'
            with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:
                z.writestr('gamestate',FIXTURE);z.writestr('../ignored.txt','never extracted')
            with EU5Save(p) as game:
                self.assertEqual(game.metadata['date'],'1377.4.1')
                self.assertEqual(next(game.countries({1}))['gold'],42.125)
            self.assertFalse((Path(t).parent/'ignored.txt').exists())

    def test_zip_duplicate_members_and_expansion_limit(self):
        import warnings
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'a.eu5'
            with warnings.catch_warnings():
                warnings.simplefilter('ignore',UserWarning)
                with zipfile.ZipFile(p,'w') as z:
                    z.writestr('gamestate',FIXTURE);z.writestr('gamestate',FIXTURE)
            with self.assertRaises(UnsupportedFormat):EU5Save(p)
            with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('gamestate',b' '*10000)
            with self.assertRaises(UnsupportedFormat):EU5Save(p,max_bytes=1000)

    def test_invalid_projection_is_not_cached(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'a.eu5';p.write_bytes(FIXTURE.replace(b'type=boolean identity=1',b'type=boolean identity=2'))
            manifest=Path(t)/'manifest.json';manifest.write_text(json.dumps(MANIFEST));cache=Path(t)/'cache'
            with self.assertRaises(SchemaError):load_snapshot(p,manifest=manifest,cache_dir=cache)
            self.assertEqual(list(cache.glob('*.json')),[])

    def test_source_change_detected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'a.eu5';p.write_bytes(FIXTURE)
            with EU5Save(p) as game:
                # Changing timestamps is safe even when Windows holds a read mapping.
                import os
                stat=p.stat();os.utime(p,ns=(stat.st_atime_ns,stat.st_mtime_ns+1000000000))
                with self.assertRaises(SourceChanged):game.source.assert_unchanged()

    def test_cache_hit_invalidation_and_corruption_recovery(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'a.eu5';p.write_bytes(FIXTURE);manifest=Path(t)/'manifest.json'
            manifest.write_text(json.dumps(MANIFEST));cache=Path(t)/'cache'
            a,first=load_snapshot(p,manifest=manifest,cache_dir=cache)
            b,second=load_snapshot(p,manifest=manifest,cache_dir=cache)
            self.assertFalse(first['hit']);self.assertTrue(second['hit']);self.assertEqual(a,b)
            Path(second['path']).write_text('broken cache')
            _,third=load_snapshot(p,manifest=manifest,cache_dir=cache);self.assertFalse(third['hit'])
            p.write_bytes(FIXTURE.replace(b'gold=42.125',b'gold=43.125'))
            changed,info=load_snapshot(p,manifest=manifest,cache_dir=cache)
            self.assertFalse(info['hit']);self.assertEqual(changed['summary']['gold_total'],43.125)
            manifest.write_text(json.dumps({'countries':[]}))
            _,info=load_snapshot(p,manifest=manifest,cache_dir=cache);self.assertFalse(info['hit'])


if __name__=='__main__':unittest.main()
