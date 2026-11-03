"""Independent exact-answer and source-citation scoring; standard library only.

Shared by the live benchmark and the standalone public evidence replay.
No record-service helpers or model judgments determine correctness.
"""

from __future__ import annotations

import json
from typing import Any


def score(output: str, oracle: dict[str, Any], supplied: dict[int, dict[str, Any]]) -> dict[str, Any]:
    """Strict, deterministic result check, independent of the service's verifier."""
    errors: list[str] = []

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate field")
            result[key] = value
        return result

    try:
        parsed = json.loads(output, object_pairs_hook=unique,
                            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("non-finite")))
        if not isinstance(parsed, dict) or set(parsed) != {"status", "answers"}:
            raise ValueError("object fields")
        if parsed["status"] not in {"answer", "conflict", "unknown"} or not isinstance(parsed["answers"], list):
            raise ValueError("answer structure")
        actual = []
        for answer in parsed["answers"]:
            if (not isinstance(answer, dict) or set(answer) != {"value", "entry_id"}
                    or not isinstance(answer["value"], str) or type(answer["entry_id"]) is not int):
                raise ValueError("citation structure")
            actual.append((answer["value"], answer["entry_id"]))
            cited = supplied.get(answer["entry_id"])
            if cited is None or not answer["value"] or answer["value"] not in cited["untrusted"]["value"]:
                errors.append("invalid_citation")
        expected = [(a["value"], a["entry_id"]) for a in oracle["answers"]]
        if sorted(actual) != sorted(expected):
            errors.append("wrong_or_missing_value_or_source")
        if parsed["status"] != oracle["status"]:
            errors.append("wrong_status")
    except (ValueError, TypeError, KeyError):
        parsed = None
        errors.append("invalid_json_or_schema")
    return {"passed": not errors, "errors": sorted(set(errors)), "parsed": parsed}

