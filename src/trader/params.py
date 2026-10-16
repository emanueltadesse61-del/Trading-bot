"""Strategy and planner parameters (docs/portfolio-spec.md section 1)."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Params:
    """Every value is fixed before any backtest; changing one is a new registered variant."""

    ANNUALISATION: int = 252
    TREND_LOOKBACKS: tuple[int, ...] = (63, 126, 252)
    MOM_LONG: int = 252
    MOM_SKIP: int = 21
    VOL_WINDOW: int = 60
    COV_WINDOW: int = 252
    TOP_N: int = 4
    SLEEVE_TREND: float = 0.5
    SLEEVE_MOM: float = 0.5
    ASSET_CAP: float = 0.25
    CLASS_CAP: float = 0.60
    VOL_CEILING: float = 0.10
    BAND: float = 0.02
    MIN_VOL: float = 0.005
    BUY_BUFFER: float = 0.005
    COMMISSION_RESERVE: float = 3.0
    TOL: float = 1e-9
    FLOOR_EPS: float = 1e-9
    SYM_TOL: float = 1e-12
    PSD_TOL: float = 1e-12
    ASSET_CLASSES: frozenset[str] = field(
        default_factory=lambda: frozenset({"equity", "bond", "real_asset"})
    )

    @property
    def window(self) -> int:
        """Sessions of valid closes needed for eligibility (253 with the defaults)."""
        return max(*self.TREND_LOOKBACKS, self.MOM_LONG, self.COV_WINDOW) + 1
