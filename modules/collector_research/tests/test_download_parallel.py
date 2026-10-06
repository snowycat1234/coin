"""Concurrency, manifest ordering, failure draining and aggregate space guards."""
import json
import threading
import time

import pytest

from pipeline import download


def setup_collector(tmp_path, monkeypatch, workers, count):
    jobs = [download.Job('BTCUSDT', 'klines', 2022, month) for month in range(1, count + 1)]
    monkeypatch.setenv('DOWNLOAD_WORKERS', str(workers))
    monkeypatch.setenv('DAILY_FALLBACK', '0')
    monkeypatch.setattr(download, 'REPORTS', tmp_path)
    monkeypatch.setattr(download, 'planned_jobs', lambda: jobs)
    monkeypatch.setattr(download, 'progress', lambda *args: None)
    monkeypatch.setattr(download, 'disk_guard', lambda *args, **kwargs: None)
    return jobs


def test_real_overlapping_workers_own_sessions_and_stable_manifest(tmp_path, monkeypatch):
    jobs = setup_collector(tmp_path, monkeypatch, 3, 3)
    barrier = threading.Barrier(3)
    created = []
    owners = []

    class Session:
        def __init__(self):
            self.closed = False
            created.append(self)
        def close(self):
            self.closed = True

    def fetch(job, session, *, reserved):
        assert reserved
        owners.append((threading.get_ident(), id(session)))
        barrier.wait(timeout=3)  # A serial implementation fails this check.
        time.sleep((4 - job.month) * .01)
        return {**job.record(), 'status': 'DOWNLOADED_VERIFIED'}

    monkeypatch.setattr(download, 'session', Session)
    monkeypatch.setattr(download, 'fetch', fetch)
    result = download.collect()
    assert len({thread for thread, _ in owners}) == 3
    assert len({session for _, session in owners}) == 3
    assert all(s.closed for s in created)
    assert result['completed'] == result['planned'] == 3
    assert [row['month'] for row in result['archives']] == [j.month for j in jobs]
    assert json.loads((tmp_path / 'download_manifest.json').read_text()) == result


def test_failure_drains_successes_and_starts_no_extra_jobs(tmp_path, monkeypatch):
    setup_collector(tmp_path, monkeypatch, 2, 5)
    barrier = threading.Barrier(2)
    calls = []

    class Session:
        def close(self):
            pass

    def fetch(job, session, *, reserved):
        calls.append(job.month)
        barrier.wait(timeout=3)
        if job.month == 1:
            raise RuntimeError('source unavailable')
        time.sleep(.04)
        return {**job.record(), 'status': 'DOWNLOADED_VERIFIED'}

    monkeypatch.setattr(download, 'session', Session)
    monkeypatch.setattr(download, 'fetch', fetch)
    with pytest.raises(RuntimeError, match='source unavailable'):
        download.collect()
    assert sorted(calls) == [1, 2]
    result = json.loads((tmp_path / 'download_manifest.json').read_text())
    assert result['status'] == 'FAILED_PARTIAL_PRESERVED'
    assert result['completed'] == 1 and result['planned'] == 5
    assert [row['month'] for row in result['archives']] == [2]


def test_space_reservations_cover_all_inflight_archives(monkeypatch):
    sizes = []
    monkeypatch.setenv('MAX_ARCHIVE_MIB', '1')
    monkeypatch.setattr(download, 'disk_guard', lambda n: sizes.append(n))
    reservations = download.DownloadReservations()
    reservations.acquire()
    reservations.acquire()
    assert sizes == [2**20 + 8192, 2 * (2**20 + 8192)]
    reservations.release()
    reservations.refresh()
    assert sizes[-1] == 2**20 + 8192
    reservations.release()
    assert reservations.reserved == 0
