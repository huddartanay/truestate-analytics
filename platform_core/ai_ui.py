"""Native Streamlit market-intelligence presentation; backend audits stay private.

The summary is a first-class dashboard section. The assistant is a single shared
dialog opened by a small page-header control; its context and all answer work
remain supplied by the existing snapshot/backend contracts.
"""
from dataclasses import asdict
from datetime import datetime
import streamlit as st
from intelligence.production.store import production_root,ProductionUnavailable
from intelligence.production.artifacts import validate_serving
from intelligence.query.models import QueryRequest
from intelligence.current.cache import read,root_path
from platform_core import ai_service as service,ai_presentation as presentation


ASSISTANT_OPEN = 'truestate.ai.assistant_open'


def _container(key):
    """Use stable semantic container keys without breaking older Streamlit builds."""
    try:
        return st.container(key=key)
    except TypeError:  # pragma: no cover - compatibility with Streamlit < 1.45
        return st.container()


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


def render_trigger() -> None:
    """Render the shared assistant entry control at the top-right of a page."""
    _, action = st.columns([6, 2], gap='small')
    with action:
        with _container('truestate-ai-trigger'):
            if st.button('✦  Market Assistant', key='truestate.ai.open',
                         use_container_width=True):
                st.session_state[ASSISTANT_OPEN] = True
                st.rerun()


def _summary_state(snapshot, build):
    """Return the existing session state, invalidating it for a new context."""
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
    return state,current,now,as_of,day


def _render_summary(snapshot, build, state, current, now, as_of, day):
    """Render the always-visible summary section without changing its backend."""
    with _container('truestate-ai-summary'):
        heading, action = st.columns([5, 1], gap='medium')
        with heading:
            st.markdown(
                '<div class="truestate-ai-summary-heading">'
                '<div class="truestate-ai-kicker">✦ Intelligence layer</div>'
                '<h2>Market Intelligence Summary</h2>'
                '<p>A clear overview of the latest market signals, activity and developments.</p>'
                '</div>', unsafe_allow_html=True)
        with action:
            action_label='Refresh summary' if state['summary'] else 'Generate summary'
            summary_clicked=st.button(action_label,key='truestate.ai.summary',use_container_width=True)
        if summary_clicked:
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
        if timestamp:
            st.caption(presentation.freshness(timestamp))
        else:
            st.caption('Ready when you are · using the latest available market information.')


def _dismiss_assistant() -> None:
    st.session_state[ASSISTANT_OPEN] = False


def _assistant_content(snapshot, build, state):
    """Render the reusable assistant body inside the native Streamlit dialog."""
    st.caption('Ask about UAE property markets, projects, prices, rents, transactions and recent developments.')
    now=datetime.now(presentation.DISPLAY_ZONE)
    as_of=now.isoformat()
    # Recheck availability after the freshness window, not on each rerun.
    last=presentation.parsed(state.get('suggestions_at'))
    if last is None or (now-last).total_seconds()>=900:
        state['suggestions']=service.suggestions(build,snapshot.context,as_of);state['suggestions_at']=as_of
    st.markdown('<div class="truestate-ai-dialog-label">Suggested questions</div>', unsafe_allow_html=True)
    chosen=None
    suggestions=state.get('suggestions',())
    suggestion_cols=st.columns(2, gap='small')
    for i,suggestion in enumerate(suggestions):
        with suggestion_cols[i % 2]:
            with _container('truestate-ai-suggestion-'+suggestion.question_id):
                if st.button(suggestion.question,key='truestate.ai.suggestion.'+suggestion.question_id,
                             use_container_width=True):chosen=suggestion.request
    if len(suggestions)<5:
        st.caption('Showing the questions supported by the latest available information.')
    with st.form('truestate.ai.question',clear_on_submit=True):
        question=st.text_input('Ask the Market Assistant',max_chars=1000,
                               placeholder='e.g. How are rents performing in this market?')
        submitted=st.form_submit_button('Ask')
    if submitted and question.strip():
        chosen=QueryRequest(question=question.strip(),page_context=snapshot.context,
                            as_of=datetime.now(presentation.DISPLAY_ZONE))
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
            alternatives=[s.question for s in state.get('suggestions',()) if s.question.casefold()!=chosen.question.casefold()]
            result=service.display_result(raw,request=chosen,alternatives=alternatives)
            progress.update(label='Your answer is ready' if result.status in ('ANSWER','PARTIAL_DATA') else 'Your request is complete',state='complete')
        state['history'].append(dict(question=chosen.question,request_key=service.request_key(chosen,build,fingerprint),**asdict(result)))
        state['history']=state['history'][-8:]
    for item in state.get('history',()):
        with st.chat_message('user'):st.text(item['question'])
        with st.chat_message('assistant'):show(service.View(item['status'],item['answer'],item['sources'],item.get('alternatives',())))
    if state.get('history') and st.button('Clear conversation',key='truestate.ai.clear'):
        state['history']=[];st.rerun()


if hasattr(st, 'dialog'):
    @st.dialog('TruEstate Market Assistant', width='large', dismissible=True,
               on_dismiss=_dismiss_assistant)
    def _assistant_dialog(snapshot, build, state):
        _assistant_content(snapshot, build, state)
else:  # pragma: no cover - compatibility fallback for old Streamlit versions
    def _assistant_dialog(snapshot, build, state):
        with _container('truestate-ai-assistant-fallback'):
            _assistant_content(snapshot, build, state)


def render(snapshot):
    """Render summary and, when requested, the separate assistant experience."""
    try:build=validate_serving(production_root())
    except ProductionUnavailable:build=None
    state,current,now,as_of,day=_summary_state(snapshot,build)
    _render_summary(snapshot,build,state,current,now,as_of,day)
    if st.session_state.get(ASSISTANT_OPEN):
        _assistant_dialog(snapshot,build,state)


def safe_render(factory):
    try:render(factory())
    except Exception:st.info('The Market Assistant is temporarily unavailable. Your dashboard remains available.')
