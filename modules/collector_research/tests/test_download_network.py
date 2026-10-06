"""Mock transport only: these do NOT certify reachability of Binance."""
import hashlib
import io
import zipfile
from pathlib import Path
import pytest
import requests
from pipeline import download


class Response:
    def __init__(self, status=200, content=b'', headers=None):
        self.status_code, self.content = status, content
        self.text = content.decode('utf-8', errors='replace')
        self.headers = headers or {}
    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f'HTTP {self.status_code}')
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def iter_content(self, size): yield self.content


class Session:
    def __init__(self, responses): self.responses, self.calls = list(responses), []
    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        assert self.responses, 'Unexpected network call'
        return self.responses.pop(0)


@pytest.fixture
def job(tmp_path, monkeypatch):
    monkeypatch.setattr(download, 'RAW', tmp_path)
    monkeypatch.setenv('MAX_ARCHIVE_MIB', '1')
    monkeypatch.setenv('REFRESH_CHECKSUMS', '0')
    monkeypatch.setattr(download.time, 'sleep', lambda n: None)
    j = download.Job('BTCUSDT', 'klines', 2022, 1)
    j.path.parent.mkdir(parents=True)
    return j


def payload(job):
    f = io.BytesIO()
    with zipfile.ZipFile(f, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr(job.stem.removesuffix('.zip') + '.csv', '1640995200000,100,101,99,100,1,1640995259999,100,1,0,0,0\n')
    return f.getvalue()


def proof(job, raw):
    return Response(content=(hashlib.sha256(raw).hexdigest()+'  '+job.stem+'\n').encode())


def test_old_cache_without_sidecar_is_adopted_not_redownloaded(job):
    raw = payload(job); job.path.write_bytes(raw)
    s = Session([proof(job, raw)])
    assert download.fetch(job, s)['status'] == 'ADOPTED_VERIFIED_CACHE'
    assert len(s.calls) == 1 and Path(str(job.path)+'.CHECKSUM').exists()
    assert download.fetch(job, Session([]))['status'] == 'VERIFIED_CACHE'


def test_404_unclassified_not_prelisting(job):
    result = download.fetch(job, Session([Response(404)]))
    assert result['status'] == 'ARCHIVE_UNAVAILABLE_UNCLASSIFIED'
    assert not job.path.exists()


def test_403_fails_without_venue_or_proxy_fallback(job):
    s = Session([Response(403)])
    with pytest.raises(requests.HTTPError): download.fetch(job, s)
    assert len(s.calls) == 1


@pytest.mark.parametrize('status', [200, 206, 416])
def test_resume_range_restart_and_complete_partial(job, status):
    raw = payload(job)
    have = len(raw) if status == 416 else len(raw)//2
    part = Path(str(job.path)+'.part'); part.write_bytes(raw[:have])
    body = raw[have:] if status == 206 else raw
    hdr = {'Content-Range':f'bytes {have}-{len(raw)-1}/{len(raw)}'} if status == 206 else {'Content-Length':str(len(raw))}
    s = Session([proof(job, raw), Response(status, body, hdr)])
    assert download.fetch(job, s)['status'] == 'DOWNLOADED_VERIFIED'
    assert job.path.read_bytes() == raw and not part.exists()
    assert s.calls[-1][1]['headers'] == {'Range':f'bytes={have}-'}


def test_bad_payload_quarantined_existing_archive_preserved_until_replacement(job):
    old = b'UNTRUSTED OLD CACHE'; job.path.write_bytes(old)
    raw = payload(job)
    s = Session([proof(job, raw), Response(content=b'bad'), Response(content=raw)])
    result = download.fetch(job, s)
    assert result['status'] == 'DOWNLOADED_VERIFIED'
    assert job.path.read_bytes() == raw
    assert next(job.path.parent.glob('*.old-*')).read_bytes() == old
    assert next(job.path.parent.glob('*.bad-*')).read_bytes() == b'bad'


def test_wrong_range_refused_before_appending(job):
    raw = payload(job); partial = Path(str(job.path)+'.part'); partial.write_bytes(raw[:5])
    s = Session([proof(job, raw), Response(206, raw[5:], {'Content-Range':f'bytes 0-{len(raw)-1}/{len(raw)}'})])
    with pytest.raises(ValueError, match='Range'): download.fetch(job, s)
    assert partial.read_bytes() == raw[:5] and not job.path.exists()
