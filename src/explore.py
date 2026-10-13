import pandas as pd

PRICES = "data/raw/european_wholesale_electricity_price_data_monthly.csv"

df = pd.read_csv(PRICES, parse_dates=["Date"])

print("--- head ---")
print(df.head())

print("\n--- info ---")
df.info()

print("\n--- countries ---")
print(f"{df['Country'].nunique()} countries")
print(sorted(df["Country"].unique()))

print("\n--- date range ---")
print(f"{df['Date'].min().date()} to {df['Date'].max().date()}")

print("\n--- price ---")
print(df["Price (EUR/MWhe)"].describe())

print("\n--- missing ---")
print(df.isna().sum())
