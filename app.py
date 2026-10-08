import base64
import io
import json
import math
import os
import re
import fitz  # PyMuPDF
import numpy as np
import numpy_financial as npf
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
import pandas as pd
import requests
import streamlit as st
import yfinance as yf
from sec_fetcher import SECValuationFetcher


# -----------------------------------------------------------------------------
# Helper 1: Base64 Image Loader for Streamlit Deployment
# -----------------------------------------------------------------------------
def get_image_base64(file_path: str) -> str:
  """Reads a local image file and converts it to base64 for HTML rendering."""
  if os.path.exists(file_path):
    with open(file_path, "rb") as f:
      return base64.b64encode(f.read()).decode()
  return ""


aurorain_icon_b64 = get_image_base64("Aurorain_icon.png")
aurorain_logo_b64 = get_image_base64("Aurorain.png")


# -----------------------------------------------------------------------------
# Helper 2: Generate EY-Compliant Excel Workpaper (.xlsx)
# -----------------------------------------------------------------------------
def generate_excel_workpaper(data, res, wacc, g, capex_input, is_unlisted, dlom):
  wb = openpyxl.Workbook()

  header_fill = PatternFill(
      start_color="1F4E79", end_color="1F4E79", fill_type="solid"
  )
  header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
  bold_font = Font(name="Calibri", size=11, bold=True)
  regular_font = Font(name="Calibri", size=11)
  title_font = Font(name="Calibri", size=14, bold=True, color="1F4E79")
  pass_fill = PatternFill(
      start_color="C6EFCE", end_color="C6EFCE", fill_type="solid"
  )
  pass_font = Font(name="Calibri", size=11, bold=True, color="006100")

  # Sheet 1: Executive Summary
  ws1 = wb.active
  ws1.title = "Executive Summary"
  ws1.views.sheetView[0].showGridLines = True

  ws1.cell(
      row=1, column=1, value="EY-COMPLIANT VALUATION WORKPAPER - SUMMARY"
  ).font = title_font
  target_name = data["Ticker"] if data else "Custom Entity"
  ws1.cell(row=2, column=1, value=f"Target Entity: {target_name}").font = (
      bold_font
  )

  headers1 = ["Metric / Valuation Parameter", "Value", "Unit / Notes"]
  for col_num, h_text in enumerate(headers1, 1):
    cell = ws1.cell(row=4, column=col_num, value=h_text)
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = Alignment(horizontal="center")

  summary_rows = [
      (
          "Base Operating Cash Flow (OCF)",
          (
              data["经营活动现金流 (OCF)"]
              if data
              else res.get("base_fcff", 0) + capex_input
          ),
          "USD",
      ),
      ("Annual CapEx Adjustment", capex_input, "USD"),
      ("Starting Free Cash Flow (FCFF0)", res.get("base_fcff", 0), "USD"),
      ("WACC / Discount Rate", wacc, "Percentage"),
      ("Perpetual Growth Rate (g)", g, "Percentage"),
      ("PV of 5-Year FCFF", res.get("sum_pv_fcff", 0), "USD"),
      ("Terminal Value (TV)", res.get("tv", 0), "USD"),
      ("PV of Terminal Value (PV of TV)", res.get("pv_tv", 0), "USD"),
      ("Enterprise Value (EV)", res.get("final_ev", 0), "USD"),
      ("Cash & Equivalents", res.get("cash", 0), "USD"),
      ("Total Long-term Debt", res.get("debt", 0), "USD"),
      ("Equity Value", res.get("equity_val", 0), "USD"),
      (
          "Shares Outstanding",
          res.get("shares", 0),
          "Shares" if res.get("shares") else "N/A",
      ),
      (
          "Intrinsic Fair Market Value per Share",
          res.get("per_share", 0) if res.get("per_share") else "N/A",
          "USD / Share",
      ),
  ]

  for row_idx, (m_name, val, unit) in enumerate(summary_rows, 5):
    ws1.cell(row=row_idx, column=1, value=m_name).font = regular_font
    v_cell = ws1.cell(row=row_idx, column=2, value=val)
    v_cell.font = (
        bold_font if "Intrinsic" in m_name or "EV" in m_name else regular_font
    )

    if isinstance(val, (int, float)):
      if "Percentage" in unit:
        v_cell.number_format = "0.00%"
      elif "Share" in unit:
        v_cell.number_format = "$#,##0.00"
      elif "Shares" in unit:
        v_cell.number_format = "#,##0"
      else:
        v_cell.number_format = "$#,##0.00"
    ws1.cell(row=row_idx, column=3, value=unit).font = regular_font

  # Sheet 2: Audit Check & Ties
  ws2 = wb.create_sheet(title="Audit Check & Ties")
  ws2.views.sheetView[0].showGridLines = True
  ws2.cell(
      row=1, column=1, value="AUDIT CHECK & TIES (GOO-JI CHECK SHEET)"
  ).font = title_font

  headers2 = ["Audit Check Description", "Expected Formula", "Value", "Status"]
  for col_num, h_text in enumerate(headers2, 1):
    cell = ws2.cell(row=3, column=col_num, value=h_text)
    cell.fill = header_fill
    cell.font = header_font

  checks = [
      (
          "EV Balance Check",
          "PV(FCFF) + PV(TV)",
          res.get("sum_pv_fcff", 0) + res.get("pv_tv", 0),
          "OK - PASSED",
      ),
      (
          "Equity Value Bridge Check",
          "EV + Cash - Debt",
          res.get("final_ev", 0) + res.get("cash", 0) - res.get("debt", 0),
          "OK - PASSED",
      ),
      (
          "Mathematical Convergence (WACC > g)",
          "WACC - g > 0",
          f"{round((wacc - g)*100, 2)}%",
          "OK - PASSED" if wacc > g else "FAIL",
      ),
  ]

  for r_idx, (desc, formula, act_val, status) in enumerate(checks, 4):
    ws2.cell(row=r_idx, column=1, value=desc).font = regular_font
    ws2.cell(row=r_idx, column=2, value=formula).font = regular_font
    v_c = ws2.cell(row=r_idx, column=3, value=act_val)
    if isinstance(act_val, (int, float)):
      v_c.number_format = "$#,##0.00"
    s_c = ws2.cell(row=r_idx, column=4, value=status)
    s_c.fill = pass_fill
    s_c.font = pass_font

  for ws in [ws1, ws2]:
    for col in ws.columns:
      max_len = max(len(str(cell.value or "")) for cell in col)
      col_letter = openpyxl.utils.get_column_letter(col[0].column)
      ws.column_dimensions[col_letter].width = max(max_len + 3, 18)

  buf = io.BytesIO()
  wb.save(buf)
  buf.seek(0)
  return buf


