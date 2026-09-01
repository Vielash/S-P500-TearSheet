"""Streamlit tearsheet uygulamasi. Calistir: streamlit run app.py

Akis: CSV yukle -> ticker / benchmark / pencere sec -> kartlar + grafikler.
metrics.py'daki fonksiyonlar yazildikca kartlar canlanir; yazilmamis olan "—" gosterir.
"""

from pathlib import Path

import pandas as pd
import streamlit as st

import data
import factors
import metrics as m
import plots

BASE = Path(__file__).parent
WINDOWS = {63: "63d — 1 quarter", 126: "126d — 2 quarters",
           189: "189d — 3 quarters", 252: "252d — 4 quarters"}

st.set_page_config(page_title="Quant Tearsheet", layout="wide")


# --- kucuk yardimcilar ---

def safe(fn, *args, **kwargs):
    # metrik daha yazilmadiysa None doner; kartta "—" gorunur
    try:
        return fn(*args, **kwargs)
    except NotImplementedError:
        return None


def pct(x, nd=2):
    return "—" if x is None else f"{x:.{nd}%}"


def num(x, nd=2):
    return "—" if x is None else f"{x:.{nd}f}"


def card(col, label, value, note):
    col.metric(label, value)
    col.caption(note)


def hint(fn_name):
    st.info(f"`{fn_name}` yazilinca bu grafik gelecek")


def fmt_reg(table):
    out = table.copy()
    out["coef"] = out["coef"].map(lambda v: f"{v:+.4f}")
    out["annualized"] = out["annualized"].map(lambda v: "—" if pd.isna(v) else f"{v:.2%}")
    out["t_stat"] = out["t_stat"].map(lambda v: f"{v:.2f}")
    out["p_value"] = out["p_value"].map(lambda v: f"{v:.3f}" + (" *" if v < 0.05 else ""))
    return out.set_index("factor")


@st.cache_data
def load_sample():
    return data.load_returns(BASE / "data" / "sample_returns.csv")


@st.cache_data
def load_factor_file():
    return factors.load_factors(BASE / "data" / "ff5_daily.csv")


# --- veri girisi (sidebar) ---

st.sidebar.title("Quant Tearsheet")
uploaded = st.sidebar.file_uploader("Returns CSV", type="csv")
if st.sidebar.button("Load sample data"):
    st.session_state["use_sample"] = True

if uploaded is not None:
    df = data.load_returns(uploaded)
elif st.session_state.get("use_sample"):
    df = load_sample()
    st.sidebar.caption("Ornek veri sentetiktir, gercek piyasa verisi degildir.")
else:
    # acilis ekrani (videodaki gibi)
    st.title("Turn a returns CSV into a full quant tearsheet")
    st.write("Upload daily returns and instantly get CAPM alpha & beta, Fama-French "
             "factor loadings, rolling attribution, and a performance & risk breakdown.")
    st.subheader("Expected CSV format")
    st.code("date,ticker,price,return\n"
            "2023-01-03,SPY,378.1841,-0.00478\n"
            "2023-01-03,AAPL,124.8412,-0.00127\n"
            "2023-01-04,SPY,381.2989,0.00824", language="text")
    st.caption("Kolon adlari esnek (buyuk/kucuk harf farketmez): price/close/adj_close ve "
               "return/ret kabul edilir. return kolonu yoksa fiyattan hesaplanir. "
               "Ayni dosyaya benchmark'i da (orn. SPY) ayri bir ticker olarak koy.")
    st.stop()

wide = data.returns_wide(df)
tickers = list(wide.columns)

ticker = st.sidebar.selectbox("Ticker", tickers)
bench_options = [t for t in tickers if t != ticker]
bench_default = bench_options.index("SPY") if "SPY" in bench_options else 0
bench = st.sidebar.selectbox("Benchmark", bench_options, index=bench_default) if bench_options else None
window = st.sidebar.selectbox("Rolling window", list(WINDOWS), format_func=WINDOWS.get)

r = wide[ticker].dropna()
if bench:
    r_al, b_al = data.align_pair(wide, ticker, bench)
else:
    r_al = b_al = None
    st.sidebar.warning("Benchmark metrikleri icin dosyada ikinci bir ticker olmali (orn. SPY).")

try:
    ff = load_factor_file()
except FileNotFoundError:
    ff = None

tab_main, tab_compare = st.tabs(["Tearsheet", "Compare"])


# --- ana tearsheet ---

