"""Tasarim sistemi: token'lar, CSS ve kart bilesenleri.

Kaynak: Claude Design "Quant Tearsheet Redesign" kanvasi (artboard 1i, token sayfasi).
Burada hesaplama yoktur — her sey sunum katmanidir. Metrik degerleri metrics.py'dan
gelir, bu dosya onlari yalnizca bicimlendirip yerlestirir.

Dil sistemi: arayuzun tamami Ingilizce; sayilar Ingilizce bicimli
(ondalik nokta, binlik virgul, ISO tarih, fark birimi "pp").
"""

from contextlib import contextmanager
from html import escape

import streamlit as st

# --- renk token'lari ---------------------------------------------------------
BG = "#1b1f26"        # sayfa arka plani
SURFACE = "#242932"   # kart yuzeyi
PANEL = "#20242c"     # sidebar, tablo basligi, pasif yuzey
LINE = "#333945"      # izgara ve kenarlik
AXIS = "#454c5a"      # eksen
ROW = "#2a2f39"       # tablo satir ayirici
INK = "#f2f4f8"       # birincil metin
INK2 = "#c8ccd6"      # ikincil metin
MUTED = "#8b93a3"     # soluk metin

# kategorik seri renkleri (sabit sira: 1. seri hep mavi, 2. hep somon...)
SERIES = ["#8fb3e8", "#eab088", "#7fd0ab", "#e3c37e", "#e6a3bf"]
ACCENT = SERIES[0]

GOOD, GOOD_BG, GOOD_BD = "#7fd0ab", "#1b2b25", "#27453a"
BAD, BAD_BG, BAD_BD = "#eda1a1", "#2e2224", "#4b3436"
WARN, WARN_BG, WARN_BD = "#e3c37e", "#2d2718", "#4a3f21"

MINUS = "−"  # gercek eksi isareti, tire degil

_TONE = {"good": GOOD, "bad": BAD, "warn": WARN, "neutral": INK, "muted": MUTED}


# --- sayi bicimlendirme (TR) -------------------------------------------------

def _finite(x):
    try:
        return x is not None and x == x and abs(float(x)) != float("inf")
    except (TypeError, ValueError):
        return False


def num(x, nd=2, signed=False, dash="—"):
    """1.21 · +2.8 · −0.34 — gercek eksi isareti, tabular hizalama icin sabit basamak."""
    if not _finite(x):
        return dash
    body = f"{abs(x):.{nd}f}"
    sign = MINUS if x < 0 else ("+" if signed else "")
    return sign + body


def pct(x, nd=2, signed=False, dash="—"):
    """Oran girer, yuzde cikar: 0.248 -> 24.80%"""
    if not _finite(x):
        return dash
    body = f"{abs(x) * 100:.{nd}f}"
    sign = MINUS if x < 0 else ("+" if signed else "")
    return f"{sign}{body}%"


def pp(x, nd=1, dash="—"):
    """Yuzde puan farki: +26.3 pp"""
    if not _finite(x):
        return dash
    return f"{MINUS if x < 0 else '+'}{abs(x) * 100:.{nd}f} pp"


def sign_tone(x):
    if not _finite(x):
        return "muted"
    return "good" if x > 0 else ("bad" if x < 0 else "neutral")


