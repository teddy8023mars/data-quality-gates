# Contract decoder error taxonomy regression

Acceptance: a deeply nested JSON contract or a JSON integer exceeding Python's configured decoder digit limit must produce config_error JSON, exit2 and an identical --report file, rather than an uncaught traceback/exit1. Existing explicit ConfigError messages, decimal tolerance semantics, data-quality exit1, input/report I/O exit3 and synthetic visual output remain unchanged. No new check type, dependency or scale claim.

- Establish clean28-test baseline.
- Add two actual-subprocess regression tests with independent expected status/exit/report, observe RED.
- Normalize ValueError/RecursionError only at contract decoding; preserve explicit ConfigError without rewrapping. Run full suite.
- Regenerate original showcase and verify no diff; document actual decoder failures and corrected CLI output.
- Independent review, personal commit/push, check exact-commit CI and Pages before completion.

This is bounded maintenance of the existing declared CLI error contract, not a new parser, configurable depth/memory budget, streaming guarantee or proof of protection against resource exhaustion. Work is authorized by the ongoing personal-project sprint.
