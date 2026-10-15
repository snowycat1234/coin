"""Full-2022 source/admission scaffold. Import performs no market-body I/O.

Pure validators accept metadata or synthetic fixtures. Every actual source
projection/application remains closed until exact separately pinned source GO,
completed source qualification, and independent source/quality review exist.
The frozen v4 synthetic overlay is never used to admit real observations.
"""
from dataclasses import dataclass,field
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
from types import MappingProxyType

HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
FROZEN=ROOT/'traditional_three_tier_freeze_20261015'
S=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
DAY=86_400_000_000;MINUTE=60_000_000
YEAR=2022;START=1640995200000000;END=1672531200000000
FULL_START=START;ALLOWED_START=1623801600000000
DAYS=365;MINUTES=525600
CONFIGS=tuple(s+'_'+t for s in ('STATIC50','H090','VOL_MANAGED_HOLD') for t in ('LOW','MID','HIGH'))
SOURCE_ROOT=ROOT/'full2022_unaffected_source_restore_20261015'
FINAL_PINS='b10686c8f84d3aa111d48763612b0433c2469ca605e15f4910b80a39cee6d9d5'
SOURCE_QUALIFICATION_SHA256='36310f40bddad0c6de5482085ba8fc0c81571060f7dda5da6deb62125fa1c5ec'
SOURCE_INDEPENDENT_REVIEW_SHA256='5a934063b763bd54f986a8ad8e8bb3222c737180ca03f5cafbccd4b51b521429'
SOURCE_PREP_ACTION='PREPARE_EXACT_FULL2022_SOURCE_TARGETS_ONLY_NO_HISTORY'
OVERLAY_MANIFEST_SHA256='2d132b409c9bb7ac364750e30afa025b42fd6d6a9dea46eeb8ebb3003cc85bad'
OVERLAY_CODE_SHA256='6af3c5c17f8cf7e8a522c75140547d090f0d2f1cc70811d1625288d8e9f60b18'
OVERLAY_REVIEW_SHA256='4989232aa96e4ad806096925eb29420927fdec0fa1de377ab656290b8f4fcedf'
ACTUAL_ALLOWLIST_SHA256='55e87de1c4b238ab907d57c950de2eedc1a2ec245e8b6e0fe57cd2efe07c0f71'


def sha(b):return sha256(b).hexdigest()
def plain(v):
    if hasattr(v,'items'):return {k:plain(x) for k,x in v.items()}
    if isinstance(v,(tuple,list)):return [plain(x) for x in v]
    return v

