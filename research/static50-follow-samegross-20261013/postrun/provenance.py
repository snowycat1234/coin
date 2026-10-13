"""Stdlib-only identity and terminal verification for the fixed six samegross cases."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
MODULE=ROOT/'coin_follow_samegross_20261013'
STATE=MODULE/'state_20261013T1316Z'
BASE_IDS=tuple(f'Y{year}_{arm}' for year in (2023,2024,2025) for arm in ('STATIC50_SAMEGROSS','FOLLOW_POOL_SAMEGROSS'))
CASE_IDS=tuple(base+'_FINE_ORIGINAL' for base in BASE_IDS)
PREEXECUTION_COMMIT='6eccc22a23420f52d92f1303be6d7731087be81e'
PINS={'FROZEN_CODE.json': '6ef8795088532bfe95721449c4efd9177c0283121ebe3ba1ab500471beae3c93', 'samegross_freeze.py': '6a81bf9fe8e6e8e5319c80f0da0c0cc88bd658f20f7ebfcc375100dee852f83d', 'REVIEW_RECEIPT.json': '129f1d856ed22df29a6fb2b0beea2ecfbbd381184ac8192ad3de1d5160341586', 'CASE_BINDINGS.json': 'b93be0b7d67d75705ef453853e95e72659ea2ef16c7accb08edc16cdbc768b14', 'run_cases.py': '5393d434cccf38bf33d36406485259c0f1079af6d750f8d599f2b564fa1983e5', 'resource_gate.py': 'f32c923fa0e54825c3953d2db3b268aaa54d42d4baac93b6cd6d0d109bbc9899'}

TERMINAL_PINS={'coin_follow_samegross_20261013/publication_payload/PUBLICATION_RECEIPT.json': '06f0f161a617817d6b0f63d16113720aabb46db265b38377eced55a783fb682b', 'coin_follow_samegross_20261013/state_20261013T1316Z/RESOURCE_RECEIPTS.json': '5c18e6bed0c42c79f278eab6278be4bdad3073161a7838092ad13642af703964', 'coin_follow_samegross_20261013/state_20261013T1316Z/RUN_BINDING.json': '9aa1cf95ebcc47a4cbcf780f505c1a9d42d08b4a4bdc50745014b6963f836dc5', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2023_FOLLOW_POOL_SAMEGROSS_FINE_ORIGINAL/ACCOUNT.json': '99e27f9080acc3e6e1bbb4b31c5f9a6575bb1ac96be46478c61d7d0f50a816fc', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2023_FOLLOW_POOL_SAMEGROSS_FINE_ORIGINAL/BINDING.json': 'eb3a7cf666f37324c2defbfab6e1d2388580c7f90d0f9e26006971791adc8805', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2023_FOLLOW_POOL_SAMEGROSS_FINE_ORIGINAL/DAILY.csv': '621cf9b0b9942f2a88ef69992115429cc710c8649fa762df5fb6828db92c96e8', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2023_FOLLOW_POOL_SAMEGROSS_FINE_ORIGINAL/MINUTE_NUMERIC.json': '3429286ed72f096e30477c8865dcf46234e4dd320de553cb4779b070c145fde5', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2023_FOLLOW_POOL_SAMEGROSS_FINE_ORIGINAL/RESULT.json': '7d5f57441fc7e4febc67b52ff4520dfed412a5f5fa087bd61ebabbe16c075f2c', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2023_FOLLOW_POOL_SAMEGROSS_FINE_ORIGINAL/recovery/POINTER.json': '477643caba8b7a0b1d9bbe7bfd2e999eddd186c09a8bbcaa53708c0ea9dd1188', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2023_FOLLOW_POOL_SAMEGROSS_FINE_ORIGINAL/recovery/STATE_000525600.json.gz': '849e65812e86a24613e95f565cd2bd580fd1f92225f5bc549bfb63d3258ba796', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2023_STATIC50_SAMEGROSS_FINE_ORIGINAL/ACCOUNT.json': '833a4a1f35551632a90130f424489877329c906bd0e4ddae98b5354528a1eb31', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2023_STATIC50_SAMEGROSS_FINE_ORIGINAL/BINDING.json': '6bf75fb3e8ccd58b882ab19a08430e45d5ab7444be1834944adac379a1b029ba', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2023_STATIC50_SAMEGROSS_FINE_ORIGINAL/DAILY.csv': '03d1cf50597e8a797f41591f7da1208c1df4eac22916c58dc73eaeec161efc39', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2023_STATIC50_SAMEGROSS_FINE_ORIGINAL/MINUTE_NUMERIC.json': '9a3020ddfb0b0ff843b5299b3d454da3acce6b62cd945968bdbd8ea493fdafe8', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2023_STATIC50_SAMEGROSS_FINE_ORIGINAL/RESULT.json': 'b6bc769fe8e3373f45209800c60edf6b943728003989bf5119ceb8e2073987c2', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2023_STATIC50_SAMEGROSS_FINE_ORIGINAL/recovery/POINTER.json': 'f875d71f83df8239cf669d45b48a24086f043715d859968b95a4cbd2ac4576bf', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2023_STATIC50_SAMEGROSS_FINE_ORIGINAL/recovery/STATE_000525600.json.gz': '6cb23ceea3d071f8f2d5abca8596912b6264cbe4464a0d138bd4659236ce74b2', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2024_FOLLOW_POOL_SAMEGROSS_FINE_ORIGINAL/ACCOUNT.json': '6a6329c9841eec0d0a6d7d6c3e169b645ae9651f868ba6b7932a09363878bf4f', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2024_FOLLOW_POOL_SAMEGROSS_FINE_ORIGINAL/BINDING.json': 'd6fca907309322a906c6cba29778925f1c2a8235af881000a06b9a77382c39b2', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2024_FOLLOW_POOL_SAMEGROSS_FINE_ORIGINAL/DAILY.csv': 'e2d7b615786ea8b088bff8ce782a0f69b5d955b2ab7840aa9cc3aa386a116916', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2024_FOLLOW_POOL_SAMEGROSS_FINE_ORIGINAL/MINUTE_NUMERIC.json': '833ccdf4deb1203c678efdb21acb0bae0fc2bf3aa700db55ecda3faf56efab0f', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2024_FOLLOW_POOL_SAMEGROSS_FINE_ORIGINAL/RESULT.json': 'e5b8213aa11daa259cdf5c45bfe8f9cef41118e679ad4ccd839cf28e03a748f3', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2024_FOLLOW_POOL_SAMEGROSS_FINE_ORIGINAL/recovery/POINTER.json': '52d3e50906c7b9f70c5de34124e78fc9c038a6bd8cbe51c5505e2b344aa4a3c6', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2024_FOLLOW_POOL_SAMEGROSS_FINE_ORIGINAL/recovery/STATE_000527040.json.gz': '7c342c85888f4381227db03a3c31095c314adad7052569cbca3553ec91aee890', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2024_STATIC50_SAMEGROSS_FINE_ORIGINAL/ACCOUNT.json': 'a031f62b60d954f5c9a83b23bd1e81708566342733cb3757f5188bf224479786', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2024_STATIC50_SAMEGROSS_FINE_ORIGINAL/BINDING.json': '83b48dbd23e81f1160954f3078a8b823050dfe68396032355532f6e41c33a7c8', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2024_STATIC50_SAMEGROSS_FINE_ORIGINAL/DAILY.csv': 'b992edc257a5d618c900c7a4e9a9cbdefe346c5d3d9b05c1e021b1d66e0542b1', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2024_STATIC50_SAMEGROSS_FINE_ORIGINAL/MINUTE_NUMERIC.json': 'b27f41633757a4acc052419b75c03af2b63298a43a17f2c52c091bed3c234e16', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2024_STATIC50_SAMEGROSS_FINE_ORIGINAL/RESULT.json': '8f49b3762debd40c260e88742ed44c129cdeaaed694af36f004229a9aebf3000', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2024_STATIC50_SAMEGROSS_FINE_ORIGINAL/recovery/POINTER.json': '029271709c01b8dd5d280c87fa01d22adeb3b5ff705c9252ff66c7863902b019', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2024_STATIC50_SAMEGROSS_FINE_ORIGINAL/recovery/STATE_000461654.json.gz': '1292045c604d881b69b8abbea35608396c62ec8802f47b48261676a3d8edd395', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2025_FOLLOW_POOL_SAMEGROSS_FINE_ORIGINAL/ACCOUNT.json': 'd815ea3651e010f0ecbb7087ea9d6d8bd39242737f5a605688e38223da30c16c', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2025_FOLLOW_POOL_SAMEGROSS_FINE_ORIGINAL/BINDING.json': 'a7d750b36841ff848fa7105388fc59bc301e2fcb712c25b2a5cfd5003ad5c7f8', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2025_FOLLOW_POOL_SAMEGROSS_FINE_ORIGINAL/DAILY.csv': '779fb466484894afb40fffad418f1199b79c930fc53619bafd58e0ea66d39f2a', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2025_FOLLOW_POOL_SAMEGROSS_FINE_ORIGINAL/MINUTE_NUMERIC.json': 'e9b624378451429d3b8b1769ea471c1842e8b506791e8b62a710e075ed78da7d', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2025_FOLLOW_POOL_SAMEGROSS_FINE_ORIGINAL/RESULT.json': '72fcef44df35e406ff8fffc9d734256321da62f742b99d7a73f9c8f7e3124184', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2025_FOLLOW_POOL_SAMEGROSS_FINE_ORIGINAL/recovery/POINTER.json': '123fcbee9e05aae265dec2c82fbea373395252c01da26d9daab65ab3eda3bf0f', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2025_FOLLOW_POOL_SAMEGROSS_FINE_ORIGINAL/recovery/STATE_000525600.json.gz': '467fa0abe61f38d3f6703f2c89025ac30efd74191ea45c7e60f91a05e5913f7f', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2025_STATIC50_SAMEGROSS_FINE_ORIGINAL/ACCOUNT.json': '10de2343a20f4d8b72e2e5240714fcbef09a7b16141eb8614861e9e566c6e1a8', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2025_STATIC50_SAMEGROSS_FINE_ORIGINAL/BINDING.json': '5ba970d693ae445d13d90a0f04d7ad56e237e1199937b72e3f419f5badfc118c', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2025_STATIC50_SAMEGROSS_FINE_ORIGINAL/DAILY.csv': 'ecfcc5c8d709f1710d12d276c64048fbb6ba4e7200b76d30168de08b1ed96aee', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2025_STATIC50_SAMEGROSS_FINE_ORIGINAL/MINUTE_NUMERIC.json': '7aea182a0177a09a3702232bcdf2bb92918c2d446e89e6adcf4e91abbdf59f45', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2025_STATIC50_SAMEGROSS_FINE_ORIGINAL/RESULT.json': 'd027453c736ceee4e4c28b9dc48f264d16aec93cf808dea15d3c6766e64d4b23', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2025_STATIC50_SAMEGROSS_FINE_ORIGINAL/recovery/POINTER.json': '631ff187e17c52018b6435a9d5c3efc520d97f85cb7888ef4385171bdec294d6', 'coin_follow_samegross_20261013/state_20261013T1316Z/Y2025_STATIC50_SAMEGROSS_FINE_ORIGINAL/recovery/STATE_000525600.json.gz': 'e5ddd5d22857c03caa770f8ad899a09dec6d013fc6397e2d02b756ce00a77770', 'coin_quantity_resolution_20261013/state_20261013/Y2023_STATIC50_FINE_ORIGINAL/ACCOUNT.json': '5d74f8296178f0aa5d8771072ee6d3b8dddcb6d6e870ff0d6c5162a39477c5b7', 'coin_quantity_resolution_20261013/state_20261013/Y2023_STATIC50_FINE_ORIGINAL/BINDING.json': 'b72a7b8ef2c3b7870c905d356d4d992514e26d8eb8537081799441eff5fd8e5f', 'coin_quantity_resolution_20261013/state_20261013/Y2023_STATIC50_FINE_ORIGINAL/MINUTE_NUMERIC.json': '460dbf7fe1eae9b427407b4437dd3521a426d54552ee6826c9ab239b52e9fbcd', 'coin_quantity_resolution_20261013/state_20261013/Y2023_STATIC50_FINE_ORIGINAL/RESULT.json': 'b2d7dc9bb226c5afc9eb4407d1446969d230077ba8561f5668810c925d1b05c0', 'coin_quantity_resolution_20261013/state_20261013/Y2023_STATIC50_FINE_ORIGINAL/recovery/POINTER.json': 'c54426bc98a8b112fdfab5ee74eea2f6e38177c1bdd085d9b11ed7d2e493f437', 'coin_quantity_resolution_20261013/state_20261013/Y2024_STATIC50_FINE_ORIGINAL/ACCOUNT.json': 'dc1e8d1ff753c08fd14449f631e8b97de2103cc557a0c61a18f55690ddb5cb38', 'coin_quantity_resolution_20261013/state_20261013/Y2024_STATIC50_FINE_ORIGINAL/BINDING.json': '07e738f8a59ca0be141e7cc7e06a7563161d34a6254a851d057dd964ba7f24c5', 'coin_quantity_resolution_20261013/state_20261013/Y2024_STATIC50_FINE_ORIGINAL/MINUTE_NUMERIC.json': 'ce9aa43ef48cf81c630d52fb47a12741a4941b5c530cbb4e1d9df2ec55fb9960', 'coin_quantity_resolution_20261013/state_20261013/Y2024_STATIC50_FINE_ORIGINAL/RESULT.json': '7d44047a38b272fbfda3270856c6ec88fa808957b7a9cba36bacff9931560d7d', 'coin_quantity_resolution_20261013/state_20261013/Y2024_STATIC50_FINE_ORIGINAL/recovery/POINTER.json': '9f213ea1ad76ede0434645bed03151278875d1c4754e73213a20e7b01b384052', 'coin_quantity_resolution_20261013/state_20261013/Y2025_STATIC50_FINE_ORIGINAL/ACCOUNT.json': 'c2f9fddea01a4abffa2f9247da1189773c344cb56797e225e02b63975be8978d', 'coin_quantity_resolution_20261013/state_20261013/Y2025_STATIC50_FINE_ORIGINAL/BINDING.json': '659f30b9b3bc86c0ae500aae138ee6090cf2ae5b117a4accd9a49a57ef128438', 'coin_quantity_resolution_20261013/state_20261013/Y2025_STATIC50_FINE_ORIGINAL/MINUTE_NUMERIC.json': '742ea5bb73dc3606c8abc6579bd7996226c71697d3d5fa25426358f0df9f6cda', 'coin_quantity_resolution_20261013/state_20261013/Y2025_STATIC50_FINE_ORIGINAL/RESULT.json': '753e8ed4432b17983033eed3cc15f7c11065b453ce3890b767ea7c3bd28bbfe5', 'coin_quantity_resolution_20261013/state_20261013/Y2025_STATIC50_FINE_ORIGINAL/recovery/POINTER.json': 'bb34f64025e7441d62982a39cfc7cd38d8ff8dce50b96c50121afaa50a6ff448'}

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text())
def pinned(path,expected,label):
    if Path(path).is_symlink() or sha(path)!=expected: raise ValueError('Pinned bytes changed: '+label)

def verify_plan(plan):
    cases=plan.get('cases',[])
    if (tuple(c.get('case_id') for c in cases)!=BASE_IDS or plan.get('case_count')!=6
            or plan.get('modes')!=['ORIGINAL'] or plan.get('wallets_to_rerun')!=0
            or plan.get('new_historical_wallets_executed')!=0
            or plan.get('status')!='FROZEN_SIX_FINE_CASES_PRE_GO_ZERO_HISTORY'):
        raise ValueError('Expected only explicit fixed six-case samegross plan')
    for c in cases:
        if (c['case_id']!=f"Y{c['year']}_{c['arm']}" or len(c['symbols'])!=5
                or c['calendar'][0]>=c['calendar'][1] or c.get('protective_enabled') is not False
                or set(c['reused_original_STATIC50_fine_comparator'])!={'BINDING.json','ACCOUNT.json','RESULT.json','MINUTE_NUMERIC.json','recovery/POINTER.json'}):
            raise ValueError('Case identity/calendar/comparator differs')
    return list(CASE_IDS)

def verify_frozen_inputs(module=MODULE,plan=None):
    module=Path(module)
    for name,digest in PINS.items(): pinned(module/name,digest,name)
    spec=importlib.util.spec_from_file_location('samegross_observer_verified_freeze',module/'samegross_freeze.py')
    freeze=importlib.util.module_from_spec(spec);spec.loader.exec_module(freeze)
    freeze.verify(module,require_review=True)
    actual=read(module/'CASE_BINDINGS.json')
    if plan is not None and plan!=actual: raise ValueError('Supplied plan differs')
    verify_plan(actual)
    for case in actual['cases']:
        for field in ('source_index','target_archive'):
            pinned(ROOT/case[field+'_local_locator'],case[field+'_SHA256'],field)
        for name,row in case['reused_original_STATIC50_fine_comparator'].items():
            pinned(ROOT/row['local_locator'],row['SHA256'],case['case_id']+':oldS:'+name)
    return actual

def verify_controller_population(controller: dict, ids: list[str]) -> None:
    status = controller.get('status')
    unstarted = controller.get('unstarted_case_ids')
    per_case = controller.get('per_case')
    if (status not in ('ALL_CASES_FINISHED', 'STOP_PARTIAL') or not isinstance(unstarted, list)
            or len(unstarted) != len(set(unstarted)) or not set(unstarted) <= set(ids)
            or not isinstance(per_case, dict) or set(per_case) != set(ids) - set(unstarted)):
        raise ValueError('Terminal controller receipt lacks the entire fixed population')
    for identity, row in per_case.items():
        if (type(row.get('exit_code')) is not int or type(row.get('peak_RSS')) is not int
                or row['peak_RSS'] < 0):
            raise ValueError('Malformed terminal worker receipt: ' + identity)
        if status == 'ALL_CASES_FINISHED' and (row['exit_code'] != 0
                or row.get('stop_reason') is not None or row['peak_RSS'] > 2_000_000_000):
            raise ValueError('Finished controller lacks clean bounded workers')
    if status == 'ALL_CASES_FINISHED' and unstarted:
        raise ValueError('Finished controller still has unstarted cases')
    if status == 'STOP_PARTIAL' and not unstarted and all(
            row['exit_code'] == 0 and row.get('stop_reason') is None for row in per_case.values()):
        raise ValueError('Partial controller has no failed/unstarted case')


def verify_terminal_run(state=STATE,module=MODULE,plan=None):
    plan=verify_frozen_inputs(module,plan);ids=verify_plan(plan)
    binding=read(Path(state)/'RUN_BINDING.json')
    expected={'parent_GO':True,'fine_case_ids':ids,'runner_SHA256':PINS['run_cases.py'],
        'bindings_SHA256':PINS['CASE_BINDINGS.json'],
        'fine_account_SHA256':sha(ROOT/'coin_quantity_resolution_20261013/fine_account.py'),
        'freeze_manifest_SHA256':PINS['FROZEN_CODE.json'],
        'fine_profile_SHA256':plan['fine_profile_SHA256'],'coarse_profile_SHA256':plan['coarse_profile_SHA256']}
    for key,value in expected.items():
        if binding.get(key)!=value: raise ValueError('Samegross RUN_BINDING differs: '+key)
    nonce=binding.get('nonce')
    if not isinstance(nonce,str) or len(nonce)!=32 or any(c not in '0123456789abcdef' for c in nonce):
        raise ValueError('Historical run nonce missing')
    controller=read(Path(state)/'RESOURCE_RECEIPTS.json');verify_controller_population(controller,ids)
    if controller['status']!='ALL_CASES_FINISHED': raise ValueError('This fixed observer binds the completed six-case run only')
    for identity in ids:
        for name in ('RESULT.json','ACCOUNT.json','MINUTE_NUMERIC.json','BINDING.json','DAILY.csv','recovery/POINTER.json'):
            if not (Path(state)/identity/name).is_file(): raise ValueError('Clean worker lacks output:'+identity+':'+name)
    return ids

def dispatch_case(identity,plan):
    verify_plan(plan)
    if identity not in CASE_IDS: raise ValueError('Case outside fixed six-case dispatcher')
    return plan['cases'][CASE_IDS.index(identity)]

def case_availability(state: Path, identity: str, controller: dict) -> str:
    if identity not in CASE_IDS:
        raise ValueError('Unknown case')
    path = Path(state) / identity
    if identity in controller['unstarted_case_ids']:
        if path.exists():
            raise ValueError('Unstarted case unexpectedly has wallet state')
        return 'UNSTARTED_NO_WALLET'
    if not (path / 'BINDING.json').is_file() or not (path / 'recovery/POINTER.json').is_file():
        return 'STARTED_NO_RECOVERABLE_CHECKPOINT'
    return 'ACCEPTED_RESULT' if (path / 'RESULT.json').is_file() else 'RECOVERABLE_PARTIAL_CHECKPOINT'


def verify_case_binding(binding,identity,case,state=STATE):
    plan=read(MODULE/'CASE_BINDINGS.json')
    expected={'case_id':identity,'year':case['year'],'arm':case['arm'],'mode':'ORIGINAL',
        'calendar':case['calendar'],'capital_USDT':10000,
        'source_index_SHA256':case['source_index_SHA256'],'target_archive_SHA256':case['target_archive_SHA256'],
        'target_array_SHA256':case['target_array_SHA256'],'fine_profile_SHA256':plan['fine_profile_SHA256'],
        'fine_account_class':'conditional_shared_default_fine_grid_sensitivity_v1',
        'fine_account_SHA256':sha(ROOT/'coin_quantity_resolution_20261013/fine_account.py'),
        'freeze_manifest_SHA256':PINS['FROZEN_CODE.json'],'coarse_profile_SHA256':plan['coarse_profile_SHA256'],
        'guard_policy_SHA256':sha(ROOT/'coin_margin_protective_policy_20261013/protective_policy.py'),
        'scheduler_SHA256':sha(ROOT/'coin_native_half_mix_20261013/repo/scripts/investment/resumable_perpetual.py'),
        'account_SHA256':sha(ROOT/'coin_native_half_mix_20261013/repo/src/quant/perpetual_account.py'),
        'run_binding_SHA256':sha(Path(state)/'RUN_BINDING.json'),
        'source_gate_SHA256':plan['source_gate_SHA256'],'protective_enabled':False,
        'common_gross_is_target_only':True,'persist_cash_close':False,'final_day_target_zero':False}
    if binding!=expected: raise ValueError('Samegross exact case binding differs')

def input_file_hashes(state: Path, identity: str, pointer: dict) -> dict:
    base = Path(state) / identity
    names = ['BINDING.json', 'recovery/POINTER.json', 'recovery/' + pointer['snapshot_path'],
             'RESULT.json', 'ACCOUNT.json', 'MINUTE_NUMERIC.json', 'DAILY.csv']
    paths = [base / name for name in names if (base / name).is_file()]
    paths += [base / 'recovery' / row['path'] for row in pointer['chunks']]
    paths += [Path(state) / 'RUN_BINDING.json', Path(state) / 'RESOURCE_RECEIPTS.json']
    return {str(p.relative_to(ROOT)): sha(p) for p in paths}
