"""Source-GO-gated selection of original targets and exact covariance projection.

No wallet, target recomputation, scientific fitter or market loader runs on
import. Pure projection helpers accept generated arrays for arithmetic tests.
"""
from pathlib import Path
import ast,hashlib,io,json,zipfile
import bindings as B

def raw_sha(a):return hashlib.sha256(a.tobytes()).hexdigest()

def exact_functions():
 """Compile only ready200 and original allocate's covariance statements.

 The t/p/d conversion, input guard, k/window checks, return arithmetic,
 np.cov(ddof=1)*365, append and final stack are original AST nodes. There is
 no call to scale/allocate targets, public_targets or any learned model.
 """
 import numpy as np
 if np.__version__!='2.3.5':raise ValueError('EXACT_ORIGINAL_PROJECTION_NUMPY_2_3_5_REQUIRED')
 pins=B.metadata_manifest()['projection_sources']
 risk=B.check(B.ROOT/pins['risk_budget']['path'],pins['risk_budget']['SHA256'])
 source=B.check(B.ROOT/pins['ready200']['path'],pins['ready200']['SHA256'])
 tree=ast.parse(risk.read_text());original=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='allocate')
 loop=next(n for n in original.body if isinstance(n,ast.For))
 append=next(n for n in loop.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and isinstance(n.value.func.value,ast.Name) and n.value.func.value.id=='covariance')
 # Bind the narrow original statement inventory, instead of guessing slices
 # if a future scientific source somehow differs from the exact source pin.
 if len(loop.body)<4 or not isinstance(loop.body[0],ast.Assign) or not isinstance(loop.body[1],ast.If):raise ValueError('ORIGINAL_COVARIANCE_AST_INVENTORY')
 newloop=ast.For(target=loop.target,iter=loop.iter,body=[*loop.body[:4],append],orelse=[])
 result=next(n for n in reversed(original.body) if isinstance(n,ast.Return)).value.elts[1]
 if not all(isinstance(n,ast.Assign) for n in original.body[:3]) or not isinstance(original.body[3],ast.If):raise ValueError('ORIGINAL_CLOCK_PRICE_DECISION_AST_INVENTORY')
 function=ast.FunctionDef(name='original_covariance_projection',args=ast.arguments(posonlyargs=[],args=[ast.arg(arg=n) for n in ('clocks','close','decisions')],kwonlyargs=[],kw_defaults=[],defaults=[]),body=[*original.body[:4],*ast.parse('covariance=[]').body,newloop,ast.Return(value=result)],decorator_list=[])
 ready=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='ready200')
 namespace=dict(np=np,DAY=B.DAY)
 exec(compile(ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[])),str(risk),'exec'),namespace)
 exec(compile(ast.Module(body=[ready],type_ignores=[]),str(source),'exec'),namespace)
 return namespace['original_covariance_projection'],namespace['ready200']

