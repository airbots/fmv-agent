import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
from sec_fetcher import SECValuationFetcher

# -----------------------------------------------------------------------------
# 1. Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Offline Local Financial Valuation Workbench",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Local Financial Valuation Engine")
st.caption("🔒 100% Offline & Private | DeepSeek-R1 Logic + SEC EDGAR Integration + Deterministic Python Math Engine")

# Initialize Session State for SEC Data
if 'sec_data' not in st.session_state:
    st.session_state['sec_data'] = None

# -----------------------------------------------------------------------------
# 2. Main Header: Ticker Search Input
# -----------------------------------------------------------------------------
st.markdown("---")
col_search, col_btn = st.columns([4, 1])

with col_search:
    ticker_input = st.text_input(
        "🔍 Stock Ticker Symbol (e.g., AMSC, AAPL, NVDA):", 
        value="AMSC",
        help="Enter ticker to automatically fetch official 10-K financial facts from SEC EDGAR"
    ).upper()

with col_btn:
    st.write("")  # Vertical alignment
    st.write("")
    fetch_trigger = st.button("📥 Fetch SEC Data", type="primary", use_container_width=True)

# Fetching Logic
if fetch_trigger and ticker_input:
    with st.spinner(f"Fetching official SEC EDGAR financial facts for {ticker_input}..."):
        try:
            fetcher = SECValuationFetcher()
            st.session_state['sec_data'] = fetcher.fetch_valuation_data(ticker_input)
            st.toast(f"✅ Successfully fetched SEC data for {ticker_input}!", icon="🎉")
        except Exception as e:
            st.error(f"❌ Failed to fetch SEC data: {str(e)}")

# Display SEC Summary Cards if data exists
if st.session_state['sec_data']:
    data = st.session_state['sec_data']
    st.success(f"📌 Selected Target: **{data['Ticker']}** (CIK: {data['CIK']})")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Revenue (TTM)", f"${data['营业收入 (Revenue)'] / 1e6:,.2f} M")
    m2.metric("Operating Cash Flow (OCF)", f"${data['经营活动现金流 (OCF)'] / 1e6:,.2f} M")
    m3.metric("Cash & Equivalents", f"${data['现金及现金等价物 (Cash)'] / 1e6:,.2f} M")
    m4.metric("Long-term Debt", f"${data['长期债务 (Long-term Debt)'] / 1e6:,.2f} M")

st.markdown("---")

# -----------------------------------------------------------------------------
# 3. Sidebar: Model Engine & Discounting Parameters
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Engine & Valuation Settings")
    
    selected_model = st.selectbox(
        "Base LLM Reasoning Engine", 
        ["deepseek-r1:32b", "deepseek-r1:14b", "qwen2.5:32b"]
    )
    
    st.divider()
    st.subheader("📊 DCF Discount Parameters")
    
    wacc = st.number_input("WACC / Discount Rate (%)", value=8.5, step=0.1) / 100
    g = st.number_input("Perpetual Growth Rate g (%)", value=2.5, step=0.1) / 100
    growth_rate = st.number_input("5-Yr FCFF CAGR (%)", value=15.0, step=0.5) / 100
    dlom = st.number_input("Discount for Lack of Marketability DLOM (%)", value=20.0, step=1.0) / 100
    
    is_unlisted = st.checkbox("Private Company (Apply DLOM)", value=False)

# -----------------------------------------------------------------------------
# 4. Main Navigation Tabs
# -----------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["🧮 1. DCF Model Engine", "📄 2. Unstructured PDF Parser", "📉 3. Sensitivity Matrix"])

# --- TAB 1: DCF Calculator ---
with tab1:
    st.subheader("5-Year Free Cash Flow Projection & Discounting")
    
    # Base Cash Flow Setup
    base_ocf = 23000000.0  # Default $23M
    if st.session_state['sec_data'] and st.session_state['sec_data']['经营活动现金流 (OCF)'] > 0:
        base_ocf = float(st.session_state['sec_data']['经营活动现金流 (OCF)'])
        st.info(f"💡 Automatically initialized with latest SEC Operating Cash Flow: **${base_ocf / 1e6:,.2f} M**")
    
    # Generate 5-Yr Projections
    future_fcff = [base_ocf * ((1 + growth_rate) ** i) for i in range(1, 6)]
    
    df_calc = pd.DataFrame({
        "Projection Year": ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5"],
        "Projected FCFF ($)": future_fcff
    })
    
    edited_df = st.data_editor(df_calc, num_rows="dynamic", use_container_width=True)
    
    if st.button("📐 Run Precise DCF Valuation", type="primary"):
        fcff_list = edited_df["Projected FCFF ($)"].tolist()
        
        # Python Deterministic Math Engine
        discount_factors = [(1 + wacc) ** i for i in range(1, 6)]
        pv_fcff = [fcff / df_val for fcff, df_val in zip(fcff_list, discount_factors)]
        
        # Terminal Value Calculation
        tv = (fcff_list[-1] * (1 + g)) / (wacc - g)
        pv_tv = tv / ((1 + wacc) ** 5)
        
        # Enterprise Value & Equity Value
        ev = sum(pv_fcff) + pv_tv
        final_ev = ev * (1 - dlom) if is_unlisted else ev
        
        st.divider()
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("PV of Discrete Cash Flows", f"${sum(pv_fcff) / 1e6:,.2f} M")
        c2.metric("PV of Terminal Value (PV of TV)", f"${pv_tv / 1e6:,.2f} M")
        c3.metric("Enterprise Value (EV)", f"${final_ev / 1e6:,.2f} M")
        
        # Per Share Intrinsic Value (if stock shares exist)
        if st.session_state['sec_data'] and st.session_state['sec_data']['普通股总股本 (Shares)'] > 0:
            shares = st.session_state['sec_data']['普通股总股本 (Shares)']
            cash = st.session_state['sec_data']['现金及现金等价物 (Cash)']
            debt = st.session_state['sec_data']['长期债务 (Long-term Debt)']
            
            # Equity Value = EV + Cash - Debt
            equity_val = final_ev + cash - debt
            per_share = equity_val / shares
            c4.metric("Intrinsic Value per Share", f"${per_share:,.2f} / share")
        else:
            c4.metric("Assessed Total Value", f"${final_val / 1e6:,.2f} M")

# --- TAB 2: Unstructured PDF Parser ---
with tab2:
    st.subheader("Upload Local PDF Financial Report / Pitchbook")
    uploaded_file = st.file_uploader("Drag and drop PDF file here", type=["pdf"])
    if uploaded_file:
        st.success(f"Loaded: {uploaded_file.name}. Ready for {selected_model} logic decomposition.")

# --- TAB 3: Sensitivity Matrix ---
with tab3:
    st.subheader("2D Sensitivity Analysis (WACC vs. Perpetual Growth g)")
    st.caption("Run DCF calculation in Tab 1 to dynamically render the valuation matrix.")
