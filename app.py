"""Streamlit tearsheet uygulamasi. Calistir: streamlit run app.py

Arayuz, Claude Design "Quant Tearsheet Redesign" kanvasinin implementasyonudur:
tek uzun scroll yerine bes numarali bolum, her metrigin yaninda tanim, ve
hesaplanmamis metrikler icin birinci sinif bir "hazir degil" durumu.

Akis: CSV yukle -> ticker / benchmark / pencere sec -> bolumlenmis kartlar + grafikler.
metrics.py'daki fonksiyonlar yazildikca kartlar kendiliginden canlanir; yazilmamis
olan "NOT READY" gosterir. Bu dosya hicbir metrigi kendisi hesaplamaz.
"""

import io
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

import data
import factors
import metrics as m
import plots
import ui

try:  # yfinance kurulu degilse uygulama yine acilsin, sadece canli cekme kapansin
    import market
except Exception:
    market = None

BASE = Path(__file__).parent
WINDOWS = {63: "3 months", 126: "6 months", 189: "9 months", 252: "12 months"}

# Benchmark tercih sirasi. ^SP500TR toplam getiri endeksi: temettuyu icerir.
# Hisse fiyatlari da duzeltilmis kapanis (temettu dahil) oldugu icin dogru esleme bu;
# SPY ayni isi yatirim yapilabilir bir arac olarak yapar, o yuzden ikinci sirada.
BENCH_PREFERRED = ("^SP500TR", "SPY")

# Salt fiyat endeksleri: temettu icermezler. Temettu duzeltmeli bir seriyle
# kiyaslaninca fark alpha'ya yaziliyor ve alpha yillik temettu verimi kadar sisiyor.
PRICE_ONLY = {"^GSPC", "^DJI", "^IXIC", "^NDX", "^RUT",
              "^FTSE", "^N225", "^STOXX50E", "XU100.IS"}


def bench_index(options):
    """Varsayilan benchmark: tercih sirasindaki ilk mevcut sembol, yoksa ilk eleman."""
    for sym in BENCH_PREFERRED:
        if sym in options:
            return options.index(sym)
    return 0

st.set_page_config(page_title="Quant Tearsheet", page_icon="📈", layout="wide")
ui.inject_css()


# --- metrik cagrisi ----------------------------------------------------------

ui.ERRORS.clear()
ui.STATUS.clear()


def val(fn_name, *args, **kwargs):
    """metrics.py'daki fonksiyonu cagirir; degeri yoksa None doner.

    Iki ayri "deger yok" durumu var ve arayuz bunlari ayri gosterir:
      - fonksiyon henuz yazilmadi  -> "NOT READY" (bekleyen adim, hata degil)
      - fonksiyon yazildi ama patladi -> "ERROR" + mesaj (ui.ERRORS'a dusuyor)
    Hangisi olursa olsun yalnizca o kart etkilenir; tearsheet'in kalani calisir.
    Her cagri sonucunu ui.STATUS'a yaziyor; "Metric guide" sekmesindeki rozetler
    oradan okunuyor.
    """
    fn = getattr(m, fn_name, None)
    if fn is None:
        return None
    try:
        out = fn(*args, **kwargs)
    except NotImplementedError:
        ui.STATUS[fn_name] = "pending"
        return None
    except Exception as exc:  # yarim kalmis bir metrik butun sayfayi dusurmesin
        ui.STATUS[fn_name] = "error"
        ui.ERRORS[fn_name] = f"{type(exc).__name__}: {exc}"
        return None
    ui.STATUS[fn_name] = "ready"
    return out


# --- veri yukleme ------------------------------------------------------------

@st.cache_data(show_spinner=False)
def load_sample():
    return data.load_returns(BASE / "data" / "sample_returns.csv")


@st.cache_data(show_spinner=False)
def load_factor_file():
    return factors.load_factors(BASE / "data" / "ff5_daily.csv")


@st.cache_data(show_spinner=False)
def load_bytes(raw, mapping=None):
    """Yuklenen CSV. mapping verilmisse kolonlar once elle eslenir."""
    if not mapping:
        return data.load_returns(io.BytesIO(raw))
    date_c, ticker_c, value_c, kind = mapping
    df = pd.read_csv(io.BytesIO(raw))
    df = df.rename(columns={date_c: "date", ticker_c: "ticker", value_c: kind})
    return data.load_returns(io.StringIO(df.to_csv(index=False)))


# Cekme ekraninin sabitleri. Benchmarklar listenin basinda duruyor ki
# sp500.csv'deki 500 sembolun arasinda aranmak zorunda kalinmasin.
FETCH_EXTRA = ["^SP500TR", "SPY", "^GSPC", "QQQ", "IWM"]
FETCH_DEFAULT = ["SPY", "AAPL", "MSFT", "NVDA"]


@st.cache_data(show_spinner=False)
def universe_symbols():
    """Secilebilir semboller. sp500.csv okunamazsa sadece benchmarklar kalir."""
    try:
        uni = market.load_universe(BASE / market.UNIVERSE_PATH)
        syms = [s.strip().upper() for s in uni["symbol"].astype(str)]
    except Exception:
        syms = []
    return FETCH_EXTRA + [s for s in syms if s not in FETCH_EXTRA]


@st.cache_data(show_spinner=False, ttl=3600)
def fetch_frame(symbols, start, end):
    """market.fetch_prices ciktisini load_returns'un anladigi long df'e cevirir.

    fetch_prices bir DataFrame donduruyor, load_returns ise dosya/tampon bekliyor;
    load_bytes'daki StringIO turu burada da isi goruyor. Kolon adlarini load_returns
    zaten esnek esliyor, o yuzden "Date" de "date" de kabul.
    """
    if market is None:
        raise ValueError("yfinance is not installed, so live prices are unavailable.")
    px = market.fetch_prices(list(symbols), start, end)
    if px is None or len(px) == 0:
        raise ValueError("Yahoo returned no rows for these symbols and dates.")
    return data.load_returns(io.StringIO(px.to_csv(index=False)))


@st.cache_data(show_spinner=False)
def peek_columns(raw):
    return list(pd.read_csv(io.BytesIO(raw), nrows=5).columns)


def diagnose(columns):
    """Hangi kolon rolu bulundu, hangisi eksik — hata panelinin verisi."""
    lower = {c: c.strip().lower() for c in columns}
    found = {
        "date": next((c for c, l in lower.items() if l in data.DATE_COLS), None),
        "ticker": next((c for c, l in lower.items() if l in data.TICKER_COLS), None),
        "price": next((c for c, l in lower.items() if l in data.PRICE_COLS), None),
        "return": next((c for c, l in lower.items() if l in data.RETURN_COLS), None),
    }
    return found


def reset_data():
    for k in ("_raw", "_name", "_sample", "_mapping", "_fetch"):
        st.session_state.pop(k, None)


# --- sidebar -----------------------------------------------------------------

def sidebar_brand():
    ui.html('<div style="display:flex;flex-direction:column;gap:4px;margin-bottom:18px">'
            '<div style="font:600 15px/1.2 \'IBM Plex Sans\';color:#f2f4f8">Quant Tearsheet</div>'
            '<div style="font:400 11px/1.4 \'IBM Plex Mono\';color:#8b93a3">'
            'performance · risk report</div></div>')


def sidebar_idle():
    """Veri gelmeden once: sidebar pasif ve bunu soyluyor."""
    with st.sidebar:
        sidebar_brand()
        ui.html('<span class="qt-sub">DATA</span>'
                '<div style="border:1px dashed #454c5a;border-radius:5px;padding:14px;'
                'display:flex;flex-direction:column;gap:6px">'
                '<div style="font:400 12px/1.4 \'IBM Plex Sans\';color:#c8ccd6">'
                'No data yet</div>'
                '<div style="font:400 11px/1.4 \'IBM Plex Sans\';color:#8b93a3">'
                'Upload from the panel on the right</div></div>')
        ui.html('<div style="opacity:.4;margin-top:22px"><span class="qt-sub">SETTINGS</span>'
                + "".join(
                    f'<div style="font:400 11px/1 \'IBM Plex Sans\';color:#8b93a3;'
                    f'margin:10px 0 6px">{lbl}</div>'
                    f'<div style="height:34px;border:1px solid #333945;border-radius:4px;'
                    f'background:#242932"></div>'
                    for lbl in ("Ticker", "Benchmark", "Rolling window"))
                + '<div style="font:400 10px/1.4 \'IBM Plex Mono\';color:#8b93a3;'
                  'margin-top:8px">Enabled once data is loaded</div></div>')


