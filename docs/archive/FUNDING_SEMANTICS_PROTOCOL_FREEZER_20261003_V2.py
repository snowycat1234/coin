"""Metadata-only prebinding; no network, funding rows or price arrays."""
import ast
from datetime import datetime, UTC
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path('/mnt/d/codex/coin')
source = ROOT/'scripts/investment/funding_semantics_probe_v2.py'
transport = ROOT/'scripts/investment/funding_semantics_windows_transport_v2.ps1'
destination = ROOT/'protocols/FUNDING_SEMANTICS_PROBE_20261003_V2.json'
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
module_spec = importlib.util.spec_from_file_location('_coin_funding_v2_freeze', source)
module = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(module)
protocol = json.loads((ROOT/'protocols/FUNDING_SEMANTICS_PROBE_20261003_V1.json').read_text())
protocol.update(contract_id='FUNDING_SEMANTICS_PROBE_20261003_V2',
    experiment_id='FUNDING-SEMANTICS-PROBE-20261003-V2',
    created_before_actual_requests_utc=datetime.now(UTC).isoformat(),
    source_sha256=sha(source), windows_transport_sha256=sha(transport),
    derived_main_ast_sha256=hashlib.sha256(ast.dump(module.derived_main_tree(), include_attributes=False).encode()).hexdigest(),
    document_urls=[], output='reports/fast_research/FUNDING_SEMANTICS_PROBE_20261003_V2.json',
    run_dir='/home/xflops/coin-state/funding-semantics-probe-20261003-v2',
    maximum_document_bytes=0,
    prior_failed_probe={'path':'reports/fast_research/FUNDING_SEMANTICS_PROBE_20261003_V1.json',
                        'sha256':'595acfac68508b6bac16c89271d2a40b7821cfbd8fd927efed8f495a800dff6c',
                        'status':'FAIL_OFFICIAL_FUNDING_API_PARITY_UNCONFIRMED'},
    transport_scope='WINDOWS_EXISTING_SYSTEM_NET_DEFAULT_HTTPS_BYTES_ONLY;ALL_RATE_PARSE_AND_PARITY_IN_WSL',
    network_policy='Exactly two same-host fixed history URLs; timeout20s/64000bodybytes; no HTML repeat, retry, redirect, alternatehost, TLS bypass or proxy/network setting modification; stop403/451/418/429',
    native_execution='PINNED_LOCAL_POWERSHELL_SCRIPTBLOCK_WITHOUT_EXECUTION_POLICY_CHANGE',
    memory_accounting='WSL_SELF_RSS_AND_WINDOWS_CURRENT_PROCESS_PEAK_REPORTED_SEPARATELY;NO_SHARED_TOTAL_PEAK_CLAIM',
    network_byte_accounting='RESPONSE_BODY_BYTES;HEADERS_TLS_WIRE_BYTES_NOT_MEASURED')
protocol['frozen_sources'].update({str(p.relative_to(ROOT)):sha(p) for p in (
    source,transport,ROOT/'protocols/FUNDING_SEMANTICS_PROBE_20261003_V1.json',
    ROOT/'reports/fast_research/FUNDING_SEMANTICS_PROBE_20261003_V1.json')})
assert sha(ROOT/protocol['prior_failed_probe']['path']) == protocol['prior_failed_probe']['sha256']
with destination.open('x') as stream:
    json.dump(protocol,stream,indent=2,ensure_ascii=False,allow_nan=False);stream.write('\n')
print(json.dumps({'protocol_path':str(destination),'protocol_sha256':sha(destination),
                  'source_sha256':sha(source),'transport_sha256':sha(transport),
                  'derived_main_ast_sha256':protocol['derived_main_ast_sha256'],
                  'network_requests_made':0}))
