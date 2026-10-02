"""One diagnostic, using the existing source reader and audited V8 labels.

Observed future flow is never a decision-time predictor or tradable ceiling.
No scaler/model fitting, execution, fee approximation, or model pipeline here.
"""
from __future__ import annotations

import argparse
from datetime import UTC, date, datetime, timedelta
import hashlib
import json
from pathlib import Path
import resource
import subprocess
import sys
import time

import numpy as np
import polars as pl
from scipy.stats import pearsonr, spearmanr

from quant.paths import ROOT, STATE
from quant.research_fast.dataset import (
    BAR_US, DAY_US, LOCKED, START, FastSequenceDataset, ShardSpec, day_us, file_sha,
)
from quant.research_fast.trade_flow_v2 import require

sys.path.insert(0, str(ROOT))
from scripts.research_v7.oracle_flow_ceiling import Progress
from scripts.research_v7.source_view import _json
from scripts.research_v8 import labels_v5 as labels
from scripts.research_v8.registry import FIELDS, append_event

PROTOCOL = ROOT/'protocols/NONOVERLAP_MECHANISM_V8_V1.json'


def correlations(x, y):
    x, y = np.asarray(x), np.asarray(y)
    require(x.ndim == y.ndim == 1 and x.shape == y.shape, 'Aligned diagnostic observations')
    require(np.isfinite(x).all() and np.isfinite(y).all(), 'Explicit valid finite diagnostic values')
    if len(x) < 3 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return dict(rows=len(x), pearson=None, spearman=None, reason='INSUFFICIENT_OR_CONSTANT')
    # The library IID p-values are deliberately discarded: adjacent labels overlap.
    return dict(rows=len(x), pearson=float(pearsonr(x, y).statistic),
                spearman=float(spearmanr(x, y).statistic), reason=None)


