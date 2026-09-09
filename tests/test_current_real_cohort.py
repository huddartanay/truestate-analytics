"""Read-only reference checks when a real attested smoke cache is available.

No network, copied synthetic story, or production fixture fallback is used.
"""
import unittest
from unittest.mock import patch
from intelligence.current.cache import read,root_path
from intelligence.current.retrieval import help_package,current_package,summary_package
from intelligence.production.store import load_build,readonly,digest
from intelligence.query.models import QueryRequest,PageContext
from intelligence.answer_engine.engine import AnswerEngine
from intelligence.answer_engine.models import RichGenerated
from intelligence import config as cfg

class Echo:
    def structured(self,**kw):
        import json
        p=json.loads(kw['messages'][1]['content']);fields=('evidence_id','value','unit','location','period','provenance','nature','rank')
        return {'contract':{'status':p['status'],'claims':[{**{k:f[k] for k in fields},'text':None} for f in p['evidence_data']]}}

class RealCohortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.current=read(root_path())
        if not cls.current:raise unittest.SkipTest('No attested current RSS cache; run the separately authorized smoke first')
        cls.history=load_build()
    def setUp(self):
        self.before=digest(self.current[0].path)
        self.path=patch.object(cfg,'DB_PATH',self.history.path);self.path.start()
        self.network=patch('socket.socket.connect',side_effect=AssertionError('OFFLINE'));self.network.start()
    def tearDown(self):
        self.network.stop();self.path.stop();self.assertEqual(digest(self.current[0].path),self.before)
    def test_project_scope_and_metadata(self):
        for emirate in ('DUBAI','SHARJAH','RAS_AL_KHAIMAH'):
            text='Latest '+emirate.replace('_',' ')+' projects'
            p=current_package(QueryRequest(question=text),self.current[0])
            for f in p.facts:
                self.assertEqual(f.origin,'CURRENT_RSS');self.assertTrue(f.lineage)
                self.assertTrue(f.source);self.assertTrue(f.title)
                self.assertTrue(f.lineage[0].article_url);self.assertTrue(f.lineage[0].retrieved_at)
    def test_question_specific_no_unrelated_substitution(self):
        for text in ['Latest Dubai nonexistentbanana projects','What is Nonexistentbanana City?']:
            p=help_package(QueryRequest(question=text),self.current)
            self.assertEqual(p.status,'NO_DATA');self.assertFalse(p.facts)
    def test_stable_ids_and_historical_path(self):
        req=QueryRequest(question='Latest Dubai projects')
        a=current_package(req,self.current[0]);b=current_package(req,self.current[0])
        self.assertEqual(a.facts,b.facts)
        with patch('intelligence.current.cache.ensure') as refresh:
            p=help_package(QueryRequest(question='How are Dubai rents moving?'))
            refresh.assert_not_called()
        self.assertTrue(all(f.origin=='INTELLIGENCE' for f in p.facts))
    def test_hybrid_summary_and_validation(self):
        p=summary_package(PageContext(page_type='EMIRATE',emirate='DUBAI'),(),self.current)
        self.assertLessEqual(len(p.facts),10)
        self.assertTrue(any(f.origin=='CURRENT_RSS' for f in p.facts))
        self.assertTrue(any(f.origin=='INTELLIGENCE' for f in p.facts))
        a=AnswerEngine(client_factory=lambda **kw:Echo(),max_attempts=1)._answer(lambda:p)
        self.assertEqual(a.audit.validation,'PASS');self.assertIn('Latest intelligence',a.answer)
        self.assertIn('What it means',a.answer);self.assertIn('Sources',a.answer)
        for f in p.facts:self.assertIn('['+f.evidence_id+']',a.answer)
        schema=RichGenerated.model_json_schema();self.assertIn('id',schema['$defs']['SummaryClaim']['properties'])
    def test_existing_worker_uses_current_path(self):
        from intelligence.production.worker import dispatch
        from intelligence.production.store import production_root
        engine=AnswerEngine(client_factory=lambda **kw:Echo(),max_attempts=1)
        with patch('intelligence.answer_engine.AnswerEngine',return_value=engine),patch('intelligence.current.cache.ensure',return_value=self.current):
            result=dispatch({'operation':'help','root':str(production_root()),'artifact':self.history.sha256,'request':{'question':'Latest Dubai projects'}})
        self.assertEqual(result['audit']['validation'],'PASS')
        self.assertTrue(all(f['origin']=='CURRENT_RSS' for f in result['evidence']))

    def test_no_fetch_per_repeated_question(self):
        with patch('intelligence.current.cache.refresh',side_effect=AssertionError('NO_REFRESH')):
            for _ in range(3):help_package(QueryRequest(question='Latest Dubai projects'),self.current)
    def test_no_synthetic_and_pipeline_gates(self):
        with readonly(self.current[0].path) as db:
            stamp=db.execute('SELECT data_class FROM production_build_classification').fetchone()[0]
            self.assertEqual(stamp,'PRODUCTION')
            self.assertFalse(db.execute('SELECT 1 FROM intelligence_articles WHERE stage8_accepted<>1 OR stage9_accepted<>1').fetchone())
        self.assertTrue(all(p['status']=='SUCCESS' for p in self.current[1]['pipeline']))
if __name__=='__main__':unittest.main()
