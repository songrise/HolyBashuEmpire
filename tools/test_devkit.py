"""Offline orchestration regressions: no game launch or Workshop mutation."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

from devkit.common import read_json, write_json, within
from devkit.context import Context
from devkit.artifacts import inspect, unchanged
from devkit.profiles import observation, validate, prepare
from devkit.runner import arguments, matches_process, request_stop, run_profile
from devkit.diagnostics import audit
from devkit.reporting import summarize, analyze_run
from devkit.workshop import plan, publish, verify, validate_description
from devkit.pipeline import FINAL_STAGES, run_final
from devkit.archive import archive


def artifact(root, *, compact=False):
    root.mkdir(parents=True)
    write_json(root / '.metadata/metadata.json', dict(version='9.8.7', name='Test Mod'))
    (root / 'script.txt').write_text('sample = yes\n', encoding='utf-8')
    files = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in root.rglob('*') if p.is_file()}
    manifest = dict(files=files, countries=[])
    if compact: manifest['distribution_compaction'] = dict(strategy='all_files_preserved_bc3')
    write_json(root / 'build_manifest.json', manifest)
    return root


class Workspace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='hbe dev ')
        self.root = Path(self.tmp.name)
        self.mod = artifact(self.root / 'mod/test')
        self.config = dict(schema_version=1, mod='mod/test', game='game', runs='work/runs',
            settings_template='settings.json', workshop=dict(app_id=1, item_id=2, languages=['english', 'schinese']))
        write_json(self.root / 'devtools.json', self.config)
        write_json(self.root / 'settings.json', dict(setting='template'))
        self.context = Context.load(self.root)

    def tearDown(self):
        self.tmp.cleanup()


class ArtifactTests(Workspace):
    def test_inventory_and_explicit_hash_mode(self):
        self.assertFalse(inspect(self.mod)['full_hashes_checked'])
        (self.mod / 'script.txt').write_text('tampered', encoding='utf-8')
        inspect(self.mod)  # Default is deliberately not a full content hash audit.
        with self.assertRaisesRegex(ValueError, 'invalid'):
            inspect(self.mod, hashes=True)

    def test_missing_extra_and_raw_release_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'compact'):
            inspect(self.mod, distribution=True)
        (self.mod / 'extra.txt').write_text('x')
        with self.assertRaisesRegex(ValueError, 'extra'):
            inspect(self.mod)
        (self.mod / 'extra.txt').unlink(); (self.mod / 'script.txt').unlink()
        with self.assertRaisesRegex(ValueError, 'missing'):
            inspect(self.mod)

    def test_plan_freeze_detects_same_size_edit(self):
        before = inspect(self.mod)
        (self.mod / 'script.txt').write_text('sample = noo\n', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'changed'):
            unchanged(before)

    def test_manifest_escape_is_rejected(self):
        doc = read_json(self.mod / 'build_manifest.json')
        doc['files']['../../settings.json'] = 'bad'
        write_json(self.mod / 'build_manifest.json', doc)
        with self.assertRaises(ValueError): inspect(self.mod)

    def test_atomic_json_preserves_previous_on_failure(self):
        path = self.root / 'result.json'; write_json(path, dict(old=True))
        with patch('devkit.common.os.replace', side_effect=OSError('simulated')):
            with self.assertRaises(OSError): write_json(path, dict(old=False))
        self.assertTrue(read_json(path)['old'])
        self.assertEqual(list(self.root.glob('result.json.*')), [])

    def test_local_settings_override_and_version(self):
        write_json(self.root / '.devtools.local.json', dict(workshop=dict(item_id=99)))
        c = Context.load(self.root)
        self.assertEqual(c.config['workshop']['app_id'], 1)
        self.assertEqual(c.config['workshop']['item_id'], 99)
        self.assertEqual(c.metadata['version'], '9.8.7')


class ProfileTests(Workspace):
    def scenario(self):
        s = observation(2, 1); s['telemetry'] = None
        return s

    def test_prepare_isolated_and_never_overwrite(self):
        before = inspect(self.mod)
        run = prepare(self.context, self.scenario(), run_id='first')
        self.assertEqual(read_json(run / 'status.json')['state'], 'prepared')
        self.assertEqual(inspect(self.mod)['files'], before['files'])
        self.assertIn('9.8.7', read_json(run / 'playsets.json')['playsets'][0]['name'])
        self.assertTrue((run / 'mod/holy_bashu_empire/in_game/common/tests/hbe_dev_observe.txt').is_file())
        with self.assertRaises(FileExistsError): prepare(self.context, self.scenario(), run_id='first')

    def test_natural_cannot_load_controlled_fixture(self):
        s = self.scenario(); s['fixtures'] = [dict(source='a', target='b')]
        with self.assertRaisesRegex(ValueError, 'Natural'): validate(s)

    def test_invalid_dates_order_and_test_names(self):
        for change in [dict(months=0), dict(checkpoints=['1337.4.2', '1337.4.2']),
                       dict(checkpoints=['1338.1.1', '1337.1.1']), dict(test_name='x } = {'),
                       dict(checkpoints=['1337.13.1'])]:
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate(dict(self.scenario(), **change))

    def test_checkpoint_final_is_included_for_uneven_interval(self):
        s = observation(7, 5)
        self.assertEqual(s['checkpoints'], ['1337.4.2', '1342.4.2', '1344.4.2'])

    def test_fixture_escape_and_invalid_settings_precede_copy(self):
        s = self.scenario(); s.update(mode='controlled', fixtures=[dict(source='settings.json', target='../../escape')])
        with self.assertRaises(ValueError): prepare(self.context, s, run_id='bad')
        self.assertFalse((self.root / 'work/runs/bad').exists())
        (self.root / 'settings.json').write_text('not json')
        with self.assertRaises(ValueError): prepare(self.context, self.scenario(), run_id='bad-settings')

    def test_launch_arguments_keep_space_path_as_one_argument(self):
        run = self.root / 'run with spaces'
        p = dict(scenario=self.scenario(), executable='game/binaries/eu5.exe')
        args = arguments(run, p)
        self.assertEqual(args[-1], '-userdir=' + run.resolve().as_posix())
        self.assertIn('-timed_handsoff=25', args)
        self.assertNotIn('-mod', args)

    def test_stop_rejects_pid_reuse_and_other_profile(self):
        run = self.root / 'run'
        expected = dict(pid=123, created='first', executable='D:/game/eu5.exe')
        current = dict(expected, command_line=subprocess.list2cmdline(['eu5.exe', '-userdir=' + run.as_posix()]))
        self.assertTrue(matches_process(current, expected, run))
        self.assertFalse(matches_process(dict(current, created='second'), expected, run))
        self.assertFalse(matches_process(dict(current, command_line=current['command_line'] + '-other'), expected, run))
        self.assertFalse(matches_process(dict(current, command_line=current['command_line'] + ' -userdir=other'), expected, run))
        write_json(run / 'status.json', dict(state='running')); write_json(run / 'process.json', expected)
        with patch('devkit.runner.process_identity', return_value=dict(current, created='second')), patch('devkit.runner.terminate_matching') as kill:
            with self.assertRaises(RuntimeError): request_stop(run)
            kill.assert_not_called()

    def test_supervisor_exit_and_user_stop_are_distinct(self):
        for stopped in [False, True]:
            with self.subTest(stopped=stopped):
                run = prepare(self.context, self.scenario(), run_id='stop-' + str(stopped))
                exe = self.root / 'game/binaries/eu5.exe'; exe.parent.mkdir(parents=True, exist_ok=True); exe.write_bytes(b'fake')
                if stopped: write_json(run / 'stop-request.json', dict(reason='test'))
                process = SimpleNamespace(pid=123, poll=lambda: 0, wait=lambda **kw: 0)
                with patch('devkit.runner.subprocess.Popen', return_value=process), patch('devkit.runner.process_identity', return_value=None):
                    r = run_profile(run, analyze=False)
                self.assertEqual(r['state'], 'stopped_by_user' if stopped else 'exited')
                with self.assertRaises(ValueError): run_profile(run, analyze=False)

    def test_timeout_and_analysis_failure_keep_separate_states(self):
        exe = self.root / 'game/binaries/eu5.exe'; exe.parent.mkdir(parents=True); exe.write_bytes(b'fake')
        run = prepare(self.context, self.scenario(), run_id='timeout')
        class Process:
            pid = 123
            stopped = False
            def poll(self): return 0 if self.stopped else None
            def terminate(self): self.stopped = True
            def wait(self, **kw): return 1
        proc = Process()
        with patch('devkit.runner.subprocess.Popen', return_value=proc), patch('devkit.runner.process_identity', return_value=None), patch('devkit.runner.time.monotonic', side_effect=[0, 10]):
            self.assertEqual(run_profile(run, timeout=1, analyze=False)['state'], 'timed_out')
        run = prepare(self.context, self.scenario(), run_id='analysis-error')
        with patch('devkit.runner.subprocess.Popen', return_value=proc), patch('devkit.runner.process_identity', return_value=None), patch('devkit.reporting.analyze_run', side_effect=ValueError('bad save')):
            with self.assertRaises(ValueError): run_profile(run)
        self.assertEqual(read_json(run / 'status.json')['state'], 'analysis_failed')
        self.assertEqual(read_json(run / 'completion.json')['state'], 'process_failed')

    def test_stop_terminates_only_a_verified_owned_child(self):
        import os, sys
        if os.name != 'nt': self.skipTest('Windows process handles')
        from devkit.processes import identity
        run = self.root / 'owned child'
        child = subprocess.Popen([sys.executable, '-B', '-c', 'import time; time.sleep(30)', '-userdir=' + run.as_posix()], creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            write_json(run / 'status.json', dict(state='running'))
            write_json(run / 'process.json', identity(child.pid))
            self.assertEqual(request_stop(run)['pid'], child.pid)
            self.assertEqual(child.wait(timeout=10), 1)
            self.assertTrue((run / 'stop-request.json').exists())
        finally:
            if child.poll() is None: child.terminate(); child.wait(timeout=10)


class DiagnosticTests(Workspace):
    def test_multiline_classification_and_baseline_preserve_numbers(self):
        folder = self.root / 'logs'; folder.mkdir()
        (folder / 'error.log').write_text('[12:01:00][jomini.cpp:2]: hbe_foo is orphaned\n context 123\n[12:01:01][engine.cpp:4]: Unknown effect abc\n detail\n[12:01:02][engine.cpp:4]: Unknown effect abc\n detail\n', encoding='utf-8')
        first = audit(folder)
        self.assertEqual(first['counts'], dict(registration=1, script=2))
        self.assertEqual(len(first['groups']), 2)
        second = audit(folder, first)
        self.assertTrue(all(not g['new_since_baseline'] for g in second['groups']))
        self.assertIn('123', first['groups'][0]['message'])
        self.assertIn('detail', first['groups'][1]['message'])

    def test_no_logs_is_unknown_not_clean_pass(self):
        folder = self.root / 'empty'; folder.mkdir()
        self.assertFalse(audit(folder)['logs_present'])


class FakeSteam:
    app_id, item_id = 1, 2
    def __init__(self):
        self.rows = {lang: dict(description='original-' + lang, title='title', visibility=0,
                               preview_url='image', additional_previews=[dict(filename='a')], metadata='{}')
                     for lang in ['english', 'schinese']}
        self.calls = []
    def query(self, language): return deepcopy(self.rows[language])
    def submit(self, **kwargs):
        self.calls.append(kwargs)
        if 'description' in kwargs: self.rows[kwargs['language']]['description'] = kwargs['description']
        if 'metadata' in kwargs:
            for row in self.rows.values(): row['metadata'] = kwargs['metadata']


class WorkshopTests(Workspace):
    def new_plan(self, **kwargs):
        self.plan_path = self.root / 'plan.json'
        return plan(self.context, output=self.plan_path, note='test update', **kwargs)

    def test_content_only_uses_compact_and_keeps_all_descriptions(self):
        compact = artifact(self.root / 'dist', compact=True)
        value = self.new_plan(artifact=compact)
        client = FakeSteam(); result = publish(self.plan_path, client)
        self.assertEqual(result['state'], 'published_and_verified')
        self.assertEqual(len(client.calls), 1)
        self.assertNotIn('description', client.calls[0])
        self.assertIn(value['plan_id'], client.rows['english']['metadata'])
        self.assertEqual(client.rows['schinese']['description'], 'original-schinese')
        with self.assertRaises(ValueError): publish(self.plan_path, client)

    def test_description_only_keeps_content_and_other_language(self):
        desc = self.root / 'description.bbcode'; desc.write_text('[b]新版[/b]', encoding='utf-8')
        self.new_plan(descriptions={'schinese': desc})
        client = FakeSteam(); result = publish(self.plan_path, client)
        self.assertEqual(result['errors'], [])
        self.assertNotIn('content', client.calls[0])
        self.assertEqual(client.rows['english']['description'], 'original-english')

    def test_timeout_records_unknown_and_never_resubmits(self):
        compact = artifact(self.root / 'dist', compact=True); self.new_plan(artifact=compact)
        client = FakeSteam()
        with patch.object(client, 'submit', side_effect=TimeoutError('timeout')):
            with self.assertRaises(TimeoutError): publish(self.plan_path, client)
        self.assertEqual(read_json(self.plan_path)['state'], 'outcome_unknown')
        with self.assertRaises(ValueError): publish(self.plan_path, client)
        self.assertEqual(verify(self.plan_path, client)['state'], 'verification_failed')

    def test_changed_artifact_is_rejected_before_steam_query(self):
        compact = artifact(self.root / 'dist', compact=True); self.new_plan(artifact=compact)
        (compact / 'script.txt').write_text('changed')
        client = FakeSteam()
        with patch.object(client, 'query') as query:
            with self.assertRaises(ValueError): publish(self.plan_path, client)
            query.assert_not_called()

    def test_wrong_sdk_target_is_rejected(self):
        desc = self.root / 'd'; desc.write_text('description')
        self.new_plan(descriptions={'english': desc}); client = FakeSteam(); client.item_id = 99
        with self.assertRaises(ValueError): publish(self.plan_path, client)
        with self.assertRaises(ValueError): verify(self.plan_path, client)

    def test_same_plan_cannot_publish_concurrently(self):
        from devkit.workshop import claim
        desc = self.root / 'd'; desc.write_text('description')
        self.new_plan(descriptions={'english': desc}); client = FakeSteam()
        with claim(self.plan_path):
            with self.assertRaises(FileExistsError): publish(self.plan_path, client)
        self.assertEqual(client.calls, [])
        self.assertEqual(publish(self.plan_path, client)['state'], 'published_and_verified')

    def test_bbcode_utf8_limit_placeholders_and_nul(self):
        for bad in ['[b]unclosed', '[b][i]wrong[/b][/i]', '字'*2700, 'TODO', 'bad\x00text']:
            with self.subTest(bad=bad[:20]), self.assertRaises(ValueError): validate_description(bad)
        self.assertEqual(validate_description('[list][*][b]条目[/b][/list]'), '[list][*][b]条目[/b][/list]')

    def test_unrelated_gallery_change_fails_verification(self):
        desc = self.root / 'd'; desc.write_text('new'); self.new_plan(descriptions={'english': desc})
        client = FakeSteam(); publish(self.plan_path, client)
        client.rows['schinese']['additional_previews'] = []
        self.assertEqual(verify(self.plan_path, client)['state'], 'verification_failed')


class ReportTests(Workspace):
    def test_partial_counts_separate_extinct_and_missing(self):
        rows = [dict(date='1337.4.2', playthrough_id='one', countries=[
            dict(id=1, tag='A', alive=True, gold=2, affairs=dict(completed=3)),
            dict(id=2, tag='B', alive=False, gold=0, affairs=dict(completed=2))])]
        result = summarize(rows, observation(5))
        self.assertFalse(result['target_reached'])
        self.assertEqual(result['cumulative'], dict(surviving=3, extinct_retained=2))
        self.assertEqual(result['missing_checkpoints'], ['1342.4.2'])
        with self.assertRaises(ValueError): summarize(rows + [dict(rows[0], playthrough_id='other')], observation(5))

    def test_report_uses_reusable_parser_and_preserves_archived_status(self):
        from test_eu5save import FIXTURE, MANIFEST
        run = self.root / 'legacy run'; saves = run / 'save games'; saves.mkdir(parents=True)
        (saves / 'scheduled.eu5').write_bytes(FIXTURE)
        (saves / 'autosave.eu5').write_bytes(b'currently writing')
        manifest = self.root / 'manifest.json'; write_json(manifest, MANIFEST)
        write_json(run / 'provenance.json', dict(version='old', checkpoints=['1377.4.1', '1387.4.1'], natural_ai=True))
        write_json(run / 'status.json', dict(state='stopped_by_user'))
        before = (run / 'status.json').read_bytes()
        (run / 'tests.txt').write_text('FAIL engine aggregate: 2 errors\n')
        result = analyze_run(run, manifest=manifest, catalogue={})
        self.assertEqual(len(result['snapshots']), 1)
        self.assertEqual(result['run_state'], 'stopped_by_user')
        self.assertEqual(result['engine']['wrapper_status'], 'failed')
        self.assertEqual(result['engine']['visual'], 'not_verified')
        from devkit.reporting import receipt
        evidence = receipt(result)
        self.assertEqual(evidence['checkpoint_dates'], ['1377.4.1'])
        self.assertNotIn('snapshots', evidence)
        self.assertEqual(evidence['validation_status'], 'failed')
        self.assertEqual(before, (run / 'status.json').read_bytes())
        self.assertTrue((run / 'analysis/report.md').exists())

    def test_bad_save_is_reported_not_silently_skipped(self):
        run = self.root / 'bad'; (run / 'save games').mkdir(parents=True)
        (run / 'save games/broken.eu5').write_bytes(b'not a save')
        write_json(run / 'provenance.json', dict(checkpoints=['1337.4.2'], natural_ai=True))
        result = analyze_run(run, manifest=self.mod / 'build_manifest.json', catalogue={})
        self.assertEqual(result['analysis_status'], 'failed')
        self.assertEqual(len(result['analysis_errors']), 1)

    def test_archive_crc_and_excludes_player_account_and_cache(self):
        run = self.root / 'run'; write_json(run / 'status.json', dict(state='finished'))
        write_json(run / 'account/private.json', dict(secret=True))
        write_json(run / 'analysis/cache/a.json', {})
        (run / 'save games').mkdir(); (run / 'save games/scheduled.eu5').write_bytes(b'save')
        out = self.root / 'evidence.zip'; result = archive(run, out)
        self.assertFalse(result['source_deleted'])
        with zipfile.ZipFile(out) as z: self.assertEqual(z.namelist(), ['status.json'])
        with self.assertRaises(FileExistsError): archive(run, out)
        with self.assertRaises(ValueError): archive(run, run / 'inside.zip')


class PipelineTests(unittest.TestCase):
    def test_order_signatures_and_restore_global_after_failure(self):
        calls = []
        art = SimpleNamespace(OUT='previous', export=lambda: calls.append(('art', ())))
        def load(name):
            if name == 'export_story_art': return art
            def call(*args): calls.append((name, args)); return name
            return SimpleNamespace(apply=call, build=call)
        result = run_final('out', 'root', 'game', loader=load)
        self.assertEqual(art.OUT, 'previous')
        self.assertEqual(len(calls), len(FINAL_STAGES))
        self.assertEqual(calls[-1], ('build_local_affairs', ('out', 'root', 'game')))
        self.assertLess([s.module for s in FINAL_STAGES].index('build_opening_population'), [s.module for s in FINAL_STAGES].index('apply_opening_territory'))
        self.assertEqual(result['apply_deep_balance_v031'], 'apply_deep_balance_v031')
        with patch.object(art, 'export', side_effect=RuntimeError('encoder failed')):
            with self.assertRaises(RuntimeError): run_final('out', 'root', 'game', loader=load)
        self.assertEqual(art.OUT, 'previous')

    def test_build_and_install_command_dispatch_preserve_context(self):
        from devkit.cli import parser, dispatch
        root = Path(__file__).resolve().parents[1]; context = Context.load(root)
        with patch('devkit.cli.subprocess.run', return_value=SimpleNamespace(returncode=0)) as call:
            dispatch(context, parser().parse_args(['build']))
            self.assertIn('--game-dir', call.call_args.args[0])
            dispatch(context, parser().parse_args(['install', '--userdir', 'test-user']))
            self.assertIn('-GamePath', call.call_args.args[0])


if __name__ == '__main__': unittest.main()
