import streamlit as st
import pandas as pd
import io

# Page configuration
st.set_page_config(page_title="NovaPure Engine", layout="wide")

def clean_numeric(x):
    if isinstance(x, str):
        return float(x.replace('$', '').replace('%', '').replace(',', '').strip())
    return x

st.title("Actuals Profit Engine")

# Attempt to load files from the CSV folder
try:
    # Note: Using the exact names from your folder
    df_vol = pd.read_csv('CSV/Vol_Actuals_2024_2025.csv')
    df_pri = pd.read_csv('CSV/Pricing_Cost.csv')
    df_tra = pd.read_csv('CSV/Trade_Spend.csv')
    st.sidebar.success("Files loaded correctly from /CSV")
except Exception as e:
    st.error("Error: Check that files 'Vol_Actuals_2024_2025.csv', 'Pricing_Cost.csv', and 'Trade_Spend.csv' are inside the 'CSV' folder.")
    st.stop()

if st.button("Process Financial Data"):
    # 1. Data Cleaning
    df_pri['List Price'] = df_pri['List Price'].apply(clean_numeric)
    df_pri['Std Cost'] = df_pri['Std Cost'].apply(clean_numeric)
    df_pri['GTG %'] = df_pri['GTG %'].apply(clean_numeric) / 100
    df_tra['Percentage'] = df_tra['Percentage'].apply(clean_numeric) / 100

    # 2. Integration (Merge)
    # Merging Volume with Pricing using Year, EAN, and Channel
    df_master = pd.merge(
        df_vol, 
        df_pri[['Year', 'EAN', 'Channel', 'List Price', 'Std Cost', 'GTG %']], 
        left_on=['Year', 'EAN Code', 'Channel'],
        right_on=['Year', 'EAN', 'Channel'],
        how='left'
    )

    # 3. Waterfall Calculations
    df_master['Gross_Sales'] = df_master['Units'] * df_master['List Price']
    df_master['Off_Invoice'] = df_master['Gross_Sales'] * df_master['GTG %']
    df_master['Net_Shipment'] = df_master['Gross_Sales'] - df_master['Off_Invoice']
    
    # 4. Trade Spend Application
    trade_pivot = df_tra.groupby(['Year', 'Category', 'Channel', 'Type'])['Percentage'].sum().unstack(fill_value=0)
    df_master = pd.merge(df_master, trade_pivot, on=['Year', 'Category', 'Channel'], how='left')

    df_master['Value_Agreements'] = df_master['Gross_Sales'] * df_master.get('Agreement', 0)
    df_master['Value_Activities'] = df_master['Gross_Sales'] * df_master.get('Activity', 0)
    
    df_master['Net_Total_Sales'] = df_master['Net_Shipment'] - df_master['Value_Agreements'] - df_master['Value_Activities']
    df_master['Total_COGS'] = df_master['Units'] * df_master['Std Cost']
    df_master['Gross_Profit'] = df_master['Net_Total_Sales'] - df_master['Total_COGS']

    # 5. Flat File Transformation
    id_vars = ['Year', 'Category', 'EAN Code', 'Channel', 'Customer Name']
    value_map = {
        'Units': 'Volume Units',
        'Gross_Sales': 'Gross Sales',
        'Net_Total_Sales': 'Net Total Sales',
        'Total_COGS': 'COGS',
        'Gross_Profit': 'Gross Profit'
    }
    
    df_final = pd.melt(df_master, id_vars=id_vars, value_vars=list(value_map.keys()),
                       var_name='Account', value_name='Value')
    
    df_final['Account'] = df_final['Account'].map(value_map)
    df_final.columns = ['Year', 'Category', 'EAN', 'Channel', 'Client', 'Account', 'Value']

    st.subheader("Results Preview")
    st.dataframe(df_final.head(15), use_container_width=True)

    # Export to CSV
    output = io.StringIO()
    df_final.to_csv(output, index=False)
    st.download_button(
        label="Download Consolidated GP File",
        data=output.getvalue(),
        file_name="NovaPure_Final_GP.csv",
        mime="text/csv"
    )