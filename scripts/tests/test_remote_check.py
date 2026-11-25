"""scripts/remote-check: grouping and receipt reading (the parts that run locally)."""
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
LOADER = importlib.machinery.SourceFileLoader('remote_check', str(ROOT / 'scripts/remote-check'))
SPEC = importlib.util.spec_from_loader('remote_check', LOADER)
REMOTE = importlib.util.module_from_spec(SPEC)
LOADER.exec_module(REMOTE)


class RemoteCheck(unittest.TestCase):
    def test_groups_balance_recorded_durations_and_keep_every_file_once(self):
        durations = {'a_test.bl': 9000, 'b_test.bl': 5000, 'c_test.bl': 4000, 'd_test.bl': 1}
        groups = REMOTE.groups_for(list(durations), 2, durations)
        self.assertEqual(sorted(sum(groups, [])), sorted(durations))
        self.assertEqual([['a_test.bl', 'd_test.bl'], ['b_test.bl', 'c_test.bl']], groups)

    def test_never_more_groups_than_files(self):
        self.assertEqual([['x_test.bl']], REMOTE.groups_for(['x_test.bl'], 6, {}))

    def test_file_rows_read_only_file_receipts(self):
        with tempfile.TemporaryDirectory() as temporary:
            receipts = Path(temporary)
            rows = [{'file': 'test/bl/a_test.bl', 'status': 'passed'},
                    {'file': 'test/bl/b_test.bl', 'status': 'failed', 'details': [{'message': 'x'}]},
                    {'type': 'process', 'identity': {}}]
            (receipts / 'files.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
            self.assertEqual(['test/bl/a_test.bl', 'test/bl/b_test.bl'],
                             [r['file'] for r in REMOTE.file_rows(receipts)])
            self.assertEqual([], REMOTE.file_rows(receipts / 'absent'))


if __name__ == '__main__':
    unittest.main()
