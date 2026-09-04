
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

def ulcer_index(returns: pd.Series, periods_per_year: int = TRADING_DAYS) -> float:
    wealth = (1 + returns).cumprod()
    running_peak = wealth.cummax().clip(lower=1.0)
    drawdown = wealth / running_peak - 1
    ui = np.sqrt(np.mean(drawdown ** 2))
    return ui

def annual_volatility(returns: pd.Series, periods_per_year: int = TRADING_DAYS) -> float:
    daily_vol = np.std(returns, ddof=1)
    annualized_vol = daily_vol * np.sqrt(periods_per_year)
    return annualized_vol 

def drawdown_series(returns: pd.Series) -> pd.Series:
    growth = (1+ returns).cumprod()
    peak = growth.cummax() 
    drawdown = (growth - peak)/ peak 
    return drawdown


def max_drawdown(returns: pd.Series) -> float:
    drawdown = drawdown_series(returns)
    mdd_value = drawdown.min()
    return mdd_value


def sharpe(returns: pd.Series, rf: float = 0.0, periods_per_year: int = TRADING_DAYS) -> float:
    excess_return = returns - rf/periods_per_year
    daily_sharpe = excess_return.mean() / (excess_return.std() + 1e-8)
    sharpe_ratio = daily_sharpe * np.sqrt(periods_per_year)
    return sharpe_ratio


def sortino(returns: pd.Series, rf: float = 0.0, periods_per_year: int = TRADING_DAYS) -> float:
    rf_daily = rf/periods_per_year
    downside_diff = (returns - rf_daily).clip(upper = 0)
    squared_diff = downside_diff **2
    downside_std = np.sqrt(np.mean(squared_diff))
    sortino_daily = ((returns - rf_daily).mean()) / (downside_std + 1e-8)
    sortino_annual = sortino_daily * np.sqrt(periods_per_year) 
    return sortino_annual


def calmar(returns: pd.Series, periods_per_year: int = TRADING_DAYS) -> float:
    cagr_ratio  = cagr(returns,periods_per_year)
    maximum_drawndown = max_drawdown(returns)
    calmar = cagr_ratio/np.abs(maximum_drawndown)
    return calmar

def win_rate(returns: pd.Series) -> float:
    wins = (returns > 0).sum()
    total = len(returns)
    win_rates = wins/total
    return win_rates


def best_day(returns: pd.Series) -> float:
    best_day_return = returns.max()
    return best_day_return


def worst_day(returns: pd.Series) -> float:
    worst_day_return = returns.min()
    return worst_day_return


def skewness(returns: pd.Series) -> float:
    skew = returns.skew()
    return skew


def kurtosis(returns: pd.Series) -> float:
    kurtosisis = returns.kurtosis()
    return kurtosisis


def var_historic(returns: pd.Series, level: float = 0.05) -> float:
    VaR = returns.quantile(level)
    return VaR


def cvar_historic(returns: pd.Series, level: float = 0.05) -> float:
    var_threshold = returns.quantile(level)
    CVaR_value = returns[returns < var_threshold].mean()
    return CVaR_value

def monthly_return_table(returns: pd.Series) -> pd.DataFrame:
    monthly_returns = returns.resample("ME").apply(lambda x: (1 + x).prod() - 1)

    
    monthly_returns.index = pd.MultiIndex.from_arrays(
        [monthly_returns.index.year, monthly_returns.index.month], 
        names=["Year", "Month"]
    )
    heatmap_table = monthly_returns.unstack(level="Month")
    
    return heatmap_table



def beta(returns: pd.Series, benchmark: pd.Series) -> float:
    cov_matrix = np.cov(returns,benchmark)
    cov_ri_rm = cov_matrix[0,1]
    variance_market = np.var(benchmark,ddof = 1)
    beta = cov_ri_rm/variance_market
    return beta


def capm_alpha(returns: pd.Series, benchmark: pd.Series, rf: float = 0.0,
               periods_per_year: int = TRADING_DAYS) -> float:
    rf_daily = rf/periods_per_year
    daily_alpha = np.mean(returns -rf_daily) - (beta(returns,benchmark) * np.mean(benchmark - rf_daily))
    annual_alpha = periods_per_year * daily_alpha 
    return annual_alpha


def r_squared(returns: pd.Series, benchmark: pd.Series) -> float:
    correlation = returns.corr(benchmark)
    r_2 = correlation **2
    return r_2


def correlation(returns: pd.Series, benchmark: pd.Series) -> float:
    corrr = returns.corr(benchmark)
    return corrr


def tracking_error(returns: pd.Series, benchmark: pd.Series,
                   periods_per_year: int = TRADING_DAYS) -> float:

    error = returns - benchmark
    tracking_err = error.std(ddof = 1) * np.sqrt(periods_per_year)
    return tracking_err


def information_ratio(returns: pd.Series, benchmark: pd.Series,
                      periods_per_year: int = TRADING_DAYS) -> float:
   
    excess = returns - benchmark
    ratio = excess.mean() / excess.std(ddof = 1) * np.sqrt(periods_per_year)
    return ratio

def up_capture(returns: pd.Series, benchmark: pd.Series) -> float:
    up_days = benchmark > 0
    up_captures = returns[up_days].mean() / benchmark[up_days].mean() 
    return up_captures

def down_capture(returns: pd.Series, benchmark: pd.Series) -> float:
    down_days = benchmark < 0
    down_captures = returns[down_days].mean() / benchmark[down_days].mean() 
    return down_captures



def rolling_volatility(returns: pd.Series, window: int,
                       periods_per_year: int = TRADING_DAYS) -> pd.Series:
    rolling_vol = returns.rolling(window = window).std() * np.sqrt(periods_per_year)
    return rolling_vol

def rolling_sharpe(returns: pd.Series, window: int, rf: float = 0.0,
                   periods_per_year: int = TRADING_DAYS) -> pd.Series:
    
    rf_daily = rf/periods_per_year
    excess = returns - rf_daily
    rol_sharpe = (excess.rolling(window = window).mean() / returns.rolling(window= window).std()) * np.sqrt(periods_per_year)
    return rol_sharpe

def rolling_beta(returns: pd.Series, benchmark: pd.Series, window: int) -> pd.Series:
    rolling_cov = returns.rolling(window = window).cov(benchmark)
    rolling_var = benchmark.rolling(window = window).var()
    rol_beta = rolling_cov/rolling_var
    return rol_beta