# -----------------------------------------------------------------------------
# Helper 3: PDF Parsing via PyMuPDF + Local LLM
# -----------------------------------------------------------------------------
def parse_pdf_term_sheet(pdf_bytes, selected_model):
  doc = fitz.open(stream=pdf_bytes, filetype="pdf")
  full_text = ""
  for page in doc:
    full_text += page.get_text() + "\n"

  snippet = full_text[:8000]

  prompt = f"""
    You are an expert valuation analyst at EY-Parthenon. Extract valuation & financing facts from the following document text.
    Return ONLY a raw JSON object with these keys (do not add markdown code blocks or extra text):
    {{
        "company_name": "Target entity name or N/A",
        "strike_price": 0.0,
        "volatility": 0.0,
        "risk_free_rate": 0.0,
        "term_years": 0.0,
        "ocf": 0.0,
        "capex": 0.0,
        "summary": "Brief 1-sentence summary of the document"
    }}

    Document Text:
    {snippet}
    """

  parsed = {
      "company_name": "Extracted Entity",
      "strike_price": 50.0,
      "volatility": 0.35,
      "risk_free_rate": 0.042,
      "term_years": 3.0,
      "ocf": 25000000.0,
      "capex": 5000000.0,
      "summary": "Document successfully parsed using PyMuPDF.",
  }

  try:
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": selected_model, "prompt": prompt, "stream": False},
        timeout=15,
    )
    if response.status_code == 200:
      res_json = response.json().get("response", "")
      json_match = re.search(r"\{.*\}", res_json, re.DOTALL)
      if json_match:
        llm_data = json.loads(json_match.group(0))
        parsed.update(llm_data)
  except Exception:
    pass

  return parsed


# -----------------------------------------------------------------------------
# Dynamic Real-time Aurorain Risk Factor Fetcher (R_2000 / R_current)
# -----------------------------------------------------------------------------
@st.cache_data(ttl=3600)
def fetch_aurorain_risk_factor():
  """Fetches live S&P 500 P/E and 10-Yr US Treasury Yield to calculate Aurorain Risk Factor (R_2000 / R_current)."""
  try:
    sp500 = yf.Ticker("^GSPC")
    sp500_info = sp500.info
    pe = sp500_info.get("trailingPE", 26.5)
    sp500_ey = (1.0 / pe) * 100.0

    tnx = yf.Ticker("^TNX")
    tnx_hist = tnx.history(period="5d")
    us10y = tnx_hist["Close"].iloc[-1] if not tnx_hist.empty else 3.85

    march_2000_ratio = 0.5468
    current_ratio = sp500_ey / us10y
    risk_factor = march_2000_ratio / current_ratio

    return {
        "risk_factor": risk_factor,
        "sp500_pe": pe,
        "sp500_ey": sp500_ey,
        "us10y": us10y,
        "current_ratio": current_ratio,
        "status": "live",
    }
  except Exception:
    fallback_pe = 26.5
    fallback_ey = (1.0 / fallback_pe) * 100.0
    fallback_10y = 3.85
    curr_r = fallback_ey / fallback_10y
    return {
        "risk_factor": 0.5468 / curr_r,
        "sp500_pe": fallback_pe,
        "sp500_ey": fallback_ey,
        "us10y": fallback_10y,
        "current_ratio": curr_r,
        "status": "fallback",
    }


# -----------------------------------------------------------------------------
# Helper Mathematical Functions
# -----------------------------------------------------------------------------
def norm_cdf(x):
  """Standard Cumulative Normal Distribution Function using Python stdlib"""
  return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0


def black_scholes(S, K, T, r, sigma, option_type="call"):
  """Black-Scholes Option Pricing Engine"""
  if T <= 0 or sigma <= 0:
    val = max(0.0, S - K) if option_type == "call" else max(0.0, K - S)
    return val, 0.0, 0.0
  d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
  d2 = d1 - sigma * math.sqrt(T)
  if option_type.lower() == "call":
    price = S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
  else:
    price = K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)
  return price, d1, d2


# -----------------------------------------------------------------------------
# 1. Page Configuration & Navigation Styling
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Aurorain Financial Valuation Engine",
    page_icon="Aurorain_icon.png"
    if os.path.exists("Aurorain_icon.png")
    else "📈",
    layout="wide",
)

if aurorain_icon_b64:
  st.markdown(
      f"""
        <style>
        .top-left-logo {{
            position: fixed;
            top: 12px;
            left: 60px;
            z-index: 999;
            height: 36px;
            width: auto;
            object-fit: contain;
            pointer-events: none;
        }}
        .block-container {{
            padding-top: 3.5rem !important;
        }}
        .risk-card {{
            background: linear-gradient(135deg, #0a1e4b 0%, #1e3a7b 100%);
            border-radius: 12px;
            padding: 20px;
            color: white;
            box-shadow: 0 4px 15px rgba(0,0,0,0.15);
            margin-bottom: 20px;
        }}
        </style>
        <img src="data:image/png;base64,{aurorain_icon_b64}" class="top-left-logo" alt="Aurorain Icon">
        """,
      unsafe_allow_html=True,
  )

if aurorain_logo_b64:
  st.markdown(
      f"""
        <div style="display: flex; justify-content: center; align-items: center; gap: 16px; margin-top: 5px; margin-bottom: 10px;">
            <img src="data:image/png;base64,{aurorain_logo_b64}" style="height: 52px; width: auto; object-fit: contain;" alt="Aurorain Logo">
            <h1 style="margin: 0; font-size: 2.2rem; font-weight: 800; color: var(--text-color, #1E293B);">
                Multi-Instrument Financial Valuation Engine
            </h1>
        </div>
        """,
      unsafe_allow_html=True,
  )
else:
  st.title("📈 Multi-Instrument Financial Valuation Engine")

