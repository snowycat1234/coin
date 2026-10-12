"""Only parse/check the already downloaded official policy documents, no market outcomes."""
import argparse,gzip,hashlib,html,json,re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
ROWS=[('20191030',1.75),('20200303',1.25),('20200315',.25),('20220316',.5),('20220504',1.),('20220615',1.75),('20220727',2.5),('20220921',3.25),('20221102',4.),('20221214',4.5),('20230201',4.75),('20230322',5.),('20230503',5.25),('20230726',5.5)]

def build(input_dir,nyfed,output):
    bodies={};records=[];ref=json.loads(nyfed.read_text())['refRates'];order=sorted(ref,key=lambda r:r['effectiveDate'])
    for day,upper in ROWS:
        b=(input_dir/(day+'.html')).read_bytes();text=html.unescape(b.decode())
        match=re.search(r'For release at (\d+):(\d+) (a\.m\.|p\.m\.) (EST|EDT)',text)
        if match is None:raise ValueError('Official release clock missing '+day)
        hour,minute=int(match[1]),int(match[2]);hour=hour%12+(12 if match[3]=='p.m.' else 0)
        local=datetime.strptime(day,'%Y%m%d').replace(hour=hour,minute=minute,tzinfo=ZoneInfo('America/New_York'))
        if local.tzname()!=match[4]:raise ValueError('Actual announcement DST mismatch')
        iso=local.date().isoformat();subsequent=next(r for r in order if r['effectiveDate']>iso)
        if subsequent['targetRateTo']!=upper:raise ValueError('Official target bound differs from NYFed independent cross-check '+day)
        paras=re.findall(r'<p>(.*?)</p>',text,re.S)
        statement=next(p for p in paras if 'target range for the federal funds rate' in p and any(w in p for w in ('lower','raise')))
        records.append(dict(statement_date=iso,published_us=int(local.timestamp()*1e6),published_UTC=local.astimezone(ZoneInfo('UTC')).isoformat(),target_upper_percent=upper,
          official_url='https://www.federalreserve.gov/newsevents/pressreleases/monetary'+day+'a.htm',
          original_SHA256=hashlib.sha256(b).hexdigest(),original_bytes=len(b),original_release_text=match[0],
          independent_NYFed_effective_date=subsequent['effectiveDate'],target_paragraph=re.sub('<.*?>','',statement)))
        bodies[day]=b.decode()
    output.mkdir(parents=True,exist_ok=True)
    (output/'POLICY_RELEASES.json').write_text(json.dumps(records,indent=2,allow_nan=False)+'\n')
    (output/'STATEMENTS.json.gz').write_bytes(gzip.compress(json.dumps(bodies,sort_keys=True).encode(),mtime=0))
    print(json.dumps(dict(verified_policy_releases=len(records),official_original_bytes=sum(r['original_bytes'] for r in records),NYFed_crosscheck_SHA256=hashlib.sha256(nyfed.read_bytes()).hexdigest(),new_market_reads=0,new_model_fits=0)))
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--input',type=Path);a.add_argument('--nyfed',type=Path);a.add_argument('--output',type=Path);q=a.parse_args();build(q.input,q.nyfed,q.output)
