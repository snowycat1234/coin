import io,zipfile
from pathlib import Path
import numpy as np
import pytest
from source import frame,archive_key,Intake,BUCKET

def ziprow(path,rows):
 with zipfile.ZipFile(path,'w') as z:z.writestr(path.name[:-4]+'.csv','\n'.join(','.join(map(str,r)) for r in rows)+'\n')
def row(at):return [at,10,12,9,11,2,at+86400000-1,20,3,1,10,0]
def test_actual_daily_interval_and_missing_preserved(tmp_path):
 p=tmp_path/'BTCUSDT-1d-2022-10.zip';at=1664582400000;ziprow(p,[row(at),row(at+2*86400000)]);f,complete=frame(p,'2022-10');assert not complete and len(f)==2 and f.timestamp_ms.tolist()==[at,at+2*86400000]
def test_invalid_close_or_conflicting_duplicate_rejected(tmp_path):
 p=tmp_path/'BTCUSDT-1d-2022-10.zip';r=row(1664582400000);r[6]+=1;ziprow(p,[r])
 with pytest.raises(AssertionError):frame(p,'2022-10')
 ziprow(p,[row(1664582400000),row(1664582400000)])
 with pytest.raises(AssertionError):frame(p,'2022-10')
def test_source_date_guard_precedes_network():
 for d in ('2026-03','2026-09','2024-01','2022-07'):
  with pytest.raises(AssertionError):archive_key('BTCUSDT',d)
 assert '2022-10' in archive_key('FTTUSDT','2022-10')
 with pytest.raises(AssertionError):archive_key('MATICUSDT','2024-01-01',True)
 assert archive_key('MATICUSDT','2024-01-01',True,True).endswith('2024-01-01.zip')
 with pytest.raises(AssertionError):archive_key('MATICUSDT','2024-01-02',True,True)
def test_directory_absence_is_unknown_without_archive_download(tmp_path):
 i=Intake(tmp_path);calls=[]
 def get(url,kind,limit):
  calls.append((url,kind));key=archive_key('FTTUSDT','2023-01');raw=f'<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><Name>data.binance.vision</Name><Prefix>{key}</Prefix><IsTruncated>false</IsTruncated></ListBucketResult>'.encode();return raw,dict(status=200)
 i.get=get;r=i.acquire('FTTUSDT','2023-01');assert r['status'].startswith('UNKNOWN') and not r['historical_nontradable'] and len(calls)==1 and calls[0][1]=='metadata'
