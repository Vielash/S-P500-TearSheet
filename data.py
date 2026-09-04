import pandas as pd

# kabul edilen kolon adlari (kucuk harfe cevirip esliyoruz)
DATE_COLS = {"date", "tarih"}
TICKER_COLS = {"ticker", "symbol", "sembol"}
PRICE_COLS = {"price", "close", "adj_close", "fiyat"}
RETURN_COLS = {"return", "ret", "getiri"}


def _find_col(columns, candidates):
    for c in columns:
        if c.strip().lower() in candidates:
            return c
    return None


def load_returns(source):
    """CSV'yi okuyup uzun formatta temiz tablo dondurur: date, ticker, return.

    Beklenen kolonlar: date, ticker ve (price veya return).
    return kolonu yoksa fiyattan hesaplanir: r_t = p_t / p_(t-1) - 1
    """
    df = pd.read_csv(source)

    date_c = _find_col(df.columns, DATE_COLS)
    ticker_c = _find_col(df.columns, TICKER_COLS)
    price_c = _find_col(df.columns, PRICE_COLS)
    return_c = _find_col(df.columns, RETURN_COLS)

    if date_c is None or ticker_c is None:
        raise ValueError("CSV'de 'date' ve 'ticker' kolonlari olmali")
    if price_c is None and return_c is None:
        raise ValueError("CSV'de 'price' veya 'return' kolonlarindan en az biri olmali")

    out = pd.DataFrame({
        "date": pd.to_datetime(df[date_c]),
        "ticker": df[ticker_c].astype(str).str.strip().str.upper(),
    })
    if price_c is not None:
        out["price"] = pd.to_numeric(df[price_c], errors="coerce")
    if return_c is not None:
        out["return"] = pd.to_numeric(df[return_c], errors="coerce")

    # ayni gun + ayni ticker iki kez varsa sonuncusu kalir
    out = out.sort_values(["ticker", "date"]).drop_duplicates(["ticker", "date"], keep="last")

    if "return" not in out.columns:
        prev = out.groupby("ticker")["price"].shift(1)
        out["return"] = out["price"] / prev - 1

    return out.dropna(subset=["return"]).reset_index(drop=True)


def returns_wide(df):
    """Uzun tabloyu genise cevirir: index = date, her ticker ayri kolon."""
    return df.pivot(index="date", columns="ticker", values="return").sort_index()


def align_pair(wide, a, b):
    pair = wide[[a, b]].dropna()
    return pair[a], pair[b]
