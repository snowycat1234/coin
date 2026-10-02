"""Independent accepted-Parquet Decimal basis audit; no runner math, API or account model."""
import hashlib, json, math, os, resource, sys, time
from datetime import datetime, timezone
from decimal import Decimal, localcontext
from pathlib import Path
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
WORK=STATE/'test-basis-risk-independent-audit-20261003-v1'
OUT=ROOT/'reports/fast_research/BASIS_RISK_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json'
MONTHS=('2025-08','2025-09','2025-10','2025-11');SYMBOLS=('BTCUSDT','ETHUSDT')
KINDS=('spot1m','markPriceKlines','indexPriceKlines');NAMES=('basis','mark_index','index_spot')
STEP=60000000;BP=Decimal(10000);ZERO=Decimal(0);TOL=Decimal('1e-7')

def need(ok,message):
    if not ok:raise AssertionError(message)

def sha(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1048576),b''):digest.update(block)
    return digest.hexdigest()

def load(path):return json.loads(Path(path).read_bytes())
def write_new(path,value):
    with Path(path).open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2,ensure_ascii=False,allow_nan=False);stream.write('\n')

def number(value):
    need(type(value) in (int,float) and math.isfinite(value),'Finite output number required')
    return Decimal.from_float(float(value))

def price(value):
    need(type(value) is float and math.isfinite(value) and value>0,'Unchanged positive finite Float64 close required')
    return Decimal.from_float(value)

def compare(value,expected,scale=Decimal(1)):
    error=abs((number(value)-expected)*scale)
    need(error<=TOL,'Independent absolute bp mismatch:'+str(error))
    return error

def task(identity):
    need(type(identity) is str and len(identity)==32 and all(c in '0123456789abcdef' for c in identity),'Task identity required')
    path=STATE/'task-progress'/('task-'+identity+'.json');saved=load(path)
    need(saved['id']==identity and saved['status']=='completed' and saved['exit_code']==0
         and type(saved['pid']) is int and type(saved['start_ticks']) is int,'Actual task not completed with exit zero')
    return dict(path=str(path),sha256=sha(path),**{k:saved[k] for k in ('id','status','exit_code','pid','start_ticks')})

def bounds(month):
    year,num=map(int,month.split('-'))
    start=int(datetime(year,num,1,tzinfo=timezone.utc).timestamp())*1000000
    end=int(datetime(year+(num==12),num%12+1,1,tzinfo=timezone.utc).timestamp())*1000000
    return start,end