# --- 1a landing --------------------------------------------------------------

CSV_SAMPLE = [
    ("2023-01-03", "SPY", "380.82", "−0.0040"),
    ("2023-01-03", "AAPL", "125.07", "−0.0374"),
    ("2023-01-04", "SPY", "383.76", "0.0077"),
]


def format_card():
    head = ('<div class="qt-tr head" style="grid-template-columns:repeat(4,1fr)">'
            '<div>date</div><div>ticker</div><div class="r">price</div>'
            '<div class="r">return</div></div>')
    body = "".join(
        '<div class="qt-tr" style="grid-template-columns:repeat(4,1fr);color:#8b93a3">'
        f'<div>{d}</div><div>{t}</div><div class="r">{p}</div><div class="r">{r}</div></div>'
        for d, t, p, r in CSV_SAMPLE)
    bullets = [
        ("ok", "Long format: one row per day × ticker."),
        ("ok", "Flexible column names: <code>price/close/adj_close</code>, <code>return/ret</code>."),
        ("ok", "The benchmark (e.g. SPY) can sit in the same file as its own ticker."),
        ("", "If <code>return</code> is missing it is derived from price."),
    ]
    items = "".join(
        f'<div style="display:flex;gap:8px;align-items:flex-start;'
        f'font:400 12px/1.5 \'IBM Plex Sans\';color:'
        f'{"#c8ccd6" if kind else "#8b93a3"}">'
        f'<span style="color:{"#7fd0ab" if kind else "#8b93a3"};'
        f'font-family:\'IBM Plex Mono\'">{"✓" if kind else "·"}</span>'
        f'<span>{text}</span></div>'
        for kind, text in bullets)
    return (f'<div class="qt-list"><div class="qt-list-head"><b>Expected CSV format</b>'
            f'<span>Long format, daily returns</span></div>'
            f'<div style="padding:16px 18px;display:flex;flex-direction:column;gap:14px">'
            f'<div class="qt-tbl">{head}{body}</div>'
            f'<div style="display:flex;flex-direction:column;gap:7px">{items}</div>'
            f'</div></div>')


def fetch_form():
    """Landing'in ikinci veri yolu: sembol + tarih secip Yahoo'dan fiyat cekmek."""
    if market is None:
        st.caption("Live prices are off — `pip install yfinance` to enable them.")
        return
    ui.html('<span class="qt-sub" style="margin-top:26px">OR FETCH LIVE PRICES</span>')
    symbols = st.multiselect("Tickers", universe_symbols(), default=FETCH_DEFAULT,
                             max_selections=12, key="fetch_syms",
                             label_visibility="collapsed",
                             placeholder="Pick tickers — include a benchmark")
    today = pd.Timestamp.today().normalize()
    d1, d2 = st.columns(2)
    start = d1.date_input("From", value=(today - pd.DateOffset(years=3)).date(),
                          key="fetch_start")
    end = d2.date_input("To", value=today.date(), key="fetch_end")
    if st.button("Fetch prices →", type="primary", key="fetch_go",
                 disabled=len(symbols) < 2):
        st.session_state["_fetch"] = (tuple(symbols), str(start), str(end))
        st.rerun()
    st.caption("Adjusted closes from Yahoo Finance. Two tickers minimum — one of them "
               "is the benchmark. Yahoo rate-limits repeated requests.")


def landing():
    sidebar_idle()
    ui.html('<span class="qt-sub" style="color:#8fb3e8;letter-spacing:.14em">'
            "DAILY RETURNS CSV → FULL TEARSHEET</span>"
            '<h2 class="qt-title" style="font-size:38px;max-width:680px;line-height:1.12">'
            'See your portfolio\'s performance and risk on a single page.</h2>'
            '<p style="margin:14px 0 0;max-width:660px;font:400 15px/1.6 \'IBM Plex Sans\';'
            'color:#c8ccd6">Alpha, Beta, Sharpe, drawdown, rolling risk and Fama-French '
            'factor exposure — measured against your benchmark. Uploaded files are parsed on the server for this session only and are not written to disk or kept afterwards.</p>')
    st.write("")

    left, right = st.columns([1.25, 1], gap="large")
    with left:
        up = st.file_uploader("Returns CSV", type="csv", key="csv_up",
                              label_visibility="collapsed")
        if up is not None:
            st.session_state["_raw"] = up.getvalue()
            st.session_state["_name"] = up.name
            st.rerun()
        st.caption("or")
        if st.button("Try with sample data →", type="secondary", key="try_sample"):
            st.session_state["_sample"] = True
            st.rerun()
        st.caption("SPY · AAPL · MSFT · NVDA — 4 tickers, 2023-01-03 → 2026-08-18 "
                   "(synthetic, not real market data)")

        fetch_form()
    with right:
        ui.html(format_card())
    st.stop()


# --- 1b yukleme hatasi -------------------------------------------------------

def error_screen(raw, name, message):
    sidebar_idle()
    columns = peek_columns(raw)
    found = diagnose(columns)
    used = {c for c in found.values() if c}

    tags_found = "".join(
        f'<span class="qt-tag ok">{c} ✓</span>' if c in used
        else f'<span class="qt-tag">{c}</span>' for c in columns)
    missing = ["return", "ret"] if not found["return"] else []
    if not found["price"]:
        missing += ["price", "close", "adj_close"]
    tags_missing = ("".join(f'<span class="qt-tag miss">{c}</span>' for c in missing)
                    or '<span class="qt-tag">—</span>')

    ui.html(
        f'<div class="qt-panel warn"><h4>File read, but the required columns are missing</h4>'
        f'<p><code>{name}</code> does not carry the columns a tearsheet needs. '
        f'{message}</p>'
        f'<div class="qt-grid qt-grid-2" style="margin-top:16px">'
        f'<div><span class="qt-sub">COLUMNS FOUND IN YOUR FILE</span>'
        f'<div class="qt-chips">{tags_found}</div></div>'
        f'<div><span class="qt-sub">MISSING — ONE OF THESE NAMES IS REQUIRED</span>'
        f'<div class="qt-chips">{tags_missing}</div>'
        f'</div></div></div>')
    st.write("")

    a, b, _ = st.columns([1, 1, 2])
    if a.button("Upload a different file", type="primary", key="err_reset"):
        reset_data()
        st.rerun()
    if b.button("Continue with sample data", key="err_sample"):
        reset_data()
        st.session_state["_sample"] = True
        st.rerun()

    with st.expander("Map columns manually", expanded=True):
        st.caption("If your column names differ, tell us which is which. "
                   "Returns must be decimal (0.0123 = 1.23%).")
        c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
        date_c = c1.selectbox("Date column", columns,
                              index=columns.index(found["date"]) if found["date"] else 0)
        tick_c = c2.selectbox("Ticker column", columns,
                              index=columns.index(found["ticker"]) if found["ticker"] else 0)
        val_c = c3.selectbox("Return or price column", columns)
        kind = c4.selectbox("What is it?", ["return", "price"],
                            format_func=lambda k: "Daily return" if k == "return" else "Price")
        if st.button("Load with this mapping", type="primary", key="err_map"):
            st.session_state["_mapping"] = (date_c, tick_c, val_c, kind)
            st.rerun()
    st.stop()


# --- 1c cekme hatasi ---------------------------------------------------------

