import importlib.util,json,sys
from pathlib import Path
root=Path('/workspace/coin-tail-risk');here=root/'research/portfolio-risk-budget-20261012';key,arm=sys.argv[1:]
spec=importlib.util.spec_from_file_location('existing_saved_request_diagnostic',root/'research/quantity-grid-sensitivity-20261012/request_diagnostic.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
new=Path('/workspace/portfolio-risk-budget-state')/('OBSERVED_'+key)/arm;old=Path('/workspace/quantity-grid-state')/('OBSERVED_'+key)/arm
body=dict(window=key,arm=arm,changed_risk_target=m.inspect(new),original_quantity_baseline_REUSED=m.inspect(old),account_advances=0,new_wallets=0,scope='GENUINE_SAVED_REQUESTS_NO_FINANCIAL_CONSTRUCTION_OR_REPLAY')
dest=here/'summary'/key/arm/'REQUEST_DIAGNOSTIC.json';assert not dest.exists();dest.write_text(json.dumps(body,sort_keys=True,indent=2)+'\n');print(json.dumps(dict(window=key,arm=arm,new=body['changed_risk_target']['terminal_quantity'],last5=body['changed_risk_target']['last_five_reduce_requests_for_residual_symbols']),indent=2))
