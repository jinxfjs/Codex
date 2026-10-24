"""Ordered exclusions: each record leaves at most once."""


def build_cohort(records: list[dict], minimum_age: int) -> tuple[list[dict], list[dict]]:
    retained = list(records)
    flow = [{"step": "input", "n_before": len(retained), "n_excluded": 0, "n_retained": len(retained)}]
    rules = [
        ("age_observed", lambda row: row["age"] is not None),
        ("demo_age_eligible", lambda row: row["age"] >= minimum_age),
        ("exposure_observed", lambda row: row["exposure_demo"] is not None),
        ("outcome_observed", lambda row: row["outcome_demo"] is not None),
    ]
    for step, eligible in rules:
        before = len(retained)
        retained = [row for row in retained if eligible(row)]
        flow.append({"step": step, "n_before": before,
                     "n_excluded": before - len(retained), "n_retained": len(retained)})
    return retained, flow
