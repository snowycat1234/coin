import hashlib,json,zipfile
from pathlib import Path
state=Path('/workspace/coin-state/work/temporal-two-expert-20261009/selected-refit')
source=state/'supplied-q4/research/core5-q4-2024-native-data'
index=json.loads((source/'Q42024/INDEX.json').read_text())
consumer=json.loads((source/'CONSUMER_INDEX.json').read_text())
sha=lambda b:hashlib.sha256(b).hexdigest()
package=state/'supplied-q4/package.zip'
assert sha(package.read_bytes())==index['package_SHA256']
for row in index['parts']:
    data=(source/'Q42024'/row['name']).read_bytes()
    assert len(data)==row['bytes'] and sha(data)==row['SHA256']
output=state/'q4-economics';output.mkdir()
(output/'CONSUMER_INDEX.json').write_bytes((source/'CONSUMER_INDEX.json').read_bytes())
with zipfile.ZipFile(package) as z:
    assert z.testzip() is None
    members={r['name']:r for r in index['members']}
    for row in consumer['economic_table_artifacts']:
        data=z.read(row['path']);meta=members[row['path']]
        assert len(data)==row['bytes']==meta['bytes']
        assert sha(data)==row['SHA256']==meta['SHA256']
        dest=output/row['path'];dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
    assert z.read('ECONOMICS.npz')==(source/'Q42024/ECONOMICS.npz').read_bytes()
receipt=dict(status='SUPPLIED152606_DERIVED_PACKET_MATERIALIZED_AND_BYTE_VERIFIED',
    source_commit='152606ad56fe6d8943b27ce89c8c57e2068ee944',
    frozen_refit_commit='6124170b9d0f8c7eed5e7faf7584f56044ad752c',
    consumer_SHA256=sha((output/'CONSUMER_INDEX.json').read_bytes()),
    package_SHA256=index['package_SHA256'],files={r['path']:r['SHA256'] for r in consumer['economic_table_artifacts']},
    provider_downloads=0,raw_minute_archives_restored=0,model_inferences=0,economic_wallets=0,
    synthetic_rows=0)
(state/'Q4_MATERIALIZATION.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k!='files'}))
