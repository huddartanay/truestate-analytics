"""Offline business presentation and answerable shortcut contract checks."""
import copy,json,re,tempfile,unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from intelligence import config as cfg
from intelligence.current.cache import read,root_path
from intelligence.current.retrieval import help_package,summary_package
from intelligence.current.suggestions import available_suggestions
from intelligence.production.store import load_build
from intelligence.query.models import QueryRequest,PageContext
from intelligence.answer_engine.engine import AnswerEngine
from intelligence.answer_engine.models import Fact
from platform_core import ai_presentation as presentation,ai_service,ai_facts

class Echo:
    def structured(self,**kw):
        p=json.loads(kw['messages'][1]['content']);fields=('evidence_id','value','unit','location','period','provenance','nature','rank')
        return {'contract':{'status':p['status'],'claims':[{**{k:f[k] for k in fields},'text':None} for f in p['evidence_data']]}}

PAGES=[('dubai','DUBAI',None),('abu_dhabi','ABU_DHABI',None),('sharjah','SHARJAH',None),('rak','RAS_AL_KHAIMAH',None),('area','DUBAI','Business Bay'),('forecast','DUBAI',None)]

class PresentationTests(unittest.TestCase):
    def test_friendly_dates(self):
        now=datetime(2026,9,9,16,tzinfo=presentation.DISPLAY_ZONE)
        value='2026-09-09T08:52:09.898891+00:00'
        self.assertEqual(presentation.freshness(value,now),'Market intelligence updated today at 12:52 PM (UAE time)')
        self.assertIn('yesterday',presentation.freshness('2026-09-08T08:52:09+00:00',now))
        self.assertEqual(presentation.freshness('2026-09-01T08:00:00Z',now),'Market intelligence updated 1 Sep 2026')
        self.assertEqual(presentation.freshness('invalid',now),'')
        self.assertNotIn('T08',presentation.date_label(value))
    def test_plain_numeric_semantics(self):
        fact=Fact(evidence_id='E1',identity='TEST_ONLY',origin='DASHBOARD',kind='OBSERVATION',location='Dubai',metric='SALE_PRICE_CHANGE',value='8.4',unit='PERCENT',period='2026-02',basis='YOY',provenance='SOURCE_REPORTED',nature='OBSERVED',source='Khaleej Times — Business')
        text=presentation.numeric(fact)
        self.assertIn('8.4% higher',text);self.assertIn('same period a year earlier',text)
        self.assertIn('February 2026',text);self.assertIn('Khaleej Times',text)
        self.assertNotIn('YOY',text);self.assertNotIn('SOURCE_REPORTED',text)
        lowered=presentation.numeric(fact.model_copy(update={'value':'-1.3'}));self.assertIn('1.3% lower',lowered)
        forecast=presentation.numeric(fact.model_copy(update={'nature':'SOURCE_REPORTED_FORECAST'}))
        self.assertIn('expectation, not an observed outcome',forecast)
    def test_numeric_dimensions_and_currency(self):
        f=Fact(evidence_id='E1',identity='TEST_ONLY',origin='DASHBOARD',kind='OBSERVATION',location='Sharjah',metric='transaction value',value='18.5',unit='AED billion',period='2026-Q1',statistic='TOTAL',provenance='SOURCE_REPORTED',nature='OBSERVED',source='Savills')
        line=presentation.numeric(f)
        self.assertIn('Total transaction value was AED 18.5 billion',line)
        self.assertIn('2026 Q1',line)
        self.assertEqual(presentation.clean('&#82;SS Stage 13'),'')
        ranked=f.model_copy(update={'kind':'RANKING','unit':'PERCENT','value':'-2.5','rank':2,'basis':'QOQ'})
        self.assertIn('2.5% lower',presentation.numeric(ranked));self.assertIn('Position in this comparison: 2',presentation.numeric(ranked))
        self.assertIn('previous quarter',presentation.numeric(ranked))

    def test_hidden_technical_errors(self):
        for raw,expected in [({'error':'HTTP 429 OpenRouter AUTH secret'},'TEMPORARILY_UNAVAILABLE'),({'not':'an answer'},'VALIDATION_FAILED')]:
            view=ai_service.display_result(raw);self.assertEqual(view.status,expected)
            self.assertFalse(presentation.TECH.search(view.answer));self.assertNotIn('secret',view.answer)
    def test_no_data_and_scope_messages(self):
        request=QueryRequest(question='What is Khalid Bin City?')
        v=ai_service.display_result({'stopped':'NO_DATA'},request=request,alternatives=['Latest Sharjah projects'])
        self.assertIn('Khalid Bin City',v.answer);self.assertNotIn('checked',v.answer)
        self.assertEqual(v.alternatives,('Latest Sharjah projects',))
        self.assertEqual(ai_service.display_result({'stopped':'OUT_OF_SCOPE'}).answer,presentation.MESSAGES['OUT_OF_SCOPE'])
    def test_question_identity(self):
        a=QueryRequest(question='Latest Dubai projects');b=QueryRequest(question='How are Dubai rents performing?')
        self.assertNotEqual(ai_service.request_key(a,None,'a'),ai_service.request_key(b,None,'a'))
        self.assertNotEqual(ai_service.request_key(a,None,'a'),ai_service.request_key(a,None,'b'))
        self.assertEqual(ai_service.request_key(a,None),ai_service.request_key(a.model_copy(update={'question':'  LATEST   Dubai projects  '}),None))
    def test_no_data_shortcuts_when_storage_absent(self):
        with tempfile.TemporaryDirectory() as tmp,patch.object(cfg,'DB_PATH',Path(tmp)/'missing.db'),patch('intelligence.current.cache.ensure',side_effect=AssertionError('NO_FETCH')):
            self.assertFalse(available_suggestions(PageContext(page_type='EMIRATE',emirate='DUBAI'),current=()).suggestions)

class RealUXTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.current=read(root_path())
        if not cls.current:raise unittest.SkipTest('Real cached smoke required; this test never fetches it')
        cls.build=load_build()
    def setUp(self):
        self.db=patch.object(cfg,'DB_PATH',self.build.path);self.db.start()
        self.net=patch('socket.socket.connect',side_effect=AssertionError('NO_NETWORK'));self.net.start()
        self.refresh=patch('intelligence.current.cache.ensure',side_effect=AssertionError('NO_REFRESH'));self.refresh.start()
    def tearDown(self):self.refresh.stop();self.net.stop();self.db.stop()
    def answer(self,p):return AnswerEngine(client_factory=lambda **kw:Echo(),max_attempts=1)._answer(lambda:p)
    def test_every_suggestion_is_answerable_on_all_pages(self):
        for page,scope,area in PAGES:
            with self.subTest(page=page):
                items=available_suggestions(ai_facts.context(page,scope,area),current=self.current).suggestions
                self.assertLessEqual(len(items),5);self.assertTrue(items)
                self.assertEqual(len({s.action_id for s in items}),len(items))
                for s in items:
                    if s.fallback:self.assertIn('UAE',s.question)
                    p=help_package(s.request,current=self.current)
                    self.assertTrue(p.facts);self.assertIn(p.status,('ANSWER','PARTIAL_DATA'))
                    result=self.answer(p);self.assertEqual(result.audit.validation,'PASS')
                    self.assertNotEqual(result.status,'NO_DATA')
    def test_native_widgets_every_suggestion_and_progress(self):
        from streamlit.testing.v1 import AppTest
        from platform_core import ai_ui
        import streamlit as st
        calls=[];statuses=[];original_status=st.status
        def shortcuts(build,context,as_of):
            return available_suggestions(context,as_of=as_of,current=self.current).suggestions
        def backend(operation,build,**kw):
            calls.append(operation)
            self.assertTrue(statuses,'Visible processing state must exist before answering')
            package=help_package(kw['request'],current=self.current) if operation=='help' else summary_package(kw['context'],kw['facts'],self.current)
            return self.answer(package).model_dump(mode='json')
        def progress(label,**kw):
            self.assertFalse(presentation.TECH.search(label));statuses.append(label)
            return original_status(label,**kw)
        script="""import streamlit as st
from platform_core import ai_ui,ai_facts
page,scope,area=st.session_state['test_page']
ai_ui.render(ai_facts.Snapshot(ai_facts.context(page,scope,area),(),'real stored reporting',''))
"""
        with patch.object(ai_service,'suggestions',side_effect=shortcuts),patch.object(ai_service,'call',side_effect=backend),patch.object(st,'status',side_effect=progress):
            for page in PAGES:
                with self.subTest(page=page[0]):
                    app=AppTest.from_string(script,default_timeout=30)
                    app.session_state['test_page']=page;before=len(calls);app.run()
                    self.assertFalse(app.exception);self.assertEqual(len(calls),before)
                    self.assertIn('TruEstate Market Assistant',[e.label for e in app.expander])
                    self.assertIn('✨ Market Intelligence Summary',[e.label for e in app.expander])
                    buttons=[b.key for b in app.button if (b.key or '').startswith('truestate.ai.suggestion.')]
                    self.assertTrue(buttons)
                    for key in buttons:
                        statuses.clear();app.button(key=key).click().run()
                        self.assertFalse(app.exception)
                        self.assertIn(app.session_state['truestate.ai']['history'][-1]['status'],('ANSWER','PARTIAL_DATA'))
                        self.assertTrue(statuses)
                    statuses.clear();app.button(key='truestate.ai.summary').click().run()
                    self.assertFalse(app.exception);self.assertTrue(statuses)
                    # The outlook may honestly lack evidence; never fabricate it.
                    expected=summary_package(ai_facts.context(*page),(),self.current)
                    self.assertEqual(app.session_state['truestate.ai']['summary'] is not None,expected.status in ('ANSWER','PARTIAL_DATA') and bool(expected.facts))
                    visible='\n'.join(str(e.value) for kind in (app.markdown,app.caption,app.info,app.text) for e in kind)
                    self.assertFalse(presentation.TECH.search(visible));self.assertNotRegex(visible,r'\bE\d+\b|20\d{2}-\d\d-\d\dT')
                    prior=len(calls);app.run();self.assertEqual(len(calls),prior)
                    # A new information fingerprint invalidates only the summary,
                    # retaining the conversation and rechecking available shortcuts.
                    history=list(app.session_state['truestate.ai']['history'])
                    from dataclasses import replace
                    changed=(replace(self.current[0],sha256='f'*64),self.current[1])
                    with patch.object(ai_ui,'read',return_value=changed):app.run()
                    self.assertFalse(app.exception);self.assertEqual(app.session_state['truestate.ai']['history'],history)
                    self.assertIsNone(app.session_state['truestate.ai']['summary'])

    def test_distinct_questions(self):
        text=['What are the latest Dubai projects?','How are Dubai rents performing?','Latest Sharjah projects','Latest Dubai real-estate news','What is the Dubai market outlook?']
        packages=[help_package(QueryRequest(question=q),current=self.current) for q in text]
        ids=[{(f.origin,f.identity) for f in p.facts} for p in packages]
        self.assertNotEqual(ids[0],ids[1]);self.assertNotEqual(ids[0],ids[2]);self.assertNotEqual(ids[0],ids[3]);self.assertFalse(ids[4])
    def test_summary_technical_text_hidden_current_news_last(self):
        p=summary_package(PageContext(page_type='EMIRATE',emirate='DUBAI'),(),self.current)
        a=self.answer(p);before=a.model_dump_json()
        view=ai_service.display_result(a.model_dump(mode='json'),summary=True)
        self.assertEqual(a.model_dump_json(),before)
        self.assertIn('Market at a glance',view.answer)
        self.assertFalse(presentation.TECH.search(view.answer));self.assertNotRegex(view.answer,r'\bE\d+\b|\d{4}-\d\d-\d\dT')
        headings=re.findall(r'^### (.+)$',view.answer,re.M)
        self.assertIn(headings[-1],('Projects & developments','Latest property news'))
        self.assertIn('Khaleej Times',view.answer);self.assertIn('View source',view.answer)
        self.assertLessEqual(len(p.facts),10)
        self.assertTrue(any(f.origin=='CURRENT_RSS' for f in p.facts))
    def test_clean_sources(self):
        p=help_package(QueryRequest(question='Latest Dubai projects'),current=self.current)
        view=ai_service.display_result(self.answer(p).model_dump(mode='json'))
        self.assertTrue(view.sources)
        self.assertEqual(len({s['url'] for s in view.sources}),len(view.sources))
        for s in view.sources:
            self.assertTrue(s['source']);self.assertTrue(s['article_title']);self.assertTrue(s['url']);self.assertTrue(s['published_at'])
            self.assertNotIn('source_id',s);self.assertNotIn('rss_url',s);self.assertNotRegex(s['published_at'],r'\d\d:\d\d')
    def test_rejected_answer_never_visible(self):
        p=help_package(QueryRequest(question='Latest Dubai projects'),current=self.current)
        raw=self.answer(p).model_dump(mode='json');raw['audit']['validation']='FAIL';raw['answer']='UNVERIFIED DRAFT'
        v=ai_service.display_result(raw)
        self.assertEqual(v.status,'VALIDATION_FAILED');self.assertNotIn('UNVERIFIED',v.answer);self.assertFalse(v.sources)

if __name__=='__main__':unittest.main()
