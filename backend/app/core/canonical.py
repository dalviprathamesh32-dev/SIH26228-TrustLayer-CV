import json
from typing import Any

def _normalize_obj(obj: Any) -> Any:
    """Recursively normalize objects to ensure canonical representation."""
    if isinstance(obj, dict):
        return {k: _normalize_obj(v) for k, v in sorted(obj.items())}
    elif isinstance(obj, (list, tuple)):
        return [_normalize_obj(item) for item in obj]
    elif isinstance(obj, float):
        # Round floats to 6 decimal places to prevent platform precision divergence
        return round(obj, 6)
    return obj

def canonicalize_json(data: Any) -> str:
    """
    Deterministically canonicalizes any JSON-serializable structure
    following RFC 8785 principles (sorted keys, minimal whitespace, consistent float serialization).
    """
    normalized = _normalize_obj(data)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(',', ':'),
        ensure_ascii=False
    )

def canonical_bytes(data: Any) -> bytes:
    """Returns UTF-8 encoded canonical JSON bytes."""
    return canonicalize_json(data).encode("utf-8")
