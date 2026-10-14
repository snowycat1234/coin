"""Reporting repair from exact saved records ONLY; no scoring-engine import.

Preserves ATTEMPT001's exit1 after all records were saved. Never recomputes
price returns, funding aggregates, ranks, baskets, labels, wallets or models.
"""
import hashlib
import json
import gzip
from pathlib import Path
from datetime import datetime, timezone

HERE=Path(__file__).resolve().parent
ATTEMPT=HERE.parent/'ATTEMPT001'
PIN=('cc0536ff885071ccc6793c0f6ce639a826b493fb5767d24efb500c5c031c9e06',1947533)
DAY=86_400_000_000;WEEK=7*DAY;ANCHOR=1_704_067_200_000_000
AUTHORITY='EXACT_PINNED_RETRIEVED_PROJECT_ARCHIVE_EVENT_SET_ONLY_PROVIDER_COMPLETENESS_UNCERTIFIED'
SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')


def sha(raw):return hashlib.sha256(raw).hexdigest()


def reconstruct():
    # Public cold restore uses the exact lossless saved-record archive here;
    # the original local attempt remains untouched and is preferred if present.
    local=(ATTEMPT/'RANK_RECORDS.jsonl').exists()
    base=ATTEMPT if local else HERE
    raw=(ATTEMPT/'RANK_RECORDS.jsonl').read_bytes() if local else gzip.decompress((HERE/'RANK_RECORDS.jsonl.gz').read_bytes())
    assert sha(raw)==PIN[0] and len(raw)==PIN[1]
    records=[json.loads(line) for line in raw.splitlines()]
    assert len(records)==212
    assert len({(r['year'],r['decision_us']) for r in records})==212
    failure=json.loads((base/'ATTEMPT_FAILURE.json').read_bytes())
    assert failure['status']=='FAILED_ATTEMPT_PRESERVED' and failure['error_type']=='TypeError'
    assert 'int64 is not JSON serializable' in failure['error']
    start=json.loads((base/'ATTEMPT_START.json').read_bytes())
    assert start['final_manifest_sha256']=='3d8f54ad0a02565e101a413adeb30ec99e3762e2587bed51dcb15bdd38c965f4'
    inventories={};changed_records=[];checked_ready=0
    for year in (2021,2023,2024,2025):
        lo=int(datetime(year,1,1,tzinfo=timezone.utc).timestamp())*1_000_000
        hi=int(datetime(year+1,1,1,tzinfo=timezone.utc).timestamp())*1_000_000
        context=ANCHOR+(lo-ANCHOR)//WEEK*WEEK
        clocks=list(range(context if context>=lo else context+WEEK,hi,WEEK))
        scheduled=[r for r in records if r['year']==year and r['role']=='SCHEDULED_CALENDAR_RANK']
        contexts=[r for r in records if r['year']==year and r['role']=='OWNERSHIP_CONTEXT_ONLY']
        assert [r['decision_us'] for r in scheduled]==clocks
        assert [r['decision_us'] for r in contexts]==([] if context>=lo else [context])
        for r in scheduled+contexts:
            d=r['decision_us'];lower,upper=d-22*DAY,d-DAY
            assert r['interval_us']==[lower,upper]
            assert r['latest_price_feature_available_us']==upper
            assert len(r['original_ready'])==len(r['funding_known'])==5
            assert r['original_admission_cash']==(not all(r['original_ready']))
            assert r['independent']['status']=='PASS_DIRECT_DECIMAL_EVENT_SUM_STABLE_BASKET_AND_CAUSAL_PREFIX'
            price,adjusted=r['price_only_raw_basket'],r['funding_adjusted_raw_basket']
            assert len(price)==len(adjusted)==5
            assert all(v in (-.15,0.,.15) for v in price+adjusted)
            assert r['paired_basket_changed']==(price!=adjusted)
            if r['status']=='READY_PAIRED_BASKETS':
                checked_ready+=1
                assert all(r['original_ready']) and all(r['price_known']) and all(r['funding_known']) and all(r['score_known'])
                assert len(r['price_rank_order'])==len(r['funding_rank_order'])==5
                assert sorted(r['price_rank_order'])==sorted(r['funding_rank_order'])==list(range(5))
                for a,proof in enumerate(r['funding_proof']):
                    ids=proof['event_ids']
                    assert proof['status']=='READY_CONDITIONAL_24H_DAY_PROXY'
                    assert proof['missing_or_invalid_day_us']==[]
                    assert ids==sorted(set(ids)) and all(lower<=t<upper for t in ids)
                    assert proof['observed_events']==len(ids)==r['independent']['checked_actual_event_counts'][a]
                    assert proof['latest_event_us']==ids[-1]<upper
                    assert proof['latest_input_day_available_us']==d
                    assert set(t//DAY*DAY for t in ids)==set(range(lower,upper,DAY))
                    assert abs(proof['value']-r['independent']['decimal_sums_float64'][a])<=2e-15*max(1.,abs(proof['value']))
            else:
                assert price==adjusted==[0.]*5
        ready=[r for r in scheduled if r['status']=='READY_PAIRED_BASKETS']
        missing=[r for r in scheduled+contexts if not r['original_admission_cash'] and r['status']!='READY_PAIRED_BASKETS']
        changed=[r for r in ready if r['paired_basket_changed']]
        context_change=any(r['paired_basket_changed'] for r in contexts if r['status']=='READY_PAIRED_BASKETS')
        inventories[str(year)]={'scheduled_calendar_ranks':len(scheduled),'ownership_context_clock_us':context,
            'paired_ready_ranks':len(ready),'original_admission_cash_ranks':sum(r['original_admission_cash'] for r in scheduled),
            'required_source_not_ready_ranks_including_context':len(missing),
            'rank_order_changed':sum(r['price_rank_order']!=r['funding_rank_order'] for r in ready),
            'signed_raw_basket_changed':len(changed),'ownership_context_basket_changed':context_change,
            'price_fully_tied_cash_ranks':sum(max(r['price_score'])-min(r['price_score'])<=1e-12 for r in ready),
            'adjusted_fully_tied_cash_ranks':sum(max(r['funding_adjusted_score'])-min(r['funding_adjusted_score'])<=1e-12 for r in ready),
            'conclusion':'INCONCLUSIVE_SOURCE_NOT_READY' if missing else ('FEATURE_CHANGES_BASKETS_CONDITIONAL' if changed or context_change else 'STOP_FUNDING_BASKET_NOOP_ON_ADMITTED_ORIGINAL_SUPPORT_CONDITIONAL')}
        changed_records.extend({'year':year,'date':datetime.fromtimestamp(r['decision_us']/1e6,timezone.utc).date().isoformat(),
            'decision_us':r['decision_us'],'price_only_raw_basket':r['price_only_raw_basket'],
            'funding_adjusted_raw_basket':r['funding_adjusted_raw_basket']} for r in changed)
    return {'status':'REPORTING_ONLY_SUMMARY_RECONSTRUCTED_FROM_COMPLETE_SAVED_RECORDS',
        'historical_attempt_status':'FAILED_FINAL_SUMMARY_SERIALIZATION_AFTER_RECORDS_SAVED_EXIT1_PRESERVED',
        'original_failure_receipt_sha256':sha((base/'ATTEMPT_FAILURE.json').read_bytes()),
        'rank_records_sha256':PIN[0],'rank_records_bytes':PIN[1],'complete_records':len(records),
        'scheduled_calendar_ranks':209,'paired_ready_scheduled_ranks':sum(v['paired_ready_ranks'] for v in inventories.values()),
        'paired_ready_records_including_context':checked_ready,
        'signed_raw_basket_changes':len(changed_records),'symbol_order':SYMBOLS,
        'years':inventories,'changed_baskets':changed_records,
        'completeness_authority':AUTHORITY,'funding_scale':'CONDITIONAL_RAW_FRACTION1',
        'provider_complete_set_certified':False,'historical_publication_time_certified':False,
        'funding_unit_certified':False,'actual_charge_time_certified':False,'score_is_exact_funded_PnL':False,
        'historical_engine_reinvocations':0,'signals_or_ranks_recomputed':0,'wallets':0,'fits':0,'provider_requests':0,
        'interpretation':'Same-lag paired raw weekly CS baskets only. Sparse selection change does not demonstrate profitability or original-wallet/CSH identity.'}


if __name__=='__main__':
    result=reconstruct();path=HERE/'RECONSTRUCTED_SUMMARY.json';assert not path.exists()
    path.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n');print(json.dumps(result,indent=2))