def fetch_error(exc):
    """Canli veri gelmedi. market.py yazilmamis olabilir ya da istek basarisiz."""
    sidebar_idle()
    # yfinance'in kendi sinifina bagimli olmayalim: market import edilememis olabilir
    name = type(exc).__name__
    text = str(exc).lower()
    throttled = (name == "YFRateLimitError" or "rate limit" in text
                 or "too many requests" in text)

    if isinstance(exc, NotImplementedError):
        head = "market.py is not written yet"
        body = ("<code>market.fetch_prices</code> still raises "
                "<code>NotImplementedError</code>, so there is nothing to load.")
        tail = ""
    elif throttled:
        head = "Yahoo is rate-limiting this server"
        body = ("Yahoo Finance throttles repeated requests from one address, and on a "
                "shared host that address is shared with everyone using this app.")
        tail = ("<p>Wait a few minutes and try again, or upload a CSV instead — the "
                "tearsheet does not care where the numbers came from.</p>")
    else:
        head = "Could not fetch prices"
        body = f"<code>{escape(name)}: {escape(str(exc))}</code>"
        tail = ("<p>Usual causes: a symbol Yahoo does not know, a date range with no "
                "trading days, or no network.</p>")
    ui.html(f'<div class="qt-panel warn"><h4>{head}</h4><p>{body}</p>{tail}</div>')
    st.write("")
    a, b, _ = st.columns([1, 1, 2])
    if a.button("Back", type="primary", key="fetch_back"):
        reset_data()
        st.rerun()
    if b.button("Continue with sample data", key="fetch_sample"):
        reset_data()
        st.session_state["_sample"] = True
        st.rerun()
    st.stop()


# --- veri girisi -------------------------------------------------------------

if not (st.session_state.get("_raw") or st.session_state.get("_sample")
        or st.session_state.get("_fetch")):
    landing()

if st.session_state.get("_sample"):
    df = load_sample()
    source_name = "sample_returns.csv"
    synthetic = True
elif st.session_state.get("_fetch"):
    syms, fetch_start, fetch_end = st.session_state["_fetch"]
    source_name = f"Yahoo Finance · {fetch_start} → {fetch_end}"
    synthetic = False
    try:
        with st.spinner("Fetching prices from Yahoo Finance…"):
            df = fetch_frame(syms, fetch_start, fetch_end)
    except Exception as exc:  # ag, sembol ya da henuz yazilmamis market.py
        fetch_error(exc)
else:
    raw = st.session_state["_raw"]
    source_name = st.session_state.get("_name", "returns.csv")
    synthetic = False
    try:
        df = load_bytes(raw, st.session_state.get("_mapping"))
    except ValueError as exc:
        error_screen(raw, source_name, str(exc))
    except Exception as exc:  # bozuk CSV, kodlama hatasi vb.
        error_screen(raw, source_name, f"While reading: {exc}")

wide = data.returns_wide(df)
tickers = list(wide.columns)


# --- sidebar (veri gelince) --------------------------------------------------

with st.sidebar:
    sidebar_brand()
    ui.html(f'<div class="qt-file"><b><em></em>{source_name}</b>'
            f'<span>{len(df):,} rows · {len(tickers)} tickers</span></div>')
    if st.button("Change", key="change_file"):
        reset_data()
        st.rerun()

    ui.html('<span class="qt-sub" style="margin-top:18px">SETTINGS</span>')
    ticker = st.selectbox("Ticker", tickers)
    bench_options = [t for t in tickers if t != ticker]
    bench_default = bench_index(bench_options)
    bench = (st.selectbox("Benchmark", bench_options, index=bench_default)
             if bench_options else None)
    window = st.segmented_control("Rolling window", list(WINDOWS), default=126,
                                  format_func=lambda w: f"{w}d", key="win") or 126
    st.caption(f"≈ {WINDOWS[window]} window")

    rf_slot = st.container()
    if bench is None:
        st.caption("Benchmark metrics need a second ticker in the file (e.g. SPY).")
    elif bench.upper() in PRICE_ONLY:
        st.caption(f"{bench} is a price-only index — it excludes dividends. "
                   "Measured against dividend-adjusted prices it inflates Alpha "
                   "by roughly the index dividend yield. Prefer a total-return "
                   "series such as ^SP500TR or SPY.")

r = wide[ticker].dropna()
if bench:
    r_al, b_al = data.align_pair(wide, ticker, bench)
else:
    r_al = b_al = None

try:
    ff = load_factor_file()
except FileNotFoundError:
    ff = None

# Faktor dosyasi sentetikken gercek getirilerle birlikte kullanilamaz: ne
# yuklemeleri anlamli olur ne de rf kolonu. Ikisi de sentetikse kendi icinde
# tutarli, o zaman kullanilabilir. 04. bolum de ayni bayragi okuyor.
ff_synth = ff is not None and factors.is_synthetic(ff)
ff_usable = ff is not None and not (ff_synth and not synthetic)

# Risksiz oran secilmiyor, veriden geliyor: Ken French'in gunluk 1 aylik hazine
# bonosu orani, analiz doneminin ortalamasi. Boylece Sharpe/Sortino/alpha ile
# FF regresyonu ayni rf kaynagini paylasiyor.
rf, rf_days = factors.risk_free_annual(ff, r.index) if ff_usable else (None, 0)
rf_known = rf is not None
if not rf_known:
    rf = 0.0
rf_pct = rf * 100

with rf_slot:
    ui.html('<span class="qt-sub" style="margin-top:16px">RISK-FREE RATE</span>'
            f'<div style="font:600 18px/1.2 \'IBM Plex Mono\';color:#f2f4f8">'
            f'{rf_pct:.2f}%<span style="font:400 11px/1 \'IBM Plex Sans\';'
            f'color:#8b93a3;margin-left:6px">annual</span></div>')
    if rf_known:
        cover = "" if rf_days >= len(r) else f" — covers {rf_days:,} of {len(r):,} days"
        st.caption(f"1-month T-bill (Kenneth French), averaged over this "
                   f"window{cover}. Feeds Sharpe, Sortino and Alpha.")
    else:
        st.caption("No overlapping risk-free data for these dates, so Sharpe, "
                   "Sortino and Alpha are computed at 0%.")

# CAPM regresyonu bir kez kuruluyor: 01 bolumundeki alpha karti anlamlilik rozeti
# icin t-istatistigini, 04 bolumu de ayni tabloyu okuyor. Regresyon metrics.py'daki
# capm_alpha'yi ikame etmiyor; kartin degeri hala oradan geliyor, buradan sadece
# "bu alpha sifirdan ayirt edilebiliyor mu" sorusunun cevabi aliniyor.
capm_table = capm_r2 = capm_t = None
if bench:
    try:
        capm_table, capm_r2 = factors.capm_regression(r_al, b_al, rf)
        capm_t = factors.alpha_t_stat(capm_table)
    except Exception:
        capm_table = None


# --- ortak yardimcilar -------------------------------------------------------

def bench_card(label, key):
    """Benchmark secilmemisken benchmark'a bagli metrik karti."""
    return ui.metric_card(label, "—", "No second ticker in the file — "
                                      "no benchmark selected.", tone="muted", info_key=key)


def drawdown_window(dd):
    """En derin dip ve ondan onceki zirve (sunum detayi; hesap metrics.py'da)."""
    if dd is None or len(dd) == 0:
        return None
    trough = dd.idxmin()
    before = dd.loc[:trough]
    peaks = before[before >= 0]
    peak = peaks.index.max() if len(peaks) else before.index.min()
    return peak, trough


def series_footer(s, fmt, label="Now"):
    if s is None or len(s) == 0:
        return ""
    return (f'{label} <span style="color:#f2f4f8">{fmt(s.iloc[-1])}</span> · '
            f'period range {fmt(s.min())} – {fmt(s.max())}')


def stars(p):
    return "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""


tab_main, tab_compare, tab_guide = st.tabs(["Tearsheet", "Compare", "Metric guide"])


# --- ana tearsheet -----------------------------------------------------------

