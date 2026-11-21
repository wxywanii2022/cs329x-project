"""Exercise SC orchestration with the real pipeline but no GPU or live model."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/rq1_vllm_sc.sbatch'


@unittest.skipUnless(shutil.which('bash'), 'requires bash')
class SCJobTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        bins = self.root / '.venv/bin'
        bins.mkdir(parents=True)
        (bins / 'python').symlink_to(sys.executable)
        self.executable(bins / 'tutor-assess',
                        f'#!{sys.executable}\nfrom adaptive_tutor.rq1.cli import main\nraise SystemExit(main())\n')
        self.executable(bins / 'vllm', '#!/bin/bash\nexec sleep 300\n')
        # No server/GPU: only the orchestration is stubbed, not annotations/audits.
        for name in ('curl', 'nvidia-smi'):
            self.executable(bins / name, '#!/bin/bash\nexit 0\n')
        shutil.copytree(ROOT / 'examples', self.root / 'examples')
        shutil.copytree(ROOT / 'data/rq2/v02_fixtures', self.root / 'data/rq2/v02_fixtures')
        config = json.loads((ROOT / 'configs/assessment.mock.json').read_text())
        config['contract_version'] = 'decision-point-v3'
        self.config = self.root / 'assessment.mock.json'
        self.config.write_text(json.dumps(config))
        self.prereg = self.root / 'outputs/rq1-v3/preregistration.json'
        self.prereg.parent.mkdir(parents=True)
        self.prereg.write_text('{}')  # Presence guard only; not a real preregistration.
        self.env = dict(os.environ, PATH=str(bins) + os.pathsep + os.environ['PATH'],
                        PYTHONPATH=str(ROOT / 'src'), SC_SCRATCH=str(self.root / 'scratch'),
                        RUNS='outputs/rq1-v3', SEEDS='329 330 331')

    @staticmethod
    def executable(path, text):
        path.write_text(text)
        path.chmod(0o700)

    def run_job(self, stage, **env):
        return subprocess.run(['bash', str(SCRIPT), str(self.config), stage],
                              cwd=self.root, env=dict(self.env, **env),
                              text=True, capture_output=True, timeout=30)

    def test_smoke_and_resume_keep_journal_and_attempt_logs(self):
        first = self.run_job('smoke')
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        run = self.root / 'outputs/rq1-v3/mock/smoke-s329'
        summary = json.loads((run / 'summary.json').read_text())
        self.assertEqual(summary['items'], 5)
        self.assertEqual(summary['pending'], 0)
        journal = (run / 'events.jsonl').read_bytes()
        second = self.run_job('smoke')
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(journal, (run / 'events.jsonl').read_bytes())
        self.assertEqual(len(list((self.root / 'outputs/logs').glob('run-*.json'))), 2)

    def test_fatal_pipeline_error_is_not_hidden_by_old_complete_results(self):
        first = self.run_job('smoke')
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.executable(self.root / '.venv/bin/tutor-assess', '#!/bin/bash\nexit 2\n')
        result = self.run_job('smoke')
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('stage smoke finished', result.stdout)

    def test_fixtures_each_seed_and_immutable_config(self):
        result = self.run_job('fixtures')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for seed in (329, 330, 331):
            run = self.root / f'outputs/rq1-v3/mock/fixtures-s{seed}'
            self.assertEqual(json.loads((run / 'summary.json').read_text())['items'], 13)
            self.assertTrue((run / 'vs-fixtures.json').is_file())
        frozen_config = self.root / 'outputs/rq1-v3/mock/config.s329.json'
        original = frozen_config.read_bytes()
        config = json.loads(self.config.read_text())
        config['budget']['max_output_tokens'] += 1
        self.config.write_text(json.dumps(config))
        changed = self.run_job('fixtures')
        self.assertNotEqual(changed.returncode, 0)
        self.assertIn('Seed config changed', changed.stderr)
        self.assertEqual(original, frozen_config.read_bytes())

    def test_historical_destinations_and_missing_prereg_are_rejected(self):
        for runs in ('outputs/rq1', 'outputs/rq1-v2', 'outputs/rq1-v3/../rq1-v2/nested'):
            with self.subTest(runs=runs):
                result = self.run_job('smoke', RUNS=runs)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Historical outputs are read-only', result.stderr)
        self.prereg.unlink()
        result = self.run_job('smoke')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Missing v3 preregistration', result.stderr)

    def test_unknown_stage_rejected_before_startup(self):
        result = self.run_job('typo')
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.root / 'outputs/logs').exists())

    def test_main_stage_uses_three_references(self):
        # Synthetic fixtures stand in for Main 1; no human data/model calls here.
        data = self.root / 'data/rq1/main60'
        data.mkdir(parents=True)
        fixtures = self.root / 'data/rq2/v02_fixtures'
        shutil.copyfile(fixtures / 'items.jsonl', data / 'items.jsonl')
        for name in ('A', 'B', 'adjudicated'):
            shutil.copyfile(fixtures / 'reference.csv', data / f'reference_{name}.csv')
        result = self.run_job('main60', SEEDS='329')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        run = self.root / 'outputs/rq1-v3/mock/main60-s329'
        for name in ('A', 'B', 'adjudicated'):
            self.assertTrue((run / f'vs-{name}.json').is_file())

    def test_main2_requires_own_prereg_config_dir_and_pinned_items(self):
        # Synthetic fixtures stand in for Main 2; no human data/model calls here.
        import hashlib
        data = self.root / 'data/rq1/main2'
        data.mkdir(parents=True)
        fixtures = self.root / 'data/rq2/v02_fixtures'
        shutil.copyfile(fixtures / 'items.jsonl', data / 'items.jsonl')
        for name in ('A', 'B', 'adjudicated'):
            shutil.copyfile(fixtures / 'reference.csv', data / f'reference_{name}.csv')
        configs = self.root / 'configs/main2'
        configs.mkdir(parents=True)
        main2_config = configs / 'assessment.mock.json'
        shutil.copyfile(self.config, main2_config)
        env = dict(RUNS='outputs/rq1-main2', SEEDS='329')

        def job(config=main2_config, **extra):
            return subprocess.run(['bash', str(SCRIPT), str(config), 'main2'], cwd=self.root,
                                  env={**self.env, **env, **extra}, text=True, capture_output=True, timeout=30)

        result = job()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Missing Main 2 preregistration', result.stderr)
        prereg = self.root / 'outputs/rq1-main2/preregistration.json'
        prereg.parent.mkdir(parents=True)
        prereg.write_text(json.dumps({'items_sha256': '0' * 64}))
        result = job()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('not the preregistered file', result.stderr)
        prereg.write_text(json.dumps({'items_sha256': hashlib.sha256((data / 'items.jsonl').read_bytes()).hexdigest()}))
        result = job(config=self.config)
        self.assertIn('requires a configs/main2/ config', result.stderr)
        result = job(RUNS='outputs/rq1-v3')
        self.assertIn('must go under outputs/rq1-main2', result.stderr)
        result = self.run_job('main60', RUNS='outputs/rq1-main2')
        self.assertIn('reserved for the main2 stage', result.stderr)
        result = job()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        run = self.root / 'outputs/rq1-main2/mock/main2-s329'
        for name in ('A', 'B', 'adjudicated'):
            self.assertTrue((run / f'vs-{name}.json').is_file())
