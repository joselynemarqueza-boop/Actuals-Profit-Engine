import streamlit as st
import pandas as pd
import os
import io
import plotly.express as px
import plotly.graph_objects as go

# --- PAGE CONFIGURATION ---
# Fixed the function name from set_config to set_page_config
st.set_page_config(page_title="NovaPure | Profitability Analytics", layout="wide")

# Custom CSS for NovaPure Theme
st.markdown("""
    <style>
    [data-testid="stSidebar"] { background-color: #002b50; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] label, [data-testid="stSidebar"] .stMarkdown p { color: white !important; }
    .stMetric { background-color: #ffffff; border-radius: 10px; padding: 15px; border: 1px solid #e0e0e0; }
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

    # 2. ROBUST EAN CLEANING
    df_vol['EAN_Key'] = df_vol['EAN Code'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    df_pri['EAN_Key'] = df_pri['EAN'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
    
    # 3. Clean numeric columns
    for col in ['List Price', 'Std Cost', 'GTG %']:
        df_pri[col] = df_pri[col].apply(clean_val)
    df_pri['GTG %'] = df_pri['GTG %'] / 100
    df_tra['Percentage'] = df_tra['Percentage'].apply(clean_val) / 100

    # 4. Aggregate Volume
    df_master = df_vol.groupby(['Year', 'Channel', 'Category', 'Customer Name', 'EAN_Key']).agg({'Units': 'sum'}).reset_index()

    # 5. MERGE PRICING
    df_master = pd.merge(df_master, df_pri[['Year', 'Channel', 'EAN_Key', 'List Price', 'Std Cost', 'GTG %']], 
                         on=['Year', 'Channel', 'EAN_Key'], how='left')
    
    df_master.fillna(0, inplace=True)

    # 6. Financial Calculations
    df_master['Gross Sales'] = df_master['Units'] * df_master['List Price']
    df_master['Off_Invoice'] = df_master['Gross Sales'] * df_master['GTG %']
    df_master['GTS'] = df_master['Gross Sales'] - df_master['Off_Invoice']
    
    df_tra_pct = df_tra.groupby(['Year', 'Channel', 'Category']).agg({'Percentage': 'sum'}).reset_index()
    df_tra_pct.rename(columns={'Percentage': 'TS_Policy_Pct'}, inplace=True)
    df_master = pd.merge(df_master, df_tra_pct, on=['Year', 'Channel', 'Category'], how='left').fillna(0)

    df_master['Trade_Spend_Value'] = df_master['Gross Sales'] * df_master['TS_Policy_Pct']
    df_master['Net_Total_Sales'] = df_master['GTS'] - df_master['Trade_Spend_Value']
    df_master['COGS'] = df_master['Units'] * df_master['Std Cost']
    df_master['Gross_Profit'] = df_master['Net_Total_Sales'] - df_master['COGS']

    return df_master

df_all = run_financial_engine()

# --- SIDEBAR FILTERS ---
with st.sidebar:
    st.title("🌐 Global Filters")
    sel_year = st.selectbox("📅 Year", sorted(df_all['Year'].unique(), reverse=True))
    sel_chan = st.multiselect("🏪 Channel", sorted(df_all['Channel'].unique()), default=df_all['Channel'].unique())
    sel_cat = st.multiselect("🏷️ Category", sorted(df_all['Category'].unique()), default=df_all['Category'].unique())

df_f = df_all[(df_all['Year'] == sel_year) & 
                (df_all['Channel'].isin(sel_chan)) & 
                (df_all['Category'].isin(sel_cat))]

# --- DASHBOARD ---
st.title(f"📊 Profitability Engine - {sel_year}")
tab_pl, tab_weights, tab_pvm, tab_download, tab_ean = st.tabs([
    "📉 P&L Summary", "⚖️ Mix Weights", "🌊 PVM Analysis", "📥 Raw Data", "📦 EAN Volume Summary"
])

with tab_pl:
    c1, c2, c3, c4 = st.columns(4)
    nts = df_f['Net_Total_Sales'].sum()
    gp = df_f['Gross_Profit'].sum()
    c1.metric("Gross Sales", f"${df_f['Gross Sales'].sum():,.0f}")
    c2.metric("Net Total Sales", f"${nts:,.0f}")
    c3.metric("Gross Profit", f"${gp:,.0f}")
    c4.metric("GP Margin %", f"{(gp/nts*100 if nts != 0 else 0):.1f}%")

    st.subheader("Performance by Category")
    brand_pl = df_f.groupby('Category').agg({
        'Units': 'sum', 'Gross Sales': 'sum', 'Net_Total_Sales': 'sum', 'Gross_Profit': 'sum'
    }).reset_index()
    st.dataframe(brand_pl.style.format({'Units': '{:,.0f}', 'Gross Sales': '${:,.0f}', 'Net_Total_Sales': '${:,.0f}', 'Gross_Profit': '${:,.0f}'}), use_container_width=True, hide_index=True)

with tab_ean:
    st.subheader("Total Volume by EAN Code")
    ean_summary = df_f.groupby(['EAN_Key', 'Category']).agg({'Units': 'sum'}).sort_values('Units', ascending=False).reset_index()
    st.dataframe(ean_summary.style.format({'Units': '{:,.0f}'}), use_container_width=True, hide_index=True)

with tab_download:
    st.subheader("Detailed Export View")
    export_cols = ['Channel', 'Category', 'Customer Name', 'EAN_Key', 'Units', 'Gross Sales', 'Net_Total_Sales', 'Gross_Profit']
    st.dataframe(df_f[export_cols].style.format({'Units':'{:,.0f}', 'Gross Sales':'${:,.2f}', 'Net_Total_Sales':'${:,.2f}', 'Gross_Profit':'${:,.2f}'}), use_container_width=True, hide_index=True)
