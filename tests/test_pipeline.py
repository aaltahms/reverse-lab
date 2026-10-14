import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from lab.pipeline import ROOT, SEED, cases_for, digest, evidence, generate, oracle, packet, run, verify
from lab.webbuild import validate
from reconstructions import checksum, fsm
from reconstructions.packet import reconstruct, faulty_endian

class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        # Real native compilation and execution; don't replace the shipped demo.
        cls.record = generate(count=50, output=Path(cls.temp.name) / 'report.json')

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_real_reports_and_optimization_agreement(self):
        validate(self.record)
        for fixture in self.record['fixtures']:
            with self.subTest(fixture=fixture['id']):
                slow, fast = fixture['variants']
                self.assertEqual([c['expected'] for c in slow['reports'][0]['cases']],
                                 [c['expected'] for c in fast['reports'][0]['cases']])
                for variant in fixture['variants']:
                    self.assertEqual(digest((ROOT / variant['artifact']).read_bytes()), variant['sha256'])
                    self.assertEqual(variant['reports'][0]['failed'], 0)
                    for kind in ['disassembly', 'symbols', 'artifact']:
                        self.assertEqual(variant['evidence'][kind]['status'], 'available')
                        self.assertTrue(variant['evidence'][kind]['output'].strip())

    def test_known_checksum_vector_and_bound(self):
        # Fletcher-16 standard hand-computed example: 'abcde' -> 0xc8f0.
        self.assertEqual(checksum.reconstruct(b'abcde'), 0xC8F0)
        for variant in ['O0', 'O2']:
            values = oracle(ROOT / f'build/checksum-{variant}', [{'hex': b'abcde'.hex()}, {'hex': ''}, {'hex': (bytes([1])*32).hex()}, {'hex': (bytes([1])*32+b'\xff').hex()}])
            self.assertEqual(values, [0xC8F0, 0, 0x1220, 0x1220])

    def test_packet_error_precedence_and_packing(self):
        good = packet(3, 0x1234, b'\xff\x01')
        malformed = [b'', b'\x00'*6, bytes([165, 8, 0, 0, 200, 0]), bytes([165, 1, 0, 0, 200, 0]), good[:-1]+bytes([good[-1]^1])]
        cases = [{'hex': c.hex()} for c in malformed + [good]]
        for variant in ['O0', 'O2']:
            self.assertEqual(oracle(ROOT / f'build/packet-{variant}', cases), [1,2,3,4,5,0x83123400])
        self.assertEqual(reconstruct(good), 0x83123400)
        self.assertEqual(faulty_endian(good), 0x83341200)

    def test_mutant_is_detected_but_symmetric_sequences_pass(self):
        for seq in [0, 0x1111, 0xFFFF]:
            data = packet(0, seq, b'')
            self.assertEqual(reconstruct(data), faulty_endian(data))
        for seq in [1, 256, 0x1234]:
            data = packet(0, seq, b'')
            self.assertNotEqual(reconstruct(data), faulty_endian(data))
        reports = next(f for f in self.record['fixtures'] if f['id']=='packet')['variants']
        for variant in reports:
            self.assertGreater(variant['reports'][1]['failed'], 20)

    def test_fsm_sticky_fault_reset_and_invalid_counts(self):
        traces = [bytes([1,2]), bytes([2,1,2]), bytes([2,3,1,2]), bytes([255,255]), bytes([1,0,2])]
        expected = [0x202, 0x103, 0x402, 0x20103, 0x303]
        self.assertEqual([fsm.reconstruct(t) for t in traces], expected)
        for variant in ['O0','O2']:
            self.assertEqual(oracle(ROOT / f'build/fsm-{variant}', [{'hex':t.hex()} for t in traces]), expected)

    def test_harness_rejects_and_recovers(self):
        stream = '\nzz\n0\n' + '00'*65 + '\n-\n00\x00\n-\n' + '01'*64
        result = run([str(ROOT / 'build/packet-O2')], input=stream)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.splitlines(), ['ERR','ERR','ERR','ERR','1','ERR','1','2'])

    def test_case_stream_is_seeded_and_bounded(self):
        for name in ['checksum','packet','fsm']:
            cases = cases_for(name, SEED, 50)
            self.assertEqual(cases, cases_for(name, SEED, 50))
            self.assertNotEqual(cases, cases_for(name, SEED+1, 50))
            self.assertTrue(all(len(bytes.fromhex(c['hex'])) <= 64 for c in cases))
            self.assertEqual(len(set(c['id'] for c in cases)), len(cases))

    def test_missing_tool_retains_unavailable_status(self):
        item = evidence(['reverselab-nonexistent-tool'])
        self.assertEqual(item['status'], 'unavailable')
        self.assertIsNone(item['exitCode'])

    def test_report_validation_catches_inconsistent_results(self):
        corrupt = copy.deepcopy(self.record)
        corrupt['fixtures'][0]['variants'][0]['reports'][0]['failed'] += 1
        with self.assertRaises(ValueError):
            validate(corrupt)

    def test_replay_case_and_hash_guard(self):
        with patch('lab.pipeline.Path.read_text', return_value=json.dumps(self.record)):
            replay = verify('packet','O2','faulty_endian',SEED,50,'boundary-006')
            self.assertEqual(replay['failed'], 1)
            self.assertEqual(replay['failures'][0]['hex'], 'a503123400ee')
            damaged = copy.deepcopy(self.record)
            damaged['fixtures'][1]['variants'][1]['sha256'] = '0'*64
            with patch('lab.pipeline.Path.read_text', return_value=json.dumps(damaged)):
                with self.assertRaisesRegex(ValueError, 'Executable missing or changed'):
                    verify('packet','O2','reconstruct',SEED,50)

    def test_replay_allowlist_and_missing_case(self):
        with self.assertRaises(ValueError):
            verify('../x','O2','reconstruct',SEED,50)
        with patch('lab.pipeline.Path.read_text', return_value=json.dumps(self.record)):
            with self.assertRaisesRegex(ValueError, 'Case ID absent'):
                verify('packet','O2','reconstruct',SEED,50,'absent')

    def test_replay_case_stream_digest_guard(self):
        stale = copy.deepcopy(self.record)
        stale['fixtures'][0]['variants'][1]['reports'][0]['caseDigest'] = '0'*64
        with patch('lab.pipeline.Path.read_text', return_value=json.dumps(stale)):
            with self.assertRaisesRegex(ValueError, 'Case generator changed'):
                verify('checksum','O2','reconstruct',SEED,50)

    def test_unsupported_tool_retains_error(self):
        result = subprocess.CompletedProcess([], 2, '', 'unsupported option')
        with patch('lab.pipeline.shutil.which', return_value='/some/tool'), patch('lab.pipeline.run', return_value=result):
            item = evidence(['tool','--flag'])
        self.assertEqual(item['status'], 'unsupported')
        self.assertEqual(item['exitCode'], 2)
        self.assertEqual(item['error'], 'unsupported option')

    def test_oracle_detects_truncated_response(self):
        fake = subprocess.CompletedProcess([], 0, '1\n', '')
        with patch('lab.pipeline.run', return_value=fake):
            with self.assertRaisesRegex(RuntimeError, 'Invalid oracle response'):
                oracle(Path('/unused'), [{'hex':''},{'hex':'00'}])

if __name__ == '__main__':
    unittest.main()
