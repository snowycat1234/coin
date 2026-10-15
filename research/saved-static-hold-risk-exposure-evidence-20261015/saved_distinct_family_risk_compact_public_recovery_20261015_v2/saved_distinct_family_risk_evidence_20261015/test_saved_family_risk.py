"""Generated small fixtures only. No real output/source/provider/account reads."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('saved_family_risk',HERE/'saved_family_risk.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def minute_fixture(days=2):
    a=np.zeros((days*1440,37),dtype=np.float64)
    a[:,0]=10000+np.arange(1,len(a)+1,dtype=float)/100
    a[:,1]=a[:,0];a[:,36]=np.arange(1,len(a)+1,dtype=np.int64)*m.MINUTE_US
    return a,np.array(m.COLUMN_NAMES,dtype='<U64')


def cohort_fixture():
    rows=[];cells=[]
    for y in m.CALENDARS:
        n=(m.CALENDARS[y][1]-m.CALENDARS[y][0])//m.MINUTE_US
        for f in ('STATIC50','H090','VOL_MANAGED_HOLD'):
            for t in m.TIERS:
                cid=f'{y}_{f}_{t}'
                r={'year':y,'strategy':f,'tier':t,'cell_id':cid,'required_minutes':n,'completed_minutes':n,
                  'evidence_status':'REVIEW_APPROVED_SAVED_TERMINAL','initial_wallet_USDT':'10000',
                  'adaptive_DEV_only':True,'bindings':{'new_expansion_manifest_SHA256':m.MANIFEST_SHA256},
                  'return_taxonomy':m.PAID_STATUS,'conditional_settlement_count':0,'unpaid_liability_USDT':'0',
                  'terminal_NAV_USDT':'10100','annual_return_fraction':'0.01',
                  'comparable_paid_annual_return_fraction':'0.01','conditional_model_annual_return_fraction':None,
                  'all_observation_MDD_fraction':.05,'minute_close_MDD_fraction':.04,
                  'complete_daily_close_MDD_fraction':.03,'realized_daily_annualized_volatility':.1,
                  'gross_held_mean_minute_close':.2,'gross_held_max_minute_close':.3,
                  'minimum_free_cash_minute_close_USDT':7000.,'maximum_isolated_margin_minute_close_USDT':3000.}
                rows.append(r)
                if cid!='2024_STATIC50_MID':
                    cells.append({'cell_id':cid,'year':y,'strategy':f,'tier':t,'calendar':list(m.CALENDARS[y])})
                else:r['reused_prior_completed_case']=True
    return {'status':'FINAL_SAVED_ONLY','review_approved_terminal_rows':18,'pending_rows':0,'rows':rows},{'cells':cells}


class TestSavedFamilyRisk(unittest.TestCase):
    def test_complete_calendar_and_daily(self):
        a,c=minute_fixture();m.validate_minute(a,c,(0,len(a)*m.MINUTE_US),len(a))
        d,n=m.daily_telemetry(a,c);x=m.aggregate_daily(d,n)
        self.assertEqual(x['observed_minutes'],2880)
        self.assertEqual(x['complete_days'],2)
        self.assertEqual(x['flat_actual_quantity_fraction'],1.)
        self.assertEqual(x['gross_weight_mean'],0.)
        self.assertEqual(x['daily_close_MDD_fraction'],0.)
        self.assertEqual(x['daily_realized_annual_volatility'],d[:,list(n).index('daily_simple_return')].std(ddof=1)*np.sqrt(365))

    def test_missing_extra_out_of_order_minutes(self):
        a,c=minute_fixture()
        for b in (a[:-1],np.r_[a,a[-1:]],a[::-1]):
            with self.assertRaises(m.EvidenceError):m.validate_minute(b,c,(0,len(a)*m.MINUTE_US),len(a))
        b=a.copy();b[400,36]+=1
        with self.assertRaises(m.EvidenceError):m.validate_minute(b,c,(0,len(a)*m.MINUTE_US),len(a))

    def test_nonfinite_nonpositive_and_type(self):
        a,c=minute_fixture()
        for v in (np.nan,np.inf,-np.inf):
            b=a.copy();b[20,5]=v
            with self.assertRaises(m.EvidenceError):m.validate_minute(b,c,(0,len(a)*m.MINUTE_US),len(a))
        for v in (0.,-1.):
            b=a.copy();b[20,0]=v
            with self.assertRaises(m.EvidenceError):m.validate_minute(b,c,(0,len(a)*m.MINUTE_US),len(a))
        with self.assertRaises(m.EvidenceError):m.validate_minute(a.astype('float32'),c,(0,len(a)*m.MINUTE_US),len(a))

    def test_calendar_leap_and_partial_day(self):
        self.assertEqual((m.CALENDARS[2024][1]-m.CALENDARS[2024][0])//m.DAY_US,366)
        self.assertEqual((m.CALENDARS[2023][1]-m.CALENDARS[2023][0])//m.DAY_US,365)
        a,c=minute_fixture()
        with self.assertRaises(m.EvidenceError):m.validate_minute(a,c,(0,(len(a)+1440)*m.MINUTE_US),len(a))
        with self.assertRaises(m.EvidenceError):m.daily_telemetry(a[:-1],c)
        d,n=m.daily_telemetry(a,c);d[1,0]+=1
        with self.assertRaises(m.EvidenceError):m.aggregate_daily(d,n)

    def test_funding_sign_and_fee_execution(self):
        self.assertEqual(m.cost_diagnostic('3','4','2')['same_quantity_fee_execution_less_signed_funding_USDT'],'5')
        self.assertEqual(m.cost_diagnostic('3','4','-2')['same_quantity_fee_execution_less_signed_funding_USDT'],'9')
        for x in ('NaN','Infinity',True,None):
            with self.assertRaises(m.EvidenceError):m.cost_diagnostic('1','1',x)
        with self.assertRaises(m.EvidenceError):m.cost_diagnostic('-1','1','0')

    def test_exposure_projection_and_exact_flat(self):
        a,c=minute_fixture();a[0,9]=.00001;a[0,29]=.1;a[0,34]=.1;a[0,35]=.1
        m.validate_minute(a,c,(0,len(a)*m.MINUTE_US),len(a))
        d,n=m.daily_telemetry(a,c);x=m.aggregate_daily(d,n)
        self.assertEqual(x['flat_actual_quantity_minutes'],2879)
        self.assertEqual(x['asset_weights']['BTCUSDT']['absolute_max'],.1)
        self.assertEqual(x['gross_weight_max'],.1)
        a[0,34]=0
        with self.assertRaises(m.EvidenceError):m.validate_minute(a,c,(0,len(a)*m.MINUTE_US),len(a))

    def test_canonical_hash_endian_layout_bit_columns_signed_zero(self):
        a,c=minute_fixture();s=m.canonical_array_signature(a,c)
        for b in (np.asfortranarray(a),a.astype('>f8')):
            self.assertEqual(m.canonical_array_signature(b,c)['values_C_order_SHA256'],s['values_C_order_SHA256'])
        b=a.copy();b[0,0]=np.nextafter(b[0,0],np.inf)
        self.assertNotEqual(m.canonical_array_signature(b,c)['values_C_order_SHA256'],s['values_C_order_SHA256'])
        b=a.copy();b[0,4]=-0.
        self.assertNotEqual(m.canonical_array_signature(b,c)['values_C_order_SHA256'],s['values_C_order_SHA256'])
        cc=c.copy();cc[[0,1]]=cc[[1,0]]
        self.assertNotEqual(m.canonical_array_signature(a,cc)['columns_UTF8_canonical_JSON_SHA256'],s['columns_UTF8_canonical_JSON_SHA256'])
        cc=c.copy();cc[1]=cc[0]
        with self.assertRaises(m.EvidenceError):m.canonical_array_signature(a,cc)

    def test_status_taxonomy_and_contradictions(self):
        for mutation in [lambda r:r.update(status='PARTIAL_SNAPSHOT_PENDING_EXCLUDED'),
                         lambda r:r.update(pending_rows=1),
                         lambda r:r['rows'][0].update(evidence_status='PENDING'),
                         lambda r:r['rows'][0].update(completed_minutes=100),
                         lambda r:r['rows'][0].update(return_taxonomy='MADE_UP'),
                         lambda r:r['rows'][0].update(conditional_settlement_count=1),
                         lambda r:r['rows'][0].update(unpaid_liability_USDT='1'),
                         lambda r:r['rows'][0].update(realized_daily_annualized_volatility=float('nan')),
                         lambda r:r['rows'][0].update(completed_minutes=True),
                         lambda r:r['rows'][0].update(annual_return_fraction='0.02')]:
            r,f=cohort_fixture();mutation(r)
            with self.assertRaises(m.EvidenceError):m.validate_full_cohort(r,f)
        r,f=cohort_fixture();selected=m.validate_full_cohort(r,f)
        self.assertEqual(len(selected),12)
        self.assertEqual({x['strategy'] for x in selected},set(m.FAMILIES))

    def test_dedup_cohort_missing_duplicate_no_family_inflation(self):
        r,f=cohort_fixture();r['rows'][-1]=copy.deepcopy(r['rows'][0])
        with self.assertRaises(m.EvidenceError):m.validate_full_cohort(r,f)
        r,f=cohort_fixture();r['rows'].pop()
        with self.assertRaises(m.EvidenceError):m.validate_full_cohort(r,f)
        r,f=cohort_fixture();f['cells'].pop()
        with self.assertRaises(m.EvidenceError):m.validate_full_cohort(r,f)

    def test_bound_json_and_path(self):
        with tempfile.TemporaryDirectory() as t:
            base=Path(t);p=base/'a.json';p.write_text('{"x":1}')
            self.assertEqual(m.bound_json(base,{'path':'a.json','SHA256':m.file_sha(p)}),{'x':1})
            for path in ('../a.json','/tmp/a.json'):
                with self.assertRaises(m.EvidenceError):m.bound_json(base,{'path':path,'SHA256':'0'*64})
            with self.assertRaises(m.EvidenceError):m.bound_json(base,{'path':'a.json','SHA256':'0'*64})

    def test_lossless_daily_archive(self):
        a,c=minute_fixture();d,n=m.daily_telemetry(a,c)
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'d.npz';np.savez_compressed(p,values=d,columns=n)
            with np.load(p,allow_pickle=False) as z:
                self.assertEqual(m.canonical_array_signature(z['values'],z['columns']),m.canonical_array_signature(d,n))
                self.assertEqual(m.aggregate_daily(z['values'],z['columns']),m.aggregate_daily(d,n))

    def test_future_informed_ratios_and_native_return(self):
        self.assertEqual(m.exact_annual_return('10100'),'0.01')
        self.assertEqual(m.ratio_diagnostic('0.10',.2),'0.5')
        self.assertIsNone(m.ratio_diagnostic('0',0.))
        with self.assertRaises(m.EvidenceError):m.ratio_diagnostic('1',float('nan'))

    def test_no_account_provider_or_financial_runtime_imports(self):
        tree=ast.parse((HERE/'saved_family_risk.py').read_text())
        imports=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):imports.extend(x.name for x in node.names)
            if isinstance(node,ast.ImportFrom):imports.append(node.module)
        self.assertEqual(set(imports)-{'__future__','argparse','datetime','decimal','csv','hashlib','json','pathlib','typing','numpy'},set())

if __name__=='__main__':unittest.main()