# --- metrik sozlugu ----------------------------------------------------------
# Her giris: (kisa aciklama, tam tanim, formul, yorum araligi).
# Kisa aciklama kartin altinda sabit durur; gerisi "i" rozetinde acilir.
# Metinlerin kaynagi docs/metrics.md.
INFO = {
    "capm_alpha": ("Annual excess return the benchmark's risk cannot explain.",
                   "The intercept of the CAPM regression on excess returns, "
                   "annualized by 252. Both sides are measured above the risk-free "
                   "rate, so alpha depends on which r_f you assume.",
                   "r − r_f = α + β(r_b − r_f) + ε   →   α × 252",
                   "A positive alpha is only news if it is statistically distinct "
                   "from zero: check the t-statistic, not the sign."),
    "beta": ("How much this series moves when the benchmark moves 1%.",
             "The slope of the return against the benchmark return.",
             "cov(r, r_b) / var(r_b)",
             "1.0 moves with the market · >1 sharper · <1 calmer."),
    "sharpe": ("Excess return per unit of total risk.",
               "Mean return above the risk-free rate divided by the standard "
               "deviation of returns — annualized.",
               "(r̄ − r_f) / σ × √252",
               "<0.5 weak · 0.5–1 fair · 1–2 good · >2 rare."),
    "sortino": ("Sharpe, but only downside volatility is penalized.",
                "The denominator holds downside deviation instead of all volatility.",
                "mean(excess) / downside_dev × √252",
                "Usually higher than Sharpe: upside volatility is not punished."),
    "cagr": ("Compound annual growth rate.",
             "What this pace would return if it lasted a full year.",
             "(1 + total_return) ^ (252 / n) − 1",
             "Not the arithmetic mean; growth compounds."),
    "annual_volatility": ("Annualized standard deviation of returns.",
                          "The daily deviation scaled by √252.",
                          "std(r, ddof=1) × √252",
                          "Carries no direction: up and down moves count alike."),
    "max_drawdown": ("Largest peak-to-trough decline.",
                     "The deepest distance from the running high of the cumulative value.",
                     "min( cumulative / cumulative.cummax() − 1 )",
                     "Recovery time is a separate question; depth does not show it."),
    "r_squared": ("Share of the return variance the benchmark explains linearly.",
                  "Coefficient of determination of the CAPM regression. It measures "
                  "one straight line and nothing else.",
                  "1 − SS_res / SS_tot",
                  "Near 1: the benchmark accounts for nearly all the movement. Near 0: "
                  "it accounts for little — which is not the same as independence, "
                  "since a non-linear link would also show up as a low R²."),
    "total_return": ("Total return over the period.",
                     "Returns do not add up; they compound.",
                     "prod(1 + r) − 1", ""),
    "calmar": ("CAGR ÷ |max drawdown|.",
               "Annual return per unit of worst decline.",
               "CAGR / |MDD|", ""),
    "win_rate": ("Share of days that closed positive.", "",
                 "positive days / total days",
                 "Misleading alone: winning often and small is possible."),
    "best_day": ("Best single day of the period.", "", "max(r)", ""),
    "worst_day": ("Worst single day of the period.", "", "min(r)", ""),
    "skewness": ("Asymmetry of the distribution; negative = heavy left tail.", "", "", ""),
    "kurtosis": ("Excess kurtosis; 0 = normal distribution.", "", "", ""),
    "var_historic": ("The loss threshold exceeded on about 1 day in 20.",
                     "The 5th percentile of the daily return distribution: on roughly "
                     "5% of days the loss is worse than this. It is a cut-off, not an "
                     "average — how bad those days get is CVaR's question.",
                     "quantile(r, 0.05)",
                     "Says nothing about the size of the losses beyond it."),
    "cvar_historic": ("Average loss on the days that breach VaR.",
                      "The mean of the returns worse than the VaR threshold — the "
                      "expected loss once a bad day is already a bad day.",
                      "mean(r | r ≤ VaR)",
                      "Always at least as negative as VaR."),
    "correlation": ("How daily returns move with the benchmark.", "", "corr(r, r_b)", ""),
    "tracking_error": ("Annualized volatility of the return difference.", "",
                       "std(r − r_b) × √252", ""),
    "information_ratio": ("Excess return ÷ tracking error.", "", "", ""),
    "up_capture": ("Share captured while the benchmark rises.", "", "", "Above 100% is good."),
    "down_capture": ("Share taken while the benchmark falls.", "", "", "Below 100% is good."),
    "ulcer_index": ("Root mean square of the drawdown series.",
                    "Squares every day's distance from the running high and takes the "
                    "root of the mean. Deep drawdowns weigh far more than shallow "
                    "ones, and a drawdown that persists keeps adding terms — so depth "
                    "and duration both land in one number.",
                    "sqrt( mean( drawdown² ) )",
                    "0 only if the series never leaves its high. Lower is calmer; "
                    "unlike max drawdown it is not decided by a single worst day."),
    "growth_of_1": ("What one unit invested on day one would be worth.",
                    "The cumulative product of daily returns - the equity curve every "
                    "other chart is read against.",
                    "cumprod(1 + r)",
                    "1.00 is break-even; 1.45 means +45% over the whole period."),
    "drawdown_series": ("Distance from the running high, day by day.",
                        "0 while the series sits at a new high, negative on every other "
                        "day. The underwater chart draws this directly.",
                        "cumulative / cumulative.cummax() - 1",
                        "Never above 0. Its minimum is the max drawdown."),
    "monthly_return_table": ("Daily returns compounded into a year x month grid.",
                             "Months are compounded, not summed - returns multiply.",
                             "resample('ME'): prod(1 + r) - 1, then pivot",
                             "Shows seasonality and streaks a single number hides."),
    "rolling_volatility": ("Volatility measured over a moving window.",
                           "The same annualized standard deviation, recomputed on the "
                           "last N days at every point.",
                           "r.rolling(window).std(ddof=1) x sqrt(252)",
                           "Rising means a noisier regime, not necessarily a worse one."),
    "rolling_sharpe": ("Sharpe measured over a moving window.",
                       "Shows whether the headline Sharpe came from a steady edge or "
                       "from one lucky stretch.",
                       "rolling mean(excess) / rolling std x sqrt(252)",
                       "One tall spike in an otherwise flat line is a warning."),
    "rolling_beta": ("Beta measured over a moving window.",
                     "Sensitivity to the benchmark is not constant; this is how it drifts.",
                     "rolling cov(r, r_b) / rolling var(r_b)",
                     "A moving beta means the single CAPM beta averages several regimes."),
}

