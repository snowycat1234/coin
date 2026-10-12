"""Boundary/identity and unchanged actual grid/paid-close golden checks."""
import sys,importlib.util
from pathlib import Path
import numpy as np
import pytest
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(HERE))
import driver as m
def test_saved_follow_adapter_rejects_wrong_calendar_and_column_identity(tmp_path):
 d=np.arange(m.native.utc('2023-01-01'),m.native.utc('2024-01-01'),m.DAY);w=np.zeros((365,5));w[0,0]=.12;p=tmp_path/'t.npz'
 def write(**changes):
  data=dict(decision_us=d,FOLLOW=w,FADE=-w,symbol_order=np.array(m.SYMBOLS));data.update(changes);np.savez_compressed(p,**data)
 write();a,b=m.exact_targets('Y2023',p);np.testing.assert_array_equal(a,d);np.testing.assert_array_equal(b,w)
 for changes in (dict(decision_us=d+m.DAY),dict(FADE=w),dict(symbol_order=np.array(m.SYMBOLS[::-1])),dict(FOLLOW=np.full_like(w,np.nan))):
  write(**changes)
  with pytest.raises((AssertionError,ValueError)):m.exact_targets('Y2023',p)
 write()
 with pytest.raises(AssertionError):m.exact_targets('Y2025',p)
def test_existing_calendar_exit_and_funding_financial_methods_are_unchanged():
 from scripts.investment.perpetual_closing_exempt_account import USDTLinearPerpetualAccount as Fine
 assert m.Closing.execute_fill is Fine.execute_fill and m.Closing.apply_funding is Fine.apply_funding and m.Closing._floor is Fine._floor
 assert m.proto()['fixed_order']==['Y2023','Y2025'] and m.profile_sha()==m.proto()['quantity_profile']['SHA256']
