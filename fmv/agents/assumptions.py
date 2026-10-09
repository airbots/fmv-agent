"""Bounded model-assisted assumptions. Hypotheses, never verified market data."""
import json
import re
from fmv.agents.ollama import OllamaAgent

class AssumptionError(ValueError):
    pass

def model_assumptions(ticker, evidence, model='deepseek-r1:32b', agent=None):
    """Generate 5-year hypotheses; reject uncontrolled or invalid output.
    The resulting scenario is UNVERIFIED and MUST require human review.
    """
    agent=agent or OllamaAgent(model)
    request={'ticker':ticker,'annual_fcf':evidence['fcf'],'financial_period':evidence.get('financial_period'),
             'warnings':evidence.get('warnings',[]),'task':'Suggest scenario assumptions, not factual claims.'}
    text=agent.ask('You are a skeptical valuation scenario analyst. Output ONLY valid JSON with keys discount_rate (decimal), terminal_growth (decimal), growth_rates (array of 5 decimals), rationale (string). Do not claim external knowledge or SEC verification. If uncertain, use conservative scenario and explicitly state uncertainty.',json.dumps(request))
    text=re.sub(r'<think>.*?</think>','',text,flags=re.S).strip()
    candidate=re.search(r'\{.*\}',text,re.S)
    if candidate is None: raise AssumptionError('Model did not return parseable JSON; analyst review required')
    try: v=json.loads(candidate.group(0))
    except json.JSONDecodeError as exc: raise AssumptionError('Model returned malformed assumptions') from exc
    try:
        rate=float(v['discount_rate']); terminal=float(v['terminal_growth']); growth=[float(x) for x in v['growth_rates']]
        rationale=str(v['rationale']).strip()
    except (KeyError,TypeError,ValueError) as exc: raise AssumptionError('Missing or invalid model assumption') from exc
    if not (0.07 <= rate <= 0.25 and -0.02 <= terminal <= 0.04 and rate>terminal and len(growth)==5 and all(-0.4<=g<=0.4 for g in growth) and rationale):
        raise AssumptionError('Assumption outside configured bounds: analyst review required')
    return {'discount_rate':rate,'terminal_growth':terminal,'growth_rates':growth,'rationale':rationale,'origin':'UNVERIFIED_LLM_HYPOTHESIS'}
