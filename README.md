# nanobot-eval

Evaluation framework for nanobot AI assistant. Clone this repo, point at your nanobot source and run.

## Quick Start

```bash
# Clone this repo
git clone https://github.com/harveysmurf/nanobot-eval.git
cd nanobot-eval

# Run with local nanobot source
python3 run_eval.py --nanobot-dir /path/to/nanobot -o results.json

# Run against a specific git revision (from remote repo)
python3 run_eval.py --nanobot-url https://github.com/HKUDS/nanobot --sha abc123
```

## Prerequisites

- Docker installed and running
- Python 3.10+
- `OPENAI_API_KEY` environment variable set (or in `~/.nanobot/config.json`)

## Usage

```bash
# Use local nanobot source
python3 run_eval.py --nanobot-dir ~/nanobot

# Use git revision from remote repo
python3 run_eval.py --nanobot-url https://github.com/HKUDS/nanobot --sha main

# Custom timeout per prompt (default: 60s)
python3 run_eval.py --nanobot-dir ~/nanobot -t 120

# Use custom prompts file
python3 run_eval.py --nanobot-dir ~/nanobot --prompts my_prompts.jsonl

# Skip Docker rebuild (use cached image)
python3 run_eval.py --nanobot-dir ~/nanobot --no-rebuild
```

## How It Works

1. **Build**: Copies nanobot source + eval scripts into Docker image
2. **Seed**: Initializes LCM database with seed data (context, conversations, memory)
3. **Run**: Each prompt runs in isolated container with seed memory
4. **Score**: Use `scorer.py` to evaluate response quality

## Prompt Format

```jsonl
{"id": "unique_id", "prompt": "Your prompt here", "lang": "en", "category": "basic"}
```

## Adding Prompts

Edit `prompts.jsonl` or create your own file:

```jsonl
{"id": "my_test_01", "prompt": "Hello!", "lang": "en", "category": "greeting"}
{"id": "my_test_02", "prompt": "Какво ще обядваме?", "lang": "bg", "category": "food"}
```

## Credentials

API key loaded from (in order of priority):
1. `OPENAI_API_KEY` environment variable
2. `~/.nanobot/config.json` → `api_key`

No secrets are stored in this repo. Results are saved locally (gitignored).

## Project Structure

```
nanobot-eval/
├── run_eval.py      # Main evaluation runner
├── scorer.py        # Response quality scorer
├── prompts.jsonl    # Test prompts
├── lcm_seed.sql     # Seed data for LCM database
├── Dockerfile      # Container image definition
└── README.md
```
