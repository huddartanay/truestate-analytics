"""One native Streamlit component for six existing analytical contexts."""
from dataclasses import asdict
from datetime import datetime
import streamlit as st
from intelligence.production.store import production_root,ProductionUnavailable
from intelligence.production.artifacts import validate_serving
from intelligence.query.models import QueryRequest
from platform_core import ai_service as service


def show(view):
    # Only Stage 16's final verified text reaches Markdown. HTML remains disabled.
    if view.status in ('ANSWER','PARTIAL_DATA'):
        st.markdown(view.answer)
        if view.status=='PARTIAL_DATA':st.caption('Some requested evidence is unavailable. The answer covers only the supported facts.')
        if view.sources:
            with st.expander('Sources and dates'):
                for source in view.sources:
                    st.text(f"[{source['evidence_id']}] {source['source']}")
                    if source.get('url'):st.link_button('Open source article',source['url'])
                    elif source.get('reference'):st.caption(source['reference'])
                    if source.get('published_at'):st.caption('Published: '+source['published_at'])
                    if source.get('retrieved_at'):st.caption('Retrieved: '+source['retrieved_at'])
    else:st.info(view.answer)


def render(snapshot):
    with st.expander('✨ AI Market Summary',expanded=False):
        st.caption(snapshot.caption)
        try:build=validate_serving(production_root())
        except ProductionUnavailable:
            st.info('TruEstate intelligence data is currently unavailable.')
            build=None
        as_of=build.completed_at if build else datetime.now().astimezone().replace(hour=0,minute=0,second=0,microsecond=0).isoformat()
        key=service.context_key(snapshot.context,snapshot.facts,snapshot.selection,build,as_of)
        state=st.session_state.get('truestate.ai')
        if not state or state['context_key']!=key:
            state={'context_key':key,'summary':None,'history':[],
                'suggestions':service.suggestions(build,snapshot.context,as_of)}
            st.session_state['truestate.ai']=state
        if build:st.caption('Intelligence updated: '+build.completed_at+' · Summary runs only when requested.')
        if st.button('Refresh summary' if state['summary'] else 'Generate summary',key='truestate.ai.summary'):
            with st.spinner('Checking the available evidence and preparing your summary… This may take a little longer when the service is busy.'):
                result=service.display_result(service.call('summary',build,context=snapshot.context,facts=snapshot.facts,secrets=st.secrets))
            # Failures are displayed but never treated as a reusable successful summary.
            state['summary']=asdict(result) if result.status in ('ANSWER','PARTIAL_DATA') else None
            if state['summary'] is None:show(result)
        if state['summary']:show(service.View(**state['summary']))
        with st.expander('Ask TruEstate',expanded=False):
            st.caption('Ask about UAE property markets. Suggested questions use available intelligence; dashboard filters do not constrain explicit questions about another UAE location.')
            chosen=None
            if not state['suggestions']:
                # Transient suggestion failures may recover on the next rerun.
                state['suggestions']=service.suggestions(build,snapshot.context,as_of)
            for suggestion in state['suggestions']:
                if st.button(suggestion.question,key='truestate.ai.suggestion.'+suggestion.question_id,use_container_width=True):chosen=suggestion.request
            if len(state['suggestions'])!=5:st.caption('Suggested questions are temporarily unavailable.')
            with st.form('truestate.ai.question',clear_on_submit=True):
                question=st.text_input('Your UAE real-estate question',max_chars=1000)
                submitted=st.form_submit_button('Ask TruEstate')
            if submitted and question.strip():
                chosen=QueryRequest(question=question.strip(),page_context=snapshot.context,as_of=datetime.fromisoformat(as_of))
            if chosen:
                with st.spinner('Retrieving and checking TruEstate evidence…'):
                    result=service.display_result(service.call('help',build,request=chosen,secrets=st.secrets))
                state['history'].append(dict(question=chosen.question,**asdict(result)))
                state['history']=state['history'][-8:]
            for item in state['history']:
                with st.chat_message('user'):st.text(item['question'])
                with st.chat_message('assistant'):show(service.View(item['status'],item['answer'],item['sources']))
            if state['history'] and st.button('Clear conversation',key='truestate.ai.clear'):
                state['history']=[];st.rerun()


def safe_render(factory):
    # Analytics and navigation must survive adapter/storage failures. Never render
    # exception bodies or raw backend results into the product interface.
    try:render(factory())
    except Exception:st.info('AI assistance is temporarily unavailable. Your dashboard remains available.')
