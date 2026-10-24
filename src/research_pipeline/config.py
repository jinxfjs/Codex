"""Read the explicit demo contract; fail before touching output on mistakes."""

from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class Config:
    root: Path
    config_path: Path
    project_id: str
    source: Path
    dictionary: Path
    output: Path
    minimum_age: int


def inside(root: Path, value: str | Path) -> Path:
    path = (root / value).resolve()
    if not path.is_relative_to(root):
        raise ValueError("Path must stay inside the repository")
    return path


def load_config(root: Path, path: str | Path, output: str | Path | None = None) -> Config:
    root = root.resolve()
    config_path = inside(root, path)
    with config_path.open("rb") as handle:
        raw = tomllib.load(handle)
    if not isinstance(raw.get("project"), dict):
        raise ValueError("Config requires a [project] section")
    if raw["project"].get("data_mode") != "synthetic":
        raise ValueError("Only synthetic mode is implemented; complete the real-study modules first")
    expected = {
        "project": {"id", "name", "data_mode"},
        "paths": {"source", "dictionary", "output"},
        "cohort": {"minimum_age"},
    }
    if set(raw) != set(expected):
        raise ValueError("Config sections must be project, paths and cohort")
    for section, keys in expected.items():
        if not isinstance(raw[section], dict) or set(raw[section]) != keys:
            raise ValueError(f"Invalid or missing keys in [{section}]")
    for section in ("project", "paths"):
        if any(not isinstance(v, str) or not v.strip() for v in raw[section].values()):
            raise ValueError(f"[{section}] requires nonempty strings")
    minimum_age = raw["cohort"]["minimum_age"]
    if type(minimum_age) is not int or not 0 <= minimum_age <= 120:
        raise ValueError("minimum_age must be an integer between 0 and 120")
    source = inside(root, raw["paths"]["source"])
    synthetic = inside(root, "data/synthetic")
    if not source.is_relative_to(synthetic):
        raise ValueError("Demo input must be inside data/synthetic")
    destination = inside(root, output if output is not None else raw["paths"]["output"])
    reports = inside(root, "reports")
    if destination == reports or not destination.is_relative_to(reports):
        raise ValueError("Output must be a subdirectory of reports")
    dictionary = inside(root, raw["paths"]["dictionary"])
    if dictionary.is_relative_to(destination) or config_path.is_relative_to(destination):
        raise ValueError("Output must not contain input configuration or dictionary")
    return Config(root, config_path, raw["project"]["id"], source, dictionary,
                  destination, minimum_age)
