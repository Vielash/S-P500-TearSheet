"""Yahoo Finance'ten fiyat cekme. app.py'nin ucuncu veri kaynagi.

Cikti hep ayni sekilde: uzun format (date, ticker, price). Getiriyi burada
hesaplamiyoruz, onu data.load_returns fiyattan turetiyor.
"""

import pandas as pd
import yfinance as yf

UNIVERSE_PATH = "data/sp500.csv"


def load_universe(path=UNIVERSE_PATH):
    """Secilebilir sembol listesi: symbol, name. build_universe.py uretiyor."""
    df = pd.read_csv(path, index_col=False)
    return df


def _close_frame(raw):
    """yf.download ciktisindan sadece kapanislari alir: index = tarih, kolon = ticker."""
    if raw is None or len(raw) == 0 or "Close" not in raw:
        raise ValueError("Yahoo returned no data — check the symbols and the date range.")
    return raw["Close"]


def fetch_prices(symbols, start, end):
    """Duzeltilmis kapanislari uzun formatta dondurur: date, ticker, price.

    auto_adjust=True temettu ve bolunmeyi fiyata isliyor; benchmark da ayni
    muameleyi gormeli, yoksa fark alpha'ya yaziliyor (bkz. docs/metrics.md 5).
    """
    data = yf.download(symbols, start=start, end=end, auto_adjust=True, progress=False)
    large_data = _close_frame(data)

    # yf indeksi "Date" adiyla geliyor; asagida "date" ile calisacagiz
    index_col_name = large_data.index.name if large_data.index.name else "Date"
    long_data = large_data.reset_index().melt(id_vars=index_col_name,
                                              var_name="ticker", value_name="price")
    long_data = long_data.rename(columns={index_col_name: "date"})

    long_data["ticker"] = long_data["ticker"].astype(str).str.upper()
    long_data = long_data.dropna(subset=["price"])
    long_data = long_data.sort_values(by=["ticker", "date"]).reset_index(drop=True)
    return long_data
