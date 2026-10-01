# 完整单窗口诊断：MDD计量口径补充

独立只读复核发现原模块说明第31行把MDD也归入“初始资金百分比”。
准确口径如下：

- gross、fee、spread、slippage、net为各项金额占初始NAV的百分比。
- MDD是相对此前最高NAV的最大回撤百分比：
  `max(1 - NAV[t] / max(NAV[:t+1])) × 100%`，NAV序列包含初始资金观察。
- turnover为原共同评价器的无量纲换手；Sharpe仍是本7日净NAV的描述性年化值。

表内MDD数值来自原共同评价器，数值正确，无须改动。
原模块文档、四份结果/验收凭证及原训练源码保持字节不变，本补充只纠正文档单位说明。
不重新拟合、不替换评价结果、不授予正式六fold、top-3或交易资格。

原说明：`MODULE_FR_ROLLING00_FULL_WINDOW_DIAGNOSTIC_20261002_V1.md`。
独立根侧补充凭证：`FR_ROLLING00_DOCUMENTATION_ADDENDUM_ACCEPTANCE_20261002_V1.json`。
