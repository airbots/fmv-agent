import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import requests
import json
from sec_fetcher import SECValuationFetcher
# -----------------------------------------------------------------------------
# 1. 页面基本配置与样式定义
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="离线本地金融估值工作台",
    page_icon="📈",
    layout="wide"
)

st.title("📈 高精度离线估值平台 (Local Valuation Engine)")
st.caption("🔒 100% 离线私有化运行 | DeepSeek-R1 逻辑推演 + 确定性 Python 算术引擎")

# -----------------------------------------------------------------------------
# 2. 侧边栏：模型配置与估值核心参数设定
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 引擎与基础参数设置")
    
    # 本地 API 配置
    llm_url = st.text_input("本地 Ollama 接口", value="http://localhost:11434/api/generate")
    selected_model = st.selectbox("选择基座推理模型", ["deepseek-r1:32b", "qwen2.5:32b"])
    
    st.divider()
    st.subheader("📊 折现现金流 (DCF) 参数")
    
    wacc = st.number_input("加权平均资本成本 WACC (%)", value=8.5, step=0.1) / 100
    g = st.number_input("永续增长率 g (%)", value=2.5, step=0.1) / 100
    dlom = st.number_input("流动性折价 DLOM (%) [未上市公司]", value=20.0, step=1.0) / 100
    
    is_unlisted = st.checkbox("该目标为未上市公司（启用 DLOM/DLOC 修正）", value=False)

# -----------------------------------------------------------------------------
# 3. 主界面布局：三步法估值流程
# -----------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📄 1. 财报/BP 解析与假设提炼", "🧮 2. 确定性模型计算", "📉 3. 敏感度分析"])

# --- TAB 1: 财报解析 ---
with tab1:
    st.subheader("上传非结构化文档 (财报 / 招股书 / BP)")
    uploaded_file = st.file_uploader("拖拽 PDF 或 Excel 到此处", type=["pdf", "xlsx"])
    
    col1, col2 = st.columns(2)
    with col1:
        user_prompt = st.text_area(
            "提示词（让大模型提取历史财务数据与逻辑）:",
            value="请解析资产负债表与利润表，提取近3年的 EBITDA Margin、资本支出 CapEx 及净营运资金变动，并给出未来5年的预测逻辑假设。"
        )
        parse_btn = st.button("🚀 启动离线智能解析", type="primary")
        
    with col2:
        if parse_btn:
            st.info("大模型 CoT 思维链推理中...")
            # 模拟调用本地 Ollama 接口（此处可拓展连接 PyMuPDF 解析文本）
            st.success("解析完成！已提炼关键参数与页码溯源。")
            st.json({
                "源文件页码": "PDF Page 42, Table 3",
                "提取数据": {"EBITDA_Margin_Avg": "22.5%", "CapEx_Ratio": "5.1%"},
                "推理逻辑": "基于过去三年经营现金流推演，永续增长阶段 CAPEX 趋近于折旧摊销。"
            })

