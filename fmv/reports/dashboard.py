from pathlib import Path
import os
import sqlite3
import streamlit as st

st.set_page_config(page_title='FMV Autonomous Agent Platform',layout='wide')
st.title('FMV Autonomous Agent Platform')
st.caption('Local execution status. Estimates are NOT investment advice.')
db=Path(os.environ.get('FMV_RUNTIME',Path.cwd()/'runtime'))/'state.db'
if not db.exists():
    st.info('No tasks yet. Run: python -m fmv.platform.cli submit tasks/example.json')
else:
    with sqlite3.connect(db) as connection:
        rows=connection.execute('SELECT id,ticker,status,updated_at,error FROM tasks ORDER BY updated_at DESC').fetchall()
    st.dataframe([dict(zip(['id','ticker','status','updated_at','error'],r)) for r in rows],use_container_width=True)
    st.caption('Source financial data and DCF assumptions must be independently checked.')
