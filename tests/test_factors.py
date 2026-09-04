"""factors.py testleri: regresyonlar ve veriden turetilen risksiz oran.

metrics.py testlerinden ayri duruyorlar cunku burada olcemek istedigimiz sey
hesabin dogrulugu degil, arayuzun guvendigi sozlesmeler:
  - sentetik bir faktor dosyasi taninabiliyor mu (04. bolum buna gore aciliyor)
  - rf gercekten veriden mi geliyor, ortak gun yoksa ne oluyor
  - alpha'nin t-istatistigi okunabiliyor mu (kartin "significant" rozeti bundan)
"""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import factors

ROOT = Path(__file__).parent.parent
approx = pytest.approx

# benchmark'in tam iki kati hareket eden seri: beta=2, alpha=0 olmali
B = pd.Series([0.005, 0.010, -0.015, 0.020, -0.004, 0.011],
              index=pd.bdate_range("2023-01-02", periods=6))
R = 2 * B


@pytest.fixture(scope="module")
def ff():
    return factors.load_factors(ROOT / "data" / "ff5_daily.csv")


# --- faktor dosyasinin kimligi ----------------------------------------------

def test_load_factors_kolonlari(ff):
    for col in factors.FF5_COLS + ["rf"]:
        assert col in ff.columns
    assert isinstance(ff.index, pd.DatetimeIndex)
    assert ff.index.is_monotonic_increasing


def test_repodaki_dosya_gercek(ff):
    """Repoda gercek Ken French serisi olmali; sentetik ornek degil.

    Bu test bir gun kirmizi olursa data/ff5_daily.csv sentetik bir dosyayla
    degistirilmis demektir: python update_factors.py gercegini geri getirir.
    """
    assert not factors.is_synthetic(ff)
    assert ff.index.min().year == 1963


def test_is_synthetic_kisa_seriyi_yakalar(ff):
    assert factors.is_synthetic(ff.loc["2023-01-01":])
    assert factors.is_synthetic(None)
    assert factors.is_synthetic(ff.iloc[:0])


# --- veriden turetilen risksiz oran -----------------------------------------

def test_risk_free_donemle_degisir(ff):
    """rf bir ayar degil: yuklenen tarih araligiyla birlikte oynamali."""
    sifir_faiz, _ = factors.risk_free_annual(ff, pd.bdate_range("2021-01-04", "2021-12-31"))
    yuksek_faiz, n = factors.risk_free_annual(ff, pd.bdate_range("2023-01-03", "2024-12-31"))
    assert sifir_faiz == approx(0.0, abs=5e-4)
    assert 0.03 < yuksek_faiz < 0.07
    assert n > 400


def test_risk_free_ortak_gun_yoksa_none(ff):
    """Faktor dosyasinin bittigi tarihten sonrasi icin uydurma deger uretmemeli."""
    ileri = pd.bdate_range(ff.index.max() + pd.Timedelta(days=30), periods=20)
    assert factors.risk_free_annual(ff, ileri) == (None, 0)
    assert factors.risk_free_annual(None, ileri) == (None, 0)


def test_risk_free_yillik_olcekte(ff):
    """Donen deger yillik: gunluk ortalamanin 252 kati."""
    idx = pd.bdate_range("2023-01-03", "2023-12-29")
    yillik, n = factors.risk_free_annual(ff, idx)
    gunluk = ff["rf"].reindex(idx).dropna()
    assert yillik == approx(float(gunluk.mean()) * factors.TRADING_DAYS)
    assert n == len(gunluk)


# --- CAPM ---------------------------------------------------------------------

def test_capm_regression_tanim_geregi():
    """R = 2*B ise beta 2, alpha 0 olmali — insadan gelen dogru."""
    table, r2 = factors.capm_regression(R, B)
    beta = float(table.loc[table["factor"] == "Beta (Market)", "coef"].iloc[0])
    alpha = float(table.loc[table["factor"] == "Alpha", "coef"].iloc[0])
    assert beta == approx(2.0)
    assert alpha == approx(0.0, abs=1e-12)
    assert r2 == approx(1.0)


def test_capm_rf_betayi_degistirmez():
    """rf iki taraftan da ayni sabiti dusuyor: egim degismemeli."""
    def beta_of(rf):
        t, _ = factors.capm_regression(R, B, rf=rf)
        return float(t.loc[t["factor"] == "Beta (Market)", "coef"].iloc[0])

    assert beta_of(0.0) == approx(beta_of(0.05))


def test_alpha_t_stat_okunabiliyor():
    table, _ = factors.capm_regression(R, B)
    t = factors.alpha_t_stat(table)
    assert t is None or isinstance(t, float)
    # alpha satiri olmayan bir tabloda None donmeli
    assert factors.alpha_t_stat(table[table["factor"] != "Alpha"]) is None


# --- Fama-French --------------------------------------------------------------

def test_ff_regression_gercek_veride_anlamli(ff):
    """Gercek faktorlerle gercek bir piyasa serisi guclu bir MKT-RF yuku vermeli.

    Burada faktor dosyasinin kendi mkt_rf serisini getiri gibi kullaniyoruz:
    aginternet gerektirmez ve beklenen sonuc tanim geregi bilinir — piyasanin
    kendisini piyasaya regres edince yuk 1, R-kare 1 cikar.
    """
    pencere = ff.loc["2015":"2019"]
    piyasa = pencere["mkt_rf"] + pencere["rf"]  # ham piyasa getirisi
    table, r2 = factors.ff_regression(piyasa, pencere, "ff5")
    yuk = float(table.loc[table["factor"] == "mkt_rf", "coef"].iloc[0])
    assert yuk == approx(1.0, abs=1e-6)
    assert r2 == approx(1.0, abs=1e-6)


def test_ff3_ff5_alt_kumesi(ff):
    pencere = ff.loc["2018":"2019"]
    piyasa = pencere["mkt_rf"] + pencere["rf"]
    t5, _ = factors.ff_regression(piyasa, pencere, "ff5")
    t3, _ = factors.ff_regression(piyasa, pencere, "ff3")
    assert set(t3["factor"]) - {"Alpha"} == set(factors.FF3_COLS)
    assert set(t5["factor"]) - {"Alpha"} == set(factors.FF5_COLS)


def test_rolling_ff_betas_pencere_kadar_bosluk(ff):
    pencere = ff.loc["2018":"2019"]
    piyasa = pencere["mkt_rf"] + pencere["rf"]
    betas = factors.rolling_ff_betas(piyasa, pencere, 126)
    assert list(betas.columns) == factors.FF5_COLS
    assert len(betas) == len(pencere) - 125
    assert not betas.isna().any().any()
    assert betas["mkt_rf"].iloc[-1] == approx(1.0, abs=1e-6)


def test_kisa_ortaklik_hata_verir(ff):
    """Ortak gun yoksa regresyon kurulamaz; app.py bunu yakalayip panel gosteriyor."""
    bos = pd.Series(dtype=float, index=pd.DatetimeIndex([]))
    with pytest.raises(Exception):
        factors.ff_regression(bos, ff, "ff5")
