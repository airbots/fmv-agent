from fmv.data.sec_client import select_facts

def test_as_of_filter():
    data={'facts':{'us-gaap':{'Revenues':{'units':{'USD':[
      {'val':10,'end':'2025-12-31','filed':'2026-02-01','form':'10-K'},
      {'val':11,'end':'2025-12-31','filed':'2026-07-01','form':'10-K'}
    ]}}}}}
    assert len(select_facts(data,'us-gaap','Revenues',as_of='2026-03-01'))==1
