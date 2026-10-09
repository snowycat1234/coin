"""Read-only NumPy reference for the source-bound v2 boundary diagnostic.

No model inference, fit or native account is run. This independent numerical
reference follows the published Torch equations on saved native target weights;
it is not a claim that Torch ran here or that boundary fills are minute-native.
"""
import argparse
from decimal import Decimal as D, localcontext
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np
from pyarrow.parquet import read_table

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from native61 import require, sha, START, END, DAY, SYMBOLS

OBJECTIVE_SHA = 'c438a85a1853f7b8cef02dede194dd3c905d93f74bbb2882b5ae0fd8d50ad040'
FRAGMENT_SHA = 'c13de3125698f1fc350d1435453cbb6e33b7d5873537d7f859c1570344f081bc'
PROTOTYPE_SHA = '46a0ca0b76bf29d50133bdd85b5730f4fd029f05378ce2ef086752b869a8fcab'


def boundary_reference(w, prices, funding):
    """Published full-fill boundary assumptions; stop on any unresolved breach."""
    def cost(delta, mid):
        a = abs(delta)
        return np.array([(.00055*mid*(a+.0008*delta)).sum(),
                         (.0004*mid*a).sum(), (.0004*mid*a).sum()])
    def breached(q, p, nav):
        a = abs(q)*p
        return bool((a > .3*nav+1e-8).any() or a.sum() > .6*nav+1e-8)
    nav, carry, totals, funding_total = [10000.], np.zeros(5), np.zeros(3), 0.
    quantities, held, reductions, charges = [], [], [], []
    for i, weight in enumerate(w):
        q = .99*nav[-1]*weight/prices[i]
        payment = cost(q-carry, prices[i]); after = nav[-1]-payment.sum()
        require(after > 0 and not breached(q, prices[i], after), 'V2 post-fill hard stop')
        f = -float(q@funding[i]); marked = after+float(q@(prices[i+1]-prices[i]))+f
        require(marked > 0, 'V2 insolvency stop')
        carry = q.copy(); totals += payment; funding_total += f
        reduction = 0.
        if breached(carry, prices[i+1], marked):
            a = abs(carry)*prices[i+1]
            scale = min(1., .99*.3*marked/a.max(), .99*.6*marked/a.sum())
            intent = carry*scale
            rc = cost(-np.sign(carry)*abs(carry-intent), prices[i+1])
            reduction = float(rc.sum()); marked -= reduction; totals += rc; carry = intent
            require(marked > 0 and not breached(carry, prices[i+1], marked), 'V2 unresolved required reduction stop')
            reductions.append(dict(day_index=i, scale=scale, attempts=1,
                                   charged_reduction_cost_USDT=reduction))
        charges.append(reduction); quantities.append(q); held.append(carry.copy()); nav.append(marked)
    path = np.array(nav); r = path[1:]/path[:-1]-1
    return dict(nav=path, quantities=np.array(quantities), held=np.array(held),
                reduction_charges=np.array(charges), fees=float(totals[0]),
                spread=float(totals[1]), slippage=float(totals[2]), funding=funding_total,
                charged_reduction_cost=float(sum(charges)), risk_events=reductions,
                utility_sum=float((np.log(path[1:]/path[:-1])-5*np.minimum(r,0)**2).sum()))


def decimal_check(w, prices, funding, reference):
    """Independent 50-digit scalar recomputation of sizing, costs and reduction."""
    def vector(a): return [D(str(float(v))) for v in a]
    def charge(delta, mid):
        return sum(p*(D('.00135')*abs(d)+D('.00000044')*d) for d,p in zip(delta,mid))
    def breach(q, p, equity):
        a = [abs(x)*y for x,y in zip(q,p)]
        return max(a) > D('.3')*equity+D('1e-8') or sum(a) > D('.6')*equity+D('1e-8')
    with localcontext() as ctx:
        ctx.prec = 50
        equity, carry, max_error, reductions = D(10000), [D(0)]*5, D(0), 0
        for i, weight in enumerate(w):
            p, end, f = vector(prices[i]), vector(prices[i+1]), vector(funding[i])
            q = [D('.99')*equity*x/y for x,y in zip(vector(weight),p)]
            after = equity-charge([x-y for x,y in zip(q,carry)],p)
            require(after > 0 and not breach(q,p,after), 'Decimal post-fill stop')
            equity = after+sum(x*(y-z-fu) for x,y,z,fu in zip(q,end,p,f))
            require(equity > 0, 'Decimal insolvency')
            carry = q
            if breach(q,end,equity):
                a = [abs(x)*y for x,y in zip(q,end)]
                scale = min(D(1),D('.297')*equity/max(a),D('.594')*equity/sum(a))
                carry = [x*scale for x in q]
                equity -= charge([x-y for x,y in zip(carry,q)],end); reductions += 1
                require(equity > 0 and not breach(carry,end,equity), 'Decimal unresolved reduction')
            max_error = max(max_error,abs(equity-D(str(reference['nav'][i+1]))))
        require(max_error < D('1e-8') and reductions == len(reference['risk_events']) and all(x==0 for x in carry), 'Decimal reference mismatch')
        return dict(status='PASS_INDEPENDENT_50_DIGIT_BOUNDARY_RECOMPUTATION',
                    maximum_NAV_error_USDT=float(max_error), charged_reduction_events=reductions,
                    terminal_cash_flat=True)


