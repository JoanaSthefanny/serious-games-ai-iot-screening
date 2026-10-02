"""Offline regression tests for import integrity and master creation."""

import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import bibtexparser
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import importers
from importers import ieee, pubmed
from importers.acm import ACM_COLUMN_MAP
from importers.compendex import COMPENDEX_COLUMN_MAP
from importers.scopus import SCOPUS_COLUMN_MAP
from importers.springer import SPRINGER_COLUMN_MAP
from data_management import CANONICAL_COLUMNS, standardize_dataframe
from data_management import create_master, update_master


class QuietTestCase(unittest.TestCase):
    def setUp(self):
        super().setUp()
        quiet = contextlib.redirect_stdout(io.StringIO())
        quiet.__enter__()
        self.addCleanup(quiet.__exit__, None, None, None)


class VolumeTests(QuietTestCase):
    def test_tabular_volume_survives_conversion_and_deduplication(self):
        maps = {
            "acm": ACM_COLUMN_MAP,
            "compendex": COMPENDEX_COLUMN_MAP,
            "scopus": SCOPUS_COLUMN_MAP,
            "springer": SPRINGER_COLUMN_MAP,
        }
        for database, mapping in maps.items():
            for header in ("Volume", "Volume Number", "Vol."):
                with self.subTest(database=database, header=header):
                    original_map = {key: list(value) for key, value in mapping.items()}
                    raw = pd.DataFrame([
                        {"Title": "Same title", header: "1"},
                        {"Title": "Same title", header: "2"},
                    ])
                    converted = importers.tabular_to_dataframe(raw, database, mapping)
                    records = standardize_dataframe(converted, database)
                    unique, duplicates = importers.deduplicate_records(records)
                    self.assertEqual(records.volume.tolist(), ["1", "2"])
                    self.assertEqual(len(unique), 2)
                    self.assertTrue(duplicates.empty)
                    self.assertEqual(mapping, original_map)

    def test_explicit_volume_mapping_has_priority_and_fills_gaps(self):
        raw = pd.DataFrame({
            "Title": ["First", "Second"],
            "Custom Volume": ["7", ""],
            "Volume": ["99", "8"],
        })
        mapping = {"title": ["Title"], "volume": ["Custom Volume"]}
        result = importers.tabular_to_dataframe(raw, "scopus", mapping)
        self.assertEqual(result.volume.tolist(), ["7", "8"])
        self.assertEqual(mapping["volume"], ["Custom Volume"])

    def test_missing_tabular_volume_remains_empty(self):
        raw = pd.DataFrame({"Title": ["Study"]})
        result = importers.tabular_to_dataframe(raw, "scopus", SCOPUS_COLUMN_MAP)
        self.assertEqual(result.volume.tolist(), [""])

    def test_nbib_volume_survives_parsing_and_deduplication(self):
        text = (
            "PMID- 12345\nTI  - Same title\nVI  - 1\n"
            "DP  - 2024 Jan\nAB  - First abstract\n"
            "      continued here.\nLID - 10.1234/first [doi]\n\n"
            "PMID- 12346\nTI  - Same title\nVI  - 2\n"
            "AB  - Second abstract\n\n"
            "PMID- 12347\nTI  - No volume\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "export.nbib"
            source.write_text(text, encoding="utf-8")
            result = pubmed.nbib_records_to_dataframe(pubmed.parse_nbib_file(source))
        self.assertEqual(result.volume.tolist(), ["1", "2", ""])
        self.assertEqual(result.iloc[0]["abstract"], "First abstract continued here.")
        self.assertEqual(result.iloc[0]["doi"], "10.1234/first")
        self.assertEqual(result.iloc[0]["url"], "https://pubmed.ncbi.nlm.nih.gov/12345/")
        records = standardize_dataframe(result, "pubmed")
        unique, duplicates = importers.deduplicate_records(records)
        self.assertEqual(len(unique), 3)
        self.assertTrue(duplicates.empty)


@unittest.skipUnless(hasattr(bibtexparser, "parse_file"), "Requires bibtexparser v2")
class BibTeXIntegrityTests(QuietTestCase):
    def test_rejected_entries_abort_every_bibtex_database(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "export.bib"
            source.write_text(
                "@article{good,title={Good study}}\n"
                "@article{bad,title={One},title={Two}}",
                encoding="utf-8",
            )
            for database in ("ieee", "acm", "scopus", "pubmed", "compendex"):
                with self.subTest(database=database):
                    with self.assertRaisesRegex(ValueError, "rejected block"):
                        importers.bibtex_files_to_dataframe([source], database)

    def test_copyright_recovery_is_compendex_only(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "export.bib"
            source.write_text(
                "@article{one,title={Study},volume={2},"
                "copyright={Publisher},copyright={Compendex}}",
                encoding="utf-8",
            )
            result = importers.bibtex_files_to_dataframe([source], "compendex")
            self.assertEqual(result.title.tolist(), ["Study"])
            self.assertEqual(result.volume.tolist(), ["2"])
            for database in ("ieee", "acm", "scopus", "pubmed"):
                with self.subTest(database=database):
                    with self.assertRaisesRegex(ValueError, "rejected block"):
                        importers.bibtex_files_to_dataframe([source], database)

    def test_partial_import_does_not_overwrite_existing_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "export.bib"
            source.write_text(
                "@article{good,title={Good}}\n"
                "@article{bad,title={One},title={Two}}",
                encoding="utf-8",
            )
            output = root / "ieee_records.xlsx"
            report = root / "ieee_duplicates_internal.xlsx"
            pd.DataFrame({"title": ["Existing study"]}).to_excel(output, index=False)
            pd.DataFrame({"title": ["Existing duplicate"]}).to_excel(report, index=False)
            originals = (output.read_bytes(), report.read_bytes())
            with (
                patch.object(ieee, "discover_files", return_value=[source]),
                patch.dict(importers.OUTPUT_FILES, ieee=output),
                patch.object(importers, "PROCESSED_DIR", root),
            ):
                with self.assertRaisesRegex(ValueError, "rejected block"):
                    ieee.main()
            self.assertEqual(originals, (output.read_bytes(), report.read_bytes()))


class MasterCreationTests(QuietTestCase):
    def setUp(self):
        super().setUp()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.master_file = self.root / "master_records.xlsx"
        self.report_file = self.root / "master_duplicates_not_added.xlsx"
        pd.DataFrame({"title": ["Old master"]}).to_excel(self.master_file, index=False)
        pd.DataFrame({"title": ["Old report"]}).to_excel(self.report_file, index=False)
        self.original_master = self.master_file.read_bytes()
        self.original_report = self.report_file.read_bytes()
        self.new_master = standardize_dataframe(pd.DataFrame([{
            "master_id": "MASTER-0001", "title": "New study",
        }]), "ieee")
        self.empty_report = pd.DataFrame(columns=create_master.DUPLICATE_COLUMNS)
        for name, value in (
            ("MASTER_FILE", self.master_file),
            ("DUPLICATES_FILE", self.report_file),
        ):
            patcher = patch.object(create_master, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def assert_originals_preserved(self):
        self.assertEqual(self.master_file.read_bytes(), self.original_master)
        self.assertEqual(self.report_file.read_bytes(), self.original_report)

    def assert_no_temporary_workbooks(self):
        self.assertEqual(list(self.root.glob(".*.xlsx")), [])

    def run_with_records(self):
        return patch.object(create_master, "create_master", return_value=(
            self.new_master, self.empty_report,
        ))

    def test_no_input_preserves_existing_outputs(self):
        with patch.object(update_master, "resolve_database_source_file", return_value=None):
            self.assertIsNone(create_master.main())
        self.assert_originals_preserved()
        self.assertEqual(len(list(self.root.iterdir())), 2)

    def test_empty_processed_input_preserves_existing_outputs(self):
        source = self.root / "ieee_records.xlsx"
        pd.DataFrame(columns=CANONICAL_COLUMNS).to_excel(source, index=False)
        with patch.object(update_master, "resolve_database_source_file", return_value=source):
            self.assertIsNone(create_master.main())
        self.assert_originals_preserved()
        self.assert_no_temporary_workbooks()

    def test_success_saves_headers_and_backs_up_both_outputs(self):
        with self.run_with_records():
            result = create_master.main()
        self.assertEqual(len(result), 1)
        self.assertEqual(pd.read_excel(self.master_file).title.tolist(), ["New study"])
        report = pd.read_excel(self.report_file)
        self.assertTrue(report.empty)
        self.assertEqual(list(report.columns), create_master.DUPLICATE_COLUMNS)
        backups = list(self.root.glob("*_backup_before_create_*.xlsx"))
        self.assertEqual(len(backups), 2)
        self.assertEqual({p.read_bytes() for p in backups}, {
            self.original_master, self.original_report,
        })
        self.assert_no_temporary_workbooks()

    def test_report_write_failure_preserves_both_outputs(self):
        original_write = pd.DataFrame.to_excel
        calls = 0

        def fail_second_write(dataframe, *args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("Simulated report write failure")
            return original_write(dataframe, *args, **kwargs)

        with self.run_with_records(), patch.object(pd.DataFrame, "to_excel", new=fail_second_write):
            with self.assertRaisesRegex(OSError, "report write failure"):
                create_master.main()
        self.assertEqual(calls, 2)
        self.assert_originals_preserved()
        self.assert_no_temporary_workbooks()

    def test_backup_failure_preserves_both_outputs(self):
        original_backup = create_master.create_file_backup

        def fail_report_backup(path):
            if path == self.report_file:
                raise OSError("Simulated backup failure")
            return original_backup(path)

        with self.run_with_records(), patch.object(create_master, "create_file_backup", side_effect=fail_report_backup):
            with self.assertRaisesRegex(OSError, "backup failure"):
                create_master.main()
        self.assert_originals_preserved()
        self.assert_no_temporary_workbooks()

    def test_first_replace_failure_preserves_both_outputs(self):
        with self.run_with_records(), patch.object(create_master.os, "replace", side_effect=OSError("Simulated replace failure")):
            with self.assertRaisesRegex(OSError, "replace failure"):
                create_master.main()
        self.assert_originals_preserved()
        self.assert_no_temporary_workbooks()

    def test_second_replace_failure_retains_recovery_backups(self):
        original_replace = create_master.os.replace

        def fail_report_replace(source, destination):
            if destination == self.report_file:
                raise OSError("Simulated report replace failure")
            return original_replace(source, destination)

        with self.run_with_records(), patch.object(create_master.os, "replace", side_effect=fail_report_replace):
            with self.assertRaisesRegex(OSError, "report replace failure"):
                create_master.main()
        self.assertEqual(pd.read_excel(self.master_file).title.tolist(), ["New study"])
        self.assertEqual(self.report_file.read_bytes(), self.original_report)
        backups = list(self.root.glob("*_backup_before_create_*.xlsx"))
        self.assertEqual(len(backups), 2)
        self.assertEqual({p.read_bytes() for p in backups}, {
            self.original_master, self.original_report,
        })
        self.assert_no_temporary_workbooks()


if __name__ == "__main__":
    unittest.main()
