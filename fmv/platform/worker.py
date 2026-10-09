import json
import hashlib
import os
from pathlib import Path
from dataclasses import asdict
from fmv.core.valuation import Assumptions, dcf
from fmv.platform.store import Store
from fmv.agents.ollama import OllamaAgent

ROLE='You are a cautious financial analyst. Distinguish data from assumptions. Never claim independently verified figures. You are not a trading agent.'

def verify(value, inputs):
    assert value.fair_value_per_share == value.equity_value / inputs['shares']
    assert abs(value.enterprise_value-value.explicit_pv-value.terminal_pv) < 1e-7*max(1,abs(value.enterprise_value))

def process(store, task, artifacts, model, use_llm=True):
    id=task['id']
    data=json.loads(task['payload'])
    store.event(id,'START','valuation started')
    try:
        for field in ('ticker','fcf','shares','cash','debt','discount_rate','terminal_growth','growth_rates'):
            if field not in data: raise ValueError(f'missing required input {field}')
        a=Assumptions(float(data['discount_rate']),float(data['terminal_growth']),tuple(map(float,data['growth_rates'])))
        result=dcf(float(data['fcf']),float(data['shares']),float(data['cash']),float(data['debt']),a)
        verify(result,data)
        store.event(id,'VALUATION','deterministic DCF verified')
        narrative='LLM analysis disabled; figures are provided by task author.'
        if use_llm:
            try:
                narrative=OllamaAgent(model).ask(ROLE, 'Critique the following USER-SUPPLIED assumptions. Do not invent external filings or prices. Identify risks and unanswered questions.\n'+json.dumps(data))
            except Exception as exc:
                narrative='LLM analysis unavailable: '+str(exc)
                store.event(id,'LLM_WARNING',str(exc)[:400])
        folder=Path(artifacts)/id
        folder.mkdir(parents=True,exist_ok=True)
        report={'task_id':id,'ticker':data['ticker'],'status':'COMPLETED','verified':'arithmetic only; source data is user supplied','inputs':data,'valuation':asdict(result),'risk_analysis':narrative}
        out=folder/'valuation.json'
        out.write_text(json.dumps(report,indent=2,ensure_ascii=False))
        md=folder/'report.md'
        md.write_text(f"# {data['ticker']} DCF analysis\n\n**Fair value/share (input currency):** {result.fair_value_per_share:.4f}\n\n**Source status:** UNVERIFIED, user-supplied inputs.\n\n## Risks\n{narrative}\n")
        for file in (out,md): store.add_artifact(id,str(file),hashlib.sha256(file.read_bytes()).hexdigest())
        store.update(id,'COMPLETED')
        store.event(id,'DONE','results saved')
        return report
    except Exception as exc:
        store.update(id,'FAILED',str(exc))
        store.event(id,'FAILED',str(exc)[:400])
        raise
