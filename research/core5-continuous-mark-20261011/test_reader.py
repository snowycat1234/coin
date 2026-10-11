import json
import pytest
import mark_reader
from test_mark import row


def test_october_mark_reader_never_selects_trade_parts(monkeypatch,tmp_path):
    mark=b'mark source';trade=b'trade source';check=b'official checksum\n'
    r=row(period='2022-10');r.update(wrapper_id='OCT2022_PUBLISHED',ZIP_bytes=len(mark),
        ZIP_SHA256=mark_reader.digest(mark),CHECKSUM_member_SHA256=mark_reader.digest(check),official_checksum_text=check.decode())
    records=[]
    for family,body in [('klines',trade),('markPriceKlines',mark)]:
        records.append(dict(family=family,symbol='BTCUSDT',official_URL=r['official_URL'].replace('markPriceKlines',family),
            SHA256=mark_reader.digest(body),bytes=len(body),parts=[dict(path=family)],checksum_path=family+'.CHECKSUM'))
    raw=json.dumps({'monthly_sources':records}).encode()
    inv={'source_wrappers':{'OCT2022_PUBLISHED':dict(commit='a'*40,index_path='phase/index.json',index_SHA256=mark_reader.digest(raw))}}
    monkeypatch.setattr(mark_reader,'git',lambda *args:raw if args[-1].endswith('index.json') else check)
    reader=mark_reader.MarkSourceReader(inv,tmp_path)
    monkeypatch.setattr(reader,'part',lambda commit,p:mark if p['path']=='phase/markPriceKlines' else trade)
    assert reader.read(r)==(mark,check)
    wrong={**r,'family':'klines'}
    with pytest.raises(ValueError,match='independent'):reader.read(wrong)
    wrong={**r,'ZIP_SHA256':mark_reader.digest(trade)}
    with pytest.raises(AssertionError):reader.read(wrong)
