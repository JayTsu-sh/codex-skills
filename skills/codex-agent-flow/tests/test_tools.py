import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('usage', ROOT / 'scripts/usage.py')
usage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(usage)


def meta(sid, parent=None, fork=None):
    source = {'subagent': {'thread_spawn': {'parent_thread_id': parent}}} if parent else 'cli'
    return dict(type='session_meta', payload=dict(id=sid, source=source, forked_from_id=fork))


def record(sid, rid, amount=100, at='2026-09-30T01:00:00Z'):
    return dict(type='token_usage_record', timestamp=at,
                payload=dict(thread_id=sid, response_id=rid, turn_id='turn-' + sid,
                             usage=dict(input_tokens=amount, cached_input_tokens=60,
                                        output_tokens=20, reasoning_output_tokens=5,
                                        cache_write_input_tokens=0, total_tokens=amount + 20)))


class UsageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, events):
        (self.root / (name + '.jsonl')).write_text(''.join(json.dumps(e) + '\n' for e in events))

    def test_inherited_history_deduplicated_children_included_manual_fork_excluded(self):
        parent = record('root', 'response-root')
        self.write('root', [meta('root'), parent, parent])
        self.write('child', [meta('child', 'root', 'root'), meta('root'), parent,
                             record('child', 'response-child', 200)])
        self.write('fork', [meta('fork', fork='root'), record('fork', 'response-fork', 900)])
        self.write('other-source', [dict(type='session_meta', payload=dict(
            id='other-source', source={'subagent': 'compact'}))])
        report = usage.summarize(self.root, 'root')
        self.assertEqual(report['responses'], 2)
        self.assertEqual(report['usage']['input_tokens'], 300)
        self.assertEqual(report['usage']['total_tokens'], 340)
        self.assertEqual(report['usage']['uncached_input_tokens'], 180)
        self.assertEqual(report['usage']['non_reasoning_output_tokens'], 30)
        self.assertEqual(report['sessions'], ['child', 'root'])
        child_only = usage.summarize(self.root, 'child')
        self.assertEqual(child_only['usage']['input_tokens'], 200)

    def test_interval_and_rejected_conflict(self):
        self.write('root', [meta('root'), record('root', 'one'),
                            record('root', 'two', at='2026-09-30T02:00:00Z')])
        report = usage.summarize(self.root, 'root', usage.timestamp('2026-09-30T09:00:00+08:00'),
                                 usage.timestamp('2026-09-30T10:00:00+08:00'))
        self.assertEqual(report['responses'], 1)
        self.write('root', [meta('root'), record('root', 'one'), record('root', 'one', 200)])
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            usage.summarize(self.root, 'root')

    def test_unknown_format_and_inconsistent_cache_fail(self):
        self.write('root', [meta('root'), dict(type='event_msg', payload=dict(type='token_count'))])
        with self.assertRaisesRegex(ValueError, 'No token_usage_record'):
            usage.summarize(self.root, 'root')
        self.write('root', [meta('root'), record('root', 'one', 50)])
        with self.assertRaisesRegex(ValueError, 'Cached input exceeds'):
            usage.summarize(self.root, 'root')


class RunnerTests(unittest.TestCase):
    def run_check(self, code, timeout=5):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/run_check.py'),
                                     '--log-dir', tmp, '--timeout', str(timeout), '--',
                                     sys.executable, '-c', code], capture_output=True, text=True,
                                    timeout=15)
            folder = next(Path(tmp).iterdir())
            report = json.loads((folder / 'result.json').read_text())
            log = (folder / 'output.log').read_text()
            return result, report, log

    def test_success_keeps_full_log_and_short_output(self):
        result, report, log = self.run_check("print('hello'*100000)")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(report['status'], 'PASS')
        self.assertGreater(len(log), 400000)
        self.assertLess(len(result.stdout), 1000)

    def test_failure_keeps_exit_status_and_bounds_long_line(self):
        result, report, log = self.run_check("import sys; print('error:' + 'x'*1000000); sys.exit(7)")
        self.assertEqual(result.returncode, 7)
        self.assertEqual(report['exit_code'], 7)
        self.assertGreater(len(log), 1000000)
        self.assertLess(len(result.stdout), 6000)

    def test_timeout_stops_child_process(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / 'child-survived'
            child = f"import time,pathlib; time.sleep(2); pathlib.Path({str(marker)!r}).touch()"
            code = f"import subprocess,sys,time; subprocess.Popen([sys.executable,'-c',{child!r}]); time.sleep(10)"
            result, report, _ = self.run_check(code, timeout=0.2)
            self.assertEqual(result.returncode, 124)
            self.assertEqual(report['status'], 'TIMEOUT')
            import time
            time.sleep(2.1)
            self.assertFalse(marker.exists())


if __name__ == '__main__':
    unittest.main()
