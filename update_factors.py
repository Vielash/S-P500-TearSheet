"""Gercek Ken French faktor verisini indirip data/ff5_daily.csv'ye yazar.

Kendi makinende, internet varken bir kez calistir:
    python update_factors.py

Ken French dosyalari yuzde cinsinden gelir (1.25 = %1.25), biz her yerde
ondalik kullaniyoruz (0.0125), o yuzden 100'e boluyoruz.
"""

import pandas_datareader.data as web

ff = web.DataReader("F-F_Research_Data_5_Factors_2x3_daily", "famafrench", start="2000-01-01")[0]
ff = ff / 100
ff.columns = ["mkt_rf", "smb", "hml", "rmw", "cma", "rf"]
ff.index.name = "date"
ff.to_csv("data/ff5_daily.csv")
print(f"yazildi: data/ff5_daily.csv ({len(ff)} gun, {ff.index.min().date()} -> {ff.index.max().date()})")
