"""CAPM ve Fama-French regresyonlari. Bu dosya hazir geliyor ama okumaya deger:
statsmodels ile regresyon kurmanin standart kalibi burada.

data/ff5_daily.csv artik GERCEK Ken French verisidir (1963-07-01'den itibaren);
python update_factors.py ile tazelenir. Dosya sentetik bir ornekle degistirilirse
is_synthetic() bunu yakalar ve app.py faktor bolumunu kapatir: gercek getirileri
uydurma faktorlere regres etmek anlamsiz katsayi uretir.
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


def is_synthetic(ff):
    """Faktor dosyasi gercek Ken French serisi mi, sentetik bir ornek mi?

    Gercek gunluk FF5 serisi 1963-07-01'de basliyor; repodaki eski sentetik ornek
    2023'te basliyordu. Tarihe bakmak dosyaya ayri bir bayrak koymaktan daha
    dayanikli: update_factors.py'yi kim calistirirsa calistirsin ayni sonucu verir.
    """
    return ff is None or len(ff) == 0 or ff.index.min().year >= 1990


def risk_free_annual(ff, index, periods_per_year=TRADING_DAYS):
    """Analiz doneminde gecerli olan ortalama risksiz oran, yillik ondalik.

    ff["rf"] Ken French'in gunluk 1 aylik hazine bonosu getirisi. Sharpe, Sortino
    ve capm_alpha imzalari tek bir skaler bekliyor, o yuzden serinin kapsadigi
    gunlerin ortalamasini alip yilliga ceviriyoruz: "bu donemde nakit ne
    kazandirdi" sorusunun tek sayilik cevabi.

    Donen deger (yillik_oran, kapsanan_gun_sayisi). Ortak gun yoksa (None, 0) —
    cagiran taraf o zaman 0'a duser ve bunu kullaniciya soyler.

    Dosya gunluk oranlari dort ondalikla tutuyor, yani tek bir gun kaba; ortalama
    bircok gunu topladigi icin cozunurluk geri geliyor.
    """
    if ff is None or "rf" not in ff.columns:
        return None, 0
    daily = ff["rf"].reindex(index).dropna()
    if daily.empty:
        return None, 0
    return float(daily.mean()) * periods_per_year, len(daily)


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


def capm_regression(returns, benchmark, rf=0.0, periods_per_year=TRADING_DAYS):
    """CAPM: (r - rf) = alpha + beta * (r_b - rf) + eps.

    rf yillik orandir, iceride gunluge boluyoruz. rf=0 verilirse iki taraftan da
    ayni sabit dusuyor, beta degismiyor; alpha ise tam olarak rf=0 varsayimini
    yansitiyor. Arayuz hangi rf ile calistigini kullaniciya yaziyor.
    """
    rf_daily = rf / periods_per_year
    df = pd.concat([returns.rename("r"), benchmark.rename("b")], axis=1, join="inner").dropna()
    table, r2 = _ols_table(df["r"] - rf_daily, (df[["b"]] - rf_daily))
    table["factor"] = table["factor"].replace({"b": "Beta (Market)"})
    return table, r2


def alpha_t_stat(table):
    """Regresyon tablosundaki alpha satirinin t-istatistigi. Yoksa None.

    Kart uzerindeki "anlamli mi" rozeti bunu okuyor: pozitif bir alpha tek basina
    iyi haber degil, sifirdan ayirt edilebiliyor olmasi lazim.
    """
    hit = table[table["factor"] == "Alpha"]
    if hit.empty:
        return None
    t = float(hit["t_stat"].iloc[0])
    return None if pd.isna(t) else t
