# nanobot-eval

Evaluation framework for [nanobot](https://github.com/harveysmurf/nanobot). Builds a Docker image from any git SHA and runs prompts against it.

## Quick Start

```bash
# Eval current HEAD
python3 run_eval.py --latest

# Eval specific commit
python3 run_eval.py --sha af16a35

# Eval with specific suite
python3 run_eval.py --latest --suite basic
python3 run_eval.py --sha af16a35 --suite memory --suite safety

# Score results
python3 scorer.py results/2341a37_20260419.json

# Compare against baseline
python3 compare.py baseline_scored.json results/2341a37_20260419_scored.json

# Promote new baseline
./promote_baseline.sh results/2341a37_20260419_scored.json
```

## How It Works

1. `run_eval.py` builds a Docker image from a nanobot git SHA
2. Config + secrets are merged at build time (no runtime injection)
3. LCM seed data is baked into the image
4. Each prompt runs in a fresh container
5. Results are saved as timestamped JSON

## Structure

```
nanobot-eval/
├── run_eval.py              # Build image from SHA, run prompts
├── scorer.py                # LLM-as-judge (uses nanobot's provider framework)
├── compare.py               # Diff two scored runs
├── promote_baseline.sh      # Promote scored run → committed baseline
├── baseline_scored.json     # Committed "known good" (git-tracked)
├── Dockerfile
├── entrypoint.sh
├── config/
│   └── merge_config.py      # Merge config.json + secrets.env
├── suites/
│   ├── basic.jsonl          # Greetings, math, format, code (10)
│   ├── memory.jsonl         # LCM memory recall (5)
│   ├── tools.jsonl          # Tool/skill usage (6)
│   └── safety.jsonl         # Guardrail tests (3)
├── fixtures/
│   ├── seed_lcm.py          # Generate LCM mock data
│   └── lcm_seed.sql         # SQL dump for Docker
└── results/                 # Timestamped outputs (gitignored)
```

## Workflow

```
run eval → score → compare against baseline → promote if good
```

```bash
python3 run_eval.py --latest
python3 scorer.py results/<sha>_<ts>.json
python3 compare.py baseline_scored.json results/<sha>_<ts>_scored.json
./promote_baseline.sh results/<sha>_<ts>_scored.json
git add baseline_scored.json && git commit -m "update baseline"
```

## Options

| Flag | Description |
|------|-------------|
| `--sha <sha>` | Evaluate a specific git commit |
| `--latest` | Evaluate current HEAD |
| `--branch <name>` | Evaluate latest on branch |
| `--suite <name>` | Run specific suite(s), repeatable |
| `--config <path>` | Custom config.json |
| `--secrets <path>` | Custom secrets.env |
| `--nanobot-dir <path>` | Nanobot git repo (default: ~/nanobot-dev) |
| `--timeout <sec>` | Per-prompt timeout (default: 60) |

## Scoring

Dimensions (0-1): **correctness**, **personality**, **tool_use**, **safety**, **format**

Category-specific weights and thresholds:

| Category | Threshold | Primary weight |
|----------|-----------|----------------|
| safety | 0.95 | 80% safety |
| math | 0.70 | correctness |
| code | 0.60 | 50% correctness |
| memory | 0.60 | 40% correctness |
| basic | 0.50 | balanced |

## Adding Prompts

Add `.jsonl` to `suites/`. Each line:
```json
{"id": "unique_id", "prompt": "...", "lang": "en", "category": "basic", "description": "...", "timeout": 60, "expected_keywords": ["word1"], "expect_refusal": false}
```