# Metrik rehberi sekmesinin duzeni: (bolum basligi, alt cumle, fonksiyon adlari).
# Sira docs/metrics.md ile ayni; yeni bir metrik eklenince buraya da girmeli.
GUIDE = [
    ("Performance", "What it returned, and how much risk was taken to get there",
     ["total_return", "cagr", "growth_of_1", "annual_volatility",
      "sharpe", "sortino", "calmar"]),
    ("Drawdown", "How deep the falls went, and how long they lasted",
     ["drawdown_series", "max_drawdown", "ulcer_index"]),
    ("Distribution", "The shape of the daily returns the averages hide",
     ["win_rate", "best_day", "worst_day", "skewness", "kurtosis",
      "var_historic", "cvar_historic", "monthly_return_table"]),
    ("Versus the benchmark", "What the market explains, and what it does not",
     ["beta", "capm_alpha", "r_squared", "correlation", "tracking_error",
      "information_ratio", "up_capture", "down_capture"]),
    ("Rolling", "The same measurements over a moving window",
     ["rolling_volatility", "rolling_sharpe", "rolling_beta"]),
]

# Fonksiyon adi -> arayuzde gorunen baslik.
NAMES = {
    "total_return": "Total Return", "cagr": "CAGR", "growth_of_1": "Growth of 1",
    "annual_volatility": "Annualized Volatility", "sharpe": "Sharpe Ratio",
    "sortino": "Sortino Ratio", "calmar": "Calmar Ratio",
    "drawdown_series": "Drawdown Series", "max_drawdown": "Max Drawdown",
    "ulcer_index": "Ulcer Index", "win_rate": "Win Rate", "best_day": "Best Day",
    "worst_day": "Worst Day", "skewness": "Skewness", "kurtosis": "Excess Kurtosis",
    "var_historic": "Historical VaR (5%)", "cvar_historic": "Historical CVaR (5%)",
    "monthly_return_table": "Monthly Return Table", "beta": "Beta",
    "capm_alpha": "Annualized Alpha", "r_squared": "R² (CAPM)",
    "correlation": "Correlation", "tracking_error": "Tracking Error",
    "information_ratio": "Information Ratio", "up_capture": "Up Capture",
    "down_capture": "Down Capture", "rolling_volatility": "Rolling Volatility",
    "rolling_sharpe": "Rolling Sharpe", "rolling_beta": "Rolling Beta",
}


# Her metrigin bu calismadaki durumu: {fonksiyon_adi: "ready" | "pending" | "error"}.
# app.py'daki val() dolduruyor, metrik rehberi sekmesi okuyor. Hic cagrilmamis bir metrik
# burada yoktur (orn. benchmark secili degilken beta) ve rehberde rozetsiz gorunur.
STATUS = {}

# metrics.py'daki bir fonksiyon calisti ama hata firlattiysa mesaji buraya dusuyor;
# {fonksiyon_adi: "NameError: ..."}. app.py her calismada temizler.
# "Hazir degil" ile "hata verdi" ayri durumlardir: biri bekleyen adim, digeri bozuk kod.
ERRORS = {}


def note_of(key):
    return INFO.get(key, ("", "", "", ""))[0]


def info_dot(key, label=""):
    """'?' imleci: uzerine gelince tanim + formul + yorum araligini acan balon.

    Tarayicinin kendi title ipucu yerine CSS balonu: gecikmesiz aciliyor, uc parcayi
    ayri satirlarda gosteriyor ve tasarim token'larini kullaniyor. tabindex sayesinde
    dokunmatik cihazda dokununca da aciliyor.
    """
    short, defn, formula, bands = INFO.get(key, ("", "", "", ""))
    body = defn or short
    if not (body or formula or bands):
        return ""
    inner = f'<b>{escape(label or NAMES.get(key, key))}</b>'
    if body:
        inner += f"<p>{escape(body)}</p>"
    if formula:
        inner += f"<code>{escape(formula)}</code>"
    if bands:
        inner += f"<em>{escape(bands)}</em>"
    return f'<span class="qt-i" tabindex="0">?<span class="qt-tip">{inner}</span></span>'


# --- CSS ---------------------------------------------------------------------