with tab_main:
    meta = [f"{len(r):,} observations", f"{r.index.min():%Y-%m-%d} → {r.index.max():%Y-%m-%d}"]
    if bench:
        meta.append(f"Benchmark: {bench}")
    meta.append(f"Rolling {window}d")
    # Sharpe, Sortino ve Alpha hangi risksiz oranla hesaplandi: kullanici bunu
    # sayfadan okuyabilmeli, yoksa sayilar hangi varsayimla uretildigi belirsiz.
    meta.append(f"r_f {rf_pct:.2f}%" + ("" if rf_known else " (no data)"))
    title_extra = f' <small>vs</small> {bench}' if bench else ""
    badge_html = (ui.badge("Synthetic sample data", "warn") if synthetic else "")
    ui.html(f'<div style="display:flex;justify-content:space-between;align-items:flex-end;'
            f'gap:24px;flex-wrap:wrap"><div><h2 class="qt-title">{ticker}{title_extra}</h2>'
            f'<div class="qt-meta">'
            + "<i></i>".join(f"<span>{x}</span>" for x in meta)
            + f'</div></div><div>{badge_html}</div></div>')

    # hata veren metriklerin ozeti — icerik en sonda doldurulur, yeri burasi
    error_slot = st.container()

    # ---------- 01 · PERFORMANCE ----------
    ui.section("01", "Performance",
               "What it returned, and how much risk was taken to get there")

    alpha_v = val("capm_alpha", r_al, b_al, rf) if bench else None
    beta_v = val("beta", r_al, b_al) if bench else None
    r2_v = val("r_squared", r_al, b_al) if bench else None
    sharpe_v = val("sharpe", r, rf)
    sortino_v = val("sortino", r, rf)
    cagr_v = val("cagr", r)
    vol_v = val("annual_volatility", r)
    mdd_v = val("max_drawdown", r)
    dd_s = val("drawdown_series", r)

    b_cagr = val("cagr", b_al) if bench else None
    b_vol = val("annual_volatility", b_al) if bench else None

    cards = []

    # Annualized Alpha
    if not bench:
        cards.append(bench_card("Annualized Alpha", "capm_alpha"))
    elif alpha_v is None:
        cards.append(ui.pending_card("Annualized Alpha", "capm_alpha"))
    else:
        # Alpha'nin isareti tek basina bir sey soylemiyor. Rozet t-istatistiginden
        # geliyor: |t| < 1.96 ise deger sifirdan ayirt edilemiyor demektir ve kart
        # ne yesil ne kirmizi olur — "olcemedik" ile "kotu" ayni sey degil.
        note = f"Annual excess return {bench} risk cannot explain."
        if capm_t is None:
            tone, b_text, b_tone = "neutral", None, "neutral"
        elif abs(capm_t) >= 1.96:
            tone = ui.sign_tone(alpha_v)
            b_text = "▲ SIGNIFICANT" if alpha_v > 0 else "▼ SIGNIFICANT"
            b_tone = "good" if alpha_v > 0 else "bad"
            note += f" t = {ui.num(capm_t, 2)}, distinct from zero at 95%."
        else:
            tone, b_text, b_tone = "neutral", "NOT SIGNIFICANT", "neutral"
            note += (f" t = {ui.num(capm_t, 2)} — not distinct from zero, so the "
                     f"sign is noise as much as skill.")
        cards.append(ui.metric_card(
            "Annualized Alpha", ui.pct(alpha_v, 2, signed=True), note,
            tone=tone, info_key="capm_alpha",
            badge_text=b_text, badge_tone=b_tone))

    # Beta
    if not bench:
        cards.append(bench_card("Beta", "beta"))
    elif beta_v is None:
        cards.append(ui.pending_card("Beta", "beta"))
    else:
        cards.append(ui.metric_card(
            "Beta", ui.num(beta_v, 2),
            f"When {bench} moves 1%, {ticker} moves {ui.num(beta_v, 2)}% on average.",
            info_key="beta", chip="vs 1.00"))

    # Sharpe
    if sharpe_v is None:
        cards.append(ui.pending_card("Sharpe", "sharpe"))
    else:
        tone = "good" if sharpe_v >= 1 else ("bad" if sharpe_v < 0.5 else "neutral")
        cards.append(ui.metric_card(
            "Sharpe", ui.num(sharpe_v, 2), ui.note_of("sharpe"), tone=tone,
            info_key="sharpe",
            badge_text={"good": "▲ GOOD", "bad": "▼ WEAK"}.get(tone),
            badge_tone=tone if tone != "neutral" else "neutral"))

    # Sortino
    cards.append(ui.pending_card("Sortino", "sortino") if sortino_v is None else
                 ui.metric_card("Sortino", ui.num(sortino_v, 2), ui.note_of("sortino"),
                                info_key="sortino"))

    # CAGR
    cards.append(ui.pending_card("CAGR", "cagr") if cagr_v is None else
                 ui.metric_card("CAGR", ui.pct(cagr_v, 1), ui.note_of("cagr"),
                                info_key="cagr",
                                chip=f"{bench} {ui.pct(b_cagr, 1)}" if b_cagr is not None else None))

    # Volatility
    cards.append(ui.pending_card("Volatility", "annual_volatility") if vol_v is None else
                 ui.metric_card("Volatility", ui.pct(vol_v, 1),
                                ui.note_of("annual_volatility"),
                                info_key="annual_volatility",
                                chip=f"{bench} {ui.pct(b_vol, 1)}" if b_vol is not None else None))

    # Max Drawdown
    if mdd_v is None:
        cards.append(ui.pending_card("Max Drawdown", "max_drawdown"))
    else:
        span = drawdown_window(dd_s)
        note = ui.note_of("max_drawdown")
        if span:
            note += f" · {span[0]:%Y-%m} → {span[1]:%Y-%m}"
        cards.append(ui.metric_card(
            "Max Drawdown", ui.pct(mdd_v, 1), note, tone="bad", info_key="max_drawdown",
            badge_text="▼ WATCH" if mdd_v <= -0.20 else None, badge_tone="bad"))

    # R² (CAPM)
    if not bench:
        cards.append(bench_card("R² (CAPM)", "r_squared"))
    elif r2_v is None:
        cards.append(ui.pending_card("R² (CAPM)", "r_squared"))
    else:
        cards.append(ui.metric_card("R² (CAPM)", ui.num(r2_v, 2), ui.note_of("r_squared"),
                                    info_key="r_squared"))

    ui.card_grid(cards, cols=4)

    # ---------- 02 · GROWTH ----------
    ui.section("02", "Growth", "The path of $1 over time, and distance from the peak")

    left, right = st.columns(2, gap="medium")
    with left:
        g = val("growth_of_1", r_al if bench else r)
        if g is None:
            ui.pending_chart("equity", "Equity Curve", "growth_of_1")
        else:
            with ui.chart_card("equity", "Equity Curve", "Growth of $1",
                               "What $1 invested at the start is worth today. "
                               "The benchmark is dotted.", info="growth_of_1"):
                curves = {ticker: g}
                bg = val("growth_of_1", b_al) if bench else None
                if bg is not None:
                    curves[bench] = bg
                st.plotly_chart(plots.line_chart(curves, dashed=(bench,), hover_fmt=".2f"),
                                width="stretch", key="ch_equity")
                keys = [(ticker, plots.SERIES[0], "solid")]
                if bg is not None:
                    keys.append((f"{bench} (benchmark)", plots.SERIES[1], "dashed"))
                ui.chart_footer(ui.legend(keys))
    with right:
        if dd_s is None:
            ui.pending_chart("underwater", "Underwater", "drawdown_series")
        else:
            with ui.chart_card("underwater", "Underwater", "Drawdown from peak",
                               "How far below the running peak you are, "
                               "day by day.", info="drawdown_series"):
                st.plotly_chart(plots.underwater_chart(dd_s), width="stretch",
                                key="ch_uw")
                span = drawdown_window(dd_s)
                foot = f'Deepest: <span style="color:#eda1a1">{ui.pct(dd_s.min(), 1)}</span>'
                if span:
                    foot += f" · {span[0]:%Y-%m-%d} → {span[1]:%Y-%m-%d}"
                ui.chart_footer(foot)

    # ---------- 03 · RISK OVER TIME ----------
    ui.section("03", "Risk over time",
               f"{window}-day rolling window; the change itself, not one average")

    left, right = st.columns(2, gap="medium")
    with left:
        rs = val("rolling_sharpe", r, window, rf)
        if rs is None:
            ui.pending_chart("rsharpe", "Rolling Sharpe", "rolling_sharpe")
        else:
            with ui.chart_card("rsharpe", "Rolling Sharpe", f"{window}d",
                               "Above the 1.0 line: the risk taken paid off.", info="rolling_sharpe"):
                st.plotly_chart(plots.line_chart({"Sharpe": rs}, refline=1.0,
                                                 refline_label="threshold 1.0"),
                                width="stretch", key="ch_rs")
                ui.chart_footer(series_footer(rs, lambda v: ui.num(v, 2)))
    with right:
        rv = val("rolling_volatility", r, window)
        if rv is None:
            ui.pending_chart("rvol", "Rolling Volatility", "rolling_volatility")
        else:
            with ui.chart_card("rvol", "Rolling Volatility", "annualized, %",
                               "Volatility is not constant; it clusters.", info="rolling_volatility"):
                st.plotly_chart(plots.line_chart({"Volatility": rv}, pct=True,
                                                 colors=[plots.SERIES[1]]),
                                width="stretch", key="ch_rv")
                ui.chart_footer(series_footer(rv, lambda v: ui.pct(v, 1)))

    left, right = st.columns(2, gap="medium")
    with left:
        rb = val("rolling_beta", r_al, b_al, window) if bench else None
        if not bench:
            with st.container(key="pending-rbeta-nb"):
                ui.html('<div class="qt-empty" style="min-height:300px">'
                        '<div class="ring">·</div><b>Rolling Beta needs a benchmark</b>'
                        '<p>Your file holds a single ticker. Add a second one (e.g. SPY) '
                        'over the same date range and this chart opens.</p></div>')
        elif rb is None:
            ui.pending_chart("rbeta", "Rolling Beta", "rolling_beta")
        else:
            with ui.chart_card("rbeta", f"Rolling Beta <span style='color:#8b93a3;"
                                        f"font-weight:400'>vs {bench}</span>", f"{window}d",
                               "Above 1.0: you react more sharply than the market.", info="rolling_beta"):
                st.plotly_chart(plots.line_chart({"Beta": rb}, refline=1.0,
                                                 refline_label="β = 1.0",
                                                 colors=[plots.SERIES[2]]),
                                width="stretch", key="ch_rb")
                ui.chart_footer(series_footer(rb, lambda v: ui.num(v, 2)))
    with right:
        mt = val("monthly_return_table", r)
        if mt is None:
            ui.pending_chart("heat", "Monthly Returns", "monthly_return_table")
        else:
            with ui.chart_card("heat", "Monthly Returns", "%, year × month",
                               "Blue is gain, red is loss; every cell shows its number.", info="monthly_return_table"):
                st.plotly_chart(plots.monthly_heatmap(mt), width="stretch",
                                key="ch_heat")

    # ---------- 04 · FACTOR EXPOSURE ----------
    # Bu bolum metrik kartlarindan farkli: regresyon, grafik ve tablo uretimi
    # ic ice geciyor ve herhangi biri patlarsa sayfanin geri kalani (05 ve
    # kenar cubugundaki CSV disa aktarimi dahil) hic render edilmiyordu.
    # val() metrikler icin ne yapiyorsa, bu sarmalayici da bolum icin onu yapiyor:
    # hata bolumun kendi icinde kalir, tearsheet'in kalani ayakta durur.
    try:
        # ff_synth / ff_usable yukarida, rf ile birlikte hesaplandi: sentetik bir
        # faktor dosyasina gercek getiri regres etmek anlamsiz katsayi uretir.
        if ff is not None and not ff_usable:
            ui.section("04", "Factor exposure",
                       "How much of your return comes from known risk factors?")
            ui.html('<div class="qt-panel warn"><h4>Factor analysis is off for this data</h4>'
                    '<p>The factor file in <code>data/ff5_daily.csv</code> is a synthetic '
                    'placeholder, but the returns loaded here are real. Regressing real '
                    'returns on invented factors produces coefficients that mean nothing — '
                    'a near-zero R² and loadings that are pure noise — so the section is '
                    'hidden rather than shown with numbers you should not read.</p>'
                    '<p>Run <code>python update_factors.py</code> to pull the real '
                    'Kenneth French series, and this section comes back.</p></div>')

        if ff_usable:
            ui.section("04", "Factor exposure",
                       "How much of your return comes from known risk factors?")

            with st.expander("What do the five factors mean?", expanded=True):
                terms = [
                    ("Mkt-RF", "Market excess",
                     "The whole market's return above the risk-free rate."),
                    ("SMB", "Small − big",
                     "Excess return of small companies over large ones. "
                     "Negative: you sit on the large-cap side."),
                    ("HML", "Value − growth",
                     "Excess return of cheap (value) stocks over expensive (growth) ones. "
                     "Negative: a growth tilt."),
                    ("RMW", "Robust − weak",
                     "Excess return of companies with high operating profitability."),
                    ("CMA", "Conservative − aggressive",
                     "Excess return of low-investment companies over high-investment ones."),
                ]
                ui.html('<div class="qt-grid qt-grid-5">' + "".join(
                    f'<div style="display:flex;flex-direction:column;gap:5px">'
                    f'<span style="font:600 12px/1 \'IBM Plex Mono\';color:#8fb3e8">{code}</span>'
                    f'<span style="font:500 11.5px/1.35 \'IBM Plex Sans\';color:#f2f4f8">{tr}</span>'
                    f'<span style="font:400 11px/1.45 \'IBM Plex Sans\';color:#8b93a3">{desc}</span>'
                    f'</div>' for code, tr, desc in terms) + "</div>"
                    + '<div style="font:400 11.5px/1.5 \'IBM Plex Sans\';color:#8b93a3;'
                      'padding-top:12px;margin-top:12px;border-top:1px solid #333945">'
                      'A loading is your sensitivity to that factor. '
                      '<span style="color:#c8ccd6">+0.5</span> means "when the factor gains '
                      '1%, you gain 0.5%". <span style="color:#c8ccd6">Alpha</span> is what '
                      'none of the five factors explains.</div>')

            if ff_synth:
                st.caption("Factor data: data/ff5_daily.csv — synthetic sample; "
                           "run python update_factors.py for the real series.")
            else:
                st.caption(f"Factor data: Kenneth French 5-factor daily, "
                           f"{ff.index.min():%Y-%m-%d} → {ff.index.max():%Y-%m-%d}. "
                           f"The library publishes with a lag, so the last few weeks of "
                           f"your return series may sit outside the regression window.")

            # Sentetik getiriyi gercek faktore regres etmek, tersi kadar anlamsiz:
            # ortak neden yok, R-kare sifira yakin cikiyor. Bolumu gizlemiyoruz —
            # ornek veri yolunda duzenin nasil gorundugu gorulsun — ama sayilarin
            # okunacak sey olmadigi burada acikca yaziyor.
            if synthetic:
                ui.html('<div class="qt-panel warn" style="margin:10px 0 4px">'
                        '<h4>These loadings are illustrative, not a real exposure</h4>'
                        '<p>The sample returns are synthetic while the factors are '
                        'real, so nothing connects the two series: expect an R² near '
                        'zero and coefficients that are noise. The section stays '
                        'visible to show the layout — load your own data or fetch '
                        'live prices for numbers worth reading.</p></div>')

            # faktor dosyasiyla ortak gun sayisi az oldugunda regresyon kurulamaz;
            # bu bir hata degil, veri kisitidir — bolum kendi durumunu anlatir
            try:
                betas = factors.rolling_ff_betas(r, ff, window)
            except Exception:
                betas = pd.DataFrame()
            try:
                ff5_table, ff5_r2 = factors.ff_regression(r, ff, "ff5")
                ff3_table, ff3_r2 = factors.ff_regression(r, ff, "ff3")
            except Exception:
                ff5_table = None

        if ff_usable and ff5_table is None:
            ui.html('<div class="qt-panel warn"><h4>Not enough overlapping days for factor analysis</h4>'
                    '<p>The overlap between your return series and <code>data/ff5_daily.csv</code> '
                    'is too short to fit a regression. Load a longer date range, or pull fresh '
                    'factor data with <code>python update_factors.py</code>.</p>'
                    '</div>')

        if ff_usable and ff5_table is not None:
            left, right = st.columns([1.35, 1], gap="medium")
            with left:
                if betas.empty:
                    with st.container(key="pending-fbeta"):
                        ui.html('<div class="qt-empty" style="min-height:300px">'
                                '<div class="ring">·</div>'
                                '<b>Rolling factor betas need a longer series</b>'
                                f'<p>The {window}-day window is longer than the overlap with the '
                                'factor file. Pick a shorter window, or load a longer date '
                                'range.</p></div>')
                else:
                    with ui.chart_card("fbeta", "Rolling factor betas", f"{window}d",
                                       "Exposure is not fixed: it shifts across the window."):
                        named = {c.upper().replace("_RF", "-RF"): betas[c] for c in betas.columns}
                        st.plotly_chart(plots.line_chart(named, patterned=True),
                                        width="stretch", key="ch_fb")
                        ui.chart_footer(ui.legend([
                            (n, plots.SERIES[i % 5], {"solid": "solid"}.get(
                                plots.DASHES[i % 5], "dashed"))
                            for i, n in enumerate(named)]))
            with right:
                with ui.chart_card("floads", "FF5 loadings", "full period",
                                   "Right of zero is positive exposure, left is negative."):
                    loadings = ff5_table.set_index("factor")["coef"].drop("Alpha")
                    loadings.index = [i.upper().replace("_RF", "-RF") for i in loadings.index]
                    st.plotly_chart(plots.loadings_bar(loadings), width="stretch",
                                    key="ch_fl")

            def reg_table(title, table, r2, foot=""):
                # Alpha'nin gunluk katsayisi 0.0001 mertebesinde: uc ondalikta 0.000
                # gorunuyordu. Baz puana cevirince (x 10000) okunur bir sayi oluyor,
                # faktor yuklemeleri ise zaten 0.1-1.5 araliginda, onlar ondalik kaliyor.
                cols = "grid-template-columns:1.15fr 92px 78px 52px"
                out = [f'<div class="qt-tbl"><div class="qt-tbl-head"><b>{title}</b>'
                       f'<span>R² {ui.num(r2, 2)}</span></div>',
                       f'<div class="qt-tr head" style="{cols}"><div>FACTOR</div>'
                       f'<div class="r">COEF</div><div class="r">ANN.</div>'
                       f'<div class="r">t</div></div>']
                for _, row in table.iterrows():
                    is_alpha = row["factor"] == "Alpha"
                    name = row["factor"].upper().replace("_RF", "-RF") if not is_alpha else "Alpha"
                    mark = stars(row["p_value"])
                    ann = ("—" if pd.isna(row["annualized"])
                           else ui.pct(row["annualized"], 2, signed=True))
                    ann_color = ("#7fd0ab" if row["annualized"] > 0 else "#eda1a1") \
                        if not pd.isna(row["annualized"]) else "#8b93a3"
                    label_color = "#f2f4f8" if is_alpha else ("#c8ccd6" if mark else "#8b93a3")
                    coef = (f'{ui.num(row["coef"] * 1e4, 1, signed=True)} bp'
                            if is_alpha else ui.num(row["coef"], 3))
                    out.append(
                        f'<div class="qt-tr" style="{cols}">'
                        f'<div style="color:{label_color}">{name} {mark}</div>'
                        f'<div class="r">{coef}</div>'
                        f'<div class="r" style="color:{ann_color}">{ann}</div>'
                        f'<div class="r">{ui.num(row["t_stat"], 2)}</div></div>')
                legend_note = ("* p&lt;0.05 · ** p&lt;0.01 · *** p&lt;0.001 — rows without a star "
                               "are not statistically significant.")
                out.append(f'<div class="qt-tbl-foot">{foot or legend_note}</div></div>')
                return "".join(out)

            t1 = reg_table("FF5 regression", ff5_table, ff5_r2)
            t2 = reg_table("FF3 regression", ff3_table, ff3_r2,
                           "Alpha shifts once profitability and investment are dropped: "
                           "those two were explaining part of the return.")
            if bench and capm_table is not None:
                t3 = reg_table(f"CAPM (vs {bench})", capm_table, capm_r2,
                               f"Single-factor model, excess returns on both sides: "
                               f"(r − r_f) = α + β(r_b − r_f) + ε, with r_f = "
                               f"{rf_pct:.2f}% annual, taken from the factor file rather "
                           f"than assumed. Alpha's daily coefficient is shown "
                               f"in basis points; 1 bp = 0.01%.")
            else:
                t3 = ('<div class="qt-list" style="border-style:dashed;border-color:#454c5a;'
                      'background:#20242c"><div class="qt-list-head" style="border-bottom:'
                      '1px dashed #333945;flex-direction:row;justify-content:space-between;'
                      'align-items:center"><b style="color:#c8ccd6">CAPM regression</b>'
                      + ui.badge("NO BENCHMARK", "warn") +
                      '</div><div class="qt-empty" style="min-height:180px">'
                      '<b>The single-factor CAPM table needs a benchmark</b>'
                      '<p>Add a second ticker (e.g. SPY) to your file and Alpha, Beta and R² '
                      'land here. This is not an error.</p></div></div>')
            # Uc tabloyu ayni siraya sikistirinca ANNUAL ve t sutunlari masaustunde
            # bile iki satira boluniyordu. FF5/FF3 yan yana, CAPM tam genislikte altta.
            ui.html(f'<div class="qt-grid qt-grid-2">{t1}{t2}</div>'
                    f'<div style="margin-top:14px">{t3}</div>')
    except Exception as exc:  # bolum coksun, sayfa cokmesin
        ui.ERRORS["factor section"] = f"{type(exc).__name__}: {exc}"
        ui.html('<div class="qt-panel warn" style="border-left-color:#eda1a1">'
                '<h4>The factor section could not be rendered</h4>'
                f'<p><code>{escape(type(exc).__name__)}: {escape(str(exc))}</code></p>'
                '<p>Every other section on this page is unaffected. This is most '
                'often a factor file that does not overlap the loaded date range; '
                '<code>python update_factors.py</code> refreshes it.</p></div>')

    # ---------- 05 · DETAILED METRICS ----------
    ui.section("05", "Detailed metrics",
               "Three questions: how returns are distributed · how bad a bad day is · "
               "where you stand against the benchmark")

    def row(label, key, value, fmt, tone=None, sub=None):
        """Liste satiri; deger yoksa 'hazir degil' satirina donusur."""
        if value is None:
            return (label, key, None, None)
        return (label, sub or ui.note_of(key), fmt(value),
                tone if tone else "neutral")

    tr_v = val("total_return", r)
    calmar_v = val("calmar", r)
    win_v = val("win_rate", r)
    best_v = val("best_day", r)
    worst_v = val("worst_day", r)

    g1 = ui.stat_list("Return & distribution", "How much it returned, and how often", [
        row("Total Return", "total_return", tr_v, lambda v: ui.pct(v, 1, signed=True),
            ui.sign_tone(tr_v)),
        row("Calmar", "calmar", calmar_v, lambda v: ui.num(v, 2)),
        row("Win Rate", "win_rate", win_v, lambda v: ui.pct(v, 1)),
        row("Best Day", "best_day", best_v, lambda v: ui.pct(v, 2, signed=True), "good",
            sub=f"{r.idxmax():%Y-%m-%d}"),
        row("Worst Day", "worst_day", worst_v, lambda v: ui.pct(v, 2, signed=True), "bad",
            sub=f"{r.idxmin():%Y-%m-%d}"),
    ])

    skew_v = val("skewness", r)
    kurt_v = val("kurtosis", r)
    var_v = val("var_historic", r)
    cvar_v = val("cvar_historic", r)
    ulcer_v = val("ulcer_index", r)

    g2 = ui.stat_list("Tail risk", "The character of rare but sharp days", [
        row("Skewness", "skewness", skew_v, lambda v: ui.num(v, 2), ui.sign_tone(skew_v)),
        row("Kurtosis", "kurtosis", kurt_v, lambda v: ui.num(v, 2)),
        row("VaR 95%", "var_historic", var_v, lambda v: ui.pct(v, 2), "bad"),
        row("CVaR 95%", "cvar_historic", cvar_v, lambda v: ui.pct(v, 2), "bad"),
        row("Ulcer Index", "ulcer_index", ulcer_v, lambda v: ui.num(v, 2)),
    ])

    lists = [g1, g2]
    if bench:
        corr_v = val("correlation", r_al, b_al)
        te_v = val("tracking_error", r_al, b_al)
        ir_v = val("information_ratio", r_al, b_al)
        up_v = val("up_capture", r_al, b_al)
        down_v = val("down_capture", r_al, b_al)
        lists.append(ui.stat_list(
            f"Relative to benchmark · {bench}",
            "What holding this instead of the index bought you", [
                row("Correlation", "correlation", corr_v, lambda v: ui.num(v, 2)),
                row("Tracking Error", "tracking_error", te_v, lambda v: ui.pct(v, 1)),
                row("Information Ratio", "information_ratio", ir_v, lambda v: ui.num(v, 2),
                    ui.sign_tone(ir_v)),
                row("Up Capture", "up_capture", up_v, lambda v: ui.pct(v, 0),
                    "good" if up_v is not None and up_v > 1 else "neutral"),
                row("Down Capture", "down_capture", down_v, lambda v: ui.pct(v, 0),
                    "bad" if down_v is not None and down_v > 1 else "good"),
            ]))
    ui.html(f'<div class="qt-grid qt-grid-{len(lists)}">' + "".join(lists) + "</div>")
    if not bench:
        st.caption("No benchmark selected, so the third column is hidden — a two-column "
                   "layout instead of empty rows.")

    # ---------- export (sidebar'in dibinde kalici) ----------
    export_rows = [("Ticker", ticker), ("Benchmark", bench or ""),
                   ("Observations", len(r)), ("Start", f"{r.index.min():%Y-%m-%d}"),
                   ("End", f"{r.index.max():%Y-%m-%d}"), ("Rolling window", window)]
    for label, v, fmt in [
            ("Annualized Alpha", alpha_v, "pct"), ("Beta", beta_v, "num"),
            ("Sharpe", sharpe_v, "num"), ("Sortino", sortino_v, "num"),
            ("CAGR", cagr_v, "pct"), ("Volatility", vol_v, "pct"),
            ("Max Drawdown", mdd_v, "pct"), ("R2 (CAPM)", r2_v, "num"),
            ("Total Return", tr_v, "pct"), ("Calmar", calmar_v, "num"),
            ("Win Rate", win_v, "pct"), ("Best Day", best_v, "pct"),
            ("Worst Day", worst_v, "pct"), ("Skewness", skew_v, "num"),
            ("Kurtosis", kurt_v, "num"), ("VaR 95%", var_v, "pct"),
            ("CVaR 95%", cvar_v, "pct")]:
        export_rows.append((label, "" if v is None else round(float(v), 6)))

    with st.sidebar:
        # Pasif PDF/PNG dugmeleri "bozuk ozellik" hissi veriyordu; calisan tek yol
        # kaldi. PDF isteyen tarayicidan yazdirabilir, onu dugme olarak sunmuyoruz.
        ui.html('<span class="qt-sub" style="margin-top:22px">EXPORT</span>')
        st.download_button(
            "Download metrics (CSV)",
            pd.DataFrame(export_rows, columns=["metric", "value"]).to_csv(index=False),
            file_name=f"tearsheet_{ticker}_{r.index.max():%Y%m%d}.csv",
            mime="text/csv", key="exp_csv", width="stretch")
        st.caption("Every number on this page as a two-column table. "
                   "For a PDF, print the page from your browser.")


