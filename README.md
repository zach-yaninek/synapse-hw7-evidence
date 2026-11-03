# Synapse current fact retrieval benchmark

Synthetic execution evidence for Homework 7 by Zachary Yaninek.

Does Synapse help an agent recover the current, correctly attributed booking reference
from a noisy care history? The experiment compares the same model reading the full
authorized history, the actual Synapse brief, and a compact representation of that brief.
The revised caller removes whitespace and null optional fields while preserving accounts,
non-null values, provenance, availability states, and untrusted-text labels. It uses the
same model and answer instructions.

## Results

All three conditions answered 42/42 fresh test questions correctly: 14 synthetic cases,
each answered three times. "Fresh" means the cases were held out while selecting and
checking the caller change on six separate development cases. Repeated answers are
not independent cases.

| Condition | Correct answers | Mean input tokens | Median model call, seconds |
| --- | ---: | ---: | ---: |
| Flat history | 42/42 | 60,759 | 1.54 |
| Synapse | 42/42 | 7,356 | 1.29 |
| Revised caller | 42/42 | 5,575 | 1.26 |

Synapse used 87.9% fewer input tokens than the full-history baseline. The revised caller
used a further 24.2% fewer than the original Synapse caller. No accuracy advantage was
observed. Total estimated API cost for all 162 trials was $0.4227422, calculated from
recorded usage and Anthropic's published rates. The invoice has not been checked.

## Check the saved results

Download this repository, then run from its root with Python 3:

```sh
python3 -m benchmarks.replay --evidence evidence
```

This uses only Python's standard library and makes no network or model calls. It checks
case and request hashes, the scorer's hash, answers and citations, token-based charges,
and agreement with the saved success counts. A successful replay reports 162 verified
trials. `SHA256SUMS` covers the distributed files. On macOS, check it with
`shasum -a 256 -c SHA256SUMS`.

The repository contains:

- `evidence/cases/`: all twenty synthetic histories, expected answers, tool responses,
  audit results, delivered contexts, and measured context positions.
- `evidence/events.jsonl`: exact model requests and responses, call timings, usage,
  and budget accounting.
- `evidence/manifest.json`: experiment settings, case hashes, model, pricing, and counts.
- `evidence/revision.json`: the caller change and when it was frozen.
- `evidence/results.csv`, `scored-results.json`, and `summary.json`: scores and measurements.
- `evidence/validation.json` and `validation-pytest.txt`: validation results.
- `benchmarks/scoring.py` and `replay.py`: the independent scorer and replay tool.

## Experimental setup

Two scripted writers contributed observations through the real Synapse service running
locally with signed test identities, authentication, consent, HTTP, and SQLite storage.
One receiving agent read the brief and passed it to the model. This local experiment is
separate from the deployed HW6 demonstration. All people, organizations, references,
and observations are synthetic. Service source and credentials are not included here.

The full-history baseline contains the same authorized observations, including timestamps,
authors, source references, and outdated entries. Each synthetic world has one actual
service read. All model repetitions reuse that saved response. The generator fixed
expected references and source IDs before reads, independently of service verification.
The scorer requires exact reference values and current source IDs. Conflicts require
both accounts, and missing information requires abstention. Invalid or duplicate
citations fail.

Six development cases cover short and long ordinary histories, short and long corrected
histories, a conflict, and a missing reference. Fourteen fresh cases cross 32 or 256
entries, 10%, 50%, or 90% insertion depth, and ordinary or corrected information, plus
conflict and missing-reference controls. Cases use separate fixed random seeds.

Both original conditions ran twice per development case (24 trials). All passed, so
the caller change reduced context overhead. It passed two development retests per case
(12 trials). The change was frozen before any fresh calls. All three conditions then
ran three times per fresh case (126 trials), without further changes. Every call used
`claude-haiku-5-5`, low effort, and a 2,048-token output maximum. There were no automatic
retries, model fallback, or requested prompt caching. All results were retained.

## Repeat against authorized Synapse access

Replaying this repository checks saved evidence. A new service experiment requires an
authorized Synapse checkout containing the benchmark harness, Python 3.13, its `dev`
and `agents` dependencies, and permission to use a model API key. From that checkout:

```sh
python3.13 -m pytest -q
python3.13 -m benchmarks.experiment prepare --output benchmarks/evidence/current-fact
python3.13 -m benchmarks.experiment run --output benchmarks/evidence/current-fact --phase development
python3.13 -m benchmarks.experiment freeze --output benchmarks/evidence/current-fact
python3.13 -m benchmarks.experiment run --output benchmarks/evidence/current-fact --phase retest
python3.13 -m benchmarks.experiment run --output benchmarks/evidence/current-fact --phase test
python3.13 -m benchmarks.experiment verify --output benchmarks/evidence/current-fact
```

Only `run` makes paid calls. Set `ANTHROPIC_API_KEY` in the environment. Keep it outside
the evidence directory. The harness reserves each request's potential cost before
sending against a $10 total allowance across all phases. It settles completed calls at
recorded usage, retains reservations for unknown outcomes, and skips completed slots
when resuming. Use a separate output directory for each new experiment.

## Limits and contributions

This tests one current-fact task, two history sizes, fixed contributors, and one model.
Most distracting information is in other categories or older accounts. Search-based
or deduplicated baselines remain untested. Matching stored, attributed observations
does not establish that the observations are true. The experiment does not establish
historical recall, clinical correctness, prompt-injection resistance, production
reliability, or performance at larger scales. Model-call timing excludes preparation,
writes, consent, and retrieval. Local read timing is saved separately.

Zachary Yaninek selected the question, scope, model, protocol, and budget, and reviewed
the results and final report. Codex implemented the benchmark and scorer, ran validation
and experiments, analyzed the saved results, and prepared the report and evidence.

Sources: [Needle in a Haystack](https://github.com/gkamradt/needle-in-a-haystack)
(benchmark inspiration) and [Anthropic pricing](https://platform.claude.com/docs/en/about-claude/pricing)
(checked November 2nd, 2026).