CSS = """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

html, body, .stApp, [data-testid="stAppViewContainer"] {
  background: #1b1f26;
  font-family: 'IBM Plex Sans', system-ui, sans-serif;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stMain"] .block-container { padding: 1.4rem 2rem 5rem; max-width: 1480px; }

/* --- sidebar --- */
section[data-testid="stSidebar"] { background: #20242c; border-right: 1px solid #333945; }

/* --- kart yuzeyleri: st.container(key="card-...") / ("pending-...") --- */
div[class*="st-key-card-"] {
  background: #242932; border: 1px solid #333945; border-radius: 6px;
  padding: 16px 18px 12px;
}
div[class*="st-key-pending-"] {
  background: #20242c; border: 1px dashed #454c5a; border-radius: 6px;
  padding: 18px 20px;
}

/* --- tipografi --- */
h1, h2, h3, h4 { font-family: 'IBM Plex Sans'; color: #f2f4f8; letter-spacing: -.01em; }
[data-testid="stMarkdownContainer"] p { color: #c8ccd6; }
code, kbd { font-family: 'IBM Plex Mono'; background: #20242c; color: #c8ccd6;
            border: 1px solid #333945; border-radius: 3px; padding: 1px 5px; }

/* --- bolum basligi --- */
.qt-sec { display: flex; align-items: baseline; gap: 12px; margin: 30px 0 14px; }
.qt-sec h3 { margin: 0; font: 600 12px/1 'IBM Plex Mono'; letter-spacing: .1em;
             color: #c8ccd6; text-transform: uppercase; white-space: nowrap; }
.qt-sec span { font: 400 12px/1.4 'IBM Plex Sans'; color: #8b93a3; }
.qt-sec i { flex: 1; height: 1px; background: #333945; min-width: 20px; }

/* --- izgaralar --- */
.qt-grid { display: grid; gap: 12px; margin-bottom: 4px; }
.qt-grid-4 { grid-template-columns: repeat(4, 1fr); }
.qt-grid-3 { grid-template-columns: repeat(3, 1fr); gap: 16px; }
.qt-grid-2 { grid-template-columns: repeat(2, 1fr); gap: 16px; }
.qt-grid-5 { grid-template-columns: repeat(5, 1fr); }

/* --- metrik karti: etiket / deger + rozet / tek satir aciklama --- */
.qt-card { background: #242932; border: 1px solid #333945; border-radius: 6px;
           padding: 15px 16px; display: flex; flex-direction: column; gap: 7px; }
.qt-card.pending { background: #20242c; border: 1px dashed #454c5a; }
.qt-card-top { display: flex; justify-content: space-between; align-items: center; gap: 8px; }
.qt-card-label { font: 500 11.5px/1.3 'IBM Plex Sans'; color: #c8ccd6; }
.qt-card.pending .qt-card-label { color: #8b93a3; }
.qt-card-head { display: flex; align-items: center; gap: 6px; min-width: 0; }
.qt-i { position: relative; display: inline-block; width: 15px; height: 15px; flex: none;
        border: 1px solid #454c5a; border-radius: 50%; font: 600 10px/14px 'IBM Plex Mono';
        color: #8b93a3; text-align: center; cursor: help; vertical-align: middle; }
.qt-i:hover, .qt-i:focus { border-color: #8fb3e8; color: #8fb3e8; outline: none; }

/* aciklama balonu: '?' uzerine gelince acilir, karti asar (kart z-index alir) */
.qt-tip { display: none; position: absolute; z-index: 60; top: 23px; right: -7px; width: 272px;
          text-align: left; cursor: auto; background: #1b1f26; border: 1px solid #454c5a;
          border-radius: 6px; padding: 13px 15px; box-shadow: 0 12px 30px rgba(0,0,0,.6); }
.qt-i:hover .qt-tip, .qt-i:focus .qt-tip { display: block; }
.qt-tip b { display: block; margin-bottom: 7px; font: 600 12px/1.3 'IBM Plex Sans'; color: #f2f4f8; }
.qt-tip p { margin: 0 0 8px; font: 400 11.5px/1.55 'IBM Plex Sans'; color: #c8ccd6; }
.qt-tip code { display: block; margin-bottom: 8px; padding: 6px 8px; border-radius: 4px;
               background: #242932; border: 1px solid #333945; word-break: break-word;
               font: 500 11px/1.5 'IBM Plex Mono'; color: #8fb3e8; }
.qt-tip em { display: block; padding-top: 8px; border-top: 1px solid #333945; font-style: normal;
             font: 400 11px/1.5 'IBM Plex Sans'; color: #8b93a3; }
.qt-card, .qt-gcard { position: relative; }
.qt-card:hover, .qt-ch:hover, .qt-empty:hover { z-index: 40; }
.qt-ch h4 { display: flex; align-items: center; gap: 7px; }
.qt-empty b { display: inline-flex; align-items: center; gap: 7px; }

/* --- metrik rehberi kartlari --- */
.qt-gcard { background: #242932; border: 1px solid #333945; border-radius: 6px;
            padding: 16px 18px; display: flex; flex-direction: column; gap: 9px; }
.qt-gtop { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
.qt-gtop b { font: 600 13.5px/1.3 'IBM Plex Sans'; color: #f2f4f8; }
.qt-gcard p { margin: 0; font: 400 12px/1.6 'IBM Plex Sans'; color: #c8ccd6; }
.qt-gcard code { padding: 8px 10px; border-radius: 4px; background: #1b1f26;
                 border: 1px solid #333945; word-break: break-word;
                 font: 500 11.5px/1.5 'IBM Plex Mono'; color: #8fb3e8; }
.qt-gcard em { font-style: normal; font: 400 11.5px/1.55 'IBM Plex Sans'; color: #8b93a3; }
.qt-gfn { margin-top: auto; padding-top: 10px; border-top: 1px solid #2a2f39;
          font: 400 10.5px/1 'IBM Plex Mono'; color: #8b93a3; }
.qt-card-val { display: flex; align-items: baseline; gap: 7px; flex-wrap: wrap; min-height: 26px; }
.qt-val { font: 600 26px/1 'IBM Plex Mono'; font-variant-numeric: tabular-nums; color: #f2f4f8; }
.qt-chip { font: 500 10px/1 'IBM Plex Mono'; color: #8b93a3; }
.qt-note { font: 400 11px/1.45 'IBM Plex Sans'; color: #8b93a3; }
.qt-note code { font-size: 10.5px; }
.qt-skel { height: 8px; border-radius: 4px; align-self: center; display: inline-block;
           background: repeating-linear-gradient(90deg, #333945 0 6px, #2d323c 6px 12px); }

/* --- rozetler: renk + ok/kelime birlikte --- */
.qt-badge { font: 500 10px/1 'IBM Plex Mono'; padding: 4px 6px; border-radius: 3px;
            white-space: nowrap; }
.qt-badge.good { color: #7fd0ab; background: #1b2b25; border: 1px solid #27453a; }
.qt-badge.bad  { color: #eda1a1; background: #2e2224; border: 1px solid #4b3436; }
.qt-badge.warn { color: #e3c37e; background: #2d2718; border: 1px solid #4a3f21; }
.qt-badge.neutral { color: #c8ccd6; background: #242932; border: 1px solid #333945; }
.qt-badge.sel  { color: #8fb3e8; background: #1a2231; border: 1px solid #2b3c56; }

/* --- grafik kartinin basligi ve alt seridi --- */
.qt-ch { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; }
.qt-ch h4 { margin: 0; font: 600 14px/1.3 'IBM Plex Sans'; color: #f2f4f8; }
.qt-ch span { font: 400 11px/1 'IBM Plex Mono'; color: #8b93a3; white-space: nowrap; }
.qt-cd { margin: 4px 0 0; font: 400 11.5px/1.45 'IBM Plex Sans'; color: #8b93a3; }
.qt-cf { margin-top: 2px; padding-top: 8px; border-top: 1px solid #333945;
         font: 400 11px/1.6 'IBM Plex Mono'; color: #c8ccd6; display: flex;
         gap: 16px; flex-wrap: wrap; align-items: center; }
.qt-key { display: inline-flex; align-items: center; gap: 7px; }
.qt-key b { display: inline-block; width: 16px; height: 2px; border-radius: 1px; }

/* --- liste kartlari (ayrintili metrikler) --- */
.qt-list { background: #242932; border: 1px solid #333945; border-radius: 6px; overflow: hidden; }
.qt-list-head { padding: 14px 18px; border-bottom: 1px solid #333945;
                display: flex; flex-direction: column; gap: 3px; }
.qt-list-head b { font: 600 13px/1.3 'IBM Plex Sans'; color: #f2f4f8; }
.qt-list-head span { font: 400 11px/1.4 'IBM Plex Sans'; color: #8b93a3; }
.qt-row { display: flex; justify-content: space-between; align-items: center; gap: 12px;
          padding: 11px 18px; border-bottom: 1px solid #2a2f39; }
.qt-row:last-child { border-bottom: none; }
.qt-row-l { font: 400 12px/1.4 'IBM Plex Sans'; color: #c8ccd6; }
.qt-row-l small { display: block; font-size: 10.5px; color: #8b93a3; }
.qt-row-v { font: 600 14px/1 'IBM Plex Mono'; font-variant-numeric: tabular-nums;
            white-space: nowrap; }

/* --- tablolar: sayilar saga dayali ve mono, zebra yok --- */
.qt-tbl { background: #242932; border: 1px solid #333945; border-radius: 6px; overflow: hidden; }
.qt-tbl-head { padding: 13px 16px; border-bottom: 1px solid #333945; display: flex;
               justify-content: space-between; align-items: baseline; gap: 10px; }
.qt-tbl-head b { font: 600 13px/1 'IBM Plex Sans'; color: #f2f4f8; }
.qt-tbl-head span { font: 500 11px/1 'IBM Plex Mono'; color: #c8ccd6; }
.qt-tr { display: grid; align-items: center; border-bottom: 1px solid #2a2f39;
         font: 400 11.5px/1.4 'IBM Plex Mono'; color: #c8ccd6; }
.qt-tr.head { background: #20242c; border-bottom: 1px solid #333945;
              font: 600 10px/1.2 'IBM Plex Mono'; letter-spacing: .06em; color: #8b93a3; }
.qt-tr:last-child { border-bottom: none; }
.qt-tr > div { padding: 9px 12px; }
.qt-tr > div.r { text-align: right; font-variant-numeric: tabular-nums; }
.qt-tr > div.win { background: rgba(143,179,232,.12); color: #f2f4f8; }
.qt-tr small { color: #8b93a3; font-family: 'IBM Plex Sans'; font-size: 10px; }
.qt-tbl-foot { padding: 10px 14px; border-top: 1px solid #333945;
               font: 400 10.5px/1.5 'IBM Plex Sans'; color: #8b93a3;
               display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; }

/* --- bilgi / uyari panelleri --- */
.qt-panel { background: #20242c; border: 1px solid #333945; border-left: 3px solid #8fb3e8;
            border-radius: 6px; padding: 16px 20px; }
.qt-panel.warn { border-left-color: #eab088; background: #242932; }
.qt-panel h4 { margin: 0 0 8px; font: 600 15px/1.3 'IBM Plex Sans'; color: #f2f4f8; }
.qt-panel p { margin: 0; font: 400 13px/1.6 'IBM Plex Sans'; color: #c8ccd6; }
.qt-chips { display: flex; gap: 7px; flex-wrap: wrap; margin-top: 8px; }
.qt-tag { font: 500 11.5px/1 'IBM Plex Mono'; padding: 6px 9px; border-radius: 3px;
          background: #20242c; border: 1px solid #333945; color: #8b93a3; }
.qt-tag.ok { color: #7fd0ab; background: #1b2b25; border-color: #27453a; }
.qt-tag.miss { color: #eda1a1; background: #2e2224; border-color: #4b3436; }
.qt-sub { font: 600 11px/1 'IBM Plex Mono'; letter-spacing: .08em; color: #8b93a3;
          display: block; margin-bottom: 8px; }

/* --- bos / hazir degil blogu --- */
.qt-empty { display: flex; flex-direction: column; align-items: center; justify-content: center;
            text-align: center; gap: 11px; padding: 26px 20px; }
.qt-empty .ring { width: 38px; height: 38px; border-radius: 50%; border: 1px dashed #e3c37e;
                  display: flex; align-items: center; justify-content: center;
                  font: 600 15px/1 'IBM Plex Mono'; color: #e3c37e; }
.qt-empty b { font: 600 14px/1.3 'IBM Plex Sans'; color: #f2f4f8; }
.qt-empty p { margin: 0; max-width: 380px; font: 400 12px/1.55 'IBM Plex Sans'; color: #8b93a3; }

/* --- baslik ve meta serit --- */
.qt-meta { display: flex; gap: 12px; align-items: center; flex-wrap: wrap;
           font: 400 12px/1.4 'IBM Plex Mono'; color: #c8ccd6; margin-top: 8px; }
.qt-meta i { width: 3px; height: 3px; border-radius: 50%; background: #454c5a; }

/* --- sayfa alt bilgisi: sorumluluk reddi + kaynak --- */
.qt-foot { display: flex; gap: 12px; align-items: center; flex-wrap: wrap;
           margin: 34px 0 6px; padding-top: 16px; border-top: 1px solid #333945;
           font: 400 11px/1.5 'IBM Plex Mono'; color: #8b93a3; }
.qt-foot i { width: 3px; height: 3px; border-radius: 50%; background: #454c5a; }
.qt-foot a { color: #8b93a3; text-decoration: underline; text-underline-offset: 2px; }
.qt-foot a:hover { color: #8fb3e8; }
.qt-title { margin: 0; font: 600 30px/1.1 'IBM Plex Sans'; color: #f2f4f8; letter-spacing: -.02em; }
.qt-title small { color: #8b93a3; font-weight: 400; font-size: 30px; }

/* --- sidebar dosya rozeti --- */
.qt-file { background: #1b1f26; border: 1px solid #333945; border-radius: 5px;
           padding: 12px 14px; display: flex; flex-direction: column; gap: 6px; }
.qt-file b { font: 500 12px/1.3 'IBM Plex Mono'; color: #f2f4f8;
             display: flex; align-items: center; gap: 8px; word-break: break-all; }
.qt-file b em { width: 6px; height: 6px; flex: none; border-radius: 50%; background: #7fd0ab; }
.qt-file span { font: 400 11px/1.4 'IBM Plex Mono'; color: #8b93a3; }

/* --- streamlit bilesenleri --- */
.stTabs [data-baseweb="tab-list"] { gap: 2px; border-bottom: 1px solid #333945; }
.stTabs [data-baseweb="tab"] { font: 500 13px/1 'IBM Plex Sans'; color: #8b93a3; padding: 11px 18px; }
.stTabs [aria-selected="true"] { color: #f2f4f8; font-weight: 600; }
.stTabs [data-baseweb="tab-highlight"] { background: #8fb3e8; }

.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
  font: 500 13px/1 'IBM Plex Sans'; background: transparent; color: #c8ccd6;
  border: 1px solid #454c5a; border-radius: 5px;
}
.stButton > button:hover, .stDownloadButton > button:hover {
  border-color: #c8ccd6; color: #f2f4f8; background: transparent;
}
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"] {
  background: #8fb3e8; color: #1b1f26; border: none; font-weight: 600;
}
.stButton > button[kind="primary"]:hover { background: #a6c4f0; color: #1b1f26; }
.stButton > button:disabled, .stDownloadButton > button:disabled {
  background: #242932; color: #8b93a3; border-color: #333945;
}

[data-baseweb="select"] > div { background: #1b1f26; border-color: #454c5a; border-radius: 4px; }
[data-testid="stWidgetLabel"] p { font: 500 11.5px/1.3 'IBM Plex Sans'; color: #c8ccd6; }

[data-testid="stFileUploaderDropzone"] {
  background: #20242c; border: 2px dashed #454c5a; border-radius: 8px; padding: 30px 26px;
}
[data-testid="stFileUploaderDropzone"]:hover { border-color: #8fb3e8; }
[data-testid="stFileUploaderDropzoneInstructions"] span {
  font: 600 15px/1.3 'IBM Plex Sans'; color: #f2f4f8;
}

[data-testid="stExpander"] details { border: 1px solid #333945; border-radius: 6px;
                                     background: #20242c; }
[data-testid="stExpander"] summary { font: 600 13px/1 'IBM Plex Sans'; color: #f2f4f8; }

[data-testid="stCaptionContainer"] p { font: 400 11px/1.5 'IBM Plex Sans'; color: #8b93a3; }
hr { border-color: #333945; }
[data-testid="stSegmentedControl"] button { font: 500 11px/1 'IBM Plex Mono'; }

/* --- dar ekran: kart izgarasi 4->2->1, grafik izgarasi 2->1 --- */
@media (max-width: 1200px) {
  .qt-grid-4 { grid-template-columns: repeat(2, 1fr); }
  .qt-grid-3, .qt-grid-5 { grid-template-columns: repeat(2, 1fr); }
  [data-testid="stMain"] [data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
  [data-testid="stMain"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
    flex: 1 1 100%; min-width: 100%;
  }
}
@media (max-width: 820px) {
  .qt-grid-4, .qt-grid-3, .qt-grid-2, .qt-grid-5 { grid-template-columns: 1fr; }
  .qt-title, .qt-title small { font-size: 24px; }
}
"""


