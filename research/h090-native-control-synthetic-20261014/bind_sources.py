"""Bind copied, pinned cached originals. This file never reads market history."""
from pathlib import Path
import hashlib, importlib.util, json, os, sys
HERE=Path(__file__).resolve().parent
DEPS=HERE/'dependencies'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def exact_import(name,path):
    path=Path(path).resolve()
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module
    from verified_source import require_runtime
    require_runtime()
    spec.loader.exec_module(module)
    if Path(module.__file__).resolve()!=path or Path(module.__spec__.origin).resolve()!=path:
        raise ValueError('EXACT_IMPORT_IDENTITY_REQUIRED:'+name)
    return module


def verify():
    pins=json.loads((HERE/'DEPENDENCY_PINS.json').read_text())
    for name,want in pins['files_SHA256'].items():
        path=HERE/name
        if path.is_symlink() or not path.is_file() or sha(path)!=want:
            raise ValueError('DEPENDENCY_PIN_MISMATCH:'+name)
    if sha(DEPS/'account/SOURCE_FREEZE.json')!=pins['account_freeze_SHA256']:
        raise ValueError('REVIEWED_ACCOUNT_FREEZE_REQUIRED')
    if sha(DEPS/'CALENDAR_PUBLIC_REVIEW_RECEIPT.json')!=pins['calendar_review_SHA256']:
        raise ValueError('REVIEWED_CALENDAR_RECEIPT_REQUIRED')
    if sha(HERE/'h090_risk_controller.py')!=pins['h090_risk_source_SHA256']:
        raise ValueError('UNCHANGED_REVIEWED_RISK_CODE_REQUIRED')
    return pins


def load():
    from verified_source import require_runtime
    runtime=require_runtime()
    verify()
    # A cached official polars installation is reused, with no package download.
    # Outside this workspace, install the pinned version in an ordinary venv.
    cached=HERE.parent/'native_pair_replacement_review_20261014/site'
    if cached.exists():
        sys.path.insert(0,str(cached))
    cached_arrow=HERE.parent/'coin_funding_rank_dependencies_20261013/site'
    if cached_arrow.exists():
        sys.path.insert(0,str(cached_arrow))
    repo=DEPS/'repo';fine=DEPS/'fine';account=DEPS/'account'
    sys.path[:0]=[str(repo),str(repo/'src'),str(fine),str(account),str(DEPS)]
    os.environ['QUANT_ROOT']=str(repo)
    os.environ['QUANT_STATE']=str(DEPS)
    os.environ['CONFIG_FILE']='/dev/null'
    port=exact_import('h090_exact_original_port',repo/'research/static50-sma-20261013/local_native_apis.py')
    port.verify()
    runtime.register_strategy_stub(port)
    import fine_account,terminal_adapter,bounded_policy
    from scripts.investment import resumable_perpetual,bybit_cost_inputs
    from quant import perpetual_account
    for module,path in ((fine_account,fine/'fine_account.py'),
                        (terminal_adapter,DEPS/'terminal_adapter.py'),
                        (bounded_policy,account/'bounded_policy.py'),
                        (resumable_perpetual,repo/'scripts/investment/resumable_perpetual.py'),
                        (bybit_cost_inputs,repo/'scripts/investment/bybit_cost_inputs.py'),
                        (perpetual_account,repo/'src/quant/perpetual_account.py')):
        if Path(module.__file__).resolve()!=path.resolve():
            raise ValueError('FINANCIAL_IMPORT_SHADOW:'+path.name)
    target=exact_import('h090_exact_original_functions',DEPS/'original_targets/original_functions.py')
    return port,fine_account.FineGridAccount,terminal_adapter.EarlierTerminalSimulator,bounded_policy,bybit_cost_inputs,perpetual_account,target.load_originals()
