"""Regression tests without network calls or research data."""

import importlib
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import importers
import main as app
from data_management import springer_metadata
from screening import interactive_screening as screening
from screening import classifier as core


def assessment(**updates):
    fields = dict(
        serious_game="YES",
        gamification_only="NO",
        health="YES",
        ai="YES",
        iot="EXPLICIT_IOT",
        secondary_or_incomplete="NO",
    )
    fields.update(updates)

    for key in (
        "evidence_serious_game",
        "evidence_gamification",
        "evidence_health",
        "evidence_ai",
        "evidence_iot",
        "evidence_study_type",
    ):
        fields[key] = "Test evidence"

    return core.ScreeningAssessment(**fields)


class ImportTests(unittest.TestCase):
    def test_empty_import_preserves_both_workbooks(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            output = directory / "ieee_records.xlsx"
            duplicates = directory / "ieee_duplicates_internal.xlsx"

            pd.DataFrame(
                {"title": ["Existing record"]}
            ).to_excel(output, index=False)

            pd.DataFrame(
                {"title": ["Existing duplicate"]}
            ).to_excel(duplicates, index=False)

            originals = (
                output.read_bytes(),
                duplicates.read_bytes(),
            )

            with (
                patch.dict(importers.OUTPUT_FILES, ieee=output),
                patch.object(importers, "PROCESSED_DIR", directory),
            ):
                result = importers.finalize_import(
                    pd.DataFrame(), "ieee"
                )

            self.assertTrue(result.empty)
            self.assertIn("abstract", result.columns)
            self.assertEqual(
                originals,
                (output.read_bytes(), duplicates.read_bytes()),
            )

            unique, report = importers.deduplicate_records(result)

            self.assertEqual(
                list(unique.columns), list(result.columns)
            )
            self.assertIn("duplicate_reason", report.columns)

    def test_duplicate_recovers_metadata_and_registers_recovered_doi(self):
        records = pd.DataFrame([
            dict(
                source_id="first",
                title="Same title",
                doi="",
                abstract=None,
                authors="Original",
            ),
            dict(
                source_id="second",
                title="Same title",
                doi="10.1234/test",
                abstract="Available abstract",
                authors="Other",
            ),
            dict(
                source_id="third",
                title="Different title",
                doi="10.1234/test",
                abstract="Other abstract",
                authors="Third",
            ),
        ])

        unique, report = importers.deduplicate_records(records)

        self.assertEqual(len(unique), 1)
        self.assertEqual(len(report), 2)
        self.assertEqual(
            unique.iloc[0]["abstract"], "Available abstract"
        )
        self.assertEqual(unique.iloc[0]["source_id"], "first")
        self.assertEqual(unique.iloc[0]["authors"], "Original")

    def test_same_title_with_different_dois_stays_separate(self):
        records = pd.DataFrame([
            dict(
                source_id="first",
                title="Same title",
                doi="10.1234/first",
            ),
            dict(
                source_id="second",
                title="Same title",
                doi="10.1234/second",
            ),
        ])

        unique, report = importers.deduplicate_records(records)

        self.assertEqual(len(unique), 2)
        self.assertTrue(report.empty)
        self.assertEqual(
            set(unique["doi"]),
            {"10.1234/first", "10.1234/second"},
        )

    def test_all_importers_return_finalized_records(self):
        records = pd.DataFrame({"title": ["New record"]})

        for name in (
            "ieee", "pubmed", "acm", "scopus", "compendex", "springer"
        ):
            with self.subTest(database=name):
                module = importlib.import_module("importers." + name)

                filename = Path(
                    "export.nbib"
                    if name == "pubmed"
                    else "export.csv"
                    if name == "springer"
                    else "export.bib"
                )

                with (
                    patch.object(
                        module,
                        "discover_files",
                        side_effect=lambda database, extensions: (
                            [filename]
                            if filename.suffix in extensions
                            else []
                        ),
                    ),
                    patch.object(
                        module,
                        "finalize_import",
                        return_value=records,
                    ),
                ):
                    if name == "pubmed":
                        with (
                            patch.object(
                                module,
                                "parse_nbib_file",
                                return_value=[{}],
                            ),
                            patch.object(
                                module,
                                "nbib_records_to_dataframe",
                                return_value=records,
                            ),
                        ):
                            self.assertIs(module.main(), records)

                    elif name == "springer":
                        with (
                            patch.object(
                                module,
                                "read_tabular_file",
                                return_value=records,
                            ),
                            patch.object(
                                module,
                                "tabular_to_dataframe",
                                return_value=records,
                            ),
                        ):
                            self.assertIs(module.main(), records)

                    else:
                        with patch.object(
                            module,
                            "bibtex_files_to_dataframe",
                            return_value=records,
                        ):
                            self.assertIs(module.main(), records)

    def test_workflow_stops_after_failed_empty_or_cancelled_import(self):
        for result in (None, pd.DataFrame(), False):
            with self.subTest(result=type(result).__name__):
                with (
                    patch.object(
                        app,
                        "select_database",
                        return_value=app.DATABASES["6"],
                    ),
                    patch("builtins.input", return_value="y"),
                    patch.object(
                        app,
                        "run_module",
                        return_value=result,
                    ) as run,
                ):
                    app.run_complete_workflow()

                self.assertEqual(run.call_count, 1)

    def test_workflow_continues_after_valid_import(self):
        records = pd.DataFrame({"title": ["New record"]})

        with (
            patch.object(
                app,
                "select_database",
                return_value=app.DATABASES["6"],
            ),
            patch("builtins.input", return_value="y"),
            patch.object(
                app,
                "run_module",
                side_effect=[records, None, records, None],
            ) as run,
        ):
            app.run_complete_workflow()

        self.assertEqual(
            [call.args[0] for call in run.call_args_list],
            [
                "importers.springer",
                "data_management.springer_metadata",
                "data_management.update_master",
                "screening.interactive_screening",
            ],
        )


class SpringerMergeTests(unittest.TestCase):
    def test_same_title_with_different_dois_stays_separate(self):
        checkpoint = pd.DataFrame([
            dict(
                title="Same title",
                doi="10.1234/first",
                abstract="Saved abstract",
            ),
        ])

        imported = pd.DataFrame([
            dict(
                title="Same title",
                doi="10.1234/second",
                abstract="New abstract",
            ),
        ])

        merged = springer_metadata.merge_springer_records(
            checkpoint, imported
        )

        self.assertEqual(len(merged), 2)
        self.assertEqual(
            set(merged["doi"]),
            {"10.1234/first", "10.1234/second"},
        )
        self.assertEqual(
            merged.iloc[0]["abstract"], "Saved abstract"
        )

    def test_same_title_with_different_volumes_stays_separate(self):
        checkpoint = pd.DataFrame([
            dict(
                title="Proceedings",
                doi="",
                volume="1",
                abstract="Volume one",
            ),
        ])

        imported = pd.DataFrame([
            dict(
                title="Proceedings",
                doi="",
                volume="2",
                abstract="Volume two",
            ),
        ])

        merged = springer_metadata.merge_springer_records(
            checkpoint, imported
        )

        self.assertEqual(len(merged), 2)
        self.assertEqual(list(merged["volume"]), ["1", "2"])
        self.assertEqual(
            list(merged["abstract"]),
            ["Volume one", "Volume two"],
        )

    def test_missing_volume_does_not_choose_between_candidates(self):
        checkpoint = pd.DataFrame([
            dict(
                title="Proceedings",
                doi="",
                volume="1",
                abstract="Volume one",
            ),
            dict(
                title="Proceedings",
                doi="",
                volume="2",
                abstract="Volume two",
            ),
        ])

        imported = pd.DataFrame([
            dict(
                title="Proceedings",
                doi="",
                volume="",
                abstract="Unidentified volume",
            ),
        ])

        merged = springer_metadata.merge_springer_records(
            checkpoint, imported
        )

        self.assertEqual(len(merged), 3)
        self.assertEqual(
            list(merged["abstract"]),
            [
                "Volume one",
                "Volume two",
                "Unidentified volume",
            ],
        )

    def test_unique_compatible_volume_recovers_metadata_and_doi(self):
        checkpoint = pd.DataFrame([
            dict(
                title="Proceedings",
                doi="",
                volume="1",
                abstract="Volume one",
                springer_api_status="SUCCESS",
            ),
            dict(
                title="Proceedings",
                doi="",
                volume="2",
                abstract="",
                springer_api_status="NO_DOI",
            ),
        ])

        imported = pd.DataFrame([
            dict(
                title="Proceedings",
                doi="10.1234/volume2",
                volume="2.0",
                abstract="Recovered abstract",
            ),
            dict(
                title="Different title",
                doi="https://doi.org/10.1234/volume2",
                volume="2",
                abstract="Other abstract",
            ),
        ])

        merged = springer_metadata.merge_springer_records(
            checkpoint, imported
        )

        self.assertEqual(len(merged), 2)
        self.assertEqual(
            merged.iloc[0]["abstract"], "Volume one"
        )
        self.assertEqual(
            merged.iloc[0]["springer_api_status"], "SUCCESS"
        )
        self.assertEqual(
            merged.iloc[1]["doi"], "10.1234/volume2"
        )
        self.assertEqual(
            merged.iloc[1]["abstract"], "Recovered abstract"
        )
        self.assertNotEqual(
            merged.iloc[1]["springer_api_status"], "NO_DOI"
        )


class WorkflowMasterTests(unittest.TestCase):
    def test_invalid_master_return_stops_before_screening(self):
        records = pd.DataFrame({"title": ["New record"]})

        for database in app.DATABASES.values():
            for result in (None, pd.DataFrame(), False):
                with self.subTest(
                    database=database["slug"],
                    result=type(result).__name__,
                ):
                    expected = [database["import_module"]]
                    returns = [records]

                    if database["slug"] == "springer":
                        expected.append(
                            "data_management.springer_metadata"
                        )
                        returns.append(None)

                    expected.append("data_management.update_master")
                    returns.append(result)

                    with (
                        patch.object(
                            app,
                            "select_database",
                            return_value=database,
                        ),
                        patch("builtins.input", return_value="y"),
                        patch.object(
                            app,
                            "run_module",
                            side_effect=returns,
                        ) as run,
                    ):
                        app.run_complete_workflow()

                    self.assertEqual(
                        [call.args[0] for call in run.call_args_list],
                        expected,
                    )
                    self.assertEqual(
                        run.call_args.kwargs,
                        {"database": database["slug"]},
                    )

    def test_master_exception_or_interrupt_stops_before_screening(self):
        records = pd.DataFrame({"title": ["New record"]})

        for error in (
            OSError("Simulated master write failure"),
            KeyboardInterrupt(),
        ):
            with self.subTest(error=type(error).__name__):
                update = Mock(side_effect=error)
                screen = Mock()

                modules = {
                    "importers.ieee": SimpleNamespace(
                        main=Mock(return_value=records)
                    ),
                    "data_management.update_master": SimpleNamespace(
                        main=update
                    ),
                    "screening.interactive_screening": SimpleNamespace(
                        main=screen
                    ),
                }

                with (
                    patch.object(
                        app,
                        "select_database",
                        return_value=app.DATABASES["1"],
                    ),
                    patch("builtins.input", return_value="y"),
                    patch.object(
                        app,
                        "import_module",
                        side_effect=lambda name: modules[name],
                    ),
                ):
                    app.run_complete_workflow()

                update.assert_called_once_with(database="ieee")
                screen.assert_not_called()

    def test_valid_master_continues_for_all_databases(self):
        records = pd.DataFrame({"title": ["New record"]})

        for database in app.DATABASES.values():
            with self.subTest(database=database["slug"]):
                expected = [database["import_module"]]
                returns = [records]

                if database["slug"] == "springer":
                    expected.append(
                        "data_management.springer_metadata"
                    )
                    returns.append(None)

                expected.extend([
                    "data_management.update_master",
                    "screening.interactive_screening",
                ])
                returns.extend([records, None])

                with (
                    patch.object(
                        app,
                        "select_database",
                        return_value=database,
                    ),
                    patch("builtins.input", return_value="y"),
                    patch.object(
                        app,
                        "run_module",
                        side_effect=returns,
                    ) as run,
                ):
                    app.run_complete_workflow()

                self.assertEqual(
                    [call.args[0] for call in run.call_args_list],
                    expected,
                )
                self.assertEqual(
                    run.call_args_list[-2].kwargs,
                    {"database": database["slug"]},
                )


class CheckpointTests(unittest.TestCase):
    def test_write_failure_keeps_success_and_stops_before_next_article(self):
        records = pd.DataFrame([
            dict(
                master_id="MASTER-0001",
                database="IEEE Xplore",
                title="First",
                abstract="Abstract",
                keywords="",
            ),
            dict(
                master_id="MASTER-0002",
                database="IEEE Xplore",
                title="Second",
                abstract="Abstract",
                keywords="",
            ),
        ])

        captured = []

        def fail(results, *args):
            captured.extend(results)
            raise OSError("Simulated disk failure")

        with (
            patch.object(
                screening,
                "load_checkpoint",
                return_value=pd.DataFrame(),
            ),
            patch.object(
                core,
                "analyze_article",
                return_value=assessment(),
            ) as analyze,
            patch.object(
                screening,
                "save_checkpoint",
                side_effect=fail,
            ),
            patch.object(
                screening,
                "create_error_result",
            ) as api_error,
        ):
            with self.assertRaisesRegex(OSError, "disk failure"):
                screening.process_database(
                    records,
                    screening.DATABASES["1"],
                    object(),
                )

        self.assertEqual(analyze.call_count, 1)
        api_error.assert_not_called()
        self.assertEqual(captured[0]["decision"], "RETAIN")
        self.assertEqual(captured[0]["api_status"], "SUCCESS")

    def test_atomic_checkpoint_preserves_previous_file_on_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "checkpoint.xlsx"

            result = screening.create_success_result(
                pd.Series(dict(
                    master_id="MASTER-0001",
                    title="Title",
                    abstract="Abstract",
                )),
                assessment(),
                "RETAIN",
                "Reason",
                "",
            )

            screening.save_checkpoint(
                [result], output, "IEEE", 1
            )
            original = output.read_bytes()

            with patch.object(
                screening.os,
                "replace",
                side_effect=OSError("Simulated disk failure"),
            ):
                with self.assertRaises(OSError):
                    screening.save_checkpoint(
                        [result], output, "IEEE", 1
                    )

            self.assertEqual(output.read_bytes(), original)
            self.assertEqual(
                list(Path(directory).iterdir()), [output]
            )


class DecisionTests(unittest.TestCase):
    def test_current_rescues_and_priority(self):
        cases = [
            (
                assessment(iot="NO"),
                "sensor",
                "UNCERTAIN",
                "RESGATE_IOT_3_DE_4",
            ),
            (
                assessment(serious_game="NO", iot="NO"),
                "interactive sensor",
                "UNCERTAIN",
                "RESGATE_MULTIMODAL",
            ),
            (
                assessment(serious_game="NO", ai="UNCERTAIN"),
                "aal platform cognitive stimulation",
                "UNCERTAIN",
                "RESGATE_AAL_ESTIMULACAO",
            ),
            (
                assessment(
                    gamification_only="YES",
                    secondary_or_incomplete="YES",
                ),
                "",
                "UNCERTAIN",
                "",
            ),
            (
                assessment(
                    secondary_or_incomplete="YES",
                    iot="NO",
                ),
                "sensor",
                "EXCLUDE",
                "",
            ),
            (
                assessment(health="NO", ai="UNCERTAIN"),
                "",
                "EXCLUDE",
                "",
            ),
            (
                assessment(iot="NO"),
                "",
                "EXCLUDE",
                "",
            ),
        ]

        for labels, text, expected, rescue in cases:
            with self.subTest(expected=expected, rescue=rescue):
                decision, _, code = core.make_screening_decision(
                    labels, abstract=text
                )

                self.assertEqual(
                    (decision, code), (expected, rescue)
                )


if __name__ == "__main__":
    unittest.main()