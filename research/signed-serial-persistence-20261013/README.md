# Signed intraday persistence: one local diagnostic

Fixed nested OLS comparison of signed adjacent five-minute return covariance
against existing price/HAR/semivariance/sampling/unsigned-jump controls.
No strategy income or novelty beyond the documented bounded history review
is established. All validation years are seen development. No wallet is run.

`PREREG.json` defines the exact recipe and rejection criteria. `core.py` is pure
numerical logic. `test_synthetic.py` never opens historical files. `prepare.py`
reads only immutable saved source inputs; it cannot fit a model. `run.py fit`
and `run.py score` are separate so model bytes are frozen before scoring.

The named public source packet is currently absent locally. Existing source
identity metadata is not a source body. `read_saved_source.py` can materialize
only the one exact previously published packet after parent coordination;
there are no provider calls, retries or alternative-source recovery.

Commands use the existing bounded launcher and inner explicit CPU cap.
Use fresh result paths; no failed attempt is overwritten.

1. Synthetic tests: `python test_synthetic.py`.
2. Source-only preparation: `python prepare.py --jump-packet CACHE/JUMP_INPUTS_PACKET.zip --output PREPARED_001`.
3. After the actual cohort receipt and parent GO: `python run.py fit --prepared PREPARED_001 --output FIT_001`.
4. Bind the returned model SHA, then: `python run.py score --prepared PREPARED_001 --model FIT_001/MODEL.json --model-sha256 EXACT_RETURNED_SHA --output SCORES_001`.

Primary gate requires all three full calendars to pass both conditional
prediction and independent paid-price-cost relevance. The roundtrip probe
excludes funding and portfolio execution. It is never native wallet PnL.