# --- iki hisse karsilastirma -------------------------------------------------

with tab_compare:
    if len(tickers) < 2:
        with st.container(key="pending-compare"):
            ui.html('<div class="qt-empty" style="min-height:220px">'
                    '<div class="ring">1</div>'
                    '<b>Comparison needs a second series</b>'
                    f'<p>Your file holds a single ticker (<code>{tickers[0]}</code>). Add '
                    'another ticker over the same date range and this tab opens — or add '
                    'a benchmark.</p></div>')
        if st.button("Try with sample data", type="primary", key="cmp_sample"):
            reset_data()
            st.session_state["_sample"] = True
            st.rerun()
    else:
        c1, c2, c3 = st.columns([1, 1, 2])
        a_name = c1.selectbox("First", tickers, index=0)
        options_b = [t for t in tickers if t != a_name]
        b_name = c2.selectbox("Second", options_b, index=bench_index(options_b))
        a, b = data.align_pair(wide, a_name, b_name)
        with c3:
            ui.html(f'<div class="qt-meta" style="margin-top:26px"><span>{len(a):,} common '
                    f'observations</span><i></i><span>{a.index.min():%Y-%m-%d} → '
                    f'{a.index.max():%Y-%m-%d}</span><i></i>'
                    f'<span>r_f {rf_pct:.2f}%</span></div>')

        # metrik karsilastirmasi: fark sutunu + kazanan hucre
        SPECS = [
            ("Total Return", "total_return", "pct", "up", None),
            ("CAGR", "cagr", "pct", "up", None),
            ("Volatility", "annual_volatility", "pct", "down", "↓ better"),
            ("Sharpe", "sharpe", "num", "up", None),
            ("Sortino", "sortino", "num", "up", None),
            ("Max Drawdown", "max_drawdown", "pct", "up", "↑ better"),
            ("Calmar", "calmar", "num", "up", None),
            ("Win Rate", "win_rate", "pct", "up", None),
            ("VaR 95%", "var_historic", "pct", "up", "↑ better"),
        ]
        # Sharpe ve Sortino risksiz orani ikinci konumsal argüman olarak aliyor;
        # kenar cubugundaki deger burada da gecerli olsun.
        RF_METRICS = {"sharpe", "sortino"}
        cols = "grid-template-columns:1.6fr 1fr 1fr 1.1fr"
        out = [f'<div class="qt-tbl"><div class="qt-tbl-head">'
               f'<b>Metric comparison</b><span>Delta = {a_name} − {b_name}</span></div>',
               f'<div class="qt-tr head" style="{cols}"><div>METRIC</div>'
               f'<div class="r">{a_name}</div><div class="r">{b_name}</div>'
               f'<div class="r">DELTA</div></div>']
        a_wins = b_wins = 0
        for label, key, kind, direction, hint in SPECS:
            extra = (rf,) if key in RF_METRICS else ()
            va, vb = val(key, a, *extra), val(key, b, *extra)
            fmt = (lambda v: ui.pct(v, 1)) if kind == "pct" else (lambda v: ui.num(v, 2))
            if va is None or vb is None:
                out.append(f'<div class="qt-tr" style="{cols}">'
                           f'<div style="color:#8b93a3">{label}<small>metrics.{key}() '
                           f'is not written yet</small></div>'
                           f'<div class="r"><span class="qt-skel" style="width:32px">'
                           f'</span></div><div class="r"><span class="qt-skel" '
                           f'style="width:32px"></span></div><div class="r">—</div></div>')
                continue
            delta = va - vb
            eps = 0.01 if kind == "pct" else 0.1
            dtxt = ui.pp(delta, 1) if kind == "pct" else ui.num(delta, 2, signed=True)
            win_a = (va > vb) if direction == "up" else (va < vb)
            # Ok, farkin isaretini degil metrigin yonunu anlatiyor: volatilitede
            # daha yuksek olmak kotu, orada pozitif bir delta asagi ok demek.
            arrow = "≈" if abs(delta) < eps else ("▲" if win_a else "▼")
            dcolor = "#8b93a3" if arrow == "≈" else (
                "#8fb3e8" if win_a else "#eab088")
            if abs(delta) < eps:
                win_a = None
            elif win_a:
                a_wins += 1
            else:
                b_wins += 1
            ca = " win" if win_a is True else ""
            cb = " win" if win_a is False else ""
            tag = (f'<small style="margin-left:6px;color:#8b93a3">{hint}</small>'
                   if hint else "")
            out.append(f'<div class="qt-tr" style="{cols}"><div>{label}{tag}</div>'
                       f'<div class="r{ca}">{fmt(va)}</div>'
                       f'<div class="r{cb}">{fmt(vb)}</div>'
                       f'<div class="r" style="color:{dcolor}">{arrow} {dtxt}</div></div>')
        leader = (f"{a_name if a_wins >= b_wins else b_name} leads in "
                  f"{max(a_wins, b_wins)} of {len(SPECS)} rows"
                  if a_wins or b_wins else "No comparable metric yet")
        out.append(f'<div class="qt-tbl-foot"><span>Highlighted cell = winner of that row · '
                   f'▲/▼ = better / worse for {a_name} on that metric, not the raw sign '
                   f'of the delta</span>'
                   f'<span>{leader}</span></div></div>')
        table_html = "".join(out)

        beta_ab = val("beta", a, b)
        corr_ab = val("correlation", a, b)
        stats = ui.stat_list("Relationship", f"Between {a_name} and {b_name}", [
            ("Beta", f"How much {a_name} moves when {b_name} moves 1%",
             ui.num(beta_ab, 2), "neutral") if beta_ab is not None else
            ("Beta", "beta", None, None),
            ("Correlation", "How closely their daily returns move together",
             ui.num(corr_ab, 2), "neutral") if corr_ab is not None else
            ("Correlation", "correlation", None, None),
        ])

        left, right = st.columns([1.5, 1], gap="medium")
        with left:
            ui.html(table_html)
        with right:
            ui.html(stats)
            points = []
            for t in tickers:
                s = wide[t].dropna()
                ret, vol = val("cagr", s), val("annual_volatility", s)
                if ret is not None and vol is not None:
                    points.append({"ticker": t, "ret": ret, "vol": vol})
            if points:
                with ui.chart_card("scatter", "Risk vs Return", "all tickers in the file",
                                   "Top left is better: less volatility, more return."):
                    st.plotly_chart(
                        plots.risk_return_scatter(pd.DataFrame(points),
                                                  highlight=(a_name, b_name)),
                        width="stretch", key="ch_scatter")
            else:
                ui.pending_chart("scatter", "Risk vs Return", "cagr + annual_volatility", 240)

        c_left, c_mid, c_right = st.columns(3, gap="medium")
        with c_left:
            ga, gb = val("growth_of_1", a), val("growth_of_1", b)
            if ga is None or gb is None:
                ui.pending_chart("cmp-growth", "Growth of $1", "growth_of_1", 260)
            else:
                with ui.chart_card("cmp-growth", "Growth of $1", "",
                                   "The cumulative path of both series.", info="growth_of_1"):
                    st.plotly_chart(plots.line_chart({a_name: ga, b_name: gb},
                                                     hover_fmt=".2f", height=260),
                                    width="stretch", key="ch_cg")
                    ui.chart_footer(ui.legend([(a_name, plots.SERIES[0], "solid"),
                                               (b_name, plots.SERIES[1], "solid")]))
        with c_mid:
            da, db = val("drawdown_series", a), val("drawdown_series", b)
            if da is None or db is None:
                ui.pending_chart("cmp-dd", "Drawdown", "drawdown_series", 260)
            else:
                with ui.chart_card("cmp-dd", "Drawdown", "",
                                   "Who fell deeper, and who recovered faster.", info="drawdown_series"):
                    st.plotly_chart(plots.line_chart({a_name: da, b_name: db}, pct=True,
                                                     height=260),
                                    width="stretch", key="ch_cd")
                    ui.chart_footer(f"Deepest: {a_name} {ui.pct(da.min(), 1)} · "
                                    f"{b_name} {ui.pct(db.min(), 1)}")
        with c_right:
            # kayan korelasyon pandas'ta tek satir, metrics'e koymaya degmedi
            rc = a.rolling(window).corr(b).dropna()
            with ui.chart_card("cmp-corr", "Rolling Correlation", f"{window}d",
                               "The tendency to move together is not constant.", info="correlation"):
                st.plotly_chart(plots.line_chart({"Correlation": rc}, refline=0.0,
                                                 refline_label="0", height=260,
                                                 colors=[plots.SERIES[2]]),
                                width="stretch", key="ch_cc")
                ui.chart_footer(series_footer(rc, lambda v: ui.num(v, 2)))


