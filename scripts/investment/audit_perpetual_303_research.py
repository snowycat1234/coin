"""UNRUN D045: privately reuse the accepted D043 audit main for one303D window.

Only metadata routing changes: exact94 accepted source records, the reader's
accepted date-map helper, and the fifth selector's accepted independent HOLD
reference. Original audit_case/HandLedger, cash_alias and numeric tolerances
are direct unchanged references. No producer simulate/target/QA is imported.
No Python, payload, financial run or HTTP was used to prepare this cache draft.
Root must freeze this source and ACTUAL_BINDING after the new actual closed0.
CLI --protocol --actual --run-dir --output follows the original D043 interface.
"""
from __future__ import annotations
import ast, copy, gc, hashlib
from pathlib import Path
from types import SimpleNamespace

ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
BASE='docs/archive/PERPETUAL_213_FINANCIAL_INDEPENDENT_AUDITOR_20261003_V3.py'
BASE_SHA='9c9fa8877f2b917a2a0787ce9ea40ae251bfd2b5817e8c8a036faa5ad175763b'
DATE='docs/archive/PERPETUAL_303_INDEPENDENT_ADAPTER_HELPERS_20261003_V1.py'
DATE_SHA='356086d2534539dba0aecf04b1e716d39ec1f5bb5e1c5817b80affdb38d36b31'
LOADER='docs/archive/PERPETUAL_213_INDEPENDENT_ADAPTER_HELPERS_20261003_V1.py'
LOADER_SHA='f50223ad5ec0da2be16ae3ac5447bec2d5763260566000893f1697483b7667e4'
HOLD='scripts/investment/audit_perpetual_hold_research_v3.py'
HOLD_SHA='6c8363a314c2a2779c812a593265e0ce4e14f016b4055960904132e78ae9b717'
INPUT='reports/fast_research/PERPETUAL_303D_INPUT_BINDING_20261003_V1.json'
INPUT_SHA='8b665b2829eafd192871fe4a3bc418dac1c202ed54f7d2d5494545fa6636fbfa'
SOURCE='reports/fast_research/PERPETUAL_303_SOURCE_ROOT_ACCEPTANCE_20261003_V1.json'
SOURCE_SHA='3df702c3147b10c606ba92391cff39d251247b170bea502a1b2ffc8d6a7e9ad6'
QA='reports/fast_research/PERPETUAL_303_SOURCE_INDEPENDENT_20261003_V1.json'
QA_SHA='a72c265bc821f6256600333a3fc64c9b5a738c63e3bf758e386e3a15c8287592'
PERIOD,START,END='303D','2024-09-01T00:00:00+00:00','2025-07-01T00:00:00+00:00'
STATUS='PASS_D045_TWENTY_FIXED303D_SMA_HOLD_PERPETUAL_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_NATIVE_OR_LONG_TERM_APR'
FAIL='FAIL_D045_FIXED303D_SMA_HOLD_PERPETUAL_INDEPENDENT_AUDIT'
INPUT_STATUS='PASS_D045_FIXED_303D_USDM_INPUT_SOURCE_BINDING_NOT_ECONOMICS'
SOURCE_STATUS='PASS_ROOT_D045_COMPLETE_303_USDM_SOURCE_NOT_UNIT_OR_ECONOMICS'
ACTUAL_STATUS='COMPLETE_D045_FIXED303D_PERPETUAL_SCREENING_NOT_NATIVE_OR_LONG_TERM_APR'
CONTRACT='D045_FIXED_303D_SMA_DIRECTIONS_AND_CONSTANT_LONG_CONDITIONAL_V1'
HOLD_ID='COIN_PAST30_COVARIANCE_CONSTANT_LONG_USDM_REFERENCE'
MODES=('LONG_ONLY','SHORT_ONLY','LONG_SHORT','CASH','HOLD_LONG_ONLY')
SYMS=('BTCUSDT','ETHUSDT')
RUN=STATE/'d045-perpetual-303-financial-independent-20261003-v1'
OUT=ROOT/'reports/fast_research/PERPETUAL_303_RESEARCH_INDEPENDENT_20261003_V1.json'


