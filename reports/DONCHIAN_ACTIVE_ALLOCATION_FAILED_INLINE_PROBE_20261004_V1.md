# D065 独立 inline 合成探测失败（保留）

子agent `active_allocation_reference` 在 root 已要求合并验证前启动一次 inline 探测。
实际任务 `4334609c665c422c9a07116c304ac70b`，标题 `D065独立激活预算参考合成核验`。
开始1791125299.260405，结束1791125345.4157672，实际 exit1；无市场/模型/经济结果，无重试。
原STATE任务JSON在模块闭合时逐字节归档。本记录是事后如实取证，不是事前协议。

执行环境为 hpc_linux，`with_task_progress.sh`/`bounded.sh`，既有v8环境和2线程配置，Python通过stdin执行。
探测循环本欲比较0/1/2/3/6个激活资产、EQUAL与ACTIVE_EQUAL的独立目标和producer目标，最后检验不支持策略拒绝新allocation。
实际第一轮使用 `symbols=('Z','A','M','Q','B','F')`，没有USDT后缀；在producer的正常身份校验处退出，后续比较与拒绝检查都未完成。不能登记为通过。

原stdin源码如下（保存取证，不再执行）：

```python
import numpy as np
import polars as pl
from scripts.investment import multi_asset_financial_audit as ref
from scripts.investment import donchian_daily_pool_target as prod
D=ref.DAY
symbols=('Z','A','M','Q','B','F')
for count in (0,1,2,3,6):
    frames=[]
    for j,s in enumerate(symbols):
        close=np.full(201,100.)
        close[199:]=110. if j<count else 100.
        dates=np.arange(201,dtype=np.int64)*D
        frames.append(pl.DataFrame(dict(symbol=[s]*201,open_us=dates,close_us=dates+D,available_us=dates+D,open=close,close=close,high=close+.1,low=close-.1,volume=np.ones(201))))
    bars=pl.concat(frames)
    decisions=[200*D,201*D]
    window=dict(start=decisions[0],end=decisions[-1]+D,bars={s:bars.filter(pl.col('symbol')==s) for s in symbols})
    for allocation in ('EQUAL','ACTIVE_EQUAL'):
        got=ref.target_reference(dict(window),symbols,allocation,strategy_id=ref.DONCHIAN_POOL_STRATEGY)
        actual,_=prod.fixed_targets(bars,decisions,symbols=symbols,allocation=allocation)
        expect=(min(.3,.6/count) if count else 0.) if allocation=='ACTIVE_EQUAL' else .1
        raw=[expect if j<count else 0. for j in range(6)]
        assert np.allclose(got['raw_signed_target'].to_numpy().reshape(2,6),[raw,raw],atol=1e-14,rtol=0)
        assert got.select('available_us','symbol','mode','eligibility_reason').equals(actual.select('available_us','symbol','mode','eligibility_reason'))
        assert np.allclose(got.select('raw_signed_target','target_weight').to_numpy(),actual.select('raw_signed_target','target_weight').to_numpy(),rtol=0,atol=1e-13)
for strategy in (None,ref.SMA_POOL_STRATEGY,ref.RSI_POOL_STRATEGY,ref.MOMENTUM_POOL_STRATEGY,ref.ALLOCATION_STRATEGIES['EQUAL']):
    try:ref.target_reference({},symbols,'ACTIVE_EQUAL',strategy_id=strategy)
    except ValueError:pass
    else:raise AssertionError('Active permission leak')
print('PASS: direct reference and producer, active-count 0/1/2/3/6, caps and covariance, EQUAL preserved, unsupported strategies rejected; no market replay')
```

原末traceback指向 `public_sma_perpetual.symbol_order` → `require`，错误：
`ValueError: Unique explicit ordered USDT symbols required`。
上方print的PASS字符串没有执行，不是实际结果。
正常独立核验由 root 的新合法合成用例与四个完整市场账户的独立直接窗口参考承担，不删除此失败。

## 独立核账首次CLI失败

另一个root首次核账调用只提供actual/run-dir，遗漏既有入口必填protocol/output。
任务 `416d6729bb5f4fec903117ad57276b65`，标题 `D065独立重建激活预算信号和四账户资金流水`，实际argparse退出码2。
发生在入口解析阶段，没有运行金融检查、没有写RUN_BINDING或金融结果，不是账本不守恒。
V2仅补齐原市场协议与新金融报告路径，同一已保存账户与原参考数学/容差保持；市场回放没有重跑。
