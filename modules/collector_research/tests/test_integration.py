"""Local synthetic fixtures only; never use these as market observations."""
import hashlib
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]


def run(env, *args, success=True):
    p = subprocess.run([sys.executable, '-m', 'pipeline.cli', *args], cwd=ROOT,
                       env=env, capture_output=True, text=True, timeout=45)
    if success:
        assert p.returncode == 0, p.stdout + p.stderr
    else:
        assert p.returncode != 0, p.stdout
    return p


def environment(tmp):
    env = os.environ.copy()
    env.update(WORK_DIR=str(tmp/'work'), RAW_CACHE_DIR=str(tmp/'old/raw'), SYMBOLS='BTCUSDT',
               WARMUP_START='2022-01-01', START_DATE='2022-01-01', END_DATE='2022-01-06',
               TABLE_FORMAT='csv.gz', MIN_FREE_GIB='0', MAX_WORK_GIB='100',
               MIN_HISTORY_DAYS='2', LOOKBACK_DAYS='2', HORIZON_DAYS='2', EMBARGO_DAYS='2',
               HTTP_RETRIES='0', MODEL_FAMILIES='PER_ASSET_XGB', FUNDING_RATE_SCALE='UNKNOWN')
    return env


def build_raw(env, partial=False):
    n = 6*1440
    t = pd.date_range('2022-01-01', periods=n, freq='min', tz='UTC').as_unit('ms').asi8
    base = 100 + np.arange(n)*.0001
    data = np.column_stack([t, base, base+1, base-1, base+.1, np.ones(n), t+59999,
                            np.ones(n)*100, np.ones(n), np.zeros(n), np.zeros(n), np.zeros(n)])
    for fam in ('klines', 'markPriceKlines', 'premiumIndexKlines', 'fundingRate'):
        folder = Path(env['RAW_CACHE_DIR'])/fam/'BTCUSDT'; folder.mkdir(parents=True)
        middle = 'fundingRate' if fam == 'fundingRate' else '1m'
        fn = f'BTCUSDT-{middle}-2022-01.zip'; path = folder/fn
        if fam == 'fundingRate':
            ft = pd.date_range('2022-01-01', periods=18, freq='8h', tz='UTC').as_unit('ms').asi8
            d = pd.DataFrame({'calc_time':ft,'funding_interval_hours':8,'last_funding_rate':.0001})
            csv = d.to_csv(index=False)
        else:
            d = pd.DataFrame(data.copy())
            if fam == 'premiumIndexKlines': d.iloc[:,1:5] = np.array([-.001,.001,-.002,-.0005])
            if partial and fam == 'klines': d = d.drop(index=2*1440+500)
            csv = d.to_csv(index=False, header=False, float_format='%.17g')
        with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr(fn.removesuffix('.zip')+'.csv',csv)
        Path(str(path)+'.CHECKSUM').write_text(hashlib.sha256(path.read_bytes()).hexdigest()+'  '+fn+'\n')


def test_full_collector_verify_export_raw_cache_resume(tmp_path):
    env = environment(tmp_path); build_raw(env, partial=True)
    # Old completion flags MUST NOT skip execution.
    (Path(env['WORK_DIR'])/'state').mkdir(parents=True)
    (Path(env['WORK_DIR'])/'state/normalize.done').write_text('old invalid marker')
    run(env, 'collect')  # cache-only transport: four already checksum-bound ZIPs
    report = Path(env['WORK_DIR'])/'reports'
    audit = json.loads((report/'data_audit.json').read_text())[0]
    assert audit['complete_kline_days'] == 5 and audit['internal_incomplete_kline_days'] == 1
    dpath = Path(env['WORK_DIR'])/'data/normalized/BTCUSDT_daily.csv.gz'
    d = pd.read_csv(dpath)
    assert pd.isna(d.loc[2,'close']) and d.loc[2,'rows'] == 1439
    manifest = json.loads((report/'DATASET_MANIFEST.json').read_text())
    assert len(manifest['artifacts']) == 6 and not manifest['full_requested_coverage_certified']
    canonical = pd.read_csv(Path(env['WORK_DIR'])/'data/normalized/minute/BTCUSDT/klines/2022-01.csv.gz')
    assert (canonical.close_us == canonical.open_us + 60_000_000).all()
    minute_sha = hashlib.sha256(canonical.to_csv(index=False).encode()).hexdigest()
    run(env, 'verify')
    run(env, 'normalize')
    assert minute_sha == hashlib.sha256(pd.read_csv(Path(env['WORK_DIR'])/'data/normalized/minute/BTCUSDT/klines/2022-01.csv.gz').to_csv(index=False).encode()).hexdigest()
    # Unknown unit blocks labels, not collection.
    assert 'unconfirmed' in run(env,'labels',success=False).stdout.lower()
    env['FUNDING_RATE_SCALE'] = '1.0'; run(env,'labels')
    out = tmp_path/'portable.zip'; run(env,'export','--include-raw','--output',str(out))
    extracted = tmp_path/'portable'
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        assert not any('proxy' in n or 'venv' in n or 'weights' in n for n in z.namelist())
        z.extractall(extracted)
    p = subprocess.run([sys.executable, str(extracted/'verify_bundle.py')],capture_output=True,text=True,timeout=20)
    assert p.returncode == 0 and 'PASS:' in p.stdout
    run(env,'export','--output',str(out),success=False)
    with dpath.open('ab') as f: f.write(b'tampered')
    assert 'corrupt' in run(env,'verify',success=False).stdout.lower()


