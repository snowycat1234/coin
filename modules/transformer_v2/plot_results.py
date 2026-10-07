"""Standalone economic evidence matrix; descriptive only, after final decision."""
import argparse,json
from pathlib import Path
import numpy as np
from .train import sha

FAMILIES=('TRANSFORMER_SHARED','CROSS_ASSET_UTILITY','CROSS_ASSET_MULTITASK','PATCH_CROSS_ASSET_MULTITASK')
BASES=('BASE_CASH','BASE_HOLD','BASE_SMA200_SIGNED','BASE_STATIC_DIRECTION3','OLD_FROZEN_TRANSFORMER_SHARED','PER_ASSET_XGB')

def matrix(dev,locked_rows,scale,windows):
    keys=[(b,'DIRECTIONAL') for b in BASES]+[(f,m) for f in FAMILIES for m in ('DIRECTIONAL','NEUTRAL','COMBINED')]
    values=np.full((len(keys),len(windows)),np.nan)
    for row in dev['rows']+locked_rows:
        if row['funding_scale']!=scale or row['noncausal'] or row['window'] not in windows:continue
        if row['family'] in FAMILIES and str(row['seed'])!='ENSEMBLE':continue
        key=(row['family'],row['mapping'])
        if key in keys and row['full_calendar_and_paid_cash'] and row['net_return_percent'] is not None:
            values[keys.index(key),windows.index(row['window'])]=row['net_return_percent']
    return keys,values

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);a=p.parse_args();state=Path(a.state)
    decision=json.loads((state/'TRANSFORMER_V2_FINAL_DECISION.json').read_text());dev=json.loads((state/'TRANSFORMER_V2_DEV_RESULTS.json').read_text())
    assert decision['development_results_sha256']==sha(state/'TRANSFORMER_V2_DEV_RESULTS.json')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import TwoSlopeNorm
    windows=sorted({r['window'] for r in dev['rows']})+['LOCKED_20260301_20260831']
    grids=[matrix(dev,decision['locked_rows'],scale,windows) for scale in (1.,.01)]
    finite=np.concatenate([v[np.isfinite(v)] for _,v in grids]);limit=max(1.,float(abs(finite).max()) if len(finite) else 1.)
    fig,axes=plt.subplots(1,2,figsize=(16,10),layout='constrained',sharey=True)
    names=dict(TRANSFORMER_SHARED='Shared / new 3 seeds',CROSS_ASSET_UTILITY='Cross-asset utility',CROSS_ASSET_MULTITASK='Cross-asset multitask',PATCH_CROSS_ASSET_MULTITASK='8-day patch multitask',
               BASE_CASH='CASH',BASE_HOLD='HOLD',BASE_SMA200_SIGNED='SMA200 signed',BASE_STATIC_DIRECTION3='Static .5/.25/.25',OLD_FROZEN_TRANSFORMER_SHARED='Old frozen Transformer',PER_ASSET_XGB='Old frozen XGBoost')
    cmap=plt.get_cmap('RdYlGn').copy();cmap.set_bad('#dddddd')
    for ax,scale,(keys,values) in zip(axes,(1.,.01),grids):
        image=ax.imshow(np.ma.masked_invalid(values),aspect='auto',cmap=cmap,norm=TwoSlopeNorm(vmin=-limit,vcenter=0.,vmax=limit))
        ax.set_title(f'Conditional funding scale {scale}: full-capital NET %')
        ax.set_xticks(range(len(windows)),[f'DEV {i+1}' if i<len(windows)-1 else 'LOCKED\n184 days' for i in range(len(windows))])
        ax.set_yticks(range(len(keys)),[names[f]+(' / '+m[:3] if f in FAMILIES else '') for f,m in keys])
        ax.axvline(len(windows)-1.5,color='#154c79',linewidth=2)
        chosen=(dev['chosen']['family'],dev['chosen']['mapping'])
        if chosen in keys:ax.axhspan(keys.index(chosen)-.48,keys.index(chosen)+.48,fill=False,edgecolor='black',linewidth=1.5)
        for i in range(values.shape[0]):
            for j in range(values.shape[1]):ax.text(j,i,f'{values[i,j]:.2f}' if np.isfinite(values[i,j]) else 'N/E',ha='center',va='center',fontsize=7.5)
    fig.colorbar(image,ax=axes,shrink=.75,label='NET return on independent initial 10k USDT (%)')
    fig.suptitle('Frozen candidate outlined; grey = NOT EVALUABLE\nDevelopment reset wallets are not additive APR. Locked requires one complete continuous 184-day wallet.',fontsize=12)
    fig.savefig(state/'TRANSFORMER_V2_ECONOMIC_HEATMAP.png',dpi=150);plt.close(fig)
    print('Saved standalone economic matrix; no selection, gate or result changed')

if __name__=='__main__':main()
