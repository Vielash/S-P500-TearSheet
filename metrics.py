
import numpy as np
import pandas as pd


TRADING_DAYS = 252



def total_return(returns: pd.Series) -> float:
    out = np.prod(1 + returns) - 1
    return out

def growth_of_1(returns: pd.Series) -> pd.Series:
    growth = np.cumprod(1+returns)
    return growth


def cagr(returns: pd.Series, periods_per_year: int = TRADING_DAYS) -> float:
    total_growth = np.prod(1+returns)
    total_periods = len(returns)
    years = total_periods/periods_per_year

    calculate_cagr = total_growth**(1/years) - 1
    return calculate_cagr

# 2) risk

def annual_volatility(returns: pd.Series, periods_per_year: int = TRADING_DAYS) -> float:
    daily_vol = np.std(returns, ddof=1)
    annualized_vol = daily_vol * np.sqrt(periods_per_year)
    return annualized_vol 

def drawdown_series(returns: pd.Series) -> pd.Series:
    growth = (1+ returns).cumprod()
    peak = growth.cummax() 
    drawdown = (growth - peak)/ peak * 100
    return drawdown


def max_drawdown(returns: pd.Series) -> float:
    drawdown = drawdown_series(returns)
    mdd_value = drawdown.min()
    return mdd_value


# 3) riske gore getiri

def sharpe(returns: pd.Series, rf: float = 0.0, periods_per_year: int = TRADING_DAYS) -> float:
    daily_volatility = returns.std()
    annual_volatiltiy = daily_volatility * np.sqrt(periods_per_year)

    excess_return = returns - rf
    daily_sharpe = excess_return.mean() / excess_return.std()
    sharpe_ratio  = daily_sharpe * np.sqrt(periods_per_year)

    return sharpe_ratio


def sortino(returns: pd.Series, rf: float = 0.0, periods_per_year: int = TRADING_DAYS) -> float:
    downside_std = sqrt(mean)
    """Sortino: Sharpe gibi ama paydada sadece asagi yonlu oynaklik var.

    Ipucu: excess = r - rf/periods_per_year
           downside = sqrt(mean(clip(excess, upper=0) ** 2))  <- TUM gunler uzerinden ortalama
           mean(excess) / downside * sqrt(periods_per_year)
    """
    raise NotImplementedError


def calmar(returns: pd.Series, periods_per_year: int = TRADING_DAYS) -> float:
    """Calmar: CAGR / |max drawdown|."""
    raise NotImplementedError


# 4) dagilim ve gunler

def win_rate(returns: pd.Series) -> float:
    """Pozitif gecen gunlerin orani (0 ile 1 arasi)."""
    raise NotImplementedError


def best_day(returns: pd.Series) -> float:
    """En iyi gunun getirisi."""
    raise NotImplementedError


def worst_day(returns: pd.Series) -> float:
    """En kotu gunun getirisi."""
    raise NotImplementedError


def skewness(returns: pd.Series) -> float:
    """Carpiklik. pandas'in .skew() metoduyla ayni sonucu vermeli."""
    raise NotImplementedError


def kurtosis(returns: pd.Series) -> float:
    """Basiklik (excess kurtosis). pandas'in .kurt() metoduyla ayni sonucu vermeli."""
    raise NotImplementedError


def var_historic(returns: pd.Series, level: float = 0.05) -> float:
    """Tarihsel VaR: getirilerin level'inci yuzdelik dilimi (kotu gun esigi, negatif cikar).

    Ipucu: returns.quantile(level)
    """
    raise NotImplementedError


def cvar_historic(returns: pd.Series, level: float = 0.05) -> float:
    """CVaR / Expected Shortfall: VaR esiginin ALTINDA kalan gunlerin ortalamasi.

    Ipucu: returns[returns <= var_historic(returns, level)].mean()
    """
    raise NotImplementedError


def monthly_return_table(returns: pd.Series) -> pd.DataFrame:
    """Ay ay bilesik getiri tablosu: satir = yil, kolon = ay (1-12).

    Ipucu: once aylik bilesik getiri -> resample("ME").apply(...)
           sonra yil/ay pivotu. Isi haritasi bu tablodan cizilecek.
    """
    raise NotImplementedError


# 5) benchmark'a gore (iki seri ayni gunlere hizali gelir, data.align_pair halleder)

def beta(returns: pd.Series, benchmark: pd.Series) -> float:
    """CAPM beta: piyasa 1 birim oynayinca sen kac birim oynuyorsun.

    Ipucu: cov(r, b) / var(b)  (pandas .cov ve .var isini gorur)
    """
    raise NotImplementedError


def capm_alpha(returns: pd.Series, benchmark: pd.Series, rf: float = 0.0,
               periods_per_year: int = TRADING_DAYS) -> float:
    """Yillik CAPM alpha: beta'nin acikladigi kismin ustunde kalan getiri.

    Ipucu: rd = rf / periods_per_year
           gunluk_alpha = mean(r - rd) - beta * mean(b - rd)
           gunluk_alpha * periods_per_year
    """
    raise NotImplementedError


def r_squared(returns: pd.Series, benchmark: pd.Series) -> float:
    """Getirinin ne kadari piyasayla aciklaniyor. Ipucu: korelasyonun karesi."""
    raise NotImplementedError


def correlation(returns: pd.Series, benchmark: pd.Series) -> float:
    """Iki serinin korelasyonu."""
    raise NotImplementedError


def tracking_error(returns: pd.Series, benchmark: pd.Series,
                   periods_per_year: int = TRADING_DAYS) -> float:
    """Benchmark'tan sapmanin yillik oynakligi.

    Ipucu: aktif = r - b; std(aktif, ddof=1) * sqrt(periods_per_year)
    """
    raise NotImplementedError


def information_ratio(returns: pd.Series, benchmark: pd.Series,
                      periods_per_year: int = TRADING_DAYS) -> float:
    """Benchmark'i yenme becerisi / bunun icin alinan aktif risk.

    Ipucu: aktif = r - b; mean(aktif) / std(aktif, ddof=1) * sqrt(periods_per_year)
    """
    raise NotImplementedError


def up_capture(returns: pd.Series, benchmark: pd.Series) -> float:
    """Piyasanin YUKARI gunlerinde onun kacta kacini yakaliyorsun.

    Ipucu: mean(r[b > 0]) / mean(b[b > 0])
    """
    raise NotImplementedError


def down_capture(returns: pd.Series, benchmark: pd.Series) -> float:
    """Piyasanin ASAGI gunlerinde dususun kacta kacini yiyorsun (dusuk olmasi iyi).

    Ipucu: mean(r[b < 0]) / mean(b[b < 0])
    """
    raise NotImplementedError


# 6) rolling (kayan pencere) - grafiklerde kullanilacak

def rolling_volatility(returns: pd.Series, window: int,
                       periods_per_year: int = TRADING_DAYS) -> pd.Series:
    """Kayan pencerede yillik volatilite. Ipucu: rolling(window).std() * sqrt(...)"""
    raise NotImplementedError


def rolling_sharpe(returns: pd.Series, window: int, rf: float = 0.0,
                   periods_per_year: int = TRADING_DAYS) -> pd.Series:
    """Kayan pencerede Sharpe. Ipucu: rolling mean / rolling std (ddof=1) * sqrt(...)"""
    raise NotImplementedError


def rolling_beta(returns: pd.Series, benchmark: pd.Series, window: int) -> pd.Series:
    """Kayan pencerede beta.

    Ipucu: returns.rolling(window).cov(benchmark) / benchmark.rolling(window).var()
    """
    raise NotImplementedError
