"""Replay the shareable evidence bundle using only Python's standard library.

Run ``python -m benchmarks.replay --evidence evidence`` from an extracted bundle.
This checks saved real-model outputs against synthetic oracles without making API
calls. It is a replay of execution evidence, not a new live service experiment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from benchmarks.scoring import score


def fingerprint(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    return hashlib.sha256(encoded.encode()).hexdigest()


def usage_cost(usage):
    """Recompute November 2nd list pricing from raw provider token categories."""
    inputs = usage["input_tokens"]
    outputs = usage["output_tokens"]
    writes = usage.get("cache_creation_input_tokens", 0) or 0
    reads = usage.get("cache_read_input_tokens", 0) or 0
    hour = (usage.get("cache_creation") or {}).get("ephemeral_1h_input_tokens", 0) or 0
    if any(type(n) is not int or n < 0 for n in (inputs, outputs, writes, reads, hour)) or hour > writes:
        raise ValueError("invalid usage")
    factor = 5 if inputs + writes + reads > 100000 else 1
    return factor * (inputs * 100 + outputs * 500 + (writes - hour) * 125 + hour * 200 + reads * 10)


def replay(evidence: Path):
    """Check case/request hashes, source-supported scores, and complete settled accounting."""
    manifest = json.loads((evidence / "manifest.json").read_text())
    cases = {}
    for case_id, expected_hash in manifest["case_hashes"].items():
        case = json.loads((evidence / "cases" / f"{case_id}.json").read_text())
        if fingerprint(case) != expected_hash:
            raise ValueError(f"case hash differs: {case_id}")
        cases[case_id] = case
    scorer = Path(__file__).with_name("scoring.py")
    if hashlib.sha256(scorer.read_bytes()).hexdigest() != manifest["code_hashes"]["benchmarks/scoring.py"]:
        raise ValueError("scorer differs from the version used in the experiment")
    started, finished = {}, {}
    groups = defaultdict(lambda: {"passed": 0, "runs": 0, "case_ids": set()})
    for line in (evidence / "events.jsonl").read_text().splitlines():
        event = json.loads(line)
        trial_id = event["trial_id"]
        if event["event"] == "started":
            if trial_id in started or fingerprint(event["request"]) != event["request_hash"]:
                raise ValueError("duplicate trial or altered request")
            started[trial_id] = event
        elif event["event"] == "finished":
            if trial_id in finished or trial_id not in started:
                raise ValueError("duplicate or unmatched completion")
            finished[trial_id] = event
        else:
            raise ValueError("unknown event")
    if set(started) != set(finished):
        raise ValueError("unsettled request")
    total_cost = 0
    for trial_id, finish in finished.items():
        start = started[trial_id]
        case = cases[start["case_id"]]
        entries = (case["flat_history"]["entries"] if start["arm"] == "flat_history" else
                   [entry for claim in case["synapse"]["claims"] for entry in claim["entries"]])
        response = finish["response"]
        expected_cost = usage_cost(response["usage"]) if response else start["reserved_nano_usd"]
        if finish["charged_nano_usd"] != expected_cost:
            raise ValueError("saved charge differs from provider usage or reservation")
        text = "\n".join(block["text"] for block in response.get("content", []) if block.get("type") == "text") if response else ""
        verdict = score(text, case["oracle"], {entry["entry_id"]: entry for entry in entries})
        passed = verdict["passed"] and not finish["error"] and response is not None and response["stop_reason"] == "end_turn"
        group = groups[(start["phase"], start["arm"])]
        group["passed"] += int(passed)
        group["runs"] += 1
        group["case_ids"].add(start["case_id"])
        total_cost += expected_cost
    if total_cost > manifest["budget_cap_nano_usd"]:
        raise ValueError("budget exceeded")
    results = [{"phase": phase, "arm": arm, "cases": len(value["case_ids"]),
                "runs": value["runs"], "passed": value["passed"]} for (phase, arm), value in sorted(groups.items())]
    saved = json.loads((evidence / "summary.json").read_text())
    if len(finished) != saved["completed_trials"] or abs(total_cost / 1e9 - saved["charged_usd"]) > 1e-12:
        raise ValueError("saved summary differs from the journal")
    for result in results:
        group = next(row for row in saved["groups"] if (row["phase"], row["arm"]) == (result["phase"], result["arm"]))
        if any(group[key] != result[key] for key in ("cases", "runs", "passed")):
            raise ValueError("saved success counts differ from replay")
    return {"verified": True, "trials": len(finished), "charged_usd": total_cost / 1e9, "groups": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, default=Path("evidence"))
    args = parser.parse_args()
    print(json.dumps(replay(args.evidence), indent=2))


if __name__ == "__main__":
    main()
