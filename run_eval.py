#!/usr/bin/env python3
"""
Nanobot Eval Runner.

Usage:
    # Use local nanobot source
    python3 run_eval.py --nanobot-dir /path/to/nanobot -o results.json

    # Use git revision
    python3 run_eval.py --nanobot-url https://github.com/HKUDS/nanobot --sha abc123

    # With custom prompts
    python3 run_eval.py --nanobot-dir /path/to/nanobot --prompts custom.jsonl

    # Skip Docker rebuild (use cached image)
    python3 run_eval.py --nanobot-dir /path/to/nanobot --no-rebuild
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
import os
import tempfile
import hashlib
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

# Configuration
IMAGE_NAME = "nanobot-eval"
CONTAINER_NAME_PREFIX = "nanobot-eval"
WORKSPACE_DIR = Path(__file__).parent
PROMPTS_FILE = WORKSPACE_DIR / "prompts.jsonl"
RESULTS_DIR = WORKSPACE_DIR / "results"
DEFAULT_TIMEOUT = 60  # seconds per prompt


@dataclass
class EvalConfig:
    """Evaluation configuration."""
    nanobot_dir: Path
    nanobot_sha: str
    image_tag: str
    results_file: Path
    timeout: int
    model: str
    api_key: Optional[str] = None
    rebuild: bool = True


def run_cmd(cmd: list[str], check: bool = True, capture: bool = True, 
            timeout: int = 60, binary: bool = False) -> subprocess.CompletedProcess:
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
    """Get OpenAI API key from environment or config."""
    # First check environment
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        return api_key
    
    # Then check nanobot config
    try:
        config_path = Path.home() / ".nanobot" / "config.json"
        if config_path.exists():
            import json
            with open(config_path) as f:
                config = json.load(f)
                return config.get("api_key", config.get("OPENAI_API_KEY"))
    except:
        pass
    return None


def get_nanobot_sha(nanobot_dir: Path) -> str:
    """Get current git SHA of nanobot directory."""
    result = run_cmd(["git", "-C", str(nanobot_dir), "rev-parse", "HEAD"], capture=True)
    return result.stdout.strip()


def get_nanobot_url(nanobot_dir: Path) -> str:
    """Get remote URL of nanobot directory."""
    result = run_cmd(["git", "-C", str(nanobot_dir), "remote", "get-url", "origin"], capture=True)
    return result.stdout.strip()


def build_image(config: EvalConfig, dockerfile: Path) -> str:
    """Build Docker image from nanobot source."""
    nanobot_dir = config.nanobot_dir
    image_tag = config.image_tag
    
    # Create temp build context
    build_dir = Path("/tmp/nanobot-eval-build")
    if build_dir.exists():
        shutil.rmtree(build_dir)
    build_dir.mkdir(exist_ok=True)
    
    # Copy Dockerfile
    (build_dir / "Dockerfile").write_bytes(dockerfile.read_bytes())
    
    # Copy eval directory
    eval_src = WORKSPACE_DIR
    eval_dest = build_dir / "eval"
    shutil.copytree(eval_src, eval_dest, ignore=shutil.ignore_patterns("results", "__pycache__", "*.pyc"))
    
    # Copy nanobot source
    nanobot_dest = build_dir / "nanobot"
    shutil.copytree(nanobot_dir, nanobot_dest, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"))
    
    print(f"Building Docker image: {image_tag}")
    result = run_cmd([
        "docker", "build", "-t", image_tag, "-f", str(dockerfile),
        str(build_dir)
    ], timeout=300)
    
    if result.returncode != 0:
        print(f"Docker build failed:\n{result.stderr}")
        sys.exit(1)
    
    print(f"✅ Image built: {image_tag}")
    return image_tag


def run_prompt(image_tag: str, container_name: str, prompt: str, 
               api_key: Optional[str], timeout: int = DEFAULT_TIMEOUT) -> tuple[str, float]:
    """Run a single prompt in the container."""
    start = time.time()
    
    # Escape prompt for shell
    safe_prompt = prompt.replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')
    
    cmd = [
        "docker", "run", "--rm", "--name", container_name,
        "-e", f"OPENAI_API_KEY={api_key}" if api_key else "",
    ]
    
    # Remove empty env var if no key
    if not api_key:
        cmd.pop()
    
    cmd.extend([image_tag, "agent", "-m", safe_prompt])
    
    result = run_cmd(cmd, timeout=timeout)
    elapsed = time.time() - start
    return result.stdout.strip(), elapsed


def run_eval(config: EvalConfig) -> dict:
    """Run full evaluation."""
    results = []
    
    print(f"🚀 Eval for nanobot @ {config.nanobot_sha}")
    print(f"   Results: {config.results_file}")
    print()
    
    # Load prompts
    prompts = []
    with open(PROMPTS_FILE) as f:
        for line in f:
            if line.strip():
                prompts.append(json.loads(line))
    
    print(f"📋 Loaded {len(prompts)} prompts")
    print()
    
    # Build or load image
    dockerfile = WORKSPACE_DIR / "Dockerfile"
    if config.rebuild:
        build_image(config, dockerfile)
    else:
        print(f"Using cached image: {config.image_tag}")
    
    # Run each prompt
    for i, item in enumerate(prompts):
        prompt_id = item["id"]
        prompt_text = item["prompt"]
        category = item.get("category", "unknown")
        
        container_name = f"{CONTAINER_NAME_PREFIX}-{config.nanobot_sha[:8]}-{i}"
        
        print(f"[{i+1}/{len(prompts)}] {prompt_id}...", end=" ", flush=True)
        
        try:
            response, elapsed = run_prompt(
                config.image_tag, container_name, prompt_text,
                config.api_key, timeout=config.timeout
            )
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
            "nanobot_sha": config.nanobot_sha,
            "timestamp": datetime.now().isoformat(),
        }
        results.append(result)
        
        if success:
            print(f"✅ {elapsed:.1f}s")
        else:
            print(f"❌ {error}")
        
        time.sleep(0.5)
    
    # Save results
    config.results_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config.results_file, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Summary
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
    for cid in result.stdout.strip().split("\n"):
        if cid:
            subprocess.run(["docker", "rm", "-f", cid], capture_output=True)


def main():
    parser = argparse.ArgumentParser(description="Nanobot Eval Runner")
    parser.add_argument("--nanobot-dir", type=Path, help="Path to nanobot source")
    parser.add_argument("--nanobot-url", help="Git URL for nanobot (clone if no dir)")
    parser.add_argument("--sha", help="Git SHA (default: current HEAD)")
    parser.add_argument("--branch", default="main", help="Branch for --nanobot-url")
    parser.add_argument("--prompts", type=Path, help="Custom prompts file")
    parser.add_argument("-t", "--timeout", type=int, default=DEFAULT_TIMEOUT)
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument("--no-rebuild", action="store_true", help="Use cached image")
    parser.add_argument("--cleanup", action="store_true", help="Clean up containers first")
    
    args = parser.parse_args()
    
    # Resolve nanobot source
    nanobot_dir = None
    nanobot_sha = "local"
    
    if args.nanobot_dir:
        nanobot_dir = args.nanobot_dir.resolve()
        nanobot_sha = get_nanobot_sha(nanobot_dir)
    elif args.nanobot_url:
        clone_dir = Path(tempfile.mkdtemp(prefix="nanobot-clone-"))
        run_cmd(["git", "clone", "--depth=1", "-b", args.branch, args.nanobot_url, str(clone_dir)])
        nanobot_dir = clone_dir
        if args.sha:
            run_cmd(["git", "-C", str(clone_dir), "checkout", args.sha])
            nanobot_sha = args.sha
        else:
            nanobot_sha = get_nanobot_sha(nanobot_dir)
    else:
        # Try to find nanobot in common locations
        for candidate in [
            Path.home() / "nanobot",
            Path.home() / "nanobot-dev",
            Path("/home/simo/nanobot"),
            Path("/home/simo/nanobot-dev"),
        ]:
            if candidate.exists() and (candidate / "nanobot").exists():
                nanobot_dir = candidate
                nanobot_sha = get_nanobot_sha(nanobot_dir)
                break
        
        if not nanobot_dir:
            print("Error: No nanobot source found.")
            print("Use --nanobot-dir or --nanobot-url to specify location.")
            sys.exit(1)
    
    print(f"Using nanobot from: {nanobot_dir}")
    print(f"Git SHA: {nanobot_sha}")
    
    # Get API key
    api_key = get_api_key()
    if not api_key:
        print("Warning: No API key found (set OPENAI_API_KEY env var)")
    
    # Setup output path
    output_path = Path(args.output) if args.output else RESULTS_DIR / f"{nanobot_sha[:8]}.json"
    
    # Cleanup if requested
    if args.cleanup:
        cleanup_containers()
    
    # Create config
    config = EvalConfig(
        nanobot_dir=nanobot_dir,
        nanobot_sha=nanobot_sha,
        image_tag=f"{IMAGE_NAME}:{nanobot_sha[:8]}",
        results_file=output_path,
        timeout=args.timeout,
        model="gpt-4o",
        api_key=api_key,
        rebuild=not args.no_rebuild,
    )
    
    # Override prompts file if specified
    global PROMPTS_FILE
    if args.prompts:
        PROMPTS_FILE = args.prompts
    
    run_eval(config)


if __name__ == "__main__":
    main()
