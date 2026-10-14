import copy
import json
from pathlib import Path
import tempfile
import unittest

from lab.pipeline import ROOT, SEED, generate, digest
from lab.holdout import (case_stream, evaluate, freeze, fresh_cases, replay,
                         validate_evaluation)
from lab.webbuild import validate, validate_assets


class HoldoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.web = Path(cls.temp.name) / 'web'
        cls.path = cls.web / 'data/report.json'
        cls.receipt_path = cls.web / 'data/evaluation-freeze.json'
        cls.base = generate(count=30, output=cls.path)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.path.write_text(json.dumps(self.base))

    def run_evaluation(self):
        receipt = freeze(self.path, self.receipt_path)
        record = evaluate(self.path, self.receipt_path, count=100, seed=42)
        return receipt, record

    def test_real_evaluation_is_disjoint_and_detects_mutation(self):
        receipt, record = self.run_evaluation()
        validate(record)
        validate_assets(record, self.web)
        self.assertEqual(record['evaluation']['freezeSha256'], digest(self.receipt_path.read_bytes()))
        self.assertNotIn('seed', receipt)
        for fixture in record['fixtures']:
            development = {c['hex'] for c in fixture['variants'][0]['reports'][0]['cases']}
            for variant in fixture['variants']:
                correct = variant['evaluationReports'][0]
                self.assertEqual((correct['passed'], correct['failed']), (100, 0))
                self.assertFalse(development & {c['hex'] for c in correct['cases']})
                self.assertEqual(len({c['hex'] for c in correct['cases']}), 100)
                if fixture['id'] == 'packet':
                    self.assertGreater(variant['evaluationReports'][1]['failed'], 20)

    def test_replay_regenerates_exact_case_and_native_outputs(self):
        _, record = self.run_evaluation()
        packet = next(f for f in record['fixtures'] if f['id'] == 'packet')
        failure = next(c for c in packet['variants'][1]['evaluationReports'][1]['cases'] if not c['passed'])
        result = replay('packet', 'O2', 'faulty_endian', failure['id'], self.path, self.receipt_path)
        self.assertEqual(result['failed'], 1)
        self.assertEqual(result['failures'][0]['expected'], failure['expected'])
        self.assertEqual(result['failures'][0]['actual'], failure['actual'])
        correct = replay('packet', 'O2', 'reconstruct', failure['id'], self.path, self.receipt_path)
        self.assertEqual(correct['failed'], 0)

    def test_changed_binary_is_rejected_before_evaluation(self):
        freeze(self.path, self.receipt_path)
        artifact = ROOT / self.base['fixtures'][0]['variants'][0]['artifact']
        original = artifact.read_bytes()
        try:
            artifact.write_bytes(original + b'changed')
            with self.assertRaisesRegex(ValueError, 'Frozen input changed'):
                evaluate(self.path, self.receipt_path, count=10, seed=42)
        finally:
            artifact.write_bytes(original)

    def test_changed_candidate_snapshot_and_generator_are_rejected(self):
        receipt = freeze(self.path, self.receipt_path)
        corrupt = copy.deepcopy(receipt)
        corrupt['candidateTexts']['packet'] += '\n# edited\n'
        self.receipt_path.write_text(json.dumps(corrupt))
        with self.assertRaisesRegex(ValueError, 'Frozen candidate text changed'):
            evaluate(self.path, self.receipt_path, count=10, seed=42)
        receipt['generatorSha256'] = '0' * 64
        self.receipt_path.write_text(json.dumps(receipt))
        with self.assertRaisesRegex(ValueError, 'generator changed'):
            evaluate(self.path, self.receipt_path, count=10, seed=42)

    def test_development_seed_and_repeated_evaluation_are_rejected(self):
        freeze(self.path, self.receipt_path)
        with self.assertRaisesRegex(ValueError, 'differ from development'):
            evaluate(self.path, self.receipt_path, count=10, seed=SEED)
        evaluate(self.path, self.receipt_path, count=10, seed=42)
        with self.assertRaisesRegex(ValueError, 'Already evaluated'):
            evaluate(self.path, self.receipt_path, count=10, seed=43)
        freeze(self.path, self.receipt_path)
        self.assertNotIn('evaluation', json.loads(self.path.read_text()))

    def test_duplicate_overlap_and_result_corruption_block_export(self):
        receipt, record = self.run_evaluation()
        corrupt = copy.deepcopy(record)
        cases = corrupt['fixtures'][0]['variants'][0]['evaluationReports'][0]['cases']
        cases[0]['hex'] = corrupt['fixtures'][0]['variants'][0]['reports'][0]['cases'][0]['hex']
        with self.assertRaisesRegex(ValueError, 'overlap'):
            validate_evaluation(corrupt, receipt)
        corrupt = copy.deepcopy(record)
        corrupt['fixtures'][0]['variants'][0]['evaluationReports'][0]['passed'] -= 1
        with self.assertRaisesRegex(ValueError, 'summary mismatch'):
            validate(corrupt)
        self.receipt_path.write_text(self.receipt_path.read_text() + ' ')
        with self.assertRaisesRegex(ValueError, 'receipt hash mismatch'):
            validate_assets(record, self.web)

    def test_corpus_is_deterministic_unique_and_bounded(self):
        for fixture in self.base['fixtures']:
            development = case_stream(fixture['variants'][0]['reports'][0])
            cases, skipped = fresh_cases(fixture['id'], 42, 500, development)
            self.assertEqual((cases, skipped), fresh_cases(fixture['id'], 42, 500, development))
            self.assertTrue(all(len(bytes.fromhex(c['hex'])) <= 64 for c in cases))
        with self.assertRaises(ValueError):
            fresh_cases('fsm', 42, 0, [])

    def test_absent_case_and_recording_change_reject_replay(self):
        self.run_evaluation()
        with self.assertRaisesRegex(ValueError, 'Case ID absent'):
            replay('packet', 'O2', 'reconstruct', 'missing', self.path, self.receipt_path)
        corrupt = json.loads(self.path.read_text())
        corrupt['fixtures'][0]['reconstruction']['sha256'] = '0' * 64
        self.path.write_text(json.dumps(corrupt))
        with self.assertRaisesRegex(ValueError, 'identity differs'):
            replay('checksum', 'O2', 'reconstruct', None, self.path, self.receipt_path)


if __name__ == '__main__':
    unittest.main()
