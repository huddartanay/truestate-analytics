"""Native Streamlit market-assistant presentation; backend audits stay private."""
from dataclasses import asdict
from datetime import datetime
import streamlit as st
from intelligence.production.store import production_root,ProductionUnavailable
from intelligence.production.artifacts import validate_serving
from intelligence.query.models import QueryRequest
from intelligence.current.cache import read,root_path
from platform_core import ai_service as service,ai_presentation as presentation


def show(view):
    if view.status in ('ANSWER','PARTIAL_DATA'):
        st.markdown(view.answer)
        if view.sources:
            with st.expander('Sources'):
                for source in view.sources:
                    st.text(source['source'])
                    if source.get('article_title'):st.text(source['article_title'])
                    if source.get('published_at'):st.caption(source['published_at'])
                    elif source.get('period'):st.caption(source['period'])
                    if source.get('url'):st.link_button('View article',source['url'])
    else:
        st.info(view.answer)
        if view.alternatives:
            st.caption('Try asking:')
            for question in view.alternatives:st.text('• '+question)


def render(snapshot):
    with st.expander('✨ Market Intelligence Summary',expanded=False):
        st.caption('A clear overview of the latest market signals, activity and developments.')
        try:build=validate_serving(production_root())
        except ProductionUnavailable:build=None
        current=read(root_path());fingerprint=current[0].sha256 if current else None
        now=datetime.now(presentation.DISPLAY_ZONE)
        as_of=now.isoformat()
        day=now.date().isoformat()
        key=service.context_key(snapshot.context,snapshot.facts,snapshot.selection,build,day,current_fingerprint=fingerprint)
        page_key=service.context_key(snapshot.context,snapshot.facts,snapshot.selection,build,day)
        state=st.session_state.get('truestate.ai')
        if not state or state.get('page_key')!=page_key:
            state={'context_key':key,'page_key':page_key,'summary':None,'history':[],
                'suggestions':service.suggestions(build,snapshot.context,as_of),'suggestions_at':as_of}
            st.session_state['truestate.ai']=state
        elif state['context_key']!=key:
            state['context_key']=key;state['summary']=None
            state['suggestions']=service.suggestions(build,snapshot.context,as_of);state['suggestions_at']=as_of
        if st.button('Refresh summary' if state['summary'] else 'Generate summary',key='truestate.ai.summary'):
            with st.status('Checking the latest market information and preparing your summary…',expanded=False) as progress:
                result=service.display_result(service.call('summary',build,context=snapshot.context,facts=snapshot.facts,secrets=st.secrets),summary=True)
                progress.update(label='Your summary is ready' if result.status in ('ANSWER','PARTIAL_DATA') else 'Your request is complete',state='complete')
            state['summary']=asdict(result) if result.status in ('ANSWER','PARTIAL_DATA') else None
            if state['summary'] is None:show(result)
            # A requested summary can refresh current information. Refresh only
            # shortcut availability afterwards, with no acquisition/model call.
            current=read(root_path());fingerprint=current[0].sha256 if current else None
            state['context_key']=service.context_key(snapshot.context,snapshot.facts,snapshot.selection,build,day,current_fingerprint=fingerprint)
            state['suggestions']=service.suggestions(build,snapshot.context,datetime.now(presentation.DISPLAY_ZONE).isoformat())
            state['suggestions_at']=datetime.now(presentation.DISPLAY_ZONE).isoformat()
        if state['summary']:show(service.View(**state['summary']))
        timestamp=current[1]['processed_at'] if current else build.completed_at if build else None
        if timestamp:st.caption(presentation.freshness(timestamp))
        st.caption('Ask the Market Assistant for more details.')
        with st.expander('TruEstate Market Assistant',expanded=False):
            st.caption('Ask about UAE property markets, projects, prices, rents, transactions and recent developments.')
            # Recheck availability after the freshness window, not on each rerun.
            last=presentation.parsed(state.get('suggestions_at'))
            if last is None or (now-last).total_seconds()>=900:
                state['suggestions']=service.suggestions(build,snapshot.context,as_of);state['suggestions_at']=as_of
            chosen=None
            for suggestion in state['suggestions']:
                if st.button(suggestion.question,key='truestate.ai.suggestion.'+suggestion.question_id,use_container_width=True):chosen=suggestion.request
            if len(state['suggestions'])<5:st.caption('Showing the questions supported by the latest available information.')
            with st.form('truestate.ai.question',clear_on_submit=True):
                question=st.text_input('Ask the Market Assistant',max_chars=1000)
                submitted=st.form_submit_button('Ask')
            if submitted and question.strip():chosen=QueryRequest(question=question.strip(),page_context=snapshot.context,as_of=datetime.now(presentation.DISPLAY_ZONE))
            if chosen:
                chosen=chosen.model_copy(update={'as_of':datetime.now(presentation.DISPLAY_ZONE)})
                with st.status('Checking the latest market information and preparing your answer…',expanded=False) as progress:
                    raw=service.call('help',build,request=chosen,secrets=st.secrets)
                    current=read(root_path());fingerprint=current[0].sha256 if current else None
                    if raw.get('status')=='NO_DATA' or raw.get('stopped')=='NO_DATA':
                        from intelligence.query.router import route
                        from intelligence.query.models import PageContext
                        decision=route(chosen)
                        ctx=PageContext(page_type='EMIRATE',emirate=decision.filters.emirate) if decision.scope_status=='IN_SCOPE' else snapshot.context
                        state['suggestions']=service.suggestions(build,ctx,datetime.now(presentation.DISPLAY_ZONE).isoformat())
                    alternatives=[s.question for s in state['suggestions'] if s.question.casefold()!=chosen.question.casefold()]
                    result=service.display_result(raw,request=chosen,alternatives=alternatives)
                    progress.update(label='Your answer is ready' if result.status in ('ANSWER','PARTIAL_DATA') else 'Your request is complete',state='complete')
                state['history'].append(dict(question=chosen.question,request_key=service.request_key(chosen,build,fingerprint),**asdict(result)))
                state['history']=state['history'][-8:]
            for item in state['history']:
                with st.chat_message('user'):st.text(item['question'])
                with st.chat_message('assistant'):show(service.View(item['status'],item['answer'],item['sources'],item.get('alternatives',())))
            if state['history'] and st.button('Clear conversation',key='truestate.ai.clear'):
                state['history']=[];st.rerun()


def safe_render(factory):
    try:render(factory())
    except Exception:st.info('The Market Assistant is temporarily unavailable. Your dashboard remains available.')
