"""Independent Decimal audit of saved rows; never imports source scorers/models."""
import argparse
import csv
import hashlib
import json
import resource
import subprocess
import time
from datetime import datetime, timezone
from decimal import Decimal as D, localcontext
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
TARGET = "7393eee91f37478a24055c8fd1c660ff37eda0ca"
PREFIX = "research/slow-momentum-cpd-cost-feasibility-20261011"
SOURCES = {
    2048: ("research/slow-momentum-cpd-sharpe-continuation-20261011", "2d391cdaa5cfdaade0b7c98b89cd5ae0df2cdeb4f9b1d7308b0160acc866cfac"),
    1024: ("research/slow-momentum-cpd-sharpe-20261011", "a5e48ddc6f739fd26ab05a0e09ba7ed511375de203b6f5015751759586690f3a"),
}
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")
POLICIES = tuple(f"{arm}_{suffix}" for arm in ("trend", "trend_cpd")
                 for suffix in ("seed2001", "seed2002", "seed2003", "ensemble"))
BLOCKS = (("2023-01-01", "2023-07-01", 180), ("2023-07-01", "2024-01-01", 183),
          ("2024-01-01", "2024-05-01", 120))
FEE, SPREAD, SLIP = D('.00055'), D('.0004'), D('.0004')
ZERO, ONE, FIVE = D(0), D(1), D(5)
DAY = 86400000000


def digest(body):
    return hashlib.sha256(body).hexdigest()


def git_body(path):
    return subprocess.check_output(["git", "show", f"{TARGET}:{path}"], cwd=ROOT)


def utc_us(date):
    return int(datetime.fromisoformat(date).replace(tzinfo=timezone.utc).timestamp()*1e6)


def json_write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def policy_position(row, policy):
    if policy.endswith('_ensemble'):
        arm = policy[:-len('_ensemble')]
        return sum((D(row[f'{arm}_seed{s}']) for s in (2001, 2002, 2003)), ZERO)/D(3)
    return D(row[policy])


def fee_on_trade(delta):
    # Explicit buy/sell fill prices, not the production sign-array expression.
    buys, sells = max(delta, ZERO), max(-delta, ZERO)
    return FEE*((ONE+SPREAD+SLIP)*buys+(ONE-SPREAD-SLIP)*sells)


def independent_book(days, policy):
    """Fixed-reference marked notional and scalar trade cashflows; no wallet engine."""
    previous = [ZERO]*5
    buys = sells = gross_total = simple_turnover = entry = terminal = ZERO
    max_product_residual = ZERO
    daily = []
    witnesses = []
    for day_index, records in enumerate(days):
        weights, profits, deltas, absolute, fees = [], [], [], [], []
        for asset, row in enumerate(records):
            pos = policy_position(row, policy)
            if row['eligible'] == '1':
                vol, scaled = D(row['daily_vol']), D(row['scaled_next_return'])
                w = D('.15')*pos/(D(365).sqrt()*vol*FIVE)
                realized = scaled*vol*D(365).sqrt()/D('.15')
                profit = w*realized
                product_reference = pos*scaled/FIVE
                max_product_residual = max(max_product_residual, abs(profit-product_reference))
            else:
                w, realized, profit = ZERO, None, ZERO
            delta = w-previous[asset]
            previous[asset] = w if realized is None else w*(ONE+realized)
            weights.append(w); profits.append(profit); deltas.append(delta)
            absolute.append(abs(delta)); fees.append(fee_on_trade(delta))
            buys += max(delta, ZERO); sells += max(-delta, ZERO)
            if day_index == 0 and row['eligible'] == '1' and not witnesses:
                witnesses.append({'block': row['block'], 'symbol': row['symbol'], 'available_us': int(row['available_us']),
                                  'position': float(pos), 'daily_vol': float(vol), 'scaled_next_return': float(scaled),
                                  'target_fraction': float(w), 'unscaled_simple_return': float(realized),
                                  'captured_reference_fraction': float(profit)})
        gross = sum(profits, ZERO); turnover = sum(absolute, ZERO); fee = sum(fees, ZERO)
        spread, slippage = turnover*SPREAD, turnover*SLIP
        if day_index == 0:
            entry = fee+spread+slippage
        gross_total += gross
        row = {'gross_target': sum((abs(w) for w in weights), ZERO), 'net_target': sum(weights, ZERO),
               'gross_price_proxy': gross, 'drift_trade_turnover': turnover, 'fee': fee,
               'spread': spread, 'slippage': slippage, 'terminal_cost_at_label_end': ZERO,
               'fixed_cost_adjusted_price_proxy': gross-fee-spread-slippage,
               'available_us': int(records[0]['available_us'])}
        daily.append(row)
        # Descriptive turnover is intentionally separated from drift-aware execution turnover.
        if day_index == 0:
            simple_turnover += sum((abs(w) for w in weights), ZERO)
        else:
            prior_weights = daily[-2]['weights']
            simple_turnover += sum((abs(w-old) for w, old in zip(weights, prior_weights, strict=True)), ZERO)
        row['weights'] = weights
    closing = [-value for value in previous]
    for delta in closing:
        buys += max(delta, ZERO); sells += max(-delta, ZERO)
        terminal += abs(delta)*(SPREAD+SLIP)+fee_on_trade(delta)
    simple_turnover += sum((abs(w) for w in daily[-1]['weights']), ZERO)
    daily[-1]['terminal_cost_at_label_end'] = terminal
    daily[-1]['fixed_cost_adjusted_price_proxy'] -= terminal
    turnover = buys+sells
    fee = FEE*((ONE+SPREAD+SLIP)*buys+(ONE-SPREAD-SLIP)*sells)
    spread, slippage = SPREAD*turnover, SLIP*turnover
    cost = fee+spread+slippage
    closed_flow_residual = buys-sells+gross_total
    linear_cost_residual = cost-(FEE+SPREAD+SLIP)*turnover+FEE*(SPREAD+SLIP)*gross_total
    summary = {'days': len(days), 'gross_price_proxy': gross_total, 'fixed_cost_total': cost,
               'fixed_cost_adjusted_price_proxy': gross_total-cost, 'drift_trade_turnover': turnover,
               'descriptive_target_turnover': simple_turnover, 'fee': fee, 'half_spread': spread,
               'slippage': slippage, 'entry_cost': entry, 'terminal_cost': terminal,
               'break_even_nominal_per_side_bps': gross_total/turnover*D(10000) if turnover else None,
               'gross_target_mean': sum((d['gross_target'] for d in daily), ZERO)/D(len(days)),
               'gross_target_max': max(d['gross_target'] for d in daily),
               'abs_target_max': max(abs(w) for d in daily for w in d['weights'])}
    return summary, daily, witnesses, max(abs(closed_flow_residual), abs(linear_cost_residual), max_product_residual)