def canonical(v):return json.dumps(plain(v),sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def jsha(v):return sha(canonical(v))
def immutable(v):
    if isinstance(v,dict):return MappingProxyType({k:immutable(x) for k,x in v.items()})
    if isinstance(v,(tuple,list)):return tuple(immutable(x) for x in v)
    return v

def digest(value):
    if type(value) is not str or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError('EXACT_LOWERCASE_SHA256_REQUIRED')
    return value

def exact(path,expected,size=None):
    digest(expected);p=Path(path)
    if not p.is_file() or p.is_symlink() or any(x.is_symlink() for x in p.parents):
        raise ValueError('ORDINARY_EXACT_SOURCE_FILE_REQUIRED')
    b=p.read_bytes()
    if sha(b)!=expected or size is not None and (type(size) is not int or len(b)!=size):raise ValueError('SOURCE_PIN_CHANGED')
    return b

def require_full_source_pins():
    for value in (FINAL_PINS,SOURCE_QUALIFICATION_SHA256,SOURCE_INDEPENDENT_REVIEW_SHA256):
        if value is None:raise ValueError('FULL2022_SOURCE_UNQUALIFIED_UNPINNED_NO_ACTUAL_STAGE')
        digest(value)

def _external(raw,expected,pinned,error):
    # Expectations are supplied independently by the root invocation, never
    # read from a saved GO/review artifact or embedded into its own code hash.
    if pinned is None:raise ValueError(error)
    digest(pinned)
    if type(raw) is not bytes or expected!=pinned or sha(raw)!=pinned:raise ValueError(error)
    return json.loads(raw)

def require_source_stage_authority(raw,expected):
    require_full_source_pins()
    a=_external(raw,expected,expected,'EXACT_EXTERNAL_SOURCE_PREP_ROOT_AUTHORITY_REQUIRED')
    required=dict(schema='ROOT_SOURCE_PREP_FULL2022_V1',action=SOURCE_PREP_ACTION,
        source_completion_SHA256=FINAL_PINS,qualification_SHA256=SOURCE_QUALIFICATION_SHA256,
        source_independent_review_SHA256=SOURCE_INDEPENDENT_REVIEW_SHA256,
        overlay_manifest_SHA256=OVERLAY_MANIFEST_SHA256,overlay_code_SHA256=OVERLAY_CODE_SHA256,
        overlay_review_SHA256=OVERLAY_REVIEW_SHA256,actual_allowlist_SHA256=ACTUAL_ALLOWLIST_SHA256,
        calendar=[START,END],target_generation_authorized=True,actual_overlay_application_authorized=True,
        historical_execution_authorized=False,account_construction_authorized=False,
        provider_iteration_authorized=False,process_launch_authorized=False,canonical_claims_authorized=False)
    if any(type(a.get(k)) is not type(v) or a[k]!=v for k,v in required.items()):raise ValueError('EXACT_SOURCE_PREP_ONLY_SCOPE_REQUIRED')
    digest(a.get('actual_source_adapter_review_SHA256'))
    from full_entry import code_identity
    if a.get('code_identity')!=code_identity():raise ValueError('EXACT_REVIEWED_ACTUAL_ADAPTER_PROJECTOR_CODE_REQUIRED')
    SourceQualificationBinding.validate(a.get('qualified_source_binding'),qualification_sha256=SOURCE_QUALIFICATION_SHA256)
    return a

def require_historical_authority(raw,expected):
    require_full_source_pins()
    return _external(raw,expected,expected,'EXACT_NEW_EXTERNAL_FULL2022_ROOT_GO_REQUIRED')


@dataclass(frozen=True,slots=True)
class SourceQualificationBinding:
    """No price bodies and no authority. A verified complete metadata shape."""
    source_identity:str
    qualification_SHA256:str
    provenance_SHA256:str
    allowlist_SHA256:str
    endpoint_source_SHA256:str
    @classmethod
    def validate(cls,m,*,qualification_sha256=None):
        fixed=dict(schema='FULL2022_COMPLETE_SOURCE_QUALIFICATION_V1',status='PASS_SOURCE_ONLY_NO_HISTORICAL_GO',
            year=2022,calendar=[START,END],days=365,minute_count=525600,monthly_original_streams=120,
            original_ZIP_bytes=158411229,genuine_daily_repairs=16,genuine_daily_added_asset_minutes=23040,
            daily_projection_rows=564,daily_projection_calendar=[ALLOWED_START,END-DAY],
            daily_projection_strictly_before_us=END,ready_200close_decisions=365,raw_funding_events=5550,
            remaining_missing_trade_cells=0,remaining_missing_mark_cells=27,unique_mark_gap_open_clocks=11,
            mark_gap_asset_runs=8,mark_gap_singleton_runs=4,mark_gap_longest_run=7,
            endpoint_open_us=END-MINUTE,endpoint_completed_us=END,
            endpoint_origin='GENUINE_DEC31_2359_NATIVE_BAR',selected_2023_daily_cube_rows=0,
            historical_arrival_certified=False,funding_unit_certified=False,native_exchange_certified=False,
            source_observation_implies_ownership=False,accounts_constructed=0,historical_runs=0)
        if type(m) is not dict or any(type(m.get(k)) is not type(v) or m[k]!=v for k,v in fixed.items()):
            raise ValueError('EXACT_FULL2022_COMPLETE_SOURCE_METADATA_REQUIRED')
        for k in ('source_identity','provenance_SHA256','allowlist_SHA256','endpoint_source_SHA256'):digest(m.get(k))
        qualification_sha256=jsha(m) if qualification_sha256 is None else digest(qualification_sha256)
        if m['allowlist_SHA256']!=ACTUAL_ALLOWLIST_SHA256:raise ValueError('EXACT27_ORIGINAL_ALLOWLIST_REQUIRED')
        return cls(m['source_identity'],qualification_sha256,m['provenance_SHA256'],m['allowlist_SHA256'],m['endpoint_source_SHA256'])


@dataclass(frozen=True,slots=True)
class QualityCell:
    symbol:str
    minute_open_us:int
    completed_us:int
    evaluation_us:int
    price_text:str
    anchor_open_us:int
    anchor_completed_us:int
    anchor_available_us:int
    anchor_installed_us:int
    source_freshness_clock_us:int
    anchor_source_SHA256:str
    anchor_record_id:str
    quality:str='UNKNOWN_OR_DERIVED'
    arrival_status:str='UNKNOWN_NOT_CERTIFIED'
    is_genuine:bool=False
    permits_new_increase:bool=False
    permits_topup:bool=False
    certifies_liquidation:bool=False
    certifies_no_liquidation:bool=False
    availability_clock_semantics:str='OFFLINE_MODEL_COMPLETION_BOUNDARY'
    installation_clock_semantics:str='OFFLINE_MODEL_REPLAY_INSTALLATION'
    actual_publication_arrival_installation:str='UNKNOWN_NOT_CERTIFIED'
    def validate(self):
        clocks=(self.minute_open_us,self.completed_us,self.evaluation_us,self.anchor_open_us,self.anchor_completed_us,
                self.anchor_available_us,self.anchor_installed_us,self.source_freshness_clock_us)
        if any(type(x) is not int or x<0 for x in clocks):raise ValueError('EXPLICIT_INTEGER_QUALITY_CLOCKS_REQUIRED')
        if (self.minute_open_us%MINUTE or self.anchor_open_us%MINUTE or self.completed_us!=self.minute_open_us+MINUTE
                or self.evaluation_us!=self.completed_us or self.anchor_completed_us!=self.anchor_open_us+MINUTE
                or not self.anchor_completed_us<=self.anchor_available_us<=self.anchor_installed_us<=self.evaluation_us
                or self.anchor_open_us>=self.minute_open_us
                or self.source_freshness_clock_us!=self.anchor_available_us
                or not 1<=(self.minute_open_us-self.anchor_open_us)//MINUTE<=7):raise ValueError('CAUSAL_ANCHOR_SOURCE_CLOCK_NOT_FRESH_MISSING_CLOCK_REQUIRED')
        digest(self.anchor_source_SHA256)
        if type(self.price_text) is not str or not 0<len(self.price_text)<=200:raise ValueError('EXACT_ANCHOR_PRICE_TEXT_REQUIRED')
        p=Decimal(self.price_text)
        if not p.is_finite() or p<=0:raise ValueError('POSITIVE_ANCHOR_PRICE_REQUIRED')
        if (self.quality!='UNKNOWN_OR_DERIVED' or self.arrival_status!='UNKNOWN_NOT_CERTIFIED'
                or any(type(x) is not bool or x for x in (self.is_genuine,self.permits_new_increase,self.permits_topup,
                    self.certifies_liquidation,self.certifies_no_liquidation))):raise ValueError('UNKNOWN_QUALITY_NO_NEW_RISK_OR_CERTIFICATION_REQUIRED')
        if (self.availability_clock_semantics!='OFFLINE_MODEL_COMPLETION_BOUNDARY' or self.installation_clock_semantics!='OFFLINE_MODEL_REPLAY_INSTALLATION' or self.actual_publication_arrival_installation!='UNKNOWN_NOT_CERTIFIED'):raise ValueError('OFFLINE_MODEL_CLOCKS_AND_UNKNOWN_ACTUAL_ARRIVAL_REQUIRED')
        if type(self.anchor_record_id) is not str or not self.anchor_record_id:raise ValueError('ANCHOR_PROVENANCE_REQUIRED')
        return self


def validate_quality_binding(cells,*,expected_missing_cells):
    if type(cells) is not tuple or any(type(c) is not QualityCell for c in cells):raise ValueError('IMMUTABLE_TYPED_QUALITY_CELLS_REQUIRED')
    expected=tuple(sorted(expected_missing_cells))
    if len(set(expected))!=len(expected) or len(expected)!=27:raise ValueError('EXACT27_MISSING_CELL_SET_REQUIRED')
    actual=tuple(sorted((c.symbol,c.minute_open_us) for c in cells))
    if actual!=expected:raise ValueError('EXACT27_QUALITY_ALLOWLIST_REQUIRED')
    for c in cells:c.validate()
    # Anchors must remain genuinely outside the entire original missing set.
    absent=set(expected)
    for c in cells:
        if (c.symbol,c.anchor_open_us) in absent:raise ValueError('DERIVED_CELL_CANNOT_BECOME_GENUINE_ANCHOR')
        for at in range(c.anchor_open_us+MINUTE,c.minute_open_us+MINUTE,MINUTE):
            if (c.symbol,at) not in absent:raise ValueError('LATEST_EARLIER_GENUINE_ANCHOR_REQUIRED')
    anchor_values={}
    for c in cells:
        key=(c.symbol,c.anchor_source_SHA256,c.anchor_record_id,c.anchor_open_us)
        value=(c.price_text,c.anchor_completed_us,c.anchor_available_us,c.anchor_installed_us)
        if key in anchor_values and anchor_values[key]!=value:raise ValueError('CONSISTENT_GENUINE_ANCHOR_PROVENANCE_REQUIRED')
        anchor_values[key]=value
    return dict(quality='UNKNOWN_OR_DERIVED',arrival_status='UNKNOWN_NOT_CERTIFIED',cells=27,
        funding_impact='PENDING_ACTUAL_SAVED_EVIDENCE',risk_impact='PENDING_ACTUAL_SAVED_EVIDENCE',
        execution_impact='PENDING_ACTUAL_SAVED_EVIDENCE',past2_envelope_is_future_bound=False,
        certifies_liquidation=False,certifies_no_liquidation=False)


_SOURCE_SEAL=object()
@dataclass(frozen=True,slots=True)
class ActualSourceApplicationScope:
    qualification:SourceQualificationBinding
    root_source_GO_SHA256:str
    _qualification_raw:bytes
    _go_raw:bytes
    _seal:object
    def __post_init__(self):
        if self._seal is not _SOURCE_SEAL:raise ValueError('ACTUAL_SOURCE_SCOPE_ONLY_AFTER_SEPARATE_REVIEW_AND_ROOT_STAGE_GO')
    def validate_current(self):
        require_full_source_pins()
        if self._seal is not _SOURCE_SEAL:
            raise ValueError('EXACT_CURRENT_SOURCE_STAGE_GO_REQUIRED')
        require_source_stage_authority(self._go_raw,self.root_source_GO_SHA256)
        if sha(self._qualification_raw)!=SOURCE_QUALIFICATION_SHA256 or SourceQualificationBinding.validate(json.loads(self._go_raw)['qualified_source_binding'],qualification_sha256=sha(self._qualification_raw))!=self.qualification:
            raise ValueError('EXACT_CURRENT_QUALIFIER_BODY_AND_BINDING_REQUIRED')
        return True


def admit_actual_source_stage(qualification_raw,raw_go,expected_go_sha256):
    # Never called by generated tests; metadata validation alone mints nothing.
    require_source_stage_authority(raw_go,expected_go_sha256)
    if type(qualification_raw) is not bytes or sha(qualification_raw)!=SOURCE_QUALIFICATION_SHA256:
        raise ValueError('EXACT_PINNED_SOURCE_QUALIFICATION_BODY_REQUIRED')
    q=SourceQualificationBinding.validate(json.loads(raw_go)['qualified_source_binding'],qualification_sha256=sha(qualification_raw))
    if q.qualification_SHA256!=SOURCE_QUALIFICATION_SHA256:raise ValueError('EXACT_PINNED_SOURCE_QUALIFICATION_REQUIRED')
    return ActualSourceApplicationScope(q,expected_go_sha256,qualification_raw,raw_go,_SOURCE_SEAL)


def apply_actual_causal_marks(*args,source_scope=None,**kwargs):
    # This separate adapter never routes actual data through frozen v4 fixtures.
    from source_overlay import apply_actual_causal_marks as apply
    return apply(*args,source_scope=source_scope,**kwargs)


@dataclass(frozen=True,slots=True)
class CapturedMinuteProvider:
    year:int
    months:tuple
    quality_cells:tuple=()
    _historical_scope:object=field(default=None,repr=False,compare=False)
    def _bind_historical_scope(self,scope):
        from full_entry import FreshHistoricalExecutionScope
        if type(scope) is not FreshHistoricalExecutionScope or self._historical_scope is not None:raise ValueError('EXACT_FRESH_HISTORICAL_PROVIDER_ADMISSION_REQUIRED')
        if scope._bound_window.get('minute_blocks') is not self:raise ValueError('EXACT_ENTRY_OWNED_PROVIDER_REFERENCE_REQUIRED')
        scope.validate_current();object.__setattr__(self,'_historical_scope',scope)
    @property
    def identity(self):return dict(months=[[name,start,count,sha(body),len(body),lo,hi] for name,start,count,body,lo,hi in self.months],quality_SHA256=jsha([__import__('dataclasses').asdict(c) for c in self.quality_cells]))
    def __call__(self):
        require_full_source_pins()
        from full_entry import FreshHistoricalExecutionScope
        if type(self._historical_scope) is not FreshHistoricalExecutionScope:raise ValueError('HISTORICAL_PROVIDER_REQUIRES_SEPARATE_ROOT_GO')
        self._historical_scope.validate_current()
        if self.year!=2022:raise ValueError('ONLY_EXACT_FULL2022_PROVIDER_ALLOWED')
        from source_projection import month_arrays
        cursor=START
        for name,start,count,body,lo,hi in self.months:
            if start+lo*MINUTE!=cursor:raise ValueError('EXACT_CHRONOLOGICAL_SOURCE_PROVIDER_REQUIRED')
            a,_=month_arrays(body,start,count,self.quality_cells)
            for off in range(lo,hi,1440):
                stop=min(off+1440,hi)
                yield dict(times=a['times'][off:stop],market={symbol:{k:a[symbol+'_'+k][off:stop] for k in ('open','close','quote_volume','mark')} for symbol in S})
            cursor=start+hi*MINUTE
        if cursor!=END:raise ValueError('EXACT_FULL2022_PROVIDER_END_REQUIRED')


def project(source_root=SOURCE_ROOT,*,source_scope=None,source_authorization_raw=None,expected_source_authorization_sha256=None):
    require_full_source_pins()
    from source_projection import project as apply
    return apply(source_root,source_scope=source_scope,source_authorization_raw=source_authorization_raw,expected_source_authorization_sha256=expected_source_authorization_sha256)

# Exact original absent OPEN metadata only; no price/source bodies.
ACTUAL27_OPEN_POINTS_US=(('DOGEUSDT', 1657631820000000), ('DOGEUSDT', 1657631880000000), ('DOGEUSDT', 1657631940000000), ('DOGEUSDT', 1657632000000000), ('DOGEUSDT', 1657632060000000), ('ETHUSDT', 1657630620000000), ('ETHUSDT', 1657631220000000), ('ETHUSDT', 1657631700000000), ('ETHUSDT', 1657631760000000), ('ETHUSDT', 1657631820000000), ('ETHUSDT', 1657631880000000), ('ETHUSDT', 1657631940000000), ('ETHUSDT', 1657632000000000), ('ETHUSDT', 1657632060000000), ('ETHUSDT', 1657633920000000), ('ETHUSDT', 1657695540000000), ('SOLUSDT', 1657631760000000), ('SOLUSDT', 1657631820000000), ('SOLUSDT', 1657631880000000), ('SOLUSDT', 1657631940000000), ('SOLUSDT', 1657632000000000), ('SOLUSDT', 1657632060000000), ('XRPUSDT', 1657631820000000), ('XRPUSDT', 1657631880000000), ('XRPUSDT', 1657631940000000), ('XRPUSDT', 1657632000000000), ('XRPUSDT', 1657632060000000))
