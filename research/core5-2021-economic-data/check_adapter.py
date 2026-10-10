"""Invoke the actual independently published adapter without a model/scaler fit."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

EXPECTED_ADAPTER='556fc9d157747a76f28a15d03dd953e6ca44529a'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main(source_root,packet,output,source_commit):
    source=source_root/'modules/temporal_history_expansion/packet.py'
    assert sha(source)=='91b2a6e13dd7aaf038d20536e05906a0e5b7e91659e5befd1ba080a2e6676f3a'
    sys.path.insert(0,str(source_root))
    from modules.temporal_history_expansion.packet import load_packet
    from modules.temporal_history_expansion import packet as module
    assert Path(module.__file__).resolve()==source.resolve()
    index_sha=sha(packet/'CONSUMER_INDEX.json')
    result=load_packet(packet,source_commit=source_commit,consumer_sha256=index_sha)
    receipt=dict(status='ACTUAL_PUBLISHED_ADAPTER_LOAD_PACKET_PASSED',adapter_source_commit=EXPECTED_ADAPTER,
        adapter_source_SHA256=sha(source),consumer_SHA256=index_sha,packet_identity=result.identity,
        prices_shape=list(result.prices.shape),funding_shape=list(result.funding_coeff.shape),
        all_prices_known=bool(result.price_known.all()),all_funding_known=bool(result.funding_known.all()),
        actual_packet_receipt=result.receipt,model_fits=0,scaler_fits=0,model_inferences=0,backtests=0,wallets=0)
    output.write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='actual_packet_receipt'}))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--packet',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--source-commit',required=True)
    a=p.parse_args();main(a.source_root,a.packet,a.output,a.source_commit)
