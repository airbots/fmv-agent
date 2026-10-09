import pytest
from fmv.agents.assumptions import model_assumptions,AssumptionError
from fmv.platform.guardrails import check_assumptions,assess_evidence

class Dummy:
    def __init__(self,answer):self.answer=answer
    def ask(self,*args):return self.answer

def test_valid_ai_scenario():
    import json
    text=json.dumps({'discount_rate':.12,'terminal_growth':.025,'growth_rates':[.1,.08,.07,.06,.05],'rationale':'Illustrative only'})
    a=model_assumptions('MU',{'fcf':100,'sources':{}},agent=Dummy(text))
    assert a['origin']=='UNVERIFIED_LLM_HYPOTHESIS'
    assert check_assumptions(a)

def test_invalid_ai_scenario_rejected():
    import json
    text=json.dumps({'discount_rate':.06,'terminal_growth':.07,'growth_rates':[.8]*5,'rationale':'Excessive'})
    with pytest.raises(AssumptionError):model_assumptions('MU',{'fcf':100},agent=Dummy(text))

def test_ai_thinking_tags_removed():
    text='<think>work</think> {"discount_rate":0.12,"terminal_growth":0.02,"growth_rates":[0.1,0.1,0.1,0.1,0.1],"rationale":"uncertain"}'
    assert model_assumptions('MU',{'fcf':100},agent=Dummy(text))['discount_rate']==.12

def test_unproven_financials_never_marked_verified():
    assert assess_evidence({'fcf':10,'shares':2,'sources':{}})[0]=='UNVERIFIED'
    assert assess_evidence({'fcf':10,'shares':2,'sources':{'x':'sec'}})[0]=='NEEDS_ANALYST_REVIEW'
