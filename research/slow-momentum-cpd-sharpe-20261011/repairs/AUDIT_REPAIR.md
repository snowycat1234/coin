# Read-only audit receipt repair

The first audit of the completed six fits reached the final receipt writer,
then failed encoding a NumPy Boolean in the independently recomputed gates.
The partial receipt and failed resource receipt are preserved in the independent
state; their identities are recorded in AUDIT_FAILURE.json. That partial file
is not a successful audit. No scientific training is repeated.

The auditor converts the same four gate expressions to builtin bool. It still
checks the published original auditor hash in the fit commit, and the current
trainer and original focused tests against that commit. The executing auditor's
hash and commit are now disclosed separately in the successful receipt. The
second read-only audit uses --run-number 2. No scoring, threshold, policy,
checkpoint, original result, original position CSV, GP or scaler changed.

One focused regression passed for NumPy values, including exact zero and absent
confidence bounds. The original 29 prefit tests remain the fit-time evidence.
This engineering fix adds zero scientific attempts, fits or optimizer updates.
