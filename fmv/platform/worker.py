"""Actual six-stage orchestration. Never fabricates unavailable fundamentals."""
import hashlib
import json
import os
from dataclasses import asdict
from pathlib import Path
from fmv.core.valuation import Assumptions, dcf
from fmv.platform.store import Store
from fmv.data.sec_client import SECClient
from fmv.data.normalization import extract_financials, MissingFinancialData
from fmv.agents.ollama import OllamaAgent
from fmv.agents.roles import RESEARCH_SYSTEM, REVIEW_SYSTEM
from fmv.agents.assumptions import model_assumptions
from fmv.platform.guardrails import check_assumptions, assess_evidence

def process(store, task, artifacts, model='deepseek-r1:32b', use_llm=True):
    task_id=task['id']
    payload=json.loads(task['payload'])
    folder=Path(artifacts)/task_id
    folder.mkdir(parents=True, exist_ok=True)
    try:
        ticker=payload['ticker'].upper().strip()
        store.event(task_id,'FINANCIAL_DATA','Loading financial evidence')
        if payload.get('type') == 'sec_valuation':
            client=SECClient(os.environ.get('SEC_USER_AGENT',''),str(Path(artifacts).parent/'sec_cache'))
            cik=client.cik_for(ticker)
            evidence=extract_financials(client.companyfacts(cik),payload.get('as_of'))
            verified_source='SEC XBRL (automated conservative extraction, requires analyst review)'
        else:
            for field in ('fcf','shares','cash','debt'):
                if field not in payload: raise ValueError('Missing supplied '+field)
            evidence={k:payload[k] for k in ('fcf','shares','cash','debt')}
            evidence['sources']={}
            evidence['warnings']=['Financial data supplied by task author; NOT SEC verified']
            verified_source='User supplied, unverified'
        (folder/'financial_data.json').write_text(json.dumps(evidence,indent=2))
        if 'assumptions' in payload:
            terms=payload['assumptions']
        else:
            terms={k:payload[k] for k in ('discount_rate','terminal_growth','growth_rates') if k in payload}
        if any(k not in terms for k in ('discount_rate','terminal_growth','growth_rates')):
            if not use_llm:
                raise ValueError('Auto assumptions require Ollama or explicit user assumptions')
            store.event(task_id,'ASSUMPTIONS','Requesting bounded unverified scenario from local model')
            terms=model_assumptions(ticker,evidence,model)
        check_assumptions(terms)
        assumptions=Assumptions(float(terms['discount_rate']),float(terms['terminal_growth']),tuple(float(x) for x in terms['growth_rates']))
        agent=OllamaAgent(model)
        store.event(task_id,'RESEARCH','Assessing data and assumptions')
        research='LLM skipped; source facts and assumptions retained.'
        if use_llm:
            research=agent.ask(RESEARCH_SYSTEM,json.dumps({'ticker':ticker,'facts':evidence,'assumptions':terms})[:16000])
        store.event(task_id,'VALUATION','Running deterministic discounted cash flow')
        result=dcf(float(evidence['fcf']),float(evidence['shares']),float(evidence['cash']),float(evidence['debt']),assumptions)
        store.event(task_id,'VERIFICATION','Checking valuation arithmetic and data constraints')
        if abs(result.equity_value-result.fair_value_per_share*float(evidence['shares']))>1e-7*max(1,abs(result.equity_value)):
            raise ValueError('Arithmetic verification failed')
        if abs(result.enterprise_value-result.explicit_pv-result.terminal_pv)>1e-7*max(1,abs(result.enterprise_value)):
            raise ValueError('PV verification failed')
        terminal_weight=abs(result.terminal_pv)/max(1,abs(result.enterprise_value))
        quality,gate_warnings=assess_evidence(evidence)
        warnings=list(gate_warnings)
        if terms.get('origin')=='UNVERIFIED_LLM_HYPOTHESIS': warnings.append('Growth and WACC are model-generated hypotheses, not validated forecasts')
        if terminal_weight > .8: warnings.append('Terminal value exceeds 80% of EV: high sensitivity')
        review='LLM review skipped.'
        if use_llm:
            review=agent.ask(REVIEW_SYSTEM,json.dumps({'evidence':evidence,'assumptions':terms,'valuation':asdict(result),'warnings':warnings})[:16000])
        report={'schema_version':3,'task_id':task_id,'ticker':ticker,'status':'COMPLETED_WITH_REVIEW','valuation':asdict(result),
                'assumptions':terms,'financial_data':evidence,'source_status':verified_source,
                'research':research,'review':review,'warnings':warnings,
                'human_review_required':True,'data_quality':quality,'valuation_method':'DCF','model':model if use_llm else None}
        store.event(task_id,'REPORTING','Saving sourced artifacts')
        out=folder/'valuation.json';out.write_text(json.dumps(report,indent=2,ensure_ascii=False))
        md=folder/'report.md'
        lines=[f'# {ticker}: FMV research draft', '',
               f"**Indicative DCF/share:** {result.fair_value_per_share:,.4f} USD", '',
               '**Status:** Analyst review required. Not investment advice.', '',
               f'**Data provenance:** {verified_source}', '',
               '## Warnings', *[f'- {x}' for x in warnings], '',
               '## Research',research,'','## Independent critique',review]
        md.write_text('\n'.join(lines)+'\n')
        for file in (out,md,folder/'financial_data.json'):
            store.add_artifact(task_id,str(file),hashlib.sha256(file.read_bytes()).hexdigest())
        store.event(task_id,'MONITORING','Comparing against prior completed tasks')
        prior=[x for x in store.tasks() if x['ticker']==ticker and x['id']!=task_id and x['status'].startswith('COMPLETED')]
        if prior:
            older=Path(artifacts)/prior[0]['id']/'valuation.json'
            if older.exists():
                old=json.loads(older.read_text()).get('valuation',{}).get('fair_value_per_share')
                new=result.fair_value_per_share
                if isinstance(old,(int,float)) and old != 0: store.event(task_id,'MONITORING',f'DCF change since prior run: {(new/old-1)*100:.2f}% (assumptions may differ)')
        store.update(task_id,'COMPLETED_WITH_REVIEW')
        store.event(task_id,'DONE','All six stages executed; human review needed')
        return report
    except Exception as exc:
        status='REVIEW_REQUIRED' if isinstance(exc,(MissingFinancialData,ValueError)) else 'FAILED'
        store.update(task_id,status,str(exc))
        store.event(task_id,status,str(exc)[:500])
        raise
