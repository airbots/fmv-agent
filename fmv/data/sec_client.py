import json
import time
import urllib.request
from pathlib import Path

class SECClient:
    """Explicit User-Agent required by SEC; caller provides real contact."""
    def __init__(self, user_agent: str, cache_dir: str, pause_seconds: float = .25):
        if not user_agent or '@' not in user_agent:
            raise ValueError('Set SEC_USER_AGENT to an identifying name and contact email')
        self.user_agent=user_agent
        self.cache=Path(cache_dir)
        self.cache.mkdir(parents=True,exist_ok=True)
        self.pause=pause_seconds

    def companyfacts(self, cik: str):
        cik=str(int(cik)).zfill(10)
        target=self.cache/f'CIK{cik}.json'
        if target.exists(): return json.loads(target.read_text())
        req=urllib.request.Request(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json', headers={'User-Agent':self.user_agent,'Accept-Encoding':'gzip, deflate','Host':'data.sec.gov'})
        with urllib.request.urlopen(req,timeout=25) as response:
            payload=response.read()
            if response.headers.get('Content-Encoding') == 'gzip':
                import gzip
                payload=gzip.decompress(payload)
        obj=json.loads(payload)
        target.write_text(json.dumps(obj))
        time.sleep(self.pause)
        return obj

def select_facts(companyfacts, taxonomy, tag, unit='USD', form=('10-K','10-Q'), as_of=None):
    """Return sourced facts; do not silently select ambiguous fiscal periods."""
    metric=companyfacts.get('facts',{}).get(taxonomy,{}).get(tag,{})
    rows=metric.get('units',{}).get(unit,[])
    selected=[]
    for row in rows:
        if row.get('form') not in form: continue
        if as_of and row.get('filed','9999') > as_of: continue
        if 'val' not in row or 'end' not in row: continue
        selected.append({k:row.get(k) for k in ('val','start','end','filed','form','accn','fy','fp','frame')})
    return sorted(selected,key=lambda r:(r.get('end') or '',r.get('filed') or ''))
