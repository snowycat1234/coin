import importlib.util
from pathlib import Path
from decimal import Decimal
import pytest
spec=importlib.util.spec_from_file_location('drag',Path(__file__).with_name('core.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def test_short_sale_and_unpaid_inventory_are_joint_marked_bridge():
    r=dict(symbol='X',leg='OPEN',event_us=1,decimal_strings=dict(quantity_before='0',quantity_after='-2',position_delta='-2',mid_price='10',fee_amount='1',execution_cost='1',realized_PnL='0'))
    p={'X':dict(decimal_strings=dict(quantity='-2'))};o=m.split_money([r],[],p,dict(X=11))
    assert o['X','SHORT']['net']==Decimal('-4')
    p['X']['decimal_strings']['quantity']='0'
    with pytest.raises(ValueError):m.split_money([r],[],p,dict(X=11))

def test_substep_expiry_is_not_an_executable_sized_failure():
    assert m.expiry_class(dict(remaining_signed_quantity='9.9e-9'))=='SUBSTEP_REMAINDER'
    assert m.expiry_class(dict(remaining_signed_quantity='1e-8'))=='AT_LEAST_ONE_EXECUTABLE_STEP'