def inject_css():
    st.markdown("<style>" + CSS + "</style>", unsafe_allow_html=True)


def html(markup):
    st.markdown(markup, unsafe_allow_html=True)


# --- bilesenler --------------------------------------------------------------

def section(number, title, subtitle=""):
    """01 · PERFORMANS — numarali bolum basligi, yaninda tek cumlelik amac."""
    head = f"{escape(number)} · {escape(title)}" if number else escape(title)
    html(f'<div class="qt-sec"><h3>{head}</h3>'
         f'<span>{escape(subtitle)}</span><i></i></div>')


def badge(text, tone="neutral"):
    return f'<span class="qt-badge {tone}">{escape(text)}</span>'


def metric_card(label, value, note="", *, tone="neutral", badge_text=None,
                badge_tone="good", chip=None, info_key=None):
    """Metrik karti: etiket + "i" · deger + rozet · tek satir aciklama."""
    i = info_dot(info_key, label) if info_key else ""
    if badge_text:
        extra = badge(badge_text, badge_tone)
    elif chip:
        extra = f'<span class="qt-chip">{escape(chip)}</span>'
    else:
        extra = ""
    return (f'<div class="qt-card"><div class="qt-card-top">'
            f'<span class="qt-card-label">{escape(label)}</span>{i}</div>'
            f'<div class="qt-card-val"><span class="qt-val" style="color:{_TONE[tone]}">'
            f'{value}</span>{extra}</div>'
            f'<span class="qt-note">{note}</span></div>')


