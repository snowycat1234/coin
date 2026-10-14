"""Exact reviewed daily-quality proof consumer; no source-array or finance imports.

The carrier is a lossless encoding of the reviewed audit output. Completeness,
actual-source and imputation flags come only from those exact reviewed rows.
Following-day UTC clocks retain their original proxy semantics.
"""
from pathlib import Path
from types import MappingProxyType
import gzip,hashlib,json,math,struct
HERE=Path(__file__).resolve().parent
DAY=86400000000
SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
START=1655337600000000;END=1703980800000000
CALENDAR=(1672531200000000,1704067200000000)
PROOF_SHA='0f61b8fa7a099a6071a6e0505a6cf99c2ce04b3843ac2799ed638b402e2808b1'
PROOF_BYTES=3628422
CARRIER_SHA='ffb99d83840828c3bc6547562b530d9c584938acd9e23f1391a71079fdf091d7'
CARRIER_BYTES=80536
REVIEW_SHA='3ce7f58d42423379453c9015ce386f0074627380cf71cc64ef7e1f6ff1c21cfe'
CONTRACT_SHA='ff9569c00fa50689e8c383db8636ab2638f26991273160fc92c324219166962f'
AUDIT_GO_SHA='fc54cf827b0bc0d50c5e94bafa2be6dd4aead370e03c18e3853f312166ef5cd4'
PRICE_SHA='90896d1e89817baa58452d30c36a32b2ca3801efaa5da0637c825345d535c76f'
PREDECESSOR_SHA='bf61fac4b4dcb5690ae4bb6a284ad31488faa7145cf24bff9e747839926197e1'
CLOCK='ORIGINAL_COMPLETED_UTC_DAILY_BOUNDARY_PROXY_NOT_PROVIDER_PUBLICATION_CERTIFICATION'
_TOKEN=object()

def _exact_file(path,digest,size=None):
 path=Path(path)
 if path.is_symlink() or any(p.is_symlink() for p in path.parents) or not path.is_file():raise ValueError('EXACT_ORIGINAL200_PROOF_FILE_REQUIRED')
 body=path.read_bytes()
 if (size is not None and len(body)!=size) or hashlib.sha256(body).hexdigest()!=digest:raise ValueError('EXACT_ORIGINAL200_PROOF_FILE_HASH_REQUIRED')
 return body

def _freeze(value):
 if isinstance(value,dict):return MappingProxyType({k:_freeze(v) for k,v in value.items()})
 if isinstance(value,list):return tuple(_freeze(v) for v in value)
 return value

def _plain(value):
 if isinstance(value,MappingProxyType):return {k:_plain(v) for k,v in value.items()}
 if isinstance(value,tuple):return [_plain(v) for v in value]
 return value