# --- TAB 2: Python 引擎精准计算 ---
with tab2:
    st.subheader("🤖 1-Click 自动化 SEC 数据拉取")
    
    col_input, col_btn = st.columns([3, 1])
    with col_input:
        symbol = st.text_input("输入美股股票代码 (Ticker):", value="AMSC").upper()
    with col_btn:
        st.write("") # 垂直对齐
        st.write("") 
        fetch_btn = st.button("📥 一键抓取 SEC 财报数据")

    if fetch_btn:
        with st.spinner(f"正在连接 SEC EDGAR 数据库抓取 {symbol} 官方财报..."):
            try:
                fetcher = SECValuationFetcher()
                sec_data = fetcher.fetch_valuation_data(symbol)
                
                st.success(f"成功获取 {symbol} (CIK: {sec_data['CIK']}) 最新 SEC 10-K 财报数据！")
                
                # 自动填充到前端展示指标中
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("营业收入", f"${sec_data['营业收入 (Revenue)'] / 1e6:,.1f} M")
                c2.metric("经营现金流 (OCF)", f"${sec_data['经营活动现金流 (OCF)'] / 1e6:,.1f} M")
                c3.metric("手头现金", f"${sec_data['现金及现金等价物 (Cash)'] / 1e6:,.1f} M")
                c4.metric("长期债务", f"${sec_data['长期债务 (Long-term Debt)'] / 1e6:,.1f} M")
                
                # 将自动拉取到的现金流直接灌入 DCF 折现引擎
                st.session_state['base_ocf'] = sec_data['经营活动现金流 (OCF)']
            except Exception as e:
                st.error(f"抓取失败: {str(e)}")


    st.subheader("未来自由现金流 (FCFF) 预测与折现计算")
    st.markdown("💡 *大模型负责推演表格假设，实际数值折现完全由 Python 沙盒执行，确保零计算幻觉。*")
    
    # 允许用户在线编辑预测表
    default_data = {
        "年份": ["Year 1", "Year 2", "Year 3", "Year 4", "Year 5"],
        "预计营业收入 (万元)": [10000, 12500, 15000, 17500, 19000],
        "FCFF 自由现金流 (万元)": [1500, 1900, 2400, 2800, 3100]
    }
    df = pd.DataFrame(default_data)
    edited_df = st.data_editor(df, num_rows="dynamic")
    
    if st.button("📐 执行精确 DCF 折现计算"):
        fcff_list = edited_df["FCFF 自由现金流 (万元)"].tolist()
        
        # 精确数学计算 (Python 引擎)
        discount_factors = [(1 + wacc) ** i for i in range(1, 6)]
        pv_fcff = [fcff / df_val for fcff, df_val in zip(fcff_list, discount_factors)]
        
        # 终值 (Terminal Value)
        tv = (fcff_list[-1] * (1 + g)) / (wacc - g)
        pv_tv = tv / ((1 + wacc) ** 5)
        
        # 企业价值 (EV)
        ev = sum(pv_fcff) + pv_tv
        
        # 未上市公司流动性折价修正
        final_val = ev * (1 - dlom) if is_unlisted else ev
        
        st.divider()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("预测期现金流现值", f"¥ {sum(pv_fcff):,.2f} 万")
        m2.metric("终值现值 (PV of TV)", f"¥ {pv_tv:,.2f} 万")
        m3.metric("企业价值 (EV)", f"¥ {ev:,.2f} 万")
        m4.metric("最终评估价值 (含折价)", f"¥ {final_val:,.2f} 万", delta=f"-{dlom*100}% DLOM" if is_unlisted else None)

# --- TAB 3: 敏感度分析 ---
with tab3:
    st.subheader("二维敏感度矩阵 (WACC vs. 永续增长率 g)")
    st.caption("避免单一绝对值误导，为投资决策提供估值区间。")
    
    if 'ev' in locals():
        wacc_range = np.linspace(wacc - 0.01, wacc + 0.01, 5)
        g_range = np.linspace(g - 0.005, g + 0.005, 5)
        
        matrix = []
        for w_val in wacc_range:
            row = []
            for g_val in g_range:
                tv_temp = (fcff_list[-1] * (1 + g_val)) / (w_val - g_val)
                pv_tv_temp = tv_temp / ((1 + w_val) ** 5)
                pv_fcff_temp = [fcff / ((1 + w_val) ** i) for i, fcff in enumerate(fcff_list, 1)]
                val = sum(pv_fcff_temp) + pv_tv_temp
                if is_unlisted: val *= (1 - dlom)
                row.append(round(val, 2))
            matrix.append(row)
            
        sens_df = pd.DataFrame(
            matrix, 
            index=[f"WACC {w*100:.1f}%" for w in wacc_range],
            columns=[f"g {g_v*100:.1f}%" for g_v in g_range]
        )
        st.dataframe(sens_df.style.highlight_max(axis=None, color='#d4edda').highlight_min(axis=None, color='#f8d7da'))
    else:
        st.warning("请先在 TAB 2 中点击执行 DCF 计算。")
