# Quality gates implementation plan

Scope: synthetic personal portfolio project, standard library, Python 3.11+.

Interface: `python -m data_quality_gates --contract PATH --data PATH --reference-time ISO8601 [--report PATH]`. Reference time always requires timezone. stdout JSON; optional identical report file. Exit 0 passed; 1 quality violation; 2 invalid config; 3 invalid input or report I/O; CLI usage errors 2.

API: `evaluate(contract: dict, data_path: Path, reference_time: str, base_dir: Path) -> dict`; exceptions `ConfigError`, `InputError`. `main(argv=None) -> int`.

Contract version 1: exact top-level keys `version`, `required_columns`, `empty_policy`, `checks`; schema lists nonempty distinct column names; empty policy `fail` or `allow`. Checks have unique `id` and `type`: `not_null`/`unique` use `columns`; `numeric_range` uses `column` and optional finite `min`/`max` (at least one); `allowed_values` uses `column`, `values` (nonempty strings); `foreign_key` uses `column`, `reference_file`, `reference_column`; `freshness` uses `column`, `max_age_seconds` (finite nonnegative). Reject extra or missing keys, booleans where numbers required, unknown columns/types, malformed JSON, duplicate JSON keys. CSV headers must contain schema with no duplicate/blank headers; extras allowed. Row width must match. UTF-8, comma-separated CSV only. FK references resolved relative to contract.

Semantics: null is empty/whitespace-only string; strings otherwise compared exactly. Unique violations count only subsequent duplicate rows (including null keys). Range uses finite Decimal values, inclusive limits, null fails. Allowed values and FK exact strings, null fails. Freshness accepts timezone-aware ISO datetimes, 0 <= age <= limit; null/naive/invalid/future timestamps fail as quality data. Invalid reference time is input error. Bad CSV shape is input error. Header-only CSV explicit policy; zero-byte CSV invalid input. Required-schema quality failure short-circuits checks. All references preloaded even for empty data. Deterministic row numbers are physical CSV record numbers including header, not text line numbers for quoted multiline fields.

1. Write independent tests covering clean/dirty checks and CLI exit/report semantics, malformed input/config and timezone edge cases. Run RED.
2. Implement config/CSV validation and check evaluator. Run GREEN full suite.
3. Add synthetic demos, README, MIT, packaging and CI. Run exact documented demo commands, record actual outputs.

Ruling: do not use git-based skill bookkeeping/commits because coordinator explicitly owns repository creation and publication; record progress in this project plan and verification report. No shared interfaces with sibling labs.

Progress 2026-10-15: all three implementation steps complete locally. 15 tests pass, clean CLI exit 0, dirty CLI exit 1 with exact expected violations, editable install/console command work on Python 3.12.14. Actual evidence in verification.md and JSON reports. Coordinator independent review completed: all 15 tests and demos rerun; no first-slice blocker. No git operations performed.
