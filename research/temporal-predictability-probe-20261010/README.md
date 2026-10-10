# Fixed next-day predictability probe

One eight-input/two-output ridge recipe, penalty1 on mean squared error,
four prescribed63-day forward blocks. Features/standardization/penalty/targets/
trailing20 baseline fixed before scoring; no feature/grid selection or retuning.
True completed-close labels only, strict prefix maturity; no synthetic paidflat
outcomes. Return is equal-weightCORE5 simple return; risk is mean squared five
asset daily returns, not intraday realized variance. Original market aggregates
retain their ten-asset semantics. No portfolio execution or profit claim.

Installed NumPy suffices; tests use pytest/Ruff. Reproduce with PYTHONPATH pointing
to checkout and src, through existing bounded resource launcher:
`python -m modules.temporal_predictability_probe.probe --state STATE --destination NEW_OUTPUT`.
Immutable output, four closed-form fits,18 coefficients per fit, no deep training.
Historical project-seen data;63 observations perblock, dependent market days.
7 label-clock/maturity/normalization/trailing/mask/ridge unit tests pass.
