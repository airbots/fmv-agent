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

# Initialize Session States
if 'sec_data' not in st.session_state:
    st.session_state['sec_data'] = None

if 'dcf_results' not in st.session_state:
    st.session_state['dcf_results'] = None

# -----------------------------------------------------------------------------
# 2. Main Header: Ticker Search Input
# -----------------------------------------------------------------------------
st.markdown("---")
col_search, col_btn = st.columns([4, 1])

with col_search:
    ticker_input = st.text_input(
        "🔍 Stock Ticker Symbol (e.g., MU, AMSC, AAPL, NVDA):", 
        value="MU",
        help="Enter ticker to automatically fetch official 10-K financial facts from SEC EDGAR"
    ).upper()

with col_btn:
    st.write("")  # Vertical alignment padding
    st.write("")
    fetch_trigger = st.button("📥 Fetch SEC Data", type="primary", use_container_width=True)

# Fetching Logic
if fetch_trigger and ticker_input:
    with st.spinner(f"Fetching official SEC EDGAR financial facts for {ticker_input}..."):
        try:
            fetcher = SECValuationFetcher()
            st.session_state['sec_data'] = fetcher.fetch_valuation_data(ticker_input)
            st.session_state['dcf_results'] = None
            st.toast(f"✅ Successfully fetched SEC data for {ticker_input}!", icon="🎉")
        except Exception as e:
            st.error(f"❌ Failed to fetch SEC data: {str(e)}")

# Display SEC Summary Cards (Vertical Stacking)
if st.session_state['sec_data']:
    data = st.session_state['sec_data']
    st.success(f"📌 Selected Target: **{data['Ticker']}** (CIK: {data['CIK']})")
    
    # 🌟 竖向排列：SEC 基础财务指标
    st.markdown("##### **SEC Key Financial Metrics (Vertical View)**")
    st.metric("Revenue (TTM)", f"${data['营业收入 (Revenue)'] / 1e6:,.2f} M")
    st.metric("Operating Cash Flow (OCF)", f"${data['经营活动现金流 (OCF)'] / 1e6:,.2f} M")
    st.metric("Cash & Equivalents", f"${data['现金及现金等价物 (Cash)'] / 1e6:,.2f} M")
    st.metric("Long-term Debt", f"${data['长期债务 (Long-term Debt)'] / 1e6:,.2f} M")

    # 可点击展开查看完整的 SEC EDGAR 原始与结构化数据
    with st.expander("📄 **View Complete Downloaded SEC EDGAR Data (点击展开/查看完整 SEC 抓取数据)**", expanded=False):
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
    st.header("⚙️ Engine & Valuation Settings")
    
    selected_model = st.selectbox(
        "Base LLM Reasoning Engine", 
        ["deepseek-r1:32b", "deepseek-r1:14b", "qwen2.5:32b"]
    )
    
    st.divider()
    st.subheader("📊 DCF Discount Parameters")
    
    wacc = st.number_input("WACC / Discount Rate (%)", value=10.5, step=0.1) / 100
    g = st.number_input("Perpetual Growth Rate g (%)", value=2.5, step=0.1) / 100
    growth_rate = st.number_input("5-Yr FCFF CAGR (%)", value=10.0, step=0.5) / 100
    
    st.divider()
    st.subheader("🛠️ Capital Expenditure (CapEx) Adjustment")
    capex_input = st.number_input("Estimated Annual CapEx ($ Millions)", value=7000.0, step=500.0) * 1e6
    
    dlom = st.number_input("Discount for Lack of Marketability DLOM (%)", value=20.0, step=1.0) / 100
    is_unlisted = st.checkbox("Private Company (Apply DLOM)", value=False)

# -----------------------------------------------------------------------------
# 4. Main Navigation Tabs
# -----------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["🧮 1. DCF Model Engine", "📄 2. Unstructured PDF Parser", "📉 3. Sensitivity Matrix"])

