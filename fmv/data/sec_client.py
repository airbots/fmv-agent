"""SEC companyfacts client with cache provenance and point-in-time selection."""
import json
import os
import time
import gzip
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

class SECClient:
    def __init__(self, user_agent: str, cache_dir: str, pause_seconds: float = .3, ttl_seconds: int = 21600):
        if not user_agent or '@' not in user_agent:
            raise ValueError('Set SEC_USER_AGENT to a real name and contact email')
        self.user_agent = user_agent
        self.cache = Path(cache_dir)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.pause = pause_seconds
        self.ttl = ttl_seconds

    def _get(self, url, name):
        target = self.cache / name
        if target.exists() and time.time() - target.stat().st_mtime < self.ttl:
            return json.loads(target.read_text())
        req = urllib.request.Request(url, headers={
            'User-Agent': self.user_agent, 'Accept': 'application/json',
            'Accept-Encoding': 'gzip'})
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=30) as r:
                    raw = r.read()
                    if r.headers.get('Content-Encoding','').lower() == 'gzip':
                        raw = gzip.decompress(raw)
                result = json.loads(raw)
                target.write_text(json.dumps(result))
                time.sleep(self.pause)
                return result
            except Exception as e:
                if attempt == 2: raise
                time.sleep(2 ** attempt)

    def ticker_map(self):
        raw = self._get('https://www.sec.gov/files/company_tickers.json', 'company_tickers.json')
        return {x['ticker'].upper(): str(x['cik_str']).zfill(10) for x in raw.values()}

    def cik_for(self, ticker):
        cik = self.ticker_map().get(ticker.upper())
        if not cik: raise ValueError(f'Ticker {ticker} not found in SEC directory')
        return cik

    def companyfacts(self, cik):
        cik = str(int(cik)).zfill(10)
        return self._get(f'https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json',f'CIK{cik}.json')

def select_facts(companyfacts, taxonomy, tag, unit='USD', form=('10-K','10-Q'), as_of=None):
    rows = companyfacts.get('facts',{}).get(taxonomy,{}).get(tag,{}).get('units',{}).get(unit,[])
    found = []
    for row in rows:
        if row.get('form') not in form: continue
        if as_of and row.get('filed','9999') > as_of: continue
        if 'val' not in row or 'end' not in row: continue
        found.append({k:row.get(k) for k in ('val','start','end','filed','form','accn','fy','fp','frame')})
    return sorted(found,key=lambda r:(r.get('end') or '',r.get('filed') or ''))
