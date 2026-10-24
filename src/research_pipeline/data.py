"""Dictionary-driven CSV validation. No network or clinical derivations."""

import csv
from dataclasses import dataclass
import math
from pathlib import Path


DEMO_TYPES = {
    "participant_id": "string", "cycle": "category", "age": "integer",
    "sex": "category", "exposure_demo": "integer", "outcome_demo": "integer",
    "survey_weight": "number", "stratum": "integer", "psu": "integer",
}
DICTIONARY_FIELDS = {
    "variable", "dtype", "required", "minimum", "maximum", "levels",
    "unit", "description", "source", "missing_rule", "derivation",
}


@dataclass(frozen=True)
class Field:
    name: str
    dtype: str
    required: bool
    minimum: float | None
    maximum: float | None
    levels: tuple[str, ...]


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, strict=True)
        header = next(reader, [])
        if not header or len(header) != len(set(header)) or any(not h for h in header):
            raise ValueError("CSV requires a nonempty header with unique names")
        rows = []
        for line, values in enumerate(reader, 2):
            if len(values) != len(header):
                raise ValueError(f"CSV row {line}: wrong number of columns")
            rows.append(dict(zip(header, (v.strip() for v in values))))
    return header, rows


def numeric_bound(value: str) -> float | None:
    if not value:
        return None
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Dictionary bounds must be finite")
    return result


def load_dictionary(path: Path) -> list[Field]:
    header, rows = read_csv(path)
    if set(header) != DICTIONARY_FIELDS or not rows:
        raise ValueError("Invalid dictionary columns or empty dictionary")
    fields = []
    for row in rows:
        name, dtype = row["variable"], row["dtype"]
        if dtype not in {"string", "category", "integer", "number"}:
            raise ValueError("Unknown dictionary dtype")
        if not name or row["required"] not in {"true", "false"}:
            raise ValueError("Invalid variable name or required flag")
        if any(not row[key] for key in ("unit", "description", "source", "missing_rule", "derivation")):
            raise ValueError(f"Incomplete dictionary documentation for {name}")
        minimum, maximum = numeric_bound(row["minimum"]), numeric_bound(row["maximum"])
        if minimum is not None and maximum is not None and minimum > maximum:
            raise ValueError("Dictionary minimum exceeds maximum")
        levels = tuple(row["levels"].split("|")) if row["levels"] else ()
        if dtype == "category" and (not levels or "" in levels or len(levels) != len(set(levels))):
            raise ValueError("Category fields require distinct nonempty levels")
        if dtype not in {"number", "integer"} and (minimum is not None or maximum is not None):
            raise ValueError("Numeric bounds apply only to numeric fields")
        fields.append(Field(name, dtype, row["required"] == "true", minimum, maximum, levels))
    if len({f.name for f in fields}) != len(fields):
        raise ValueError("Duplicate dictionary variable")
    if {f.name: f.dtype for f in fields} != DEMO_TYPES:
        raise ValueError("Dictionary must match the demo variable names and types")
    for field in fields:
        if field.name in {"participant_id", "cycle", "survey_weight", "stratum", "psu"} and not field.required:
            raise ValueError("Demo identifiers and design fields must be required")
    return fields


def parse_value(value: str, field: Field, row_number: int):
    label = f"Row {row_number}, field {field.name}"
    if value == "":
        if field.required:
            raise ValueError(f"{label}: required value missing")
        return None
    try:
        result = int(value) if field.dtype == "integer" else float(value) if field.dtype == "number" else value
    except ValueError as error:
        raise ValueError(f"{label}: invalid {field.dtype}") from error
    if isinstance(result, (int, float)):
        if not math.isfinite(result):
            raise ValueError(f"{label}: non-finite number")
        if field.minimum is not None and result < field.minimum:
            raise ValueError(f"{label}: below minimum")
        if field.maximum is not None and result > field.maximum:
            raise ValueError(f"{label}: above maximum")
    if field.levels and str(result) not in field.levels:
        raise ValueError(f"{label}: invalid category")
    return result


def load_participants(path: Path, dictionary: Path) -> list[dict]:
    fields = load_dictionary(dictionary)
    header, raw = read_csv(path)
    if set(header) != {f.name for f in fields}:
        raise ValueError("Participant columns do not match the dictionary")
    if not raw:
        raise ValueError("Participant file has no records")
    records, keys = [], set()
    for line, values in enumerate(raw, 2):
        row = {f.name: parse_value(values[f.name], f, line) for f in fields}
        if not row["participant_id"].startswith("DEMO_") or row["cycle"] != "SYNTHETIC":
            raise ValueError(f"Row {line}: demo identifier and cycle markers required")
        key = (row["cycle"], row["participant_id"])
        if key in keys:
            raise ValueError(f"Row {line}: duplicate participant key")
        if row["survey_weight"] <= 0 or row["stratum"] < 1 or row["psu"] < 1:
            raise ValueError(f"Row {line}: invalid demo design fields")
        if any(row[f] not in (None, 0, 1) for f in ("exposure_demo", "outcome_demo")):
            raise ValueError(f"Row {line}: demo flags must be binary or missing")
        keys.add(key)
        records.append(row)
    return records
