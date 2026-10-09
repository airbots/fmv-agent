import pytest
from fmv.core.valuation import Assumptions,dcf
from fmv.platform.store import Store
from fmv.platform.worker import process

def test_dcf_accounting():
    r=dcf(100,10,20,5,Assumptions(.1,.02,(.05,.05)))
    assert r.equity_value == pytest.approx(r.enterprise_value+15)
    assert r.fair_value_per_share == pytest.approx(r.equity_value/10)

def test_invalid_rates():
    with pytest.raises(ValueError): dcf(100,10,0,0,Assumptions(.02,.03,(.1,)))
    with pytest.raises(ValueError): dcf(100,0,0,0,Assumptions(.12,.03,(.1,)))

def test_db_queue_and_artifacts(tmp_path):
    db=Store(tmp_path/'state.db')
    payload={'ticker':'DEMO','fcf':100,'shares':10,'cash':5,'debt':2,'discount_rate':.12,'terminal_growth':.02,'growth_rates':[.05]}
    db.submit('demo','DEMO',payload)
    task=db.claim()
    assert task['id']=='demo'
    assert db.claim() is None
    r=process(db,task,tmp_path/'artifacts','unused',use_llm=False)
    assert r['status']=='COMPLETED'
    assert db.tasks()[0]['status']=='COMPLETED'
    assert (tmp_path/'artifacts/demo/valuation.json').exists()

def test_missing_input_fails(tmp_path):
    db=Store(tmp_path/'s.db')
    db.submit('bad','BAD',{'ticker':'BAD'})
    with pytest.raises(ValueError): process(db,db.claim(),tmp_path/'out','unused',use_llm=False)
    assert db.tasks()[0]['status']=='FAILED'
