"""Offline tests for Compendex parsing, index terms and volume identity."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
import bibtexparser

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import importers
from data_management import CANONICAL_COLUMNS, standardize_dataframe
from data_management import update_master


class CompendexTests(unittest.TestCase):
    def test_copyright_recovery_preserves_metadata_and_entry_order(self):
        text = '''@article{first,
 copyright={Publisher}, copyright={Compendex},
 title={First title}, abstract={Original abstract},
 keywords={sensor}, key={serious games}, note={Bluetooth; Exergaming},
 volume={2}, url={https://doi.org/10.1234/first}}
@article{second, title={Second title}, abstract={Second abstract}}
'''
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'export.bib'
            source.write_text(text)
            records = importers.bibtex_files_to_dataframe([source], 'compendex')
        self.assertEqual(records.title.tolist(), ['First title', 'Second title'])
        self.assertEqual(records.iloc[0]['abstract'], 'Original abstract')
        self.assertEqual(records.iloc[0]['doi'], '10.1234/first')
        self.assertEqual(records.iloc[0]['volume'], '2')
        for term in ('sensor', 'serious games', 'Bluetooth', 'Exergaming'):
            self.assertIn(term, records.iloc[0]['keywords'])

    @unittest.skipUnless(hasattr(bibtexparser, 'parse_file'), 'Checks BibTeX v2 rejection behavior')
    def test_other_repeated_fields_abort_instead_of_disappearing(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'export.bib'
            source.write_text('@article{bad, title={One}, title={Two}}')
            with self.assertRaisesRegex(ValueError, 'rejected block'):
                importers.load_bibtex_file(source, recover_compendex=True)

    def test_note_is_not_keywords_for_other_databases(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'export.bib'
            source.write_text('@article{one, title={Title}, keywords={sensor}, note={Administrative note}}')
            records = importers.bibtex_files_to_dataframe([source], 'ieee')
        self.assertEqual(records.iloc[0]['keywords'], 'sensor')

    def test_internal_dedup_keeps_volumes_and_merges_same_volume(self):
        records = pd.DataFrame([
            dict(source_id='v1', title='Conference proceedings', volume='1', doi='', abstract=''),
            dict(source_id='v2', title='Conference proceedings', volume='2', doi='', abstract=''),
            dict(source_id='again', title='Conference proceedings', volume='2.0', doi='', abstract='Recovered'),
        ])
        unique, duplicates = importers.deduplicate_records(records)
        self.assertEqual(len(unique), 2)
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(unique.iloc[1]['abstract'], 'Recovered')
        self.assertEqual(duplicates.iloc[0]['matched_source_id'], 'v2')

    def test_missing_volume_does_not_choose_between_multiple_candidates(self):
        records = pd.DataFrame([
            dict(title='Conference proceedings', volume='1', doi=''),
            dict(title='Conference proceedings', volume='2', doi=''),
            dict(title='Conference proceedings', volume='', doi=''),
        ])
        unique, _ = importers.deduplicate_records(records)
        self.assertEqual(len(unique), 3)

    def test_master_keeps_volumes_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'compendex_records.xlsx'
            incoming = pd.DataFrame([
                dict(title='Conference proceedings', volume='1', abstract='First'),
                dict(title='Conference proceedings', volume='2', abstract='Second'),
            ])
            incoming.to_excel(source, index=False)
            with patch.object(update_master, 'resolve_database_source_file', return_value=source):
                master, duplicates, added = update_master.update_database(pd.DataFrame(columns=CANONICAL_COLUMNS), 'compendex')
                updated, repeated, added_again = update_master.update_database(master, 'compendex')
        self.assertEqual((len(master), added, len(duplicates)), (2, 2, 0))
        self.assertEqual((len(updated), added_again, len(repeated)), (2, 0, 2))
        self.assertEqual(master.master_id.tolist(), updated.master_id.tolist())
        self.assertEqual(set(updated.volume), {'1', '2'})

    def test_legacy_tables_gain_volume_without_losing_ids(self):
        records = standardize_dataframe(pd.DataFrame([dict(master_id='MASTER-0009', title='Old record')]), 'compendex')
        self.assertEqual(records.iloc[0]['master_id'], 'MASTER-0009')
        self.assertEqual(records.iloc[0]['volume'], '')


if __name__ == '__main__':
    unittest.main()