with tab_main:
    st.subheader(f"Portfolio Tearsheet — {ticker}")
    st.caption(f"{len(r)} daily observations · "
               f"{r.index.min():%Y-%m-%d} → {r.index.max():%Y-%m-%d}"
               + (f" · benchmark: {bench}" if bench else ""))

    # metrik kartlari (videodaki 8'li duzen)
    alpha_v = safe(m.capm_alpha, r_al, b_al) if bench else None
    beta_v = safe(m.beta, r_al, b_al) if bench else None
    r2_v = safe(m.r_squared, r_al, b_al) if bench else None

    row1 = st.columns(4)
    card(row1[0], "ANNUALIZED ALPHA", pct(alpha_v), f"CAPM intercept vs {bench}")
    card(row1[1], "BETA", num(beta_v, 3), f"Market exposure vs {bench}")
    card(row1[2], "SHARPE", num(safe(m.sharpe, r)), "Risk-adjusted return")
    card(row1[3], "SORTINO", num(safe(m.sortino, r)), "Downside risk-adjusted")

    row2 = st.columns(4)
    card(row2[0], "CAGR", pct(safe(m.cagr, r)), "Annualized growth")
    card(row2[1], "VOLATILITY", pct(safe(m.annual_volatility, r)), "Annualized std dev")
    card(row2[2], "MAX DRAWDOWN", pct(safe(m.max_drawdown, r)), "Worst peak-to-trough")
    card(row2[3], "R² (CAPM)", num(r2_v, 3), "Variance explained by market")

    # equity curve
    g = safe(m.growth_of_1, r_al if bench else r)
    if g is None:
        hint("growth_of_1")
    else:
        curves = {ticker: g}
        bg = safe(m.growth_of_1, b_al) if bench else None
        if bg is not None:
            curves[bench] = bg
        st.plotly_chart(plots.line_chart(curves, "Equity Curve — Growth of $1",
                                         dashed=(bench,), hover_fmt=".2f"),
                        use_container_width=True)

    # drawdown + rolling sharpe
    left, right = st.columns(2)
    with left:
        dd = safe(m.drawdown_series, r)
        if dd is None:
            hint("drawdown_series")
        else:
            st.plotly_chart(plots.underwater_chart(dd), use_container_width=True)
    with right:
        rs = safe(m.rolling_sharpe, r, window)
        if rs is None:
            hint("rolling_sharpe")
        else:
            st.plotly_chart(plots.line_chart({"Sharpe": rs},
                                             f"Rolling Sharpe Ratio ({window}-day window)",
                                             refline=1.0), use_container_width=True)

    # rolling beta + rolling volatilite
    left, right = st.columns(2)
    with left:
        rb = safe(m.rolling_beta, r_al, b_al, window) if bench else None
        if rb is not None:
            st.plotly_chart(plots.line_chart({"Beta": rb}, f"Rolling Beta vs {bench} ({window}d)",
                                             refline=1.0), use_container_width=True)
        elif bench:
            hint("rolling_beta")
        else:
            st.info("Benchmark yok")
    with right:
        rv = safe(m.rolling_volatility, r, window)
        if rv is None:
            hint("rolling_volatility")
        else:
            st.plotly_chart(plots.line_chart({"Volatility": rv},
                                             f"Rolling Volatility ({window}d, annualized)",
                                             pct=True), use_container_width=True)

    # aylik getiri isi haritasi
    mt = safe(m.monthly_return_table, r)
    if mt is None:
        hint("monthly_return_table")
    else:
        st.plotly_chart(plots.monthly_heatmap(mt), use_container_width=True)

    # fama-french bolumu (bu kisim hazir gelir: factors.py)
    if ff is not None:
        st.divider()
        note = " — sentetik ornek, gercegi icin: python update_factors.py" if ff.index.min().year >= 2023 else ""
        st.caption(f"Factor data source: data/ff5_daily.csv{note}")

        betas = factors.rolling_ff_betas(r, ff, window)
        if not betas.empty:
            st.plotly_chart(plots.line_chart(
                {c.upper().replace("_RF", "-RF"): betas[c] for c in betas.columns},
                f"Rolling Fama-French Factor Betas ({window}-day window)"),
                use_container_width=True)

        ff5_table, ff5_r2 = factors.ff_regression(r, ff, "ff5")
        ff3_table, ff3_r2 = factors.ff_regression(r, ff, "ff3")

        left, right = st.columns(2)
        with left:
            loadings = ff5_table.set_index("factor")["coef"].drop("Alpha")
            st.plotly_chart(plots.loadings_bar(loadings), use_container_width=True)
        with right:
            st.markdown(f"**Fama-French 5-Factor Regression**  ·  R² = {ff5_r2:.3f}")
            st.dataframe(fmt_reg(ff5_table), use_container_width=True)
            st.caption("* significant at the 5% level (p < 0.05)")

        left, right = st.columns(2)
        with left:
            st.markdown(f"**Fama-French 3-Factor**  ·  R² = {ff3_r2:.3f}")
            st.dataframe(fmt_reg(ff3_table), use_container_width=True)
        with right:
            if bench:
                capm_table, capm_r2 = factors.capm_regression(r_al, b_al)
                st.markdown(f"**CAPM (vs {bench})**  ·  R² = {capm_r2:.3f}")
                st.dataframe(fmt_reg(capm_table), use_container_width=True)

    # diger metrikler (hepsi metrics.py'dan geliyor)
    st.divider()
    st.markdown("**More metrics**")
    rows = [
        ("Total Return", pct(safe(m.total_return, r))),
        ("Calmar", num(safe(m.calmar, r))),
        ("Win Rate", pct(safe(m.win_rate, r), 1)),
        ("Best Day", pct(safe(m.best_day, r))),
        ("Worst Day", pct(safe(m.worst_day, r))),
        ("Skewness", num(safe(m.skewness, r))),
        ("Kurtosis (excess)", num(safe(m.kurtosis, r))),
        ("VaR 95% (daily)", pct(safe(m.var_historic, r))),
        ("CVaR 95% (daily)", pct(safe(m.cvar_historic, r))),
    ]
    if bench:
        rows += [
            (f"Correlation vs {bench}", num(safe(m.correlation, r_al, b_al))),
            ("Tracking Error", pct(safe(m.tracking_error, r_al, b_al))),
            ("Information Ratio", num(safe(m.information_ratio, r_al, b_al))),
            ("Up Capture", pct(safe(m.up_capture, r_al, b_al), 0)),
            ("Down Capture", pct(safe(m.down_capture, r_al, b_al), 0)),
        ]
    st.dataframe(pd.DataFrame(rows, columns=["Metric", "Value"]).set_index("Metric"),
                 use_container_width=True, height=(len(rows) + 1) * 35 + 3)


