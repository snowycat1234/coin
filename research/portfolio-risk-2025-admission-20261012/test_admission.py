import pytest
from recover_h2 import identity,old_records

def test_exact_old_receipts_60_missing_bodies_and_no_H1_daily_funding_or_other_domain():
 rows=old_records();assert len(rows)==60 and sum(r['bytes'] for r in rows)==82770519
 for row in rows:identity(row)
 row=rows[0]
 for changed in (dict(row,month='2025-06'),dict(row,symbol='OTHER'),dict(row,family='fundingRate'),dict(row,url=row['url'].replace('data.binance.vision','fapi.binance.com'))):
  with pytest.raises(AssertionError):identity(changed)
