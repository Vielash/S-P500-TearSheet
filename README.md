# Quant Tearsheet

Getiri CSV'sinden tam bir quant tearsheet üreten Streamlit uygulaması:
CAPM alpha & beta, Fama-French faktör yüklemeleri, rolling metrikler,
drawdown analizi ve iki hisse karşılaştırması.

Buradaki tek eksik parça sensin: `metrics.py` içindeki fonksiyonların gövdeleri
boş. Sen doldurdukça testler yeşile döner, arayüzdeki kartlar canlanır.

## Kurulum ve çalıştırma

```
pip install -r requirements.txt
streamlit run app.py
```

Açılınca "Load sample data" ile örnek veriyi yükle (sentetiktir, gerçek piyasa
verisi değildir) ya da kendi CSV'ni sürükle.

## Çalışma düzeni

1. `metrics.py`'da sıradaki fonksiyonu doldur (yukarıdan aşağıya kolaydan zora).
2. `pytest -v -k <fonksiyon_adi>` ile kontrol et. Yeşilse doğru.
3. `streamlit run app.py` — o metriğin kartı/grafiği artık dolu.
4. Kavram için `docs/metrics.md`'deki bölümü oku (formül + sezgi + tuzak).

`pytest -v` toplam durumu gösterir: skip = daha yazılmadı, passed = doğru.

## CSV formatı

```
date,ticker,price,return
2023-01-03,SPY,378.1841,-0.00478
2023-01-03,AAPL,124.8412,-0.00127
```

- Uzun format: her satır bir gün × bir ticker. Benchmark'ı (örn. SPY) da aynı
  dosyaya ayrı ticker olarak koy.
- `price` düzeltilmiş kapanış (adjusted close) olmalı, `return` basit getiri
  (0.001 = %0.1). `return` yoksa fiyattan hesaplanır.
- Kolon adları esnek: price/close/adj_close, return/ret kabul edilir.

Veriyi kendin hazırlıyorsun (yfinance ile çek, bu formata dönüştür) — bu bilinçli
bir tercih, ilk alıştırma o.

## Dosya yapısı ve okuma sırası

```
app.py              Streamlit arayüzü          (hazır)
data.py             CSV okuma, pivot, hizalama (hazır)
metrics.py          metrik hesapları           (SEN yazacaksın)
factors.py          CAPM + Fama-French regresyonları, statsmodels (hazır)
plots.py            Plotly grafikleri          (hazır)
update_factors.py   gerçek Ken French verisini indirir (kendi makinende çalıştır)
tests/              her metriğin doğruluk testleri
docs/metrics.md     metrik rehberi
data/               örnek veri + faktör dosyası (ikisi de sentetik örnek)
```

Kodu okuma sırası önerisi: `data.py` → `metrics.py` → `factors.py` → `plots.py` → `app.py`.

## Notlar

- `data/ff5_daily.csv` sentetik bir örnektir. Gerçeğini indirmek için (internet
  gerekli): `python update_factors.py`
- Fonksiyon imzalarını değiştirme; testler ve app o imzalara göre çağırıyor.
- Bir metrikte takılırsan testin beklediği değerle kendi sonucunu karşılaştır,
  `docs/metrics.md`'deki tuzak notuna bak.
