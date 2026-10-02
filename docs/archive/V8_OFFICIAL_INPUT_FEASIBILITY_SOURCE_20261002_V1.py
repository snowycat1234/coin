"""Source-only synthesis of recorded official metadata and primary documentation."""
from collections import Counter
from datetime import UTC, date, datetime
import hashlib
import json
from pathlib import Path
import resource
import subprocess

ROOT=Path('/mnt/d/codex/coin')
REPORTS=ROOT/'reports/fast_research'
out=REPORTS/'V8_OFFICIAL_INPUT_FEASIBILITY_20261002_V1.json'
assert not out.exists()
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
metadata_path=REPORTS/'V8_OFFICIAL_INPUT_METADATA_20261002_V1.json'
assert digest(metadata_path)=='7d1fdfb19b406c41ed6d3634dedb37081ffd00f2306160d23183f3701e474217'
metadata=json.loads(metadata_path.read_bytes())
staff_path=REPORTS/'V8_OFFICIAL_STAFF_COMMENTS_20261002_V1.json'
policy_path=REPORTS/'V8_OFFICIAL_ARCHIVE_POLICY_COMMENTS_20261002_V1.json'
staff=json.loads(staff_path.read_bytes())
policy=json.loads(policy_path.read_bytes())
protocol_path=ROOT/'protocols/P1_GATE_V8.json'
protocol=json.loads(protocol_path.read_bytes())
assert [(i['id'],i['test_start'],i['test_end_exclusive']) for i in protocol['folds']]==[tuple(i) for i in metadata['folds']]
assert metadata['archive_zip_bytes_read']==0 and not metadata['row_or_model_outcomes_read']
assert len(metadata['objects'])==224 and all(not i['archive_body_downloaded'] for i in metadata['objects'])
assert all('2025-08' <= (i.get('date') or i['month'])[:7] <= '2025-11' for i in metadata['objects'])
market_doc='https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data'
account_doc='https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/account'
spot_doc='https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/ws-streams/~'
base='https://data.binance.vision/data'

def daily_by_fold(market,kind):
    result=[]
    for fold,first,end in metadata['folds']:
        rows=[i for i in metadata['objects'] if i['fold']==fold and i['market']==market and i['kind']==kind]
        assert len(rows)==14
        result.append({'fold':fold,'start_inclusive':first,'end_exclusive':end,
            'nominal_objects_required':len(rows),'objects_with_head_and_valid_checksum':sum(i['metadata_object_available'] for i in rows),
            'head_statuses':dict(Counter(str(i['head']['http_status']) for i in rows)),
            'checksum_statuses':dict(Counter(str(i['checksum_access']['http_status']) for i in rows)),
            'announced_compressed_bytes':sum(i['announced_zip_bytes'] for i in rows) if all(i['metadata_object_available'] and i['announced_zip_bytes'] is not None for i in rows) else None,
            'actual_row_calendar_coverage':'UNKNOWN_NO_ZIP_OR_ROWS_READ'})
    return result

def monthly_by_fold(kind):
    result=[]
    for fold,first,end in metadata['folds']:
        months={first[:7],date.fromordinal(date.fromisoformat(end).toordinal()-1).isoformat()[:7]}
        rows=[i for i in metadata['objects'] if i['market']=='futures/um' and i['kind']==kind and i['partition']=='monthly' and i['month'] in months]
        assert len(rows)==2*len(months)
        result.append({'fold':fold,'required_months':sorted(months),'nominal_objects_required':len(rows),
            'objects_with_head_and_valid_checksum':sum(i['metadata_object_available'] for i in rows),
            'actual_row_calendar_coverage':'UNKNOWN_NO_ZIP_OR_ROWS_READ'})
    return result

schema_refs=[]
for record in staff['records']:
    for item in record.get('staff_comments',[]):
        schema_refs.append({'url':item['html_url'],'publisher_association':item['author_association'],
            'created_at':item['created_at'],'body_sha256':item['body_sha256'],
            'access':'WSL_HTTP_200_SAVED_BODY','full_body_in_state_only':True})
assert len(schema_refs)==2
route_groups={(i['market'],i['kind'],i['partition']):i for i in metadata['groups']}

