# Databricks Notebooks & Scripts

Ready-to-import Databricks notebooks (standard `# Databricks notebook source` format — import via **Databricks Git Folders / Repos** or paste cell-by-cell into a Serverless Notebook).

## Files

- `generate_synthetic_seb_data.py` — Uses `dbldatagen` on Spark to generate 100k–1M+ synthetic SEB Kort customer-service conversations matching the hackathon schema (`private_cardholder`, `corporate_cardholder`, `corporate_administrator`, W37–W48, CSAT, wait times, escalations) and saves them to Unity Catalog.
- `transcribe_audio_notebook.py` — Transcribes the `.wav` voice calls from a Unity Catalog Volume with `faster-whisper`, then runs Databricks `ai_analyze_sentiment()`, `ai_classify()`, and `ai_summarize()`.
