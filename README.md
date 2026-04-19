# nanobot-eval

Evaluation framework for nanobot AI assistant.

## Setup

```bash
# Install dependencies
pip install openai tiktoken aiohttp pydantic

# Ensure nanobot repo is available locally
cd /path/to/nanobot  # nanobot source code
```

## Usage

```bash
# Run full eval (23 prompts)
python3 eval/run_eval.py --sha <git-sha> -o results.json

# Run specific prompts only
# Edit PROMPTS_FILE in run_eval.py or create custom prompts.jsonl

# Run with custom timeout per prompt
python3 eval/run_eval.py --sha <git-sha> -t 120
```

## How it works

1. Builds Docker image from nanobot source + seed LCM data
2. Runs each prompt in isolated container
3. Captures response and timing
4. Saves results to JSON

## Prompt Format

```jsonl
{"id": "unique_id", "prompt": "Your prompt here", "lang": "en", "category": "basic"}
```

## Adding New Prompts

1. Add entry to `prompts.jsonl`
2. Update categories as needed
3. Re-run eval

## Scoring

Use `scorer.py` to evaluate response quality:

```bash
python3 scorer.py results.json
```

## Credentials

API credentials are loaded from `~/.nanobot/config.json` and mounted into the Docker container at runtime. No secrets are stored in the repo.
