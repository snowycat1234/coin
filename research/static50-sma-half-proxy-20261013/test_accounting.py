"""Synthetic independent Decimal/accounting and publication gate checks."""
from pathlib import Path
import tempfile
import unittest
import numpy as np
import score
from core import DAY, write_json


class AccountingTests(unittest.TestCase):
    def test_independent_decimal_reconciles_paid_terminal_and_signed_funding(self):
        old=score.load_module('audit_test_old_score',score.OLD_SCORE)
        d=np.arange(4,dtype=np.int64)*DAY
        w=np.zeros((4,5));w[:,0]=[.1,-.1,.1,.1];w[:,1]=[-.05,.05,0,-.05]
        p0=np.full((4,5),100.);p1=np.full((4,5),100.)
        fp=np.zeros((4,5));fp[:,0]=[.1,-.1,.2,-.2]
        metrics,rows=old.reference(d,w,p0,p1,fp,np.ones((4,5),dtype=bool))
        self.assertTrue(metrics['hypothetical_cost_terminal'])
        self.assertGreater(metrics['terminal_cost_proxy_USDT'],0)
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'rows.json';write_json(p,rows)
            import json
            saved=json.loads(p.read_text())
            audit=old.decimal_audit(d,w,p0,p1,fp,metrics,saved)
        self.assertTrue(audit['passed'],audit.get('errors'))

    def test_unchanged_dependency_identity(self):
        self.assertEqual(score.sha256(score.OLD_SCORE),score.OLD_SCORE_SHA256)
        self.assertEqual(score.sha256(score.REFERENCE),score.REFERENCE_SHA256)
        self.assertEqual(score.sha256(score.ECONOMICS),score.ECONOMICS_SHA256)
        self.assertEqual(score.sha256(score.RISK),score.RISK_SHA256)

    def test_parent_go_gate_precedes_publication_and_economics(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'results'
            with self.assertRaisesRegex(ValueError,'Explicit parent go'):
                score.run(Path(directory)/'missing.json',Path(directory),output,parent_go=False)
            self.assertFalse(output.exists())


if __name__=='__main__':unittest.main()
