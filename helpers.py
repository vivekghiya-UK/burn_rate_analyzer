import pandas as pd
import openai
import os

from dotenv import load_dotenv
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def calculate_burn_and_runway(df):
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date")

    df["Monthly Change"] = df["Cash Balance"].diff()
    recent_burn = df["Monthly Change"].dropna().tail(3).mean() * -1  # Burn is negative change
    current_cash = df["Cash Balance"].iloc[-1]
    runway = current_cash / recent_burn if recent_burn > 0 else float("inf")

    return recent_burn, runway

def generate_summary(df, burn, runway):
    openai.api_key = os.getenv("OPENAI_API_KEY")

    latest_date = df["Date"].max().strftime("%B %Y")
    prompt = (
        f"The company has a current cash balance of £{df['Cash Balance'].iloc[-1]:,.0f} as of {latest_date}.\n"
        f"The average burn rate over the last 3 months is £{burn:,.0f} per month.\n"
        f"The estimated runway is {runway:.1f} months.\n\n"
        "Write a short financial summary that could go into a board report."
    )

    response = openai.ChatCompletion.create(
    model="gpt-3.5-turbo",  # ← changed from "gpt-4"
    messages=[
        {"role": "system", "content": "You are a helpful financial analyst."},
        {"role": "user", "content": prompt}
    ],
    temperature=0.3
)

    return response['choices'][0]['message']['content'].strip()
