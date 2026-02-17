import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="NovaPure Engine", layout="wide")

def clean_numeric(x):
    if isinstance(x, str):
        # Limpia símbolos de moneda y porcentajes
        return float(x.replace('$', '').replace('%', '').replace(',', '').strip())
    return x

st.title("Actuals Profit Engine")

# --- CARGA DE DATOS ---
try:
    # Usamos la carpeta 'CSV' como indicaste
    df_vol = pd.read_csv('CSV/Vol_Actuals_2024_2025.csv')
    df_pri = pd.read_csv('CSV/Pricing_Cost.csv')
    df_tra = pd.read_csv('CSV/Trade_Spend.csv')
    st.sidebar.success("Archivos cargados correctamente.")
except Exception as e:
    st.error(f"Error de archivos: Asegúrate de que la carpeta se llame 'CSV' y los nombres de los archivos sean exactos.")
    st.info("Estructura requerida: CSV/Vol_Actuals_2024_2025.csv, CSV/Pricing_Cost.csv, CSV/Trade_Spend.csv")
    st.stop()

if st.button("Calcular Rentabilidad"):
    try:
        # 1. Limpieza de Precios y Costos
        df_pri['List Price'] = df_pri['List Price'].apply(clean_numeric)
        df_pri['Std Cost'] = df_pri['Std Cost'].apply(clean_numeric)
        df_pri['GTG %'] = df_pri['GTG %'].apply(clean_numeric) / 100
        df_tra['Percentage'] = df_tra['Percentage'].apply(clean_numeric) / 100

        # 2. Cruce de Volumen con Precios
        # Nota: En tu archivo de volumen la columna es 'Units'
        df_master = pd.merge(
            df_vol, 
            df_pri[['Year', 'EAN', 'Channel', 'List Price', 'Std Cost', 'GTG %']], 
            left_on=['Year', 'EAN Code', 'Channel'],
            right_on=['Year', 'EAN', 'Channel'],
            how='left'
        )

        # 3. Cálculos de Cascada
        df_master['Gross_Sales'] = df_master['Units'] * df_master['List Price']
        df_master['Off_Invoice'] = df_master['Gross_Sales'] * df_master['GTG %']
        df_master['Net_Shipment'] = df_master['Gross_Sales'] - df_master['Off_Invoice']
        
        # 4. Agrupar Trade Spend por Tipo (Agreement vs Activity)
        trade_pivot = df_tra.groupby(['Year', 'Category', 'Channel', 'Type'])['Percentage'].sum().unstack(fill_value=0)
        df_master = pd.merge(df_master, trade_pivot, on=['Year', 'Category', 'Channel'], how='left')

        # Asegurar que existan las columnas tras el pivot
        for col in ['Agreement', 'Activity']:
            if col not in df_master.columns:
                df_master[col] = 0

        df_master['Value_Agreements'] = df_master['Gross_Sales'] * df_master['Agreement']
        df_master['Value_Activities'] = df_master['Gross_Sales'] * df_master['Activity']
        
        df_master['Net_Total_Sales'] = df_master['Net_Shipment'] - df_master['Value_Agreements'] - df_master['Value_Activities']
        df_master['Total_COGS'] = df_master['Units'] * df_master['Std Cost']
        df_master['Gross_Profit'] = df_master['Net_Total_Sales'] - df_master['Total_COGS']

        # 5. Formato Final (Unpivot)
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

        st.subheader("Vista Previa")
        st.dataframe(df_final.head(10))

        # Descarga
        csv_data = df_final.to_csv(index=False).encode('utf-8')
        st.download_button("Descargar CSV Consolidado", csv_data, "NovaPure_Output.csv", "text/csv")
        
    except Exception as e:
        st.error(f"Error durante el proceso: {e}")
