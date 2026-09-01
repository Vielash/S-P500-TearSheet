# Metrik Rehberi

Sıra, `metrics.py`'daki sırayla aynı: kolaydan zora. Her bölümde formül, sezgi
ve klasik tuzak var. Bir fonksiyonu yazınca `pytest -v -k <isim>` ile kontrol et.

Genel kurallar (her metrikte geçerli):

- Getiriler **basit getiri**: `r = P_t / P_(t-1) - 1`. Log getiri değil.
- Yıllıklaştırma katsayısı günlük veride 252 (bir yıldaki ortalama işlem günü).
  Ortalamalar 252 ile, standart sapmalar sqrt(252) ile çarpılır — çünkü
  bağımsız günlerin varyansı toplanır, sapması değil.
- Standart sapmada `ddof=1` (örneklem sapması, pandas'ın varsayılanı).

---

## 1) Getiri

### total_return
`prod(1 + r) - 1`

Getiriler toplanmaz, **bileşik** olarak çarpılır: %10 kazanıp %10 kaybedersen
sıfırda değilsin, %1 eksidesin (1.10 × 0.90 = 0.99). Tuzak: `r.sum()` yazmak.
Kısa vadede yakın görünür, uzun seride ciddi sapar.

### growth_of_1
`(1 + r).cumprod()`

1 doların gün gün yolculuğu. Tearsheet'teki equity curve bu serinin grafiği.
total_return'un "her güne yayılmış" hali.

### cagr
`(1 + toplam_getiri) ** (252 / n) - 1`

"Bu tempo bir tam yıl sürseydi yıllık kaç yapardı?" sorusunun cevabı.
n = gözlem sayısı. Üs alma bileşik büyümeyi korur; `toplam / yıl_sayısı` diye
bölmek yine aritmetik tuzağına düşmek olur.

---

## 2) Risk

### annual_volatility
`std(r, ddof=1) * sqrt(252)`

Günlük dalgalanmanın yıllık ölçeğe taşınmış hali. sqrt neden? Varyans zamanla
doğrusal büyür (252 katı), volatilite onun karekökü olduğu için sqrt(252) katı.

### drawdown_series
`g = growth_of_1(r);  g / g.cummax() - 1`

Her gün için: "şimdiye kadarki zirveden yüzde kaç aşağıdayım?" `cummax` o ana
kadarki zirveyi taşır. Seri hiç pozitif olamaz; zirvede 0'dır.

### max_drawdown
`drawdown_series(r).min()`

Dönemin en kötü zirve→dip düşüşü. Negatif sayı olarak bırakıyoruz (tearsheet'te
-24.80% gibi görünür). Volatiliteden farkı: vol her iki yönü de sayar, drawdown
sadece yaşanmış en kötü senaryoyu anlatır. Yatırımcının "midesini" ölçer.

---

## 3) Riske göre getiri

### sharpe
`excess = r - rf/252;  mean(excess) / std(excess, ddof=1) * sqrt(252)`

"Aldığım her birim dalgalanma başına ne kadar fazla getiri aldım?" rf = risksiz
faiz (yıllık). Basitlik için 0 varsayıyoruz; gerçek analizde tahvil faizi konur.
Tuzak: payı 252, paydayı sqrt(252) ile ayrı ayrı yıllıklaştırmak yerine tek
sqrt(252) çarpanı kullanılır (252/sqrt(252) = sqrt(252) — sadeleşiyor).

### sortino
Sharpe'ın paydasını değiştir: `downside = sqrt(mean(min(excess, 0)²))`

Fikir: yukarı yönlü dalgalanma "risk" değildir, kimse kazandığı için şikayet
etmez. Sadece negatif günlerin şiddeti sayılır. Tuzak: ortalamayı yalnızca
negatif günlere bölmek — payda **tüm** günler üzerinden alınır (negatif olmayan
günler 0 katkı verir). İki tanım da literatürde var, biz yaygın olanı kullanıyoruz.

### calmar
`cagr / |max_drawdown|`

Sharpe'ın "riski" volatilite, Calmar'ınki en kötü düşüş. "Yıllık büyümem, en
derin çukurumun kaç katı?" 1'in üstü genelde iyi sayılır.

---

## 4) Dağılım ve günler

### win_rate — `(r > 0).mean()`
Pozitif günlerin oranı. Tek başına yanıltıcıdır: her gün 1 kuruş kazanıp ayda
bir gün her şeyi kaybeden strateji %95 win rate'le batabilir. O yüzden hep
best/worst day ve çarpıklıkla beraber okunur.

### best_day / worst_day — `r.max()` / `r.min()`
Tek günlük uçlar. Getirinin "dokusunu" gösterir.

### skewness — `r.skew()`
Çarpıklık: dağılımın kuyruğu hangi yanda? Negatif çarpıklık = "çoğu gün ufak
kazanç, arada bir büyük kayıp" (satılmış opsiyon profili, tehlikeli olan bu).

### kurtosis — `r.kurt()`
Basıklık: uç günler normal dağılımın öngördüğünden ne kadar sık? pandas
**excess** kurtosis verir (normal dağılım = 0). Hisse getirilerinde hep
pozitiftir — "fat tails". Rejim projendeki QQ plot bunun görsel hali.

### var_historic
`r.quantile(0.05)`

%95 güvenle "günlük kaybım şundan kötü olmaz" eşiği. Tarihsel yöntem: geçmiş
dağılımın 5. yüzdeliği, dağılım varsayımı yok. Negatif bir sayı döner.

### cvar_historic
`r[r <= VaR].mean()`

VaR eşiği aşıldığında ortalama ne kadar kaybediyorum? VaR "kapının yeri",
CVaR "kapının arkasındaki uçurumun derinliği". Her zaman VaR'dan kötüdür
(testte bu özellik de kontrol ediliyor).

### monthly_return_table
Günlükleri aya bileşikle: `resample("ME").apply(lambda r: (1+r).prod() - 1)`,
sonra yıl × ay pivotu. Isı haritası bu tablodan çiziliyor.

---

## 5) Benchmark'a göre

Bu bölümdeki fonksiyonlara iki seri gelir ve ikisi de **aynı günlere hizalı**
gelir (data.py'daki `align_pair` halleder — hizalamadan cov almak klasik hata).

### beta
`cov(r, b) / var(b)`

Piyasa 1 birim oynadığında sen ortalama kaç birim oynuyorsun. 1.2 beta =
piyasanın %20 abartılmış hali. Regresyon eğimiyle aynı şey — app'te
statsmodels'in bulduğu beta ile seninkinin aynı çıktığını gör.

### capm_alpha
`(mean(r - rf_d) - beta * mean(b - rf_d)) * 252`

Beta'nın açıkladığı kısmı düş, geriye kalan "beceri" (ya da şans). Tearsheet'in
en üstteki kartı bu. Tuzak: alpha'yı yüksek beta'yla karıştırmak — kaldıraçlı
piyasa pozisyonu alpha değildir, CAPM tam bunu ayrıştırır.

### r_squared
`corr(r, b) ** 2`

Getirinin yüzde kaçı piyasa hareketiyle açıklanıyor. Tek değişkenli regresyonda
R² korelasyonun karesine eşittir. 0.9 R² = neredeyse endeks fonu.

### correlation — `r.corr(b)`
Yön birlikteliği, -1 ile 1 arası. Beta'dan farkı: korelasyon "ne kadar beraber",
beta "kaç katı büyüklükte".

### tracking_error
`std(r - b, ddof=1) * sqrt(252)`

Benchmark'tan sapmanın oynaklığı. `r - b`'ye aktif getiri denir. Endeks fonunda
sıfıra yakın; TE yüksekse "bu fon endeksten bağımsız bir şey yapıyor" demektir.

### information_ratio
`mean(r - b) / std(r - b, ddof=1) * sqrt(252)`

Aktif getirinin Sharpe'ı: benchmark'ı yenme becerin, bunun için aldığın aktif
riske bölünmüş. Fon değerlendirmede Sharpe'tan çok buna bakılır.

### up_capture / down_capture
`mean(r[b > 0]) / mean(b[b > 0])` (down için `b < 0`)

Piyasa yükselen günlerde yükselişin, düşen günlerde düşüşün kaçta kaçını
"yakalıyorsun". İdeal profil: up > 1, down < 1. İkisi birden 1.2 ise sadece
kaldıraçlı beta'sın demektir (bkz. capm_alpha tuzağı).

---

## 6) Rolling (kayan pencere)

Tek sayı bütün dönemi özetler ama zamana yayılmış hikayeyi saklar: Sharpe 0.9
"iki sakin yıl" da olabilir, "muhteşem bir yıl + felaket bir yıl" da. Kayan
pencere bunu açar. Penceredeki gün sayısı app'te seçiliyor: 63 = 1 çeyrek.

### rolling_volatility — `r.rolling(w).std(ddof=1) * sqrt(252)`
### rolling_sharpe — `excess.rolling(w).mean() / excess.rolling(w).std(ddof=1) * sqrt(252)`
### rolling_beta — `r.rolling(w).cov(b) / b.rolling(w).var()`

Üçünde de ilk `w-1` gün NaN kalır — pencere daha dolmadı, bu bir hata değil
(testler bunu da kontrol ediyor). Tuzak: pencereyi küçülttükçe seri "duyarlı"
ama gürültülü olur; 63 gün klasik dengedir.

---

## Bilerek basitleştirdiklerimiz

- rf'yi çoğu yerde 0 aldık; gerçek analizde günlük T-bill serisi (faktör
  dosyasındaki `rf` kolonu) kullanılır. factors.py regresyonları zaten
  `r - rf` (fazla getiri) ile çalışıyor, farkı oradan görebilirsin.
- CAGR'de takvim yılı yerine 252 gün varsaydık; iki yöntem hafif farklı sayı
  verir, ikisi de kullanılıyor.
- Capture'da "ortalama oranı" tanımını seçtik; bileşik tanım da var.