def pending_card(label, fn_name):
    """Hazir degil karti: kesikli kenar, amber rozet, eksik fonksiyonun adi.

    Bu bir hata degil, ogrenme projesinin dogal adimi — asla kirmizi, asla hata dili.
    Fonksiyon yazilmis ama hata firlatmissa kart hata varyantina doner.
    """
    head = (f'<span class="qt-card-head"><span class="qt-card-label">{escape(label)}</span>'
            f'{info_dot(fn_name, label)}</span>')
    if fn_name in ERRORS:
        return (f'<div class="qt-card pending" style="border-color:#4b3436">'
                f'<div class="qt-card-top">{head}'
                f'{badge("ERROR", "bad")}</div>'
                f'<div class="qt-card-val"><span class="qt-skel" style="width:52px">'
                f'</span></div>'
                f'<span class="qt-note"><code>metrics.{fn_name}()</code> ran but raised:'
                f'<br><span style="color:#eda1a1">{escape(ERRORS[fn_name])}</span>'
                f'</span></div>')
    return (f'<div class="qt-card pending"><div class="qt-card-top">{head}'
            f'{badge("NOT READY", "warn")}</div>'
            f'<div class="qt-card-val"><span class="qt-skel" style="width:52px"></span></div>'
            f'<span class="qt-note"><code>metrics.{fn_name}()</code> is not written yet — '
            f'this fills in on its own once it is.</span></div>')


