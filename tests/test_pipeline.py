"""Behavior checks using only fabricated records and temporary directories."""

import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from research_pipeline.analysis import summarize
from research_pipeline.cohort import build_cohort
from research_pipeline.config import load_config
from research_pipeline.data import load_dictionary, load_participants, read_csv
from research_pipeline.pipeline import ARTIFACTS, run, sha256


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        reports = ROOT / "reports"
        reports.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="test_", dir=reports)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for folder in ("config", "metadata", "src", "scripts", "data/synthetic"):
            shutil.copytree(ROOT / folder, self.root / folder, ignore=shutil.ignore_patterns("__pycache__"))
        self.source = self.root / "data/synthetic/participants.csv"
        self.dictionary = self.root / "metadata/data_dictionary.csv"
        self.config = self.root / "config/demo.toml"

    def read_records(self):
        return load_participants(self.source, self.dictionary)

    def rewrite_csv(self, path, modify):
        header, rows = read_csv(path)
        modify(header, rows)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)

    def change_config(self, old, new):
        self.config.write_text(self.config.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")

    def test_demo_counts_and_exclusion_conservation(self):
        records = self.read_records()
        cohort, flow = build_cohort(records, 20)
        self.assertEqual([r["n_retained"] for r in flow], [12, 11, 10, 9, 8])
        self.assertEqual(sum(r["n_excluded"] for r in flow) + len(cohort), len(records))
        self.assertTrue(any(r["age"] == 20 for r in cohort))
        self.assertEqual(len(records), 12)  # Input collection is not mutated.

    def test_summary_known_values_and_missing_denominators(self):
        cohort, _ = build_cohort(self.read_records(), 20)
        result = {(r["variable"], r["statistic"]): r for r in summarize(cohort)}
        self.assertEqual(result[("age", "mean")]["value"], "47.375000")
        self.assertEqual(result[("exposure_demo", "proportion_1")]["value"], "0.625000")
        self.assertEqual(result[("outcome_demo", "proportion_1")]["value"], "0.500000")
        self.assertEqual(result[("sex", "n_F")]["value"], 3)
        self.assertEqual(result[("sex", "n_M")]["value"], 4)
        self.assertEqual(result[("sex", "n_F")]["n_observed"], 7)
        self.assertEqual(result[("sex", "n_F")]["n_missing"], 1)
        self.assertTrue(all(r["estimation"] == "unweighted_synthetic_only" for r in result.values()))

    def test_duplicate_key_rejected(self):
        self.rewrite_csv(self.source, lambda header, rows: rows.append(rows[0].copy()))
        with self.assertRaisesRegex(ValueError, "duplicate participant"):
            self.read_records()

    def test_missing_and_unexpected_columns_rejected(self):
        original = self.source.read_text(encoding="utf-8")
        for replacement in ("unknown", ""):
            with self.subTest(replacement=replacement):
                self.source.write_text(original.replace("participant_id,", replacement + ",", 1), encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.read_records()

    def test_duplicate_header_and_ragged_rows_rejected(self):
        original = self.source.read_text(encoding="utf-8")
        for content in (original.replace("participant_id,cycle", "cycle,cycle", 1), original + "DEMO_EXTRA,SYNTHETIC\n"):
            with self.subTest(content=content[:30]):
                self.source.write_text(content, encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.read_records()

    def test_invalid_values_fail_without_echoing_record(self):
        original = self.source.read_bytes()
        for field, value in (("survey_weight", "NaN"), ("survey_weight", "inf"), ("survey_weight", "-1"),
                             ("age", "35.2"), ("age", "121"), ("sex", "X"),
                             ("exposure_demo", "2"), ("participant_id", ""), ("psu", "0")):
            with self.subTest(field=field, value=value):
                self.source.write_bytes(original)
                self.rewrite_csv(self.source, lambda header, rows: rows[0].update({field: value}))
                with self.assertRaises(ValueError) as error:
                    self.read_records()
                self.assertNotIn("DEMO_001", str(error.exception))

    def test_synthetic_markers_required(self):
        self.rewrite_csv(self.source, lambda header, rows: rows[0].update(participant_id="12345"))
        with self.assertRaisesRegex(ValueError, "demo identifier"):
            self.read_records()

    def test_optional_missing_values_remain_missing(self):
        records = self.read_records()
        self.assertIsNone(records[6]["age"])
        self.assertIsNone(records[11]["sex"])

    def test_empty_input_rejected(self):
        self.source.write_text(self.source.read_text(encoding="utf-8").splitlines()[0] + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "no records"):
            self.read_records()

    def test_dictionary_contract_rejected_when_inconsistent(self):
        original = self.dictionary.read_bytes()
        cases = [
            lambda header, rows: rows.append(rows[0].copy()),
            lambda header, rows: rows[0].update(required="yes"),
            lambda header, rows: rows[2].update(dtype="string"),
            lambda header, rows: rows[2].update(minimum="130", maximum="120"),
            lambda header, rows: rows[2].update(description=""),
            lambda header, rows: rows[0].update(required="false"),
        ]
        for index, mutate in enumerate(cases):
            with self.subTest(case=index):
                self.dictionary.write_bytes(original)
                self.rewrite_csv(self.dictionary, mutate)
                with self.assertRaises(ValueError):
                    load_dictionary(self.dictionary)

    def test_real_mode_fails_before_output(self):
        with self.assertRaisesRegex(ValueError, "Only synthetic"):
            run(self.root, "config/study.example.toml")
        self.assertFalse((self.root / "reports").exists())

    def test_bad_config_fails_before_output(self):
        original = self.config.read_bytes()
        cases = [('minimum_age = 20', 'minimum_age = true'),
                 ('minimum_age = 20', 'minimun_age = 20'),
                 ('data/synthetic/participants.csv', '../outside.csv'),
                 ('data/synthetic/participants.csv', 'data/raw/participants.csv')]
        for old, new in cases:
            with self.subTest(new=new):
                self.config.write_bytes(original)
                self.change_config(old, new)
                with self.assertRaises(ValueError):
                    run(self.root)
                self.assertFalse((self.root / "reports").exists())

    def test_unsafe_output_paths_rejected(self):
        for output in ("reports", "data/synthetic", "../outside", ".", "src"):
            with self.subTest(output=output):
                with self.assertRaises(ValueError):
                    run(self.root, output=output)

    def test_empty_cohort_fails_without_outputs(self):
        self.change_config('minimum_age = 20', 'minimum_age = 120')
        with self.assertRaisesRegex(ValueError, "No participants remain"):
            run(self.root)
        self.assertFalse((self.root / "reports").exists())

    def test_manifest_checksums_and_aggregate_only_outputs(self):
        manifest = run(self.root)
        output = self.root / "reports/demo"
        self.assertEqual(manifest["counts"], {"input": 12, "retained": 8})
        for name, digest in manifest["outputs_sha256"].items():
            self.assertEqual(sha256(output / name), digest)
        for group in ("inputs_sha256", "code_sha256"):
            for name, digest in manifest[group].items():
                self.assertEqual(sha256(self.root / name), digest)
        for path in output.iterdir():
            self.assertNotIn("DEMO_001", path.read_text(encoding="utf-8"))
        self.assertEqual(json.loads((output / "run_manifest.json").read_text(encoding="utf-8")), manifest)

    def test_repeat_runs_are_byte_identical_and_refresh_outputs(self):
        run(self.root, output="reports/first")
        run(self.root, output="reports/second")
        for name in (*ARTIFACTS, "run_manifest.json"):
            self.assertEqual((self.root / "reports/first" / name).read_bytes(),
                             (self.root / "reports/second" / name).read_bytes())
        report = self.root / "reports/first/report.md"
        report.write_text("obsolete", encoding="utf-8")
        run(self.root, output="reports/first")
        self.assertIn("SYNTHETIC ONLY", report.read_text(encoding="utf-8"))

    def test_cli_nonzero_exit_for_invalid_configuration(self):
        result = subprocess.run([sys.executable, str(self.root / "scripts/run_pipeline.py"),
                                 "--config", "config/study.example.toml"],
                                capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn("Only synthetic", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
