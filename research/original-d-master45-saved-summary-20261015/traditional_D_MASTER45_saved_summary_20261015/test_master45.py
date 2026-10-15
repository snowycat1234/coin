#!/usr/bin/env python3
"""Focused source/row-binding tests. Mutates only in-memory or temporary copies."""
import copy, csv, hashlib, json, pathlib, tempfile, unittest
import assemble_master45 as m

class SavedMaster45Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inp=m.Inputs();cls.rows=m.build_rows(cls.inp)
        cls.fixture=json.loads((m.HERE/'fixtures/EXPECTED_CELLS.json').read_text())
    def reject(self,rows):
        with self.assertRaises((ValueError,KeyError)):m.validate_candidate(rows,self.rows)
    def test_positive_exact_axes(self):
        self.assertEqual([r['cell_id']for r in self.rows],self.fixture['ordered_cells'])
        self.assertEqual(len(self.rows),45);m.validate_candidate(self.rows,self.rows)
    def test_missing_cell(self):self.reject(copy.deepcopy(self.rows[:-1]))
    def test_duplicate_cell(self):self.reject(copy.deepcopy(self.rows+[self.rows[0]]))
    def test_duplicate_replaces_cell(self):
        r=copy.deepcopy(self.rows);r[-1]=copy.deepcopy(r[0]);self.reject(r)
    def test_swapped_period(self):
        r=copy.deepcopy(self.rows);r[0]['period_start_UTC']='2021-01-01';self.reject(r)
    def test_swapped_year(self):
        r=copy.deepcopy(self.rows);r[0]['year']=2022;self.reject(r)
    def test_swapped_tier(self):
        r=copy.deepcopy(self.rows);r[0]['tier']='HIGH';self.reject(r)
    def test_swapped_cost_metric(self):
        r=copy.deepcopy(self.rows);r[0]['fees_USDT'],r[1]['fees_USDT']=r[1]['fees_USDT'],r[0]['fees_USDT'];self.reject(r)
    def test_execution_cost_not_fee_plus_funding(self):
        r=copy.deepcopy(self.rows);r[0]['execution_cost_USDT']=r[0]['fees_USDT'];self.reject(r)
    def test_metric_fake_zero(self):
        r=copy.deepcopy(self.rows);r[0]['realized_daily_annualized_volatility']=0;self.reject(r)
    def test_primary_financial_rounding(self):
        r=copy.deepcopy(self.rows);r[0]['terminal_NAV_USDT']='10981.60';self.reject(r)
    def test_financial_string_type_loss(self):
        r=copy.deepcopy(self.rows);r[0]['fees_USDT']=float(r[0]['fees_USDT']);self.reject(r)
    def test_missing_duplicate_group(self):
        r=copy.deepcopy(self.rows);r[0]['duplicate_realized_path_group']='';self.reject(r)
    def test_pruned_H090(self):self.reject([copy.deepcopy(r)for r in self.rows if r['strategy']!='H090'])
    def test_partial_return_annualization(self):
        r=copy.deepcopy(self.rows);r[0]['return_annualized']=True;self.reject(r)
    def test_wrong_period_sourcefile(self):
        self.changed_source_must_reject(m.P22+'/2022_STATIC50_LOW_JAN1_DEC31_D_REVIEW.json',m.P25+'/2025_STATIC50_LOW_JAN1_DEC31_D_REVIEW.json')
    def test_wrong_tier_sourcefile(self):
        self.changed_source_must_reject(m.P22+'/2022_STATIC50_LOW_JAN1_DEC31_D_REVIEW.json',m.P22+'/2022_STATIC50_HIGH_JAN1_DEC31_D_REVIEW.json')
    def changed_source_must_reject(self,target,other):
        old=m.ROOT
        with tempfile.TemporaryDirectory(prefix='master45_negative_')as tmp:
            p=pathlib.Path(tmp)/target;p.parent.mkdir(parents=True);p.write_bytes((old/other).read_bytes());m.ROOT=pathlib.Path(tmp)
            try:
                with self.assertRaisesRegex(ValueError,'pin/path mismatch'):m.Inputs().load(target)
            finally:m.ROOT=old
    def test_path_exclusion(self):
        with self.assertRaisesRegex(ValueError,'Path exclusion'):m.Inputs().load('../not-a-source.json')
    def test_unpinned_source(self):
        i=m.Inputs();i.pins['files'].pop(m.OVERALL)
        with self.assertRaisesRegex(ValueError,'pin/path mismatch'):i.load(m.OVERALL)
    def test_false_duplicate_proof(self):
        i=m.Inputs();m.build_rows(i);i.cache[m.P25+'/H090_STATIC50_THREE_TIER_PATH_COMPARISON.json']['rows'][0]['all_saved_minute_fields_bit_equal']=False
        with self.assertRaisesRegex(ValueError,'Invalid exact duplicate'):m.verify_duplicates(i,self.rows)
    def test_swapped_duplicate_proof(self):
        i=m.Inputs();m.build_rows(i);i.cache[m.OVERALL]['exact_H090_STATIC50_realized_equivalence_groups'][0]['proof_SHA256']='0'*64
        with self.assertRaisesRegex(ValueError,'Invalid exact duplicate'):m.verify_duplicates(i,self.rows)
    def test_output_csv_preserves_every_value(self):
        with open(m.HERE/'MASTER45.csv',newline='')as f:actual=list(csv.DictReader(f))
        self.assertEqual(len(actual),45)
        for a,b in zip(actual,self.rows):self.assertEqual(a,{k:str(v)for k,v in b.items()})
    def test_saved_daily_derivation_bindings(self):
        j=self.inp.cache[m.DERV];self.assertEqual(len(j['cells']),12)
        for c in j['cells']:
            self.assertEqual(c['complete_days'],365);self.assertEqual(len(c['daily_close_NAV_float64']),365)
            self.assertEqual(len(c['daily_simple_returns_float64']),365)
            self.assertEqual(c['daily_simple_returns_float64'][0],c['daily_close_NAV_float64'][0]/10000.0-1.0)
            for now,prev,ret in zip(c['daily_close_NAV_float64'][1:],c['daily_close_NAV_float64'][:-1],c['daily_simple_returns_float64'][1:]):self.assertEqual(ret,now/prev-1.0)
            review=self.inp.load(c['bound_review']['path']);self.assertEqual(c['original_MINUTE']['SHA256'],review['evidence']['MINUTE.npz']['SHA256'])

if __name__=='__main__':unittest.main(verbosity=2)
