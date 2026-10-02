"""Offline Springer checkpoint identity and preservation regressions."""
import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from test_compendex_regressions import CANONICAL_COLUMNS
from data_management import standardize_dataframe
from data_management import springer_metadata as springer


class SpringerSourceIdentityTests(unittest.TestCase):
    def rows(self):
        return standardize_dataframe(pd.DataFrame([
            dict(source_id='v1',title='Proceedings',volume='1',doi=''),
            dict(source_id='v2',title='Proceedings',volume='2',doi=''),
            dict(source_id='unknown',title='Proceedings',volume='',doi=''),
        ]),'springer')

    def test_repeated_ambiguous_batch_remains_three_records(self):
        incoming = self.rows()
        first = springer.merge_springer_records(pd.DataFrame(columns=CANONICAL_COLUMNS),incoming)
        second = springer.merge_springer_records(first,incoming)
        third = springer.merge_springer_records(second,incoming)
        self.assertEqual((len(first),len(second),len(third)),(3,3,3))
        self.assertEqual(first.source_id.tolist(),third.source_id.tolist())
        self.assertEqual(first.volume.tolist(),third.volume.tolist())

    def test_excel_round_trip_preserves_abstracts_and_api_status_columns(self):
        checkpoint = self.rows()
        checkpoint['abstract']=['Original abstract','', 'Third abstract']
        checkpoint['springer_api_status']=['FOUND','NOT_FOUND','ALREADY_HAS_ABSTRACT']
        checkpoint['springer_api_error']=['','Original error','']
        checkpoint['springer_api_title']=['API first','API second','API third']
        checkpoint['custom_checkpoint_field']=['one','two','three']
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'checkpoint.xlsx'
            checkpoint.to_excel(path,index=False)
            loaded=pd.read_excel(path)
        incoming=self.rows()
        incoming['abstract']='Replacement abstract'
        incoming['springer_api_status']='ERROR'
        incoming['springer_api_error']='Replacement error'
        merged=springer.merge_springer_records(loaded,incoming)
        self.assertEqual(len(merged),3)
        self.assertEqual(merged.abstract.tolist(),['Original abstract','Replacement abstract','Third abstract'])
        self.assertEqual(merged.springer_api_status.tolist(),checkpoint.springer_api_status.tolist())
        self.assertEqual(merged.iloc[1]['springer_api_error'],'Original error')
        self.assertEqual(merged.springer_api_title.tolist(),checkpoint.springer_api_title.tolist())
        self.assertEqual(merged.custom_checkpoint_field.tolist(),['one','two','three'])

    def test_recovered_doi_clears_no_doi_and_is_indexed(self):
        checkpoint=self.rows()
        checkpoint['springer_api_status']='NO_DOI'
        checkpoint['springer_api_error']='Missing DOI'
        incoming=checkpoint.iloc[[0]].copy()
        incoming['doi']='10.1234/recovered'
        incoming['springer_api_status']='ERROR'
        second=incoming.copy()
        second['title']='Different title'
        second['source_id']='another'
        merged=springer.merge_springer_records(checkpoint,pd.concat([incoming,second],ignore_index=True))
        self.assertEqual(len(merged),3)
        self.assertEqual(merged.iloc[0]['doi'],'10.1234/recovered')
        self.assertEqual(merged.iloc[0]['springer_api_status'],'')
        self.assertEqual(merged.iloc[0]['springer_api_error'],'')
        self.assertEqual(merged.iloc[1]['springer_api_status'],'NO_DOI')

    def test_same_source_with_conflicting_doi_remains_separate(self):
        checkpoint=self.rows().iloc[[0]].copy()
        checkpoint['doi']='10.1234/first'
        incoming=checkpoint.copy()
        incoming['doi']='10.1234/second'
        self.assertEqual(len(springer.merge_springer_records(checkpoint,incoming)),2)

    def test_same_source_with_conflicting_volume_remains_separate(self):
        checkpoint=self.rows().iloc[[0]].copy()
        incoming=checkpoint.copy()
        incoming['volume']='2'
        self.assertEqual(len(springer.merge_springer_records(checkpoint,incoming)),2)

    def test_regenerated_id_with_different_title_remains_separate(self):
        checkpoint=self.rows().iloc[[0]].copy()
        incoming=checkpoint.copy()
        incoming['title']='New study'
        self.assertEqual(len(springer.merge_springer_records(checkpoint,incoming)),2)

    def test_source_id_from_another_database_does_not_resolve_ambiguity(self):
        checkpoint=self.rows()
        incoming=checkpoint.iloc[[0]].copy()
        incoming['database']='Scopus'
        self.assertEqual(len(springer.merge_springer_records(checkpoint,incoming)),4)

    def test_multiple_origin_candidates_remain_ambiguous(self):
        checkpoint=self.rows().iloc[:2].copy()
        checkpoint['source_id']='same'
        incoming=checkpoint.iloc[[0]].copy()
        incoming['volume']=''
        self.assertEqual(len(springer.merge_springer_records(checkpoint,incoming)),3)

    def test_missing_source_id_does_not_resolve_title_ambiguity(self):
        checkpoint=self.rows()
        incoming=checkpoint.iloc[[0]].copy()
        incoming['source_id']=''
        self.assertEqual(len(springer.merge_springer_records(checkpoint,incoming)),4)

    def test_database_slug_recognizes_same_origin(self):
        checkpoint=self.rows()
        checkpoint['database']='springer'
        self.assertEqual(len(springer.merge_springer_records(checkpoint,self.rows())),3)

    def test_doi_match_precedes_origin_match(self):
        checkpoint=self.rows().iloc[:2].copy()
        checkpoint['doi']=['10.1234/a','10.1234/b']
        incoming=checkpoint.iloc[[0]].copy()
        incoming['doi']='10.1234/b'
        incoming['abstract']='Recovered'
        merged=springer.merge_springer_records(checkpoint,incoming)
        self.assertEqual(len(merged),2)
        self.assertEqual(merged.iloc[1]['abstract'],'Recovered')
        self.assertEqual(merged.iloc[0]['abstract'],'')

    def test_main_repeated_runs_save_same_three_records_without_api_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            directory=Path(directory)
            imported=directory/'springer_records.xlsx'
            enriched=directory/'springer_records_enriched.xlsx'
            self.rows().to_excel(imported,index=False)
            with patch.object(springer,'OUTPUT_FILE',enriched), patch.object(springer,'resolve_springer_import_file',return_value=imported), patch.object(springer,'load_dotenv'), patch.dict(os.environ,{'SPRINGER_API_KEY':'offline-test'}), patch.object(springer,'request_springer_metadata') as request, contextlib.redirect_stdout(io.StringIO()):
                first=springer.main()
                second=springer.main()
                saved=pd.read_excel(enriched)
            request.assert_not_called()
            self.assertEqual((len(first),len(second),len(saved)),(3,3,3))
            self.assertEqual(saved.springer_api_status.tolist(),['NO_DOI']*3)
            self.assertEqual(saved.source_id.tolist(),self.rows().source_id.tolist())

    def test_existing_abstracts_skip_api_after_repeated_merge(self):
        checkpoint=self.rows()
        checkpoint['abstract']='Existing abstract'
        checkpoint['springer_api_status']='FOUND'
        merged=springer.merge_springer_records(checkpoint,self.rows())
        with patch.object(springer,'request_springer_metadata') as request, patch.object(springer,'save_checkpoint'), contextlib.redirect_stdout(io.StringIO()):
            enriched=springer.enrich_records(merged,'offline-test')
        request.assert_not_called()
        self.assertEqual(enriched.abstract.tolist(),['Existing abstract']*3)
        self.assertEqual(enriched.springer_api_status.tolist(),['FOUND']*3)

if __name__=='__main__':
    unittest.main()
