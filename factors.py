"""CAPM ve Fama-French regresyonlari. Bu dosya hazir geliyor ama okumaya deger:
statsmodels ile regresyon kurmanin standart kalibi burada.

Not: repodaki data/ff5_daily.csv SENTETIK ornek veridir. Gercek Ken French
faktorlerini indirmek icin kendi makinende bir kez calistir: python update_factors.py
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.regression.rolling import RollingOLS

FF5_COLS = ["mkt_rf", "smb", "hml", "rmw", "cma"]
FF3_COLS = ["mkt_rf", "smb", "hml"]
TRADING_DAYS = 252


def load_factors(path="data/ff5_daily.csv"):
    """Faktor dosyasini okur. Kolonlar: date, mkt_rf, smb, hml, rmw, cma, rf (ondalik)."""
    return pd.read_csv(path, parse_dates=["date"]).set_index("date").sort_index()


def _ols_table(y, X):
    """OLS kurup videodakine benzer ozet tablo dondurur: (tablo, r_kare).

    add_constant sabit terimi (alpha) ekler; gerisini statsmodels halleder.
    """
    model = sm.OLS(y, sm.add_constant(X)).fit()
    rows = []
    for name in model.params.index:
        is_alpha = name == "const"
        rows.append({
            "factor": "Alpha" if is_alpha else name,
            "coef": model.params[name],
            # sadece alpha yillik anlamli: gunluk sabiti 252 ile carpiyoruz
            "annualized": model.params[name] * TRADING_DAYS if is_alpha else np.nan,
            "t_stat": model.tvalues[name],
            "p_value": model.pvalues[name],
        })
    return pd.DataFrame(rows), float(model.rsquared)


def ff_regression(returns, factors, model="ff5"):
    """Hissenin FAZLA getirisini (r - rf) faktorlere karsi regres eder.

    returns: date indeksli gunluk getiri serisi
    model: "ff5" veya "ff3"
    """
    cols = FF5_COLS if model == "ff5" else FF3_COLS
    df = pd.concat([returns.rename("r"), factors], axis=1, join="inner").dropna()
    y = df["r"] - df["rf"]
    return _ols_table(y, df[cols])


def rolling_ff_betas(returns, factors, window, model="ff5"):
    """Kayan pencerede faktor betalari (videodaki renkli cizgi grafigin verisi).

    Donen DataFrame'de her kolon bir faktorun zaman icindeki katsayisi.
    """
    cols = FF5_COLS if model == "ff5" else FF3_COLS
    df = pd.concat([returns.rename("r"), factors], axis=1, join="inner").dropna()
    y = df["r"] - df["rf"]
    X = sm.add_constant(df[cols])
    res = RollingOLS(y, X, window=window).fit()
    return res.params[cols].dropna()


def capm_regression(returns, benchmark):
    """Basit CAPM: r = alpha + beta * benchmark. (rf'siz sade hali; fark docs'ta)"""
    df = pd.concat([returns.rename("r"), benchmark.rename("b")], axis=1, join="inner").dropna()
    table, r2 = _ols_table(df["r"], df[["b"]])
    table["factor"] = table["factor"].replace({"b": "Beta (Market)"})
    return table, r2