bbo=[]
for market in ('spot','futures/um'):
    bbo.append({'market':market,'information':'TRUE_BBO_WITH_PRICE_AND_TOP_SIZE',
        'daily_url_template':f'{base}/{market}/daily/bookTicker/{{symbol}}/{{symbol}}-bookTicker-{{YYYY-MM-DD}}.zip',
        'monthly_url_template':f'{base}/{market}/monthly/bookTicker/{{symbol}}/{{symbol}}-bookTicker-{{YYYY-MM}}.zip',
        'checksum':'same ZIP URL + .CHECKSUM',
        'oos_archive_state':'NO_COMPLETE_AVAILABLE_SOURCE_AT_CHECKED_OFFICIAL_URLS',
        'four_fold_nominal_coverage':daily_by_fold(market,'bookTicker'),
        'monthly_metadata':route_groups[(market,'bookTicker','monthly')],
        'historical_schema_timestamp_unit':'UNKNOWN_NO_AVAILABLE_ARCHIVE',
        'live_documented_fields':['u','s','b','B','a','A'] if market=='spot' else ['symbol','bidPrice','bidQty','askPrice','askQty','time'],
        'live_endpoint':'wss://stream.binance.com:9443/ws/{symbol}@bookTicker' if market=='spot' else 'https://fapi.binance.com/fapi/v1/ticker/bookTicker',
        'live_primary_doc':spot_doc if market=='spot' else market_doc,
        'live_clock_limit':'Spot listed bookTicker message has no exchange event timestamp; preserve actual receipt clock separately.' if market=='spot' else 'Current quote time does not backfill historical quotes; exact API time semantics must remain distinct from local receipt.',
        'compressed_and_uncompressed_historical_capacity':None,
        'capacity_reason':'Required official archives were not available; do not extrapolate from trades or live traffic.'})

price_proxies=[]
for kind,endpoint in (('markPriceKlines','/fapi/v1/markPriceKlines'),('indexPriceKlines','/fapi/v1/indexPriceKlines'),('premiumIndexKlines','/fapi/v1/premiumIndexKlines')):
    price_proxies.append({'kind':kind,'official_monthly_url_template':f'{base}/futures/um/monthly/{kind}/{{symbol}}/1m/{{symbol}}-1m-{{YYYY-MM}}.zip',
        'checksum':'same ZIP URL + .CHECKSUM','four_fold_nominal_coverage':monthly_by_fold(kind),
        'metadata':route_groups[('futures/um',kind,'monthly')],
        'api_endpoint':endpoint,'api_doc':market_doc,
        'documented_api_fields':['open_time','open','high','low','close','close_time','ignore_fields'],
        'information':'1_MINUTE_OHLC_PROXY_NO_BBO_NO_EXECUTABLE_SIZE',
        'timestamp_unit':'API epoch milliseconds; exact archive bytes/header/units NOT_VERIFIED',
        'price_unit':'USDT price for mark/index of BTCUSDT/ETHUSDT; premium index encoding/unit NOT_VERIFIED' if kind=='premiumIndexKlines' else 'USDT price for BTCUSDT/ETHUSDT; exact archive encoding NOT_VERIFIED',
        'event_mark_or_simultaneous_basis_reconstructed':False})

