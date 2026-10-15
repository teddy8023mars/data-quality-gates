# Strict synthetic retention contract

The [base seven-check contract](retention-contract.md) catches retained users exceeding cohort size but permits fractional counts and a wrong rate inside 0..1. The new [eight-check variant](../examples/moba-retention/strict-contract.json) adds integral-count requirements and count/rate consistency. These close specific documented gaps; they do not add an orchestrator or live monitoring service.

## Actual CLI outcomes

All fixtures have eight records from the same pinned synthetic MOBA snapshot. [Provenance](../examples/moba-retention/PROVENANCE.md) records the source/checksum and deliberate changes. CSV record 2 is the only modified record.

| Fixture | Deliberate change | Failing check IDs | Exit | Recorded report |
|---|---|---|---:|---|
| clean.csv | None | None | 0 | [clean](strict-clean-output.json) |
| wrong-rate.csv | Rate 0.5 for retained 2 / cohort 3 | rate_matches_counts | 1 | [wrong rate](strict-wrong-rate-output.json) |
| fractional-count.csv | Retained 2.5, rate adjusted to 0.8333333333333334 | nonnegative_retained (integer requirement) | 1 | [fractional count](strict-fractional-count-output.json) |
| dirty.csv | Retained 4 / cohort 3, rate left unchanged | retained_within_cohort, rate_matches_counts | 1 | [impossible count](strict-dirty-output.json) |

The fractional fixture deliberately keeps rate arithmetic within tolerance, isolating the integer failure. Check hits can overlap: two failed checks in dirty.csv still refer to one bad record.

```bash
export PYTHONPATH=src
python3 -m data_quality_gates --contract examples/moba-retention/strict-contract.json --data examples/moba-retention/clean.csv --reference-time 2026-10-15T12:00:00Z
# Expected exit 0, 8 rows, 8 zero violation counts.
python3 -m data_quality_gates --contract examples/moba-retention/strict-contract.json --data examples/moba-retention/wrong-rate.csv --reference-time 2026-10-15T12:00:00Z
# Expected exit 1, only rate_matches_counts fails at CSV record 2.
python3 -m data_quality_gates --contract examples/moba-retention/strict-contract.json --data examples/moba-retention/fractional-count.csv --reference-time 2026-10-15T12:00:00Z
# Expected exit 1, only nonnegative_retained fails at CSV record 2.
```

## Exact semantics

`numeric_range` accepts optional `integer: true` or `false`. The default remains false for backwards compatibility. True rejects fractional mathematical values in addition to existing inclusive range bounds: 2, 2.0 and 2e1 are integral, 2.5 fails. At least one min/max bound is still required. A malformed integer option is a configuration error even for empty input.

`ratio_consistency` requires three distinct column names (`numerator_column`, `denominator_column`, `ratio_column`) in required_columns and explicit `absolute_tolerance`, a finite JSON number between 0 and 1 inclusive. A row passes when the denominator is positive and `abs(actual_ratio - numerator / denominator) <= absolute_tolerance`. Negative numerator/rate values can be mathematically consistent; business sign/range/count constraints belong in separate checks. Zero or negative denominators always fail.

Operands are parsed from finite decimal cells, then converted to exact Python Fraction values. Arithmetic does not use binary floats or the caller's Decimal division context. The CLI preserves the original JSON decimal token for absolute_tolerance before validation/comparison, preventing float rounding or underflow from bypassing its limits. Existing scalar numeric settings retain their historical float interpretation. API callers may pass Decimal for an exact tolerance; a Python float has already been rounded by its caller and is interpreted using its decimal string representation. The strict example uses 1e-12 absolute tolerance to permit the producer's printed repeating decimal rates. Inclusive boundaries are exact: for 1/4 and tolerance .01, .26 passes, .2600000000000001 fails. With zero tolerance, any finite printed approximation of 1/3 fails; it is not equal to the exact rational value.

Before Fraction construction, each operand/tolerance is restricted to at most 100 **stored coefficient digits** and an absolute stored decimal exponent no larger than 100. This bounds integer expansion and computation. These are encoding limits: an excessively long zero-padded representation can fail even if its numeric magnitude is small. Out-of-bound/blank/malformed/non-finite data cells become quality violations (exit 1), not unhandled arithmetic errors. An invalid tolerance or malformed contract is a configuration error (exit 2), including with no data. Existing numeric_range/column_compare checks retain their previous finite-decimal scope; the new bound applies only to ratio arithmetic.

## Verification and remaining limits

Six initial test methods first failed before implementation. Review exposed JSON tolerance rounding; a seventh method failed for four raw-token regressions, then passed after decimal token preservation. The full 28-test suite passes: [actual output](strict-test-output.txt). Independent literal cases cover tolerance boundaries, zero/negative denominators, invalid cells, numeric values above 2^53, global Decimal precision set to 2, strict zero-tolerance repeating fractions, arithmetic encoding bounds, integer/scientific notation, malformed empty-data config, raw JSON tolerance underflow/over-one/boundary cases and actual CLI reports/exit codes. The original six-check showcase exporter regenerated with identical JSON/SVG/HTML.

The contract still does not validate cohort-date syntax or establish whether source cohorts have matured. Maturity remains the producer's responsibility. It reads local CSV in memory and does not guarantee a cross-table transactional snapshot. No company data or production results are used, and the API/report/exit taxonomy remains unchanged for old contracts.
