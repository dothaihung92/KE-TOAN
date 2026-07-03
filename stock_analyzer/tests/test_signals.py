import numpy as np
import pandas as pd

from stock_analyzer.analysis.indicators import compute_indicators
from stock_analyzer.analysis.signals import compute_signal


def _trend_df(n, start, end):
    close = np.linspace(start, end, n)
    return pd.DataFrame(
        {
            "time": pd.date_range("2025-01-01", periods=n),
            "open": close,
            "high": close + 0.1,
            "low": close - 0.1,
            "close": close,
            "volume": np.full(n, 200_000),
        }
    )


def test_strong_uptrend_gives_positive_score():
    df = compute_indicators(_trend_df(80, 10, 25))
    signal = compute_signal(df)
    assert signal.score > 0
    assert signal.reasons


def test_strong_downtrend_gives_negative_score():
    df = compute_indicators(_trend_df(80, 25, 10))
    signal = compute_signal(df)
    assert signal.score < 0


def test_empty_dataframe_neutral():
    signal = compute_signal(pd.DataFrame())
    assert signal.score == 0.0


def test_score_within_bounds():
    df = compute_indicators(_trend_df(80, 10, 100))
    signal = compute_signal(df)
    assert -1.0 <= signal.score <= 1.0
