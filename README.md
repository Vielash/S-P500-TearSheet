# Quant Tearsheet

Getiri verisinden tam bir quant tearsheet üreten Streamlit uygulaması:
CAPM alpha & beta, Fama-French faktör yüklemeleri, rolling metrikler,
drawdown analizi ve iki hisse karşılaştırması.

Bir öğrenme projesi olarak yazıldı: arayüz, tasarım sistemi, grafikler ve testler
hazır geldi, `metrics.py`'daki 28 metriğin hepsini ben tek tek doldurdum.
`pytest` bu yüzden bir doğruluk kanıtı — her metrik bilinen bir beklenen değere
karşı test ediliyor.

## Kurulum ve çalıştırma

```
pip install -r requirements.txt
streamlit run app.py
```

Testleri ve veri indirme betiklerini de çalıştıracaksan:

```
pip install -r requirements-dev.txt
pytest -v
```

## Veri girişi

Açılış ekranında üç yol var:

1. **Kendi CSV'ni sürükle** — aşağıdaki formatta.
2. **Try with sample data** — `data/sample_returns.csv`. Bu dosya sentetiktir,
   gerçek piyasa verisi değildir; uygulama da kaynağın yanında bunu belirtir.
3. **Fetch live prices** — sembol ve tarih aralığı seç, `market.py` üzerinden
   `yfinance` ile Yahoo Finance'ten düzeltilmiş kapanışları çeker. Sembol listesi
   `data/sp500.csv`'den gelir; `python build_universe.py` onu Wikipedia'dan
   tazeler. `yfinance` kurulu değilse uygulama yine açılır, sadece bu bölüm
   görünmez.

Üç yol da aynı yere bağlanır: `data.load_returns()` → uzun tablo → `returns_wide()`.
Uygulamanın geri kalanı verinin nereden geldiğini bilmez.

### CSV formatı

```
date,ticker,price,return
2023-01-03,SPY,378.1841,-0.00478
2023-01-03,AAPL,124.8412,-0.00127
```

- Uzun format: her satır bir gün × bir ticker. Benchmark'ı da aynı dosyaya ayrı
  ticker olarak koy. Uygulama varsayılan benchmark'ı `^SP500TR` → `SPY` sırasıyla
  seçer; ikisi de toplam getiri serisidir. `^GSPC` koyma — salt fiyat endeksidir,
  temettü içermez ve düzeltilmiş fiyatlarla kıyaslanınca alpha'yı şişirir
  (uygulama seçersen uyarıyor).
- `price` düzeltilmiş kapanış (adjusted close) olmalı, `return` basit getiri
  (0.001 = %0.1). `return` yoksa fiyattan hesaplanır.
- Kolon adları esnek: price/close/adj_close, return/ret kabul edilir.

## Arayüz

Üç sekme var. **Tearsheet** beş numaralı bölümde bütün metrikleri ve grafikleri
gösterir. **Compare** iki tickerı yan yana koyar. **Metric guide** her metriğin
tanımını, formülünü ve yorum aralığını tek sayfada toplar; yanındaki rozet o
metriğin bu veride hazır mı, bekliyor mu, hata mı verdiğini söyler. Kartların ve
grafiklerin başlığındaki `?` imleci aynı açıklamayı yerinde açar. Metinlerin tek
kaynağı `ui.INFO`.

Yarım kalmış bir metrik uygulamayı düşürmez: yazılmamışsa "NOT READY", patlıyorsa
o kartta "ERROR" görünür, sayfanın kalanı çalışmaya devam eder.

## Dosya yapısı

```
app.py              Streamlit arayüzü, beş bölüm + Compare + Metric guide
ui.py               tasarım sistemi: renk token'ları, CSS, kartlar, metrik metinleri
data.py             CSV okuma, uzun->geniş pivot, seri hizalama
market.py           Yahoo Finance'ten fiyat çekme (yfinance)
metrics.py          28 metriğin hesabı
factors.py          CAPM + Fama-French regresyonları (statsmodels)
plots.py            Plotly grafikleri, ui.py ile aynı temada
build_universe.py   S&P 500 sembol listesini indirir -> data/sp500.csv
update_factors.py   gerçek Ken French faktör verisini indirir
tests/              her metriğin doğruluk testleri
docs/metrics.md     metrik rehberi: formül + sezgi + tuzak
data/               örnek getiri ve faktör dosyaları (ikisi de sentetik)
```

Kodu okuma sırası önerisi: `data.py` → `metrics.py` → `factors.py` → `plots.py` → `app.py`.

## Notlar

- `data/sample_returns.csv` ve `data/ff5_daily.csv` sentetik örneklerdir, gerçek
  piyasa verisi değildir. Gerçek faktörler için: `python update_factors.py`
- `metrics.py`'daki fonksiyon imzaları sabittir; testler ve `app.py` onları o
  adlarla ve sırayla çağırıyor.
- `rf` yıllık orandır (0.04 = %4); fonksiyonlar içeride `periods_per_year`'a böler.
- Getiriler her yerde ondalıktır, yüzde değil.

## Canlıya alma (Streamlit Community Cloud)

1. [share.streamlit.io](https://share.streamlit.io) → **New app** → bu repo, branch
   `main`, main file `app.py`. Advanced settings'ten Python 3.10 seç.
2. `requirements.txt`'i kendisi kurar; `requirements-dev.txt`'e dokunmaz.
3. Ayarlanacak secret yok — uygulama hiçbir API anahtarı kullanmıyor.

Canlıda bilinmesi gereken tek şey **Yahoo'nun rate limit'i**: bulutta bütün
ziyaretçiler tek bir IP'den çıkar ve Yahoo tekrarlayan istekleri kısar. Bu
durumda uygulama düşmüyor — "Yahoo is rate-limiting this server" paneli çıkıyor,
CSV yükleme ve örnek veri yolları çalışmaya devam ediyor. Çekilen veri bir saat
boyunca önbellekte tutuluyor (`fetch_frame`), bu da aynı isteği tekrar tekrar
Yahoo'ya taşımayı önlüyor.

## Sorumluluk reddi

Bu proje eğitim amaçlıdır. Ürettiği sayılar yatırım tavsiyesi değildir. Piyasa
verisi Yahoo Finance'ten gelir; doğruluğu ya da sürekliliği garanti edilmez.
