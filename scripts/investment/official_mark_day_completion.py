"""Thin official daily-data completion for a proven incomplete monthly mark file.

Never interpolates. Original month is kept, overlap must agree numerically,
and both official input CHECKSUMs plus the derived artifact are retained.
"""
import csv,io,zipfile
from datetime import UTC,datetime,timedelta
from decimal import Decimal
from pathlib import Path
import httpx
from scripts.investment.cta_cycle_source import sha,save
from scripts.investment.official_carry_chronology_source import metadata_inspector

def raw_rows(archive,header):
    with zipfile.ZipFile(archive) as z:
        members=z.infolist();assert len(members)==1 and members[0].file_size<128000000
        rows=list(csv.reader(io.StringIO(z.read(members[0]).decode('utf-8-sig'))))
    if rows[0][0]=='open_time':assert rows.pop(0)==header
    assert all(len(r)==12 for r in rows)
    return rows

def complete(archive,entry,job,upstream,header,max_days):
    assert entry['kind']=='markPriceKlines' and entry['interval']=='1m' and 0<max_days<=6
    rows=raw_rows(archive,header);lookup={int(r[0]):r for r in rows};assert len(lookup)==len(rows)
    start=datetime.fromisoformat(entry['month']+'-01').replace(tzinfo=UTC);end=(start+timedelta(days=32)).replace(day=1)
    begin=int(start.timestamp()*1000);stop=int(end.timestamp()*1000);expected=set(range(begin,stop,60000))
    assert set(lookup)<=expected
    missing=sorted(expected-set(lookup));days=sorted({datetime.fromtimestamp(t/1000,UTC).strftime('%Y-%m-%d') for t in missing})
    assert missing and len(days)<=min(2,max_days), 'Finite mark repair budget; no broad day sweep'
    parents=[dict(path=str(archive),sha256=sha(archive),official_url=entry['url'],rows=len(rows))];new_rows=0
    for day in days:
        url=f"https://data.binance.vision/data/futures/um/daily/markPriceKlines/{entry['symbol']}/1m/{entry['symbol']}-1m-{day}.zip"
        e=dict(market='futures/um',partition='daily',kind='markPriceKlines',symbol=entry['symbol'],interval='1m',day=day,url=url,checksum_url=url+'.CHECKSUM')
        with httpx.Client(timeout=12,follow_redirects=False) as client:meta=metadata_inspector(client)(e)
        save(job/('DAILY-'+day+'-METADATA.json'),meta)
        assert meta['metadata_object_available'] and 0<meta['announced_zip_bytes']<2000000
        base=url.removeprefix(upstream.BASE_URL);prefix,name=base.rsplit('/',1)
        upstream.download_file(prefix+'/',name,folder=str(job));upstream.download_file(prefix+'/',name+'.CHECKSUM',folder=str(job))
        file=job/base;checksum=job/(base+'.CHECKSUM');fields=checksum.read_text().split()
        assert len(fields)==2 and fields[1]==name and sha(file)==fields[0]==meta['checksum']['announced_zip_sha256']
        assert file.stat().st_size==meta['announced_zip_bytes']
        daily=raw_rows(file,header);opened=int(datetime.fromisoformat(day).replace(tzinfo=UTC).timestamp()*1000)
        assert [int(r[0]) for r in daily]==list(range(opened,opened+86400000,60000))
        for row in daily:
            t=int(row[0])
            if t in lookup:assert all(Decimal(a)==Decimal(b) for a,b in zip(lookup[t],row)), 'Official month/day overlap mismatch'
            else:lookup[t]=row;new_rows+=1
        parents.append(dict(path=str(file),sha256=sha(file),official_url=url,rows=len(daily),
            checksum_path=str(checksum),checksum_sha256=sha(checksum),metadata=meta))
    assert set(lookup)==expected and new_rows==len(missing)
    text=io.StringIO(newline='');csv.writer(text,lineterminator='\n').writerows(lookup[t] for t in sorted(lookup))
    derived=job/'derived-complete-month.zip';member=f"{entry['symbol']}-1m-{entry['month']}.csv"
    with zipfile.ZipFile(derived,'w',compression=zipfile.ZIP_DEFLATED) as z:z.writestr(member,text.getvalue())
    checksum=job/'derived-complete-month.zip.CHECKSUM';checksum.write_text(sha(derived)+'  '+derived.name+'\n')
    derived_entry=dict(entry,url='derived://explicit-official-month-plus-days',checksum=dict(announced_zip_sha256=sha(derived)),
        announced_zip_bytes=derived.stat().st_size,checksum_provenance='LOCAL_DERIVED_NOT_BINANCE_OFFICIAL',published_inputs=parents)
    derivation=dict(kind='EXACT_ORIGINAL_MONTH_PLUS_MISSING_OFFICIAL_DAILY_ROWS',missing_minutes=len(missing),
        extra_official_daily_archives=len(days),original_month_unchanged=True,interpolated=False,all_overlap_fields_equal=True,parents=parents)
    save(job/'DERIVATION.json',derivation)
    return derived,checksum,len(text.getvalue().encode()),derived_entry,derivation