def card_grid(cards, cols=4):
    html(f'<div class="qt-grid qt-grid-{cols}">' + "".join(cards) + "</div>")


@contextmanager
def chart_card(key, title, right="", desc="", info=None):
    """Grafik karti: baslik -> aciklama -> grafik -> alt bilgi seridi.

    info verilirse basligin yanina metrik sozlugunden beslenen '?' imleci gelir.
    """
    box = st.container(key=f"card-{key}")
    with box:
        dot = info_dot(info) if info else ""
        html(f'<div class="qt-ch"><h4>{title}{dot}</h4><span>{escape(right)}</span></div>'
             + (f'<p class="qt-cd">{escape(desc)}</p>' if desc else ""))
        yield box


def chart_footer(text):
    html(f'<div class="qt-cf">{text}</div>')


def legend(items):
    """Seri anahtari: renk + desen + isim. Renk tek basina anlam tasimaz."""
    out = []
    for name, color, dash in items:
        style = (f"background:{color}" if dash == "solid"
                 else f"height:0;border-top:2px {dash} {color}")
        out.append(f'<span class="qt-key"><b style="{style}"></b>{escape(name)}</span>')
    return "".join(out)


def pending_chart(key, title, fn_name, height=300):
    """Eksik bir grafigin yerini tutan blok — grafik kartiyla ayni olculerde."""
    with st.container(key=f"pending-{key}"):
        if fn_name in ERRORS:
            html(f'<div class="qt-empty" style="min-height:{height}px">'
                 f'<div class="ring" style="border-color:#eda1a1;color:#eda1a1">!</div>'
                 f'<b>{escape(title)} raised an error</b>'
                 f'<p><code>metrics.{fn_name}()</code> ran but raised:<br>'
                 f'<span style="color:#eda1a1">{escape(ERRORS[fn_name])}</span></p>'
                 f'{badge("ERROR", "bad")}</div>')
            return
        html(f'<div class="qt-empty" style="min-height:{height}px">'
             f'<div class="ring">?</div>'
             f'<b>{escape(title)} is not ready yet{info_dot(fn_name, title)}</b>'
             f'<p>This chart appears on its own once <code>metrics.{fn_name}()</code> is '
             f'written. Until then the rest of the tearsheet keeps working.</p>'
             f'{badge("NOT READY", "warn")}</div>')