def aggregate(parts):
    summable = ['days', 'gross_price_proxy', 'fixed_cost_total', 'fixed_cost_adjusted_price_proxy',
                'drift_trade_turnover', 'descriptive_target_turnover', 'fee', 'half_spread', 'slippage', 'entry_cost', 'terminal_cost']
    out = {k: sum((part[k] for part in parts), ZERO) for k in summable}
    out['break_even_nominal_per_side_bps'] = out['gross_price_proxy']/out['drift_trade_turnover']*D(10000)
    out['gross_target_mean'] = sum((part['gross_target_mean']*part['days'] for part in parts), ZERO)/out['days']
    out['gross_target_max'] = max(part['gross_target_max'] for part in parts)
    out['abs_target_max'] = max(part['abs_target_max'] for part in parts)
    return out


def float_values(value):
    if isinstance(value, D):
        return float(value)
    if isinstance(value, dict):
        return {k: float_values(v) for k, v in value.items()}
    if isinstance(value, list):
        return [float_values(v) for v in value]
    return value


def review(state):
    source_paths = ['modules/slow_momentum_cpd/'+name for name in
                    ['core.py', 'sharpe.py', 'continuation.py', 'cost_feasibility.py', 'audit_cost_feasibility.py']]
    source_paths += [PREFIX+'/'+name for name in ['PROTOCOL.json', 'README.md', 'FINAL_REVIEW.md', 'results/RESULT.json',
                                                 'results/HISTORY_REFERENCE.json', 'results/DAILY.csv']]
    source_paths += [prefix+'/results/'+name for prefix, _ in SOURCES.values() for name in ['POSITIONS.csv', 'RESULT.json']]
    identities = {}
    for path in source_paths:
        body = (ROOT/path).read_bytes()
        if body != git_body(path):
            raise ValueError('Target source/artifact changed: '+path)
        identities[path] = {'bytes': len(body), 'sha256': digest(body)}
    config_path = 'research/recover-frozen-runner-20261009/FINANCIAL_CONFIG.json'
    config_body = git_body(config_path)
    if digest(config_body) != '84cb7726bbd38a700cc9b31c456b5b8bf5f93d3b4948293bd05ea6ea19cafd68':
        raise ValueError('Frozen cost config differs')
    cost = json.loads(config_body)['cost']
    if not (D(cost['fee_rate_fraction']) == FEE and D(cost['half_spread_bps'])/D(10000) == SPREAD and
            D(cost['slippage_bps'])/D(10000) == SLIP and cost['second_debit_execution_cost'] is False):
        raise ValueError('Frozen fixed costs differ')
    identities[config_path] = {'bytes': len(config_body), 'sha256': digest(config_body), 'scope_used': 'cost fields only, no market data'}
    daily_saved = list(csv.DictReader((ROOT/PREFIX/'results/DAILY.csv').open()))
    saved_lookup = {(row['policy'], row['block'], int(row['available_us'])): row for row in daily_saved}
    if len(daily_saved) != 3864 or len(saved_lookup) != 3864:
        raise ValueError('daily row count')
    maximum_residual, decimal_identity_residual, checks = 0., ZERO, 0
    outputs = {}
    for checkpoint, (prefix, identity) in SOURCES.items():
        path = ROOT/prefix/'results/POSITIONS.csv'
        if digest(path.read_bytes()) != identity:
            raise ValueError('saved position identity')
        rows = list(csv.DictReader(path.open()))
        if len(rows) != 2415:
            raise ValueError('saved full asset/day axis')
        evidence = json.loads((ROOT/PREFIX/'results'/('RESULT.json' if checkpoint == 2048 else 'HISTORY_REFERENCE.json')).read_text())
        forecast = json.loads((ROOT/prefix/'results/RESULT.json').read_text())
        policies, stats, witnesses = {}, {}, []
        eligibility, row_offset, raw_abs = [], 0, []
        for start, end, count in BLOCKS:
            selected = rows[row_offset:row_offset+count*5]; row_offset += count*5
            eligibility.append({'block': start, 'days': count, 'eligible_assets': sum(row['eligible']=='1' for row in selected),
                                'cash_assets': sum(row['eligible']=='0' for row in selected),
                                'missing_eligible_vol_or_return': sum(row['eligible']=='1' and (not row['daily_vol'] or not row['scaled_next_return']) for row in selected)})
            for i, row in enumerate(selected):
                if (row['symbol'] != SYMBOLS[i%5] or row['block'] != start or
                        int(row['available_us']) != utc_us(start)+(i//5)*DAY or
                        int(row['label_end_us']) != int(row['available_us'])+DAY or
                        int(row['label_end_us']) >= utc_us(end)):
                    raise ValueError('date/asset order or maturity')
                if row['eligible'] not in ('0', '1'):
                    raise ValueError('invalid eligibility')
                for policy in POLICIES:
                    pos = D(row[policy])
                    if not pos.is_finite() or abs(pos)>ONE or (row['eligible']=='0' and pos != ZERO):
                        raise ValueError('invalid or masked output')
                for arm in ('trend', 'trend_cpd'):
                    if abs(D(row[arm+'_ensemble'])-policy_position(row, arm+'_ensemble')) > D('1e-15'):
                        raise ValueError('three-seed mean differs')
                if row['eligible']=='1':
                    vol, scaled = D(row['daily_vol']), D(row['scaled_next_return'])
                    if not vol.is_finite() or vol<=ZERO or not scaled.is_finite():
                        raise ValueError('missing eligible current risk or outcome')
                    raw_abs.append(abs(policy_position(row, 'trend_cpd_ensemble')))
            days = [selected[i:i+5] for i in range(0, len(selected), 5)]
            for policy in POLICIES:
                summary, daily, sample, residual = independent_book(days, policy)
                decimal_identity_residual = max(decimal_identity_residual, residual)
                original = next(b for b in evidence['blocks'] if b['start']==start)['policies'][policy]
                for key, value in summary.items():
                    if value is None:
                        continue
                    err = abs(float(value)-original[key]); maximum_residual=max(maximum_residual,err); checks += 1
                    if err>1e-11:
                        raise ValueError(f'block scalar mismatch {checkpoint}/{start}/{policy}/{key}: {err}')
                policies.setdefault(policy, []).append(summary)
                stats.setdefault(policy, []).extend(d['gross_price_proxy'] for d in daily)
                if checkpoint == 2048:
                    for d in daily:
                        original = saved_lookup[(policy, start, d['available_us'])]
                        for key in ['gross_target', 'net_target', 'gross_price_proxy', 'drift_trade_turnover', 'fee', 'spread',
                                    'slippage', 'terminal_cost_at_label_end', 'fixed_cost_adjusted_price_proxy']:
                            err = abs(float(d[key])-float(original[key])); maximum_residual=max(maximum_residual,err); checks += 1
                            if err>1e-11:
                                raise ValueError('saved daily mismatch')
                if policy == 'trend_cpd_ensemble':
                    witnesses.extend(sample)
        summaries = {policy: aggregate(parts) for policy, parts in policies.items()}
        for policy, summary in summaries.items():
            for key, value in summary.items():
                err=abs(float(value)-evidence['aggregate'][policy][key]); maximum_residual=max(maximum_residual,err); checks += 1
                if err>1e-11:
                    raise ValueError('aggregate mismatch')
        gross_stats = {}
        for arm in ('trend', 'trend_cpd'):
            values = stats[arm+'_ensemble']; mean=sum(values,ZERO)/D(len(values))
            variance=sum(((v-mean)**2 for v in values),ZERO)/D(len(values)); std=variance.sqrt()
            s={'days':len(values),'mean_daily_proxy_return':float(mean),'daily_proxy_std':float(std),
               'annual_proxy_vol':float(std*D(365).sqrt()),'sharpe':float(D(365).sqrt()*mean/std)}
            for key,value in s.items():
                err=abs(value-forecast['aggregate'][arm][key]); maximum_residual=max(maximum_residual,err); checks += 1
                if err>1e-11:
                    raise ValueError('original daily Sharpe/stat mismatch')
            seed_gross=sum((summaries[f'{arm}_seed{seed}']['gross_price_proxy'] for seed in (2001,2002,2003)),ZERO)/D(3)
            if abs(seed_gross-summaries[arm+'_ensemble']['gross_price_proxy']) > D('1e-30'):
                raise ValueError('second seed mean detected')
            gross_stats[arm]=s
        outputs[str(checkpoint)]={'all_policies':float_values(summaries),'gross_daily_statistics':gross_stats,
                                  'eligibility':eligibility,'CPD_raw_signal_abs_mean_eligible':float(sum(raw_abs,ZERO)/D(len(raw_abs))),
                                  'CPD_raw_signal_abs_max_eligible':float(max(raw_abs)), 'unit_witnesses':witnesses}
    for path, spec in identities.items():
        body=git_body(path)
        if digest(body)!=spec['sha256']:
            raise ValueError('source identity changed during review')
    result={'status':'PASS_NO_SCALING_OR_DUPLICATE_NORMALIZATION_DEFECT_FOUND', 'target_commit':TARGET,
            'fits':0,'new_model_inferences':0,'native_wallets':0,'market_downloads':0,'source_artifacts_modified':False,
            'checkpoint_results':outputs,'independent_numeric_checks':checks,'saved_rows_per_checkpoint':2415,
            'primary_daily_rows_checked':3864,'maximum_float_reference_residual':maximum_residual,
            'maximum_decimal_product_trade_cost_identity_residual':str(decimal_identity_residual),
            'units':{'annual_vol_parameter':.15,'annual_days':365,'daily_rate_exact_reference':str(D('.15')/D(365).sqrt()),
                     'return':'single-day simple close-to-close','vol':'causal daily simple-return EWMA std',
                     'model_output':'dimensionless tanh risk signal, not final capital fraction','target':'daily_rate * signal / daily_sigma / fixed5',
                     'ensemble':'exactly one equal3seed mean BEFORE targets and turnover','gross':'sum signal*scaled_outcome/5 = sum target*simple_return',
                     'cost':'13.5bp per L1 traded side with fee-on-fill cross term; entry/exit both included',
                     'Sharpe':'sqrt365*daily_mean/population_daily_std; no scored epsilon or averaged block/seed Sharpe'},
            'cost_identity':'C=(.00055+.0004+.0004)*T-.00055*(.0004+.0004)*G after each block is closed',
            'limits':['static-reference additive price proxy, not NAV or compounded return','full completed-close fills exclude real latency/lot/minimum/capacity effects',
                      'funding not measured, not known zero','15pct parameter does not force15pct realized portfolio vol','pooled training Sharpe differs from calendar portfolio objective; not a duplicate scaling defect'],
            'source_sha256':identities,'protocol_sha256':digest((HERE/'PROTOCOL.json').read_bytes()),'review_source_sha256':digest(Path(__file__).read_bytes())}
    json_write(state/'REVIEW_RESULT.json',result)
    print(json.dumps({'status':result['status'],'checks':checks,'maximum_residual':maximum_residual,'primary_CPD':outputs['2048']['all_policies']['trend_cpd_ensemble'],
                      'primary_CPD_gross_statistics':outputs['2048']['gross_daily_statistics']['trend_cpd'],'new_models':0}))


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--state',type=Path,required=True); args=parser.parse_args()
    args.state.mkdir(parents=True,exist_ok=False)
    started=time.monotonic(); receipt={'stage':'STARTED','started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'fits':0,'new_inference':0,'wallets':0}
    try:
        with localcontext() as context:
            context.prec=40
            review(args.state)
        if sum(p.stat().st_size for p in args.state.iterdir()) > 2000000:
            raise ValueError('review output budget exceeded')
        receipt['stage']='SUCCESS'
    except BaseException as error:
        receipt.update(stage='FAILED',error_type=type(error).__name__,error=str(error)); raise
    finally:
        receipt.update(elapsed_seconds=time.monotonic()-started,max_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        json_write(args.state/'ATTEMPT.json',receipt)


if __name__=='__main__':
    main()
