import base64
import math
import os
import numpy as np
import numpy_financial as npf
import pandas as pd
import streamlit as st
from sec_fetcher import SECValuationFetcher


# -----------------------------------------------------------------------------
# Helper: Base64 Image Loader for Streamlit Cloud Deployment
# -----------------------------------------------------------------------------
def get_image_base64(file_path: str) -> str:
  """Reads a local image file and converts it to base64 for HTML rendering."""
  if os.path.exists(file_path):
    with open(file_path, "rb") as f:
      return base64.b64encode(f.read()).decode()
  return ""


aurorain_icon_b64 = get_image_base64("Aurorain.png")
aurorain_logo_b64 = get_image_base64("Aurorain_icon.png")


# -----------------------------------------------------------------------------
# 0. Helper Mathematical Functions
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
# 1. Page Configuration & Top-Left Logo Styling
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Offline Financial Valuation Workbench",
    page_icon="Aurorain_icon.png"
    if os.path.exists("Aurorain_icon.png")
    else "📈",
    layout="wide",
)

# 1.1 Inject CSS for Floating Top-Left Icon (Aurorain_icon.png)
if aurorain_icon_b64:
  st.markdown(
      f"""
        <style>
        .top-left-logo {{
            position: fixed;
            top: 14px;
            left: 20px;
            z-index: 999999;
            height: 40px;
            width: auto;
            object-fit: contain;
        }}
        .block-container {{
            padding-top: 3.5rem !important;
        }}
        </style>
        <img src="data:image/png;base64,{aurorain_icon_b64}" class="top-left-logo" alt="Aurorain Icon">
        """,
      unsafe_allow_html=True,
  )

# 1.2 Main Page Header Title with Aurorain.png Logo
if aurorain_logo_b64:
  st.markdown(
      f"""
        <div style="display: flex; justify-content: center; align-items: center; gap: 16px; margin-top: 10px; margin-bottom: 10px;">
            <img src="data:image/png;base64,{aurorain_logo_b64}" style="height: 55px; width: auto; object-fit: contain;" alt="Aurorain Logo">
            <h1 style="margin: 0; font-size: 2.2rem; font-weight: 800; color: #0A1E4B;">
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
    " Deterministic Python Math Engine"
)

# Initialize Session States
if "sec_data" not in st.session_state:
  st.session_state["sec_data"] = None

if "dcf_results" not in st.session_state:
  st.session_state["dcf_results"] = None

# -----------------------------------------------------------------------------
# 2. Main Header: Ticker Search Input
# -----------------------------------------------------------------------------
st.markdown("---")
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
  st.write("")  # Vertical alignment padding
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
      st.session_state["sec_data"] = fetcher.fetch_valuation_data(
          ticker_input
      )
      st.session_state["dcf_results"] = None
      st.toast(
          f"✅ Successfully fetched SEC data for {ticker_input}!", icon="🎉"
      )
    except Exception as e:
      st.error(f"❌ Failed to fetch SEC data: {str(e)}")

# Display SEC Summary Metrics (Vertical View)
if st.session_state["sec_data"]:
  data = st.session_state["sec_data"]
  st.success(
      f"📌 Selected Target: **{data['Ticker']}** (CIK: {data['CIK']})"
  )

  st.markdown("##### **SEC Key Financial Metrics (Vertical View)**")
  st.metric(
      "Revenue (TTM)", f"${data['营业收入 (Revenue)'] / 1e6:,.2f} M"
  )
  st.metric(
      "Operating Cash Flow (OCF)",
      f"${data['经营活动现金流 (OCF)'] / 1e6:,.2f} M",
  )
  st.metric(
      "Cash & Equivalents",
      f"${data['现金及现金等价物 (Cash)'] / 1e6:,.2f} M",
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
# 3. Sidebar: Model Engine & Discounting Parameters
# -----------------------------------------------------------------------------
with st.sidebar:
  st.header("⚙️️ Engine & Valuation Settings")

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
# 4. Main Navigation Tabs (Each Asset Class in a Dedicated Tab)
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
    st.markdown("### 🎯 Final Valuation Results (Fair Market Value)")

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

    # Effective Conversion Cap Price vs Discount Price
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
  st.subheader("Upload Local PDF Financial Report / Pitchbook")
  uploaded_file = st.file_uploader("Drag and drop PDF file here", type=["pdf"])
  if uploaded_file:
    st.success(
        f"Loaded: {uploaded_file.name}. Ready for {selected_model} logic"
        " decomposition."
    )

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
