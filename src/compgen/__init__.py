import argparse
import sys
from pathlib import Path
from typing import Optional

from .detectors import detect_packages
from .analyzers import analyze_packages
from .generators import generate_completions
from .cache import save_completions, get_cache_dir, save_source_script
from .logger import setup_logging, get_logger


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate shell completions for installed Python tools"
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
    
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging(args.verbose)
    
    try:
        # Detect installed packages
        logger.info("Detecting installed packages...")
        packages = detect_packages()
        logger.info(f"Found {len(packages)} packages")
        
        # Analyze for completion support
        logger.info("Analyzing packages for completion support...")
        completion_packages = analyze_packages(packages)
        logger.info(f"Found {len(completion_packages)} packages with completion support")
        
        # Generate completions
        logger.info("Generating completions...")
        completions = generate_completions(completion_packages)
        logger.info(f"Generated {len(completions)} completions")
        
        # Save to cache
        cache_dir = args.cache_dir or get_cache_dir()
        save_completions(completions, cache_dir, force=args.force)
        
        # Generate source script
        source_script = save_source_script(cache_dir)
        
        logger.info(f"Completions saved to {cache_dir}")
        logger.info(f"Source script: {source_script}")
        
        # Only print to console if verbose
        if args.verbose:
            print(f"Completions saved to {cache_dir}")
            print(f"Source script: {source_script}")
            print(f"Add this to your shell config: source {source_script}")
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        if args.verbose:
            print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
