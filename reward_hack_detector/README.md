# reward_hack_detector

Automated detection of reward hacks in language-model training data.

Given `(prompt, output, reward [, reference])` samples, this tool surfaces cases
where the model is *gaming* the reward instead of behaving correctly. It assigns
each sample a **suspicion score** in `[0, 1]` and tags the type of hack
(`verbosity_exploitation`, `format_gaming`, `hallucinated_confidence`,
`keyword_stuffing`).

The package is stdlib-only by default; optional `sentence-transformers`
embeddings are supported but never required.

## Install

```bash
pip install -e .
# Optional: real semantic embeddings instead of bag-of-words cosine
pip install -e ".[embeddings]"
```

## Quick start

```bash
detect_reward_hacks --input examples/data.jsonl --top-k 5 \
    --report-json out.json --report-md out.md
```

Input is JSONL — one sample per line:

```json
{"id": "s1", "prompt": "...", "output": "...", "reward": 0.93, "reference": "..."}
```

`id`, `reference`, and any extra fields are optional. `output` may also be named
`response`; `reward` may be `score`.

## CLI

```
detect_reward_hacks --input data.jsonl
                    [--top-k 20]
                    [--report-json path.json]
                    [--report-md path.md]
                    [--use-embeddings] [--embedding-model NAME]
                    [--tag-threshold 0.4]
                    [--format table|json] [--quiet]
```

The CLI prints a ranked top-K table to stdout and (optionally) writes a
JSON + Markdown report.

## Architecture

```
reward_hack_detector/
├── data.py                # Sample dataclass + JSONL loader
├── signals/               # heuristics + learned signals
│   ├── length.py          # token_length, char_length, length_zscore
│   ├── lexical.py         # bow_cosine, jaccard, ngram_repetition, …
│   ├── format.py          # bullet/header/code-fence density
│   ├── confidence.py      # strong-claim vs hedge ratios
│   └── embedding.py       # optional sentence-transformers wrapper
├── detectors/             # one detector per hack pattern
│   ├── verbosity.py
│   ├── format_gaming.py
│   ├── hallucinated_confidence.py
│   └── keyword_stuffing.py
├── analysis/
│   ├── correlation.py     # Pearson; reward-vs-length correlation
│   ├── scoring.py         # combine detectors → SuspicionScore
│   ├── ranking.py         # top-K
│   └── clustering.py      # group high-reward, low-quality outputs
├── pipeline/
│   ├── runner.py          # detect(samples) → PipelineResult
│   └── report.py          # JSON + Markdown writers
└── cli.py                 # detect_reward_hacks entry point
```

## Detection strategies

- **Reward vs. semantic-correctness divergence.** When a `reference` is
  provided, embedding similarity (or a bag-of-words fallback) is compared to
  the reward; high reward + low agreement is a strong hack signal.
- **Reward / length correlation spikes.** Pearson correlation across the
  whole dataset is computed once and used to *boost* per-sample verbosity
  scores when training rewards are riding length.
- **Clustering of high-reward, low-quality outputs.** Suspicious samples are
  grouped by detector-score profile to surface recurring failure modes.
- **Rule-based + lexical-similarity checks.** Keyword stuffing, format gaming
  and overconfident-language detectors combine n-gram repetition,
  type-token ratio, structural-line ratios, prompt keyword echo, and
  confidence-vs-hedge ratios.

## Suspicion score

For each sample, every detector returns a score in `[0, 1]`. The aggregator
takes a weighted blend of the maximum and the mean of detectors firing above
the tag threshold, then multiplies by a sigmoid of the sample's reward
z-score so that the *same evidence* looks more suspicious on a high-reward
example. Samples are ranked by the resulting score.

## Output

JSON report (`--report-json`):

```json
{
  "n_samples": 15,
  "reward_length_correlation": 0.61,
  "hack_type_counts": {"verbosity_exploitation": 3, "keyword_stuffing": 2, ...},
  "top_suspicions": [
    {
      "sample_id": "verbose-1",
      "suspicion": 0.82,
      "primary_hack": "verbosity_exploitation",
      "tags": ["verbosity_exploitation", "keyword_stuffing"],
      "reasons": ["[verbosity_exploitation] length z-score +2.1 …", "..."],
      "detector_scores": {...},
      "reward": 0.97,
      "prompt_preview": "...",
      "output_preview": "..."
    }
  ],
  "clusters": [{"cluster_id": 1, "size": 3, "dominant_hack": "...", ...}]
}
```

Markdown report mirrors the JSON in human-readable form, with a per-sample
breakdown and a clusters section.

## Library use

```python
from reward_hack_detector import load_jsonl, detect

samples = load_jsonl("data.jsonl")
result = detect(samples, use_embeddings=False)

for s in result.top(10):
    print(s.sample_id, s.primary_hack, s.suspicion)
```

## Tests

```bash
python -m unittest discover -s tests
```

## License

MIT.
