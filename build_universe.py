
import io

import pandas as pd
import requests

URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
OUT = "data/sp500.csv"
UA = {"User-Agent": "Mozilla/5.0 (tearsheet build_universe.py)"}

resp = requests.get(URL, headers=UA, timeout=30)
resp.raise_for_status()

# ilk tablo mevcut S&P 500 bilesenleri; Symbol + Security bize yetiyor
df = pd.read_html(io.StringIO(resp.text))[0][["Symbol", "Security"]]
df.columns = ["symbol", "name"]

df["symbol"] = df["symbol"].astype(str).str.strip().str.upper().str.replace(".", "-", regex=False)
df["name"] = df["name"].astype(str).str.strip()

df = df.drop_duplicates("symbol").sort_values("symbol").reset_index(drop=True)
df.to_csv(OUT, index=False)

print(f"yazildi: {OUT} ({len(df)} sembol)")
print(df.head(3).to_string(index=False))
