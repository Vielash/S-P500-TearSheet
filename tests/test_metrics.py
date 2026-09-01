"""Her metrigin dogrulugunu kontrol eden testler.

Calistir:  pytest -v          (hepsi)
           pytest -v -k sharpe (sadece sharpe)

Yazilmamis fonksiyonlarin testleri SKIP olur; sen yazdikca yesile doner.
Iki tur test var:
- elle kontrol edilebilen kucuk seriler (dogrulamayi kagit ustunde yapabilirsin)
- ornek veri (data/sample_returns.csv) uzerinde sabitlenmis beklenen degerler
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import data
import metrics as m

ROOT = Path(__file__).parent.parent
approx = pytest.approx


def call(fn, *args, **kwargs):
    """Fonksiyon henuz yazilmadiysa testi atla, yazildiysa sonucu dondur."""
    try:
        return fn(*args, **kwargs)
    except NotImplementedError:
        pytest.skip(f"{fn.__name__} henuz yazilmadi")


# --- kucuk el serileri ---

# uc gunluk getiri: %10, -%5, %2
R3 = pd.Series([0.10, -0.05, 0.02],
               index=pd.bdate_range("2023-01-02", periods=3))

# esit araliklarla artan getiri: mean=0.02, std(ddof=1)=0.01
Z3 = pd.Series([0.01, 0.02, 0.03],
               index=pd.bdate_range("2023-01-02", periods=3))

# benchmark'in tam iki kati hareket eden seri (beta=2, korelasyon=1)
B4 = pd.Series([0.005, 0.010, -0.015, 0.020],
               index=pd.bdate_range("2023-01-02", periods=4))
R4 = 2 * B4


@pytest.fixture(scope="module")
def sample():
    """Ornek veriden AAPL ve SPY, ortak gunlere hizali."""
    df = data.load_returns(ROOT / "data" / "sample_returns.csv")
    wide = data.returns_wide(df)
    return data.align_pair(wide, "AAPL", "SPY")


# 1) getiri

def test_total_return():
    # 1.10 * 0.95 * 1.02 - 1 = 0.0659
    assert call(m.total_return, R3) == approx(0.0659)


def test_total_return_sample(sample):
    r, _ = sample
    assert call(m.total_return, r) == approx(1.2345575876, rel=1e-6)


def test_growth_of_1():
    g = call(m.growth_of_1, R3)
    assert list(g) == approx([1.10, 1.045, 1.0659])
    assert isinstance(g, pd.Series)


def test_cagr():
    # iki donem, yilda 2 donem varsayimi: toplam getiri 0.21 -> yillik da 0.21
    r = pd.Series([0.10, 0.10])
    assert call(m.cagr, r, periods_per_year=2) == approx(0.21)


def test_cagr_sample(sample):
    r, _ = sample
    assert call(m.cagr, r) == approx(0.2388516795, rel=1e-6)


# 2) risk

def test_annual_volatility():
    assert call(m.annual_volatility, Z3) == approx(0.01 * np.sqrt(252))


def test_annual_volatility_sample(sample):
    r, _ = sample
    assert call(m.annual_volatility, r) == approx(0.2950113916, rel=1e-6)


def test_drawdown_series():
    dd = call(m.drawdown_series, R3)
    # zirve 1.10'da; sonraki gunler zirveye gore: 1.045/1.10-1 ve 1.0659/1.10-1
    assert list(dd) == approx([0.0, 1.045 / 1.10 - 1, 1.0659 / 1.10 - 1])
    assert (dd <= 0).all()


def test_max_drawdown():
    assert call(m.max_drawdown, R3) == approx(1.045 / 1.10 - 1)


def test_max_drawdown_sample(sample):
    r, _ = sample
    assert call(m.max_drawdown, r) == approx(-0.2480017803, rel=1e-6)


# 3) riske gore getiri

def test_sharpe():
    assert call(m.sharpe, Z3) == approx(0.02 / 0.01 * np.sqrt(252))


def test_sharpe_sample(sample):
    r, _ = sample
    assert call(m.sharpe, r) == approx(0.8733018277, rel=1e-6)
    # rf verilince dusmeli
    assert call(m.sharpe, r, rf=0.04) == approx(0.7377138431, rel=1e-6)


def test_sortino():
    r = pd.Series([0.05, -0.03, 0.01])
    # excess = r (rf=0), asagi taraf: sadece -0.03
    # downside = sqrt(0.03**2 / 3), sortino = mean/downside * sqrt(252)
    expected = 0.01 / np.sqrt(0.03 ** 2 / 3) * np.sqrt(252)
    assert call(m.sortino, r) == approx(expected)


def test_sortino_sample(sample):
    r, _ = sample
    assert call(m.sortino, r) == approx(1.3112174061, rel=1e-6)


def test_calmar_sample(sample):
    r, _ = sample
    assert call(m.calmar, r) == approx(0.9631046970, rel=1e-6)
    # tanim geregi cagr / |maxdd| ile tutarli olmali
    cagr_v = call(m.cagr, r)
    mdd_v = call(m.max_drawdown, r)
    assert call(m.calmar, r) == approx(cagr_v / abs(mdd_v))


# 4) dagilim ve gunler

def test_win_rate():
    assert call(m.win_rate, R3) == approx(2 / 3)


def test_best_worst_day():
    assert call(m.best_day, R3) == approx(0.10)
    assert call(m.worst_day, R3) == approx(-0.05)


def test_skewness_sample(sample):
    r, _ = sample
    assert call(m.skewness, r) == approx(0.1996369011, rel=1e-6)


def test_kurtosis_sample(sample):
    r, _ = sample
    assert call(m.kurtosis, r) == approx(2.8778878754, rel=1e-6)


def test_var_historic_sample(sample):
    r, _ = sample
    assert call(m.var_historic, r) == approx(-0.0266853875, rel=1e-6)


def test_cvar_historic_sample(sample):
    r, _ = sample
    cvar = call(m.cvar_historic, r)
    assert cvar == approx(-0.0411610215, rel=1e-6)
    # CVaR, VaR esiginin altindaki gunlerin ortalamasi: daha kotu olmali
    assert cvar <= call(m.var_historic, r)


def test_monthly_return_table():
    # 2023 Ocak basindan Subat sonuna, her gun sabit %1
    idx = pd.bdate_range("2023-01-02", "2023-02-28")
    r = pd.Series(0.01, index=idx)
    table = call(m.monthly_return_table, r)
    n_jan = (idx.month == 1).sum()
    n_feb = (idx.month == 2).sum()
    assert table.loc[2023, 1] == approx(1.01 ** n_jan - 1)
    assert table.loc[2023, 2] == approx(1.01 ** n_feb - 1)


def test_monthly_return_table_sample(sample):
    r, _ = sample
    table = call(m.monthly_return_table, r)
    assert table.loc[2023, 1] == approx(0.1033624093, rel=1e-6)
    assert table.loc[2024, 3] == approx(-0.0114405157, rel=1e-6)


# 5) benchmark'a gore

def test_beta():
    # R4 = 2 * B4, tanim geregi beta = 2
    assert call(m.beta, R4, B4) == approx(2.0)


def test_beta_sample(sample):
    r, b = sample
    assert call(m.beta, r, b) == approx(1.2171109918, rel=1e-6)


def test_capm_alpha():
    # r tamamen beta ile aciklaniyor -> alpha 0
    assert call(m.capm_alpha, R4, B4) == approx(0.0, abs=1e-12)


def test_capm_alpha_sample(sample):
    r, b = sample
    assert call(m.capm_alpha, r, b) == approx(0.1027920705, rel=1e-6)


def test_r_squared_and_correlation():
    assert call(m.correlation, R4, B4) == approx(1.0)
    assert call(m.r_squared, R4, B4) == approx(1.0)


def test_r_squared_sample(sample):
    r, b = sample
    assert call(m.r_squared, r, b) == approx(0.5710025188, rel=1e-6)
    assert call(m.correlation, r, b) == approx(0.7556470862, rel=1e-6)


def test_tracking_error():
    # aktif getiri = R4 - B4 = B4, yani TE = std(B4) * sqrt(252)
    assert call(m.tracking_error, R4, B4) == approx(float(B4.std(ddof=1)) * np.sqrt(252))


def test_information_ratio_sample(sample):
    r, b = sample
    assert call(m.tracking_error, r, b) == approx(0.1972757102, rel=1e-6)
    assert call(m.information_ratio, r, b) == approx(0.6610703327, rel=1e-6)


def test_up_down_capture():
    # R4 = 2*B4: yukari gunlerde de asagi gunlerde de iki kat hareket
    assert call(m.up_capture, R4, B4) == approx(2.0)
    assert call(m.down_capture, R4, B4) == approx(2.0)


def test_up_down_capture_sample(sample):
    r, b = sample
    assert call(m.up_capture, r, b) == approx(1.2353283565, rel=1e-6)
    assert call(m.down_capture, r, b) == approx(1.1350136203, rel=1e-6)


# 6) rolling

def test_rolling_volatility():
    rv = call(m.rolling_volatility, Z3, 2)
    assert pd.isna(rv.iloc[0])  # ilk gun: pencere daha dolmadi
    assert rv.iloc[1] == approx(float(pd.Series([0.01, 0.02]).std(ddof=1)) * np.sqrt(252))


def test_rolling_volatility_sample(sample):
    r, _ = sample
    rv = call(m.rolling_volatility, r, 63)
    assert int(rv.isna().sum()) == 62
    assert rv.iloc[-1] == approx(0.3582464626, rel=1e-6)


def test_rolling_sharpe_sample(sample):
    r, _ = sample
    rs = call(m.rolling_sharpe, r, 63)
    assert rs.iloc[-1] == approx(-0.1975925721, rel=1e-6)


def test_rolling_beta_sample(sample):
    r, b = sample
    rb = call(m.rolling_beta, r, b, 63)
    assert int(rb.isna().sum()) == 62
    assert rb.iloc[-1] == approx(1.4181445983, rel=1e-6)
