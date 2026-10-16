"""Integration checks for user-selected trusted local programs and runner boundaries."""
import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from functools import partial
from http.server import ThreadingHTTPServer

from lab.compare import compare, CompareError, parse_inputs, run_limited, ROOT
from lab.serve import Handler

REFERENCE = (ROOT / 'web/starter/reference.c').read_text()
CANDIDATE = (ROOT / 'web/starter/candidate.py').read_text()
CORRECTED = (ROOT / 'web/starter/corrected.py').read_text()

class InputTests(unittest.TestCase):
    def test_spaces_empty_and_case_ids(self):
        rows = parse_inputs('-\n\nFF ff\n01 02\n')
        self.assertEqual([r['hex'] for r in rows], ['', 'ffff', '0102'])
        self.assertEqual(rows[1]['id'], 'input-3')

    def test_invalid_hex_and_limits(self):
        for value in ['a', 'gg', '00' * 65, '', '\n' * 4, '-\n' * 257]:
            with self.subTest(value=value[:20]), self.assertRaises(CompareError):
                parse_inputs(value)

    def test_seeded_inputs_reproduce(self):
        self.assertEqual(parse_inputs('', 20, 42), parse_inputs('', 20, 42))
        self.assertNotEqual(parse_inputs('', 20, 42), parse_inputs('', 20, 43))

    def test_generation_parameters(self):
        for count, seed in [(True, 42), (-1, 42), (201, 42), (1, -1), (1, 2**32), (1, '42')]:
            with self.subTest(count=count, seed=seed), self.assertRaises(CompareError):
                parse_inputs('-', count, seed)

class ExecutionTests(unittest.TestCase):
    def test_real_mismatch_and_identity(self):
        result = compare(REFERENCE, CANDIDATE, '-\n0102\nffff')
        self.assertEqual((result['passed'], result['failed']), (2, 1))
        self.assertEqual((result['cases'][2]['expected'], result['cases'][2]['actual']), (254, 510))
        self.assertEqual(len(result['reference']['artifactSha256']), 64)
        self.assertNotIn('text', result['reference'])

    def test_corrected_and_random_inputs(self):
        result = compare(REFERENCE, CORRECTED, '-', count=20, seed=123)
        self.assertEqual((result['total'], result['failed']), (21, 0))
        self.assertEqual(result['generation']['seed'], 123)

    def test_python_case_error_does_not_drop_later_inputs(self):
        candidate = 'def evaluate(data):\n    return 1 // len(data)\n'
        result = compare(REFERENCE, candidate, '-\n01')
        self.assertIn('ZeroDivisionError', result['cases'][0]['error'])
        self.assertTrue(result['cases'][1]['passed'])
        self.assertEqual(result['errors'], 1)

    def test_invalid_python_return_is_error(self):
        for value in ['True', '-1', '4294967296']:
            with self.subTest(value=value):
                result = compare(REFERENCE, 'def evaluate(data): return ' + value, '-')
                self.assertEqual((result['failed'], result['errors']), (1, 1))

    def test_python_prints_are_diagnostics(self):
        result = compare(REFERENCE, 'print("loaded")\ndef evaluate(data):\n    print("called")\n    return 0\n', '-')
        self.assertEqual(result['failed'], 0)
        self.assertIn('loaded', result['diagnostics']['candidate'])
        self.assertIn('called', result['diagnostics']['candidate'])

    def test_custom_entry_point(self):
        self.assertEqual(compare(REFERENCE, 'def reconstruct(data): return sum(data) & 255', '0102', 'reconstruct')['failed'], 0)

    def test_compile_error_and_missing_function(self):
        with self.assertRaises(CompareError) as error:
            compare('broken C', CORRECTED, '-')
        self.assertEqual(error.exception.stage, 'C compilation')
        with self.assertRaises(CompareError) as error:
            compare(REFERENCE, 'x = 1', '-')
        self.assertEqual(error.exception.stage, 'Python execution')

    def test_native_crash_is_reported(self):
        source = '#include <stddef.h>\n#include <stdint.h>\n#include <stdlib.h>\nuint32_t evaluate(const uint8_t *p, size_t n) { (void)p; (void)n; abort(); }'
        with self.assertRaises(CompareError) as error:
            compare(source, CORRECTED, '-')
        self.assertEqual(error.exception.stage, 'C execution')

    def test_timeout_and_output_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(CompareError) as error:
                run_limited([sys.executable, '-I', '-c', 'import time; time.sleep(10)'], Path(directory), 'Test', timeout=1)
            self.assertIn('timed out', str(error.exception))
            with self.assertRaises(CompareError):
                run_limited([sys.executable, '-I', '-c', 'import os\nwhile True: os.write(1, b"x" * 65536)'], Path(directory), 'Test', timeout=2)

    def test_source_and_entry_validation(self):
        for reference, function in [('', 'evaluate'), ('x' * (256 * 1024 + 1), 'evaluate'), (REFERENCE, 'x;bad')]:
            with self.subTest(function=function), self.assertRaises(CompareError):
                compare(reference, CORRECTED, '-', function)

class QuietHandler(Handler):
    def log_message(self, *args):
        pass

class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=str(ROOT / 'web')))
        cls.server.execution_enabled = True
        cls.server.execution_token = 'test-session-token'
        cls.server.execution_lock = threading.Lock()
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown(); cls.server.server_close(); cls.thread.join()

    def request(self, payload=None, **overrides):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        headers = {'Content-Type':'application/json', 'Origin':'http://127.0.0.1:%s' % self.server.server_port,
                   'X-ReverseLab-Token':self.server.execution_token}
        headers.update(overrides)
        connection.request('POST', '/api/compare', json.dumps(payload or {}), headers)
        response = connection.getresponse(); data = json.loads(response.read()); connection.close()
        return response.status, data

    def test_real_api_run(self):
        status, data = self.request({'reference':REFERENCE,'candidate':CANDIDATE,'inputs':'ffff','trusted':True})
        self.assertEqual((status, data['failed']), (200, 1))

    def test_origin_token_host_and_trust_required(self):
        for headers in [{'Origin':'https://example.org'}, {'X-ReverseLab-Token':'wrong'}, {'Host':'evil.example'}]:
            status, _ = self.request(**headers)
            self.assertEqual(status, 403)
        status, data = self.request({'trusted':False})
        self.assertEqual(status, 400)
        self.assertIn('trust', data['error'])

    def test_execution_disabled(self):
        self.server.execution_enabled = False
        try:
            self.assertEqual(self.request()[0], 403)
        finally:
            self.server.execution_enabled = True

    def test_one_run_at_a_time(self):
        self.server.execution_lock.acquire()
        try:
            self.assertEqual(self.request()[0], 409)
        finally:
            self.server.execution_lock.release()

    def test_bad_request_content(self):
        self.assertEqual(self.request(**{'Content-Type':'text/plain'})[0], 400)
        self.assertEqual(self.request(**{'Content-Length':'1048577'})[0], 413)

if __name__ == '__main__':
    unittest.main()
