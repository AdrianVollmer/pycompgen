import argparse
import os
import sys
import time
from pathlib import Path

from .detectors import detect_packages
from .analyzers import analyze_packages
from .generators import generate_completions
from .cache import save_completions, get_cache_dir, save_source_script, get_source_path
from .logger import setup_logging
from .models import Shell


def main() -> None:
    args = parse_args()

    # Set up logging
    logger = setup_logging(args.verbose)

    shell = Shell(args.shell or os.path.basename(os.environ.get("SHELL", "bash")))
    cache_dir = args.cache_dir or get_cache_dir()
    source_script = get_source_path(cache_dir, shell)

    if args.source:
        try:
            # Print the source file contents and exit
            print(open(source_script, "r").read())
            sys.exit(0)
        except (FileNotFoundError, OSError):
            print("Source file does not exist or permission denied")
            sys.exit(1)

    check_cooldown_period(source_script, args, logger)

    try:
        run(shell, cache_dir, args.force, logger)
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        if args.verbose:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate shell completions for installed Python tools"
    )
    parser.add_argument(
        "--shell",
        type=str,
        help="Target shell (default: ${SHELL:-bash})",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        help="Override default cache directory",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force regeneration of all completions",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--source",
        action="store_true",
        help="Only write the source file contents to stdout",
    )
    parser.add_argument(
        "--cooldown-time",
        type=int,
        default=60,
        help="Minimum seconds between regenerations (default: 60)",
    )

    args = parser.parse_args()

    return args


def check_cooldown_period(source_script: Path, args, logger) -> None:
    # Check cooldown period (skip if --source was given, but we already handled that above)
    if source_script.exists() and not args.force:
        try:
            script_age = time.time() - source_script.stat().st_mtime
            if script_age < args.cooldown_time:
                remaining = args.cooldown_time - script_age
                logger.info(
                    f"Completions are fresh (last generated {script_age:.1f}s ago). "
                    f"Skipping regeneration. Use --force to override or wait {remaining:.1f}s."
                )
                sys.exit(0)
        except OSError:
            # If we can't stat the file, continue with regeneration
            pass


def run(shell: Shell, cache_dir: Path, force: bool, logger) -> None:
    # Detect installed packages
    logger.info("Detecting installed packages...")
    packages = detect_packages()
    logger.info(f"Found {len(packages)} packages")

    # Analyze for completion support
    logger.info("Analyzing packages for completion support...")
    completion_packages = analyze_packages(packages)
    logger.info(f"Found {len(completion_packages)} packages with completion support")

    # Generate completions
    logger.info(f"Generating completions for {shell.value}...")
    completions = generate_completions(completion_packages, shell)
    logger.info(f"Generated {len(completions)} completions")

    # Save to cache
    save_completions(completions, cache_dir, force=force)

    # Generate source script
    source_script = save_source_script(cache_dir, shell)

    logger.info(f"Completions saved to {cache_dir}")
    logger.info(f"Source script: {source_script}")


if __name__ == "__main__":
    main()
