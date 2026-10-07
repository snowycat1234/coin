"""Read-only common-input, actual protective-fill and cash reconciliation."""
import argparse,gzip,hashlib,json,math,time
from decimal import Decimal as D
from pathlib import Path
from modules.transformer_v3.market_binding import verify_binding
from scripts.research.run_public_momentum import sha,save,ROOT


def near(a,b):
    assert math.isfinite(a) and math.isfinite(b) and math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-7),(a,b)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--result',type=Path,required=True);ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args();began=time.monotonic();r=json.loads(a.result.read_text());p=r['protocol']
    protocol=ROOT/'protocols/SHORT_COLLATERAL_HALF_20261008.json'
    assert sha(protocol)==r['protocol_sha256'] and json.loads(protocol.read_text())==p
    assert r['status']=='COMPLETE_ONE_SHORT_COLLATERAL_PROTECTION' and r['new_wallets']==10 and r['new_fits']==0
    prior=ROOT/'reports/CSMOM_ABSOLUTE_SHORT_20261008.json';assert sha(prior)==p['input_reports'][str(prior.relative_to(ROOT))]
    previous=json.loads(prior.read_text());key=lambda x:(x['window'],x['funding_scale'])
    controls={key(x):x for x in previous['reused_controls']};old={key(x):x for x in r['reused_controls']};new={key(x):x for x in r['cases']}
    assert set(controls)==set(old)==set(new) and len(old)==10
    for k in old:assert {f:v for f,v in controls[k].items() if f!='kind'}=={f:v for f,v in old[k].items() if f!='kind'}
    checked_bindings=set();cells=[]
    for k,row in new.items():
        assert sha(row['result_path'])==row['result_sha256'] and sha(old[k]['result_path'])==old[k]['result_sha256']
        current=json.loads(Path(row['result_path']).read_text());before=json.loads(Path(old[k]['result_path']).read_text())
        c,b=current['task'],before['task']
        for field in ('target_path','target_sha256','window','funding_scale','work','symbols','profile'):
            if field=='symbols':assert current['summary']['symbols']==before['summary']['symbols'];continue
            assert c[field]==b[field],field
        assert c['native_market_binding_sha256']==b['native_market_binding_sha256'],'Old/new market identity differs'
        for t in (b,c):
            path=t['native_market_binding_path'];expected=t['native_market_binding_sha256']
            assert sha(path)==expected
            if expected not in checked_bindings:
                bound=verify_binding(path,expected)
                assert bound['window']==t['window'] and bound['symbols']==p['symbols'] and bound['work']==t['work']
                checked_bindings.add(expected)
        assert sha(c['target_path'])==c['target_sha256']
        def artifact(name):
            entry=current['artifacts'][name+'.json'];assert sha(entry['path'])==entry['sha256']
            raw=gzip.decompress(Path(entry['path']).read_bytes());assert hashlib.sha256(raw).hexdigest()==entry['uncompressed_sha256']
            return json.loads(raw)
        trades=artifact('trades');journal=artifact('protection_journal')
        actual={(x['symbol'],x['event_us'],x['signal_us'],x['quantity_before'],x['quantity_after']):x for x in trades}
        protective=[x for x in journal if x['kind']=='PROTECTIVE_FILL'];triggers=[x for x in journal if x['kind']=='OBSERVED_SHORT_COLLATERAL_FLOOR']
        for event in triggers:
            assert D(event['quantity'])<0 and 0<D(event['isolated_equity'])<=D('.5')*D(event['isolated_collateral'])
        for f in protective:
            x=actual[f['symbol'],f['event_us'],f['signal_us'],f['quantity_before'],f['quantity_after']]
            assert x['side']=='BUY' and x['leg']=='CLOSE' and x['quantity_before']<0 and x['quantity_after']<=0
            assert x['event_us']>=x['signal_us']+60_000_001
            assert any(e['symbol']==f['symbol'] and e['event_us']<=f['signal_us'] for e in triggers)
            near(f['fees'],x['fee_USDT_mid']);near(f['execution_cost'],x['execution_cost'])
        for role,item in (('old',old[k]),('new',row)):
            days=next(w['days'] for w in p['windows'] if w['id']==k[0])
            metrics=item['daily_metrics']
            near(metrics['initial_nav'],p['capital'])
            near(metrics['final_nav']-p['capital'],item['net_PnL'])
            near(metrics['total_return'],item['net_PnL']/p['capital'])
            assert metrics['days']==days and item['complete_minutes']==days*1440
            near(item['gross_PnL']-item['fees']-item['execution_cost']+item['funding'],item['net_PnL'])
            legs=item['contributions']
            for name,total in (('gross','gross_PnL'),('fees','fees'),('execution_cost','execution_cost'),('funding','funding'),('net_contribution','net_PnL')):
                near(sum(v[name] for v in legs.values()),item[total])
            assert item['terminal_cash_realized'] and item['audit_status'].startswith('PASS_')
        d=next(x for x in r['contrasts'] if key(x)==k)
        near(d['net_increment'],row['net_PnL']-old[k]['net_PnL'])
        near(d['SHORT_increment'],row['contributions']['SHORT']['net_contribution']-old[k]['contributions']['SHORT']['net_contribution'])
        near(d['LONG_increment'],row['contributions']['LONG']['net_contribution']-old[k]['contributions']['LONG']['net_contribution'])
        near(d['MDD_change'],row['minute_MDD']-old[k]['minute_MDD'])
        near(d['vol_change'],row['daily_metrics']['annual_volatility']-old[k]['daily_metrics']['annual_volatility'])
        near(d['cost_change'],row['fees']+row['execution_cost']-old[k]['fees']-old[k]['execution_cost'])
        near(d['turnover_change'],row['turnover']-old[k]['turnover'])
        cells.append(dict(window=k[0],funding_scale=k[1],net_PnL=row['net_PnL'],net_increment=d['net_increment'],
            protective_triggers=len(triggers),actual_protective_fills=len(protective),common_native_input_sha256=c['native_market_binding_sha256']))
    checks=dict(no_liquidation=all(x['liquidations']==0 for x in new.values()),
        all_vol_at_most12pct=all(x['daily_metrics']['annual_volatility']<=.12 for x in new.values()),
        all_MDD_at_most12pct=all(x['minute_MDD']<=.12 for x in new.values()),
        each_pair_net_or_DD_improves=all(x['net_increment']>=-1e-7 or x['MDD_change']<=-.0001 for x in r['contrasts']),
        any_material_net_or_DD_improvement=any(x['net_increment']>=10 or x['MDD_change']<=-.001 for x in r['contrasts']),
        both2025_stages_SHORT_positive=all(x['contributions']['SHORT']['net_contribution']>0 for x in new.values() if x['window'].startswith(('fold3','fold4'))))
    assert checks==r['checks']
    decision='RETAIN_TAIL_PROTECTION_FOR_INDEPENDENT_VALIDATION' if all(checks.values()) else 'PAUSE_EXACT_TAIL_PROTECTION_RECIPE'
    assert decision==r['decision']
    out=dict(status='PASS_COMMON_INPUT_ACTUAL_PROTECTION_AND_SUMMARY_BRIDGES',result_sha256=sha(a.result),source_sha256=sha(__file__),
        cells=cells,old_new_same_market_inputs=10,old_new_exact_target_identity=10,financial_summaries=20,
        frozen_gate_recalculation=checks,decision=decision,complete_capital_and_minute_paths=20,
        native_bindings_verified=len(checked_bindings),qualification='NONE_CASH',new_wallets=0,new_fits=0,elapsed_seconds=time.monotonic()-began,
        limitations=['Post-run input identity/actual protective-fill and summary review, not another wallet or independently simulated strategy.',
            'Native minute cash/risk audit remains the existing bound independent auditor. This reviewer does not replay every order or independently fit risk models.',
            'Seen development, conditional funding units/MMR/filters and cross-venue proxy remain; stops do not guarantee survival or investment alpha.'])
    save(a.output,out);print(json.dumps(dict(status=out['status'],cells=10,seconds=out['elapsed_seconds'])),flush=True)


if __name__=='__main__':main()