def need(ok,reason):
    if not bool(ok):raise ValueError(reason)


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def source_metadata(h,manifest):
    """Scalar identity checks only, before the original reader's payload IO."""
    need(manifest['status']==INPUT_STATUS and manifest['funding_rate_unit']=='UNCONFIRMED'
        and manifest['funding_unit_certified'] is False and manifest['locked_consumed'] is False
        and manifest['native_Bybit_certified'] is False
        and manifest['publication_or_exact_charge_certified'] is False
        and manifest['preceding_547_failure_preserved'] is True
        and manifest['source_rows_repaired'] is False
        and manifest['period_chosen_on_source_completeness_before_new_PnL'] is True,
        'Complete source-selected303 window; no unit/native/failed547 qualification')
    need(len(manifest['source_files'])==94 and len(manifest['windows'])==1
        and manifest['first_QA_files']==70 and manifest['reused_accepted_QA_files']==24,
        'Exact94 accepted metadata records, firstQA70 and reusedQA24')
    window=manifest['windows'][0]
    need((window['id'],window['start'],window['end_exclusive'],window['days'],window['minutes_per_symbol'])
        ==(PERIOD,START,END,303,436320)
        and window['daily_warmup_start']=='2024-02-01T00:00:00+00:00'
        and window['initial_completed_daily_warmup_days']==213,'Whole303 score and213 daily warmup')
    layout={
        'trade_1m':('klines','1m','trade:1m:','2024-09','2025-06',436320),
        'mark_1m':('markPriceKlines','1m','markPriceKlines:','2024-09','2025-06',436320),
        'funding':('fundingRate',None,'fundingRate:','2024-09','2025-06',None),
        'trade_1d_warmup':('klines','1d','trade:1d:','2024-02','2024-08',213),
        'trade_1d_score':('klines','1d','trade:1d:','2024-09','2025-06',303)}
    seen=[];evidence={};files=manifest['source_files']
    for symbol in SYMS:
        roles=window['source_ids'][symbol];declared=window['symbols'][symbol]
        need(set(roles)==set(layout) and declared['source_ids']==roles,'Exactly five used roles, no Spot/index/2h')
        for role,(kind,interval,prefix,first,last,count) in layout.items():
            ids=[prefix+symbol+':'+month for month in h.month_range(first,last)]
            need(roles[role]==ids,'Exact chronological symbol/product/month role '+symbol+' '+role)
            for identity in ids:
                item=files[identity];month=identity[-7:];entry=item['entry']
                suffix=(f'{symbol}-fundingRate-{month}.zip' if interval is None
                    else f'{interval}/{symbol}-{interval}-{month}.zip')
                url=f'https://data.binance.vision/data/futures/um/monthly/{kind}/{symbol}/{suffix}'
                expected=dict(market='futures/um',partition='monthly',kind=kind,symbol=symbol,
                    month=month,url=url,checksum_url=url+'.CHECKSUM')
                if interval is not None:expected['interval']=interval
                need(h.identity(item)==(kind,symbol,interval,month)
                    and all(entry.get(k)==v for k,v in expected.items())
                    and type(item['rows']) is int and item['rows']>0,
                    'Exact accepted official product, month, clock and actual row count')
                product='USD_M_PERPETUAL_TRADE_KLINES' if kind=='klines' else 'USD_M_PERPETUAL_'+kind
                role_evidence=item['format_evidence_role']
                need(item['product']==product and role_evidence in (
                    'FIRST_INDEPENDENT_RAW_NORMALIZED_EOF_CRC','REUSED_ACCEPTED_EXACT_BYTES_NO_ROWS_OR_CRC_REREAD')
                    and item['independent_QA_report_path']==QA and item['independent_QA_report_sha256']==QA_SHA,
                    'Exact accepted format evidence; not a repeated QA or unit certificate')
                if role_evidence=='REUSED_ACCEPTED_EXACT_BYTES_NO_ROWS_OR_CRC_REREAD':
                    need(isinstance(item['prior_QA'],dict) and item['prior_QA']['sha256']
                        ==manifest['accepted_source_roles'][item['prior_QA']['path']],
                        'Reused24 source rows retain the accepted prior QA byte identity')
                else:need(item['prior_QA'] is None,'FirstQA rows have no invented priorQA')
                evidence[role_evidence]=evidence.get(role_evidence,0)+1;seen.append(identity)
            observed=sum(files[identity]['rows'] for identity in ids)
            if count is not None:need(observed==count,'Every required complete score/warmup row')
            else:need(declared['rows_inherited_from_receipts']['funding']==observed,
                'Actual funding count from receipts, never a presumed8h schedule')
    need(len(seen)==len(set(seen))==94 and set(seen)==set(files)
        and evidence==dict(FIRST_INDEPENDENT_RAW_NORMALIZED_EOF_CRC=70,
            REUSED_ACCEPTED_EXACT_BYTES_NO_ROWS_OR_CRC_REREAD=24),
        'Every94 input used once; complete first/reused format scope')
    return window


