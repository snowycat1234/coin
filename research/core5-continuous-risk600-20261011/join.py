"""Certify the published chronological source chain; no new labels or fits."""
import argparse
import io
import json
from pathlib import Path
import numpy as np
from prepare import HERE,PHASES,SYMBOLS,SourceReader,bind_current,digest,git,save

PREFIX='research/core5-continuous-risk600-20261011/'


def assemble(commit):
    phases=[];arrays=[];previous=None;newbytes=0;newarchives=0;minutes=0;added=0;common=0
    for phase in PHASES:
        prefix=PREFIX+'phases/'+phase+'/'
        indexraw=git('show',commit+':'+prefix+'SOURCE_INDEX.json');index=json.loads(indexraw)
        raw=git('show',commit+':'+prefix+'RECOVERY.json');assert digest(raw)==index['proof_SHA256']
        coldraw=git('show',commit+':'+prefix+'PUBLIC_RESTORE.json');cold=json.loads(coldraw)
        assert cold['status']=='PASS_PUBLIC_GIT_OBJECT_RAW_MINUTE_COLD_RESTORE' and cold['source_index_SHA256']==digest(indexraw)
        assert cold['original_STATE_open_attempts']==cold['fits']==cold['wallets']==cold['provider_downloads']==0
        assert git('show',cold['artifact_commit']+':'+prefix+'SOURCE_INDEX.json')==indexraw
        proof=bind_current(json.loads(raw),cold['artifact_commit'])
        assert proof['fits']==proof['wallets']==proof['labels_created']==0
        if previous is not None:
            assert proof['previous_proof_SHA256']==previous['raw_SHA256']
            firstmonth=proof['sources'][0]['source']['month']
            for symbol in SYMBOLS:
                first=next(r for r in proof['sources'] if r['source']['symbol']==symbol and r['source']['month']==firstmonth)
                assert first['past_boundary']==previous['proof']['end_boundaries'][symbol]
        else:assert proof['previous_proof_SHA256'] is None
        row=index['artifacts']['DAILY.npz'];b=b''.join(SourceReader.part(cold['artifact_commit'],p) for p in row['parts'])
        assert len(b)==row['bytes'] and digest(b)==row['SHA256']
        with np.load(io.BytesIO(b),allow_pickle=False) as a:
            assert tuple(a['symbol_order'])==SYMBOLS
            arrays.append({k:a[k].copy() for k in a.files if k!='symbol_order'})
        newbytes+=proof['new_original_bytes'];newarchives+=index['original_new_source_count'];minutes+=proof['actual_minutes']
        added+=proof['official_daily_repairs_added'];common+=proof['official_daily_common_rows_verified']
        phases.append(dict(phase=phase,artifact_commit=cold['artifact_commit'],index_SHA256=digest(indexraw),
            proof_SHA256=digest(raw),cold_receipt_SHA256=digest(coldraw),daily_SHA256=row['SHA256'],
            calendar_days=proof['calendar_days'],valid_joint_RV_days=proof['valid_joint_RV_days'],
            previous_boundary_raw_checks=cold['boundary_previous_month_raw_checks'],
            new_original_bytes=proof['new_original_bytes'],source_months=len(proof['sources'])))
        previous=dict(proof=proof,raw_SHA256=digest(raw))
    assert len({tuple(a) for a in arrays})==1
    full={k:np.concatenate([a[k] for a in arrays]) for k in arrays[0]}
    t=full['available_us'];assert len(t)==699 and np.all(np.diff(t)==86400000000)
    assert int(t[0])==1609545600000000 and int(t[-1])==1669852800000000
    riskkeys=('RV_1m','RV_5m','RSplus_1m','RSminus_1m','RSplus_5m','RSminus_5m','max_log_up','max_log_down')
    for k in full:
        if k=='available_us':continue
        assert full[k].shape==(699,5)
        if k in riskkeys:
            assert np.isnan(full[k][0]).all() and np.isfinite(full[k][1:]).all()
        else:assert np.isfinite(full[k]).all()
    assert np.all(full['observed_minutes']==1440) and minutes==699*1440*5==5032800
    assert newarchives==45 and newbytes<=100000000 and added+common==10*1440
    for suffix in ('1m','5m'):
        np.testing.assert_allclose(full['RV_'+suffix],full['RSplus_'+suffix]+full['RSminus_'+suffix],rtol=2e-15,atol=1e-16,equal_nan=True)
    return full,dict(status='PASS_698_CONTINUOUS_REAL_TRADE_RISK_DATES',source_chain_commit=commit,phases=phases,
        source_calendar_dates=699,valid_continuous_joint_dates=698,valid_feature_day_start='2021-01-02',
        valid_feature_day_end='2022-11-30',availability_clock='FollowingUTCday00:00, not historicalarrivalcertificate',
        actual_minute_rows=minutes,monthly_originals=115,new_official_monthly_originals=45,new_original_bytes=newbytes,
        old_daily_repair_added_minutes=added,old_daily_overlap_common_minutes=common,
        first_unknown_boundary_preserved=True,all_month_year_boundaries_source_backed=True,
        mark_domain='Separate fullmonthly2021Jan-Nov and2022Oct-Nov; Dec2021-JanSep2022 fullmarkgap remains. No trade substitution or continuous600mark claim.',
        nominal_nonoverlapping_date_blocks={'7day_full_blocks':698//7,'30day_full_blocks':698//30},
        independence='Five correlated assets are not3490 independent experiments. Nominal block counts are not a statistical effective-sample estimate.',
        fits=0,wallets=0,labels_created=0,random_seed='NOT_APPLICABLE_DETERMINISTIC_SOURCE_ARITHMETIC',
        cold_scope='Actualrawminute andpriorboundary checks reused fromfive published phase receipts. This join itself only recovers publishedfeaturebytes/sourcechain; no new CSV scan or providerdownload.')


def run(commit,output,expected=None):
    assert output.resolve().is_relative_to(Path('/workspace')) and not output.exists();output.mkdir()
    full,proof=assemble(commit)
    np.savez_compressed(output/'DAILY_CONTINUOUS.npz',symbol_order=np.asarray(SYMBOLS),**full)
    proof['daily_continuous_SHA256']=digest((output/'DAILY_CONTINUOUS.npz').read_bytes())
    if expected is not None:
        with np.load(expected,allow_pickle=False) as a:
            assert tuple(a['symbol_order'])==SYMBOLS
            for k,v in full.items():np.testing.assert_array_equal(v,a[k])
        proof['cold_join_expected_feature_vectors_exact']=True
    save(output/'COVERAGE.json',proof);print(json.dumps({k:v for k,v in proof.items() if k!='phases'},indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--expected',type=Path);a=p.parse_args();run(a.commit,a.output,a.expected)
