-- EU wholesale electricity prices vs. renewable generation share.
-- Tables are built by src/load_duckdb.py from the CSVs in data/raw/.
--
-- A note that shapes most of what follows: countries entered the Ember price dataset at
-- different times. Albania has four months, Austria has eleven years. Any query that
-- ranks or compares countries has to guard against that, or short-coverage countries
-- land at the top purely because their few months happen to be recent and expensive.


-- 1. Monthly price series per country.
--    The base series behind the dashboard's price-over-time view.
SELECT
    country,
    iso3,
    date,
    price_eur_mwh
FROM prices
ORDER BY country, date;


-- 2. Price level and volatility per country per year.
--    Volatility is the standard deviation of monthly prices within the year. Years with
--    fewer than 10 of 12 months are dropped: a spread measured over three months is not
--    comparable to one measured over twelve.
SELECT
    country,
    iso3,
    YEAR(date)                            AS year,
    COUNT(*)                              AS months_observed,
    ROUND(AVG(price_eur_mwh), 2)          AS avg_price,
    ROUND(STDDEV_SAMP(price_eur_mwh), 2)  AS price_stddev,
    ROUND(100 * STDDEV_SAMP(price_eur_mwh) / AVG(price_eur_mwh), 1) AS cv_pct
FROM prices
GROUP BY country, iso3, YEAR(date)
HAVING COUNT(*) >= 10
ORDER BY year, price_stddev DESC;


-- 3. Renewable share per country per year, limited to countries we have prices for.
SELECT
    r.country,
    r.iso3,
    r.year,
    ROUND(r.renewable_share_pct, 1) AS renewable_share_pct
FROM renewables r
WHERE r.iso3 IN (SELECT DISTINCT iso3 FROM prices)
ORDER BY r.country, r.year;


-- 4. The core question, one row per country-year: does a higher renewable share go with
--    a lower price, or just a more volatile one?
--
--    cv_pct (coefficient of variation) is the volatility measure to compare across
--    countries, not raw stddev. A country averaging 200 EUR/MWh will show a bigger
--    absolute spread than one averaging 50 simply because it is scaled up. Dividing by
--    the mean removes that and leaves the relative swing.
WITH yearly_price AS (
    SELECT
        iso3,
        country,
        YEAR(date)                            AS year,
        ROUND(AVG(price_eur_mwh), 2)          AS avg_price,
        ROUND(100 * STDDEV_SAMP(price_eur_mwh) / AVG(price_eur_mwh), 1) AS cv_pct
    FROM prices
    GROUP BY iso3, country, YEAR(date)
    HAVING COUNT(*) >= 10
)
SELECT
    p.country,
    p.iso3,
    p.year,
    p.avg_price,
    p.cv_pct,
    ROUND(r.renewable_share_pct, 1) AS renewable_share_pct
FROM yearly_price p
JOIN renewables r
  ON r.iso3 = p.iso3
 AND r.year = p.year
ORDER BY p.year, p.country;


-- 5. Country-level summary for the dashboard scatter, 2022 onward.
--    One point per country. Countries need at least 3 complete years in the window so a
--    single unusual year cannot define them.
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
    COUNT(*)                        AS years_observed,
    ROUND(AVG(y.avg_price), 2)      AS avg_price,
    ROUND(AVG(y.cv_pct), 1)         AS avg_cv_pct,
    ROUND(AVG(r.renewable_share_pct), 1) AS avg_renewable_share_pct
FROM yearly y
JOIN renewables r
  ON r.iso3 = y.iso3
 AND r.year = y.year
GROUP BY y.country, y.iso3
HAVING COUNT(*) >= 3
ORDER BY avg_renewable_share_pct DESC;


-- 6. How the crisis moved prices: European median monthly price over time.
--    Median rather than mean, so one extreme country does not drag the line. Restricted
--    to countries present across the whole window, so the line reflects price movement
--    rather than changes in which countries are being averaged.
--
--    The current calendar month is excluded. Ember carries an average for the in-progress
--    month built from however many days have settled so far, so that point is a partial
--    month and would show as a provisional spike or dip next to the finished months.
WITH full_coverage AS (
    SELECT iso3
    FROM prices
    WHERE date >= DATE '2019-01-01'
      AND date < date_trunc('month', current_date)
    GROUP BY iso3
    HAVING COUNT(*) = (
        SELECT COUNT(DISTINCT date) FROM prices
        WHERE date >= DATE '2019-01-01'
          AND date < date_trunc('month', current_date)
    )
)
SELECT
    date,
    COUNT(*)                                             AS countries,
    ROUND(MEDIAN(price_eur_mwh), 2)                      AS median_price,
    ROUND(QUANTILE_CONT(price_eur_mwh, 0.25), 2)         AS p25,
    ROUND(QUANTILE_CONT(price_eur_mwh, 0.75), 2)         AS p75
FROM prices
WHERE iso3 IN (SELECT iso3 FROM full_coverage)
  AND date >= DATE '2019-01-01'
  AND date < date_trunc('month', current_date)
GROUP BY date
ORDER BY date;