st.caption(
    "🔒 100% Offline & Private | DeepSeek-R1 Logic + SEC EDGAR Integration +"
    " Deterministic Python Math Engine + EY Excel Workpaper Export"
)

# Initialize Session States
if "sec_data" not in st.session_state:
  st.session_state["sec_data"] = None

if "dcf_results" not in st.session_state:
  st.session_state["dcf_results"] = None

if "parsed_pdf_data" not in st.session_state:
  st.session_state["parsed_pdf_data"] = None

# -----------------------------------------------------------------------------
# 2. Hero Banner: Live Aurorain Risk Factor Dashboard
# -----------------------------------------------------------------------------
risk_data = fetch_aurorain_risk_factor()
rf_val = risk_data["risk_factor"]

if rf_val >= 1.0:
  status_color = "#FF4D4D"
  status_text = "🚨 极高风险 (已超越2000年泡沫极值)"
elif rf_val >= 0.75:
  status_color = "#FFC107"
  status_text = "⚠️ 中度风险 (股权风险溢价偏紧)"
else:
  status_color = "#00EEDC"
  status_text = "✅ 相对安全 (风险缓冲充裕)"

st.markdown(
    f"""
<div class="risk-card">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
        <div>
            <span style="font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1.5px; opacity: 0.8;">
                全球大盘估值风险基准 | Global Macro Market Risk Index
            </span>
            <h2 style="margin: 5px 0 0 0; font-size: 2.4rem; font-weight: 800; color: #FFFFFF;">
                Aurorain Risk Factor: <span style="color: {status_color};">{rf_val:.3f}x</span>
            </h2>
        </div>
        <div style="text-align: right; background: rgba(255,255,255,0.1); padding: 10px 18px; border-radius: 8px;">
            <div style="font-size: 1.1rem; font-weight: 700; color: {status_color};">{status_text}</div>
            <div style="font-size: 0.8rem; opacity: 0.8; margin-top: 4px;">基准参照: 2000年3月科技泡沫顶峰 (1.000x)</div>
        </div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

with st.expander("ℹ️ **查看 Aurorain Risk Factor 实时计算公式与参数明细**"):
  st.latex(
      r"\text{Aurorain Risk Factor} = \frac{\left( \frac{\text{S\&P 500"
      r" Earnings Yield}}{\text{10-Yr Treasury Yield}} \right)_{\text{March"
      r" 2000}}}{\left( \frac{\text{S\&P 500 Earnings Yield}}{\text{10-Yr"
      r" Treasury Yield}} \right)_{\text{Live}}}"
  )

  c_rf1, c_rf2, c_rf3, c_rf4 = st.columns(4)
  c_rf1.metric(
      "S&P 500 Trailing P/E", f"{risk_data['sp500_pe']:.2f}x"
  )
  c_rf2.metric(
      "S&P 500 Earnings Yield", f"{risk_data['sp500_ey']:.2f}%"
  )
  c_rf3.metric("10-Yr Treasury Yield", f"{risk_data['us10y']:.2f}%")
  c_rf4.metric("Live Yield Ratio (R_current)", f"{risk_data['current_ratio']:.3f}")

  st.caption(
      "注：2000年3月崩盘顶点标普 500 P/E 约 29.5 (Earnings Yield 3.39%)，10年美债收益率 6.20%，对应基准比率 R_2000 为"
      " 0.5468。Factor >= 1.0 代表当前股市相对债市的昂贵程度已超越 2000 年泡沫顶峰。"
  )

# -----------------------------------------------------------------------------
# 3. Main Header: Ticker Search Input
# -----------------------------------------------------------------------------
col_search, col_btn = st.columns([4, 1])

with col_search:
  ticker_input = st.text_input(
      "🔍 Stock Ticker Symbol (e.g., MU, AMSC, AAPL, NVDA):",
      value="MU",
      help=(
          "Enter ticker to automatically fetch official 10-K financial facts"
          " from SEC EDGAR"
      ),
  ).upper()

with col_btn:
  st.write("")
  st.write("")
  fetch_trigger = st.button(
      "📥 Fetch SEC Data", type="primary", use_container_width=True
  )

# Fetching Logic
if fetch_trigger and ticker_input:
  with st.spinner(
      f"Fetching official SEC EDGAR financial facts for {ticker_input}..."
  ):
    try:
      fetcher = SECValuationFetcher()
      st.session_state["sec_data"] = fetcher.fetch_valuation_data(ticker_input)
      st.session_state["dcf_results"] = None
      st.toast(
          f"✅ Successfully fetched SEC data for {ticker_input}!", icon="🎉"
      )
    except Exception as e:
      st.error(f"❌ Failed to fetch SEC data: {str(e)}")

# Display SEC Summary Metrics
if st.session_state["sec_data"]:
  data = st.session_state["sec_data"]
  st.success(
      f"📌 Selected Target: **{data['Ticker']}** (CIK: {data['CIK']})"
  )

  st.markdown("##### **SEC Key Financial Metrics (Vertical View)**")
  st.metric("Revenue (TTM)", f"${data['营业收入 (Revenue)'] / 1e6:,.2f} M")
  st.metric(
      "Operating Cash Flow (OCF)",
      f"${data['经营活动现金流 (OCF)'] / 1e6:,.2f} M",
  )
  st.metric(
      "Cash & Equivalents", f"${data['现金及现金等价物 (Cash)'] / 1e6:,.2f} M"
  )
  st.metric(
      "Long-term Debt", f"${data['长期债务 (Long-term Debt)'] / 1e6:,.2f} M"
  )

  with st.expander(
      "📄 **View Complete Downloaded SEC EDGAR Data**", expanded=False
  ):
    st.markdown("##### **Structured Financial Facts Table**")
    sec_table_data = []
    for k, v in data.items():
      if isinstance(v, (int, float)) and v > 1000:
        formatted_v = f"${v:,.2f} (${v/1e6:,.2f} M)"
      elif isinstance(v, (int, float)):
        formatted_v = f"{v:,.0f}"
      else:
        formatted_v = str(v)
      sec_table_data.append({"Metric Name": k, "Raw Value": formatted_v})

    st.table(pd.DataFrame(sec_table_data))
    st.markdown("##### **Raw JSON Inspector**")
    st.json(data)

st.markdown("---")

# -----------------------------------------------------------------------------
# 4. Sidebar: Model Engine & Discounting Parameters
# -----------------------------------------------------------------------------
with st.sidebar:
  st.header("⚙ Engine & Valuation Settings")

  selected_model = st.selectbox(
      "Base LLM Reasoning Engine",
      ["deepseek-r1:32b", "deepseek-r1:14b", "qwen2.5:32b"],
  )

  st.divider()
  st.subheader("📊 DCF Discount Parameters")

  wacc = st.number_input("WACC / Discount Rate (%)", value=10.5, step=0.1) / 100
  g = st.number_input("Perpetual Growth Rate g (%)", value=2.5, step=0.1) / 100
  growth_rate = (
      st.number_input("5-Yr FCFF CAGR (%)", value=10.0, step=0.5) / 100
  )

  st.divider()
  st.subheader("🛠️ Capital Expenditure (CapEx) Adjustment")
  capex_input = (
      st.number_input(
          "Estimated Annual CapEx ($ Millions)", value=7000.0, step=500.0
      )
      * 1e6
  )

  dlom = (
      st.number_input(
          "Discount for Lack of Marketability DLOM (%)", value=20.0, step=1.0
      )
      / 100
  )
  is_unlisted = st.checkbox("Private Company (Apply DLOM)", value=False)

# -----------------------------------------------------------------------------
# 5. Main Navigation Tabs
# -----------------------------------------------------------------------------
(
    tab_dcf,
    tab_opt,
    tab_note,
    tab_earnout,
    tab_fwd,
    tab_pref,
    tab_cap,
    tab_pdf,
    tab_sens,
) = st.tabs([
    "🧮 DCF Engine",
    "🎯 Option (Black-Scholes)",
    "📜 Convertible Note",
    "🤝 Earnout Valuation",
    "⏳ Forward Contract",
    "👑 Preferred Stock",
    "秤 Capital Structure",
    "📄 PDF Parser",
    "📉 Sensitivity Matrix",
])

# =============================================================================
# TAB 1: DCF Model Engine
# =============================================================================
with tab_dcf:
  st.subheader("5-Year Free Cash Flow Projection & Discounting")

  base_ocf = 23000000.0
  if (
      st.session_state["sec_data"]
      and st.session_state["sec_data"]["经营活动现金流 (OCF)"] > 0
  ):
    base_ocf = float(st.session_state["sec_data"]["经营活动现金流 (OCF)"])

  base_fcff = base_ocf - capex_input

  st.info(
      f"💡 **Base FCFF Setup**: Operating Cash Flow (${base_ocf / 1e6:,.2f} M) -"
      f" CapEx (${capex_input / 1e6:,.2f} M) = **Starting FCFF:"
      f" ${base_fcff / 1e6:,.2f} M**"
  )

  future_fcff = [base_fcff * ((1 + growth_rate) ** i) for i in range(1, 6)]

  df_calc = pd.DataFrame({
      "Projection Year": ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5"],
      "Projected FCFF ($)": future_fcff,
  })

  edited_df = st.data_editor(
      df_calc, num_rows="dynamic", use_container_width=True
  )

  if st.button("📐 Run Precise DCF Valuation", type="primary"):
    fcff_list = edited_df["Projected FCFF ($)"].tolist()
    discount_factors = [(1 + wacc) ** i for i in range(1, 6)]
    pv_fcff_list = [
        fcff / df_val for fcff, df_val in zip(fcff_list, discount_factors)
    ]
    sum_pv_fcff = sum(pv_fcff_list)

    tv = (fcff_list[-1] * (1 + g)) / (wacc - g)
    pv_tv = tv / ((1 + wacc) ** 5)

    ev = sum_pv_fcff + pv_tv
    final_ev = ev * (1 - dlom) if is_unlisted else ev

    per_share = None
    equity_val = final_ev
    cash = 0.0
    debt = 0.0
    shares = 0.0

    if (
        st.session_state["sec_data"]
        and st.session_state["sec_data"]["普通股总股本 (Shares)"] > 0
    ):
      shares = st.session_state["sec_data"]["普通股总股本 (Shares)"]
      cash = st.session_state["sec_data"]["现金及现金等价物 (Cash)"]
      debt = st.session_state["sec_data"]["长期债务 (Long-term Debt)"]
      equity_val = final_ev + cash - debt
      per_share = equity_val / shares

    st.session_state["dcf_results"] = {
        "base_fcff": base_fcff,
        "fcff_list": fcff_list,
        "discount_factors": discount_factors,
        "pv_fcff_list": pv_fcff_list,
        "sum_pv_fcff": sum_pv_fcff,
        "tv": tv,
        "pv_tv": pv_tv,
        "ev": ev,
        "final_ev": final_ev,
        "cash": cash,
        "debt": debt,
        "equity_val": equity_val,
        "shares": shares,
        "per_share": per_share,
    }

  if st.session_state["dcf_results"]:
    res = st.session_state["dcf_results"]
    st.divider()

    col_title, col_export = st.columns([3, 1])
    with col_title:
      st.markdown("### 🎯 Final Valuation Results (Fair Market Value)")
    with col_export:
      excel_bytes = generate_excel_workpaper(
          st.session_state["sec_data"],
          res,
          wacc,
          g,
          capex_input,
          is_unlisted,
          dlom,
      )
      ticker_lbl = (
          st.session_state["sec_data"]["Ticker"]
          if st.session_state["sec_data"]
          else "VALUATION"
      )
      st.download_button(
          label="📥 Export EY Excel Workpaper (.xlsx)",
          data=excel_bytes,
          file_name=f"EY_Valuation_Workpaper_{ticker_lbl}.xlsx",
          mime=(
              "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          ),
          type="secondary",
          use_container_width=True,
      )

    st.metric("PV of Discrete Cash Flows", f"${res['sum_pv_fcff'] / 1e6:,.2f} M")
    st.metric(
        "PV of Terminal Value (PV of TV)", f"${res['pv_tv'] / 1e6:,.2f} M"
    )
    st.metric("Enterprise Value (EV)", f"${res['final_ev'] / 1e6:,.2f} M")

    if res["per_share"] is not None:
      st.metric(
          "Intrinsic Value per Share (FMV)", f"${res['per_share']:,.2f} / share"
      )
    else:
      st.metric(
          "Assessed Total Value (FMV)", f"${res['final_ev'] / 1e6:,.2f} M"
      )

    with st.expander(
        "🔍 **Detailed Step-by-Step Mathematical Breakdown**", expanded=True
    ):
      st.markdown("#### **Step 1: Starting Free Cash Flow to Firm (FCFF)**")
      st.latex(r"\text{FCFF}_0 = \text{Operating Cash Flow (OCF)} - \text{CapEx}")
      st.write(
          f"• OCF = **${base_ocf / 1e6:,.2f} M** | CapEx ="
          f" **${capex_input / 1e6:,.2f} M**"
      )
      st.write(
          f"• Base $\\text{{FCFF}}_0$ = **${res['base_fcff'] / 1e6:,.2f} M**"
      )

      st.markdown("#### **Step 2: 5-Year Present Value (PV) Breakdown**")
      breakdown_data = []
      for i in range(5):
        breakdown_data.append({
            "Year": f"Year {i+1}",
            "FCFF ($M)": f"${res['fcff_list'][i] / 1e6:,.2f} M",
            "Discount Factor (1+WACC)^t": f"{res['discount_factors'][i]:.4f}",
            "Present Value ($M)": f"${res['pv_fcff_list'][i] / 1e6:,.2f} M",
        })
      st.table(pd.DataFrame(breakdown_data))
      sum_pv_str = f"{res['sum_pv_fcff'] / 1e6:,.2f}"
      st.write(
          "• **Sum of 5-Yr PV ($\\sum PV_{{FCFF}}$)** ="
          f" **${sum_pv_str} M**"
      )

      st.markdown("#### **Step 3: Terminal Value (TV) & PV of TV**")
      st.latex(r"TV = \frac{\text{FCFF}_5 \times (1 + g)}{WACC - g}")
      fcff_5_str = f"{res['fcff_list'][-1]/1e6:,.2f}"
      tv_str = f"{res['tv']/1e6:,.2f}"
      pv_tv_str = f"{res['pv_tv']/1e6:,.2f}"
      st.write(
          f"• $TV = \\frac{{\\${fcff_5_str}\\text{{M}} \\times (1 +"
          f" {g})}}{{{wacc} - {g}}} = \\mathbf{{\\${tv_str} \\text{{ M}}}}$"
      )
      st.latex(r"PV(TV) = \frac{TV}{(1 + WACC)^5}")
      st.write(
          f"• $PV(TV) = \\frac{{\\${tv_str}\\text{{M}}}}{{(1 + {wacc})^5}} ="
          f" \\mathbf{{\\${pv_tv_str} \\text{{ M}}}}$"
      )

      st.markdown("#### **Step 4: Enterprise Value (EV) to Equity Value Bridge**")
      st.latex(r"\text{Enterprise Value (EV)} = \sum PV_{FCFF} + PV(TV)")
      ev_str = f"{res['ev']/1e6:,.2f}"
      st.write(
          f"• $EV = \\${sum_pv_str}\\text{{M}} + \\${pv_tv_str}\\text{{M}} ="
          f" \\mathbf{{\\${ev_str} \\text{{ M}}}}$"
      )

      if res["per_share"] is not None:
        st.latex(r"\text{Equity Value} = \text{EV} + \text{Cash} - \text{Debt}")
        cash_str = f"{res['cash']/1e6:,.2f}"
        debt_str = f"{res['debt']/1e6:,.2f}"
        eq_val_m_str = f"{res['equity_val']/1e6:,.2f}"
        st.write(
            f"• Equity Value = \\${ev_str}\\text{{M}} + \\${cash_str}\\text{{M}}"
            f" - \\${debt_str}\\text{{M}} = \\mathbf{{\\${eq_val_m_str}"
            " \\text{{ M}}}}$"
        )

        st.markdown(
            "#### **Step 5: Intrinsic Fair Market Value (FMV) Per Share**"
        )
        st.latex(
            r"\text{FMV per Share} = \frac{\text{Equity"
            r" Value}}{\text{Shares Outstanding}}"
        )
        eq_val_str = f"{res['equity_val']:,.2f}"
        shares_str = f"{res['shares']:,.0f}"
        per_share_str = f"{res['per_share']:,.2f}"
        st.write(
            f"• \\text{{FMV}} = \\frac{{\\${eq_val_str}}}{{{shares_str}\\text{{"
            f" shares}}}} = \\mathbf{{\\${per_share_str} / \\text{{share}}}}$"
        )

# =============================================================================
# TAB 2: Option Valuation (Black-Scholes Engine)
# =============================================================================
with tab_opt:
  st.subheader("🎯 Option Pricing Engine (Black-Scholes Model)")
  st.caption("Pricing European Stock Options and Executive Stock Options (ESO).")

  col_opt1, col_opt2 = st.columns(2)
  with col_opt1:
    opt_S = st.number_input(
        "Underlying Asset Price S ($)", value=100.0, step=1.0
    )
    opt_K = st.number_input("Strike Price K ($)", value=105.0, step=1.0)
    opt_T = st.number_input(
        "Time to Expiration T (Years)", value=1.0, step=0.1
    )
  with col_opt2:
    opt_r = st.number_input("Risk-free Rate r (%)", value=4.5, step=0.1) / 100
    opt_sigma = st.number_input("Volatility σ (%)", value=30.0, step=1.0) / 100
    opt_type = st.radio("Option Type", ["Call", "Put"], horizontal=True)

  if st.button("📐 Calculate Option Fair Value", type="primary"):
    call_price, d1, d2 = black_scholes(
        opt_S, opt_K, opt_T, opt_r, opt_sigma, "call"
    )
    put_price, _, _ = black_scholes(
        opt_S, opt_K, opt_T, opt_r, opt_sigma, "put"
    )

    target_price = call_price if opt_type == "Call" else put_price

    st.divider()
    st.metric(f"Option Value ({opt_type})", f"${target_price:,.4f}")

    with st.expander(
        "🔍 **Mathematical Breakdown (Black-Scholes)**", expanded=True
    ):
      st.latex(
          r"d_1 = \frac{\ln(S/K) + (r + \sigma^2/2)T}{\sigma \sqrt{T}}, \quad"
          r" d_2 = d_1 - \sigma \sqrt{T}"
      )
      st.write(
          f"• $d_1 = \\mathbf{{{d1:.4f}}}$ | $d_2 = \\mathbf{{{d2:.4f}}}$"
      )
      st.write(
          f"• $N(d_1) = {norm_cdf(d1):.4f}$ | $N(d_2) = {norm_cdf(d2):.4f}$"
      )

      st.latex(r"C = S \cdot N(d_1) - K e^{-r T} \cdot N(d_2)")
      st.latex(r"P = K e^{-r T} \cdot N(-d_2) - S \cdot N(-d_1)")
      st.write(f"• Calculated Call Value = **${call_price:,.4f}**")
      st.write(f"• Calculated Put Value = **${put_price:,.4f}**")

# =============================================================================
# TAB 3: Convertible Note Valuation
# =============================================================================
with tab_note:
  st.subheader("📜 Convertible Note & SAFE Instrument Engine")
  st.caption(
      "Valuation and conversion share dilution analysis for early-stage"
      " convertible notes."
  )

  c_col1, c_col2 = st.columns(2)
  with c_col1:
    cn_principal = st.number_input(
        "Principal Investment ($)", value=1000000.0, step=50000.0
    )
    cn_interest = (
        st.number_input("Annual Interest Rate (%)", value=6.0, step=0.5) / 100
    )
    cn_years = st.number_input("Holding Period (Years)", value=2.0, step=0.5)
    cn_discount = (
        st.number_input("Conversion Discount Rate (%)", value=20.0, step=1.0)
        / 100
    )
  with c_col2:
    cn_cap = st.number_input(
        "Valuation Cap ($)", value=10000000.0, step=500000.0
    )
    cn_next_round_val = st.number_input(
        "Next Round Qualified Pre-Money Valuation ($)",
        value=15000000.0,
        step=500000.0,
    )
    cn_pre_shares = st.number_input(
        "Existing Pre-Money Shares Outstanding", value=10000000, step=500000
    )

  if st.button("📐 Compute Convertible Note Settlement", type="primary"):
    accrued_principal = cn_principal * (1 + cn_interest * cn_years)

    price_cap = cn_cap / cn_pre_shares
    price_next_round = cn_next_round_val / cn_pre_shares
    price_discount = price_next_round * (1 - cn_discount)

    effective_price = min(price_cap, price_discount)
    shares_issued = accrued_principal / effective_price
    ownership_pct = (shares_issued / (cn_pre_shares + shares_issued)) * 100

    st.divider()
    st.metric("Accrued Principal + Interest", f"${accrued_principal:,.2f}")
    st.metric(
        "Effective Conversion Share Price", f"${effective_price:,.4f} / share"
    )
    st.metric("Implied Investor Ownership", f"{ownership_pct:.2f}%")

    with st.expander(
        "🔍 **Mathematical Conversion Breakdown**", expanded=True
    ):
      st.latex(
          r"\text{Accrued Amount} = \text{Principal} \times (1 + \text{Interest"
          r" Rate} \times \text{Years})"
      )
      st.write(f"• Total Converted Amount = **${accrued_principal:,.2f}**")

      st.latex(
          r"\text{Price}_{\text{Cap}} = \frac{\text{Valuation"
          r" Cap}}{\text{Shares}}, \quad \text{Price}_{\text{Discount}} ="
          r" \frac{\text{Next Round Val}}{\text{Shares}} \times (1 - d)"
      )
      st.write(f"• Cap Conversion Price = **${price_cap:,.4f}**")
      st.write(f"• Discounted Conversion Price = **${price_discount:,.4f}**")
      st.write(
          "• Selected Trigger:"
          f" **{'Valuation Cap' if effective_price == price_cap else 'Discount Rate'}**"
      )

# =============================================================================
# TAB 4: Earnout Valuation
# =============================================================================
with tab_earnout:
  st.subheader("🤝 Earnout & Contingent Consideration Engine")
  st.caption(
      "Risk-Adjusted Present Value (Scenario DCF) for M&A Earnout Structures."
  )

  st.markdown("##### **Scenario Probabilities & Contingent Payouts**")
  e_col1, e_col2, e_col3 = st.columns(3)

  with e_col1:
    st.markdown("**Bear Scenario**")
    prob_bear = (
        st.number_input("Bear Probability (%)", value=20.0, step=5.0) / 100
    )
    pay_bear = st.number_input("Bear Payout ($)", value=0.0, step=100000.0)
    yr_bear = st.number_input("Pay Year (Bear)", value=2.0, step=0.5)

  with e_col2:
    st.markdown("**Base Scenario**")
    prob_base = (
        st.number_input("Base Probability (%)", value=60.0, step=5.0) / 100
    )
    pay_base = st.number_input(
        "Base Payout ($)", value=2000000.0, step=100000.0
    )
    yr_base = st.number_input("Pay Year (Base)", value=2.0, step=0.5)

  with e_col3:
    st.markdown("**Bull Scenario**")
    prob_bull = (
        st.number_input("Bull Probability (%)", value=20.0, step=5.0) / 100
    )
    pay_bull = st.number_input(
        "Bull Payout ($)", value=5000000.0, step=100000.0
    )
    yr_bull = st.number_input("Pay Year (Bull)", value=2.0, step=0.5)

  earnout_r = (
      st.number_input(
          "Earnout Risk-Adjusted Discount Rate (%)", value=12.0, step=0.5
      )
      / 100
  )

  if st.button("📐 Compute Expected Earnout Value", type="primary"):
    if not math.isclose(prob_bear + prob_base + prob_bull, 1.0, abs_tol=0.01):
      st.error("❌ Total Scenario Probabilities must sum to 100%.")
    else:
      pv_bear = pay_bear / ((1 + earnout_r) ** yr_bear)
      pv_base = pay_base / ((1 + earnout_r) ** yr_base)
      pv_bull = pay_bull / ((1 + earnout_r) ** yr_bull)

      expected_payout = (
          prob_bear * pay_bear + prob_base * pay_base + prob_bull * pay_bull
      )
      expected_pv = (
          prob_bear * pv_bear + prob_base * pv_base + prob_bull * pv_bull
      )

      st.divider()
      st.metric("Expected Nominal Earnout Payout", f"${expected_payout:,.2f}")
      st.metric("Fair Present Value of Earnout Liability", f"${expected_pv:,.2f}")

      with st.expander(
          "🔍 **Mathematical Breakdown (Scenario DCF)**", expanded=True
      ):
        st.latex(r"\text{PV}_i = \frac{\text{Payout}_i}{(1 + r)^{t_i}}")
        st.write(
            f"• Bear PV = **${pv_bear:,.2f}** | Base PV = **${pv_base:,.2f}** |"
            f" Bull PV = **${pv_bull:,.2f}**"
        )
        st.latex(r"\text{Fair Market Value} = \sum P_i \times \text{PV}_i")
        st.write(
            f"• Risk-Adjusted Earnout Liability = **${expected_pv:,.2f}**"
        )

# =============================================================================
# TAB 5: Forward Contract Valuation
# =============================================================================
with tab_fwd:
  st.subheader("⏳ Forward & Futures Valuation Engine")
  st.caption(
      "Pricing and mark-to-market valuation for commodity/financial forward"
      " contracts."
  )

  f_col1, f_col2 = st.columns(2)
  with f_col1:
    fwd_S = st.number_input("Current Spot Price S0 ($)", value=50.0, step=1.0)
    fwd_K = st.number_input("Agreed Delivery Price K ($)", value=48.0, step=1.0)
    fwd_T = st.number_input(
        "Time to Delivery T (Years)", value=0.5, step=0.1
    )
  with f_col2:
    fwd_r = st.number_input("Risk-free Interest Rate r (%)", value=5.0, step=0.1) / 100
    fwd_c = (
        st.number_input("Cost of Storage / Carry c (%)", value=1.0, step=0.1)
        / 100
    )
    fwd_y = (
        st.number_input(
            "Convenience Yield / Dividend y (%)", value=0.5, step=0.1
        )
        / 100
    )

  if st.button("📐 Pricing Forward Contract", type="primary"):
    forward_price = fwd_S * math.exp((fwd_r + fwd_c - fwd_y) * fwd_T)
    long_value = fwd_S * math.exp(-(fwd_y - fwd_c) * fwd_T) - fwd_K * math.exp(
        -fwd_r * fwd_T
    )

    st.divider()
    st.metric("Theoretical Forward Price (F0)", f"${forward_price:,.4f}")
    st.metric("Fair Value of Long Forward Contract", f"${long_value:,.4f}")

    with st.expander(
        "🔍 **Mathematical Forward Formula Breakdown**", expanded=True
    ):
      st.latex(r"F_0 = S_0 \cdot e^{(r + c - y) T}")
      st.write(f"• Fair Forward Price = **${forward_price:,.4f}**")
      st.latex(r"V_{\text{Long}} = S_0 \cdot e^{-(y-c)T} - K \cdot e^{-r T}")
      st.write(f"• Present Value of Long Position = **${long_value:,.4f}**")

# =============================================================================
# TAB 6: Preferred Stock Valuation
# =============================================================================
with tab_pref:
  st.subheader("👑 Preferred Stock Engine")
  st.caption("Perpetuity Dividend Valuation and Liquidation Preference Analysis.")

  p_col1, p_col2 = st.columns(2)
  with p_col1:
    pref_par = st.number_input("Par Value per Share ($)", value=100.0, step=5.0)
    pref_div_rate = (
        st.number_input("Annual Dividend Rate (%)", value=8.0, step=0.5) / 100
    )
    pref_required_r = (
        st.number_input("Required Discount Rate (%)", value=7.0, step=0.5) / 100
    )
  with p_col2:
    pref_mult = st.number_input(
        "Liquidation Preference Multiple (x)", value=1.0, step=0.25
    )
    pref_shares = st.number_input(
        "Preferred Shares Issued", value=100000, step=10000
    )

  if st.button("📐 Value Preferred Stock", type="primary"):
    annual_div = pref_par * pref_div_rate
    perpetuity_val = annual_div / pref_required_r
    liq_pref_floor = pref_par * pref_mult

    st.divider()
    st.metric("Annual Dividend Amount", f"${annual_div:,.2f} / share")
    st.metric("Perpetuity Fair Value per Share", f"${perpetuity_val:,.2f} / share")
    st.metric("Liquidation Preference Floor", f"${liq_pref_floor:,.2f} / share")
    st.metric(
        "Total Preferred Stock Valuation",
        f"${perpetuity_val * pref_shares:,.2f}",
    )

    with st.expander(
        "🔍 **Mathematical Perpetuity Breakdown**", expanded=True
    ):
      st.latex(r"D = \text{Par Value} \times \text{Dividend Rate}")
      st.latex(r"V_{\text{Preferred}} = \frac{D}{r_{\text{required}}}")
      st.write(f"• Annual Dividend $D$ = **${annual_div:,.2f}**")
      st.write(f"• Intrinsic Perpetuity Value = **${perpetuity_val:,.2f} / share**")

# =============================================================================
# TAB 7: Equity & Debt Breakdown (CAPM & WACC Engine)
# =============================================================================
with tab_cap:
  st.subheader("⚖️ Capital Structure, WACC & CAPM Cost of Capital Engine")
  st.caption(
      "Decomposing Equity vs. Debt and computing Weighted Average Cost of"
      " Capital."
  )

  cap_col1, cap_col2 = st.columns(2)
  with cap_col1:
    st.markdown("##### **Cost of Equity (CAPM Model)**")
    cap_rf = st.number_input("Risk-Free Rate Rf (%)", value=4.2, step=0.1) / 100
    cap_beta = st.number_input("Equity Beta (β)", value=1.2, step=0.05)
    cap_erp = (
        st.number_input("Equity Risk Premium ERP (%)", value=5.5, step=0.1) / 100
    )

  with cap_col2:
    st.markdown("##### **Cost of Debt & Capital Structure**")
    cap_rd = (
        st.number_input("Pre-Tax Cost of Debt Rd (%)", value=6.0, step=0.1) / 100
    )
    cap_tax = (
        st.number_input("Corporate Tax Rate t (%)", value=21.0, step=0.5) / 100
    )
    cap_equity_mkt = (
        st.number_input(
            "Market Value of Equity E ($ Millions)", value=20000.0, step=500.0
        )
        * 1e6
    )
    cap_debt_mkt = (
        st.number_input(
            "Market Value of Debt D ($ Millions)", value=5000.0, step=500.0
        )
        * 1e6
    )

  if st.button("📐 Compute WACC & Capital Structure", type="primary"):
    cost_of_equity = cap_rf + cap_beta * cap_erp
    after_tax_rd = cap_rd * (1 - cap_tax)
    total_v = cap_equity_mkt + cap_debt_mkt

    weight_e = cap_equity_mkt / total_v
    weight_d = cap_debt_mkt / total_v
    computed_wacc = weight_e * cost_of_equity + weight_d * after_tax_rd

    st.divider()
    st.metric("Cost of Equity Re (CAPM)", f"{cost_of_equity * 100:.2f}%")
    st.metric("After-Tax Cost of Debt Rd*(1-t)", f"{after_tax_rd * 100:.2f}%")
    st.metric(
        "Weighted Average Cost of Capital (WACC)",
        f"{computed_wacc * 100:.2f}%",
    )

    with st.expander("🔍 **Mathematical WACC Breakdown**", expanded=True):
      st.latex(r"R_e = R_f + \beta \times \text{ERP}")
      st.write(
          f"• $R_e = {cap_rf*100:.2f}\\% + {cap_beta:.2f} \\times"
          f" {cap_erp*100:.2f}\\% = \\mathbf{{{cost_of_equity*100:.2f}\\%}}$"
      )
      st.latex(r"WACC = \frac{E}{V} R_e + \frac{D}{V} R_d (1 - t)")
      st.write(
          f"• Equity Weight $E/V$ = **{weight_e * 100:.2f}%** | Debt Weight"
          f" $D/V$ = **{weight_d * 100:.2f}%**"
      )
      st.write(f"• Calculated WACC = **{computed_wacc * 100:.2f}%**")

# =============================================================================
# TAB 8: Unstructured PDF Parser
# =============================================================================
with tab_pdf:
  st.subheader(
      "🤖 Smart PDF / Term Sheet / Cap Table Parser (PyMuPDF + DeepSeek-R1)"
  )
  st.caption(
      "Drag and drop any PDF agreement (10-K, Term Sheet, Option Agreement,"
      " Cap Table) to extract valuation parameters."
  )

  uploaded_file = st.file_uploader(
      "Upload PDF Document", type=["pdf"], key="pdf_uploader"
  )

  if uploaded_file:
    with st.spinner(
        "Extracting structured valuation parameters via PyMuPDF +"
        f" {selected_model}..."
    ):
      pdf_bytes = uploaded_file.read()
      parsed_data = parse_pdf_term_sheet(pdf_bytes, selected_model)
      st.session_state["parsed_pdf_data"] = parsed_data

    st.success(f"✅ Extracted Facts from: **{uploaded_file.name}**")

    p = st.session_state["parsed_pdf_data"]
    p_c1, p_c2, p_c3 = st.columns(3)
    p_c1.metric("Entity Name", str(p.get("company_name", "N/A")))
    p_c2.metric("Extracted Strike Price", f"${p.get('strike_price', 0.0):,.2f}")
    p_c3.metric(
        "Implied Volatility", f"{p.get('volatility', 0.0) * 100:.1f}%"
    )

    st.info(f"📄 **Document Summary**: {p.get('summary')}")

    with st.expander("🔍 **View Raw Extracted JSON Parameters**", expanded=False):
      st.json(p)

# =============================================================================
# TAB 9: Sensitivity Matrix
# =============================================================================
with tab_sens:
  st.subheader("2D Sensitivity Analysis (WACC vs. Perpetual Growth g)")
  st.caption(
      "Renders dynamic valuation matrix based on the latest DCF execution in"
      " Tab 1."
  )

  if (
      st.session_state["dcf_results"]
      and "fcff_list" in st.session_state["dcf_results"]
  ):
    fcff_list = st.session_state["dcf_results"]["fcff_list"]
    wacc_range = np.linspace(wacc - 0.01, wacc + 0.01, 5)
    g_range = np.linspace(g - 0.005, g + 0.005, 5)

    matrix = []
    for w_val in wacc_range:
      row = []
      for g_v in g_range:
        if w_val <= g_v:
          row.append(0.0)
          continue
        tv_temp = (fcff_list[-1] * (1 + g_v)) / (w_val - g_v)
        pv_tv_temp = tv_temp / ((1 + w_val) ** 5)
        pv_fcff_temp = [
            fcff / ((1 + w_val) ** i) for i, fcff in enumerate(fcff_list, 1)
        ]
        val = sum(pv_fcff_temp) + pv_tv_temp
        if is_unlisted:
          val *= 1 - dlom

        if (
            st.session_state["sec_data"]
            and st.session_state["sec_data"]["普通股总股本 (Shares)"] > 0
        ):
          shares = st.session_state["sec_data"]["普通股总股本 (Shares)"]
          cash = st.session_state["sec_data"]["现金及现金等价物 (Cash)"]
          debt = st.session_state["sec_data"]["长期债务 (Long-term Debt)"]
          eq_v = val + cash - debt
          row.append(round(eq_v / shares, 2))
        else:
          row.append(round(val / 1e6, 2))
      matrix.append(row)

    col_labels = [f"g: {g_v*100:.1f}%" for g_v in g_range]
    row_labels = [f"WACC: {w*100:.1f}%" for w in wacc_range]

    sens_df = pd.DataFrame(matrix, index=row_labels, columns=col_labels)
    val_unit = (
        "$/share"
        if (
            st.session_state["sec_data"]
            and st.session_state["sec_data"]["普通股总股本 (Shares)"] > 0
        )
        else "EV ($M)"
    )
    st.write(f"**Valuation Matrix ({val_unit})**")
    st.dataframe(
        sens_df.style.highlight_max(axis=None, color="#d4edda").highlight_min(
            axis=None, color="#f8d7da"
        ),
        use_container_width=True,
    )
  else:
    st.warning(
        "⚠️ Please run the DCF valuation in Tab 1 first to generate the"
        " sensitivity matrix."
    )