def _validate_document(doc):
 if (doc.get('schema')!='PINNED_ORIGINAL200_DAILY_BAR_SOURCE_QUALITY_PROOF_V1' or type(doc.get('rows')) is not int or doc['rows']!=2820
     or doc.get('clock_semantics')!=CLOCK or any(doc.get(k) is not False for k in ('fresh_raw_CSV_verification','funding_unit_certified','provider_completeness_certified'))):
  raise ValueError('EXACT_ORIGINAL200_PROOF_SCOPE_REQUIRED')
 bars=doc.get('bars')
 if type(bars) is not list or len(bars)!=2820:raise ValueError('EXACT_ORIGINAL200_PROOF_UNION_REQUIRED')
 rows={};prices=bytearray()
 for i,row in enumerate(bars):
  t=START+(i//5)*DAY;s=SYMBOLS[i%5]
  if (type(row) is not dict or row.get('symbol')!=s or any(type(row.get(k)) is not int for k in ('open_us','close_us','available_us'))
      or (row['open_us'],row['close_us'],row['available_us'])!=(t-DAY,t,t)
      or row.get('complete') is not True or row.get('actual_source') is not True or row.get('imputed') is not False):
   raise ValueError('EXACT_ORIGINAL200_ACTUAL_COMPLETE_UNIMPUTED_ROW_REQUIRED')
  bits=row.get('close_float64_hex')
  if type(bits) is not str or len(bits)!=16:raise ValueError('EXACT_ORIGINAL200_PRICE_BITS_REQUIRED')
  try:b=bytes.fromhex(bits);price=struct.unpack('<d',b)[0]
  except (ValueError,struct.error) as e:raise ValueError('EXACT_ORIGINAL200_PRICE_BITS_REQUIRED') from e
  if b.hex()!=bits or not math.isfinite(price) or price<=0:raise ValueError('FINITE_POSITIVE_ORIGINAL200_PROOF_PRICE_REQUIRED')
  q=row.get('quality_proof')
  if type(q) is not dict or q.get('observed_minutes')!=1440:raise ValueError('GENUINE_ORIGINAL200_DAILY_QUALITY_REQUIRED')
  if t<1669939200000000:
   if q.get('authority')!='PINNED_PRIOR_PUBLIC_RAW_MINUTE_COLD_PROOF_AND_NEW_DAILY_NUMERIC_CHECK':raise ValueError('EXACT_PRIOR_PHASE_PROOF_AUTHORITY_REQUIRED')
  else:
   if (q.get('authority')!='PINNED_PRIOR_RAW_ARCHIVE_RECEIPTS_AND_CURRENT_REAL_TRADE_CHECKPOINT_COUNTS'
       or q.get('genuine_complete_kline') is not True or q.get('unique_minutes')!=1440
       or q.get('first_ms')!=(t-DAY)//1000 or q.get('last_ms')!=(t-60000000)//1000
       or q.get('original_raw_CRC_claim') is not True or q.get('original_raw_official_SHA_claim') is not True):
    raise ValueError('GENUINE_ORIGINAL200_CHECKPOINT_QUALITY_REQUIRED')
  key=(t,s)
  if key in rows:raise ValueError('DUPLICATE_ORIGINAL200_PROOF_ROW')
  rows[key]=_freeze(row);prices.extend(b)
 if END!=START+563*DAY or hashlib.sha256(prices).hexdigest()!=PRICE_SHA:raise ValueError('EXACT_ORIGINAL200_SELECTED_PRICE_SHA_REQUIRED')
 return MappingProxyType(rows)

class VerifiedOriginal200Proof:
 __slots__=('_rows',)
 def __setattr__(self,name,value):raise TypeError('IMMUTABLE_REVIEWED_ORIGINAL200_PROOF')
 def __init__(self,rows,token):
  if token is not _TOKEN:raise ValueError('EXACT_REVIEWED_ORIGINAL200_PROOF_CONSTRUCTION_REQUIRED')
  object.__setattr__(self,'_rows',rows)
 def identity(self):
  return dict(schema='H090_BOUND_ORIGINAL200_REVIEWED_QUALITY_V1',proof_SHA256=PROOF_SHA,review_SHA256=REVIEW_SHA,
   contract_SHA256=CONTRACT_SHA,audit_GO_SHA256=AUDIT_GO_SHA,selected_prices_raw_SHA256=PRICE_SHA,
   clocks=564,bars=2820,clock_semantics=CLOCK,fresh_raw_CSV_verification=False,provider_completeness_certified=False,
   provider_arrival_certified=False,funding_unit_certified=False)
 def packet_row(self,t,s,price):
  key=(t,s)
  if type(t) is not int or type(s) is not str or key not in self._rows:raise ValueError('ORIGINAL200_ROW_OUTSIDE_EXACT_PROOF_UNION')
  row=self._rows[key]
  if struct.pack('<d',float(price)).hex()!=row['close_float64_hex']:raise ValueError('ORIGINAL200_SOURCE_PRICE_PROOF_BIT_MISMATCH')
  out={k:row[k] for k in ('symbol','open_us','close_us','available_us','complete','actual_source','imputed')}
  out['close']=struct.unpack('<d',bytes.fromhex(row['close_float64_hex']))[0]
  out['record_locator']=f'reviewed_original200/{PROOF_SHA}/{t}/{s}'
  out['source_quality_proof_SHA256']=PROOF_SHA;out['source_quality_review_SHA256']=REVIEW_SHA
  out['quality_authority']=row['quality_proof']['authority']
  return out
 def validate_projection(self,decisions,clock,prices,ids):
  if (str(getattr(decisions,'dtype',None))!='int64' or str(getattr(clock,'dtype',None))!='int64'
      or str(getattr(prices,'dtype',None))!='float64' or str(getattr(ids,'dtype',None))!='int64'
      or tuple(getattr(decisions,'shape',()))!=(365,) or tuple(getattr(ids,'shape',()))!=(365,)
      or tuple(getattr(prices,'shape',()))!=(len(clock),5)):
   raise ValueError('EXACT_ORIGINAL200_PROJECTION_DTYPE_SHAPE_REQUIRED')
  seen=set()
  for i,decision in enumerate(decisions):
   t=int(decision);k=int(ids[i])
   if t!=CALENDAR[0]+i*DAY or k<199 or k>=len(clock) or int(clock[k])!=t:
    raise ValueError('EXACT365_ORIGINAL200_DECISION_BINDING_REQUIRED')
   for j in range(k-199,k+1):
    end=int(clock[j])
    if end!=t-(k-j)*DAY:raise ValueError('EXACT200_ORIGINAL_AVAILABLE_CLOCKS_REQUIRED')
    for col,s in enumerate(SYMBOLS):
     key=(end,s)
     if key not in self._rows:raise ValueError('ORIGINAL200_ROW_OUTSIDE_EXACT_PROOF_UNION')
     if struct.pack('<d',float(prices[j,col])).hex()!=self._rows[key]['close_float64_hex']:
      raise ValueError('ORIGINAL200_SOURCE_PRICE_PROOF_BIT_MISMATCH')
     seen.add(key)
  if seen!=set(self._rows):raise ValueError('EXACT365_ORIGINAL200_FULL_PROOF_UNION_REQUIRED')
  return self.identity()

def load_original200_proof():
 carrier=_exact_file(HERE/'ORIGINAL200_SOURCE_QUALITY_PROOF.json.gz',CARRIER_SHA,CARRIER_BYTES)
 try:body=gzip.decompress(carrier)
 except (OSError,EOFError) as e:raise ValueError('EXACT_ORIGINAL200_PROOF_CARRIER_REQUIRED') from e
 if len(body)!=PROOF_BYTES or hashlib.sha256(body).hexdigest()!=PROOF_SHA:raise ValueError('EXACT_ORIGINAL200_RAW_PROOF_HASH_REQUIRED')
 review=json.loads(_exact_file(HERE/'ORIGINAL200_SOURCE_QUALITY_REVIEW.json',REVIEW_SHA))
 if (review.get('schema')!='INDEPENDENT_ORIGINAL200_DAILY_SOURCE_QUALITY_PROOF_REVIEW_V1'
     or review.get('status')!='PASS_PINNED_PRIOR_SOURCE_QUALITY_AND_EXACT_CUBE_CLOSE_BITS'
     or review.get('contract_SHA256')!=CONTRACT_SHA or review.get('GO_SHA256')!=AUDIT_GO_SHA
     or review.get('historical_constructor_freeze_SHA256')!=PREDECESSOR_SHA
     or review.get('selected_prices_raw_SHA256')!=PRICE_SHA
     or review.get('artifacts',{}).get('SOURCE_BAR_QUALITY_PROOF.json')!={'SHA256':PROOF_SHA,'bytes':PROOF_BYTES}
     or any(review.get(k) is not True for k in ('all_365_original200_daily_windows_covered','all_rows_complete_actual_nonimputed','all_required_clock_symbol_pairs_unique','proof_raw_price_hash_reconstructed'))
     or review.get('historical_GO') is not False or review.get('historical_constructor_unblocked') is not False):
  raise ValueError('EXACT_INDEPENDENT_ORIGINAL200_REVIEW_BINDING_REQUIRED')
 return VerifiedOriginal200Proof(_validate_document(json.loads(body)),_TOKEN)
