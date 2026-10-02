"""Offline tests for refreshing reused checkpoint bibliography."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import pandas as pd
from test_pipeline_regressions import assessment, screening, core


class ScreeningBibliographyTests(unittest.TestCase):
    def article(self, **updates):
        row=dict(master_id='MASTER-0001',source_id='old-source',database='IEEE Xplore',title='Same title',abstract='Same abstract',keywords='Same keywords',authors='',year='',publication='',volume='',document_type='',doi='',url='')
        row.update(updates)
        return row

    def success(self, article=None):
        article=self.article() if article is None else article
        return screening.create_success_result(article,assessment(),'RETAIN','Original reason','')

    def refreshed_article(self):
        return self.article(source_id='new-source',authors='Recovered author',year='2024',publication='Recovered journal',volume='12',document_type='Article',doi='10.1234/recovered',url='https://example.org/recovered')

    def test_reconciliation_refreshes_all_exported_bibliographic_fields(self):
        saved=self.success()
        saved['extra_saved_column']='Preserved'
        current=self.refreshed_article()
        reused=screening.reconcile_checkpoint(pd.DataFrame([saved]),pd.DataFrame([current]))
        self.assertEqual(len(reused),1)
        for field in screening.BIBLIOGRAPHIC_RESULT_FIELDS:
            self.assertEqual(reused[0][field],current[field])
        for field,value in saved.items():
            if field not in screening.BIBLIOGRAPHIC_RESULT_FIELDS:
                self.assertEqual(reused[0][field],value)
        self.assertEqual(saved['doi'],'')

    def test_change_detector_distinguishes_changed_from_unchanged(self):
        saved=self.success()
        checkpoint=pd.DataFrame([saved])
        unchanged=screening.reconcile_checkpoint(checkpoint,pd.DataFrame([self.article()]))
        changed=screening.reconcile_checkpoint(checkpoint,pd.DataFrame([self.refreshed_article()]))
        self.assertFalse(screening.reusable_bibliography_changed(checkpoint,unchanged))
        self.assertTrue(screening.reusable_bibliography_changed(checkpoint,changed))

    def test_missing_legacy_master_columns_preserve_saved_values(self):
        saved=self.success(self.article(authors='Saved author',doi='10.1234/saved'))
        current=self.article()
        del current['authors']
        del current['doi']
        refreshed=screening.reconcile_checkpoint(pd.DataFrame([saved]),pd.DataFrame([current]))[0]
        self.assertEqual(refreshed['authors'],'Saved author')
        self.assertEqual(refreshed['doi'],'10.1234/saved')

    def test_explicit_master_removals_are_reflected(self):
        saved=self.success(self.article(authors='Old author',doi='10.1234/old'))
        refreshed=screening.reconcile_checkpoint(pd.DataFrame([saved]),pd.DataFrame([self.article()]))[0]
        self.assertEqual(refreshed['authors'],'')
        self.assertEqual(refreshed['doi'],'')

    def test_legacy_checkpoint_without_volume_gains_column(self):
        saved=self.success()
        del saved['volume']
        checkpoint=pd.DataFrame([saved])
        reused=screening.reconcile_checkpoint(checkpoint,pd.DataFrame([self.article(volume='12')]))
        self.assertEqual(reused[0]['volume'],'12')
        self.assertTrue(screening.reusable_bibliography_changed(checkpoint,reused))

    def test_screening_metadata_changes_still_require_reanalysis(self):
        for field in ('title','abstract','keywords'):
            with self.subTest(field=field):
                current=self.article(**{field:'Changed content'})
                self.assertEqual(screening.reconcile_checkpoint(pd.DataFrame([self.success()]),pd.DataFrame([current])),[])

    def test_configuration_or_prompt_changes_still_invalidate_results(self):
        for field in ('model','prompt_version','classifier_version','prompt_hash'):
            with self.subTest(field=field):
                saved=self.success()
                saved[field]='different'
                self.assertEqual(screening.reconcile_checkpoint(pd.DataFrame([saved]),pd.DataFrame([self.article()])),[])

    def test_api_errors_are_not_reused(self):
        saved=screening.create_error_result(self.article(),RuntimeError('Offline test'))
        self.assertEqual(screening.reconcile_checkpoint(pd.DataFrame([saved]),pd.DataFrame([self.refreshed_article()])),[])

    def test_no_abstract_results_refresh_without_changing_decision(self):
        old=self.article(abstract='')
        current=self.refreshed_article()
        current['abstract']=''
        saved=screening.create_no_abstract_result(old)
        reused=screening.reconcile_checkpoint(pd.DataFrame([saved]),pd.DataFrame([current]))[0]
        self.assertEqual(reused['doi'],current['doi'])
        self.assertEqual(reused['decision'],'UNCERTAIN')
        self.assertEqual(reused['api_status'],'NO_ABSTRACT')
        self.assertEqual(reused['ai'],'NOT_EVALUATED')

    def test_complete_workbook_refresh_is_saved_without_api_calls(self):
        old=self.success()
        current=self.refreshed_article()
        with tempfile.TemporaryDirectory() as directory:
            directory=Path(directory)
            output=directory/f"screening_ieee_v{core.CLASSIFIER_VERSION.replace('.', '_')}.xlsx"
            screening.save_checkpoint([old],output,'IEEE Xplore',1)
            with patch.object(screening,'PROCESSED_DIR',directory), patch.object(core,'analyze_article') as analyze, contextlib.redirect_stdout(io.StringIO()):
                status=screening.process_database(pd.DataFrame([current]),screening.DATABASES['1'],Mock())
            analyze.assert_not_called()
            self.assertEqual(status,'COMPLETED')
            saved=screening.load_checkpoint(output).iloc[0]
            retained=pd.read_excel(output,sheet_name='RETAIN').iloc[0]
            for field in ('doi','authors','publication','source_id','url'):
                self.assertEqual(saved[field],current[field])
                self.assertEqual(retained[field],current[field])
            self.assertEqual(saved['decision'],'RETAIN')
            self.assertEqual(saved['evidence_ai'],old['evidence_ai'])
            self.assertEqual(saved['decision_reason'],old['decision_reason'])
            self.assertEqual(saved['metadata_hash'],old['metadata_hash'])

    def test_complete_no_abstract_workbook_refresh_is_saved_without_api_calls(self):
        old=screening.create_no_abstract_result(self.article(abstract=''))
        current=self.refreshed_article()
        current['abstract']=''
        with tempfile.TemporaryDirectory() as directory:
            directory=Path(directory)
            output=directory/f"screening_ieee_v{core.CLASSIFIER_VERSION.replace('.', '_')}.xlsx"
            screening.save_checkpoint([old],output,'IEEE Xplore',1)
            with patch.object(screening,'PROCESSED_DIR',directory), patch.object(core,'analyze_article') as analyze, contextlib.redirect_stdout(io.StringIO()):
                status=screening.process_database(pd.DataFrame([current]),screening.DATABASES['1'],Mock())
            analyze.assert_not_called()
            self.assertEqual(status,'COMPLETED')
            saved=screening.load_checkpoint(output).iloc[0]
            manual=pd.read_excel(output,sheet_name='No_abstract').iloc[0]
            self.assertEqual(saved['doi'],current['doi'])
            self.assertEqual(manual['doi'],current['doi'])
            self.assertEqual(saved['api_status'],'NO_ABSTRACT')

    def test_refresh_write_failure_preserves_checkpoint_and_stops(self):
        old=self.success()
        current=self.refreshed_article()
        with tempfile.TemporaryDirectory() as directory:
            directory=Path(directory)
            output=directory/f"screening_ieee_v{core.CLASSIFIER_VERSION.replace('.', '_')}.xlsx"
            screening.save_checkpoint([old],output,'IEEE Xplore',1)
            original=output.read_bytes()
            with patch.object(screening,'PROCESSED_DIR',directory), patch.object(screening.os,'replace',side_effect=OSError('Simulated replacement failure')), patch.object(core,'analyze_article') as analyze, contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(OSError):
                    screening.process_database(pd.DataFrame([current]),screening.DATABASES['1'],Mock())
            analyze.assert_not_called()
            self.assertEqual(output.read_bytes(),original)
            self.assertEqual(list(directory.glob('.*.xlsx')),[])

    def test_unchanged_complete_checkpoint_does_not_need_rewrite(self):
        with patch.object(screening,'load_checkpoint',return_value=pd.DataFrame([self.success()])), patch.object(screening,'save_checkpoint') as save, patch.object(core,'analyze_article') as analyze, contextlib.redirect_stdout(io.StringIO()):
            status=screening.process_database(pd.DataFrame([self.article()]),screening.DATABASES['1'],Mock())
        self.assertEqual(status,'COMPLETED')
        save.assert_not_called()
        analyze.assert_not_called()

    def test_refreshed_results_are_saved_before_processing_pending_articles(self):
        old=self.success()
        current=self.refreshed_article()
        pending=self.article(master_id='MASTER-0002',title='New study')
        calls=[]
        def capture(results,*args):
            calls.append([dict(result) for result in results])
        def analyze(**kwargs):
            self.assertEqual(calls[0][0]['doi'],current['doi'])
            return assessment()
        with patch.object(screening,'load_checkpoint',return_value=pd.DataFrame([old])), patch.object(screening,'save_checkpoint',side_effect=capture), patch.object(core,'analyze_article',side_effect=analyze) as analyze_mock, patch.object(screening.time,'sleep'), contextlib.redirect_stdout(io.StringIO()):
            status=screening.process_database(pd.DataFrame([current,pending]),screening.DATABASES['1'],Mock())
        self.assertEqual(status,'COMPLETED')
        analyze_mock.assert_called_once()
        self.assertEqual(len(calls),2)
        self.assertEqual(len(calls[-1]),2)

if __name__=='__main__':
    unittest.main()