def project_generated_or_admitted(clock,prices,decisions):
 import numpy as np
 covariance,ready=exact_functions()
 t=np.asarray(clock);p=np.asarray(prices);d=np.asarray(decisions)
 if t.dtype!=np.dtype('int64') or d.dtype!=np.dtype('int64') or p.dtype!=np.dtype('float64') or t.ndim!=1 or d.ndim!=1 or not len(d):raise ValueError('EXACT_SOURCE_CLOCK_PRICE_SCHEMA')
 c=covariance(t,p,d);mask=ready(t,p);ids=np.searchsorted(t,d)
 if np.any(ids>=len(t)) or not np.array_equal(t[ids],d):raise ValueError('EXACT_DECISION_AVAILABILITY')
 # Preserve original all-five200 and64-clock daily admission, plus current31
 # price context. For these three original packets the prior receipt says all
 # days are admitted; a mismatch blocks rather than changing saved weights.
 admission=[]
 for k in ids:
  contiguous=k>=63 and np.all(np.diff(t[k-63:k+1])==B.DAY)
  admission.append(bool(contiguous and mask[k].all() and np.isfinite(p[k-30:k+1]).all() and (p[k-30:k+1]>0).all()))
 anchor=1704067200000000;week=7*B.DAY
 owners=anchor+((d-anchor)//week)*week
 owner_known=[]
 for owner in owners:
  k=int(np.searchsorted(t,owner))
  owner_known.append(bool(k>=30 and k<len(t) and t[k]==owner and np.all(np.diff(t[k-30:k+1])==B.DAY) and np.isfinite(p[k-30:k+1]).all() and (p[k-30:k+1]>0).all()))
 return dict(covariance=c,original_daily_admission=np.asarray(admission,dtype=bool),owning_rank_us=owners.astype(np.int64),owning_rank_source_known=np.asarray(owner_known,dtype=bool),decision_us=d.copy(),source_ids=ids)

def source_only(roots,year,go,go_sha):
 B.require_go(go,go_sha,'SOURCE_ONLY_ORIGINAL_PROJECTION',year)
 from verified_source import require_runtime
 if not getattr(require_runtime(),'bounded_worker_admitted',False):raise ValueError('BOUNDED_CONTROLLER_HANDOFF_REQUIRED_BEFORE_SOURCE_ARRAY')
 manifest=B.metadata_manifest();record=manifest['years'][str(year)]
 # This is the first possible array read; authorization precedes even hashes.
 container=manifest['cube_container'];zip_path=B.check(roots['cube_container'],container['SHA256'],container['bytes'])
 import numpy as np
 with zipfile.ZipFile(zip_path) as archive:
  raw=archive.read(record['cube_member'])
 if hashlib.sha256(raw).hexdigest()!=record['cube_member_SHA256'] or len(raw)!=record['cube_member_bytes']:raise ValueError('EXACT_SOURCE_CUBE_MEMBER')
 with np.load(io.BytesIO(raw),allow_pickle=False) as z:
  # Deliberately never select historical reward/outcome/funding_per_unit arrays.
  symbols=z['symbol_order'].copy();clock=z['close_available_us'].copy();prices=z['close'].copy()
 if tuple(symbols)!=B.S:raise ValueError('SOURCE_CORE5_ORDER')
 decisions=np.arange(*record['calendar'],B.DAY,dtype=np.int64)
 projected=project_generated_or_admitted(clock,prices,decisions)
 if raw_sha(projected['covariance'])!=record['raw_covariance_SHA256']:raise ValueError('ORIGINAL_COVARIANCE_RAW_HASH_MISMATCH_NO_REFIT')
 if int(projected['original_daily_admission'].sum())!=record['original_allfive200_admitted_days'] or not projected['original_daily_admission'].all():raise ValueError('ORIGINAL_MASK_OR_WARMUP_CHANGED')
 if not projected['owning_rank_source_known'].all():raise ValueError('ORIGINAL_WEEKLY_OWNER_PREFIX_UNKNOWN')
 target=B.check(roots['target'],record['target']['SHA256'],record['target']['bytes'])
 with np.load(target,allow_pickle=False) as z:
  # STATIC50 here means original unlagged CS21+HOLD; archive identity is pinned.
  d=z['decision_us'].copy();s=z['symbol_order'].copy();w=z['STATIC50'].copy()
  saved_cov=z['annual_covariance'].copy() if year==2024 else None
 if tuple(s)!=B.S or s.dtype!=np.dtype('<U8') or d.dtype!=np.dtype('int64') or not np.array_equal(d,decisions) or w.dtype!=np.dtype('float64') or w.shape!=(len(d),5) or raw_sha(w)!=record['raw_target_SHA256']:raise ValueError('ORIGINAL_UNLAGGED_TARGET_RAW_IDENTITY')
 if not np.isfinite(w).all() or np.any(np.abs(w)>.3+1e-12) or np.any(np.abs(w).sum(1)>.6+1e-12):raise ValueError('ORIGINAL_TARGET_FINITE_CAPS')
 if saved_cov is not None and saved_cov.tobytes()!=projected['covariance'].tobytes():raise ValueError('SAVED2024_COVARIANCE_BIT_MISMATCH')
 transport=B.load_transport()
 window=transport.source_window(year,roots['source'])
 # Daily price clock is the original native close_us availability boundary.
 # No extra day or lag is introduced. All values are byte-compared to the
 # original warmup cube on each admitted native daily decision.
 by={(r['symbol'],int(r['close_us'])):float(r['close']) for r in window['daily']}
 if len(by)!=len(window['daily']):raise ValueError('SOURCE_DAILY_DUPLICATES')
 expected=np.asarray([[by[(s,int(t))] for s in B.S] for t in decisions],dtype=np.float64)
 if expected.tobytes()!=prices[projected['source_ids']].tobytes():raise ValueError('ORIGINAL_DAILY_CUBE_BIT_PARITY')
 if year==2024:
  B.check(roots.get('derived_csv',''),manifest['derived2024']['SHA256'],manifest['derived2024']['bytes'])
  import csv
  with Path(roots['derived_csv']).open() as f:derived=list(csv.DictReader(f))
  if len(derived)!=10 or {(r['symbol'],int(r['open_time_ms'])) for r in derived}!={(s,t) for s in B.S for t in (1723456920000,1723456980000)} or any(r['source_missing']!='True' for r in derived):raise ValueError('ORIGINAL10_DERIVED_PROVENANCE')
 for a in (decisions,w,prices,clock,*[v for v in projected.values() if isinstance(v,np.ndarray)]):a.flags.writeable=False
 return dict(window=window,weights=w,clock=clock,prices=prices,**projected),dict(schema='ORIGINAL_CSH_SOURCE_ONLY_PROJECTION_RECEIPT_V1',status='PASS_ORIGINAL_TARGET_COVARIANCE_SOURCE_ONLY_NO_WALLET',year=year,preparation_manifest_SHA256=B.sha(B.HERE/'PREPARATION_MANIFEST.json'),input_manifest_SHA256=B.sha(B.HERE/'INPUT_MANIFEST.json'),parent_source_GO_SHA256=go_sha,target_archive_SHA256=record['target']['SHA256'],target_raw_SHA256=raw_sha(w),covariance_raw_SHA256=raw_sha(projected['covariance']),source_index_SHA256=record['source_index']['SHA256'],rank_feature_lag_hours=0,daily_admitted_days=int(projected['original_daily_admission'].sum()),wallets=0,financial_returns_computed=False,source_array_fields=['close_available_us','close','symbol_order'],target_array_fields=['decision_us','symbol_order','STATIC50']+(['annual_covariance'] if year==2024 else []))