def accepted_shards(source, wanted_days):
    selected = [s for s in source['binding']['selected'] if date.fromisoformat(s['day']) in wanted_days]
    require(len(selected) == 4*len(wanted_days), 'Complete explicit source calendar')
    shards = []
    for row in selected:
        manifest = Path(row['manifest_path'])
        require(file_sha(manifest) == row['manifest_sha256'], 'Accepted manifest bytes changed')
        value = _json(manifest, 131_072)
        require(value['date'] == row['day'] and value['market'] == row['market']
                and value['symbol'] == row['symbol'], 'Accepted source identity changed')
        if row['source_kind'] == 'original_daily':
            shard = ShardSpec.from_manifest(manifest)
        else:
            require(row['source_kind'] == 'independently_audited_monthly', 'Unknown source provenance')
            shard = ShardSpec.from_conversion(Path(value['feature_path']), value['conversion'], checksum_verified=True)
        require(str(shard.path) == row['parquet_path'] and shard.sha256 == row['parquet_sha256'],
                'Exact accepted source binding')
        shards.append(shard)
    return shards


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label-audit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--state-directory', type=Path, required=True)
    args = parser.parse_args()
    output, work = args.output.resolve(), args.state_directory.resolve()
    require(output.is_relative_to(ROOT/'reports') and not output.exists(), 'Exclusive output required')
    require(work.is_relative_to(STATE) and not work.exists(), 'Exclusive D-hosted STATE directory required')
    spec, gates = _json(PROTOCOL), _json(ROOT/'protocols/P1_GATE_V8.json')
    require(file_sha(ROOT/spec['fold_contract'])==spec['fold_contract_sha256'], 'Frozen fold contract changed')
    require(file_sha(ROOT/'scripts/research_v7/source_view.py')==spec['source_view_sha256'], 'Accepted source adapter changed')
    audit = _json(args.label_audit)
    require(audit.get('status') == spec['required_independent_label_audit_status'], 'Independent label acceptance required')
    # The auditor must bind the active implementation's bytes, not only its name.
    active_sha = file_sha(ROOT/spec['label_adapter'])
    audited_sources=audit.get('sources_sha256',{})
    require(audited_sources.get(spec['label_adapter'])==active_sha, 'Auditor did not bind the active label source')
    for name,digest in audited_sources.items():
        require(file_sha(ROOT/name)==digest, 'Audited dependency source changed: '+name)
    source_path = ROOT/spec['source_receipt']
    require(file_sha(source_path)==spec['source_receipt_sha256'], 'Frozen accepted 153-day receipt changed')
    source = _json(source_path)
    require(source['status'] == 'PASS_SHARED_V8_SOURCE_VIEW_153D' and source['actual_common_days'] == 153,
            'Actual independent 153-day source acceptance required')
    for name,digest in source['source_hashes'].items():
        require(file_sha(ROOT/name)==digest, 'Accepted source dependency changed: '+name)
    accepted_environment=source['registration_start']['hyperparameters']['environment']
    require(Path(sys.prefix).resolve()==Path(accepted_environment['sys_prefix']).resolve(), 'Accepted clean CPU runtime required')
    require(file_sha(ROOT/'environments/v8/uv.lock')==accepted_environment['lock_sha256'], 'Accepted complete environment lock changed')
    require([f['id'] for f in gates['folds']] == spec['all_fold_ids'], 'Frozen four-fold identity')
    work.mkdir()
    progress, started = Progress(), time.monotonic()
    progress.value['detail'] = '非重叠观测流量机制诊断；不是交易收益或预测上限'
    fold_calendar, wanted = [], set()
    lag, embargo = gates['maximum_nominal_label_lag_seconds']*1_000_000, gates['embargo_seconds']*1_000_000
    for f in gates['folds']:
        train, validation, test, end = [day_us(date.fromisoformat(f[k])) for k in
            ('train_start','validation_start','test_start','test_end_exclusive')]
        require(day_us(START) <= train < validation < test < end <= day_us(LOCKED), 'Development split only')
        cutoff = validation-embargo-lag-1
        days = []
        for split, lower, upper in [('TRAIN',train,cutoff),('OOS_SCREENING',test,end)]:
            cursor = lower//DAY_US*DAY_US
            while cursor < upper:
                days.append((split, max(lower,cursor), min(upper,cursor+DAY_US), cutoff if split == 'TRAIN' else end))
                # Closed past256; last minute may require source up to next-day +10m.
                first = datetime.fromtimestamp((max(lower,cursor)-256*BAR_US)//1_000_000, UTC).date()
                last = datetime.fromtimestamp((min(upper,cursor+DAY_US)+lag-1)//1_000_000, UTC).date()
                while first <= last:
                    wanted.add(first); first += timedelta(days=1)
                cursor += DAY_US
        fold_calendar.append((f, days))
    sources = dict(audited_sources) | source['source_hashes'] | {'scripts/research_v8/nonoverlap_mechanism.py': file_sha(Path(__file__)),
               spec['label_adapter']: active_sha, 'src/quant/research_fast/dataset.py':file_sha(ROOT/'src/quant/research_fast/dataset.py')}
    for name in ('scripts/research_v7/source_view.py','scripts/research_v7/oracle_flow_ceiling.py',
                 'src/quant/research_fast/labels.py','protocols/LABEL_CONTRACT_V8.json','protocols/P1_GATE_V8.json'):
        sources[name]=file_sha(ROOT/name)
    exact = ['bash','scripts/with_task_progress.sh','--title','V8 非重叠机制四fold诊断','--',sys.executable,
             str(Path(__file__).resolve()),'--label-audit',str(args.label_audit.resolve()),'--output',str(output),
             '--state-directory',str(work)]
    event = dict.fromkeys(FIELDS)
    event.update(event_id='v8-nonoverlap-mechanism-20261002-v1:START',event_type='FORMAL_START',
        experiment_id='v8-nonoverlap-mechanism-20261002-v1',git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        data_manifest_hash=file_sha(source_path),protocol_hash=file_sha(PROTOCOL),feature_set='PAST_AVAILABILITY_ONLY_NO_PREDICTOR_FEATURES',
        labels=spec['variants'],model_family='NONE',hyperparameters={'correlation':'official scipy Pearson/Spearman','scaler':'NONE'},
        seed='NOT_APPLICABLE_DETERMINISTIC',thresholds={'direction':'TRAIN Spearman sign, no OOS inversion'},
        cost_assumptions='NO_EXECUTED_LEDGER_NOT_EVALUABLE',all_folds=gates['folds'],success_failure='START',
        reason_for_next_experiment='Test whether flow has any subsequent nonoverlap price relationship before fitting additional predictors',
        result_influenced_later_choice=False,source_hashes=sources,environment_hash=file_sha(ROOT/'environments/v8/uv.lock'),
        label_audit_sha256=file_sha(args.label_audit.resolve()),exact_command=exact,market_models_fit=0,locked_consumed=False)
    registered=append_event(ROOT/'reports/experiment_registry.jsonl',event)
    report=dict(status='FAILED_NONOVERLAP_MECHANISM_DIAGNOSTIC',created_utc=datetime.now(UTC).isoformat(),
        registration_start=registered,classification='SCREENING_MECHANISM_ONLY',candidate='NONE',candidate_status='NO_QUALIFIED_CANDIDATE',
        net_CAGR=None,gross_executed_edge=None,net_executed_edge=None,strongest_benchmark_delta=None,
        break_even_roundtrip_cost=None,multiple_testing_corrected_evidence=None,executed_PnL_concentration=None,
        P1_gate='NOT_READY',next_gate_allowed=False,next_gate_reason='MECHANISM_DIAGNOSTIC_CANNOT_PASS_ECONOMIC_STATISTICAL_GATE',
        maximum_failure_mode='Observed-flow correlation may be only concurrent impact; this run cannot establish predictable incremental alpha.',
        data_execution_limits='AggTrades closed bars only; no BBO/depth/size/latency execution or risk-matched benchmark ledger.',
        next_highest_information_gain_experiment='Strict OOF flow surprise and matched direct-return first-layer baseline only if this diagnostic supports a stable nonoverlap mechanism; otherwise reassess route.',
        actual_standard_costs_roundtrip_bps=gates['cost_bps_standard_roundtrip'],
        source_hashes=sources,locked_consumed=False,orders_sent=0,market_models_fit=0,folds=[])
    try:
        progress.update('核对显式已验收档案',0,None,'文件')
        dataset=FastSequenceDataset(accepted_shards(source,wanted),mode='smoke')
        report['dataset_sha256']=dataset.contract_sha256
        total=sum(len(days) for _,days in fold_calendar);done=0
        for f,days in fold_calendar:
            chunks=[]
            for split,lower,upper,deadline in days:
                decisions=np.arange((lower+59_999_999)//60_000_000*60_000_000,upper,60_000_000,dtype=np.int64)
                if not len(decisions):continue
                joint=dataset.joint_rows(int(decisions[0]-256*BAR_US),int(decisions[-1]+lag))
                for variant in spec['variants']:
                    frame=labels.label_table(joint,decisions,variant,split=split,signal_kind='OBSERVED_FUTURE_FLOW_DIAGNOSTIC')
                    labels.assert_nonoverlap(frame)
                    frame=frame.with_columns(pl.lit(deadline).alias('split_maturity_deadline_us'),
                        (pl.col('label_valid') & (pl.col('label_mature_us') <= deadline)).fill_null(False).alias('diagnostic_outcome_valid'))
                    chunks.append(frame)
                done+=1;progress.update('非重叠标签与完整日历',done,total,'UTC 日',fold=f['id'],诊断模型数=0)
            frame=pl.concat(chunks).sort(['decision_us','label_variant'])
            path=work/f"{f['id']}-nonoverlap-label-calendar.parquet";frame.write_parquet(path)
            fold_result=dict(fold=f['id'],calendar_path=str(path),calendar_sha256=file_sha(path),variants=[])
            for variant in spec['variants']:
                by_variant=frame.filter(pl.col('label_variant')==variant)
                train=by_variant.filter((pl.col('split')=='TRAIN') & pl.col('diagnostic_outcome_valid'))
                test=by_variant.filter((pl.col('split')=='OOS_SCREENING') & pl.col('diagnostic_outcome_valid'))
                result=dict(variant=variant,calendar_minutes=by_variant.height,
                    train_valid=train.height,test_valid=test.height,invalid_or_immature=by_variant.height-train.height-test.height,pairs=[])
                for flow in labels.STREAMS:
                    for ret in labels.RETURN_STREAMS:
                        fn,rn=f'{flow}__future_flow',f'{ret}__subsequent_return_proxy'
                        tr=correlations(train[fn].to_numpy(),train[rn].to_numpy())
                        ts=correlations(test[fn].to_numpy(),test[rn].to_numpy())
                        direction=None if tr['spearman'] is None or tr['spearman']==0 else int(np.sign(tr['spearman']))
                        pair=dict(flow_stream=flow,return_stream=ret,primary=[flow,ret] in spec['primary_pairs'],
                                  train=tr,test=ts,train_frozen_direction=direction,
                                  OOS_sign_agreement=None if direction is None or ts['spearman'] is None else bool(direction*ts['spearman']>0),
                                  train_signed_mean_response_bps=None if direction is None or not len(test) else
                                    float(np.mean(direction*np.sign(test[fn].to_numpy())*test[rn].to_numpy())*10000),daily=[])
                        daily_test=test.with_columns((pl.col('decision_us')//DAY_US).alias('UTC_day_index'))
                        for day_frame in daily_test.partition_by('UTC_day_index',maintain_order=True):
                            metric=correlations(day_frame[fn].to_numpy(),day_frame[rn].to_numpy())
                            metric.update(UTC_day=datetime.fromtimestamp(int(day_frame['decision_us'][0])//1_000_000,UTC).date().isoformat())
                            metric.update(train_frozen_direction=direction,
                                train_signed_mean_response_bps=None if direction is None else
                                    float(np.mean(direction*np.sign(day_frame[fn].to_numpy())*day_frame[rn].to_numpy())*10000),
                                OOS_sign_agreement=None if direction is None or metric['spearman'] is None else bool(direction*metric['spearman']>0))
                            pair['daily'].append(metric)
                        result['pairs'].append(pair)
                fold_result['variants'].append(result)
            report['folds'].append(fold_result)
        report.update(status='PASS_DIAGNOSTIC_EXECUTION_NOT_P1_GATE',descriptive_hypotheses=4*3*4*2,
            limitations=['Observed flow is unavailable at original decision and is never fed to a predictor.',
                'Adjacent minute targets overlap; IID p-values are discarded. Dependence correction pending.',
                'Signed response is an observation statistic, not executable PnL, APR/CAGR, a cost ceiling or a trading strategy.',
                'The fixed four-fold and primary-pair contract cannot be changed after this output.'])
    except Exception as error:
        report.update(error_type=type(error).__name__,reason=str(error)[:2000]);raise
    finally:
        report.update(elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        with output.open('x') as stream:json.dump(report,stream,indent=2,ensure_ascii=False,allow_nan=False);stream.write('\n')
        append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=event['experiment_id']+':RESULT',event_type='FORMAL_RESULT',
            success_failure=report['status'],artifact_path=str(output.relative_to(ROOT)),artifact_sha256=file_sha(output),result_influenced_later_choice=False))
        progress.stop.set()


if __name__ == '__main__':
    main()
