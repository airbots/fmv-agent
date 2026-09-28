import requests
import pandas as pd

class SECValuationFetcher:
    """
    100% 免费、离线调用的 SEC EDGAR 数据抓取模块
    无需 API Key，仅需遵循 SEC 的 User-Agent 标头规范
    """
    def __init__(self, user_agent="LocalValuationBot admin@localapp.com"):
        # SEC 要求 Header 必须包含自定义 User-Agent (名称+邮箱格式)
        self.headers = {'User-Agent': user_agent}
        self._cik_map = None

    def _get_cik(self, ticker: str) -> str:
        """根据股票代码自动转换 SEC 的 10 位 CIK 编号"""
        ticker = ticker.upper()
        if not self._cik_map:
            url = "https://www.sec.gov/files/company_tickers.json"
            res = requests.get(url, headers=self.headers)
            if res.status_code == 200:
                data = res.json()
                self._cik_map = {
                    v['ticker']: str(v['cik_str']).zfill(10) 
                    for v in data.values()
                }
            else:
                raise ConnectionError("无法连接至 SEC 节点获取 CIK 列表。")
        
        cik = self._cik_map.get(ticker)
        if not cik:
            raise ValueError(f"未找到股票代码 {ticker} 对应的 SEC CIK 记录。")
        return cik

    def fetch_valuation_data(self, ticker: str) -> dict:
        """输入股票代码，自动抓取 SEC XBRL 最新财报核心估值指标"""
        cik = self._get_cik(ticker)
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
        
        res = requests.get(url, headers=self.headers)
        if res.status_code != 200:
            raise ConnectionError(f"SEC API 请求失败 (状态码: {res.status_code})")
        
        us_gaap = res.json().get('facts', {}).get('us-gaap', {})

        # 辅助函数：从 XBRL 节点中提取最新 10-K 年报数据
        def extract_latest(concept_list):
            for concept in concept_list:
                if concept in us_gaap:
                    units = us_gaap[concept]['units']
                    unit_key = list(units.keys())[0]
                    records = units[unit_key]
                    # 优先筛选 10-K 年报数据
                    k10_data = [r for r in records if r.get('form') == '10-K']
                    target_records = k10_data if k10_data else records
                    if target_records:
                        # 按财报截止日期排序提取最新值
                        latest = sorted(target_records, key=lambda x: x.get('end', ''))[-1]
                        return latest.get('val', 0)
            return 0

        # 抓取 DCF 估值必需的 5 项关键指标
        metrics = {
            "Ticker": ticker.upper(),
            "CIK": cik,
            "营业收入 (Revenue)": extract_latest(["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"]),
            "经营活动现金流 (OCF)": extract_latest(["NetCashProvidedByUsedInOperatingActivities"]),
            "现金及现金等价物 (Cash)": extract_latest(["CashAndCashEquivalentsAtCarryingValue"]),
            "长期债务 (Long-term Debt)": extract_latest(["LongTermDebtNoncurrent", "LongTermDebt"]),
            "普通股总股本 (Shares)": extract_latest(["EntityCommonStockSharesOutstanding", "WeightedAverageNumberOfSharesOutstandingBasic"])
        }
        
        return metrics

# -----------------------------------------------------------------------------
# 本地测试代码 (直接运行此脚本测试)
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    fetcher = SECValuationFetcher()
    ticker_to_test = "AMSC"
    print(f"🔍 正在从 SEC EDGAR 自动抓取 {ticker_to_test} 的公开估值数据...")
    data = fetcher.fetch_valuation_data(ticker_to_test)
    
    for k, v in data.items():
        if isinstance(v, (int, float)) and v > 1000:
            print(f"  • {k}: ${v:,.2f}")
        else:
            print(f"  • {k}: {v}")
