"""app.py testleri: arayuzun sozlesmeleri. Ag gerekmez.

metrics.py testleri sayilarin dogrulugunu olcuyor. Buradakiler sayilarin
kullaniciya nasil sunuldugunu olcuyor, cunku bu projede yanlis sunum en az
yanlis hesap kadar pahaliya mal oldu: sentetik faktorlere regresyon, sirf
pozitif diye "GOOD" yazan alpha, gizli bir rf varsayimi.

streamlit.testing.v1.AppTest scripti gercekten calistirir, o yuzden bu dosya
metrics testlerinden yavastir (uygulama basina birkac saniye).
"""

from pathlib import Path

import pandas as pd
import pytest

from streamlit.testing.v1 import AppTest

import factors
import market
import plots

ROOT = Path(__file__).parent.parent
APP = str(ROOT / "app.py")
SAMPLE_CSV = (ROOT / "data" / "sample_returns.csv").read_bytes()


def run(state=None, timeout=180):
    """Uygulamayi calistirir; state verilirse oturum durumunu kurup tekrar calistirir."""
    at = AppTest.from_file(APP, default_timeout=timeout)
    at.run()
    if state:
        for k, v in state.items():
            at.session_state[k] = v
        at.run()
    return at


def markup(at):
    """Sayfadaki butun HTML'i tek parca — icerik aramak icin."""
    return " ".join(str(m.value) for m in at.markdown)


def captions(at):
    return [c.value for c in at.get("caption")]


@pytest.fixture(scope="module")
def ornek():
    """Sentetik ornek veriyle acilmis uygulama."""
    return run({"_sample": True})


@pytest.fixture(scope="module")
def yuklenmis():
    """CSV yuklenmis uygulama: ornek veriyle ayni sayilar ama synthetic=False."""
    return run({"_raw": SAMPLE_CSV, "_name": "returns.csv"})


# --- temel render -------------------------------------------------------------

def test_ornek_veri_hatasiz(ornek):
    assert ornek.exception == []
    assert [t.label for t in ornek.get("tab")] == ["Tearsheet", "Compare", "Metric guide"]


def test_landing_uc_veri_yolu():
    """Acilis ekraninda CSV, ornek veri ve canli cekme birlikte durmali."""
    at = run()
    assert at.exception == []
    assert len(at.get("file_uploader")) == 1
    etiketler = [b.label for b in at.get("button")]
    assert "Try with sample data →" in etiketler
    assert "Fetch prices →" in etiketler
    assert [d.label for d in at.get("date_input")] == ["From", "To"]
    assert len(at.get("multiselect")[0].options) > 400


def test_alt_bilgi_ve_sorumluluk_reddi(ornek):
    h = markup(ornek)
    assert "qt-foot" in h
    assert "not investment advice" in h
    # teknik olarak savunulamayan eski gizlilik iddiasi geri gelmemeli
    assert "never leaves the browser" not in markup(run())


# --- risksiz oran veriden geliyor ---------------------------------------------

def test_rf_secilebilir_degil(ornek):
    """rf bir ayar degil: kenar cubugunda sayi girdisi olmamali."""
    assert ornek.get("number_input") == []


def test_rf_sayfada_yaziyor(ornek):
    """Hangi rf ile calisildigi okunabilmeli — gizli varsayim kalmasin."""
    assert "r_f " in markup(ornek)
    assert any("T-bill" in c or "risk-free data" in c for c in captions(ornek))


def test_rf_faktor_dosyasindan(ornek):
    """Ornek veri 2023-2026 arasi: o donemde rf sifir olamaz."""
    h = markup(ornek)
    import re
    m = re.search(r"r_f ([0-9.]+)%", h)
    assert m, "sayfada r_f etiketi yok"
    assert float(m.group(1)) > 1.0


# --- alpha anlamlilik rozeti --------------------------------------------------

def alpha_blok(at):
    for m in at.markdown:
        h = str(m.value)
        if "qt-card" in h and "Annualized Alpha" in h:
            i = h.index("Annualized Alpha")
            return h[i:i + 900]
    return ""


def test_alpha_sirf_pozitif_diye_iyi_demiyor(ornek):
    """Etiket isaretten degil t-istatistiginden gelmeli."""
    blok = alpha_blok(ornek)
    assert blok, "alpha karti bulunamadi"
    assert "GOOD" not in blok
    assert "SIGNIFICANT" in blok


def test_alpha_t_istatistigini_yaziyor(ornek):
    assert "t = " in alpha_blok(ornek)


# --- faktor bolumunun kapilari ------------------------------------------------

def test_sentetik_getiride_yuklemeler_illustratif(ornek):
    """Ornek veri sentetik, faktorler gercek: sayilar okunacak sey degil, yazmali."""
    assert "illustrative, not a real exposure" in markup(ornek)


def test_gercek_veride_illustratif_uyarisi_yok(yuklenmis):
    assert "illustrative, not a real exposure" not in markup(yuklenmis)
    assert "FF5 regression" in markup(yuklenmis)