# --- metrik rehberi ----------------------------------------------------------
# Tearsheet sekmesi bu noktada calismis oldugu icin ui.STATUS dolu: her metrigin
# bu veride hazir mi, bekliyor mu, hata mi verdigi rozet olarak gorunuyor.

with tab_guide:
    ui.html('<h2 class="qt-title">Metric guide</h2><div class="qt-meta">'
            '<span>Every number on the tearsheet, defined once</span><i></i>'
            '<span>Hover the ? on any card for the same note in place</span></div>')
    ui.html('<div class="qt-panel" style="margin:16px 0 4px">'
            '<h4>How to read these</h4><p>'
            'Returns are decimals, not percents: 0.001 is 0.1%. Annualization uses '
            '252 trading days. Benchmark metrics use only the days both series have '
            'in common, so they can rest on a shorter sample than the rest of the '
            'sheet. Longer write-ups, with the traps, live in '
            '<code>docs/metrics.md</code>.</p>'
            f'<p>Sharpe, Sortino and Alpha use an annual risk-free rate of '
            f'<code>{rf_pct:.2f}%</code>. It is not a setting: it is the 1-month '
            f'Treasury bill rate from the Kenneth French daily file, averaged over '
            f'the dates this analysis covers, so it moves with the period you load. '
            f'A positive Alpha is reported as significant only when the CAPM '
            f'regression puts its t-statistic beyond ±1.96.</p></div>')
    ui.guide(ui.STATUS)


