"""Offline regressions for repeated ambiguous imports and source identity."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

from test_compendex_regressions import update_master, CANONICAL_COLUMNS
from data_management import DATABASE_NAMES, DATABASE_ORDER, standardize_dataframe


class MasterSourceIdentityTests(unittest.TestCase):
    def run_import(self, master, rows, database='compendex'):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'records.xlsx'
            pd.DataFrame(rows).to_excel(source, index=False)
            with patch.object(update_master, 'resolve_database_source_file', return_value=source), contextlib.redirect_stdout(io.StringIO()):
                return update_master.update_database(master, database)

    def ambiguous_rows(self):
        return [
            dict(source_id='v1', title='Proceedings', volume='1', doi=''),
            dict(source_id='v2', title='Proceedings', volume='2', doi=''),
            dict(source_id='unknown', title='Proceedings', volume='', doi=''),
        ]

    def test_repeated_ambiguous_import_is_idempotent_for_all_databases(self):
        for database in DATABASE_ORDER:
            with self.subTest(database=database):
                rows = self.ambiguous_rows()
                first, _, added = self.run_import(pd.DataFrame(columns=CANONICAL_COLUMNS), rows, database)
                second, duplicates, added_again = self.run_import(first, rows, database)
                third, _, added_third = self.run_import(second, rows, database)
                self.assertEqual((len(first), added), (3, 3))
                self.assertEqual((len(second), len(duplicates), added_again), (3, 3, 0))
                self.assertEqual((len(third), added_third), (3, 0))
                self.assertEqual(first.master_id.tolist(), second.master_id.tolist())
                self.assertEqual(first.master_id.tolist(), third.master_id.tolist())
                self.assertEqual({r['duplicate_reason'] for r in duplicates}, {'SOURCE_ID'})
                self.assertEqual({r['matched_master_id'] for r in duplicates}, set(first.master_id))
                self.assertEqual(list(third.columns), CANONICAL_COLUMNS)

    def test_repeat_after_master_excel_round_trip_preserves_ids(self):
        rows = self.ambiguous_rows()
        first, _, _ = self.run_import(pd.DataFrame(columns=CANONICAL_COLUMNS), rows)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'master.xlsx'
            first.to_excel(path, index=False)
            loaded = pd.read_excel(path)
        second, duplicates, added = self.run_import(loaded, rows)
        self.assertEqual((len(second), len(duplicates), added), (3, 3, 0))
        self.assertEqual(first.master_id.tolist(), second.master_id.tolist())

    def test_database_slug_and_name_share_the_same_origin(self):
        rows = self.ambiguous_rows()
        first, _, _ = self.run_import(pd.DataFrame(columns=CANONICAL_COLUMNS), rows)
        first['database'] = 'compendex'
        second, duplicates, added = self.run_import(first, rows)
        self.assertEqual((len(second), added), (3, 0))
        self.assertTrue(all(r['duplicate_reason'] == 'SOURCE_ID' for r in duplicates))

    def test_source_id_from_another_database_does_not_break_title_ambiguity(self):
        first, _, _ = self.run_import(pd.DataFrame(columns=CANONICAL_COLUMNS), self.ambiguous_rows(), 'ieee')
        second, duplicates, added = self.run_import(first, [self.ambiguous_rows()[0]], 'compendex')
        self.assertEqual((len(second), len(duplicates), added), (4, 0, 1))

    def test_regenerated_source_id_with_conflicting_title_is_not_merged(self):
        master, _, _ = self.run_import(pd.DataFrame(columns=CANONICAL_COLUMNS), [dict(source_id='COMPENDEX-0001',title='First study')])
        updated, duplicates, added = self.run_import(master, [dict(source_id='COMPENDEX-0001',title='Different study')])
        self.assertEqual((len(updated), len(duplicates), added), (2, 0, 1))

    def test_regenerated_source_id_with_conflicting_doi_is_not_merged(self):
        master, _, _ = self.run_import(pd.DataFrame(columns=CANONICAL_COLUMNS), [dict(source_id='same',title='Study',doi='10.1234/first')])
        updated, duplicates, added = self.run_import(master, [dict(source_id='same',title='Study',doi='10.1234/second')])
        self.assertEqual((len(updated), len(duplicates), added), (2, 0, 1))

    def test_regenerated_source_id_with_conflicting_volume_is_not_merged(self):
        master, _, _ = self.run_import(pd.DataFrame(columns=CANONICAL_COLUMNS), [dict(source_id='same',title='Study',volume='1')])
        updated, duplicates, added = self.run_import(master, [dict(source_id='same',title='Study',volume='2')])
        self.assertEqual((len(updated), len(duplicates), added), (2, 0, 1))

    def test_ambiguous_source_candidates_are_not_arbitrarily_merged(self):
        records = standardize_dataframe(pd.DataFrame([
            dict(source_id='same',title='Study',volume='1'),
            dict(source_id='same',title='Study',volume='2'),
        ]),'compendex').to_dict('records')
        incoming = dict(source_id='same',database=DATABASE_NAMES['compendex'],title='Study',volume='')
        self.assertIsNone(update_master.find_unique_source_match(records,[0,1],incoming))

    def test_available_bibliographic_conflicts_block_source_matching(self):
        for field in ('year','publication','authors'):
            with self.subTest(field=field):
                existing = dict(source_id='same',database='compendex',title='Study')
                incoming = dict(existing)
                existing[field]='2024' if field=='year' else 'First value'
                incoming[field]='2025' if field=='year' else 'Different value'
                self.assertIsNone(update_master.find_unique_source_match([existing],[0],incoming))

    def test_year_numeric_excel_representation_is_compatible(self):
        existing = dict(source_id='same',database='compendex',title='Study',year=2024.0)
        incoming = dict(existing,year='2024')
        self.assertEqual(update_master.find_unique_source_match([existing],[0],incoming),0)

    def test_origin_match_recovers_metadata_and_indexes_doi(self):
        rows = self.ambiguous_rows()
        first, _, _ = self.run_import(pd.DataFrame(columns=CANONICAL_COLUMNS), rows)
        incoming = dict(rows[0], doi='10.1234/recovered',abstract='Recovered abstract')
        updated, duplicates, added = self.run_import(first,[incoming,dict(source_id='another',title='Alternate title',doi='10.1234/recovered')])
        self.assertEqual((len(updated),len(duplicates),added),(3,2,0))
        self.assertEqual([r['duplicate_reason'] for r in duplicates],['SOURCE_ID','DOI'])
        self.assertEqual(updated.iloc[0]['doi'],'10.1234/recovered')
        self.assertEqual(updated.iloc[0]['abstract'],'Recovered abstract')
        self.assertEqual(updated.iloc[0]['source_id'],'v1')
        self.assertEqual(updated.iloc[0]['master_id'],first.iloc[0]['master_id'])

    def test_doi_match_retains_priority_over_source_identity(self):
        rows = [dict(source_id='first',title='First',doi='10.1234/a'),dict(source_id='second',title='Second',doi='10.1234/b')]
        first, _, _ = self.run_import(pd.DataFrame(columns=CANONICAL_COLUMNS),rows)
        updated, duplicates, added = self.run_import(first,[dict(source_id='first',title='First',doi='10.1234/b')])
        self.assertEqual((len(updated),added),(2,0))
        self.assertEqual(duplicates[0]['duplicate_reason'],'DOI')
        self.assertEqual(duplicates[0]['matched_master_id'],first.iloc[1]['master_id'])

    def test_missing_source_id_does_not_break_title_ambiguity(self):
        first, _, _ = self.run_import(pd.DataFrame(columns=CANONICAL_COLUMNS),self.ambiguous_rows())
        updated, duplicates, added = self.run_import(first,[dict(title='Proceedings',volume='1')])
        self.assertEqual((len(updated),len(duplicates),added),(4,0,1))

if __name__ == '__main__':
    unittest.main()
