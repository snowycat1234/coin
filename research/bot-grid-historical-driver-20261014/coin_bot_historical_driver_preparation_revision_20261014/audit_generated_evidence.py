"""Compatibility projection into the byte-exact existing Decimal auditor.

Only generated final output is read. The original reviewer source is imported
unchanged, with output/global locators redirected outside its frozen package.
"""
from pathlib import Path
import argparse,gzip,importlib.util,json,tempfile
import bindings as B
AUDITOR=B.ROOT/'coin_bot_native_independent_review_20261014/audit_exported_journals.py'
AUDITOR_SHA256='c7c345f2cb674661b3566bcef785dad76c0aa4c6e731e05b750188ca095df8b7'

def read_gzip(path):return json.loads(gzip.decompress(Path(path).read_bytes()))
def rows(path):return [json.loads(line) for line in gzip.decompress(Path(path).read_bytes()).splitlines()]

def audit(output):
 B.check(AUDITOR,AUDITOR_SHA256);out=Path(output)
 receipt=B.read(out/'BENCHMARK_RECEIPT.json')
 if receipt['status']!='PASS_GENERATED_SCALING_ONLY':raise ValueError('COMPLETE_GENERATED_BENCHMARK_REQUIRED')
 with tempfile.TemporaryDirectory(prefix='coin_generated_audit_') as temporary:
  root=Path(temporary);candidate=root/'generated_evidence_projection';candidate.mkdir();runs=[]
  for record in receipt['runs']:
   directory=out/f"GENERATED_{record['days']}D_{record['arm']}"
   summary=B.read(directory/'SUMMARY.json');account=read_gzip(directory/'ACCOUNT_FINAL.json.gz');ownership=rows(directory/'OWNER_FILLS.jsonl.gz')
   journal=dict(account_final=account,native_trades=account['trades'],native_funding=account['funding'],
    ownership_allocations=ownership,funding_allocations=rows(directory/'OWNER_FUNDING.jsonl.gz'),adapter_state_final=read_gzip(directory/'OWNER_FINAL.json.gz'))
   filename=directory.name+'.json';(candidate/filename).write_text(json.dumps(journal,allow_nan=False)+'\n')
   runs.append(dict(journal=filename,fixture=directory.name,arm=record['arm'],grid_owned_fill_legs=sum(a['owner']=='GRID' for a in ownership),terminal_paid_flat=summary['terminal_cash_realized']))
  (candidate/'GENERATED_SUMMARY.json').write_text(json.dumps(dict(status='NOT_CERTIFIED_GENERATED_ONLY',historical_GO=False,runs=runs))+'\n')
  module=B.module('unchanged_decimal_generated_auditor',AUDITOR)
  module.CANDIDATE=candidate;module.HERE=root;module.main()
  checked=B.read(root/'JOURNAL_AUDIT_RECEIPT.json')
  checked.update(schema='COMPRESSED_DRIVER_EVIDENCE_EXACT_EXISTING_AUDITOR_V1',source_auditor_SHA256=AUDITOR_SHA256,
   projection='Lossless generated account/trades/funding/owner objects, output paths only; no financial runtime imported',historical_values_read_by_audit=0)
  target=out/'EXACT_DECIMAL_EVIDENCE_AUDIT.json'
  with target.open('x') as f:json.dump(checked,f,indent=2);f.write('\n')
  return checked

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args()
 result=audit(a.output);print(json.dumps({k:v for k,v in result.items() if k!='runs'}));return 0

if __name__=='__main__':raise SystemExit('USE_RUN_VERIFIED_COLD_BOOTSTRAP')
