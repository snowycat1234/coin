"""Exact two-arm 2025 admission. No historical simulator is constructed."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from freeze_terminal import verify
HERE=Path(__file__).resolve().parent;ROOT=HERE.parent
REVIEWED=verify();BINDINGS_SHA256=REVIEWED['files_SHA256']['CASE_BINDINGS.json']
DAY=86_400_000_000;MINUTE=60_000_000
EXPECTED={(2025,'STATIC50'),(2025,'COMBINED')}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def bindings():
 verify();b=json.loads((HERE/'CASE_BINDINGS.json').read_text())
 if (sha(HERE/'CASE_BINDINGS.json')!=BINDINGS_SHA256 or b['case_count']!=2 or b['modes']!=['ORIGINAL']
  or b['new_historical_wallets_executed']!=0 or len(b['cases'])!=2
  or {(c['year'],c['arm']) for c in b['cases']}!=EXPECTED
  or b['terminal_opens']!=60 or b['terminal_signal_offset_minutes']!=61):raise ValueError('Fixed terminal60 two-case plan changed')
 return b

def require_publication():
 p=HERE/'PUBLICATION_RECEIPT.json'
 if not p.is_file():raise RuntimeError('Exact remote preregistration required before GO')
 r=json.loads(p.read_text())
 if (r.get('status')!='PASS_EXACT_PRE_GO_REMOTE_PUBLICATION' or r.get('remote_verified') is not True
  or r.get('freeze_manifest_SHA256')!=sha(HERE/'FROZEN_CODE.json')
  or r.get('case_bindings_SHA256')!=sha(HERE/'CASE_BINDINGS.json')
  or r.get('publication_base_commit')!=bindings()['publication_base_commit']
  or r.get('review_receipt_SHA256')!=sha(HERE/'REVIEW_RECEIPT.json')):raise RuntimeError('Exact remote preregistration required before GO')
 return dict(publication_receipt_SHA256=sha(p))

def validate_terminal(times,available,opens,marks,volume,end):
 import numpy as np
 if (not np.array_equal(times,np.arange(end-61*MINUTE,end,MINUTE,dtype=np.int64))
  or not np.array_equal(available,times+MINUTE)):raise ValueError('Exact 61 final frozen quote clocks required')
 for a in (opens,marks):
  if a.shape!=(61,) or not np.isfinite(a).all() or (a<=0).any():raise ValueError('Actual positive terminal quotes')
 if volume.shape!=(61,) or not np.isfinite(volume).all() or (volume<0).any():raise ValueError('Actual prior quote volume')
 return {'signal_us':end-61*MINUTE,'attempt_us':[int(t+1) for t in times[1:]],'attempt_count':60,
  'prior_capacity_available_us':[int(t) for t in available[:-1]],'all_attempts_before_end':bool((times[1:]+1<end).all()),
  'capacity_rule':'PREVIOUS_COMPLETED_MINUTE_QUOTE_VOLUME_TIMES_0.001_DIVIDED_BY_CURRENT_OPEN','no_flat_promise':True}

def check():
 import numpy as np
 b=bindings();oldfine=ROOT/'coin_quantity_resolution_20261013'
 if (sha(oldfine/'FINE_PROFILE.json')!=b['fine_profile_SHA256'] or sha(oldfine/'CASE_BINDINGS.json')!=b['old_fine_plan_SHA256']
  or sha(oldfine/'state_20261013/RUN_BINDING.json')!=b['old_fine_run_binding_SHA256']):raise ValueError('Fine base changed')
 old={c['case_id']:c for c in json.loads((oldfine/'CASE_BINDINGS.json').read_text())['cases']}
 term=json.loads((HERE/'TERMINAL_QUOTE_GATE.json').read_text())
 if sha(HERE/'TERMINAL_QUOTE_GATE.json')!=b['terminal_quote_gate_SHA256'] or term['status']!='PASS_ACTUAL_60_TERMINAL_CLOCK_NO_FILL_PROMISE':raise ValueError('Terminal quote admission changed')
 for symbol,row in term['symbols'].items():
  validate_terminal(np.asarray(term['quote_open_us'],dtype=np.int64),np.asarray(term['quote_available_us'],dtype=np.int64),np.asarray(row['open_prices']),np.asarray(row['mark_prices']),np.asarray(row['quote_volume']),term['year_end_us'])
 verified=set()
 for c in b['cases']:
  for k in ('source_index_local_locator','source_index_SHA256','target_archive_local_locator','target_archive_SHA256','target_array_SHA256','target_dtype','target_shape','calendar','symbols'):
   if c[k]!=old[c['case_id']][k]:raise ValueError('Original registry changed: '+k)
  if c['protective_enabled'] is not False:raise ValueError('Guard must be off')
  src=ROOT/c['source_index_local_locator'];archive=ROOT/c['target_archive_local_locator']
  if sha(src)!=c['source_index_SHA256'] or sha(archive)!=c['target_archive_SHA256']:raise ValueError('Input bytes changed')
  idx=json.loads(src.read_text())
  if idx['calendar']!=c['calendar'] or idx['symbol_order']!=c['symbols']:raise ValueError('Calendar/order changed')
  for row in idx['months']:
   p=src.parent/'months'/f"{row['month']}.npz"
   if p not in verified:
    if p.stat().st_size!=row['source_NPZ_bytes'] or sha(p)!=row['source_NPZ_SHA256']:raise ValueError('Month bits changed')
    verified.add(p)
  for name in ('DAILY.json','EVENTS.json'):
   p=src.parent/name
   if p.stat().st_size!=idx['files'][name]['bytes'] or sha(p)!=idx['files'][name]['SHA256']:raise ValueError('Metadata changed')
  with np.load(archive,allow_pickle=False) as a:
   w=a[c['arm']]
   if w.dtype.str!=c['target_dtype'] or list(w.shape)!=c['target_shape'] or hashlib.sha256(w.tobytes()).hexdigest()!=c['target_array_SHA256']:raise ValueError('Target bits changed')
   np.testing.assert_array_equal(a['decision_us'],np.arange(*c['calendar'],DAY,dtype=np.int64))
   if tuple(a['symbol_order'])!=tuple(c['symbols']) or not np.isfinite(w).all() or np.abs(w).max()>.3+1e-12 or np.abs(w).sum(axis=1).max()>.6+1e-12:raise ValueError('Target caps/order')
   np.testing.assert_array_equal(a['COMBINED'],.5*a['STATIC50']+.5*a['SMA200_10PCT'])
  state=ROOT/c['baseline_state_local_locator']
  for name,h in c['baseline_files_SHA256'].items():
   if sha(state/name)!=h:raise ValueError('Original baseline changed')
  cb=json.loads((state/'BINDING.json').read_text())
  if cb['source_index_SHA256']!=c['source_index_SHA256'] or cb['target_array_SHA256']!=c['target_array_SHA256'] or cb['fine_profile_SHA256']!=b['fine_profile_SHA256'] or cb['mode']!='ORIGINAL':raise ValueError('Baseline pairing changed')
 return {'status':'PASS_TWO_ORIGINAL_FINE_TERMINAL60_ZERO_HISTORY','source_months_verified':len(verified),'planned_new_wallets':2,
  'historical_wallets_started':0,'old_wallets_rerun':0,'new_fits':0,'retained_2026_opened':0,'provider_downloads':0,
  'protective_enabled':False,'terminal_real_opens':60,'same_calendar_end':True,'parent_GO_required':True,'publication_required_before_launch':True}
