#!/usr/bin/env python3
"""Independent Decimal/end-point checks of generated results; no strategy code."""
import json
from decimal import Decimal, localcontext
from pathlib import Path
import resource
import signal
from datetime import datetime, timezone
import time

root=Path(__file__).resolve().parent
resource.setrlimit(resource.RLIMIT_CPU,(120,120))
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
signal.alarm(120)
start=time.monotonic()
computed=json.loads((root/'results/RESULTS.json').read_text())
checks=[]
max_difference=0.0
def near(got, want, name):
    global max_difference
    difference=abs(float(got)-float(want))
    max_difference=max(max_difference,difference)
    assert difference < 1e-10, (name,got,want,difference)
    checks.append(name)

with localcontext() as context:
    context.prec=50
    for key in ('h090','csh'):
        raw=json.loads((root/f'inputs/{key}_DAILY.json').read_text(),parse_float=Decimal)
        increments=[Decimal(str(x['net_increment_USDT'])) for x in raw]
        equity=[Decimal(10000)]
        for x in increments: equity.append(equity[-1]+x)
        logs=[(equity[i+1]/equity[i]).ln() for i in range(365)]
        annual=(equity[-1]/equity[0]).ln()
        r=computed['runs'][key]
        near(r['annual_return'],equity[-1]/equity[0]-1,key+' annual')
        months=[]
        index=0
        for month in range(1,13):
            end=next((i for i in range(index,365) if datetime.fromtimestamp(raw[i]['start_us']/1e6,timezone.utc).month!=month),365)
            ret=equity[end]/equity[index]-1
            log=(equity[end]/equity[index]).ln()
            near(r['months'][month-1]['compounded_return'],ret,key+f' month {month}')
            near(r['months'][month-1]['share_of_annual_net_log_return'],log/annual,key+f' month log share {month}')
            months.append((ret,log,index,end))
            index=end
        best=max(months,key=lambda x:x[0])
        near(r['leave_best_month_out']['return_with_best_month_daily_returns_replaced_by_zero'],(annual-best[1]).exp()-1,key+' best month deletion')
        for window in (30,90):
            worst,index=min((equity[i+window]/equity[i]-1,i) for i in range(366-window))
            near(r['worst_rolling'][str(window)]['return'],worst,key+f' rolling {window}')
            assert r['worst_rolling'][str(window)]['start_utc']==datetime.fromtimestamp(raw[index]['start_us']/1e6,timezone.utc).isoformat().replace('+00:00','Z')
        ranked=sorted(range(365),key=lambda i:(-logs[i],i))
        positive=sum(x for x in logs if x>0)
        for n in (5,10):
            total=sum(logs[i] for i in ranked[:n])
            top=r['top_daily_log_returns'][str(n)]
            near(top['share_of_annual_net_log_return'],total/annual,key+f' top {n} net share')
            near(top['share_of_all_positive_daily_log_returns'],total/positive,key+f' top {n} positive share')
            near(top['return_with_top_days_daily_returns_replaced_by_zero'],(annual-total).exp()-1,key+f' top {n} deletion')
            actual=[datetime.fromtimestamp(raw[i]['start_us']/1e6,timezone.utc).date().isoformat() for i in ranked[:n]]
            assert actual==[x['date_utc'] for x in top['observations']]

receipt={'status':'PASS','method':'50-digit Decimal cumulative NAV; independent endpoint ratios, logarithms and exhaustive windows',
         'checks':checks,'numeric_checks':len(checks),'maximum_absolute_numeric_difference':max_difference,
         'wall_seconds':time.monotonic()-start,'max_RSS_bytes_linux':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
         'finished_utc':datetime.now(timezone.utc).isoformat(),
         'limits':{'CPU_seconds':120,'wall_seconds':120,'address_space_bytes':2*1024**3}}
(root/'DECIMAL_CROSSCHECK.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
