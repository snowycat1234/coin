import json,sys
from pathlib import Path
root=Path('/workspace/coin-tail-risk');here=root/'research/portfolio-risk-budget-20261012';sys.path.insert(0,str(here));import archive as a
key,arm=sys.argv[1:];state=Path('/workspace/portfolio-risk-budget-state')/('OBSERVED_'+key)/arm;dest=here/'summary'/key/arm;assert not dest.exists();dest.mkdir(parents=True)
binding=json.loads((state/'BINDING.json').read_text());result=json.loads((state/'RESULT.json').read_text());a.identity(binding,result,key,arm)
for name in ('BINDING.json','RESULT.json','DAILY.csv','TIMING.json'):(dest/name).write_bytes((state/name).read_bytes())
assert result['inventory_audit']=='PASS'
print(json.dumps(dict(window=key,arm=arm,net_USDT=result['summary']['net_PnL'],paid_flat=result['summary']['terminal_cash_realized'],days=result['metrics']['days'],status=result['status'],seconds=json.loads((dest/'TIMING.json').read_text())['seconds']),indent=2))
