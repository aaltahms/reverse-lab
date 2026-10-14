import copy
import json
from pathlib import Path
import tempfile
import unittest
from lab.pipeline import generate, digest, ROOT, oracle, cases_for
from lab.stripped import add_variant, symbol_range
from lab.webbuild import validate

class StrippedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.path=Path(cls.temp.name)/'report.json'
        cls.record=generate(count=20,output=cls.path)
        cls.variant=add_variant('packet',cls.path)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_actual_stripped_reference_and_mutant(self):
        variant=self.variant
        self.assertTrue(variant['stripped'])
        self.assertEqual(variant['reports'][0]['failed'],0)
        self.assertGreater(variant['reports'][1]['failed'],20)
        symbol=variant['derivedFrom']['symbol']
        self.assertFalse(any(line.split()[-1:]==[symbol] for line in variant['evidence']['symbols']['output'].splitlines()))
        self.assertEqual(digest((ROOT/variant['artifact']).read_bytes()),variant['sha256'])
        self.assertEqual(variant['evidence']['locations']['status'],'unavailable')
        self.assertIn(variant['derivedFrom']['procedureAddress'][2:],variant['evidence']['disassembly']['output'])
        validate(json.loads(self.path.read_text()))

    def test_stale_twin_rejected_before_transform(self):
        original=json.loads(self.path.read_text())
        corrupt=copy.deepcopy(original)
        next(v for f in corrupt['fixtures'] if f['id']=='packet' for v in f['variants'] if v['id']=='O2')['sha256']='0'*64
        self.path.write_text(json.dumps(corrupt))
        try:
            with self.assertRaisesRegex(ValueError,'Reference artifact changed'):
                add_variant('packet',self.path)
        finally:
            self.path.write_text(json.dumps(original))

    def test_symbol_range_is_unique_and_bounded(self):
        self.assertEqual(symbol_range('00000100 T _evaluate\n00000200 T _main','_evaluate'),(256,512))
        with self.assertRaises(ValueError):
            symbol_range('00000100 T _evaluate','_evaluate')
        with self.assertRaises(ValueError):
            symbol_range('00000100 T _evaluate\n00000200 T _evaluate\n00000300 T _main','_evaluate')

if __name__=='__main__':
    unittest.main()
