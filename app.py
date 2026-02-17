import streamlit as st
import pandas as pd
import os
import io
import plotly.express as px
import plotly.graph_objects as go

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Profitability Analytics", layout="wide")

# Custom CSS
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #002b50; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] label, [data-testid="stSidebar"] .stMarkdown p { color: white !important; }
    [data-testid="stSidebar"] hr { border-color: rgba(255, 255, 255, 0.3) !important; }
    div[data-baseweb="select"] > div { background-color: white; }
    .stMetric { background-color: #ffffff; border-radius: 10px; padding: 15px; border: 1px solid #e0e0e0; }
    
    /* Estilo para tu link de LinkedIn */
    .author-link {
        font-size: 0.85rem;
        color: rgba(255, 255, 255, 0.7) !important;
        text-decoration: none;
        transition: 0.3s;
    }
    .author-link:hover {
        color: #00cc96 !important;
        text-decoration: underline;
    }
    </style>
    """, unsafe_allow_html=True)

def clean_val(x):
    if isinstance(x, str):
        return float(x.replace('$', '').replace('%', '').replace(',', '').strip())
    return x

# --- DATA CALCULATION ENGINE ---
@st.cache_data
def run_financial_engine():
    # 1. Load Files
    df_vol = pd.read_csv('CSV/Vol_Actuals_2024_2025.csv', dtype={'EAN Code': str})
    df_pri = pd.read_csv('CSV/Pricing_Cost.csv', dtype={'EAN': str})
    df_tra = pd.read_csv('CSV/Trade_Spend.csv')

    # 2. Key Normalization
    df_vol['EAN_Key'] = df_vol['EAN Code'].astype(str).str.strip().str.split('.').str[0]
    df_pri['EAN_Key'] = df_pri['EAN'].astype(str).str.strip().str.split('.').str[0]
    
    for col in ['List Price', 'Std Cost', 'GTG %']:
        df_pri[col] = df_pri[col].apply(clean_val)
    
    df_pri['GTG %'] = df_pri['GTG %'] / 100
    df_tra['Percentage'] = df_tra['Percentage'].apply(clean_val) / 100

    # 3. Aggregate Volume
    df_master = df_vol.groupby(['Year', 'Channel', 'Category', 'Customer Name', 'EAN_Key']).agg({'Units': 'sum'}).reset_index()

    # 4. Merges
    df_master = pd.merge(df_master, df_pri[['Year', 'Channel', 'EAN_Key', 'List Price', 'Std Cost', 'GTG %']], 
                         on=['Year', 'Channel', 'EAN_Key'], how='left').fillna(0)
    
    df_tra_pct = df_tra.groupby(['Year', 'Channel', 'Category']).agg({'Percentage': 'sum'}).reset_index()
    df_tra_pct.rename(columns={'Percentage': 'TS_Policy_Pct'}, inplace=True)
    df_master = pd.merge(df_master, df_tra_pct, on=['Year', 'Channel', 'Category'], how='left').fillna(0)

    # 5. Financial Calculations
    df_master['Gross Sales'] = df_master['Units'] * df_master['List Price']
    df_master['Off_Invoice'] = df_master['Gross Sales'] * df_master['GTG %']
    df_master['GTS'] = df_master['Gross Sales'] - df_master['Off_Invoice']
    df_master['Trade_Spend_Value'] = df_master['Gross Sales'] * df_master['TS_Policy_Pct']
    df_master['Net_Total_Sales'] = df_master['GTS'] - df_master['Trade_Spend_Value']
    df_master['COGS'] = df_master['Units'] * df_master['Std Cost']
    df_master['Gross_Profit'] = df_master['Net_Total_Sales'] - df_master['COGS']

    return df_master

df_all = run_financial_engine()

# --- SIDEBAR FILTERS ---
with st.sidebar:
    st.title("🌐 Global Filters")
    st.divider()
    sel_year = st.selectbox("📅 Year", sorted(df_all['Year'].unique(), reverse=True), key="y")
    sel_chan = st.multiselect("🏪 Channel", sorted(df_all['Channel'].unique()), default=df_all['Channel'].unique(), key="c")
    sel_cat = st.multiselect("🏷️ Category", sorted(df_all['Category'].unique()), default=df_all['Category'].unique(), key="b")

    # --- FOOTER AUTOR (Mantenlo indentado aquí) ---
    st.markdown("---")
    st.caption("Environment: Free Tier")
    st.markdown(
        f'<a href="https://www.linkedin.com/in/joselyne-marquez/" target="_blank" class="author-link">'
        f'👤 Author: JosyMarquez</a>', 
        unsafe_allow_html=True
    )

# Apply Filters
df_f = df_all[(df_all['Year'] == sel_year) & 
                (df_all['Channel'].isin(sel_chan)) & 
                (df_all['Category'].isin(sel_cat))]

# --- DASHBOARD TABS ---
st.title(f"📊 Financial Performance Engine - {sel_year}")
tab_pl, tab_weights, tab_pvm, tab_ean, tab_download = st.tabs([
    "📉 P&L Summary", "⚖️ Mix Weights", "🌊 PVM Analysis", "📦 Units by EAN", "📥 Raw Data"
])

with tab_pl:
    # Top Level Metrics
    c1, c2, c3, c4 = st.columns(4)
    nts = df_f['Net_Total_Sales'].sum()
    gp = df_f['Gross_Profit'].sum()
    margin = (gp / nts * 100) if nts != 0 else 0
    
    c1.metric("Gross Sales", f"${df_f['Gross Sales'].sum():,.0f}")
    c2.metric("Net Total Sales", f"${nts:,.0f}")
    c3.metric("Gross Profit", f"${gp:,.0f}")
    c4.metric("GP Margin %", f"{margin:.1f}%")

    st.divider()
    st.subheader("Performance by Category")
    brand_pl = df_f.groupby('Category').agg({
        'Units': 'sum',
        'Gross Sales': 'sum',
        'Net_Total_Sales': 'sum',
        'Gross_Profit': 'sum'
    }).reset_index()

    st.dataframe(
        brand_pl.style.format({
            'Units': '{:,.0f}', 'Gross Sales': '${:,.0f}', 
            'Net_Total_Sales': '${:,.0f}', 'Gross_Profit': '${:,.0f}'
        }), use_container_width=True, hide_index=True
    )

with tab_weights:
    st.subheader("Participation % (Mix) by Category")
    col1, col2 = st.columns(2)
    
    weights = df_f.groupby('Category').agg({'Units':'sum', 'Net_Total_Sales':'sum'}).reset_index()
    weights['% Volume'] = weights['Units'] / weights['Units'].sum()
    weights['% NTS'] = weights['Net_Total_Sales'] / weights['Net_Total_Sales'].sum()
    
    with col1:
        st.dataframe(
            weights.style.format({'Units':'{:,.0f}', 'Net_Total_Sales':'${:,.0f}', '% Volume': '{:.1%}', '% NTS': '{:.1%}'}),
            use_container_width=True, hide_index=True
        )
    with col2:
        fig_pie = px.pie(weights, values='Net_Total_Sales', names='Category', hole=0.4, title="NTS Mix %")
        st.plotly_chart(fig_pie, use_container_width=True)

with tab_pvm:
    st.subheader("Price-Volume-Mix (PVM) Analysis")
    prev_yr = sel_year - 1
    df_prev = df_all[df_all['Year'] == prev_yr]
    
    if not df_prev.empty:
        pvm_list = []
        tot_v1, tot_v2 = df_prev['Units'].sum(), df_f['Units'].sum()
        
        for cat in sorted(df_all['Category'].unique()):
            d1 = df_prev[df_prev['Category'] == cat]
            d2 = df_f[df_f['Category'] == cat]
            
            v1, v2 = d1['Units'].sum(), d2['Units'].sum()
            p1 = (d1['Net_Total_Sales'].sum() / v1) if v1 > 0 else 0
            p2 = (d2['Net_Total_Sales'].sum() / v2) if v2 > 0 else 0
            mix1 = v1 / tot_v1 if tot_v1 > 0 else 0
            mix2 = v2 / tot_v2 if tot_v2 > 0 else 0
            
            p_eff = v2 * (p2 - p1)
            v_eff = (tot_v2 - tot_v1) * mix1 * p1
            m_eff = tot_v2 * (mix2 - mix1) * p1
            
            pvm_list.append({'Category': cat, 'Price Effect': p_eff, 'Volume Effect': v_eff, 'Mix Effect': m_eff, 'Total Delta': (v2*p2)-(v1*p1)})
        
        df_pvm = pd.DataFrame(pvm_list)
        
        fig_wf = go.Figure(go.Waterfall(
            orientation = "v",
            measure = ["absolute", "relative", "relative", "relative", "total"],
            x = [f"NTS {prev_yr}", "Price", "Volume", "Mix", f"NTS {sel_year}"],
            y = [df_prev['Net_Total_Sales'].sum(), df_pvm['Price Effect'].sum(), df_pvm['Volume Effect'].sum(), df_pvm['Mix Effect'].sum(), nts],
            decreasing = {"marker":{"color":"#ef553b"}},
            increasing = {"marker":{"color":"#00cc96"}},
            totals = {"marker":{"color":"#002b50"}}
        ))
        st.plotly_chart(fig_wf, use_container_width=True)
        
        st.dataframe(df_pvm.style.format({
            'Price Effect': '${:,.0f}', 'Volume Effect': '${:,.0f}', 'Mix Effect': '${:,.0f}', 'Total Delta': '${:,.0f}'
        }), use_container_width=True, hide_index=True)
    else:
        st.warning("Insufficient data for previous year PVM.")

with tab_ean:
    st.subheader("📦 Units and Performance by Product (EAN)")
    
    # Aggregate data by EAN_Key
    df_ean = df_f.groupby(['EAN_Key', 'Category']).agg({
        'Units': 'sum',
        'Gross Sales': 'sum',
        'Net_Total_Sales': 'sum',
        'Gross_Profit': 'sum'
    }).reset_index().sort_values(by='Units', ascending=False)
    
    # Important: format EAN_Key as string to prevent commas or scientific notation
    st.dataframe(
        df_ean.style.format({
            'EAN_Key': lambda x: str(x),
            'Units': '{:,.0f}',
            'Gross Sales': '${:,.2f}',
            'Net_Total_Sales': '${:,.2f}',
            'Gross_Profit': '${:,.2f}'
        }),
        use_container_width=True,
        hide_index=True
    )

with tab_download:
    st.subheader("📄 Raw Account Data (Absolute Values to GP Level)")

    # 1. Load Trade Spend Rules
    df_tra_rules = pd.read_csv('CSV/Trade_Spend.csv')
    df_tra_rules['Percentage'] = df_tra_rules['Percentage'].apply(clean_val) / 100

    # 2. Build the Raw Data rows using absolute values
    raw_data_list = []

    for _, row in df_f.iterrows():
        common = {
            'Year': row['Year'], 
            'Channel': row['Channel'], 
            'Customer': row['Customer Name'], 
            'Category': row['Category'], 
            'EAN': row['EAN_Key']
        }
        
        # --- ALL VALUES ARE NOW ABSOLUTE (POSITIVE) ---
        
        # Gross Sales
        raw_data_list.append({**common, 'Account code': 'GS-001', 'Account': 'Gross Sales', 'Value': abs(row['Gross Sales'])})
        
        # Off-Invoice
        if row['Off_Invoice'] != 0:
            raw_data_list.append({**common, 'Account code': 'OI-001', 'Account': 'Off-Invoice', 'Value': abs(row['Off_Invoice'])})

        # Trade Spend Breakdown
        specific_trade = df_tra_rules[
            (df_tra_rules['Year'] == row['Year']) & 
            (df_tra_rules['Channel'] == row['Channel']) & 
            (df_tra_rules['Category'] == row['Category'])
        ]
        
        for _, trade_rule in specific_trade.iterrows():
            trade_value = row['Gross Sales'] * trade_rule['Percentage']
            if trade_value != 0:
                raw_data_list.append({
                    **common, 
                    'Account code': trade_rule['Account Code'], 
                    'Account': trade_rule['Account Name'], 
                    'Value': abs(trade_value)
                })

        # Cost of Goods Sold
        if row['COGS'] != 0:
            raw_data_list.append({**common, 'Account code': 'CS-001', 'Account': 'COGS', 'Value': abs(row['COGS'])})

    # 3. Create DataFrame
    df_raw_absolute = pd.DataFrame(raw_data_list)

    # 4. Streamlit Display
    st.dataframe(
        df_raw_absolute.style.format({
            'EAN': lambda x: str(x),
            'Value': '${:,.2f}'
        }),
        use_container_width=True,
        hide_index=True
    )

    # 5. Export Button
    csv_raw = df_raw_absolute.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Absolute Value P&L Report", 
        data=csv_raw, 
        file_name=f"Absolute_Financial_Data_{sel_year}.csv", 
        mime="text/csv"
    )
