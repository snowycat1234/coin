# CME Bitcoin CFTC positioning: bounded feasibility, 2026-10-10

**NO-GO for fitting this input over 2021–June 2024.** The direct official
historical archive index returned HTTP 403 with a 17-byte Cloudflare error 1010
body. The response is preserved with a SHA256 binding; cookies are omitted from
published metadata. No archive was downloaded, retried, or obtained through an
alternate host, proxy, or changed identity. This access failure does not mean
the underlying reports are absent.

The official [COT FAQ](https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm)
states that releases normally occur Friday at 3:30 pm Eastern using Tuesday's
positions, that holidays can change release dates, and that historical release
dates are available only for the 13 months of reports on its website. The
current [release schedule](https://www.cftc.gov/MarketReports/CommitmentsofTraders/ReleaseSchedule/index.htm)
is tentative and covers 2026. It supplies no verified mapping for this task's
historical range. A routine Tuesday-to-Friday shift cannot establish past
availability. No historical holiday or delayed-release dates were adopted.

Useful partial evidence is preserved from four previously retrieved official
web references. The files explicitly identify themselves as rendered web-tool
cache snapshots, not original CFTC HTML or report archives. Their checksums
bind the exact published snapshot bytes. The original 403 body is a separate
representation. The saved [historical index](https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalCompressed/index.htm)
lists Legacy Futures Only archives for 2021, 2022, 2023 and 2024; archive sizes,
archive checksums, actual CSV headers and market rows remain unverified.

The official [Legacy schema](https://www.cftc.gov/MarketReports/CommitmentsofTraders/HistoricalViewable/cotvariableslegacy.html)
documents these one-based field positions:

| Field | Description | Role |
|---:|---|---|
| 3 | As of Date in Form YYYY-MM-DD | Position date, not publication time |
| 4 | CFTC Contract Market Code | Requested `133741`, actual rows unverified |
| 8 | Open Interest (All) | Denominator |
| 9 | Noncommercial Positions-Long (All) | Long count |
| 10 | Noncommercial Positions-Short (All) | Short count |
| 39 / 40 | Change in Noncommercial-Long / Short (All) | Future independent change cross-check |
| 126 | Contract Units | Must inspect actual product units and continuity |

The feature proposal is explicitly read as
`((S_t - L_t) - (S_previous_week - L_previous_week)) / OI_t`, with current total
open interest in the denominator. This is a trader-category CME product
positioning measure. It makes no claim about retail identity, all crypto
markets, or the paper's predictive performance. The official FAQ also says
weekly changes can reflect traders changing category, entering the reporting
population, or leaving it; the measure is not a pure trading-flow series.
No feature values were
computed. The Dunbar and Owusu-Amoako DOI was not used as data or alignment
evidence; the paper's Tuesday-versus-Friday treatment remains unverified.

For an eventual usable row, both current and prior report values need verified
availability, consistent contract code/product/units, positive total OI and
consecutive observed report weeks. The eligibility clock is the first daily
00:00 UTC decision **strictly after verified release plus 48 hours**. A
date-only source needs an explicit conservative timestamp bound before use.
Unknown releases and gaps are excluded; they are not filled from a guessed
calendar or previous feature value. The requested contract's historical
continuity, unit values, missing reports and publication exceptions are all
UNKNOWN, because original market rows were not acquired.

`DAILY_EXCLUSIONS.csv` contains the 1,277 requested daily UTC decisions with
eligibility false and a blank feature value. They are requested-domain
placeholders, not invented report observations. This includes Terra, FTX and
all four folds in the requested historical domain. None is declared usable.

`RESULT.json` is the machine-readable decision and source/coverage manifest.
`build_partial.py` reconstructs the decision and exclusions from the preserved
evidence, checking the denial body and supporting source text. Creation time
is runtime metadata; source hashes and exclusion bytes are deterministic.

```bash
# Run through the applicable existing project resource launcher.
python research/cftc-btc-positioning-feasibility/build_partial.py \
  --evidence research/cftc-btc-positioning-feasibility \
  --output /own/state/cftc-feasibility-reconstruction
```

The 30 MiB acquisition cap remains in force. Direct official HTTP acquisition
was one attempt and 17 body bytes; original report-archive acquisition was
zero. Rendered snapshot sizes are recorded separately and do not claim to
measure their underlying web-cache HTTP traffic. Cloud Python used the existing
unchanged one-CPU resource monitor, 2 GB address/RSS cap, swap=0 and GPU=0.
There were no fits, tuning, backtests, credentials, trades or Library writes.
The isolated branch changes only this research module.

Reopen only with lawfully reachable official archive bytes or a source-bound
existing cache, plus trustworthy historical publication evidence. Recheck the
product/units/report gaps, preserve verified Terra and FTX observations, and
test the release clock before fitting. This result assesses the evidence
available in this module; it does not prove the concept can never be used.
