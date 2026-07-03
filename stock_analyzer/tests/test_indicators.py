import numpy as np
import pandas as pd
import pytest

from stock_analyzer.analysis.indicators import compute_indicators


def _make_ohlcv(n=80, start=10.0, step=0.05, seed=0):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2025-01-01", periods=n, freq="D")
    close = start + np.cumsum(rng.normal(step, 0.2, size=n))
    close = np.clip(close, 1, None)
    high = close + rng.uniform(0, 0.3, size=n)
    low = close - rng.uniform(0, 0.3, size=n)
    open_ = close - rng.uniform(-0.2, 0.2, size=n)
    volume = rng.integers(100_000, 500_000, size=n)
    return pd.DataFrame(
        {"time": dates, "open": open_, "high": high, "low": low, "close": close, "volume": volume}
    )


def test_compute_indicators_adds_expected_columns():
    df = _make_ohlcv()
    out = compute_indicators(df)
    for col in ["sma20", "sma50", "rsi14", "macd", "macd_signal", "macd_hist", "bb_upper", "bb_lower"]:
        assert col in out.columns
    assert len(out) == len(df)


def test_rsi_bounds():
    df = _make_ohlcv(n=100)
    out = compute_indicators(df)
    valid = out["rsi14"].dropna()
    assert (valid >= 0).all() and (valid <= 100).all()


def test_missing_columns_raises():
    with pytest.raises(ValueError):
        compute_indicators(pd.DataFrame({"close": [1, 2, 3]}))


def test_uptrend_has_sma_below_price():
    n = 60
    close = np.linspace(10, 20, n)
    df = pd.DataFrame(
        {
            "time": pd.date_range("2025-01-01", periods=n),
            "open": close,
            "high": close + 0.1,
            "low": close - 0.1,
            "close": close,
            "volume": np.full(n, 200_000),
        }
    )
    out = compute_indicators(df)
    last = out.iloc[-1]
    assert last["close"] > last["sma20"] > last["sma50"]