class Component:
    def __init__(self,name,s0,reported):
        self.name=name;self.s0=s0;self.reported=reported;self.count=0;self.start=None
        self.minimum=self.maximum=self.peak=self.dd=ZERO
        self.fmin=self.fmax=self.fpeak=self.fdd=0.;self.first={};self.requested={}
        self.request_times={key:value['open_us'] for key,value in reported['witnesses'].items()}
        need(set(self.request_times)=={'max_adverse','max_favorable','max_drawdown'},'All extreme witnesses required')
    def update(self,stamp,level,float_level,prices):
        if self.start is None:self.start=level;self.fstart=float_level
        change=(level-self.start)/self.s0*BP;valuation=-change
        self.minimum=min(self.minimum,change);self.maximum=max(self.maximum,change)
        self.peak=max(self.peak,valuation);dd=self.peak-valuation;self.dd=max(self.dd,dd)
        # Independent scalar Float64 traversal verifies declared first-row ties;
        # all magnitudes and decomposition are independently checked with Decimal.
        fc=(float_level-self.fstart)/float(self.s0)*10000;fv=-fc
        self.fpeak=max(0.,self.fpeak,fv);fd=self.fpeak-fv
        if self.count==0:self.first={key:stamp for key in self.request_times}
        if fc>self.fmax:self.fmax=fc;self.first['max_adverse']=stamp
        if fc<self.fmin:self.fmin=fc;self.first['max_favorable']=stamp
        if fd>self.fdd:self.fdd=fd;self.first['max_drawdown']=stamp
        for label,wanted in self.request_times.items():
            if stamp==wanted:self.requested[label]=dict(open_us=stamp,close_us=stamp+STEP,
                **prices,**{self.name:level,self.name+'_change_bp':change,
                self.name+'_valuation_change_bp':valuation,self.name+'_drawdown_bp':dd})
        self.end=level;self.last_change=change;self.count+=1
        return change
    def check(self):
        saved=self.reported;errors=[]
        expected=dict(start_difference=self.start,end_difference=self.end,
            terminal_change_bp=self.last_change,terminal_valuation_change_bp=-self.last_change,
            max_adverse_change_bp=max(ZERO,self.maximum),max_favorable_change_bp=max(ZERO,-self.minimum),
            max_valuation_drawdown_bp=self.dd)
        for field,value in expected.items():
            errors.append(compare(saved[field],value,BP/self.s0 if field.endswith('difference') else Decimal(1)))
        need(saved['initial_zero_in_running_peak'] is True,'Initial zero missing from valuation peak')
        for label,stamp in self.request_times.items():
            need(stamp==self.first[label] and label in self.requested,'Wrong chronological extreme witness')
            expected_row=self.requested[label];actual=saved['witnesses'][label]
            need(set(actual)==set(expected_row),'Extreme witness schema differs')
            for field,value in expected_row.items():
                if field in ('open_us','close_us'):need(type(actual[field]) is int and actual[field]==value,'Witness clock differs')
                elif field in ('spot_close','mark_close','index_close'):
                    need(number(actual[field])==value,'Witness is not the original source close')
                else:errors.append(compare(actual[field],value,BP/self.s0 if field==self.name else Decimal(1)))
        return dict(decimal_values={key:str(value) for key,value in expected.items()},
            maximum_absolute_error_bp=float(max(errors)),verified_witnesses=3,first_chronological_ties_verified=True)

class Window:
    def __init__(self,reported):
        self.reported=reported;self.rows=0;self.parts=None;self.maximum_residual=ZERO;self.maximum_level_residual=ZERO
    def update(self,stamp,spot,mark,index):
        prices=dict(spot_close=price(spot),mark_close=price(mark),index_close=price(index))
        s,m,i=(prices[key] for key in ('spot_close','mark_close','index_close'))
        with localcontext() as context:
            context.prec=80
            if self.parts is None:
                self.s0=s;self.initial=dict(open_us=stamp,**prices)
                self.parts={name:Component(name,s,self.reported if name=='basis' else self.reported['components'][name]) for name in NAMES}
            else:need(stamp==self.last_stamp+STEP,'Window calendar missing/duplicated/shifted')
            levels=dict(basis=m-s,mark_index=m-i,index_spot=i-s)
            level_residual=abs(levels['basis']-levels['mark_index']-levels['index_spot'])/self.s0*BP
            need(level_residual<=Decimal('1e-60'),'Decimal level decomposition failed')
            self.maximum_level_residual=max(self.maximum_level_residual,level_residual)
            floats=dict(basis=mark-spot,mark_index=mark-index,index_spot=index-spot)
            changes={name:self.parts[name].update(stamp,levels[name],floats[name],prices) for name in NAMES}
            residual=abs(changes['basis']-changes['mark_index']-changes['index_spot'])
            need(residual<=Decimal('1e-60'),'Decimal common-denominator decomposition failed')
            self.maximum_residual=max(self.maximum_residual,residual)
            self.latest=prices;self.last_stamp=stamp;self.rows+=1
    def check(self):
        saved=self.reported
        need(self.rows>0 and saved['rows']==self.rows and saved['first_open_us']==self.initial['open_us']
             and saved['last_open_us']==self.last_stamp and saved['first_close_us']==self.initial['open_us']+STEP
             and saved['last_close_us']==self.last_stamp+STEP,'Window complete open/closed grid differs')
        need(saved['quantity_per_leg']==1 and saved['initial_valuation_change_bp']==0
             and saved['extrema_ties']=='FIRST_CHRONOLOGICAL_ROW','Quantity/baseline/tie rule differs')
        for name in ('spot','mark','index'):
            need(number(saved[name+'_close_start'])==self.initial[name+'_close']
                 and number(saved[name+'_close_end'])==self.latest[name+'_close'],'Window initial/terminal original closes differ')
        need(number(saved['denominator_S0'])==self.s0,'Every component must share first Spot close S0')
        result={name:self.parts[name].check() for name in NAMES}
        for field in ('maximum_decomposition_level_error_bp','maximum_decomposition_change_error_bp'):
            need(ZERO<=number(saved[field])<=TOL,'Reported decomposition error outside preregistered tolerance')
        return dict(rows=self.rows,first_open_us=self.initial['open_us'],last_open_us=self.last_stamp,
            independent_decimal_statistics=result,maximum_exact_decomposition_residual_bp=str(self.maximum_residual),
            maximum_exact_level_decomposition_residual_bp=str(self.maximum_level_residual))

