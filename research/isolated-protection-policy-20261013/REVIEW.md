# Review packet: isolated half-equity full exit

This is a new, separate research policy. No historical protective wallet has run. Parent review and a resource-admitted GO are required before any such run.

- `PROTOCOL.json`: hypothesis, exactly one 50%-of-isolated-balance threshold, causal clock, execution/reentry rules, fixed baseline-comparable 11-case comparison, known limitations.
- `protective_policy.py`: subclass of the frozen scheduler; original Decimal account and normal scheduler remain unchanged. A completed minute-close mark can schedule full reduce-only exit. Pending intent survives daily supersession and sublot capacity. Same-direction reentry requires a later neutral/opposite daily target after flat. An observed liquidation-required halt, adverse one-minute gap, partial fill, cap-priority unexecutable-risk stop, or unfilled horizon is not retroactively rescued. Equal-timestamp funding fully precedes a new guard signal.
- `RUN_MANIFEST.json`: exact 11 target-array/source-index identities for 2023/24/25; separate original 2023/25 STATIC50/SMA archive bindings; two-worker resource policy. 2023/25 CS/VOL targets exist, but their native paired baselines are not established in this study. They are excluded by a fixed baseline-comparability criterion before guard outcomes, and require separate preregistration if studied later.
- `preflight_run_plan.py`: read-only exact-case, target/protocol, original archive, all-month source and disk check. It launches no wallet and explicitly leaves RAM/cgroup verification outstanding.
- `FREEZE.json`: adapter/protocol/test/preflight/manifest plus frozen scheduler, account and quantity profile SHA-256 identities.
- `test_policy_synthetic.py`, `TEST_RESULTS.txt`: eleven synthetic causal/account/recovery tests, all pass.

Original baselines took roughly 186–229 seconds per 2024 account and 217–222 seconds for each 2023/25 combined account. Allow about 4–6 minutes per new guarded account, ~45–70 minutes sequential for 11 cases, or approximately 25–40 minutes with two *resource-admitted* independent one-CPU workers plus audit/packaging; these are estimates, not promises. The shared 8GB RAM, 2GB RSS stop per worker, no swap/GPU, 15GiB disk reserve, fresh state per case, and 250MB case limit must be checked immediately before GO. Parallel workers must never share/mutate a wallet state.
