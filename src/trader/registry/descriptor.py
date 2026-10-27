"""Immutable executable configurations; closures never supply provenance."""

from dataclasses import dataclass

from trader.backtest import generators

from .canonical import canonical_json, sha256, strict_json
from .errors import RegistryError
from .validation import (
    BENCHMARK_KEYS,
    exact,
    invalid,
    names,
    params_object,
    validate_backtest,
    validate_params,
)


@dataclass(frozen=True, init=False)
class RunDescriptor:
    _json: str

    def __init__(self, config):
        if not isinstance(config, dict) or config.get("generator") not in {
            "strategy",
            *BENCHMARK_KEYS,
        }:
            raise RegistryError("REGISTRY_UNSUPPORTED_GENERATOR")
        # Storing the encoding makes nested caller dictionaries immutable too.
        try:
            encoded = canonical_json(config)
        except (TypeError, ValueError) as exc:
            raise RegistryError("REGISTRY_PREREG_INVALID", "descriptor") from exc
        c = strict_json(encoded)
        keys = {"kind", "generator", "schedule", "params", "backtest_params"}
        if c["generator"] == "strategy":
            exact(c, keys | {"universe", "asset_class"}, "descriptor")
            if c["kind"] != "strategy":
                invalid("kind")
            ids = names(c["universe"], "universe", sorted_required=True)
            exact(c["asset_class"], ids, "asset_class")
            classes = c["asset_class"].values()
        else:
            if c["generator"] == "moving_average_10m":
                keys.add("universe")
            exact(c, keys | {"instruments"}, "descriptor")
            exact(c["instruments"], BENCHMARK_KEYS[c["generator"]], "instruments")
            if c["kind"] != "baseline" or c["schedule"] != "monthly":
                invalid("baseline kind/schedule")
            if c["generator"] == "moving_average_10m":
                ids = names(c["universe"], "universe", sorted_required=True)
                if c["instruments"]["universe"] not in ("strategy", c["universe"]):
                    invalid("instruments.universe")
            else:
                values = list(c["instruments"].values())
                ids = names(values, "instruments") if values else set()
            classes = ()
        if c["schedule"] not in ("weekly", "monthly"):
            invalid("schedule")
        validate_params(c["params"], classes)
        validate_backtest(c["backtest_params"], ids, [1])
        object.__setattr__(self, "_json", encoded)

    @property
    def config(self):
        return strict_json(self._json)

    @property
    def config_hash(self):
        return sha256(self._json)

    @property
    def schedule(self):
        return self.config["schedule"]

    @property
    def instrument_ids(self):
        c = self.config
        ids = set(c["backtest_params"]["HALF_SPREAD"])
        ids.update(c.get("universe", ()))
        ids.update(c.get("asset_class", {}))
        if c["generator"] not in ("strategy", "moving_average_10m"):
            ids.update(c["instruments"].values())
        return ids


def build_generator(descriptor):
    if type(descriptor) is not RunDescriptor:
        raise RegistryError("REGISTRY_UNSUPPORTED_GENERATOR")
    c = descriptor.config
    p = params_object(c["params"])
    name = c["generator"]
    if name == "strategy":
        return generators.strategy_generator(c["universe"], c["asset_class"], p)
    if name == "moving_average_10m":
        return generators.moving_average_10m(c["universe"], p)
    if name == "cash":
        return generators.cash()
    return getattr(generators, name)(**c["instruments"], params=p)
