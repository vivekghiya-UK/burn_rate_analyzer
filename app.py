import streamlit as st
import pandas as pd
import openai
import os




# Get OpenAI API key from environment variables
openai.api_key = st.secrets["OPENAI_API_KEY"]

if not openai.api_key:
    st.error("OpenAI API key not found. Please set OPENAI_API_KEY in your environment or .env file.")
    st.stop()

st.title("Burn Rate & Runway Analyzer")

uploaded_file = st.file_uploader("Upload your Excel or CSV file", type=["xlsx", "csv"])

if uploaded_file:
    if uploaded_file.name.endswith('.xlsx'):
        # Read Excel sheets and ask user to select one
        xl = pd.ExcelFile(uploaded_file)
        sheet = st.selectbox("Select the Excel sheet to load", options=xl.sheet_names)
        df = xl.parse(sheet)
    else:
        df = pd.read_csv(uploaded_file)

    st.write("### Preview of your data")
    st.dataframe(df.head())

    # Select date column (only columns with date-like values or strings)
    date_col = st.selectbox("Select the Date column", options=df.columns)

    # Select cashflow/cash balance column (numeric)
    cashflow_col = st.selectbox("Select the Cashflow / Cash Balance column", options=df.columns, index =1)
    

    if date_col and cashflow_col:
        # Convert date column to datetime, coerce errors to NaT then drop
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        df = df.dropna(subset=[date_col])

        # Sort by date
        df = df.sort_values(date_col)

        st.write("### Cashflow over Time")
        st.line_chart(df.set_index(date_col)[cashflow_col])

        # Calculate burn rate (average change in cash balance)
        df['change'] = df[cashflow_col].diff()
        avg_burn_rate = df['change'].mean()

        st.markdown(f"**Average Burn Rate (avg change in cash):** {avg_burn_rate:.2f}")

        if avg_burn_rate < 0:
            current_cash = df[cashflow_col].iloc[-1]
            runway_days = current_cash / abs(avg_burn_rate)
            st.markdown(f"**Estimated Runway (days):** {runway_days:.0f}")
        else:
            st.markdown("Runway estimation not available (burn rate is positive or zero).")

        # AI summary generation
        if st.button("Generate AI Summary Report"):
            with st.spinner("Generating AI summary..."):
                prompt = (
                    f"Here is the cashflow data with average burn rate of {avg_burn_rate:.2f} "
                    f"and estimated runway {runway_days if avg_burn_rate < 0 else 'N/A'} days. "
                    "Provide a concise analysis and recommendations."
                )
                try:
                    response = openai.ChatCompletion.create(
                        model="gpt-3.5-turbo",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=300,
                        temperature=0.7,
                    )
                    summary = response['choices'][0]['message']['content']
                    st.markdown("### AI Summary Report")
                    st.write(summary)
                except Exception as e:
                    st.error(f"Failed to generate AI summary: {e}")
