"""One canonical encoding for configurations, events and strict input JSON."""

import hashlib
import json
import math


def _default(value):
    if isinstance(value, frozenset):
        return sorted(value)
    raise TypeError(type(value).__name__)


def canonical_json(value):
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=_default,
    )


def sha256(value):
    return hashlib.sha256(
        value.encode("utf-8") if isinstance(value, str) else value
    ).hexdigest()


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"duplicate key: {key}")
            result[key] = value
        return result

    def bad(value):
        raise ValueError(f"non-finite: {value}")

    def number(value):
        parsed = float(value)
        return parsed if math.isfinite(parsed) else bad(value)

    return json.loads(
        text, object_pairs_hook=pairs, parse_constant=bad, parse_float=number
    )
