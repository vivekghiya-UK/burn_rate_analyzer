import streamlit as st
import pandas as pd
import openai
import os

# --- Setup OpenAI API key ---
openai.api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")

st.set_page_config(page_title="Burn Rate & Runway Analyzer", layout="wide")

st.title("🔥 Burn Rate & Runway Analyzer")

st.markdown("""
Upload an Excel file with your financial data.  
Your file **must contain at least two columns**:
- A **Date** column (e.g., 'Date', 'Month') with dates or monthly periods  
- A **Cash Balance** column (e.g., 'Cash', 'Closing Cash') showing cash at period end  

You can upload Excel files with multiple sheets — select the relevant sheet after upload.

[Download sample file](https://github.com/vivekghiya-UK/burn_rate_analyzer/raw/main/sample_data.xlsx)  
(You can use this to see the expected format.)
""")

# --- File uploader ---
uploaded_file = st.file_uploader("Upload your Excel file", type=["xlsx", "xls"])
if not uploaded_file:
    st.info("Please upload an Excel file to continue.")
    st.stop()

# --- Load Excel sheets ---
try:
    xls = pd.ExcelFile(uploaded_file)
except Exception as e:
    st.error(f"Error reading Excel file: {e}")
    st.stop()

sheet_name = st.selectbox("Select the sheet to analyze", xls.sheet_names)

try:
    df = pd.read_excel(xls, sheet_name=sheet_name)
except Exception as e:
    st.error(f"Error loading sheet '{sheet_name}': {e}")
    st.stop()

st.subheader("Preview of your data")
st.dataframe(df.head())

# --- Select columns ---
date_col = st.selectbox("Select the Date column", df.columns)
cash_col = st.selectbox("Select the Cash Balance column", df.columns, index=1)

if date_col == cash_col:
    st.error("Date column and Cash Balance column must be different.")
    st.stop()

# --- Process data ---
try:
    # Convert date column to datetime
    df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
    if df[date_col].isnull().all():
        st.error(f"None of the values in column '{date_col}' could be parsed as dates.")
        st.stop()
except Exception as e:
    st.error(f"Error parsing dates in '{date_col}': {e}")
    st.stop()

# Sort by date ascending
df = df.sort_values(by=date_col).reset_index(drop=True)

# Calculate burn rate (negative of cash balance change)
df['cash_change'] = df[cash_col].diff()
average_burn_rate = -df['cash_change'][1:].mean()  # exclude first NaN

if average_burn_rate <= 0:
    st.warning("Runway estimation not available (average burn rate is zero or positive).")
else:
    latest_cash = df[cash_col].iloc[-1]
    runway_months = latest_cash / average_burn_rate if average_burn_rate > 0 else None

    st.markdown(f"""
    ### Burn Rate & Runway Summary
    - **Average Monthly Burn Rate:** £{average_burn_rate:,.2f}  
    - **Latest Cash Balance:** £{latest_cash:,.2f}  
    - **Estimated Runway:** {runway_months:.1f} months  
    """)

# --- Plot cash balance over time ---
st.line_chart(data=df.set_index(date_col)[cash_col], use_container_width=True)

# --- AI summary option ---
if openai.api_key:
    if st.button("Generate AI Summary Report"):
        with st.spinner("Generating AI summary..."):
            prompt = f"""
            You are a financial analyst.  
            Given the following monthly cash balance data, provide a brief summary of the cash flow situation, including insights on burn rate and runway.

            Data (Date - Cash Balance):\n{df[[date_col, cash_col]].to_csv(index=False)}
            """

            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=250,
                    temperature=0.5,
                )
                summary = response.choices[0].message.content.strip()
                st.markdown("### AI Summary Report")
                st.write(summary)
            except Exception as e:
                st.error(f"OpenAI API error: {e}")
else:
    st.info("Set your OpenAI API key in Streamlit secrets or environment variables to enable AI summary.")

