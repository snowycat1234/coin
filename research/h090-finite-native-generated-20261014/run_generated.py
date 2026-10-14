"""Small generated native journals. No file input or historical runner argument."""
from pathlib import Path
import argparse,json
import numpy as np
from generated_fixtures import *
from native_control import original_control


def export(directory):
    directory=Path(directory)
    directory.mkdir(parents=False,exist_ok=False)
    cases=[]
    original=make_generated(original_recipe=True)
    cases.append(('ORIGINAL60_UNLAGGED_CSH_GENERATED',finish(original_control(original[0],BASE27,UNIT,target_factory=original[1]))))
    cases.append(('H090_UNLAGGED_CSH_GENERATED',finish(new_h090(original))))
    for cost in (BASE27,STRESS43):
        cases.append(('H090_ADMITTED90_'+cost['id'],finish(new_h090(make_generated(),cost=cost))))
    for terminal_quote in (50000.,0.):
        quote=np.full(1440,10000000.);quote[-61:]=terminal_quote
        name='H090_TERMINAL60_LATE_PAID_PARTIALS' if terminal_quote else 'H090_TERMINAL60_UNPAID_RESIDUAL'
        cases.append((name,finish(new_h090(make_generated(weights=[.2,0,0,0,0],quote=quote)))))
    def delayed(source):source['daily_bars'][-1]['available_us']=START+DAY+1
    gap=make_generated(days=2,weights=[.2,-.1,0,0,0],source_mutations={START+DAY:delayed})
    cases.append(('H090_SOURCE_INVALID_PAID_REDUCTIONS',finish(new_h090(gap))))
    quote=np.full(2880,10000000.);quote[1439:]=0.
    gap=make_generated(days=2,weights=[.2,0,0,0,0],quote=quote,source_mutations={START+DAY:delayed})
    cases.append(('H090_SOURCE_INVALID_UNPAID_INVENTORY',finish(new_h090(gap))))
    summary=[]
    for name,sim in cases:
        result=sim.result()
        report={'fixture':name,'scope':'GENERATED_ONLY_NOT_RETURN_RESEARCH',
                'history_status':'NO_GO','summary':result['summary'],
                'targets':sim.target_rows,'trades':sim.account.trades,
                'funding':sim.funding_journal,'rejections':sim.rejections,
                'breaches':sim.breaches,'exact_account_snapshot':sim.account.snapshot(),
                'full_restore_certified':False,
                'terminal_signal_us':sim.terminal_signal_us}
        if hasattr(sim,'policy_events'):report['h090_policy_events']=sim.policy_events
        (directory/(name+'.json')).write_text(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+'\n')
        summary.append({'fixture':name,'final_exact_NAV':str(sim.account.nav()),
            'trade_legs':len(sim.account.trades),'completed_minutes':sim.rows_written,
            'stop_us':sim.stop,'completion':sim.completion,
            'terminal_cash_realized':all(p.quantity==0 for p in sim.account.positions.values()),
            'remaining_actual_quantities':{s:str(p.quantity) for s,p in sim.account.positions.items() if p.quantity},
            'increase_capital_rejections':sum(r.get('reason')=='SHARED_CAPITAL_OR_RESERVE_CAP' for r in sim.rejections),
            'historical_status':'NO_GO'})
    (directory/'SUMMARY.json').write_text(json.dumps(summary,indent=2,allow_nan=False)+'\n')
    return summary

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--receipt-dir',required=True)
    a=p.parse_args()
    print(json.dumps(export(a.receipt_dir),indent=2,allow_nan=False))
