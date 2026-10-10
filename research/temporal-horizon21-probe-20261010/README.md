# One fixed21-day horizon probe

Same8 canonical aggregates, prefix-only scaling, ridgeλ1 and four fixed blocks
as the [preserved next-day probe](../temporal-predictability-probe-20261010/README.md).
No horizon grid/feature selection/retuning/policy execution or new data.

Return: mean overCORE5 of close[t+21]/close[t]−1; risk: average over21 days of
mean five squared daily simple asset returns, not strategy PnL or intradayRV.
All22 real closes must be observed; training stays inside one original wallet,
full outcome strictlybeforefoldstart.63 outcome days perblock permit43 starts;
fixed disjoint starts0/21/42 cover those63 days. Overlapping windows are not43
independent observations; even three disjoint spans need not be independent.
The final endpoint may equal blockexclusiveend, but no outcome day is outside.

Baselines are prefix targetmean and latest20 fullymatured21-day targets.
Trailing history must be whollywithin an original wallet or currentforwardblock;
missing eligible history fallsback to prefixmean and is reported. Forecast risk
is clippedat0 using the unchanged rule.6 maturity/clock/gap/target/baseline tests
pass. Four closedform8x2 fits,18 coefficients perfit; NumPy/pytest/Ruff only.

Reproduce through existing bounded guard, with checkout/src in PYTHONPATH:
`python -m modules.temporal_horizon21_probe.probe --state STATE --destination NEW_OUTPUT`.
Protocol/source hashes are publicbeforefit. No continuation after this fixedrun.
