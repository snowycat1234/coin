import json,pytest
from .sources import risk_snapshot

def test_unauthorized_history_or_risk_is_unknown_not_absent():
    assert risk_snapshot(dict(http_status=403),'BTCUSDT')['status']=='UNAVAILABLE_HTTP'

def test_risk_snapshot_rejects_wrong_exchange_symbol_and_retains_all_tiers(tmp_path):
    path=tmp_path/'raw';row=dict(symbol='BTCUSDT',riskLimitValue='2000000',maintenanceMargin=.005,initialMargin=.01,mmDeduction='0',maxLeverage='100',isLowestRisk=1)
    path.write_text(json.dumps(dict(retCode=0,result=dict(list=[row]))))
    result=risk_snapshot(dict(http_status=200,response_path=str(path)),'BTCUSDT')
    assert result['tiers'][0]==row and not result['historical_tiers_certified']
    with pytest.raises(ValueError,match='symbol'):risk_snapshot(dict(http_status=200,response_path=str(path)),'ETHUSDT')
