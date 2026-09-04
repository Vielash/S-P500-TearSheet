# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A Streamlit quant tearsheet **built as a learning exercise**. The app, design
system, plots and tests shipped complete; `metrics.py` shipped with the function
bodies raising `NotImplementedError` and the repo owner filled them in one by
one. **All 28 are now written and the suite is green.**

**Do not rewrite a `metrics.py` body unless explicitly asked.** Writing them was
the whole point of the project, and a "cleaner" rewrite takes that away. Fixing a
bug the owner asks about is fine; refactoring working code is not. When the owner
is stuck, point at the failing test's expected value and the relevant section of
`docs/metrics.md` before handing over a body.

Commands run from the `tearsheet/` directory (the git root; it sits nested inside
an outer `TearSheet/` folder that is not a repo).

## Commands

```bash
pip install -r requirements.txt      # runtime only — this is what a deploy installs
pip install -r requirements-dev.txt  # adds pytest + pandas-datareader
streamlit run app.py            # the app
pytest -v                       # all tests: skip = not written yet, passed = correct
pytest -v -k sharpe             # one metric
python update_factors.py        # one-shot: download real Ken French factors (needs network)
python build_universe.py        # one-shot: refresh data/sp500.csv from Wikipedia
```

`requirements.txt` is deliberately runtime-only so a Streamlit Cloud build stays
small; anything needed just for tests or the one-shot download scripts belongs in
`requirements-dev.txt`.

`conftest.py` exists solely to put the repo root on `sys.path` so `tests/` can
`import metrics`. `update_factors.py` writes to the relative path
`data/ff5_daily.csv`, so it must be run from `tearsheet/`.

## The "not ready" contract

This is the central mechanism and it spans four files. A half-finished
`metrics.py` must never crash the app or the suite, so **`NotImplementedError` is
a first-class signal**, distinct from a real bug:

- `app.py:36` `val(fn_name, *args)` — the only way `app.py` ever calls a metric.
  Missing attribute or `NotImplementedError` → `None` (renders as "NOT READY").
  Any other exception → recorded in `ui.ERRORS` and rendered as "ERROR" on that
  card alone; the rest of the page still renders.
- `tests/test_metrics.py:24` `call(fn, ...)` — same idea, `NotImplementedError`
  becomes `pytest.skip`.
- `ui.pending_card` / `ui.pending_chart` — the styled "not ready" states.
- `app.py` collects `ui.ERRORS` into a summary slot at the top of the page (the
  block at the end of the file writes into `error_slot`).

Consequence: never let a metric raise `NotImplementedError` for a reason other
than "not written yet", and never catch it inside `metrics.py`.

## Data pipeline

Everything funnels through one shape, and this is the extension point for new
data sources:

```
CSV upload / sample / market.fetch_prices
    → data.load_returns()   long df: date, ticker, return
    → data.returns_wide()   index=date, one column per ticker
    → the rest of app.py
```

`app.py` below `wide = data.returns_wide(df)` is **source-agnostic** — it only
sees `wide`. Adding a data source means adding a branch in the "veri girisi"
block plus an entry screen; nothing downstream changes.

The three live branches are keyed off `st.session_state`: `_sample`, `_raw`
(uploaded bytes) and `_fetch` (a `(symbols, start, end)` tuple written by
`fetch_form()`). `app.py` imports `market` inside a `try` — if `yfinance` is
missing the app still opens and only the fetch form disappears, so never call
`market.*` without the `market is None` guard.

`load_returns` accepts either a `price` or a `return` column and derives returns
from price when needed (`data.py:52`), so a new source should hand it
`date, ticker, price` and let it do the conversion rather than computing returns
itself. Column-name matching is fuzzy via the `*_COLS` sets at the top of
`data.py`; `load_bytes` and `fetch_frame` both show the trick of round-tripping a
DataFrame through `io.StringIO` to reuse `load_returns` unchanged.

State between reruns lives in `st.session_state` under the keys listed in
`reset_data()` — keep that function in sync when adding a key.

## Conventions that tests and UI depend on

- **Function signatures in `metrics.py` are frozen.** Both `tests/` and `app.py`
  call them positionally by those exact names.
- **`rf` is an annual rate.** Every consumer passes e.g. `0.04` for 4%; the
  function divides by `periods_per_year` internally. See `docs/metrics.md:66`
  and the hint in the `capm_alpha` docstring. (`app.py` does not currently pass
  `rf` at all, so the live app runs at `rf=0`.)
- **Returns are decimals, not percents** (0.001 = 0.1%) everywhere, including
  `data/ff5_daily.csv` — that's why `update_factors.py` divides Ken French data
  by 100.
- Annualization is `TRADING_DAYS = 252`, defined separately in `metrics.py` and
  `factors.py`.

## Rendering layers

- `ui.py` is a self-contained design system: fixed dark palette (`BG`, `SURFACE`,
  `SERIES`, …), one large CSS blob injected once, and card/section builders.
  Use the existing tokens and helpers rather than inline styles or new colors.
- `ui.INFO` holds the per-metric copy keyed by metric name: `(short note,
  definition, formula, interpretation)`. It feeds three places at once — the card
  sub-line (`ui.note_of`), the `?` hover bubble (`ui.info_dot`) and the "Metric
  guide" tab (`ui.guide`). A new metric needs an entry there plus a display name
  in `ui.NAMES` and a slot in `ui.GUIDE`, or it shows up blank or not at all.
- `ui.STATUS` is filled by `app.py`'s `val()` on every run
  (`ready` / `pending` / `error`) and is what the guide tab badges each metric
  with. A metric `app.py` never called this run carries no badge.
- `plots.py` returns Plotly figures already themed to match `ui.py` via
  `_layout()`. New charts should go through it.
- `app.py` is a single linear script in five numbered `ui.section` blocks plus a
  "Compare" tab and a "Metric guide" tab. It computes nothing itself — every
  number comes from `val()`. The guide tab renders last on purpose: by then every
  `val()` call has run, so `ui.STATUS` is complete.

## Data files are synthetic

`data/sample_returns.csv` and `data/ff5_daily.csv` are both **synthetic
placeholders**, not real market data (the app badges this at `app.py:355`).
Never present numbers derived from them as real market facts. Real factors come
from `python update_factors.py`.

## Style

Code comments and `docs/` prose are Turkish (ASCII-only, no diacritics in `.py`
files); user-facing UI strings are English. Match this when adding code.
