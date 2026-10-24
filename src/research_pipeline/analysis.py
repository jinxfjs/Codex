"""Unweighted synthetic summaries only; no population inference."""

from statistics import mean


def summarize(records: list[dict]) -> list[dict]:
    if not records:
        raise ValueError("No participants remain after demo eligibility rules")
    results = []

    def add(variable, statistic, value, observed, missing):
        results.append({"variable": variable, "statistic": statistic, "value": value,
                        "n_observed": observed, "n_missing": missing,
                        "estimation": "unweighted_synthetic_only"})

    add("cohort", "n", len(records), len(records), 0)
    ages = [r["age"] for r in records if r["age"] is not None]
    add("age", "mean", f"{mean(ages):.6f}" if ages else "", len(ages), len(records) - len(ages))
    for variable in ("exposure_demo", "outcome_demo"):
        values = [r[variable] for r in records if r[variable] is not None]
        add(variable, "proportion_1", f"{mean(values):.6f}" if values else "",
            len(values), len(records) - len(values))
    for level in ("F", "M"):
        observed = [r["sex"] for r in records if r["sex"] is not None]
        add("sex", f"n_{level}", observed.count(level), len(observed), len(records) - len(observed))
    return results