def financial_case_interface(fin,w,case,g,hand,run,target,witness,maximum):
    need((w['days'],w['count'],case['period'])==(303,436320,PERIOD),
        'Only exact303 window, no stitched account or prefix called full')
    need(fin.CASH_TOL==1e-7 and fin.RATIO_TOL==1e-10,'Original financial tolerances unchanged')
    return fin.audit_case(w,case,g,hand,run,target,witness,maximum)


def prepare_stack(base,plan,g,report):
    pins={BASE:BASE_SHA,DATE:DATE_SHA,LOADER:LOADER_SHA,HOLD:HOLD_SHA,base.GUARD:base.GUARD_SHA}
    need(all(plan['source_hashes'].get(path)==digest for path,digest in pins.items()),
        'Every imported original main/date/reference/guard source explicitly frozen')
    old=base.load(ROOT/LOADER,LOADER_SHA,'d045_original_independent_loader')
    date=base.load(ROOT/DATE,DATE_SHA,'d045_independent303_date_adapter')
    fin,reader,reader_proof=date.prepare_financial_adapter()
    reference=base.load(ROOT/HOLD,HOLD_SHA,'d045_accepted_independent_constant_long')
    hand=base.load(ROOT/old.HAND,old.HAND_SHA,'d045_original_sparse_hand')
    h=SimpleNamespace(month_range=old.month_range,identity=old.identity,TOLERANCES=old.TOLERANCES,
        financial_case_interface=financial_case_interface)
    imported={**pins,old.FINANCE:old.FINANCE_SHA,old.HAND:old.HAND_SHA,**base.EXTRA_PINS}
    need(all(plan['source_hashes'].get(path)==digest for path,digest in imported.items()),
        'All actually imported financial/scientific/progress source bytes pinned')
    need(fin.CASH_TOL==1e-7 and fin.RATIO_TOL==1e-10 and old.TOLERANCES==plan['tolerances'],
        'Original HandLedger and exact financial tolerances')
    report['private_derivations']=dict(financial_reader=reader_proof,
        orchestration=MAIN_PROOF,independent_HOLD_reference_sha256=HOLD_SHA,
        independent_HOLD_function_direct_reference=True,original_audit_case_direct_reference=True)
    return h,fin,reader,hand,reference


def replace_span(node,before,after,label,changes):
    expected=ast.parse(before).body;replacement=ast.parse(after).body;matches=0
    signature=lambda nodes:[ast.dump(part,include_attributes=False) for part in nodes]
    for parent in ast.walk(node):
        for _,value in ast.iter_fields(parent):
            if not isinstance(value,list) or not all(isinstance(part,ast.stmt) for part in value):continue
            for index in range(len(value)-len(expected)+1):
                if signature(value[index:index+len(expected)])==signature(expected):
                    value[index:index+len(expected)]=copy.deepcopy(replacement);matches+=1;break
    need(matches==1,'Exact unique metadata orchestration span '+label)
    changes.append(dict(anchor=label,matches=matches))


