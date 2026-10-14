# Explicit funding-unit arithmetic contract

Standalone Python standard-library checker. It reads only an explicitly supplied JSON object/file; it has no market downloader, network calls, credentials, account access, trading, or dependency on other project code. All included data are synthetic. This module is independently written; it does not bundle source datasets or existing research artifacts.

## Run

```
python -m unittest -v
python funding_contract.py synthetic_example.json
```

Exit codes: 0 = arithmetic matches the supplied expectation, 1 = arithmetic mismatch, 2 = rejected input. A PASS verifies only arithmetic under caller-declared units. It does not verify a source, position ownership, funding timing, market prices, exchange rounding, dataset completeness, or historical accounting.

## Contract

- Supply decimal strings for raw rate, signed base quantity, positive mark price, and expected quote-currency cashflow.
- A positive quantity means long; a negative quantity means short.
- Fraction input requires `unit=fraction` and `conversion=none`.
- Percent input requires `unit=percent` and `conversion=explicit_percent_divide_100`. The output records the applied scale.
- No rate-size heuristic, implicit percent parsing, guessed unit, annualization, leverage factor, or silent 100x correction is permitted.
- Per-settlement linear quote-settled arithmetic is `cashflow = -signed_base_quantity * mark_price * rate_fraction`. Negative cashflow is paid by the account; positive cashflow is received.
- Provenance must identify source kind, source reference, field, record, unit basis, product and rate basis. These are caller assertions, not authenticated evidence. Every result explicitly leaves provenance verification and historical dataset certification false.
- No `certified` mode exists. Inverse/coin-settled products and annualized rates are rejected. Explicitly declared high fractions are not silently reinterpreted as percentages.
- The bounded decimal-string grammar permits at most 24 digits on each side of the decimal point. Calculations use sufficient decimal precision for the supported input bounds. There is no exchange-specific rounding or fee settlement policy.

Synthetic example: 2 base units at 50,000 quote/base, rate 0.0001 as a fraction (=0.01%), implies -10 quote for a long or +10 quote for a short. Entering 0.01 as a fraction implies -1,000 quote for the same long. The checker flags a 100x mismatch against -10, without rewriting the rate.

## Public documentation findings (checked 2026-10-14)

1. Binance's official funding explanation defines funding from position nominal value and rate, nominal value from mark price and contract size, and positive funding as longs paying shorts. It expresses the default per-interval interest component as 0.01%.
   https://www.binance.com/en/support/faq/detail/360033525031
2. Binance's official USD-M market API documentation shows `interestRate` = `0.00010000` and `lastFundingRate` = `0.00038246` for the premium-index API. Together with the percentage explanation, this supports fractional API arithmetic as an inference. The history API uses the distinct field `fundingRate`. These examples are not an explicit unit declaration for an archive column.
   https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data
3. The official Binance public-data README describes archive delivery and checksum integrity. The inspected README does not document the funding archive column `last_funding_rate` or an explicit scale relationship to the API field. A checksum establishes byte integrity, not semantic units.
   https://github.com/binance/binance-public-data

The exact remaining evidence gap is an authoritative unit definition for the funding archive field, plus a verified binding of the actual historical inputs and their transformation chain to that definition. API examples, plausible magnitudes, a field-name resemblance, or synthetic tests cannot supply that binding. No historical archive was downloaded or inspected for this module.

## Suggested later integration boundary

Before a historical runner consumes funding, preserve source/field/record provenance and explicitly declared units. Use this checker against independently established expected settlement examples. Keep the real dataset's unit status unresolved until its archive-field contract and input transformation lineage are verified. This module does not change existing runners or certify their historical outputs.

## Tests

14 unittest methods cover positive/negative rates for long/short positions, flat and zero-rate cases, explicit percent equivalence, 100x mismatch in both directions without correction, sign mismatch, unknown units, malformed/nonfinite/float numeric inputs, missing provenance, unsupported product/rate basis, extra fields, declaration-versus-certification separation, input immutability, duplicate JSON keys, and CLI exit codes.
