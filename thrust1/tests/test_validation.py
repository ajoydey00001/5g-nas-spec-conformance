"""Regression checks for evidence validation and witness claims."""
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('build_spec', ROOT/'thrust1/extract/build_spec_fsm.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)

class ValidationTests(unittest.TestCase):
    def test_invalid_evidence_fails_before_writing_model(self):
        doc = {'cells': {'S0': {'input': {'evidence': [{'clause_id': '1', 'quote': 'invented'}]}}}}
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            (tmp/'cells.json').write_text(json.dumps(doc))
            (tmp/'clauses.jsonl').write_text(json.dumps({'id': '1', 'title': 'Title', 'text': 'actual text'})+'\n')
            result = subprocess.run([sys.executable, '-I', str(ROOT/'thrust1/extract/build_spec_fsm.py'), str(tmp/'cells.json'), str(tmp/'clauses.jsonl'), str(tmp/'output')], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('quote validation failed', result.stderr)
            self.assertFalse((tmp/'output').exists())

    def test_missing_clause_is_invalid_evidence(self):
        doc = {'cells': {'S0': {'input': {'evidence': [{'clause_id': 'missing', 'quote': 'text'}]}}}}
        self.assertEqual(len(builder.check_quotes(doc, {})), 1)

    def test_case_two_does_not_imply_invisibility(self):
        classes = json.loads((ROOT/'thrust1/results/T1.6_spec_vs_ABsrs.json').read_text())['classes']
        self.assertEqual(sum(c['case'] == 2 and c['visible_to_diff'] for c in classes), 8)
        for c in classes:
            visible = len({tuple(o) for o in c['device_outputs'].values()}) > 1
            self.assertEqual(c['visible_to_diff'], visible)

    def test_devlyzer_categories_overlap(self):
        base = ROOT/'thrust1/lab/devlyzer_srs'
        ids = {kind: {t['Id'] for t in json.loads((base/f'deviant-queries_{kind}.json').read_text())['traces']} for kind in ('attack','benign','unresolved')}
        self.assertEqual(len(ids['attack']), 23)
        self.assertEqual(len(ids['attack'] & ids['benign']), 7)
        self.assertFalse(ids['unresolved'])

if __name__ == '__main__':
    unittest.main()
