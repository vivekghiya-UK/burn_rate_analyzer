import streamlit as st
import pandas as pd
from io import BytesIO
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.title("Burn Rate & Runway Analyzer with AI Summary")

st.markdown("""
**Instructions:**  
- Upload an Excel file with your financial plan.  
- Make sure it includes a date column and a cash balance column.  
- Select the correct sheet and columns below.  
- The app will plot cash balance over time, estimate runway, and generate an AI summary.
""")

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    processed_data = output.getvalue()
    return processed_data

# Sample data for download
sample_df = pd.DataFrame({
    "Date": pd.date_range(start="2025-01-01", periods=6, freq='M'),
    "Cash Balance": [100000, 85000, 70000, 55000, 40000, 25000]
})

st.download_button(
    label="Download Sample Excel File",
    data=to_excel(sample_df),
    file_name="sample_burn_rate_data.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

uploaded_file = st.file_uploader("Upload Excel file", type=["xls", "xlsx"])

if uploaded_file:
    # Load Excel file
    xls = pd.ExcelFile(uploaded_file)
    sheet_names = xls.sheet_names
    sheet = st.selectbox("Select sheet", sheet_names)

    df = pd.read_excel(xls, sheet_name=sheet)

    st.write("Preview of selected sheet:")
    st.dataframe(df.head())

    # Let user pick date and cashflow columns
    date_col = st.selectbox("Select Date column", options=df.columns)
    cashflow_col = st.selectbox("Select Cash balance column", options=df.columns, index=1)

    # Validate date column parsing
    try:
        df[date_col] = pd.to_datetime(df[date_col])
    except Exception:
        st.error(f"Could not parse '{date_col}' as dates. Please select a proper date column.")
        st.stop()

    # Sort by date just in case
    df = df.sort_values(by=date_col)

    # Plot cash balance over time
    st.line_chart(df.set_index(date_col)[cashflow_col])

    # Calculate average burn rate: avg change of cash balance per period (usually monthly)
    df['cash_diff'] = df[cashflow_col].diff()
    avg_burn_rate = df['cash_diff'].mean()

    st.markdown(f"**Average Burn Rate:** {avg_burn_rate:.2f} per period")

    if avg_burn_rate < 0:
        current_cash = df[cashflow_col].iloc[-1]
        runway_periods = current_cash / abs(avg_burn_rate)
        st.markdown(f"**Estimated Runway:** {runway_periods:.1f} periods")
    else:
        st.warning("Runway estimation not available (average burn rate is zero or positive).")

    # AI summary generation
    if st.button("Generate AI Summary Report"):
        sample_data = df[[date_col, cashflow_col]].tail(10).to_string(index=False)
        prompt = (
            f"Analyze the following cash balance data with dates:\n{sample_data}\n"
            "Please provide a concise financial summary including burn rate and runway insights."
        )

        with st.spinner("Generating AI summary..."):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a helpful financial assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.5,
                    max_tokens=300,
                )
                summary = response.choices[0].message.content.strip()
                st.markdown("### AI Summary Report")
                st.write(summary)
            except Exception as e:
                st.error(f"OpenAI API error: {e}")
