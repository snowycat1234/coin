"""Materialize only the exact existing 2021 source parser/audit dependencies."""
from recover import STATE,FULL2021,get,write,sha
import json
NAMES=('source_parser.py','test_source_parser.py','inspect_cached_prefix.py','restore_public_sources.py','audit_warmup.py','audit_funding.py','assemble_offline.py','prepare_full_2021.py','verify_few_boundaries.py','evidence/Y2021_INDEX.json','evidence/DEC2021_RECOVERY.json','evidence/DEC2021_SOURCE_INDEX.json')
def main():
 records=[]
 for n in NAMES:
  path='research/core5-2021-fullsource-20261013/'+n;raw=get(FULL2021,path);write(STATE/'source2021'/n,raw);records.append(dict(commit=FULL2021,path=path,sha256=sha(raw)))
 write(STATE/'source2021/RESTORED_CODE.json',(json.dumps(records,indent=2)+'\n').encode())
if __name__=='__main__':main()
