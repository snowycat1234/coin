"""Official bounded observations and an explicit conservative source clock."""
import csv,io
from datetime import datetime,timezone
import numpy as np
DAY=86400000000
START=1614556800000000
END=1704067200000000
URL='https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS&cosd=2021-03-01&coed=2023-12-31'
def clock(s):return int(datetime.strptime(s,'%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp()*1000000)
def parse(body):
 text=body.decode('utf-8-sig');reader=csv.DictReader(io.StringIO(text));assert reader.fieldnames in (['observation_date','VIXCLS'],['DATE','VIXCLS']),'Actual bounded official CSV schema required'
 datefield=reader.fieldnames[0];days=[];values=[]
 for row in reader:
  at=clock(row[datefield]);assert START<=at<END,'Official response observation outside admitted historical dates'
  # Validate dates BEFORE converting any observation value.
  value=row['VIXCLS'];v=float(value) if value not in ('.','') else np.nan
  assert np.isnan(v) or np.isfinite(v) and v>0,'Actual VIX positive or explicit missing'
  days.append(at);values.append(v)
 t=np.asarray(days,np.int64);v=np.asarray(values,float);assert len(t)>0 and np.all(np.diff(t)>0),'Unique increasing source dates required'
 return t,v
def feature(decisions,observation_us,values):
 d=np.asarray(decisions,np.int64);t=np.asarray(observation_us,np.int64);v=np.asarray(values,float)
 assert t.shape==v.shape and np.all(np.diff(t)>0) and np.all(np.diff(d)>0)
 actual=np.isfinite(v);t=t[actual];v=v[actual];available=t+2*DAY;x=np.full(len(d),np.nan);proof=[]
 for i,at in enumerate(d):
  k=int(np.searchsorted(available,at,side='right')-1)
  if k<0:proof.append(dict(decision_us=int(at),status='NO_AVAILABLE_ACTUAL_CLOSE'));continue
  age=int(at-available[k]);row=dict(decision_us=int(at),observation_date_us=int(t[k]),available_proxy_us=int(available[k]),age_after_proxy_us=age,status='KNOWN' if age<=4*DAY else 'STALE_ACTUAL_QUOTE_UNKNOWN')
  if age<=4*DAY:x[i]=v[k]
  proof.append(row)
 return x,proof
