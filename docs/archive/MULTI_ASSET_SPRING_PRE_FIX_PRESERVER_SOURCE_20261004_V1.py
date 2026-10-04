"""Recover exact pre-fix source bytes by reversing only this turn's diff."""
import hashlib,json,os,subprocess
from pathlib import Path
ROOT=Path('/mnt/d/codex/coin')
def digest(raw):return hashlib.sha256(raw).hexdigest()
def save_exact(raw,expected,name):
    variants=[raw,raw.replace(b'\r\n',b'\n'),raw.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')]
    matches=[x for x in variants if digest(x)==expected];assert matches,name
    p=ROOT/'docs/archive'/name
    if p.exists():assert p.read_bytes()==matches[0]
    else:
        with p.open('xb') as f:f.write(matches[0])
    return dict(path=p.relative_to(ROOT).as_posix(),sha256=expected)
assert os.environ['COIN_TASK_ID']
raw=(ROOT/'scripts/investment/multi_asset_data.py').read_text()
a=raw.index("        saved = authorization.get('saved_archive_reuse'")
b=raw.index('\n    else:\n        with client.stream',a)
raw=raw[:a]+'''        with deadline(budgets['source_file_seconds']):
            client.download(item['checksum_url'], checksum, 4096)
            check = checksum.read_text(encoding='ascii').split()
            require(len(check) == 2 and re.fullmatch('[0-9a-fA-F]{64}', check[0]) and
                check[1].lstrip('*') == name, 'Official exact CHECKSUM identity before ZIP')
            client.download(item['url'], archive, limit)'''+raw[b:]
raw=raw.replace("'FAIL_D062_SOURCE_STAGE' if spring else 'FAIL_D050_SOURCE_STAGE'","'FAIL_D050_SOURCE_STAGE'")
raw=raw.replace("phase in ('SEPTEMBER_SOURCE', 'SPRING_SOURCE')","phase == 'SEPTEMBER_SOURCE'")
a=raw.index("            if spring and row['symbol'] in ('BTCUSDT', 'ETHUSDT'):",raw.index("if spec.get('partial_source_reuse')"))
b=raw.index("            for field in ('zip', 'checksum', 'receipt'):",a)
raw=raw[:a]+"            require(key not in catalog and row['month'] == '2024-09' and row['symbol'] in spec['symbols'], 'One distinct bounded partial source')\n"+raw[b:]
raw=raw.replace("r['acquisition'] in ('NEW_OFFICIAL_BYTES_FORMAT_QA_PENDING_INDEPENDENT_ACCEPTANCE',\n                        'REUSED_FAILED_STAGE_COMPLETED_ROW_PENDING_INDEPENDENT_QA')", "r['acquisition'] == 'NEW_OFFICIAL_BYTES_FORMAT_QA_PENDING_INDEPENDENT_ACCEPTANCE'")
records=[save_exact(raw.encode(),'337f92a9a3d5bf4b30006cd83273a738459aafc7c26a409bc6fe399f8ff499d9',
    'MULTI_ASSET_SPRING_PRE_FIX_PRODUCER_SOURCE_20261004_V1.py')]
records.append(save_exact(subprocess.check_output(['git','show','HEAD:src/quant/data.py'],cwd=ROOT),
    'd6574aa1964b03f9d9a2a110365d47f8210eccfadb1ac11c391b4c8fb3f7862e','TRADE_NUMERIC_PRE_FIX_SOURCE_20261004_V1.py'))
raw=(ROOT/'scripts/investment/multi_asset_source_acceptance.py').read_text()
a=raw.index('                row_owner = owner\n');b=raw.index('                result = audit_trade',a)
raw=raw[:a]+'                parquet, archive, csv_bytes = new_receipt(row, owner, g)\n'+raw[b:]
records.append(save_exact(raw.encode(),'861b9126102abb302db1ba815d37912f73714025040f58c3c1b9aa5f2a97dd09',
    'MULTI_ASSET_SPRING_PRE_RECOVERY_QA_SOURCE_20261004_V1.py'))
p=ROOT/'reports/fast_research/MULTI_ASSET_SPRING_PRE_FIX_SOURCE_PRESERVED_20261004_V1.json'
with p.open('x') as f:json.dump(dict(status='PASS_EXACT_PRE_FIX_BYTES_RECOVERED_NO_OLD_EVIDENCE_CHANGED',
    task_id=os.environ['COIN_TASK_ID'],archives=records,old_QA_repeated=False,science_calls=0),f,indent=2);f.write('\n')
print(json.dumps(dict(status='PASS_EXACT_PRE_FIX_SOURCE_PRESERVED',archives=records)),flush=True)