def context():
    """Compile all exact private main/reader routes before any payload read."""
    need(sha(ROOT/BASE)==BASE_SHA,'Accepted immutable original D043 V3 orchestration')
    import importlib.util,sys
    spec=importlib.util.spec_from_file_location('_d045_original213_audit',ROOT/BASE)
    base=importlib.util.module_from_spec(spec);sys.modules[spec.name]=base;spec.loader.exec_module(base)
    tree=ast.parse((ROOT/BASE).read_bytes());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main']
    need(len(nodes)==1,'One accepted original audit main');node=nodes[0];original=ast.dump(node,include_attributes=False);changes=[]
    before="""need(plan['source_hashes'].get(HELPER)==HELPER_SHA and plan['source_hashes'].get(GUARD)==GUARD_SHA
            and plan['source_hashes'].get(HOOK)==HOOK_SHA
            and plan['source_hashes'].get(Path(__file__).absolute().relative_to(ROOT).as_posix())==own,
            'Own, date adapter, raw-hook and guard sources explicitly frozen')
        """
    # Parse spans independently with no inherited indentation.
    replace_span(node,before,"""need(plan['source_hashes'].get(Path(__file__).absolute().relative_to(ROOT).as_posix())==own,
        'Own exact303 independent entry frozen before payload')""",'ENTRY_SOURCE_IDENTITY',changes)
    start="""h=load(g.project(HELPER),HELPER_SHA,'d043_financial_date_adapter')
fin,reader,reader_proof=h.prepare_financial_adapter()
reference,signal_reader,signal_proof=prepare_signal_reader(h,fin)
hand=load(ROOT/h.HAND,h.HAND_SHA,'d043_financial_hand')
hook=load(ROOT/HOOK,HOOK_SHA,'d043_financial_donchian_hooks')
report['private_derivations']=dict(financial_reader=reader_proof,signal_reader=signal_proof)
need(fin.CASH_TOL==1e-7 and fin.RATIO_TOL==1e-10 and h.TOLERANCES==plan['tolerances'],'Financial body/tolerances exact')
imported={HELPER:HELPER_SHA,GUARD:GUARD_SHA,HOOK:HOOK_SHA,h.FINANCE:h.FINANCE_SHA,h.HAND:h.HAND_SHA,
    h.DONCHIAN_REFERENCE:h.DONCHIAN_REFERENCE_SHA,**EXTRA_PINS}
need(all(plan['source_hashes'].get(p)==v for p,v in imported.items()),'All imported independent financial/scientific/progress dependencies pinned')"""
    replace_span(node,start,'h,fin,reader,hand,reference=prepare_stack(BASE_MODULE,plan,g,report)',
        'ACCEPTED303_READER_AND_INDEPENDENT_CONSTANT_HOLD_STACK',changes)
    before="""need(source['status']==source_ref['required_status']==SOURCE_STATUS and source['actual_archives']==72
    and source['reused_failed_parent_complete_files']==51 and source['new_files']==21
    and source['funding_rate_unit']=='UNCONFIRMED' and source['funding_unit_certified'] is False,'Complete new72 mixed-owner source acceptance only')"""
    after="""need(source_ref['path']==SOURCE and source_sha==SOURCE_SHA
    and source['status']==source_ref['required_status']==SOURCE_STATUS and source['actual_archives']==94
    and source['first_QA_files']==70 and source['reused_accepted_QA_files']==24
    and source['source_only'] is True and source['market_arrays_read'] is False
    and source['source_QA_repeated'] is False and source['funding_rate_unit']=='UNCONFIRMED'
    and source['funding_unit_certified'] is False and source['native_Bybit_certified'] is False,
    'Exact closed94-source acceptance; firstQA70/reused24, no unit or economics certification')"""
    replace_span(node,before,after,'ACCEPTED94_SOURCE_ROOT_METADATA',changes)
    replace_span(node,"need(mref['path']==source['input_binding_path'] and manifest_sha==source['input_binding_sha256'],'Source acceptance pins this exact new input manifest')",
        "need(mref['path']==INPUT==source['input_binding_path'] and manifest_sha==INPUT_SHA==source['input_binding_sha256'],'Source acceptance pins exact303 metadata bytes')",
        'EXACT303_INPUT_METADATA',changes)
    replace_span(node,"""need(produced['id']==PERIOD and produced['input_proofs']==w['proofs']+signal_input_proofs(manifest,window)
    and produced['original_funding_events']==len(w['events'])
    and produced['score_start_us']==w['start'] and produced['score_end_exclusive_us']==w['end'],
    'Every financial input and every signal-only input exact; no array filtering or replacement')""",
        """need(produced['id']==PERIOD and produced['input_proofs']==w['proofs']
    and produced['original_funding_events']==len(w['events'])
    and produced['score_start_us']==w['start'] and produced['score_end_exclusive_us']==w['end'],
    'All exact303 financial/daily inputs; no index or twohour source array read')""",
        'DAILY_ONLY_INPUT_PROOF_BRIDGE',changes)
    replace_span(node,"""warm=dict(sources=[manifest['source_files'][window['source_ids'][s]['signal_warmup_2h'][0]] for s in SYMS])
signal,signal_sources=signal_reader(fin,manifest,warm,w)
need(signal.height==2*(372+213*12),'Full December2h warmup and all213 scored days')
report['signal_source_proofs']=signal_sources""",'pass','REMOVE_UNUSED_TWOHOUR_PAYLOAD_ROUTE',changes)
    replace_span(node,"expected_targets['DONCHIAN_LONG_ONLY']=reference.target_reference(fin,w,signal,hook)",
        "expected_targets['HOLD_LONG_ONLY']=reference.target_reference(fin,w)",'DIRECT_ACCEPTED_INDEPENDENT_HOLD_REFERENCE',changes)
    replace_span(node,'del w,signal,expected_targets','del w,expected_targets','NO_UNUSED_TWOHOUR_STATE',changes)
    exact_literals={
        'DONCHIAN_LONG_ONLY':'HOLD_LONG_ONLY',
        'D043-213D-TWENTY-FINANCIAL-INDEPENDENT-20261003-V3':'D045-303D-TWENTY-FINANCIAL-INDEPENDENT-20261003-V1',
        'SMA_DAILY_FOUR_DIRECTION_AND_DONCHIAN2H_LONG_ONLY':'SMA_DAILY_FOUR_DIRECTION_AND_CONSTANT_LONG_SHARED_RISK',
        'SEEN_COMPLETE213_JAN_JUL2024_ONE_INDEPENDENT_ACCOUNT_WINDOW':'SEEN_COMPLETE303_SEP2024_JUN2025_ONE_INDEPENDENT_ACCOUNT_WINDOW',
        'Independent accounting of fixed213 source-complete screening; preserve rejected547 interval':
            'Independent fixed303 source-complete account checks; source-selected calendar and rejected547 remain explicit',
        'Exactly four SMA modes and original Donchian long-only':'Four SMA modes and accepted constant-long shared-risk reference',
        'Same original capital/cost/caps/covariance/latency assumptions; new exact213 period':
            'Same original capital/cost/caps/covariance/latency assumptions; exact303 period',
        'No conflation of SMA LONG_ONLY and Donchian; exact configured cost/unit':'Distinct SMA/HOLD long-only selectors; exact configured cost/unit',
        '固定213日 · 20选择器独立资金与原hook因果':'固定303日 · 20选择器独立资金与过去目标',
        'UNCHANGED_D041_SCALAR_PRIOR20_CURRENT200_RAW_HOOKS':'UNCHANGED_D044_CONSTANT_LONG_CURRENT200_ELIGIBILITY_PAST30_COVARIANCE'}
    found={key:0 for key in exact_literals}
    for part in ast.walk(node):
        if isinstance(part,ast.Constant) and isinstance(part.value,str) and part.value in exact_literals:
            found[part.value]+=1;part.value=exact_literals[part.value]
        if isinstance(part,ast.keyword) and part.arg in ('source_files_verified_by_prior_accepted_QA',
            'unique_score_minutes_per_account','unique_score_days','unique_score_months'):
            expected,new={'source_files_verified_by_prior_accepted_QA':(72,94),
                'unique_score_minutes_per_account':(306720,436320),'unique_score_days':(213,303),
                'unique_score_months':(7,10)}[part.arg]
            need(isinstance(part.value,ast.Constant) and part.value.value==expected,'Original final count anchor '+part.arg)
            part.value=ast.Constant(new);changes.append(dict(anchor=part.arg,old=expected,new=new,matches=1))
        if isinstance(part,ast.keyword) and part.arg=='timeframe_minutes':
            need(isinstance(part.value,ast.IfExp) and isinstance(part.value.body,ast.Constant)
                and part.value.body.value==120 and part.value.orelse.value==1440,'Only original fifth-selector signal clock metadata')
            part.value=ast.Constant(1440);changes.append(dict(anchor='HOLD_DAILY_SIGNAL_CLOCK',matches=1))
    need(all(found[key]>0 for key in exact_literals),'Every exact old orchestration label located')
    changes.extend(dict(anchor='metadata literal',old=key,new=value,matches=found[key]) for key,value in exact_literals.items())
    proof=dict(original_main_source_sha256=BASE_SHA,
        original_main_AST_sha256=hashlib.sha256(original.encode()).hexdigest(),
        derived_main_AST_sha256=hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest(),
        changes=changes,original_financial_body_direct_reference=True,
        original_cash_alias_function_direct_reference=True,original_tolerances_unchanged=True,
        metadata_compile_only_before_payload=True,producer_simulate_or_target_imported=False)
    namespace=dict(vars(base),__file__=__file__,BASE_MODULE=base,prepare_stack=prepare_stack,MAIN_PROOF=proof,
        source_metadata=source_metadata,STATUS=STATUS,FAIL=FAIL,ACTUAL_STATUS=ACTUAL_STATUS,CONTRACT=CONTRACT,
        INPUT_STATUS=INPUT_STATUS,SOURCE_STATUS=SOURCE_STATUS,DONCHIAN_ID=HOLD_ID,MODES=MODES,
        PERIOD=PERIOD,START=START,END=END,RUN=RUN,OUT=OUT,SOURCE=SOURCE,SOURCE_SHA=SOURCE_SHA,INPUT=INPUT,INPUT_SHA=INPUT_SHA)
    # prepare_stack needs this proof as a metadata global; financial functions
    # retain their original independent module globals and never use it.
    globals()['MAIN_PROOF']=proof
    exec(compile(ast.fix_missing_locations(ast.Module([node],type_ignores=[])),
        '<D045-private-303-accepted-audit-main>','exec'),namespace)
    return namespace['main'],proof


def main():
    entry,_=context();entry()


if __name__=='__main__':main()