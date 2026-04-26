# grading_comparator

Tooling for comparing grading methodologies (rubrics, preference models, heuristics) over a shared dataset and analysing how the choice of grader affects model rankings.

## Why

When you grade the same model outputs with multiple methods — rubric A, rubric B, a preference model, a cheap heuristic — you usually get *different rankings*. This package quantifies the disagreement, surfaces the samples that drive it, and shows how much grader choice changes downstream selection (e.g. which top-k of a candidate pool you'd ship).

## Install

```bash
pip install -e .
# optional plots
pip install -e .[plot]
```

Only hard dependency is `PyYAML`. The package is pure-Python; metrics (Spearman, Kendall tau-b, Cohen's kappa, etc.) are implemented from scratch so no `scipy` or `numpy` are required.

## Layout

```
grading_comparator/
├── pyproject.toml
├── README.md
├── grading_comparator/
│   ├── cli.py                 # `compare_graders` entry point
│   ├── graders/               # abstraction layer
│   │   ├── base.py            #   Grader / Sample / GraderResult
│   │   ├── precomputed.py     #   load scores from CSV / JSON / JSONL
│   │   ├── rubric.py          #   rubric-as-file + weighted inline rubric
│   │   ├── preference.py      #   preference-model adapter
│   │   ├── heuristic.py       #   file- and callable-based heuristics
│   │   └── loader.py          #   factory: dict -> Grader
│   ├── metrics/               # statistical primitives
│   │   ├── correlation.py     #   Pearson / Spearman / Kendall tau-b
│   │   ├── agreement.py       #   agreement rate, kappa, top-k overlap
│   │   ├── distribution.py    #   per-grader summary stats
│   │   ├── bias.py            #   mean diff, optional group slices
│   │   └── ranking.py         #   average-tie ranks
│   ├── comparison/            # comparison engine
│   │   ├── engine.py          #   ComparisonEngine + ComparisonResult
│   │   ├── disagreement.py    #   top divergent samples (z-spread)
│   │   └── sensitivity.py     #   how top-k changes between graders
│   ├── experiments/           # config-driven experiments
│   │   ├── config.py          #   YAML loader -> ExperimentConfig
│   │   └── runner.py          #   end-to-end pipeline + report writer
│   └── plotting/plots.py      # optional matplotlib histograms / scatter
├── configs/example.yaml       # sample experiment
├── data/                      # 30 samples, four scoring methods
└── tests/                     # pytest suite
```

## CLI

```bash
compare_graders --config configs/example.yaml          # run the example
compare_graders --config my.yaml --plots               # also emit PNGs
compare_graders --config my.yaml --quiet               # no stdout summary
```

The CLI writes the following into `output_dir`:

| File | Description |
|---|---|
| `summary.json` | full machine-readable result |
| `pairwise_metrics.csv` | one row per grader pair (Spearman, Kendall, agreement, mean diff, kappa, top-k overlap) |
| `top_disagreements.csv` | samples with the largest z-score spread across graders |
| `distributions.csv` | per-grader mean / std / quartiles |
| `selection_shifts.csv` | top-k overlap by pair (when `top_k` is set in the config) |
| `plots/` | histograms + pairwise scatter, when `--plots` and matplotlib are available |

## Config schema

```yaml
name: my_experiment

dataset:
  path: data/dataset.csv      # optional; pins sample order + groups
  sample_id_col: sample_id
  group_col: domain           # optional; enables per-group bias slicing

graders:                      # >= 1 grader; types: rubric | preference_model | heuristic | precomputed
  - name: rubric_a
    type: rubric
    path: data/rubric_a_scores.csv
  - name: preference_model
    type: preference_model
    path: data/preference_scores.csv

binarise_threshold: 0.7       # optional; enables Cohen's kappa
top_k: 0.2                    # int, or float in (0,1] — fraction of dataset
max_disagreements: 20
plots: false

output_dir: runs/my_experiment
```

Score files can be CSV, TSV, JSONL or JSON, with `sample_id` and `score` columns/keys (overridable per grader via `sample_col` / `score_col`).

## Programmatic API

```python
from grading_comparator.experiments.config import load_config
from grading_comparator.experiments.runner import run_experiment, write_reports

cfg = load_config("configs/example.yaml")
result = run_experiment(cfg)

print(result.distributions)
for pair in result.pairwise:
    print(pair.grader_a, pair.grader_b, pair.spearman, pair.kendall_tau)

write_reports(result, cfg.resolved_output_dir, plots=True)
```

## Tests

```bash
pip install -e .[test]
pytest -q
```
