# EU Electricity Prices & the Renewables Transition

Does a higher renewable share mean cheaper electricity, or just more volatile prices?

This project takes EU day-ahead wholesale electricity prices since 2022 and checks them
against each country's renewable generation share. DuckDB and pandas for the pipeline,
a Streamlit dashboard on top, and a short-term price forecast at the end.

Work in progress.

## Data

Wholesale prices: Ember, European wholesale electricity price data.
Renewable generation share: Ember / Our World in Data.

Worth stating up front: these are day-ahead wholesale prices, what generators get paid on
the spot market. They are not retail prices. A household bill adds taxes, network charges
and levies on top, so the two move differently.

## Stack

Python, DuckDB, pandas, Streamlit, plotly, statsmodels.
