"""Small toy-only finance/transport oracle. No real source or archive is read."""
from pathlib import Path
from decimal import Decimal as D
import argparse,hashlib,importlib,json,sys,tempfile,unittest
import numpy as np

H=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(add_help=False)
parser.add_argument('--module',type=Path,default=H.parent)
parser.add_argument('--roots',type=Path,required=True)
args,remainder=parser.parse_known_args()
sys.argv=[sys.argv[0],*remainder]
MODULE=args.module.resolve()
sys.path.insert(0,str(MODULE))
import pair_launcher as p
if Path(p.__file__).resolve()!=MODULE/'pair_launcher.py':raise RuntimeError('Subject module import shadowing')
ROOTS=json.loads(args.roots.read_text())
PORT,FINE,SIM=p.load_synthetic_engine(ROOTS)
M=p.MINUTE;DAY=p.DAY;S=p.S

def fixture(days=1,weights=None,transport=False,terminal_quote=10000.,events=None):
    """Synthetic dates begin at zero; vectors are not research target archives."""
    if days not in (1,2):raise ValueError('Only one/two toy days permitted')
    clock=np.arange(0,days*DAY,DAY,dtype=np.int64)
    weights=np.asarray(weights if weights is not None else [[.1,0,0,0,-.1]]*days,dtype=np.float64)
    if weights.shape!=(days,5):raise ValueError('Toy shape')
    weights=weights.copy();weights.flags.writeable=False
    market={s:{'open':np.full(days*1440,10.),'close':np.full(days*1440,10.),'mark':np.full(days*1440,10.),'quote_volume':np.full(days*1440,300000.)} for s in S}
    for row in market.values():row['quote_volume'][-61:]=terminal_quote
    records=[dict(symbol=s,close_us=int(t),close=10.) for t in clock for s in S]
    window=dict(start=0,end=days*DAY,symbols=S,daily=p.normalize_daily(records) if transport else PORT.native.pl.DataFrame(records),events=list(events or []))
    if transport:
        def blocks():
            for off in range(0,days*1440,1440):
                yield dict(times=np.arange(off*M,(off+1440)*M,M,dtype=np.int64),market={s:{k:v[off:off+1440] for k,v in row.items()} for s,row in market.items()})
        window['minute_blocks']=blocks
        bound={'control':weights,'candidate':weights,'raw_arrays':{'decision_us':clock}}
        factory=p.target_factory(bound,'control',PORT.native.pl)
    else:
        window['market']=market
        def factory(_daily,decisions,mode):
            np.testing.assert_array_equal(decisions,clock)
            if mode!='LONG_SHORT':raise ValueError('Toy mode')
            rows=[dict(available_us=int(t),symbol=s,target_weight=float(weights[i,j])) for i,t in enumerate(clock) for j,s in enumerate(S)]
            return PORT.native.pl.DataFrame(rows),{'source':'INDEPENDENT_DIRECT_TOY_ROWS'}
    return SIM(window,'LONG_SHORT',PORT.native.COSTS[0],PORT.native.UNITS[0],target_factory=factory,account_factory=FINE)

def finish(sim):
    while sim.cursor<sim.end and sim.stop is None:sim.advance_day()
    return sim

def numeric_and_finance(sim):
    return {'account':sim.account.snapshot(),'funding':sim.funding_journal,'rejections':sim.rejections,'pending':sim.pending,'rows':sim.rows_written,'cursor':sim.cursor,'stop':sim.stop}

