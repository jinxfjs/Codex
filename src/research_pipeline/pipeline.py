"""Execute validated layers and write aggregate outputs and provenance."""

import csv
import hashlib
import io
import json
from pathlib import Path
import platform
import subprocess

from . import __version__
from .analysis import summarize
from .cohort import build_cohort
from .config import load_config
from .data import load_participants


ARTIFACTS = ("cohort_flow.csv", "descriptive.csv", "report.md")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_text(rows: list[dict]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue()


def git_state(root: Path) -> dict:
    def git(*args):
        return subprocess.run(["git", "-C", str(root), *args], check=True,
                              capture_output=True, text=True, timeout=10).stdout.strip()
    try:
        if Path(git("rev-parse", "--show-toplevel")).resolve() != root:
            return {"commit": None, "dirty": None}
        dirty = bool(git("status", "--porcelain"))
        try:
            commit = git("rev-parse", "--verify", "HEAD")
        except subprocess.CalledProcessError:
            commit = None
        return {"commit": commit, "dirty": dirty}
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "dirty": None}


def run(root: Path, config_path="config/demo.toml", output=None) -> dict:
    config = load_config(root, config_path, output)
    records = load_participants(config.source, config.dictionary)
    cohort, flow = build_cohort(records, config.minimum_age)
    summary = summarize(cohort)
    report = (
        "# SYNTHETIC ONLY — workflow demonstration\n\n"
        f"Project: {config.project_id}\n\n"
        f"Input records: {len(records)}; retained records: {len(cohort)}.\n\n"
        "All values are fabricated. Statistics are unweighted and describe only the demo rows.\n"
        "No MASLD definition, clinical classification, population prevalence, confidence interval,\n"
        "hypothesis test or regression effect is calculated. Demo survey weights are not used.\n\n"
        "See cohort_flow.csv for sequential exclusions and descriptive.csv for aggregates.\n"
    )
    payloads = {"cohort_flow.csv": csv_text(flow), "descriptive.csv": csv_text(summary), "report.md": report}
    inputs = {p.relative_to(config.root).as_posix(): sha256(p)
              for p in (config.source, config.dictionary, config.config_path)}
    code_paths = sorted((config.root / "src").rglob("*.py")) + sorted((config.root / "scripts").glob("*.py"))
    code = {p.relative_to(config.root).as_posix(): sha256(p) for p in code_paths}
    manifest = {
        "schema_version": 1, "pipeline_version": __version__, "project_id": config.project_id,
        "data_mode": "synthetic", "estimation": "unweighted_synthetic_only",
        "python": platform.python_version(), "implementation": platform.python_implementation(),
        "git": git_state(config.root), "inputs_sha256": inputs, "code_sha256": code,
        "counts": {"input": len(records), "retained": len(cohort)},
        "outputs_sha256": {name: hashlib.sha256(text.encode("utf-8")).hexdigest()
                           for name, text in payloads.items()},
    }
    payloads["run_manifest.json"] = json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    # Validate all targets before writing. Output must not redirect through a symlink.
    for name in payloads:
        target = config.output / name
        if target.is_symlink() or (target.exists() and not target.is_file()):
            raise ValueError("Output targets must be regular files without symlinks")
    config.output.mkdir(parents=True, exist_ok=True)
    for name, content in payloads.items():
        (config.output / name).write_text(content, encoding="utf-8", newline="\n")
    return manifest
