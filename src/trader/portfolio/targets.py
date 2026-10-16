"""Target weights per docs/portfolio-spec.md section 5. Pure function."""

from dataclasses import dataclass

from trader.errors import InvalidInputError
from trader.numerics import is_finite_number, portfolio_vol, validate_covariance
from trader.params import Params
from trader.signals.core import Signals


@dataclass(frozen=True)
class TargetResult:
    weights: dict[str, float]
    cash: float
    eligible: list[str]
    ranking: list[str]
    top_n: list[str]
    w_trend: dict[str, float]
    w_mom: dict[str, float]
    combined: dict[str, float]
    after_asset_cap: dict[str, float]
    after_class_cap: dict[str, float]
    sigma_p_before_scale: float
    scale: float


def _validate(signals: Signals, asset_class: dict[str, str], params: Params) -> None:
    for instrument, cls in asset_class.items():
        if cls not in params.ASSET_CLASSES:
            raise InvalidInputError("INVALID_ASSET_CLASS", f"{instrument}: {cls!r}")
    for instrument, vol in signals.sigma.items():
        if not is_finite_number(vol) or float(vol) < 0.0:
            raise InvalidInputError("INVALID_SIGMA", f"{instrument}: {vol!r}")
    for name, values in (("trend_score", signals.trend_score), ("momentum_return", signals.momentum_return)):
        for instrument, value in values.items():
            if not is_finite_number(value):
                raise InvalidInputError("INVALID_SIGNAL", f"{name} {instrument}: {value!r}")
    validate_covariance(signals.cov, params)


def compute_targets(signals: Signals, asset_class: dict[str, str], params: Params) -> TargetResult:
    _validate(signals, asset_class, params)

    universe = sorted(
        i for i in signals.eligible
        if i in asset_class and i in signals.sigma and signals.sigma[i] >= params.MIN_VOL
    )
    for instrument in universe:
        if instrument not in signals.trend_score or instrument not in signals.momentum_return:
            raise InvalidInputError("INVALID_SIGNAL", f"{instrument}: missing score")
        if instrument not in signals.cov.index:
            raise InvalidInputError("INVALID_COVARIANCE", f"{instrument}: not in covariance")

    weights = {i: 0.0 for i in asset_class}
    if not universe:
        return TargetResult(
            weights=weights, cash=1.0, eligible=[], ranking=[], top_n=[], w_trend={}, w_mom={},
            combined={}, after_asset_cap={}, after_class_cap={}, sigma_p_before_scale=0.0, scale=1.0,
        )

    inverse_vol = {i: 1.0 / signals.sigma[i] for i in universe}
    trend_denominator = sum(inverse_vol.values())
    w_trend = {i: signals.trend_score[i] * inverse_vol[i] / trend_denominator for i in universe}

    ranking = sorted(universe, key=lambda i: (-signals.momentum_return[i], i))
    top_n = ranking[: min(params.TOP_N, len(universe))]
    momentum_denominator = sum(inverse_vol[i] for i in top_n)
    w_mom = {
        i: (inverse_vol[i] / momentum_denominator
            if i in top_n and signals.momentum_return[i] > 0 else 0.0)
        for i in universe
    }

    combined = {i: params.SLEEVE_TREND * w_trend[i] + params.SLEEVE_MOM * w_mom[i] for i in universe}
    after_asset_cap = {i: min(combined[i], params.ASSET_CAP) for i in universe}

    after_class_cap = dict(after_asset_cap)
    for cls in sorted({asset_class[i] for i in universe}):
        members = [i for i in universe if asset_class[i] == cls]
        total = sum(after_class_cap[i] for i in members)
        if total > params.CLASS_CAP:
            for i in members:
                after_class_cap[i] *= params.CLASS_CAP / total

    sigma_p = portfolio_vol(after_class_cap, signals.cov, params)
    scale = params.VOL_CEILING / sigma_p if sigma_p > params.VOL_CEILING else 1.0
    for i in universe:
        weights[i] = after_class_cap[i] * scale

    return TargetResult(
        weights=weights,
        cash=1.0 - sum(weights.values()),
        eligible=universe,
        ranking=ranking,
        top_n=top_n,
        w_trend=w_trend,
        w_mom=w_mom,
        combined=combined,
        after_asset_cap=after_asset_cap,
        after_class_cap=after_class_cap,
        sigma_p_before_scale=sigma_p,
        scale=scale,
    )