# --- TAB 1: DCF Calculator ---
with tab1:
    st.subheader("5-Year Free Cash Flow Projection & Discounting")
    
    # Base Cash Flow Setup (OCF - CapEx = FCFF)
    base_ocf = 23000000.0  # Default fallback
    if st.session_state['sec_data'] and st.session_state['sec_data']['经营活动现金流 (OCF)'] > 0:
        base_ocf = float(st.session_state['sec_data']['经营活动现金流 (OCF)'])
    
    # FCFF Base calculation
    base_fcff = base_ocf - capex_input
    
    st.info(
        f"💡 **Base FCFF Setup**: Operating Cash Flow (${base_ocf / 1e6:,.2f} M) - CapEx (${capex_input / 1e6:,.2f} M) "
        f"= **Starting FCFF: ${base_fcff / 1e6:,.2f} M**"
    )
    
    # Generate 5-Yr Projections
    future_fcff = [base_fcff * ((1 + growth_rate) ** i) for i in range(1, 6)]
    
    df_calc = pd.DataFrame({
        "Projection Year": ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5"],
        "Projected FCFF ($)": future_fcff
    })
    
    edited_df = st.data_editor(df_calc, num_rows="dynamic", use_container_width=True)
    
    # Execute Calculation
    if st.button("📐 Run Precise DCF Valuation", type="primary"):
        fcff_list = edited_df["Projected FCFF ($)"].tolist()
        
        # 1. Discount Factors
        discount_factors = [(1 + wacc) ** i for i in range(1, 6)]
        pv_fcff_list = [fcff / df_val for fcff, df_val in zip(fcff_list, discount_factors)]
        sum_pv_fcff = sum(pv_fcff_list)
        
        # 2. Terminal Value Calculation
        tv = (fcff_list[-1] * (1 + g)) / (wacc - g)
        pv_tv = tv / ((1 + wacc) ** 5)
        
        # 3. Enterprise Value & Equity Value
        ev = sum_pv_fcff + pv_tv
        final_ev = ev * (1 - dlom) if is_unlisted else ev
        
        per_share = None
        equity_val = final_ev
        cash = 0.0
        debt = 0.0
        shares = 0.0
        
        if st.session_state['sec_data'] and st.session_state['sec_data']['普通股总股本 (Shares)'] > 0:
            shares = st.session_state['sec_data']['普通股总股本 (Shares)']
            cash = st.session_state['sec_data']['现金及现金等价物 (Cash)']
            debt = st.session_state['sec_data']['长期债务 (Long-term Debt)']
            
            equity_val = final_ev + cash - debt
            per_share = equity_val / shares

        # Save DCF calculation results persistently
        st.session_state['dcf_results'] = {
            'base_fcff': base_fcff,
            'fcff_list': fcff_list,
            'discount_factors': discount_factors,
            'pv_fcff_list': pv_fcff_list,
            'sum_pv_fcff': sum_pv_fcff,
            'tv': tv,
            'pv_tv': pv_tv,
            'ev': ev,
            'final_ev': final_ev,
            'cash': cash,
            'debt': debt,
            'equity_val': equity_val,
            'shares': shares,
            'per_share': per_share
        }

    # Persistent Display of FMV Results (Vertical Stacking)
    if st.session_state['dcf_results']:
        res = st.session_state['dcf_results']
        st.divider()
        st.markdown("### 🎯 Final Valuation Results (Fair Market Value)")
        
        # 🌟 竖向排列：估值结果指标
        st.metric("PV of Discrete Cash Flows", f"${res['sum_pv_fcff'] / 1e6:,.2f} M")
        st.metric("PV of Terminal Value (PV of TV)", f"${res['pv_tv'] / 1e6:,.2f} M")
        st.metric("Enterprise Value (EV)", f"${res['final_ev'] / 1e6:,.2f} M")
        
        if res['per_share'] is not None:
            st.metric("Intrinsic Value per Share (FMV)", f"${res['per_share']:,.2f} / share")
        else:
            st.metric("Assessed Total Value (FMV)", f"${res['final_ev'] / 1e6:,.2f} M")

        # -----------------------------------------------------------------------------
        # 🔍 Step-by-Step Calculation Breakdown Web Section
        # -----------------------------------------------------------------------------
        with st.expander("🔍 **Detailed Step-by-Step Mathematical Breakdown (全流程计算推导步骤)**", expanded=True):
            st.markdown("#### **Step 1: Starting Free Cash Flow to Firm (FCFF)**")
            st.latex(r"\text{FCFF}_0 = \text{Operating Cash Flow (OCF)} - \text{CapEx}")
            st.write(f"• OCF = **${base_ocf / 1e6:,.2f} M** | CapEx = **${capex_input / 1e6:,.2f} M**")
            st.write(f"• Base $\\text{{FCFF}}_0$ = **${res['base_fcff'] / 1e6:,.2f} M**")

            st.markdown("#### **Step 2: 5-Year Present Value (PV) Breakdown**")
            breakdown_data = []
            for i in range(5):
                breakdown_data.append({
                    "Year": f"Year {i+1}",
                    "FCFF ($M)": f"${res['fcff_list'][i] / 1e6:,.2f} M",
                    "Discount Factor (1+WACC)^t": f"{res['discount_factors'][i]:.4f}",
                    "Present Value ($M)": f"${res['pv_fcff_list'][i] / 1e6:,.2f} M"
                })
            st.table(pd.DataFrame(breakdown_data))
            sum_pv_str = f"{res['sum_pv_fcff'] / 1e6:,.2f}"
            st.write(f"• **Sum of 5-Yr PV ($\sum PV_{{FCFF}}$)** = **${sum_pv_str} M**")

            st.markdown("#### **Step 3: Terminal Value (TV) & PV of TV**")
            st.latex(r"TV = \frac{\text{FCFF}_5 \times (1 + g)}{WACC - g}")
            fcff_5_str = f"{res['fcff_list'][-1]/1e6:,.2f}"
            tv_str = f"{res['tv']/1e6:,.2f}"
            pv_tv_str = f"{res['pv_tv']/1e6:,.2f}"
            st.write(f"• $TV = \\frac{{\\${fcff_5_str}\\text{{M}} \\times (1 + {g})}}{{{wacc} - {g}}} = \\mathbf{{\\${tv_str} \\text{{ M}}}}$")
            st.latex(r"PV(TV) = \frac{TV}{(1 + WACC)^5}")
            st.write(f"• $PV(TV) = \\frac{{\\${tv_str}\\text{{M}}}}{{(1 + {wacc})^5}} = \\mathbf{{\\${pv_tv_str} \\text{{ M}}}}$")

            st.markdown("#### **Step 4: Enterprise Value (EV) to Equity Value Bridge**")
            st.latex(r"\text{Enterprise Value (EV)} = \sum PV_{FCFF} + PV(TV)")
            ev_str = f"{res['ev']/1e6:,.2f}"
            st.write(f"• $EV = \\${sum_pv_str}\\text{{M}} + \\${pv_tv_str}\\text{{M}} = \\mathbf{{\\${ev_str} \\text{{ M}}}}$")
            
            if res['per_share'] is not None:
                st.latex(r"\text{Equity Value} = \text{EV} + \text{Cash} - \text{Debt}")
                cash_str = f"{res['cash']/1e6:,.2f}"
                debt_str = f"{res['debt']/1e6:,.2f}"
                eq_val_m_str = f"{res['equity_val']/1e6:,.2f}"
                st.write(f"• Equity Value = $\\${ev_str}\\text{{M}} + \\${cash_str}\\text{{M}} - \\${debt_str}\\text{{M}} = \\mathbf{{\\${eq_val_m_str} \\text{{ M}}}}$")
                
                st.markdown("#### **Step 5: Intrinsic Fair Market Value (FMV) Per Share**")
                st.latex(r"\text{FMV per Share} = \frac{\text{Equity Value}}{\text{Shares Outstanding}}")
                
                eq_val_str = f"{res['equity_val']:,.2f}"
                shares_str = f"{res['shares']:,.0f}"
                per_share_str = f"{res['per_share']:,.2f}"
                st.write(f"• $\\text{{FMV}} = \\frac{{\\${eq_val_str}}}{{{shares_str}\\text{{ shares}}}} = \\mathbf{{\\${per_share_str} / \\text{{share}}}}$")