def source_rows(entry):
    import pyarrow as pa
    import pyarrow.parquet as pq
    kind,symbol,month=(entry[key] for key in ('kind','symbol','month'))
    expected=(ROOT/'data/normalized/spot'/symbol/'1m'/(month+'.parquet') if kind=='spot1m' else
              STATE/'v8-funding-mark-index-source-20261002-v1'/(kind+'-'+symbol+'-'+month)/'source.parquet')
    path=Path(entry['parquet_path'])
    need(path==expected and path.resolve()==expected and path.is_file() and not path.is_symlink(),'Exact accepted source path only')
    need(sha(path)==entry['parquet_sha256'],'Accepted source file bytes changed')
    opened,closed=bounds(month);count=0;parquet=pq.ParquetFile(path)
    columns=['open_us','close_us','close','symbol','valid_day'] if kind=='spot1m' else ['timestamp_ms','close_time_ms','close']
    need(parquet.metadata.num_rows==entry['rows']==(closed-opened)//STEP,'Original entire month metadata differs')
    schema=parquet.schema_arrow
    need(schema.field('close').type==pa.float64(),'Original double close required')
    clocks=('open_us','close_us') if kind=='spot1m' else ('timestamp_ms','close_time_ms')
    need(all(schema.field(key).type==pa.int64() for key in clocks),'Original integer clock schema required')
    if kind=='spot1m':need(schema.field('valid_day').type==pa.bool_(),'Original validity Boolean required')
    for batch in parquet.iter_batches(batch_size=4096,columns=columns,use_threads=False):
        arrays=[batch.column(pos).to_pylist() for pos in range(len(columns))]
        for values in zip(*arrays,strict=True):
            row=dict(zip(columns,values,strict=True));price(row['close'])
            if kind=='spot1m':
                stamp,close=row['open_us'],row['close_us']
                need(row['symbol']==symbol and row['valid_day'] is True,'Spot NULL/bad quality or wrong symbol must fail, never drop')
            else:
                need(type(row['timestamp_ms']) is int and type(row['close_time_ms']) is int
                     and row['close_time_ms']==row['timestamp_ms']+59999,'Original proxy inclusive ms endpoint differs')
                stamp=row['timestamp_ms']*1000;close=(row['close_time_ms']+1)*1000
            need(type(stamp) is int and type(close) is int and stamp==opened+count*STEP
                 and close==stamp+STEP,'Every original minute retained/aligned; never rebase/drop/fill')
            count+=1;yield stamp,close,row['close']
    need(count==entry['rows'] and sha(path)==entry['parquet_sha256'],'Source count/bytes changed during read')

def main():
    need(sys.prefix==str(STATE/'v8-clean-env-20261002-v2'),'Frozen clean interpreter required')
    bound=load(WORK/'ACTUAL_BINDING.json')
    need(not OUT.exists() and sha(__file__)==bound['checker_sha256'],'New report and prebound checker required')
    report=dict(status='FAIL_BASIS_DECIMAL_INDEPENDENT_AUDIT',binding=dict(task_id=os.environ['COIN_TASK_ID'],
        checker_sha256=sha(__file__),ACTUAL_BINDING_sha256=sha(WORK/'ACTUAL_BINDING.json')),
        independent_source=str(Path(__file__)),independent_source_sha256=sha(__file__),
        absolute_tolerance_bp=str(TOL),input_precision='EXACT_BINARY_FLOAT64_DECIMAL_FROM_FLOAT_PRECISION80',
        actual_HTTP_requests=0,raw_ZIP_CRC_QA_repeated=False,old_tests_repeated=False,
        funding_arrays_read=False,fees_or_coupon_or_cash_NAV_APR_computed=False,
        candidate_status='NO_QUALIFIED_CANDIDATE',per_symbol=[],completed_joined_minutes=0)
    started=time.monotonic()
    try:
        for path,digest in bound['small_inputs'].items():need(sha(path)==digest,'Prebound small input changed:'+path)
        spec=load(ROOT/bound['protocol_path']);actual=load(ROOT/bound['actual_report_path'])
        options=load(ROOT/spec['source_options_path'])
        need(sha(ROOT/spec['source_options_path'])==spec['source_options_sha256'],'Actual metadata hash differs from protocol')
        need(Decimal(str(spec['independent_absolute_tolerance_bp']))==TOL and bound['absolute_tolerance_bp']==str(TOL),
             'Prebound tolerance changed')
        need(spec['math']==dict(quantity_per_leg=1,basis='MARK_MINUS_SPOT',normalization='WINDOW_FIRST_SPOT_CLOSE',
            adverse='POSITIVE_BASIS_CHANGE',valuation='NEGATIVE_BASIS_CHANGE',drawdown='PREFIX_RUNNING_PEAK_WITH_INITIAL_ZERO',
            month_scope='ALL_FOUR_LOCAL_BASELINES_DESCRIPTIVE_ONLY'),'Preregistered mathematical convention differs')
        need(spec['symbols']==list(SYMBOLS) and spec['source_calendar']==list(MONTHS)
             and spec['period_start']=='2025-08-01' and spec['period_end_exclusive']=='2025-12-01'
             and spec['expected_files']==24 and spec['expected_minutes_per_symbol']==175680,'Fixed whole period differs')
        need(actual['status']=='COMPLETE_FIXED_QUANTITY_BASIS_CLOSE_PROXY_RISK_NOT_CASH_NAV_OR_APR'
             and actual['completed_files']==24 and len(actual['per_symbol'])==2 and actual['source_bytes_unchanged'] is True,
             'Actual report is partial/failed/changed')
        report['actual_task']=task(bound['actual_task_id'])
        need(actual['binding']['task_id']==bound['actual_task_id']
             and actual['binding']==load(Path(actual['run_dir'])/'RUN_BINDING.json')
             and actual['binding']['protocol_sha256']==sha(ROOT/bound['protocol_path']),'Actual source/run binding differs')
        report['verified_source_hashes']=actual['binding']['source_hashes']
        for path,digest in report['verified_source_hashes'].items():need(sha(ROOT/path)==digest,'Frozen actual code/proof changed:'+path)
        need(all(actual['binding']['source_hashes'][key]==digest for key,digest in spec['frozen_sources'].items()),
             'Actual source hashes differ from frozen protocol')
        smoke=load(ROOT/spec['required_smoke_receipt']);report['smoke_actual_task']=task(smoke['binding']['task_id'])
        need(smoke['status']=='PASS_BASIS_RISK_SYNTHETIC_MATH_ALIGNMENT_NOT_MARKET_RESULT'
             and smoke['test_exit_code']==0 and smoke['binding']['source_hashes']==actual['binding']['source_hashes']
             and actual['accepted_smoke_sha256']==sha(ROOT/spec['required_smoke_receipt']),'Closed same-source smoke binding differs')
        sources=options['sources'];lookup={(e['kind'],e['symbol'],e['month']):e for e in sources}
        need(len(sources)==len(lookup)==24 and set(lookup)=={(k,s,m) for k in KINDS for s in SYMBOLS for m in MONTHS},
             'Only all24 accepted sources permitted')
        expected_bindings=[{key:entry[key] for key in ('kind','symbol','month','parquet_path','parquet_sha256','rows',
             'source_receipt_path','source_receipt_sha256')} for entry in sources]
        need(sorted(actual['input_bindings'],key=lambda e:(e['kind'],e['symbol'],e['month']))==
             sorted(expected_bindings,key=lambda e:(e['kind'],e['symbol'],e['month'])),'Actual inputs not exactly source options')
        for symbol in SYMBOLS:
            saved=next(e for e in actual['per_symbol'] if e['symbol']==symbol);whole=Window(saved['full_period']);month_results=[]
            need([e['month'] for e in saved['months']]==list(MONTHS),'All four months required without selection')
            for month,stats in zip(MONTHS,saved['months'],strict=True):
                need(stats['baseline_scope']=='MONTH_LOCAL_DESCRIPTIVE_NOT_ACCOUNT_RESET','Local month scope differs')
                local=Window(stats);streams=[source_rows(lookup[kind,symbol,month]) for kind in KINDS]
                for spot,mark,index in zip(*streams,strict=True):
                    need(spot[:2]==mark[:2]==index[:2],'Exact Spot/mark/index time alignment failed')
                    stamp=spot[0];values=(spot[2],mark[2],index[2])
                    whole.update(stamp,*values);local.update(stamp,*values)
                month_results.append(dict(month=month,**local.check()))
            full=whole.check();need(full['rows']==175680,'Whole122d grid count differs')
            report['per_symbol'].append(dict(symbol=symbol,full_period=full,months=month_results))
            report['completed_joined_minutes']+=full['rows']
            print(json.dumps(dict(symbol=symbol,verified_minutes=full['rows'],verified_windows=5)),flush=True)
        for field in ('funding_arrays_read','locked_consumed','fees_fills_NAV_cash_PnL_or_realized_funding_computed',
                      'funding_units_certified','coupon_added_to_basis'):
            need(actual[field] is False,'Forbidden economics/qualification claim:'+field)
        need(actual['candidate_status']=='NO_QUALIFIED_CANDIDATE' and actual['capital_net_APR']=='NOT_EVALUABLE'
             and actual['coupon_context_is_different_unit'] is True,'Coupon/basis or candidate scope differs')
        need(report['completed_joined_minutes']==351360,'All351360 joint minutes required')
        for path,digest in bound['small_inputs'].items():need(sha(path)==digest,'Small bound input changed during audit:'+path)
        report.update(status='PASS_FIXED_QUANTITY_BASIS_DECIMAL_PROXY_RISK_NOT_PNL_NAV_APR',
            actual_report_path=bound['actual_report_path'],actual_report_sha256=sha(ROOT/bound['actual_report_path']),
            protocol_sha256=sha(ROOT/bound['protocol_path']),completed_files_verified=24,completed_windows_verified=10,
            maximum_absolute_error_bp=max(p['maximum_absolute_error_bp'] for s in report['per_symbol']
                for w in [s['full_period'],*s['months']] for p in w['independent_decimal_statistics'].values()),
            scope='SEEN_BINANCE_CLOSE_PROXY_FIXED_COIN_QUANTITY_SCALE_ONLY_NO_EXECUTION_OR_COUPON_ADDING_OR_UNIT_CERTIFICATION')
    except Exception as error:
        report.update(error_type=type(error).__name__,reason=str(error));raise
    finally:
        report.update(elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        write_new(OUT,report)
    print(json.dumps(dict(status=report['status'],output=str(OUT),sha256=sha(OUT))))
if __name__=='__main__':main()
