# Local verification — 2026-10-15

Environment: macOS, bundled Python **3.12.14**. Working directory is the repository root. No cloud or employer data used. These are actual local results; Python 3.11 and remote CI have not yet been run.

## Test-first evidence

The initial RED run recorded missing evaluator behavior in [red-test-output.txt](red-test-output.txt): 12 tests, 1 failure and 31 subtest/test errors. An initial import failure was corrected by adding only exception/interface stubs, then missing implementation and CLI behavior were observed. A CLI fixture helper was corrected to write malformed data without calling the evaluator first. The NUL reference-path regression failed before its validation fix: [adversarial-red-output.txt](adversarial-red-output.txt), 15 tests with 1 error (`ValueError: embedded null byte`).

## Full suite

Actual command:

```bash
PYTHONPATH=src /Users/teddy/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m unittest discover -s tests -v
```

Actual output summary (exit 0):

```text
Ran 15 tests in 0.186s
OK
```

Full output: [test-output.txt](test-output.txt). Expectations are literal, hand-checked violation counts/record numbers and exit codes. Covers six checks, timezone conversion and invalid offsets, inclusive bounds, composite duplicate/null keys, header-only policy and zero-byte input, missing required schema, malformed CSV/UTF-8, missing FK references/schema, invalid settings/types, NaN/Inf, duplicate JSON keys and CLI report-file equality/error taxonomy.

## Synthetic CLI demos

Actual command (exit **0**):

```bash
PYTHONPATH=src /Users/teddy/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m data_quality_gates --contract examples/contract.json --data examples/clean.csv --reference-time 2026-10-15T12:00:00Z --report docs/clean-report.json
```

Actual JSON: [clean-report.json](clean-report.json). Status `passed`, rows `2`, reference time `2026-10-15T12:00:00+00:00`, empty violation `false`, no missing columns; all six violation counts `0`.

Actual command (exit **1**, intentional quality failure):

```bash
PYTHONPATH=src /Users/teddy/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m data_quality_gates --contract examples/contract.json --data examples/dirty.csv --reference-time 2026-10-15T12:00:00Z --report docs/dirty-report.json
```

Actual JSON: [dirty-report.json](dirty-report.json). Status `failed`, rows `3`, no missing columns; violation counts `[1, 1, 3, 2, 2, 3]`. Per-check bad record numbers: not-null `[4]`, unique `[3]`, numeric `[2,3,4]`, allowed values `[2,4]`, FK `[2,4]`, freshness `[2,3,4]`.

## Editable package and command

Actual commands, each exited 0:

```bash
/Users/teddy/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/data-quality-gates --contract examples/contract.json --data examples/clean.csv --reference-time 2026-10-15T12:00:00Z
```

Install output ended `Successfully installed data-quality-gates-0.1.0`. Installed command emitted the same clean pass report (2 rows, all checks zero). Build-time setuptools is downloaded by pip when needed; the evaluator uses only the Python standard library at runtime. The virtual environment and packaging metadata are ignored.

## Review and remaining verification

Coordinator independent review reran all 15 tests and both clean/dirty fixtures, verified exits 0/1 and counts, and found no first-slice blocker. No repository was initialized, no commit was created and nothing was published by this implementer. Git-based skill bookkeeping was omitted because coordinator explicitly owns those actions; the project implementation plan records this ruling. Local self-review checked malformed settings, empty references and timestamp precision; coordinator completed the fresh review before publication.

Limits: data/reference sets and all bad-row identifiers held in memory; no benchmark, streaming or connectors; input files not transactionally snapshotted; reports not atomically replaced; microsecond timestamp precision; no named timezones or leap seconds. See README for exact input/check semantics. Python 3.11 compatibility and Ubuntu behavior are declared CI targets, not local results. Remote CI pending publication.

## Retention contract extension — 2026-10-15

The earlier sections describe initial pre-publication validation. The additive column comparison feature and committed cross-project examples now pass 21 tests on bundled Python 3.12.14: [full output](retention-test-output.txt). Recorded CLI runs: clean exit 0, 8 rows, seven zero counts; dirty exit 1, 8 rows, counts [0,0,0,0,0,0,1], only CSV record 2 fails retained_within_cohort. The original showcase exporter was rerun and its JSON, SVG and HTML remained byte-identical to the prior commit. Remote results for this extension are available in the repository Actions tab after publication; they are recorded in the sprint status separately.

## Strict retention arithmetic — 2026-10-15

Six meaningful new tests first failed due to unsupported check/options and absent strict fixtures. Full28-test suite now passes in strict-test-output.txt. Actual strict CLI runs: clean0/eight zero counts; wrong-rate1/[0,0,0,0,0,0,0,1]; fractional-count1/[0,0,0,0,1,0,0,0]; impossible-count dirty1/[0,0,0,0,0,0,1,1]. All failures at CSV record2; reports captured from real output. Exact bounded rational checks avoid global Decimal precision/float-rounding false passes, with explicit per-operand stored encoding bounds. Original7-check fixture and6-check visual remain unchanged after exporter regeneration. Remote CI must be checked separately for the published commit.

Review found JSON float rounding could accept invalid tolerance tokens or widen an exact boundary. Four direct-CLI raw-token subcases first failed, then passed after preserving Decimal tolerance tokens; other scalar numeric settings retain old float semantics. Invalid decimal construction becomes ConfigError. Full28 tests rerun successfully, all strict fixture outputs unchanged, original showcase rechecked unchanged. Independent fix review found no remaining blockers.
