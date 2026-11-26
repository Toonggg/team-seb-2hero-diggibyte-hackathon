-- ============================================================================
-- Databricks SQL: SEB Location Google Reviews Sentiment Pipeline
-- ============================================================================
-- Upload `seb_locations.csv` and `seb_reviews.csv` to a Databricks Volume
-- (or create Delta tables via UI / Auto Loader), then run the queries below
-- to scale sentiment & topic classification using Databricks AI Functions.
-- ============================================================================

-- 1. Enrich each review with Databricks built-in multilingual AI sentiment + topic
CREATE OR REPLACE TABLE seb_reviews_enriched AS
SELECT
  place_id,
  location_name,
  address,
  author,
  CAST(publish_time AS TIMESTAMP) AS publish_time,
  language,
  CAST(review_rating AS INT) AS review_rating,
  review_text,
  ai_analyze_sentiment(review_text) AS dbx_sentiment,
  ai_classify(
    review_text,
    ARRAY(
      'Customer Service & Wait Times',
      'KYC / AML & Security Controls',
      'Cards & Disputes',
      'Loans, Mortgages & Pensions',
      'Digital & App',
      'Other'
    )
  ) AS review_topic
FROM seb_reviews_raw
WHERE review_text IS NOT NULL AND trim(review_text) != '';

-- 2. Branch-level KPI table: overall Google rating + per-review sentiment breakdown
CREATE OR REPLACE TABLE seb_location_sentiment_summary AS
SELECT
  l.place_id,
  l.location_name,
  l.address,
  l.latitude,
  l.longitude,
  l.google_avg_rating,
  l.google_total_reviews,
  COUNT(r.review_text) AS analyzed_reviews,
  ROUND(AVG(r.review_rating), 2) AS analyzed_avg_rating,
  SUM(CASE WHEN r.dbx_sentiment = 'positive' THEN 1 ELSE 0 END) AS positive_count,
  SUM(CASE WHEN r.dbx_sentiment = 'neutral'  THEN 1 ELSE 0 END) AS neutral_count,
  SUM(CASE WHEN r.dbx_sentiment = 'negative' THEN 1 ELSE 0 END) AS negative_count,
  ROUND(
    100.0 * SUM(CASE WHEN r.dbx_sentiment = 'positive' THEN 1 ELSE 0 END) / NULLIF(COUNT(r.review_text), 0),
    1
  ) AS positive_pct
FROM seb_locations_raw l
LEFT JOIN seb_reviews_enriched r
  ON l.place_id = r.place_id
GROUP BY
  l.place_id, l.location_name, l.address, l.latitude, l.longitude,
  l.google_avg_rating, l.google_total_reviews
ORDER BY l.google_avg_rating DESC;

-- 3. Top pain points (negative reviews by topic across all SEB locations)
SELECT
  review_topic,
  COUNT(*) AS negative_review_count,
  ROUND(AVG(review_rating), 2) AS avg_rating
FROM seb_reviews_enriched
WHERE dbx_sentiment = 'negative'
GROUP BY review_topic
ORDER BY negative_review_count DESC;
