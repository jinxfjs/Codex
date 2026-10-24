"""Run from any working directory; config/output paths are repository-relative."""

import argparse
import csv
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from research_pipeline.pipeline import run


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the synthetic research workflow")
    parser.add_argument("--config", default="config/demo.toml")
    parser.add_argument("--output", help="Override output; must be a subdirectory of reports")
    args = parser.parse_args()
    try:
        result = run(ROOT, args.config, args.output)
    except (OSError, ValueError, csv.Error) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(f"SYNTHETIC ONLY: {result['counts']['input']} input, {result['counts']['retained']} retained")
    print(f"Outputs: {args.output or 'configured reports directory'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
