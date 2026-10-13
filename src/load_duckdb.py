import duckdb

DB = "data/electricity.duckdb"
PRICES_CSV = "data/raw/european_wholesale_electricity_price_data_monthly.csv"

con = duckdb.connect(DB)

con.execute("DROP TABLE IF EXISTS prices")
con.execute(f"""
    CREATE TABLE prices AS
    SELECT
        "Country"            AS country,
        "ISO3 Code"          AS iso3,
        CAST("Date" AS DATE) AS date,
        "Price (EUR/MWhe)"   AS price_eur_mwh
    FROM read_csv_auto('{PRICES_CSV}')
""")

print(con.sql("SELECT COUNT(*) AS rows, COUNT(DISTINCT country) AS countries FROM prices"))

print(con.sql("""
    SELECT country, ROUND(AVG(price_eur_mwh), 2) AS avg_price
    FROM prices
    GROUP BY country
    ORDER BY avg_price DESC
    LIMIT 10
"""))

con.close()