def report(account, bundle, source_root):
    require(sha(bundle/'OBJECTIVE_SOURCE.py') == OBJECTIVE_SHA and sha(source_root/'H1_VALIDATE.npz') == FRAGMENT_SHA and sha(source_root/'prototype.py') == PROTOTYPE_SHA, 'Original bound source/fragment differs')
    manifest = json.loads((bundle/'MANIFEST.json').read_text()); gate = json.loads((account/'REQUEST_GATE.json').read_text())
    require(sha(bundle/'MANIFEST.json') == gate['manifest_sha256'] and sha(bundle/manifest['request_file']) == gate['request_payload_sha256'], 'Account/request identity differs')
    with np.load(source_root/'H1_VALIDATE.npz',allow_pickle=False) as z: a={k:z[k].copy() for k in z.files}
    with np.load(bundle/manifest['request_file'],allow_pickle=False) as z: request=z['desired_expert_budget'].copy()
    require(a['symbol_order'].tolist()==list(SYMBOLS) and np.array_equal(a['decision_us'],np.arange(START,END,DAY,dtype=np.int64)) and np.array_equal(a['global_forced_terminal_day'],np.arange(61)==60), 'Exact original development grid required')
    spec=importlib.util.spec_from_file_location('_source_bound_v2_original_prototype',source_root/'prototype.py'); prototype=importlib.util.module_from_spec(spec);sys.modules[spec.name]=prototype;spec.loader.exec_module(prototype)
    contexts=[]
    for i,t in enumerate(a['decision_us']):
        target=np.zeros((5,5)); eligible=np.zeros(5,dtype=bool)
        target[[0,1,4]]=a['expert_targets'][i,[0,1,4]];eligible[[0,1,4]]=a['expert_eligible'][i,[0,1,4]]
        contexts.append(prototype.Context(int(t),int(t),target,eligible,a['past_returns30'][i],a['market_state13'][i],a['target_available_us'][i]))
    original,_=prototype.mapped_path(request,contexts)
    w=read_table(account/'account/targets.parquet')['target_weight'].to_numpy().reshape(61,5)
    require(hashlib.sha256(w.tobytes()).hexdigest()==gate['fractions_f64_sha256'] and not w[-1].any(), 'Exact saved native mapped path required')
    error=float(abs(original-w).max());require(error < 1e-14, 'Producer original mapper vs native adapter discrepancy')
    result=boundary_reference(w,a['prices'],a['funding_coeff']);audit=decimal_check(w,a['prices'],a['funding_coeff'],result)
    summary=json.loads((account/'account/summary.json').read_text()); nav=result['nav']; net=float(nav[-1]-10000)
    return dict(status='SOURCE_BOUND_V2_NUMPY_DIAGNOSTIC_REFERENCE_NOT_TORCH_EXECUTION_NOT_MINUTE_NATIVE',
                arm=manifest['arm_id'], objective_source_SHA256=OBJECTIVE_SHA, original_prototype_SHA256=PROTOTYPE_SHA,
                original_development_fragment_SHA256=FRAGMENT_SHA, exact_saved_native_target_bytes_SHA256=gate['fractions_f64_sha256'],
                producer_original_mapper_maximum_target_error=error, native_net_PnL_USDT=summary['net_PnL'],
                proxy_net_PnL_USDT=net, native_minus_same_path_proxy_USDT=summary['net_PnL']-net,
                proxy_May_PnL_USDT=float(nav[31]-nav[0]),proxy_June_PnL_USDT=float(nav[-1]-nav[31]),
                proxy_daily_max_drawdown=float((1-nav/np.maximum.accumulate(nav)).max()),
                proxy_fees_USDT=result['fees'],proxy_spread_USDT=result['spread'],proxy_slippage_USDT=result['slippage'],
                proxy_funding_USDT=result['funding'],proxy_charged_risk_reduction_USDT=result['charged_reduction_cost'],
                proxy_risk_events=result['risk_events'],proxy_utility_sum=result['utility_sum'],
                proxy_terminal_cash_realized=bool((result['held'][-1]==0).all()),independent_reference_audit=audit,
                assumptions='DECLARED_FULL_FILL_DIAGNOSTIC_ONLY;continuous_quantity;constant_daily_boundary_mid;original_daily_price_and_funding_coefficients',
                omissions=['minute_latency','intra_interval_marks','actual_quote_volume_capacity','lot_steps','historical_filters','isolated_margin_or_liquidation'],
                models_loaded=0,fits=0,native_wallets_run=0)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--account',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=report(a.account,a.bundle,a.source_root)
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps({k:result[k] for k in ('status','arm','proxy_net_PnL_USDT','native_minus_same_path_proxy_USDT','producer_original_mapper_maximum_target_error','independent_reference_audit')}))
