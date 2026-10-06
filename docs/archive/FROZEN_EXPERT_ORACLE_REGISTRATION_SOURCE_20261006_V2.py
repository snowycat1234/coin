import json,os
from datetime import UTC,datetime
from quant.paths import ROOT
from scripts.investment.reuse_cycle_controls import sha
p=ROOT/'protocols/FROZEN_EXPERT_ORACLE_20261006_V1.json';spec=json.loads(p.read_bytes())
assert spec['experts']==['CASH','HOLD','SMA200_SIGNED','DONCHIAN20_10','DC_TWO_SPEED','DC_CONFIRMED_SHORT','PUBLIC_SMA50_200']
assert not (ROOT/'reports/FROZEN_EXPERT_ORACLE_OPPORTUNITY_20261006_V1.json').exists()
spec.update(created_utc=datetime.now(UTC).isoformat(),before_oracle_results_revision=dict(previous_path=str(p.relative_to(ROOT)),previous_sha256=sha(p),
    reason='User hypothesis explicitly includes fast-confirmation bear/protection tradeoff; include preserved D101 complete fixed expert,0newaccounts0parameterchanges, before any oracle calculation.'),
    source_sha256=sha(ROOT/'scripts/investment/oracle_expert_opportunity.py'))
spec['experts'].append('SMA200_SHORT50')
out=ROOT/'protocols/FROZEN_EXPERT_ORACLE_20261006_V2.json'
with out.open('x') as f:json.dump(spec,f,indent=2,ensure_ascii=False);f.write('\n')
with (ROOT/'docs/RESEARCH_DECISION_LOG.md').open('a') as f:f.write('\n## D104 oracle运行前补充expert\n\n'+spec['created_utc']+'：7→8专家，额外保留D101固定SMA200_SHORT50（自有修改，非完整公开family）。用户条件优势假设以慢趋势熊市收益/快确认反弹保护为核心，故纳入已完成负结果配方；参数不变、0新账户，未查看任何oracle结果。V1保留并由V2在运行前supersede，仅60日horizon与500USDT门槛不变。\n')
print(json.dumps(dict(status='EIGHT_FROZEN_EXPERTS_PREREGISTERED_BEFORE_ORACLE',task_id=os.environ['COIN_TASK_ID'])))
