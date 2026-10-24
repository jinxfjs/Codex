"""Run twice in fresh temporary report directories and compare every byte."""

from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from research_pipeline.pipeline import ARTIFACTS, run, sha256


def main() -> int:
    reports = ROOT / "reports"
    reports.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="repro_", dir=reports) as temporary:
        base = Path(temporary)
        first, second = base / "first", base / "second"
        run(ROOT, output=first)
        run(ROOT, output=second)
        for name in (*ARTIFACTS, "run_manifest.json"):
            if sha256(first / name) != sha256(second / name):
                raise RuntimeError(f"Reproducibility mismatch: {name}")
    print("PASS: two fresh synthetic runs produced identical bytes for all 4 output files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
