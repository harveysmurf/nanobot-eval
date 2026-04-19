#!/usr/bin/env python3
"""
Nanobot Eval Runner.

Builds a Docker image from a git revision, runs prompts against it,
captures responses, and outputs results for scoring.

Usage:
    python3 run_eval.py --sha <git-sha>
    python3 run_eval.py --sha af16a35  # Use specific commit
    python3 run_eval.py --latest       # Use current HEAD
    python3 run_eval.py --branch main  # Use latest on branch
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass
from typing import Optional

# Configuration
IMAGE_NAME = "nanobot-eval"
CONTAINER_NAME_PREFIX = "nanobot-eval"
WORKSPACE_DIR = Path(__file__).parent
PROMPTS_FILE = WORKSPACE_DIR / "prompts.jsonl"
RESULTS_DIR = WORKSPACE_DIR / "results"
EVAL_DIR = Path(__file__).parent
DEFAULT_TIMEOUT = 60  # seconds per prompt


@dataclass
class EvalConfig:
    git_sha: str
    image_tag: str
    container_name: str
    results_file: Path
    timeout: int
    model: str
    api_key: Optional[str] = None


def run_cmd(cmd: list[str], check: bool = True, capture: bool = True, timeout: int = 60, binary: bool = False) -> subprocess.CompletedProcess:
    """Run a shell command."""
    result = subprocess.run(
        cmd,
        capture_output=capture,
        text=not binary,
        timeout=timeout,
    )
    if check and result.returncode != 0:
        print(f"Command failed: {' '.join(cmd)}")
        print(f"stderr: {result.stderr}")
        sys.exit(1)
    return result


def get_api_key() -> Optional[str]:
    """Get OpenAI API key from credentials."""
    try:
        result = subprocess.run(
            ["python3", "-c", 
             "from nanobot.credentials import get; print(get('OPENAI_API_KEY') or '')"
            ],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() or None
    except:
        return None


def build_image(git_sha: str, dockerfile: Path) -> str:
    """Build Docker image from git revision."""
    image_tag = f"{IMAGE_NAME}:{git_sha[:8]}"
    
    # Create temp build context
    build_dir = Path("/tmp/nanobot-eval-build")
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(exist_ok=True)
    
    # Copy Dockerfile
    (build_dir / "Dockerfile").write_bytes(dockerfile.read_bytes())
    
    # Copy eval directory (for LCM seed)
    eval_src = EVAL_DIR
    eval_dest = build_dir / "eval"
    shutil.copytree(eval_src, eval_dest, ignore=shutil.ignore_patterns("results", "__pycache__", "*.pyc"))
    
    # Also keep Python scripts we need
    (eval_dest / "seed_lcm.py").write_text((eval_src / "seed_lcm.py").read_text())
    
    # Get nanobot source from git
    result = run_cmd(["git", "archive", git_sha, "--prefix=source/"], capture=True, binary=True)
    tar_path = build_dir / "source.tar"
    tar_path.write_bytes(result.stdout if isinstance(result.stdout, bytes) else result.stdout.encode())
    
    # Extract tar to temp location first
    source_dir = build_dir / "source"
    if source_dir.exists():
        shutil.rmtree(source_dir)
    
    run_cmd(["tar", "-xf", str(tar_path), "-C", str(build_dir)], check=True)
    tar_path.unlink()
    
    # Move source/* contents to build_dir root (so we have nanobot/, bridge/, etc.)
    for item in source_dir.iterdir():
        dest = build_dir / item.name
        if dest.exists():
            if dest.is_dir():
                shutil.rmtree(dest)
            else:
                dest.unlink()
        shutil.move(str(item), str(dest))
    source_dir.rmdir()
    
    # Get root files from git (already included in archive, but ensure we have latest)
    for f in ["pyproject.toml", "README.md", "LICENSE"]:
        try:
            result = run_cmd(["git", "show", f"{git_sha}:{f}"], capture=True)
            if result.returncode == 0:
                (build_dir / f).write_text(result.stdout)
        except:
            pass
    
    # Generate LCM seed SQL first
    print("  Generating LCM seed data...")
    subprocess.run([sys.executable, str(eval_src / "seed_lcm.py")], check=True)
    seed_sql = eval_src / "lcm_seed.sql"
    if seed_sql.exists():
        shutil.copy(seed_sql, eval_dest / "lcm_seed.sql")
    
    print(f"Building Docker image: {image_tag}")
    
    # Build image
    result = run_cmd([
        "docker", "build", "-t", image_tag, "-f", str(dockerfile),
        str(build_dir)
    ], timeout=300)
    
    if result.returncode != 0:
        print(f"Docker build failed: {result.stderr}")
        sys.exit(1)
    
    print(f"✅ Image built: {image_tag}")
    return image_tag


def run_prompt(image_tag: str, container_name: str, prompt: str, timeout: int = DEFAULT_TIMEOUT) -> tuple[str, float]:
    """Run a single prompt in the container."""
    start = time.time()
    
    # Run nanobot agent with the prompt (escape for shell)
    safe_prompt = prompt.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
    
    # Mount config (read-only) to provide API credentials
    config_path = Path.home() / ".nanobot" / "config.json"
    
    result = run_cmd([
        "docker", "run", "--rm", "--name", container_name,
        "-v", f"{config_path}:/root/.nanobot/config.json:ro",
        image_tag,
        "agent", "-m", safe_prompt
    ], timeout=timeout)
    
    elapsed = time.time() - start
    return result.stdout.strip(), elapsed


def run_eval(config: EvalConfig) -> dict:
    """Run full evaluation."""
    git_sha = config.git_sha
    results = []
    
    print(f"🚀 Starting eval for git revision: {git_sha}")
    print(f"   Results will go to: {config.results_file}")
    print()
    
    # Load prompts
    prompts = []
    with open(PROMPTS_FILE) as f:
        for line in f:
            if line.strip():
                prompts.append(json.loads(line))
    
    print(f"📋 Loaded {len(prompts)} prompts")
    print()
    
    # Build Docker image
    dockerfile = Path(__file__).parent / "Dockerfile"
    image_tag = build_image(git_sha, dockerfile)
    
    # Run each prompt
    for i, item in enumerate(prompts):
        prompt_id = item["id"]
        prompt_text = item["prompt"]
        category = item.get("category", "unknown")
        
        container_name = f"{CONTAINER_NAME_PREFIX}-{git_sha[:8]}-{i}"
        
        print(f"[{i+1}/{len(prompts)}] {prompt_id}...", end=" ", flush=True)
        
        try:
            response, elapsed = run_prompt(config.image_tag, container_name, prompt_text, timeout=config.timeout)
            success = True
            error = None
        except subprocess.TimeoutExpired:
            response = ""
            elapsed = config.timeout
            success = False
            error = "Timeout"
            print("⏱️", end=" ")
        except Exception as e:
            response = ""
            elapsed = 0
            success = False
            error = str(e)
            print("❌", end=" ")
        
        result = {
            "id": prompt_id,
            "prompt": prompt_text,
            "category": category,
            "language": item.get("lang", "unknown"),
            "description": item.get("description", ""),
            "response": response,
            "success": success,
            "error": error,
            "elapsed_seconds": round(elapsed, 2),
            "git_sha": git_sha,
            "timestamp": datetime.now().isoformat(),
        }
        results.append(result)
        
        if success:
            print(f"✅ {elapsed:.1f}s")
        else:
            print(f"❌ {error}")
        
        # Small delay between prompts
        time.sleep(0.5)
    
    # Save results
    config.results_file.parent.mkdir(exist_ok=True)
    with open(config.results_file, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Print summary
    success_count = sum(1 for r in results if r["success"])
    print()
    print(f"✅ Eval complete!")
    print(f"   Successful: {success_count}/{len(results)}")
    print(f"   Results: {config.results_file}")
    
    return {"results": results, "summary": {
        "total": len(results),
        "successful": success_count,
        "failed": len(results) - success_count,
    }}


def cleanup_containers(prefix: str = CONTAINER_NAME_PREFIX):
    """Clean up any leftover containers."""
    result = subprocess.run(
        ["docker", "ps", "-a", "--filter", f"name={prefix}", "-q"],
        capture_output=True, text=True
    )
    container_ids = result.stdout.strip().split("\n")
    for cid in container_ids:
        if cid:
            subprocess.run(["docker", "rm", "-f", cid], capture_output=True)


def main():
    parser = argparse.ArgumentParser(description="Nanobot Eval Runner")
    parser.add_argument("--sha", help="Git SHA to evaluate")
    parser.add_argument("--latest", action="store_true", help="Use current HEAD")
    parser.add_argument("--branch", default="main", help="Branch to use")
    parser.add_argument("-t", "--timeout", type=int, default=DEFAULT_TIMEOUT, help="Timeout per prompt")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument("--cleanup", action="store_true", help="Clean up containers first")
    
    args = parser.parse_args()
    
    # Determine git revision
    if args.sha:
        git_sha = args.sha
    elif args.latest:
        result = run_cmd(["git", "rev-parse", "HEAD"], capture=True)
        git_sha = result.stdout.strip()
    else:
        result = run_cmd(["git", "rev-parse", args.branch], capture=True)
        git_sha = result.stdout.strip()
    
    print(f"Git revision: {git_sha}")
    
    # Setup output path
    output_path = Path(args.output) if args.output else RESULTS_DIR / f"{git_sha[:8]}.json"
    
    # Cleanup if requested
    if args.cleanup:
        cleanup_containers()
    
    # Run eval
    config = EvalConfig(
        git_sha=git_sha,
        image_tag=f"{IMAGE_NAME}:{git_sha[:8]}",
        container_name=f"{CONTAINER_NAME_PREFIX}-{git_sha[:8]}",
        results_file=output_path,
        timeout=args.timeout,
        model="gpt-4o",
        api_key=get_api_key(),
    )
    
    run_eval(config)


if __name__ == "__main__":
    main()