def test_sentetik_faktor_gercek_getiride_kapali(monkeypatch):
    """Uydurma faktorlere gercek getiri regres edilmemeli — bolum hic acilmamali."""
    monkeypatch.setattr(factors, "is_synthetic", lambda ff: True)
    at = run({"_raw": SAMPLE_CSV, "_name": "returns.csv"})
    h = markup(at)
    assert at.exception == []
    assert "Factor analysis is off for this data" in h
    assert "FF5 regression" not in h


# --- hata sinirlari -----------------------------------------------------------

def test_faktor_bolumu_coktugunde_sayfa_ayakta(monkeypatch):
    """04. bolum patlarsa 05 ve CSV disa aktarimi yine render edilmeli.

    Bir zamanlar edilmiyordu: Streamlit scripti orada kesiyordu ve asagidaki
    her sey sessizce kayboluyordu.
    """
    def patla(*a, **k):
        raise RuntimeError("bolum 04 icinde kasitli hata")

    monkeypatch.setattr(plots, "loadings_bar", patla)
    at = run({"_sample": True})
    h = markup(at)
    assert at.exception == []
    assert "could not be rendered" in h        # bolum kendi hatasini gosteriyor
    assert "FF5 regression" not in h
    assert "Skewness" in h                     # 05. bolum yerinde
    assert [d.label for d in at.get("download_button")] == ["Download metrics (CSV)"]


def test_calisan_tek_export_var(ornek):
    """Pasif PDF/PNG dugmeleri geri gelmemeli."""
    etiketler = [b.label for b in ornek.get("button")]
    assert "PDF" not in etiketler and "PNG" not in etiketler
    assert [d.label for d in ornek.get("download_button")] == ["Download metrics (CSV)"]


def test_yahoo_rate_limit_ayri_mesaj(monkeypatch):
    """Kisitlanma gercek bir hatadan ayirt edilmeli ve CSV yolunu gostermeli."""
    class YFRateLimitError(Exception):
        pass

    def kisitli(*a, **k):
        raise YFRateLimitError("Too Many Requests. Rate limited.")

    monkeypatch.setattr(market, "fetch_prices", kisitli)
    at = run({"_fetch": (("AAPL", "SPY"), "2001-01-02", "2001-03-01")})
    h = markup(at)
    assert at.exception == []
    assert "rate-limiting this server" in h
    assert "upload a CSV instead" in h
    assert "Continue with sample data" in [b.label for b in at.get("button")]


def test_cekme_hatasi_sayfayi_dusurmez(monkeypatch):
    monkeypatch.setattr(market, "fetch_prices",
                        lambda *a, **k: (_ for _ in ()).throw(ValueError("bozuk sembol")))
    at = run({"_fetch": (("ZZZZ",), "2002-01-02", "2002-03-01")})
    assert at.exception == []
    assert "Could not fetch prices" in markup(at)


# --- karsilastirma tablosu ----------------------------------------------------

def karsilastirma_satiri(at, etiket):
    """Compare tablosundaki bir satirin hucrelerini dondurur."""
    import re
    for m in at.markdown:
        h = str(m.value)
        if "Metric comparison" in h and etiket in h:
            seg = h[h.index(etiket):h.index(etiket) + 700]
            return re.findall(r'class="r[^"]*"[^>]*>([^<]+)<', seg)
    return []


def test_volatilite_oku_metrigin_yonunu_izliyor(ornek):
    """Daha yuksek volatilite kotudur: delta pozitif olsa bile ok asagi bakmali."""
    hucreler = karsilastirma_satiri(ornek, "Volatility")
    assert len(hucreler) >= 3, "Volatility satiri bulunamadi"
    a, b, delta = float(hucreler[0].rstrip("%")), float(hucreler[1].rstrip("%")), hucreler[2]
    yon = "▲" if a < b else "▼"       # dusuk volatilite iyi
    assert delta.startswith(yon), f"{a} vs {b} icin ok yanlis: {delta}"


def test_sharpe_oku_metrigin_yonunu_izliyor(ornek):
    hucreler = karsilastirma_satiri(ornek, "Sharpe")
    assert len(hucreler) >= 3
    a, b, delta = float(hucreler[0]), float(hucreler[1]), hucreler[2]
    yon = "▲" if a > b else "▼"       # yuksek Sharpe iyi
    assert delta.startswith(yon), f"{a} vs {b} icin ok yanlis: {delta}"


# --- metrik rehberi -----------------------------------------------------------

def test_rehber_duzeltilmis_metinleri_tasiyor(ornek):
    """Yanlis tanimlar geri gelmemeli."""
    h = markup(ornek)
    assert "worst of 20 days" not in h          # VaR bir esik, ortalama degil
    assert "Near 0: independent" not in h       # dusuk R2 bagimsizlik degil
    assert "time spent in drawdown" not in h    # Ulcer sure degil
    assert "1 day in 20" in h
    assert "not the same as independence" in h
    assert "Root mean square" in h


def test_capm_formulunde_rf_gorunuyor(ornek):
    assert "r − r_f = α + β(r_b − r_f)" in markup(ornek)


def test_rehberde_her_metrik_rozetli(ornek):
    h = markup(ornek)
    assert "metrics.ulcer_index()" in h
    assert "READY" in h
