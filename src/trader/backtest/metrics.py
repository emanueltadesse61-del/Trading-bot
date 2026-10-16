"""Descriptive run metrics; not Gate 3 statistics."""

import math
from statistics import mean, stdev


def compute_metrics(dates, nav, *, annualisation=252, fills=None):
    keys = [
        "ann_return",
        "ann_vol",
        "sharpe",
        "max_drawdown",
        "max_drawdown_sessions",
        "monthly_returns",
    ]
    if fills is not None:
        keys += ["turnover", "cost_drag"]
    result = dict.fromkeys(keys)
    result.update(insolvent_on=None, undefined={})
    for d, n in zip(dates, nav):
        if n <= 0:
            result["insolvent_on"] = d.isoformat()
            result["undefined"] = dict.fromkeys(keys, "NON_POSITIVE_NAV")
            return result
    t = len(nav) - 1
    if t < 1:
        raise ValueError("metrics require at least two session NAVs")
    returns = [b / a - 1 for a, b in zip(nav, nav[1:])]
    result["ann_return"] = (nav[-1] / nav[0]) ** (annualisation / t) - 1
    if t < 2:
        result["undefined"].update(ann_vol="SHORT_SERIES", sharpe="SHORT_SERIES")
    else:
        sd = stdev(returns)
        result["ann_vol"] = sd * math.sqrt(annualisation)
        if sd == 0:
            result["undefined"]["sharpe"] = "ZERO_STDEV"
        else:
            result["sharpe"] = mean(returns) / sd * math.sqrt(annualisation)
    peak, peak_index, drawdown, duration = nav[0], 0, 0.0, 0
    for j, n in enumerate(nav):
        if n >= peak:
            peak, peak_index = n, j
        else:
            drawdown = max(drawdown, 1 - n / peak)
            duration = max(duration, j - peak_index)
    result.update(max_drawdown=drawdown, max_drawdown_sessions=duration)
    month_ends = {}
    for d, n in zip(dates, nav):
        month_ends[d.strftime("%Y-%m")] = n
    monthly, previous = [], nav[0]
    for month, n in month_ends.items():
        monthly.append([month, n / previous - 1])
        previous = n
    result["monthly_returns"] = monthly
    if fills is not None:
        result["turnover"] = (
            sum(abs(f["qty"] * f["fill_price"]) for f in fills)
            / (2 * mean(nav))
            * annualisation
            / t
        )
        result["cost_drag"] = (
            sum(f["commission"] + f["spread_slippage_cost"] for f in fills)
            / mean(nav)
            * annualisation
            / t
        )
    return result
