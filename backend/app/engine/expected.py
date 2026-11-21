"""Expected reopen probability per work order.

expected_p = method baseline x rain factor x low-lying factor, calibrated so the
city-wide expected total equals the observed total. Factors are data-driven
(observed reopen rate in each bin / overall rate), clipped to [0.7, 1.5] so
a noisy bin cannot dominate. Deterministic, no LLM.

Rain = mean of the two stations' rainfall over the 7 days starting on the
completion date (the week the fix is exposed to weather).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ..loader import Data

CLIP = (0.7, 1.5)


def _rain_week_mm(wo: pd.DataFrame, rain: pd.DataFrame) -> pd.Series:
    daily = rain.groupby("date")["rainfall_mm"].mean()
    full = daily.reindex(pd.date_range(daily.index.min(), daily.index.max() + pd.Timedelta(days=7)), fill_value=0.0)
    roll = full[::-1].rolling(7, min_periods=1).sum()[::-1]  # sum of day d..d+6
    return wo["completed_at"].dt.normalize().map(roll).fillna(0.0)


def _factor(rate_by_bin: pd.Series, overall: float) -> pd.Series:
    return (rate_by_bin / overall).clip(*CLIP)


def add_expected(data: Data, wo: pd.DataFrame) -> pd.DataFrame:
    """Return wo with rain_week_mm, expected_reopen_p columns."""
    out = wo.copy()
    y = out["reopened"].astype(float)
    overall = y.mean()

    out["rain_week_mm"] = _rain_week_mm(out, data.rain)
    ll = out["ward_code"].map(data.wards.set_index("ward_code")["low_lying_index"])
    out["low_lying_index"] = ll

    base = y.groupby(out["repair_method"]).transform("mean")

    rain_bin = pd.qcut(out["rain_week_mm"].rank(method="first"), 3, labels=False)
    ll_bin = pd.qcut(ll.rank(method="first"), 3, labels=False)
    rain_f = rain_bin.map(_factor(y.groupby(rain_bin).mean(), overall))
    ll_f = ll_bin.map(_factor(y.groupby(ll_bin).mean(), overall))

    raw = base * rain_f * ll_f
    out["expected_reopen_p"] = (raw * y.sum() / raw.sum()).clip(0.01, 0.95)
    out["rain_factor"] = rain_f
    out["low_lying_factor"] = ll_f
    return out


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - m) / d, (c + m) / d)
