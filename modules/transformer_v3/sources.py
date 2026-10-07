"""Public-only source receipts; HTTP failure never proves an absent settlement."""
import argparse,concurrent.futures,json,time
from pathlib import Path
import requests
from modules.transformer_v2.train import atomic,sha

SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','1000PEPEUSDT','XRPUSDT','WIFUSDT','WLDUSDT','DOGEUSDT','1000SATSUSDT','ORDIUSDT')
GAPS=('WIFUSDT','1000SATSUSDT','ORDIUSDT')

def public_get(state,name,url,params=None):
    dest=Path(state)/'source-responses'/name;dest.mkdir(parents=True,exist_ok=True)
    assert not (dest/'receipt.json').exists(),'Source receipt immutable'
    request=dict(method='GET',url=url,params=params or {},headers={'Accept':'application/json'},credentials_used=False)
    result=dict(request=request,requested_at=time.time(),source_name=name)
    try:
        r=requests.get(url,params=params,headers=request['headers'],timeout=20)
        path=dest/'response.bin';path.write_bytes(r.content)
        result.update(http_status=r.status_code,returned_url=r.url,response_sha256=sha(path),response_bytes=len(r.content),
                      response_path=str(path),response_content_type=r.headers.get('content-type'))
    except requests.RequestException as e:result.update(error=str(e),http_status=None)
    result['finished_at']=time.time();atomic(dest/'receipt.json',result);return result

def risk_snapshot(receipt,symbol):
    if receipt['http_status']!=200:return dict(symbol=symbol,status='UNAVAILABLE_HTTP',receipt=receipt)
    raw=json.loads(Path(receipt['response_path']).read_bytes())
    if raw.get('retCode')!=0:return dict(symbol=symbol,status='API_ERROR',receipt=receipt)
    rows=raw['result']['list']
    if not rows or any(r['symbol']!=symbol for r in rows):raise ValueError('Risk snapshot exact symbol mismatch')
    fields=('riskLimitValue','maintenanceMargin','initialMargin','mmDeduction','maxLeverage','isLowestRisk')
    for r in rows:
        if any(k not in r for k in fields):raise ValueError('Incomplete native risk tier')
    return dict(symbol=symbol,status='RECORDED_CURRENT_BYBIT_PUBLIC_RISK',tiers=rows,receipt=receipt,
                historical_tiers_certified=False,normalization='API maintenance/initialMargin numerical fractions; validate tier values before simulation')

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);a=p.parse_args();state=Path(a.state)
    assert (state/'PHASE0_V2_PRESERVATION.json').exists(),'Protect v2 before new source work'
    records=[]
    # Ordered provider families; requests within one provider may run concurrently.
    for provider in ('BINANCE_API','BINANCE_WEBSITE','COINALYZE','COINGLASS','COINAPI'):
        jobs=[]
        for symbol in GAPS:
            if provider=='BINANCE_API':url='https://fapi.binance.com/fapi/v1/fundingRate';params=dict(symbol=symbol,startTime=1782259200000,endTime=1782288001000,limit=1000)
            elif provider=='BINANCE_WEBSITE':url='https://www.binance.com/en/futures/funding-history/perpetual/1';params=dict(symbol=symbol,startTime=1782259200000,endTime=1782288001000)
            elif provider=='COINALYZE':url='https://api.coinalyze.net/v1/funding-rate-history';params=dict(symbols=symbol+'_PERP.A',interval='4hour',**{'from':1782259200,'to':1782288001})
            elif provider=='COINGLASS':url='https://open-api-v4.coinglass.com/api/futures/funding-rate/history';params=dict(exchange='Binance',symbol=symbol,interval='4h',start_time=1782259200000,end_time=1782288001000,limit=100)
            else:url='https://rest.coinapi.io/v1/metrics/symbol/history';params=dict(metric_id='DERIVATIVES_FUNDING_RATE_CURRENT',symbol_id='BINANCEFTS_PERP_'+symbol[:-4]+'_USDT',time_start='2026-06-24T00:00:00Z',time_end='2026-06-24T08:00:01Z',period_id='4HRS',limit=10)
            jobs.append((provider+'_'+symbol,url,params))
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            own=list(pool.map(lambda j:public_get(state,*j),jobs))
        for record,symbol in zip(own,GAPS):
            record.update(provider=provider,requested_exchange='Binance USD-M',requested_symbol=symbol,
                          exact_event_verified=False,returned_exchange=None,returned_symbol=None,settlement_timestamp=None,raw_rate=None,
                          normalization=None,interpretation='UNASSESSED_RAW_RESPONSE_NOT_EVIDENCE_OF_NO_SETTLEMENT')
        records.extend(own);atomic(state/'FUNDING_SOURCE_REQUESTS.json',dict(records=records,progress_provider=provider,no_private_keys_or_paid_requests=True))
        print(provider+': '+', '.join(str(r['http_status']) for r in own),flush=True)
    def risk(symbol):return risk_snapshot(public_get(state,'BYBIT_RISK_'+symbol,'https://api.bybit.com/v5/market/risk-limit',dict(category='linear',symbol=symbol)),symbol)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:risks=list(pool.map(risk,SYMBOLS))
    atomic(state/'BYBIT_RISK_SNAPSHOT.json',dict(rows=risks,source='GET /v5/market/risk-limit',snapshot_time=time.time(),historical_certification=False))
    try:collector=requests.get('http://127.0.0.1:8765/api/status',timeout=3);collector_state=dict(http_status=collector.status_code,reachable=True)
    except requests.RequestException:collector_state=dict(reachable=False)
    atomic(state/'COLLECTOR_STATUS_OBSERVATION.json',dict(observed_at=time.time(),**collector_state,no_service_change=True))
    print('BYBIT RISK: '+', '.join(r['symbol']+':'+r['status'] for r in risks),flush=True)

if __name__=='__main__':main()