# --- hata veren metriklerin ozeti (sayfanin ustundeki yuvaya yazilir) --------

if ui.ERRORS:
    with error_slot:
        items = "".join(
            f'<div style="display:flex;gap:10px;align-items:baseline;'
            f'font:400 12px/1.6 \'IBM Plex Mono\'">'
            f'<span style="color:#c8ccd6">metrics.{fn}()</span>'
            f'<span style="color:#eda1a1">{msg}</span></div>'
            for fn, msg in sorted(ui.ERRORS.items()))
        plural = "metric" if len(ui.ERRORS) == 1 else "metrics"
        ui.html(f'<div class="qt-panel warn" style="border-left-color:#eda1a1;'
                f'margin-bottom:6px"><h4>{len(ui.ERRORS)} {plural} raised an error</h4>'
                f'<p style="margin-bottom:10px">These functions are written but blow up when '
                f'they run. Only their own cards are affected — the rest of the tearsheet '
                f'keeps working.</p>{items}</div>')


# --- alt bilgi ---------------------------------------------------------------
# Herkese acik bir dagitimda gorunmesi gereken satir. Sekmelerin disinda duruyor
# ki hangi sekmede olursan ol sayfanin altinda ayni sey yazsin.

ui.footer([
    "Educational project — not investment advice.",
    "Prices from Yahoo Finance; accuracy and availability are not guaranteed.",
    ("Source on GitHub", "https://github.com/Vielash/S-P500-TearSheet"),
])
