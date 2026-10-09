"""Read-only report display and queue UI; supports legacy reports without crashing."""
import json
import os
import re
import uuid
from pathlib import Path

import streamlit as st
from fmv.platform.store import Store
from fmv.reports.schema import normalize_report

st.set_page_config(page_title='Aurorain FMV Autonomous Platform', layout='wide')
st.title('Aurorain FMV Autonomous Platform')
st.caption('Research drafts only · SEC evidence may be incomplete · no automatic trading')
root = Path(os.environ.get('FMV_RUNTIME', Path.cwd() / 'runtime'))
store = Store(root / 'state.db')

with st.form('new_task'):
    ticker = st.text_input('US-listed ticker', 'MU').strip().upper()
    auto = st.checkbox('Let DeepSeek propose bounded, unverified assumptions (research draft)', value=True)
    c1, c2 = st.columns(2)
    with c1:
        wacc = st.number_input('Discount rate (%)', min_value=1.0, max_value=50.0, value=12.0)
    with c2:
        terminal = st.number_input('Terminal growth (%)', min_value=-5.0, max_value=9.0, value=3.0)
    forecast = st.text_input('Annual FCF growth (%) comma-separated', '10,8,6,4,3')
    if st.form_submit_button('Queue SEC valuation'):
        try:
            if not re.fullmatch(r'[A-Z][A-Z0-9.\-]{0,9}', ticker):
                raise ValueError('Ticker must be a valid US ticker identifier')
            rates = [float(x.strip()) / 100 for x in forecast.split(',') if x.strip()]
            if not 1 <= len(rates) <= 15 or any(abs(x) > 2 for x in rates) or wacc <= terminal:
                raise ValueError('Use 1–15 plausible rates and discount > terminal growth')
            payload = {'ticker':ticker, 'type':'sec_valuation'}
            if not auto:
                payload['assumptions']={'discount_rate':wacc/100,'terminal_growth':terminal/100,'growth_rates':rates}
            task_id = str(uuid.uuid4())
            store.submit(task_id, ticker, payload)
            st.success(f'Queued {task_id}. Execute python -m fmv.platform.cli run-once or wait for scheduler.')
        except (ValueError, TypeError) as exc:
            st.error(str(exc))

st.subheader('Task history')
rows = store.tasks()
st.dataframe(rows, use_container_width=True)
for task in rows[:30]:
    with st.expander(f"{task['ticker']} — {task['status']} — {task['id'][:8]}"):
        if task.get('error'):
            st.warning(str(task['error']))
        path = root / 'artifacts' / task['id'] / 'valuation.json'
        if not path.is_file():
            st.info('No report artifact yet. The worker may not have run, or this task failed.')
            continue
        try:
            raw_bytes = path.read_bytes()
            view = normalize_report(json.loads(raw_bytes), task['ticker'])
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            st.error(f'Report cannot be parsed: {exc}')
            continue
        st.write('Report type:', view.kind)
        st.write('Schema version:', view.schema_version)
        st.warning(view.label + '. No automatic investment recommendations.')
        if view.fair_value_per_share is None:
            st.error('Fair value is absent or invalid. No numeric estimate is displayed.')
        else:
            st.metric('Indicative DCF value/share (USD)', f'${view.fair_value_per_share:,.2f}')
        st.write('Data provenance:', view.provenance)
        if view.financial_data is None:
            st.warning('Financial evidence unavailable (legacy/demo/incomplete result).')
        else:
            st.markdown('### Financial evidence')
            st.json(view.financial_data)
        if view.assumptions is not None:
            st.markdown('### Forecast assumptions')
            st.json(view.assumptions)
        if view.warnings:
            st.markdown('### Warnings')
            for warning in view.warnings:
                st.warning(warning)
        st.markdown('### Research')
        st.write(view.research or 'Not available')
        st.markdown('### Independent critique')
        st.write(view.review or 'Not available')
        st.download_button('Download report JSON', data=raw_bytes,
                           file_name=f"{task['ticker']}_{task['id']}.json",
                           mime='application/json', key=f"json-{task['id']}")