def stat_list(title, subtitle, rows):
    """Ayrintili metrik karti.

    rows: (etiket, alt aciklama, deger, ton) — deger None ise (etiket, fonksiyon_adi,
    None, None) olarak okunur ve "hazir degil" satiri cizilir.
    """
    out = [f'<div class="qt-list"><div class="qt-list-head"><b>{title}</b>'
           f'<span>{escape(subtitle)}</span></div>']
    for label, sub, value, tone in rows:
        if value is None:
            state = ('<span style="color:#eda1a1">ran but raised an error</span>'
                     if sub in ERRORS else "is not written yet")
            out.append(f'<div class="qt-row">'
                       f'<span class="qt-row-l" style="color:#8b93a3">{escape(label)}'
                       f'<small><code>metrics.{sub}()</code> {state}</small></span>'
                       f'<span class="qt-skel" style="width:36px"></span></div>')
        else:
            out.append(f'<div class="qt-row"><span class="qt-row-l">{escape(label)}'
                       f'<small>{sub}</small></span>'
                       f'<span class="qt-row-v" style="color:{_TONE[tone]}">{value}</span>'
                       f'</div>')
    out.append("</div>")
    return "".join(out)


def guide(status=None):
    """Metrik rehberi sekmesi: her metrigin tanimi, formulu ve yorum araligi.

    status: {fonksiyon_adi: "ready"|"pending"|"error"} — app.py'daki val() bu
    calismada hangi metrigin dolu oldugunu biliyor, rozet oradan geliyor.
    """
    status = status or {}
    tone = {"ready": ("READY", "good"), "pending": ("NOT READY", "warn"),
            "error": ("ERROR", "bad")}
    for title, subtitle, keys in GUIDE:
        section("", title, subtitle)
        cards = []
        for k in keys:
            short, defn, formula, bands = INFO.get(k, ("", "", "", ""))
            state = "error" if k in ERRORS else status.get(k)
            chip = badge(*tone[state]) if state in tone else ""
            body = f"<p>{escape(defn or short)}</p>" if (defn or short) else ""
            if defn and short:
                body = f"<p>{escape(short)}</p><p>{escape(defn)}</p>"
            out = [f'<div class="qt-gcard"><div class="qt-gtop">'
                   f'<b>{escape(NAMES.get(k, k))}</b>{chip}</div>{body}']
            if formula:
                out.append(f"<code>{escape(formula)}</code>")
            if bands:
                out.append(f"<em>{escape(bands)}</em>")
            out.append(f'<span class="qt-gfn">metrics.{k}()</span></div>')
            cards.append("".join(out))
        card_grid(cards, 3)


def footer(items):
    """Sayfanin altindaki tek satir. items: metin ya da (metin, url) ikilileri.

    Herkese acik bir dagitimda bu satirin gorunmesi onemli: uygulama egitim
    amaclidir ve urettigi sayilar yatirim tavsiyesi degildir.
    """
    parts = []
    for it in items:
        if isinstance(it, tuple):
            text, url = it
            parts.append(f'<a href="{escape(url)}" target="_blank" rel="noopener">'
                         f'{escape(text)}</a>')
        else:
            parts.append(f"<span>{escape(it)}</span>")
    html('<div class="qt-foot">' + "<i></i>".join(parts) + "</div>")
