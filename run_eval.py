#!/usr/bin/env python3
"""Nanobot Eval Runner.

Builds a Docker image from a nanobot git revision, runs prompts against it,
and captures responses for scoring.

Usage:
    python3 run_eval.py --sha af16a35
    python3 run_eval.py --latest
    python3 run_eval.py --branch main --suite basic
    python3 run_eval.py --sha af16a35 --suite memory --suite safety
    python3 run_eval.py --latest --config ~/my_eval.config.json --secrets ~/.nanobot/credentials/secrets.env
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

REPO_DIR = Path(__file__).parent
SUITES_DIR = REPO_DIR / "suites"
RESULTS_DIR = REPO_DIR / "results"
FIXTURES_DIR = REPO_DIR / "fixtures"
CONFIG_DIR = REPO_DIR / "config"
IMAGE_NAME = "nanobot-eval"
DEFAULT_TIMEOUT = 60
DEFAULT_NANOBOT_DIR = Path.home() / "nanobot-dev"


@dataclass
class RunConfig:
    git_sha: str
    nanobot_dir: Path
    suites: list[str] = field(default_factory=lambda: ["all"])
    timeout: int = DEFAULT_TIMEOUT
    config_path: Optional[Path] = None
    secrets_path: Optional[Path] = None
    results_file: Optional[Path] = None


def load_suites(names: list[str]) -> list[dict]:
    prompts = []
    if "all" in names:
        suite_files = sorted(SUITES_DIR.glob("*.jsonl"))
    else:
        suite_files = []
        for name in names:
            f = SUITES_DIR / f"{name}.jsonl"
            if not f.exists():
                available = [p.stem for p in SUITES_DIR.glob("*.jsonl")]
                print(f"Suite not found: {name}")
                print(f"Available: {', '.join(available)}")
                sys.exit(1)
            suite_files.append(f)

    for sf in suite_files:
        for line in sf.read_text().splitlines():
            if line.strip():
                item = json.loads(line)
                item["suite"] = sf.stem
                prompts.append(item)
    return prompts


def run_cmd(cmd: list[str], timeout: int = 120, check: bool = True, binary: bool = False,
            cwd: str | None = None) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, capture_output=True, text=not binary, timeout=timeout, cwd=cwd)
    if check and result.returncode != 0:
        print(f"Command failed: {' '.join(cmd)}")
        if result.stderr:
            print(f"stderr: {result.stderr[:500]}")
        sys.exit(1)
    return result


def merge_config(config_path: Path, secrets_path: Path) -> Path:
    output = CONFIG_DIR / "merged_config.json"
    run_cmd([
        sys.executable, str(CONFIG_DIR / "merge_config.py"),
        "--config", str(config_path),
        "--secrets", str(secrets_path),
        "-o", str(output),
    ])
    return output


def build_image(git_sha: str, nanobot_dir: Path) -> str:
    image_tag = f"{IMAGE_NAME}:{git_sha[:8]}"
    build_dir = Path("/tmp/nanobot-eval-build")
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir()

    # Extract nanobot source from git
    result = run_cmd(["git", "archive", git_sha, "--prefix=source/"], binary=True,
                     cwd=str(nanobot_dir))
    tar_path = build_dir / "source.tar"
    tar_path.write_bytes(result.stdout if isinstance(result.stdout, bytes) else result.stdout.encode())
    run_cmd(["tar", "-xf", str(tar_path), "-C", str(build_dir)])
    tar_path.unlink()

    source_dir = build_dir / "source"
    for item in source_dir.iterdir():
        dest = build_dir / item.name
        if dest.exists():
            shutil.rmtree(dest) if dest.is_dir() else dest.unlink()
        shutil.move(str(item), str(dest))
    source_dir.rmdir()

    # Copy eval fixtures and config into build context
    eval_dest = build_dir / "eval"
    eval_dest.mkdir(exist_ok=True)
    for subdir in ["fixtures", "config"]:
        src = REPO_DIR / subdir
        if src.exists():
            shutil.copytree(src, eval_dest / subdir, ignore=shutil.ignore_patterns("*.db", "__pycache__"))
    shutil.copy(REPO_DIR / "entrypoint.sh", eval_dest / "entrypoint.sh")

    print(f"Building image: {image_tag}")
    run_cmd(["docker", "build", "-t", image_tag, "-f", str(REPO_DIR / "Dockerfile"), str(build_dir)],
            timeout=300)
    print(f"Image built: {image_tag}")
    return image_tag


def run_prompt(image_tag: str, prompt: str, timeout: int, run_idx: int) -> tuple[str, float]:
    container_name = f"nanobot-eval-{run_idx}"
    safe_prompt = prompt.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')

    start = time.time()
    result = subprocess.run(
        ["docker", "run", "--rm", "--name", container_name, image_tag, "agent", "-m", safe_prompt],
        capture_output=True, text=True, timeout=timeout,
    )
    elapsed = time.time() - start
    return result.stdout.strip(), elapsed


def run_eval(config: RunConfig) -> dict:
    prompts = load_suites(config.suites)
    suite_names = ", ".join(sorted(set(p["suite"] for p in prompts)))

    short_sha = config.git_sha[:8]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = config.results_file or (RESULTS_DIR / f"{short_sha}_{ts}.json")
    results_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"SHA: {config.git_sha}")
    print(f"Nanobot dir: {config.nanobot_dir}")
    print(f"Suites: {suite_names} ({len(prompts)} prompts)")
    print(f"Output: {results_file}")
    print()

    # Merge config + secrets
    cfg = config.config_path or Path.home() / ".nanobot" / "config.json"
    sec = config.secrets_path or Path.home() / ".nanobot" / "credentials" / "secrets.env"
    print("Merging config + secrets...")
    merge_config(cfg, sec)

    # Generate seed data
    print("Generating LCM seed data...")
    run_cmd([sys.executable, str(FIXTURES_DIR / "seed_lcm.py")])

    # Build image
    image_tag = build_image(config.git_sha, config.nanobot_dir)
    print()

    # Run prompts
    results = []
    for i, item in enumerate(prompts):
        prompt_id = item["id"]
        prompt_text = item["prompt"]
        item_timeout = item.get("timeout", config.timeout)

        print(f"[{i+1}/{len(prompts)}] {prompt_id}...", end=" ", flush=True)

        try:
            response, elapsed = run_prompt(image_tag, prompt_text, item_timeout, i)
            success = True
            error = None
        except subprocess.TimeoutExpired:
            response, elapsed, success, error = "", item_timeout, False, "timeout"
        except Exception as e:
            response, elapsed, success, error = "", 0, False, str(e)

        result = {
            "id": prompt_id,
            "suite": item.get("suite", "unknown"),
            "prompt": prompt_text,
            "category": item.get("category", "unknown"),
            "language": item.get("lang", "en"),
            "description": item.get("description", ""),
            "expected_keywords": item.get("expected_keywords", []),
            "expect_refusal": item.get("expect_refusal", False),
            "response": response,
            "success": success,
            "error": error,
            "elapsed_seconds": round(elapsed, 2),
            "git_sha": config.git_sha,
            "timestamp": datetime.now().isoformat(),
        }
        results.append(result)
        status = f"{elapsed:.1f}s" if success else f"{error}"
        print(f"{'OK' if success else 'FAIL'} {status}")

        time.sleep(0.3)

    with open(results_file, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    ok = sum(1 for r in results if r["success"])
    print(f"\nDone: {ok}/{len(results)} successful")
    print(f"Results: {results_file}")

    return {"results_file": str(results_file), "total": len(results), "successful": ok}


def main():
    parser = argparse.ArgumentParser(description="Nanobot Eval Runner")

    rev = parser.add_mutually_exclusive_group(required=True)
    rev.add_argument("--sha", help="Git SHA to evaluate")
    rev.add_argument("--latest", action="store_true", help="Use current HEAD")
    rev.add_argument("--branch", help="Use latest commit on branch")

    parser.add_argument("--suite", "-s", action="append", default=[], help="Suite(s) to run (default: all)")
    parser.add_argument("--timeout", "-t", type=int, default=DEFAULT_TIMEOUT, help="Default timeout per prompt")
    parser.add_argument("--config", "-c", help="Config file path")
    parser.add_argument("--secrets", help="secrets.env path")
    parser.add_argument("--output", "-o", help="Output results file path")
    parser.add_argument("--nanobot-dir", "-d", default=str(DEFAULT_NANOBOT_DIR), help="Path to nanobot git repo (default: ~/nanobot-dev)")

    args = parser.parse_args()

    nanobot_dir = Path(args.nanobot_dir).expanduser()
    if not (nanobot_dir / ".git").exists():
        print(f"Error: {nanobot_dir} is not a git repository")
        sys.exit(1)

    if args.sha:
        git_sha = args.sha
    elif args.latest:
        git_sha = run_cmd(["git", "rev-parse", "HEAD"], cwd=str(nanobot_dir)).stdout.strip()
    else:
        git_sha = run_cmd(["git", "rev-parse", args.branch], cwd=str(nanobot_dir)).stdout.strip()

    # Resolve short SHA to full
    git_sha = run_cmd(["git", "rev-parse", git_sha], cwd=str(nanobot_dir)).stdout.strip()

    rc = RunConfig(
        git_sha=git_sha,
        nanobot_dir=nanobot_dir,
        suites=args.suite or ["all"],
        timeout=args.timeout,
        config_path=Path(args.config) if args.config else None,
        secrets_path=Path(args.secrets) if args.secrets else None,
        results_file=Path(args.output) if args.output else None,
    )

    run_eval(rc)


if __name__ == "__main__":
    main()
