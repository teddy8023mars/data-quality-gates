# Data Quality Gates showcase

## Design and acceptance

The recruiter-facing page at `docs/index.html` makes a pipeline decision visible before showing the underlying evidence. It uses dark navy `#0b1220`, teal `#68e0c2`, amber `#ffb85c` and red `#ff6b7a`, system fonts, inline CSS and plain JavaScript. No CDN, font, analytics or runtime dependency is required. JSON loads from the same origin.

- Header links expose the original contract and source README.
- A prominent synthetic label and fixed reference time describe the scope honestly. The browser explores a recorded run; it does not execute the Python engine.
- Dirty/clean buttons switch gate status, exit code, metrics, all six chart counts and selected-check evidence together. Initial selection is the dirty score-bounds check.
- Dirty: report `failed`, gate blocked, exit 1; counts `[1, 1, 3, 2, 2, 3]`; 12 overlapping violations, 3 distinct bad records from the union `[2, 3, 4]`.
- Clean: report `passed`, gate passed, exit 0; 2 data records, six zeros, no offending records.
- Each chart button shows exact engine record identifiers and their original parsed CSV values. Blank values are labeled `[empty]`, a whitespace-only ID `[1 space]`. The exported JSON preserves the raw values.
- CSV record numbers include the header and count quoted multiline values as one record. No line-number claim is made.
- Error semantics distinguish parseable invalid cells (quality exit 1) from configuration errors (2) and input errors (3).
- Native buttons support Tab, Enter and Space. Pressed state, visible focus outlines, descriptive check labels, table header scopes and live gate summaries communicate state. Reduced-motion preferences disable animated bars.
- Desktop places chart and evidence beside one another; mobile stacks them, makes metrics two columns, wraps pipeline stages and horizontally scrolls long record values inside the table.
- `docs/assets/showcase.svg` is a matching 1440×820 preview showing actual dirty-run counts and score-bounds samples, with an accessible SVG title/description.

## Verification performed

Working directory: isolated `data-quality-gates` visual worktree. Engine implementation was unchanged.

```bash
PYTHONPATH=src /Users/teddy/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/build_showcase.py
# Exit 0; wrote docs/showcase-data.json.
PYTHONPATH=src /Users/teddy/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m unittest discover -s tests -v
# Exit 0; 17 tests passed, including two showcase export tests.
```

The exporter calls the public `evaluate(contract, data_path, reference_time, base_dir)` function on each fixture, then joins report record numbers to parsed source rows. Literal test expectations verify every check count, all offending record lists, selected raw values, exact sample selection, union of record numbers, distinct count, clean/dirty exit status and equality between rebuilt and checked-in evidence.

The SVG was parsed successfully as XML. HTML was checked for one complete inline script and the expected same-origin JSON fetch. The inline JavaScript passed `vm.Script` syntax compilation with the bundled Node runtime. Browser layout, keyboard interaction, console and network checks are pending coordinator verification before publication. Live-demo link in README is the intended Pages URL; publication is coordinated separately.

Coordinator browser QA: real controls exercised against served docs/. MOBA observation cutoffs and N/A cells, incremental rollback/retry/replay snapshots, and quality clean/dirty/check selection were inspected in the browser as applicable. Screenshots inspected for visual defects. Exporter and entire suite rerun by coordinator before publication. No claim of mobile-browser or all-platform validation.
