# Actuals-Profit-Engine

A streamlined data processor for NovaPure financial reporting. This engine transforms raw sales volume into a detailed profitability flat file.

## 📁 Data Structure
The engine automatically reads files from the `/data` folder:
- `Actuals_Vol.csv`: Historical volume by customer/EAN.
- `Pricing_Cost.csv`: Master list of prices and standard costs per year.
- `Trade_Spend.csv`: Investment rates (Agreements & Activities) by channel.

## ⚙️ Calculation Logic
The engine executes a full P&L waterfall:
1. **Gross Sales**: Unit Volume × List Price.
2. **Net Shipment**: Gross Sales - Off-Invoice (GTG).
3. **Net Total Sales (NTS)**: Net Shipment - (Agreements + Activities).
4. **Gross Profit**: NTS - Total COGS.

## 📊 Output Format
The resulting CSV contains the following columns for easy Pivot Table analysis:
`Year | Category | EAN | Channel Client | Account | Value`

## 🚀 Deployment
Powered by **Streamlit**. Simply push updated CSVs to the `data/` folder to refresh the calculations.
