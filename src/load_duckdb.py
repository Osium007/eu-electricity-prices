import duckdb

DB = "data/electricity.duckdb"
PRICES_CSV = "data/raw/european_wholesale_electricity_price_data_monthly.csv"
RENEWABLES_CSV = "data/raw/owid_renewable_share.csv"

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
    WHERE "Price (EUR/MWhe)" IS NOT NULL
""")

# OWID mixes countries with aggregates (ASEAN, EU-27, World); the aggregates have no ISO3
# code, so filtering on Code IS NOT NULL drops them and keeps real countries only.
con.execute("DROP TABLE IF EXISTS renewables")
con.execute(f"""
    CREATE TABLE renewables AS
    SELECT
        "Entity"      AS country,
        "Code"        AS iso3,
        "Year"        AS year,
        "Renewables"  AS renewable_share_pct
    FROM read_csv_auto('{RENEWABLES_CSV}')
    WHERE "Code" IS NOT NULL
      AND "Code" != 'OWID_WRL'
      AND "Year" >= 2015
""")

print(con.sql("""
    SELECT 'prices' AS tbl, COUNT(*) AS rows, COUNT(DISTINCT iso3) AS countries FROM prices
    UNION ALL
    SELECT 'renewables', COUNT(*), COUNT(DISTINCT iso3) FROM renewables
"""))

con.close()
