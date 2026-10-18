import duckdb
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go


st.set_page_config(page_title="EU electricity prices", layout="wide")

DB = "data/electricity.duckdb"


@st.cache_data
def run_query(sql):
    con = duckdb.connect(DB, read_only=True)
    df = con.sql(sql).df()
    con.close()
    return df


st.title("EU electricity prices and the renewables transition")
st.write("Does a higher renewable share mean cheaper electricity, or just more volatile prices?")


c1, c2, c3, c4 = st.columns(4)
c1.metric("Renewables vs price", "−0.42", "correlation", delta_color="off")
c2.metric("Variance explained", "18%", "R² of the fit", delta_color="off")
c3.metric("Crisis peak (EUR/MWh)", "459", "Aug 2022", delta_color="off")
c4.metric("Latest (EUR/MWh)", "150", "+146% vs 2019–21", delta_color="inverse")

# Core finding: renewable share vs average price, one point per country
scatter = run_query("""
    WITH yearly AS (
        SELECT
            iso3,
            country,
            YEAR(date)                            AS year,
            AVG(price_eur_mwh)                    AS avg_price,
            100 * STDDEV_SAMP(price_eur_mwh) / AVG(price_eur_mwh) AS cv_pct
        FROM prices
        WHERE date >= DATE '2022-01-01'
        GROUP BY iso3, country, YEAR(date)
        HAVING COUNT(*) >= 10
    )
    SELECT
        y.country,
        y.iso3,
        ROUND(AVG(y.avg_price), 2)               AS avg_price,
        ROUND(AVG(y.cv_pct), 1)                  AS avg_cv_pct,
        ROUND(AVG(r.renewable_share_pct), 1)     AS avg_renewable_share_pct
    FROM yearly y
    JOIN renewables r ON r.iso3 = y.iso3 AND r.year = y.year
    GROUP BY y.country, y.iso3
    HAVING COUNT(*) >= 3
""")

fig = px.scatter(
    scatter,
    x="avg_renewable_share_pct",
    y="avg_price",
    size="avg_cv_pct",
    color="avg_cv_pct",
    color_continuous_scale="Viridis",
    trendline="ols",
    trendline_color_override="#e45756",
    hover_name="country",
    labels={
        "avg_renewable_share_pct": "Renewable share (%)",
        "avg_price": "Average wholesale price (EUR/MWh)",
        "avg_cv_pct": "Volatility (CV %)",
    },
)
r2 = px.get_trendline_results(fig).iloc[0]["px_fit_results"].rsquared
for t in fig.data:
    if t.mode == "lines":
        t.name = f"Linear trend (R² = {r2:.2f})"
        t.showlegend = True

fig.update_layout(
    coloraxis_colorbar_title_text="Volatility<br>(CV %)",
    showlegend=True,
    legend=dict(yanchor="top", y=0.98, xanchor="left", x=0.02, bgcolor="rgba(0,0,0,0)"),
)

st.plotly_chart(fig, use_container_width=True)

# Same country-level data on a map. The radio is a widget: picking a metric reruns the
# whole script, which recolours the map -> the Streamlit rerun model in action.
st.subheader("The same picture, geographically")
metric = st.radio(
    "Colour the map by",
    ["Renewable share", "Average price", "Volatility"],
    horizontal=True,
)
map_col = {
    "Renewable share": "avg_renewable_share_pct",
    "Average price": "avg_price",
    "Volatility": "avg_cv_pct",
}[metric]

fig_map = px.choropleth(
    scatter,
    locations="iso3",
    locationmode="ISO-3",
    color=map_col,
    scope="europe",
    color_continuous_scale="Viridis",
    hover_name="country",
    labels={
        "avg_renewable_share_pct": "Renewable share (%)",
        "avg_price": "Avg price (EUR/MWh)",
        "avg_cv_pct": "Volatility (CV %)",
    },
)
fig_map.update_geos(bgcolor="rgba(0,0,0,0)", lakecolor="rgba(0,0,0,0)",
                    landcolor="#222", showcountries=True, countrycolor="#444")
fig_map.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=500,
                      paper_bgcolor="rgba(0,0,0,0)")
st.plotly_chart(fig_map, use_container_width=True)

# The crisis over time: Europe-wide median price with a 25th–75th percentile band (query 6).
st.subheader("How the crisis moved prices")
st.write("Median monthly wholesale price across the 28 countries present in every month since 2019.")

ts = run_query("""
    WITH full_coverage AS (
        SELECT iso3 FROM prices
        WHERE date >= DATE '2019-01-01' AND date < date_trunc('month', current_date)
        GROUP BY iso3
        HAVING COUNT(*) = (SELECT COUNT(DISTINCT date) FROM prices
            WHERE date >= DATE '2019-01-01' AND date < date_trunc('month', current_date))
    )
    SELECT date,
           ROUND(MEDIAN(price_eur_mwh), 2)              AS median_price,
           ROUND(QUANTILE_CONT(price_eur_mwh, 0.25), 2) AS p25,
           ROUND(QUANTILE_CONT(price_eur_mwh, 0.75), 2) AS p75
    FROM prices
    WHERE iso3 IN (SELECT iso3 FROM full_coverage)
      AND date >= DATE '2019-01-01'
      AND date < date_trunc('month', current_date)
    GROUP BY date
    ORDER BY date
""")

fig2 = go.Figure()
# Upper bound, drawn invisibly so the next trace can fill down to the lower bound.
fig2.add_trace(go.Scatter(x=ts["date"], y=ts["p75"], line=dict(width=0),
                          hoverinfo="skip", showlegend=False))
# Lower bound, filling the gap up to the previous trace -> the shaded band.
fig2.add_trace(go.Scatter(x=ts["date"], y=ts["p25"], fill="tonexty",
                          fillcolor="rgba(74, 123, 167, 0.25)", line=dict(width=0),
                          name="25th–75th percentile"))
# Median line on top.
fig2.add_trace(go.Scatter(x=ts["date"], y=ts["median_price"], mode="lines",
                          line=dict(color="#4a7ba7", width=2), name="Median"))
fig2.update_layout(xaxis_title="Year", yaxis_title="Wholesale price (EUR/MWh)")

fig2.add_vrect(x0="2021-09-01", x1="2023-03-01",
               fillcolor="rgba(228, 87, 86, 0.08)", line_width=0)


fig2.add_annotation(
    x="2020-05-01", y=21.4,
    text="COVID demand collapse",
    showarrow=True, arrowhead=2, arrowcolor="#8a8a8a",
    ax=0, ay=-45, font=dict(color="#e8e8e8", size=12),
)
fig2.add_annotation(
    x="2022-08-01", y=459,
    text="Russia gas cutoff —<br>gas sets the power price",
    showarrow=True, arrowhead=2, arrowcolor="#8a8a8a",
    ax=90, ay=20, font=dict(color="#e8e8e8", size=12),
)
fig2.add_annotation(
    x="2026-09-01", y=150,
    text="Elevated, never<br>back to pre-crisis",
    showarrow=True, arrowhead=2, arrowcolor="#8a8a8a",
    ax=-15, ay=-55, font=dict(color="#e8e8e8", size=12),
)
st.plotly_chart(fig2, use_container_width=True)
