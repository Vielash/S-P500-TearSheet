"""market.py testleri. Ag gerekmez: yf.download taklit ediliyor.

Burada olculen sey Yahoo'nun verisi degil, market.py'nin sozlesmesi: ciktisi her
zaman uzun formatta (date, ticker, price) olmali ve data.load_returns'un dogrudan
okuyabilecegi sekle gelmeli. Bu iki uc arasindaki bag app.py'nin canli veri
yolunun tamami, ve bir zamanlar tam burada kirikti (kolon adi "Date" iken
siralama "date" ariyordu).
"""

import io
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import data
import market

ROOT = Path(__file__).parent.parent


def yf_frame(symbols, gun=6, nan_at=None):
    """yfinance'in donduruden sekli taklit eder: MultiIndex kolon (alan, ticker)."""
    idx = pd.bdate_range("2024-01-02", periods=gun, name="Date")
    alanlar = ["Close", "High", "Low", "Open", "Volume"]
    cols = pd.MultiIndex.from_product([alanlar, symbols], names=["Price", "Ticker"])
    rng = np.random.default_rng(0)
    veri = 100 + rng.normal(0, 1, (gun, len(cols))).cumsum(axis=0)
    df = pd.DataFrame(veri, index=idx, columns=cols)
    if nan_at is not None:
        df.loc[df.index[nan_at], ("Close", symbols[0])] = np.nan
    return df


@pytest.fixture
def fake_yf(monkeypatch):
    """yf.download'u sabit bir cerceve dondurecek sekilde degistirir."""
    def kur(frame):
        monkeypatch.setattr(market.yf, "download",
                            lambda *a, **k: frame)
    return kur


# --- cikti sekli --------------------------------------------------------------

def test_uzun_format_kolonlari(fake_yf):
    fake_yf(yf_frame(["AAPL", "MSFT"]))
    out = market.fetch_prices(["AAPL", "MSFT"], "2024-01-02", "2024-01-10")
    assert list(out.columns) == ["date", "ticker", "price"]
    assert set(out["ticker"]) == {"AAPL", "MSFT"}
    assert len(out) == 12


def test_tarihe_gore_sirali(fake_yf):
    """Siralama bir zamanlar KeyError: 'date' ile patliyordu — regresyon testi."""
    fake_yf(yf_frame(["AAPL", "MSFT"]))
    out = market.fetch_prices(["AAPL", "MSFT"], "2024-01-02", "2024-01-10")
    for _, grup in out.groupby("ticker"):
        assert grup["date"].is_monotonic_increasing
    assert list(out["ticker"]) == sorted(out["ticker"])


def test_tek_sembol_de_uzun_format(fake_yf):
    fake_yf(yf_frame(["AAPL"]))
    out = market.fetch_prices(["AAPL"], "2024-01-02", "2024-01-10")
    assert list(out.columns) == ["date", "ticker", "price"]
    assert set(out["ticker"]) == {"AAPL"}


def test_ticker_buyuk_harfe_cevriliyor(fake_yf):
    fake_yf(yf_frame(["aapl"]))
    out = market.fetch_prices(["aapl"], "2024-01-02", "2024-01-10")
    assert set(out["ticker"]) == {"AAPL"}


def test_bos_fiyatlar_atiliyor(fake_yf):
    fake_yf(yf_frame(["AAPL", "MSFT"], nan_at=2))
    out = market.fetch_prices(["AAPL", "MSFT"], "2024-01-02", "2024-01-10")
    assert out["price"].notna().all()
    assert len(out) == 11


# --- hata durumlari -----------------------------------------------------------

def test_bos_yanit_temiz_hata(fake_yf):
    """Yanlis sembolde ham KeyError degil, okunur bir ValueError donmeli."""
    fake_yf(pd.DataFrame())
    with pytest.raises(ValueError, match="no data"):
        market.fetch_prices(["ZZZZ"], "2024-01-02", "2024-01-10")


def test_close_kolonu_yoksa_hata():
    with pytest.raises(ValueError):
        market._close_frame(pd.DataFrame({"Open": [1.0, 2.0]}))
    with pytest.raises(ValueError):
        market._close_frame(None)


# --- data.py ile birlesme -----------------------------------------------------

def test_load_returns_dogrudan_okuyabiliyor(fake_yf):
    """app.py'nin fetch_frame'i tam olarak bunu yapiyor: DataFrame -> CSV -> uzun tablo."""
    fake_yf(yf_frame(["AAPL", "SPY"], gun=10))
    px = market.fetch_prices(["AAPL", "SPY"], "2024-01-02", "2024-01-16")
    df = data.load_returns(io.StringIO(px.to_csv(index=False)))
    assert set(df.columns) == {"date", "ticker", "price", "return"}
    wide = data.returns_wide(df)
    assert list(wide.columns) == ["AAPL", "SPY"]
    # ilk gun getiriye cevrilemez, dusuyor
    assert len(wide) == 9
    assert wide.notna().all().all()


# --- evren dosyasi ------------------------------------------------------------

def test_load_universe():
    uni = market.load_universe(ROOT / market.UNIVERSE_PATH)
    assert "symbol" in uni.columns
    assert len(uni) > 400
    assert uni["symbol"].is_unique
    assert "AAPL" in set(uni["symbol"])
