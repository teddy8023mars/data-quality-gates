# Base retention gate and stricter arithmetic

The original seven-check example below preserves its earlier behavior. [The strict variant](strict-retention.md) adds integral-count and count/rate consistency checks, closing the arithmetic gaps described below.

This example consumes an immutable snapshot of the MOBA lab's exported D1/D7 cohorts. [Source and checksum](../examples/moba-retention/PROVENANCE.md) establish where the eight synthetic rows came from. No company data or production infrastructure is involved.

Run from the repository root:

```bash
export PYTHONPATH=src
python3 -m data_quality_gates --contract examples/moba-retention/contract.json --data examples/moba-retention/clean.csv --reference-time 2026-10-15T12:00:00Z
# Exit 0: 8 records, 7 checks, zero violations.
python3 -m data_quality_gates --contract examples/moba-retention/contract.json --data examples/moba-retention/dirty.csv --reference-time 2026-10-15T12:00:00Z
# Exit 1 (intentional): retained_within_cohort fails at CSV record 2.
```

The contract checks required cells, unique `(cohort_date, day_offset)` grain, supported offsets, positive cohort size, nonnegative retained users, rate bounds and `retained_users <= cohort_users`. The deliberate dirty row has retained_users=4 and cohort_users=3; every other check passes. Recorded [clean](retention-clean-output.json) and [dirty](retention-dirty-output.json) reports come from the commands above. A shell/CI caller can stop downstream publication on exit 1; this lab does not implement an orchestrator.

The engine's seventh check type, `column_compare`, supports `<=`, `>=` and `==` using finite decimal parsing. Two distinct required column names must be configured. Missing, malformed or non-finite cells become quality failures; unsupported operators and unknown settings become configuration errors, including with empty data. Comparisons are numeric: `10 == 1e1` passes. Arbitrary expressions are unsupported.

Limits: the contract does not check integral counts, date syntax, exact retention-rate arithmetic, or whether source cohorts have matured. The MOBA producer owns the maturity calculation; these fixtures contain only observable cohorts. Rates are merely bounded here, so the deliberately inconsistent dirty row also demonstrates a remaining arithmetic validation gap. CSV files are loaded in memory; this is local deterministic gating, not deployed monitoring.

Verification: the comparison tests first failed because the feature was unsupported (unknown check type / CLI exit 2). Tests then cover hand-calculated boundary comparisons, invalid numeric cells on either side, malformed configuration on empty input, and both complete CLI fixtures with literal exit codes and violation counts. The original six-check showcase must regenerate unchanged.
