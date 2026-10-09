import pytest
from fmv.data.normalization import extract_financials, MissingFinancialData

def entry(val,end='2025-12-31',start=None,form='10-K',filed='2026-02-15'):
    return {'val':val,'end':end,'start':start,'form':form,'filed':filed,'accn':'0001'}

def test_fcf_extraction():
    f={'facts':{'us-gaap':{
      'NetCashProvidedByUsedInOperatingActivities':{'units':{'USD':[entry(150,start='2025-01-01')]}},
      'PaymentsToAcquirePropertyPlantAndEquipment':{'units':{'USD':[entry(50,start='2025-01-01')]}},
      'CashAndCashEquivalentsAtCarryingValue':{'units':{'USD':[entry(30)]}},
      'CommonStockSharesOutstanding':{'units':{'shares':[entry(10)]}},
      'LongTermDebtNoncurrent':{'units':{'USD':[entry(20)]}}
    }}}
    x=extract_financials(f)
    assert x['fcf']==100 and x['debt']==20 and x['shares']==10

def test_negative_fcf_requires_review():
    f={'facts':{'us-gaap':{
      'NetCashProvidedByUsedInOperatingActivities':{'units':{'USD':[entry(5,start='2025-01-01')]}},
      'PaymentsToAcquirePropertyPlantAndEquipment':{'units':{'USD':[entry(50,start='2025-01-01')]}},
      'CashAndCashEquivalentsAtCarryingValue':{'units':{'USD':[entry(30)]}},
      'CommonStockSharesOutstanding':{'units':{'shares':[entry(10)]}},
      'LongTermDebtNoncurrent':{'units':{'USD':[entry(20)]}}
    }}}
    with pytest.raises(MissingFinancialData):extract_financials(f)
