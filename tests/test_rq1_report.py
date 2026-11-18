"""Report regressions: failed v3 outputs stay failed, including zero coverage."""
from contextlib import redirect_stdout
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('rq1_report', ROOT / 'scripts/rq1_report.py')
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)


class ReportTests(unittest.TestCase):
    def test_quote_sensitivity_is_historical_only(self):
        call = 'rq1/' + report.digest('M1-005')
        frozen = {'model': {'model_id': 'mock'}, 'seed': 329, 'budget': {},
                  'items': [{'item_id': 'M1-005'}]}
        results = [{'item_id': 'M1-005', 'status': 'failed', 'error': 'quote failure'}]
        events = [{'kind': 'call_failure', 'call_id': call, 'error': 'Evidence quote not in cited turn',
                   'response': {'output': {'label': 0}}}]
        for contract in ('decision-point-v1', 'decision-point-v2', 'decision-point-v3'):
            with self.subTest(contract=contract):
                frozen['contract_version'] = contract
                with patch.object(report, 'audit_run', return_value=(frozen, results)), \
                     patch.object(report.Journal, 'read', return_value=events):
                    run = report.load_run(Path('unused'))
                self.assertEqual(run['labels'], {})
                self.assertEqual(set(run['failures']), {'M1-005'})
                self.assertEqual(run['quote_failed_labels'], {} if contract.endswith('v3') else {'M1-005': '0'})

    def test_confidence_rule_does_not_mutate_or_invent_labels(self):
        run = {'labels': {'a': '0', 'b': '0', 'c': '2', 'd': 'N/A'},
               'details': {'a': {'confidence': 'low'}, 'b': {'confidence': 'high'},
                           'c': {'confidence': 'low'}, 'd': {'confidence': 'low'}},
               'failures': {'failed': 'invalid quote'}}
        before = deepcopy(run)
        self.assertEqual(report.high_confidence_zero_labels(run),
                         {'a': 'N/A', 'b': '0', 'c': '2', 'd': 'N/A'})
        self.assertEqual(run, before)

    def test_fmr_count_format_and_empty_scores(self):
        metrics = report.summary({'a': 'N/A', 'b': '2', 'c': '0'},
                                 {'a': '0', 'b': '2', 'c': '0'}, 10, 329)
        self.assertIn('(1/2)', report.fmt_fmr(metrics))
        empty = report.score([])
        self.assertIsNone(empty['false_missed_rate'])
        self.assertEqual(empty['confusion'], [[0] * 4 for _ in range(4)])
        self.assertIn('(0/0)', report.fmt_fmr(empty))

    def test_all_failed_v3_report_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / 'data'
            data.mkdir()
            (data / 'items.jsonl').write_text(json.dumps({'item_id': 'M1-005', 'behavior': 'B3'}) + '\n')
            for name in ('A', 'B', 'adjudicated'):
                (data / f'reference_{name}.csv').write_text('item_id,label\nM1-005,N/A\n')
            for seed in (329, 330, 331):
                run = root / 'runs/mock' / f'main60-s{seed}'
                run.mkdir(parents=True)
                (run / 'frozen_inputs.json').write_text('{}')
            def load(path):
                return {'model_id': 'mock', 'model': {'temperature': 0}, 'budget': {'max_output_tokens': 1000},
                        'contract': 'decision-point-v3', 'items': 1, 'pending': 0,
                        'labels': {}, 'details': {}, 'failures': {'M1-005': 'invalid opportunity quote'},
                        'quote_failed_labels': {}, 'latency_s': []}
            argv = ['rq1_report', '--runs', str(root / 'runs'), '--data', str(data),
                    '--save', str(root / 'result'), '--bootstrap', '10']
            with patch('sys.argv', argv), patch.object(report, 'load_run', side_effect=load), redirect_stdout(io.StringIO()):
                report.main()
            result = json.loads((root / 'result.json').read_text())
            model = result['models']['mock']
            self.assertEqual(model['seeds']['329']['coverage'], {'valid': 0, 'total': 1, 'fraction': 0.0})
            self.assertIsNone(model['seeds']['329']['posthoc_vs_adjudicated_with_quote_failures'])
            self.assertEqual(model['primary']['v2_false_missed_followup'][0]['status'], 'failed')
            text = (root / 'result.md').read_text()
            self.assertIn('coverage 0/1', text)
            self.assertIn('| M1-005 | N/A | failed |', text)
            before = (root / 'result.json').read_bytes()
            with patch('sys.argv', argv), redirect_stdout(io.StringIO()), \
                 patch('sys.stderr', io.StringIO()), self.assertRaises(SystemExit):
                report.main()
            self.assertEqual(before, (root / 'result.json').read_bytes())