# --- iki hisse karsilastirma ---

with tab_compare:
    if len(tickers) < 2:
        st.info("Karsilastirma icin dosyada en az iki ticker olmali.")
        st.stop()

    c1, c2 = st.columns(2)
    a_name = c1.selectbox("First", tickers, index=0)
    options_b = [t for t in tickers if t != a_name]
    b_name = c2.selectbox("Second", options_b,
                          index=options_b.index("SPY") if "SPY" in options_b else 0)
    a, b = data.align_pair(wide, a_name, b_name)

    specs = [
        ("Total Return", lambda s: pct(safe(m.total_return, s))),
        ("CAGR", lambda s: pct(safe(m.cagr, s))),
        ("Volatility", lambda s: pct(safe(m.annual_volatility, s))),
        ("Sharpe", lambda s: num(safe(m.sharpe, s))),
        ("Sortino", lambda s: num(safe(m.sortino, s))),
        ("Max Drawdown", lambda s: pct(safe(m.max_drawdown, s))),
        ("Calmar", lambda s: num(safe(m.calmar, s))),
        ("Win Rate", lambda s: pct(safe(m.win_rate, s), 1)),
        ("VaR 95% (daily)", lambda s: pct(safe(m.var_historic, s))),
    ]
    table = pd.DataFrame({a_name: [f(a) for _, f in specs],
                          b_name: [f(b) for _, f in specs]},
                         index=[name for name, _ in specs])
    st.dataframe(table, use_container_width=True, height=(len(specs) + 1) * 35 + 3)
    st.caption(f"Beta ({a_name} vs {b_name}): {num(safe(m.beta, a, b), 3)} · "
               f"Correlation: {num(safe(m.correlation, a, b), 3)}")

    ga, gb = safe(m.growth_of_1, a), safe(m.growth_of_1, b)
    if ga is None or gb is None:
        hint("growth_of_1")
    else:
        st.plotly_chart(plots.line_chart({a_name: ga, b_name: gb},
                                         "Growth of $1", hover_fmt=".2f"),
                        use_container_width=True)

    left, right = st.columns(2)
    with left:
        da, db = safe(m.drawdown_series, a), safe(m.drawdown_series, b)
        if da is None or db is None:
            hint("drawdown_series")
        else:
            st.plotly_chart(plots.line_chart({a_name: da, b_name: db}, "Drawdown from Peak",
                                             pct=True), use_container_width=True)
    with right:
        # kayan korelasyon pandas'ta tek satir, metrics'e koymaya degmedi
        rc = a.rolling(window).corr(b).dropna()
        st.plotly_chart(plots.line_chart({"Correlation": rc},
                                         f"Rolling Correlation ({window}d)", refline=0.0),
                        use_container_width=True)

    # risk-getiri haritasi: dosyadaki TUM ticker'lar
    points = []
    for t in tickers:
        s = wide[t].dropna()
        ret, vol = safe(m.cagr, s), safe(m.annual_volatility, s)
        if ret is not None and vol is not None:
            points.append({"ticker": t, "ret": ret, "vol": vol})
    if points:
        st.plotly_chart(plots.risk_return_scatter(pd.DataFrame(points)),
                        use_container_width=True)
    else:
        hint("cagr + annual_volatility")
