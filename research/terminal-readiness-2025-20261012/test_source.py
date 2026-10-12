import pytest
import source
from common import SYMBOLS,digest

def test_only_authorized_jan1_hour_before_lock_and_no_shifted_source(monkeypatch):
 source.bounds()
 monkeypatch.setattr(source,'START',1772323200000000)
 with pytest.raises(AssertionError):source.bounds()

def test_all_five_actual_january_trade_originals_are_reused_exact_from_public_git():
 for s in SYMBOLS:
  raw,proof=source.trade_body(s);assert digest(raw)==proof['original_SHA256'] and len(raw)==proof['bytes'];assert proof['URL'].endswith(f'/{s}-1m-2026-01.zip')

def test_exact_official_monthly_and_daily_job_urls(tmp_path):
 source.configure(tmp_path)
 from modules.collector_research.pipeline.download import Job
 for s in SYMBOLS:
  for family,day in (('markPriceKlines',1),('fundingRate',None)):assert Job(s,family,2026,1,day).url==source.expected_url(s,family)
 with pytest.raises(AssertionError):source.expected_url('OTHER','markPriceKlines')
 with pytest.raises(AssertionError):source.expected_url('BTCUSDT','klines')