class Oracle(unittest.TestCase):
    def test_actual_import_paths_and_original_hashes(self):
        dependency=json.loads((MODULE/'SYNTHETIC_DEPENDENCIES.json').read_text())['files']
        base=Path(ROOTS['common']).resolve().parent
        modules=['quant.execution_contract','quant.perpetual_account','quant.disk','quant.metrics','quant.paths','quant.resources','scripts.investment.resumable_perpetual','scripts.investment.perpetual_directional','scripts.investment.bybit_cost_inputs','scripts.investment.perpetual_closing_exempt_account','scripts.research_v8.funding_price_source_v2','scripts.research_v8.registry','fine_account','freeze_bootstrap']
        for name in modules:
            module=importlib.import_module(name);path=Path(module.__file__).resolve();relative=str(path.relative_to(base))
            self.assertIn(relative,dependency);self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),dependency[relative]['SHA256'])
        self.assertEqual(Path(importlib.import_module('terminal_adapter').__file__).resolve(),(MODULE/'terminal_adapter.py').resolve())
        self.assertIs(SIM.__bases__[0],PORT.native.NativeDailySimulator)
        self.assertEqual(FINE.__module__,'fine_account')

    def test_direct_native_and_record_block_wrapper_exact_parity(self):
        events=[dict(event_us=M+1,symbol='BTCUSDT',raw_rate=.001),dict(event_us=2*M+1,symbol='BTCUSDT',raw_rate=.001),dict(event_us=2*M+1,symbol='DOGEUSDT',raw_rate=.001)]
        direct=finish(fixture(events=events));wrapped=finish(fixture(transport=True,events=events))
        self.assertEqual(numeric_and_finance(direct),numeric_and_finance(wrapped))
        np.testing.assert_array_equal(direct.minute_chunks[0],wrapped.minute_chunks[0])
        self.assertFalse(wrapped.funding_journal[0]['owned'])
        self.assertEqual(D(str(wrapped.funding_journal[1]['signed_funding_USDT'])),D('-.3'))
        self.assertEqual(D(str(wrapped.funding_journal[2]['signed_funding_USDT'])),D('.3'))
        self.assertEqual(tuple(wrapped.account.positions),S)
        self.assertEqual(wrapped.account.config.initial_cash,D('10000'))

    def test_equal_later_targets_do_not_restore_account_equality(self):
        control=fixture(days=2,weights=[[.1,0,0,0,-.1],[.1,0,0,0,-.1]],transport=True,terminal_quote=300000.)
        candidate=fixture(days=2,weights=[[.15,0,0,0,-.15],[.1,0,0,0,-.1]],transport=True,terminal_quote=300000.)
        control.advance_day();candidate.advance_day()
        self.assertNotEqual(control.account.nav(),candidate.account.nav())
        self.assertEqual(control.weights[DAY],candidate.weights[DAY])
        control.advance_day();candidate.advance_day()
        self.assertEqual(control.rows_written,2880);self.assertEqual(candidate.rows_written,2880)
        self.assertTrue(control.result()['summary']['terminal_cash_realized']);self.assertTrue(candidate.result()['summary']['terminal_cash_realized'])
        self.assertNotEqual(control.account.nav(),candidate.account.nav())

    def test_snapshot_and_independent_decimal_bridge(self):
        sim=finish(fixture(transport=True,events=[dict(event_us=2*M+1,symbol='BTCUSDT',raw_rate=.001)]))
        restored=SIM.from_snapshot(sim.snapshot(),sim.window,account_class=FINE)
        self.assertEqual(sim.state_hash(),restored.state_hash())
        self.assertEqual(sim.account.snapshot(),restored.account.snapshot())
        result=sim.result();_,inventory=PORT.native.episodes(result['trades'],S)
        self.assertEqual(inventory,{s:sim.account.positions[s].quantity for s in S})
        bridge=PORT.native.nav_bridge(result['trades'],result['funding'],inventory,result['summary']['terminal_mark_prices'],sim.account.nav())
        self.assertLessEqual(D(bridge['maximum_error_USDT']),D('1e-8'))
        with tempfile.TemporaryDirectory() as tmp:
            pointer=PORT.checkpoint(Path(tmp),sim,{'toy_only':True})
            self.assertEqual(pointer['state_hash'],sim.state_hash());self.assertEqual(pointer['completed_minutes'],1440)

    def test_concrete_target_caps_and_import_shadow_rejection(self):
        start,end=p.inputs.registry()['years']['2023']['calendar'];n=365
        arrays={'decision_us':np.arange(start,end,DAY,dtype=np.int64),'symbol_order':np.array(S,dtype='<U8'),'PRICE_ONLY_CSH':np.zeros((n,5),np.float64),'FUNDING_ADJUSTED_CSH':np.zeros((n,5),np.float64),'annual_covariance':np.zeros((n,5,5),np.float64),'original_daily_admission':np.ones(n,bool),'required_source_not_ready':np.zeros(n,bool),'owning_rank_us':np.full(n,start-DAY,np.int64),'owning_rank_source_known':np.ones(n,bool)}
        for row in ([.31,0,0,0,0],[.2,.2,.2,.01,0],[float('nan'),0,0,0,0]):
            trial={k:v.copy() for k,v in arrays.items()};trial['PRICE_ONLY_CSH'][0]=row
            with self.assertRaisesRegex(p.GateError,'ORIGINAL_TARGET_CAPS'):p.validate_saved_arrays(trial,2023)
        # The exact loader rejects an already cached fine module from another root.
        original=importlib.import_module('fine_account');old=original.__file__
        try:
            original.__file__='/UNTRUSTED_SYNTHETIC_SHADOW/fine_account.py'
            with self.assertRaisesRegex(p.GateError,'FINE_IMPORT_SHADOWING'):p.load_synthetic_engine(ROOTS)
        finally:original.__file__=old

    def test_old_document_pin_preserved_and_current_history_no_go(self):
        old=json.loads((MODULE/'ORIGINAL_TERMINAL_FREEZE.json').read_text())
        name='coin_sma_fine_completion_20261013/terminal_diagnosis/DIAGNOSIS_RECEIPT.json'
        self.assertEqual(old['dependencies_SHA256'][name],'12d0ef8da673ed5d43c8e1ddbfa0f9071efc5cd0a070f90cad937848d7b1b7c3')
        self.assertFalse((Path(ROOTS['workspace'])/name).exists())
        with self.assertRaisesRegex(p.GateError,'WAITING_LAUNCHER_ECONOMIC_REVIEW'):p.require_economic_review(None)
        with self.assertRaisesRegex(p.GateError,'CONTROL_FIRST_REQUIRED'):p.require_parent_go(True,2023,'candidate',[])
        with self.assertRaisesRegex(p.GateError,'SEPARATE_LATER_YEAR_PARENT_GO'):p.require_parent_go(True,2024,'control',[])

if __name__=='__main__':unittest.main(verbosity=2)
