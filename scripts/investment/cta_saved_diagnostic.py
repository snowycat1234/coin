"""Read-only reuse of saved asset attribution and daily concentration."""
import argparse,json,hashlib
from pathlib import Path
from scripts.investment.turtle_turnover_diagnostic import asset_attribution
from quant.paths import ROOT
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    ap=argparse.ArgumentParser()
    for k in ('actual','output','document'):ap.add_argument('--'+k,type=Path,required=True)
    a=ap.parse_args();r=json.loads(a.actual.read_bytes());assert len(r['cases'])==56 and r['status'].startswith('COMPLETE_')
    rows=[]
    for c in r['cases']:
        assert c['summary']['cost_scenario']['provenance']['fee_source_sha256']=='a406d4bd0e47ff4ae4895fda0a2f2698b5763667d82b22b7f264d6220e27e8bd'
        values=[]
        for kind in ('trades.json','funding.json'):
            e=c['artifacts'][kind];assert sha(e['path'])==e['sha256'];values.append(json.loads(Path(e['path']).read_bytes()))
        assets=asset_attribution(*values,c['summary']);assert set(v['symbol'] for v in assets['assets'])==set(r['protocol']['symbols'])
        positive=sorted((v['net_contribution_USDT'] for v in assets['assets'] if v['net_contribution_USDT']>0),reverse=True)
        rows.append(dict(strategy=c['strategy'],mode=c['mode'],cost=c['cost'],unit=c['unit'],
            scope='FULL122D' if c['summary']['completed_minutes']==175680 else 'STOPPED_PREFIX_NOT_FULL_CALENDAR',
            asset_attribution=assets,daily_concentration=c['summary'].get('daily_net_gain_concentration'),
            positive_asset_top1_share=positive[0]/sum(positive) if positive else None,
            positive_asset_top3_share=sum(positive[:3])/sum(positive) if positive else None))
    out=dict(status='PASS_REUSED_SAVED_ASSET_BRIDGES_AND_ORIGINAL_DAILY_CONCENTRATION',producer_path=str(a.actual),producer_sha256=sha(a.actual),
        helper='scripts/investment/turtle_turnover_diagnostic.py',helper_sha256=sha(ROOT/'scripts/investment/turtle_turnover_diagnostic.py'),
        diagnostic_source_sha256=sha(__file__),new_accounts=0,new_fits=0,rows=rows,
        concentration_note='ACCEPTED positive_days IS EMPTY NOT_MEASURED; ACTUAL daily_net_gain_concentration IS REUSED HERE',
        interpretation='ASSET_PNL_SHARES_WITH_TERMINAL_MARK_AND_FULL10K_DENOMINATOR_NOT_SEPARATE_WALLETS_OR_TRADE_REASON_CAUSALITY')
    with a.output.open('x',encoding='utf-8') as f:json.dump(out,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
    lines=['','## 复用账本诊断：价格、资金费与收益集中度','',
        '|策略|方向|完整性|正收益日前5集中度%|正资产最大集中度%|正资产前三集中度%|',
        '|---|---|---|---:|---:|---:|']
    fmt=lambda x:'UNKNOWN' if x is None else f'{x*100:.2f}'
    for row in rows:
        if row['cost']=='BASE27' and row['unit']=='RAW_AS_PERCENT':
            lines.append('|'+ '|'.join([row['strategy'],row['mode'],row['scope'],
                fmt((row['daily_concentration'] or {}).get('top5_positive_day_share')),fmt(row['positive_asset_top1_share']),fmt(row['positive_asset_top3_share'])])+'|')
    lines+=['','逐币价差毛损益、资金费、费用和执行成本沿用既有asset_attribution参考，所有56账户与summary桥误差<=1e-7。完整NAV包含残仓mark；停止集中度仅前缀，不替代全窗指标。正收益集中度不是净收益比例或因果贡献；逐币贡献共享完整10k分母。完整逐币表见`reports/CTA_LEADERBOARD_DIAGNOSTIC_20261005_V1.json`。']
    with a.document.open('a',encoding='utf-8') as f:f.write('\n'.join(lines)+'\n')
    print(json.dumps(dict(status=out['status'],accounts=56,new_replays=0)))
if __name__=='__main__':main()
