# TLOB minimal upstream

Repository: https://github.com/LeonardoBerti00/TLOB
Commit: f1c0af4d81067978914361766db0457a7d8b6a46
Retrieved UTC: 2026-10-01T13:05:09.228246+00:00
License: MIT; complete LICENSE and original source bytes retained.

Local modifications: package-relative imports; explicit CPU-compatible device parameter;
remove unused plotting imports; BiN reset negative y Parameters in place to .01 preserving
optimizer identity and upstream reset behavior; guard feature-axis standard deviation below
1e-4 exactly as upstream already guards time-axis standard deviation. No replacement
attention, Transformer, MLP backbone or trainer. Original 3-class head replaced only by adapter.
Architecture transferred to historical trade-flow windows, not the paper's original LOB setup.
BiN and attention use the supplied past window; no token-level causal claim.
