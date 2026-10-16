"""Errors raised for invalid inputs (docs/portfolio-spec.md section 2.1)."""

INPUT_ERROR_CODES = frozenset({
    "INVALID_CALENDAR",
    "INVALID_PRICE_SERIES",
    "INVALID_ASSET_CLASS",
    "INVALID_SIGMA",
    "INVALID_SIGNAL",
    "INVALID_COVARIANCE",
    "INVALID_HOLDING",
    "INVALID_CASH",
    "INVALID_PRICE",
})


class InvalidInputError(ValueError):
    """An input that is a bug or an upstream data failure, not a market state.

    The scheduled run records BLOCKED_INVALID_INPUT, alerts and places no orders.
    """

    def __init__(self, code: str, detail: str = "") -> None:
        if code not in INPUT_ERROR_CODES:
            raise ValueError(f"unknown input error code: {code}")
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}" if detail else code)