def test_empty_dataset_fails_and_still_writes_audit(tmp_path):
    env = environment(tmp_path)
    p = run(env,'normalize',success=False)
    assert 'No complete trade day' in p.stdout
    report = Path(env['WORK_DIR'])/'reports/DATASET_MANIFEST.json'
    assert json.loads(report.read_text())['status'] == 'FAILED_NO_COMPLETE_TRADE_DAYS'
    run(env,'verify',success=False)


def test_config_change_invalidates_manifest(tmp_path):
    env = environment(tmp_path); build_raw(env)
    run(env,'normalize')
    env['END_DATE']='2022-01-05'
    assert 'config changed' in run(env,'verify',success=False).stdout


def test_parquet_roundtrip_when_dependency_available(tmp_path,monkeypatch):
    pytest.importorskip('pyarrow')
    from pipeline.storage import write_table,read_table
    monkeypatch.setenv('TABLE_FORMAT','parquet')
    d = pd.DataFrame({'dt':pd.date_range('2022-01-01',periods=3,tz='UTC'),'close':[1.,np.nan,3.], 'complete_kline':[True,False,True]})
    pd.testing.assert_frame_equal(d,read_table(write_table(d,tmp_path/'prices')))


def test_all_label_and_xgb_research_stages_four_folds(tmp_path):
    pytest.importorskip('xgboost')
    env = environment(tmp_path)
    env.update(END_DATE='2024-12-31', START_DATE='2022-01-01', LOOKBACK_DAYS='16', MIN_HISTORY_DAYS='200',
               HORIZON_DAYS='10', EMBARGO_DAYS='10', MIN_TRAIN_ASSET_ROWS='60', MIN_FOLDS='4',
               CV_START='2023-01-01', XGB_ESTIMATORS='3', FUNDING_RATE_SCALE='1.0')
    # This fixture starts at the normalized daily contract; it does NOT pretend to be a minute source.
    script = r'''
import numpy as np, pandas as pd
from pipeline.common import DATA,REPORTS,code_digest,dump,init_dirs,E
from pipeline.storage import write_table
from pipeline.normalize import artifact
init_dirs()
dt=pd.date_range(E('WARMUP_START'),E('END_DATE'),tz='UTC'); n=len(dt)
p=100*np.exp(np.cumsum(.0001+.005*np.sin(np.arange(n)/13)))
d=pd.DataFrame(dict(dt=dt,symbol='BTCUSDT',open=p,high=p*1.01,low=p*.99,close=p,
quote_volume=1000+np.arange(n),premium=0.,funding=.0001,exec_price=p,
mark_funding_per_unit=.0001*p,complete_kline=True,complete_mark=True,
complete_premium=True,complete_funding=True,funding_interval_complete=True))
path=write_table(d,DATA/'normalized/BTCUSDT_daily')
dump(dict(status='VALIDATED_AVAILABLE_SOURCE_ONLY',synthetic_test_fixture=True,
code_sha256=code_digest(),source_config={k:E(k) for k in ('FAMILIES','TABLE_FORMAT')},
date_range={'start':E('WARMUP_START'),'end_inclusive':E('END_DATE')},symbols=['BTCUSDT'],
artifacts=[artifact(path,'daily')],source_receipts=[]),REPORTS/'DATASET_MANIFEST.json')
'''
    p = subprocess.run([sys.executable,'-c',script],cwd=ROOT,env=env,capture_output=True,text=True,timeout=30)
    assert p.returncode == 0,p.stderr
    first = run(env,'research')
    assert 'FOLD 4' in first.stdout
    study_roots = list((Path(env['WORK_DIR'])/'research').iterdir()); assert len(study_roots)==1
    study=study_roots[0]
    results=pd.read_csv(study/'model_results.csv')
    assert len(results)==20 and results.days.min()>100 and np.isfinite(results.net).all()
    frozen=json.loads((study/'FROZEN_RESEARCH_WINNER.json').read_text())
    assert frozen['deployment_authorized'] is False and frozen['exact_minute_wallet_replay']=='NOT_RUN'
    if not frozen['promotion_gate_pass']:
        assert not (study/'FINAL_MODEL.json').exists()
    second = run(env,'train'); assert second.stdout.count('RESUME verified') == 4
    env['FEE_BP_PER_SIDE']='6.0'
    assert 'configuration changed' in run(env,'train',success=False).stdout


def test_multi_asset_calendar_missing_symbol_is_explicit(tmp_path):
    env=environment(tmp_path); build_raw(env)
    env['SYMBOLS']='BTCUSDT,ETHUSDT'
    run(env,'normalize')
    run(env,'verify')
    report=Path(env['WORK_DIR'])/'reports/data_audit.json'
    audits=json.loads(report.read_text())
    assert audits[0]['complete_kline_days']==6
    assert audits[1]['symbol']=='ETHUSDT' and audits[1]['complete_kline_days']==0
    assert audits[1]['listing_status']=='NOT_INFERRED_FROM_404'
    eth=pd.read_csv(Path(env['WORK_DIR'])/'data/normalized/ETHUSDT_daily.csv.gz')
    assert len(eth)==6 and eth.close.isna().all()
