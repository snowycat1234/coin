# Repaired-source fixed cost objective

This is a paper-inspired crypto adaptation on previously seen historical development data, not a replication of the paper's traditional-futures results or pristine out-of-sample evidence.

First runnable source milestone: `fb08e7024c177597f475979e106cbb22084c0e26`. Ten original SOL/XRP daily1m ZIPs and exact official CHECKSUM-response texts were recovered from already-published Git49017d88. All14,400minutes, CSV clocks/fields/CRC and dailyclose aggregation verify. Ten missing training prices change; every other price is unchanged. Existing359observations perasset and eight adjacent witnesses match the prior published repaired source exactly. No provider downloads.

The old `slow-momentum-cpd-cost-objective-20261011` stays BLOCKED/NOT_RUN. This separate version naturally changes eligible training endpoints from2526to3142 while keeping the same729-day calendar, causal mask rule and strict one-day maturity/purge. The shared training-only GP/scaler was refitted once: two capped optimizers converge at24/47iterations. No validation rows were returned during repair/refreeze. These data changes prevent attributing a comparison with older experiments solely to the cost objective.

The refreeze actually executed the published `fb08e702` source. Its original STARTED receipt's `optimizer_calls=2` denotes the planned count; both terminal results confirm completion. After that execution, the reviewer requested an additional pre-GP repair-hash assertion and clearer planned-counter names; these were added for future reproduction without repeating the fit. The original execution source hash is in CONFIG. The already-run source recovery and its post-fit price identity verification passed.

Both arms reuse the same10input/hidden16/tanh LSTM, same seeded fresh initialization,63daysequences,3seeds2001/2002/2003, Adam.001/clip1 and exactly64whole-calendar updates. Trend zerosCPchannels after the newly shared scaler. Original BASE27 costs, paid entry/exit/drift/mask/terminal, epsilon1e-9trainingloss and zero-epsilon scores remain unchanged. Five statistical gates and the descriptive near-cash prohibition remain frozen. All seeds/blocks are retained; no HPO, extension, checkpoint choice or automatic retry.

The standalone paired run uses the frozen prefit artifacts rather than recomputing GP during model fitting. Before six fits, publish the source/config, verify remoteHEAD and byte-compare each source and prefit file through its immutable rawGitHub URL; write `SOURCE_PUBLIC_READBACK.json` with statusPASS, published_commit and config_sha256 into the separate STATE. This receipt is mandatory. Original price archive recovery uses `run.recover_archive(ROOT, ARCHIVE, original_protocol)` from the three pinned existingGitparts if needed. It never reads collector locks or2026history.

```bash
cd /workspace/coin-slow-momentum
state=/workspace/slow-momentum-cost-repaired-state
config_sha=d54f4b20133bd281c04d1ae3eeb4f9f51a7de14d0d0cf54d439ff9f520aef891
published=$(git rev-parse HEAD) # use the published prefit source commit
COIN_CPD_STATE="$state" bash research/slow-momentum-cpd-20261011/launch.sh \
  /workspace/coin/.venv/bin/python -m modules.slow_momentum_cpd.repaired_cost \
  --state "$state" --config-sha "$config_sha" --published-commit "$published"
```

Source checks (zerohistoricalmodel fits): the same bounded launch with `python -m modules.slow_momentum_cpd.repaired_data recover --state NEW_STATE`, followed by `refreeze` if intentionally verifying the training-derived refreeze; compare actual price/parameter identities rather than timestamp-containing receipt hashes. Use a fresh STATE and record that verification separately. Never silently retry a begun scientific run.

The financial output is only a static reference-capital price/cost proxy. Actual signed funding, native minute execution/availability, lot/minimum-notional/capacity and shared-wallet risk remain unbound. No wallet, netProfit/APR, deployment or live qualification is authorized by a proxy pass.