# --- TAB 2: Unstructured PDF Parser ---
with tab2:
    st.subheader("Upload Local PDF Financial Report / Pitchbook")
    uploaded_file = st.file_uploader("Drag and drop PDF file here", type=["pdf"])

# --- TAB 3: Sensitivity Matrix ---
with tab3:
    st.subheader("2D Sensitivity Analysis (WACC vs. Perpetual Growth g)")
    st.caption("Renders dynamic valuation matrix based on the latest DCF execution in Tab 1.")
    
    if st.session_state['dcf_results'] and 'fcff_list' in st.session_state['dcf_results']:
        fcff_list = st.session_state['dcf_results']['fcff_list']
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
                pv_fcff_temp = [fcff / ((1 + w_val) ** i) for i, fcff in enumerate(fcff_list, 1)]
                val = sum(pv_fcff_temp) + pv_tv_temp
                if is_unlisted:
                    val *= (1 - dlom)
                
                if st.session_state['sec_data'] and st.session_state['sec_data']['普通股总股本 (Shares)'] > 0:
                    shares = st.session_state['sec_data']['普通股总股本 (Shares)']
                    cash = st.session_state['sec_data']['现金及现金等价物 (Cash)']
                    debt = st.session_state['sec_data']['长期债务 (Long-term Debt)']
                    eq_v = val + cash - debt
                    row.append(round(eq_v / shares, 2))
                else:
                    row.append(round(val / 1e6, 2))
            matrix.append(row)
            
        col_labels = [f"g: {g_v*100:.1f}%" for g_v in g_range]
        row_labels = [f"WACC: {w*100:.1f}%" for w in wacc_range]
        
        sens_df = pd.DataFrame(matrix, index=row_labels, columns=col_labels)
        
        val_unit = "$/share" if (st.session_state['sec_data'] and st.session_state['sec_data']['普通股总股本 (Shares)'] > 0) else "EV ($M)"
        st.write(f"**Valuation Matrix ({val_unit})**")
        st.dataframe(sens_df.style.highlight_max(axis=None, color='#d4edda').highlight_min(axis=None, color='#f8d7da'), use_container_width=True)
    else:
        st.warning("⚠️ Please run the DCF valuation in Tab 1 first to generate the sensitivity matrix.")
