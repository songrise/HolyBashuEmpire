import json
from pathlib import Path
import tempfile
import unittest
from package_mod import build


class PackageTests(unittest.TestCase):
    def test_complete_inventory_and_unchanged_scripts(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);source=root/'source';source.mkdir()
            (source/'unused.dds').write_bytes(b'unknown format must survive')
            (source/'script.txt').write_bytes(b'\xef\xbb\xbfx={ a=1 }\r\n')
            (source/'build_manifest.json').write_text('{"files":{},"version":"0.4.0"}')
            report=build(source,root/'out')
            self.assertEqual(report['file_count'],3)
            for name in ['unused.dds','script.txt']:
                self.assertEqual((source/name).read_bytes(),(root/'out'/name).read_bytes())
            manifest=json.loads((root/'out/build_manifest.json').read_text())
            self.assertEqual(manifest['version'],'0.4.0')
            self.assertEqual(set(manifest['files']),{'unused.dds','script.txt'})
            self.assertTrue(report['files_preserved'])

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as t:
            s=Path(t)/'source';s.mkdir();(s/'x.txt').write_text('original')
            out=Path(t)/'out';out.mkdir();(out/'keep').write_text('keep')
            with self.assertRaises(FileExistsError):build(s,out)
            self.assertEqual((out/'keep').read_text(),'keep')

    def test_nested_output_is_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            s=Path(t);(s/'x').write_text('x')
            with self.assertRaises(ValueError):build(s,s/'out')


if __name__=='__main__':unittest.main()