available=[i for i in metadata['objects'] if i['metadata_object_available']]
assert len(available)==88
announced=sum(i['announced_zip_bytes'] for i in available)
assert announced==47_872_757
claims={
 'status':'OFFICIAL_INPUT_FEASIBILITY_REVIEW_COMPLETE_NOT_DATA_ACCEPTANCE',
 'created_utc':datetime.now(UTC).isoformat(),
 'scope':'BTCUSDT/ETHUSDT, 2025 Aug-Nov; fixed V8 OOS calendar. HEAD + small official CHECKSUM/documentation only.',
 'git_head_at_synthesis':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 'protocol_binding':{'path':str(protocol_path),'sha256':digest(protocol_path),'folds':metadata['folds']},
 'evidence_bindings':[{'path':str(p),'sha256':digest(p)} for p in (metadata_path,staff_path,policy_path)],
 'upstream_repository':{'url':'https://github.com/binance/binance-public-data','commit':metadata['upstream_commit'],
   'software_license':metadata['software_license'],
   'dataset_terms_url':f'https://raw.githubusercontent.com/binance/binance-public-data/{metadata["upstream_commit"]}/TERMS_AND_CONDITIONS.md',
   'dataset_terms_sha256':metadata['data_terms_sha256'],
   'scope':'Dataset terms are distinct from software MIT. Current task is personal historical nonproduction research; future production use requires a separate terms decision.',
   'local_upstream_modifications':[]},
 'primary_document_access':[
   {'url':market_doc,'wsL_access':'ConnectError / Network unreachable; retained original report','browser_access':'SUCCESS_SEMANTIC_DOCUMENT_5180_LINES','api_called':False},
   {'url':account_doc,'wsL_access':'ConnectError / Network unreachable; retained original report','browser_access':'SUCCESS_SEMANTIC_DOCUMENT_3144_LINES','api_called':False},
   {'url':spot_doc,'wsL_access':'ConnectError / Network unreachable; retained original report','browser_access':'SUCCESS_SEMANTIC_DOCUMENT_2871_LINES','api_called':False}],
 'historical_bbo':bbo,
 'bookticker_publication':{
   'official_repo_collaborator_statement':{'url':schema_refs[0]['url'],'statement':'Publisher collaborator says support for tick-level historical orderbook data stopped in November 2024.',
     'qualification':'Comment uses I believe for the discontinued historical orderbook support; it does not certify bookTicker-specific final publication date.'},
   'bookticker_specific_final_publication_date':None,
   'specific_stop_reason':'UNKNOWN_NOT_PUBLISHER_CERTIFIED',
   'observed_required_archives':'0/128 available official daily/monthly Spot+UM bookTicker objects at this check. One UM daily HEAD 503, its CHECKSUM 404; all other ZIP HEADs and CHECKSUMs 404.',
   'user_issue_statements_used_as_confirmation':False,
   'no_claim':'A live bookTicker endpoint does not establish historical archive availability.'},
 'historical_bookdepth':{
   'official_daily_url_template':f'{base}/futures/um/daily/bookDepth/{{symbol}}/{{symbol}}-bookDepth-{{YYYY-MM-DD}}.zip',
   'checksum':'same ZIP URL + .CHECKSUM','four_fold_nominal_coverage':daily_by_fold('futures/um','bookDepth'),
   'daily_metadata':route_groups[('futures/um','bookDepth','daily')],
   'monthly_metadata':route_groups[('futures/um','bookDepth','monthly')],
   'schema_primary_refs':schema_refs,
   'publisher_confirmed_fields_semantics':{'percentage':'Ranges at minus/plus 1 to 5 percent from mid price','depth':'Depth in coin quantity','notional':'Depth in notional amount'},
   'publisher_confirmed_sampling_seconds':30,
   'timestamp_unit':'UNKNOWN_UNTIL_HEADER_AND_ROWS_ACCEPTED',
   'price_levels_or_bbo':False,'true_L5':False,
   'best_level_size_recoverable':False,'fill_or_spread_estimation_qualified':False,
   'role_if_later_accepted':'Coarse liquidity-state / imbalance research; must have a new honest information contract.'},
 'true_historical_L5':{
   'official_public_2025_aug_nov_archive_url':None,'archive_metadata_checked':'NO_VERIFIED_CURRENT_OFFICIAL_FREE_PRICE_LEVEL_ARCHIVE_ROUTE',
   'four_fold_coverage':'NOT_ESTABLISHED','compressed_capacity_bytes':None,'uncompressed_capacity_bytes':None,
   'live_references':[{'doc':spot_doc,'endpoint':'wss://stream.binance.com:9443/ws/{symbol}@depth5@100ms','fields':['lastUpdateId','bids:[[price,quantity]]','asks:[[price,quantity]]']},
     {'doc':market_doc,'endpoint':'https://fapi.binance.com/fapi/v1/depth?symbol={symbol}&limit=5','fields':['lastUpdateId','E','T','bids:[[price,quantity]]','asks:[[price,quantity]]']}],
   'clock':'Live depth timestamps/update IDs and actual local receipt are separate; live interfaces cannot supply past OOS.'},
 'funding_history':{
   'official_monthly_url_template':f'{base}/futures/um/monthly/fundingRate/{{symbol}}/{{symbol}}-fundingRate-{{YYYY-MM}}.zip',
   'checksum':'same ZIP URL + .CHECKSUM','four_fold_nominal_coverage':monthly_by_fold('fundingRate'),
   'metadata':route_groups[('futures/um','fundingRate','monthly')],
   'archive_header_fields_timestamp_unit':'UNKNOWN_NO_ZIP_BODY_READ; REST fields must not be silently imposed on CSV',
   'api_endpoint':'/fapi/v1/fundingRate','api_doc':market_doc,
   'api_fields':['symbol','fundingRate','fundingTime','markPrice','rateType'],
   'api_time':'startTime/endTime milliseconds inclusive; fundingTime is a charge event timestamp, distinct from prediction availability and account settlement.',
   'associated_mark':'API documentation ties markPrice to a funding charge; archive presence of that field is unverified.',
   'rate_unit':'Fractional rate; confirm archive encoding before conversion. Do not assume all intervals equal eight hours.'},
 'price_proxies':price_proxies,
 'basis':{'api_endpoint':'/futures/data/basis','api_doc':market_doc,'fields':['indexPrice','futuresPrice','basis','basisRate','timestamp'],
   'api_timestamp_unit':'milliseconds, period start','documented_retention_days':30,
   'api_serves_four_2025_folds_as_of_review':False,'archive_route':None,'archive_capacity_bytes':None,
   'proxy_inference':'Aligned market/mark/index bars may support a coarse basis proxy after QA; index is not a tradable Spot bid/ask and minute OHLC is not simultaneous two-leg execution.'},
 'carry_required_inputs_not_yet_accepted':[
   'Funding event calendar, actual interval and rate history, causal publication time, and exact mark at the charge; validate archive/API mapping.',
   'Both-leg causal BBO/depth, latency, lot/tick/min-notional rules and size to evaluate entry, hedge, rebalance and exit.',
   'Historical contract settlement and collateral/margin rules: initial/maintenance tiers, liquidation, ADL, isolated/cross policy, capital reserved for both legs.',
   'Applicable Spot and USD-M fee schedules over time and account tier/discount eligibility; keep the existing cost scenarios unchanged.',
   'Borrow availability and historical interest for any borrowed/short Spot leg; cash funding and transfer friction where relevant.',
   'Exposure and NAV ledger that settles funding only for positions liable at each actual charge time; no continuous prorating or double counting.'
 ],
 'signed_account_doc_limits':{'doc':account_doc,'leverageBracket':'USER_DATA signed API key; current user-specific brackets, historical schedule unverified',
   'commissionRate':'USER_DATA signed API key; current rates do not certify old fee schedules','requests_made':0},
 'capacity':{'announced_compressed_bytes':announced,'maximum_single_announced_zip_bytes':max(i['announced_zip_bytes'] for i in available),
   'funding_and_three_proxy_types_compressed_bytes':23_147_488,'four_fold_bookdepth_compressed_bytes':24_725_269,
   'bookdepth_full_aug_nov_compressed_bytes':None,'all_uncompressed_bytes':None,'parquet_or_working_memory_bytes':None,
   'availability_check_not_capacity_acceptance':True,
   'last_accepted_disk_scan_reference':{'utc':'2026-10-02T09:40:54.517503+00:00','bytes':19_355_135_811,'new_scan_executed':False},
   'future_source_intake_guard':'Before any ingestion: actual disk + announced/inspected working capacity + 1GB workspace within expected32GB/stress36GB/hard40GB, shared5GB noGPU/swap0.'},
 'research_reopen_recommendation':{
   'funding_mark_index':'Lowest input-cost new information route: 7,518 B funding plus 16,253,290 B mark/index compressed. Reopen source QA first; strategy economics remains NOT_EVALUABLE until funding, two-leg costs and margin mapping are accepted.',
   'bookdepth':'May reopen a distinct coarse-liquidity hypothesis only after schema/rows/calendar/causal timestamps acceptance; cannot satisfy a real-L1/L5 execution or candidate prerequisite.',
   'true_L1_L5':'Pause historical route for these four folds until a verified licensed official price-level source exists. Existing live capabilities are preserved and need actual audited future coverage; do not invent past folds.',
   'deeper_models':'No justification from metadata to fit new/deeper models or alter P1.',
   'frontier':'Reserve new information work without spending the frontier budget on further model capacity against unchanged information.'},
 'qualifications':{'data_acceptance':'NOT_EVALUATED','P1':'NOT_CHANGED','economics':'NOT_EVALUATED','fee_replacement':False,
   'candidate':'NO_CLAIM','apr':'NO_CLAIM','row_calendar_coverage':'UNKNOWN','zip_checksum_verified':'NO_ZIP_DOWNLOADED',
   'rate_estimates_or_profit_computed':False},
 'execution':{'metadata_session':77846,'metadata_exit_code':0,'metadata_elapsed_seconds':metadata['elapsed_seconds'],
   'metadata_peak_rss_bytes':metadata['peak_rss_bytes'],'archive_zip_bytes_read':0,'no_locked_no_models_no_keys_no_paid_no_gpu':True,
   'shared_registry_appended':False,'source_or_collector_modified':False,'no_new_downloader_or_collector':True,
   'timestamp_note':'Preserve original timezone-aware access strings, including +08:00 offsets; offset-aware instants are not durations or healthy UTC days.'},
 'synthesis_source_sha256':digest(Path(__file__)),
 'synthesis_peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
}
with out.open('x') as stream:json.dump(claims,stream,indent=2,ensure_ascii=False,allow_nan=False);stream.write('\n')
print(json.dumps({'status':claims['status'],'sha256':digest(out),'bytes':out.stat().st_size,
 'compressed_metadata_bytes':announced,'zip_bytes_downloaded':0,'true_L5_historical':'NOT_ESTABLISHED',
 'BBO_required_archive_available_objects':0,'peak_rss_bytes':claims['synthesis_peak_rss_bytes']}))
