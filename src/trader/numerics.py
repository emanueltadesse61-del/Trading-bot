"""Shared numerical helpers (docs/portfolio-spec.md section 2.2)."""

import math
from collections.abc import Mapping

import numpy as np
import pandas as pd

from trader.errors import InvalidInputError
from trader.params import Params


def is_finite_number(value: object) -> bool:
    """True for a real, finite int or float (bool excluded)."""
    if isinstance(value, bool) or not isinstance(value, (int, float, np.integer, np.floating)):
        return False
    return math.isfinite(float(value))


def validate_covariance(cov: pd.DataFrame, params: Params) -> None:
    """Square, labelled consistently, finite, symmetric within SYM_TOL, PSD within PSD_TOL."""
    if not isinstance(cov, pd.DataFrame):
        raise InvalidInputError("INVALID_COVARIANCE", "covariance must be a DataFrame")
    if cov.shape[0] != cov.shape[1] or list(cov.index) != list(cov.columns):
        raise InvalidInputError("INVALID_COVARIANCE", "covariance must be square with matching labels")
    if cov.shape[0] == 0:
        return
    matrix = cov.to_numpy(dtype=float)
    if not np.all(np.isfinite(matrix)):
        raise InvalidInputError("INVALID_COVARIANCE", "non-finite entry")
    if np.max(np.abs(matrix - matrix.T)) > params.SYM_TOL:
        raise InvalidInputError("INVALID_COVARIANCE", "not symmetric within SYM_TOL")
    if np.min(np.linalg.eigvalsh((matrix + matrix.T) / 2.0)) < -params.PSD_TOL:
        raise InvalidInputError("INVALID_COVARIANCE", "eigenvalue below -PSD_TOL")


def portfolio_vol(weights: Mapping[str, float], cov: pd.DataFrame, params: Params) -> float:
    """sigma(x) = sqrt(max(0, x' S x)); raise if x' S x < -PSD_TOL.

    Every portfolio volatility in the system goes through this function.
    """
    missing = [k for k, v in weights.items() if v != 0.0 and k not in cov.index]
    if missing:
        raise InvalidInputError("INVALID_COVARIANCE", f"no covariance for {sorted(missing)}")
    x = np.array([float(weights.get(k, 0.0)) for k in cov.index], dtype=float)
    if x.size == 0:
        return 0.0
    q = float(x @ cov.to_numpy(dtype=float) @ x)
    if q < -params.PSD_TOL:
        raise InvalidInputError("INVALID_COVARIANCE", f"quadratic form {q} below -PSD_TOL")
    return math.sqrt(max(0.0, q))
