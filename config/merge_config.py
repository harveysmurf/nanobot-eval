#!/usr/bin/env python3
"""Merge eval.config.json + secrets.env into a ready-to-use config.json.

Eliminates all runtime credential injection. The output is a complete
config file that can be COPY'd into Docker or used directly.

Usage:
    python3 merge_config.py --config eval.config.json --secrets ~/.nanobot/credentials/secrets.env -o config.json
    python3 merge_config.py --config ~/.nanobot/config.json --secrets ~/.nanobot/credentials/secrets.env -o config.json
"""

import argparse
import json
import re
import sys
from pathlib import Path

# Map of secrets.env variable names to config.json provider paths
KEY_MAP = {
    "MINIMAX_API_KEY": ("providers", "minimax", "apiKey"),
    "GROQ_API_KEY": ("providers", "groq", "apiKey"),
    "ZHIPU_API_KEY": ("providers", "zhipu", "apiKey"),
    "OPENAI_API_KEY": ("providers", "openai", "apiKey"),
    "ANTHROPIC_API_KEY": ("providers", "anthropic", "apiKey"),
    "DEEPSEEK_API_KEY": ("providers", "deepseek", "apiKey"),
    "OPENROUTER_API_KEY": ("providers", "openrouter", "apiKey"),
    "BRAVE_API_KEY": ("tools", "web", "search", "apiKey"),
    "HA_TOKEN": None,  # not a provider key
    "HA_SSH_PASSWORD": None,
}


def parse_secrets_env(path: Path) -> dict[str, str]:
    """Parse a KEY=VALUE env file, stripping quotes and comments."""
    env = {}
    if not path.exists():
        return env
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        env[key] = value
    return env


def set_nested(d: dict, path: tuple[str, ...], value: str) -> None:
    """Set a value in a nested dict, creating intermediate dicts as needed."""
    for key in path[:-1]:
        d = d.setdefault(key, {})
    d[path[-1]] = value


def merge(config_path: Path, secrets_path: Path) -> dict:
    """Merge config + secrets into a complete config dict."""
    with open(config_path) as f:
        config = json.load(f)

    secrets = parse_secrets_env(secrets_path)

    for env_key, config_path_tuple in KEY_MAP.items():
        if config_path_tuple is None:
            continue
        value = secrets.get(env_key, "")
        if value:
            set_nested(config, config_path_tuple, value)

    return config


def main():
    parser = argparse.ArgumentParser(description="Merge nanobot config with secrets")
    parser.add_argument("--config", "-c", required=True, help="Base config.json path")
    parser.add_argument("--secrets", "-s", required=True, help="secrets.env path")
    parser.add_argument("--output", "-o", default="-", help="Output path (- for stdout)")
    args = parser.parse_args()

    config = merge(Path(args.config), Path(args.secrets))

    if args.output == "-":
        json.dump(config, sys.stdout, indent=2, ensure_ascii=False)
        print()
    else:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"Wrote {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
