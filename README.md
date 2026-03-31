# BoE Stats Pipeline

An end-to-end data engineering pipeline that extracts macroeconomic data from the **Bank of England Statistical Interactive Database (IADB)**, loads it into PostgreSQL, and transforms it using dbt.

Built as part of a DE portfolio targeting the London fintech market.

---

## Pipeline Architecture
```
BoE IADB API → Python ETL → PostgreSQL → dbt (staging + marts) → Airflow (orchestration)
```

---

## Data Sources

All series fetched from the Bank of England IADB API:

| Series | Code | Description |
|---|---|---|
| Base Rate | IUMABEDR | Official Bank Rate |
| GBP/USD | XUMAUSS | Sterling vs US Dollar |
| GBP/EUR | XUMAERS | Sterling vs Euro |
| Mortgage Rate | IUMBV34 | 2yr fixed 75% LTV |
| M4 Money Supply | LPMAUZI | Monthly net flow (£m) |

---

## Tech Stack

| Layer | Tool |
|---|---|
| Ingestion | Python 3.13, requests, pandas |
| Storage | PostgreSQL 15 |
| Transformation | dbt 1.11 |
| Orchestration | Apache Airflow 2.8 |
| Containerisation | Docker |

---

## Project Structure
```
boe-stats-pipeline/
├── airflow/dags/         # Airflow DAG
├── config/               # Settings and constants
├── data/raw/             # Raw CSVs from API
├── data/transformed/     # Transformed CSVs
├── docker/               # Docker Compose
├── etl/                  # Extract, transform, load scripts
├── boe_stats_pipeline/   # dbt project
│   ├── models/staging/   # Staging views
│   └── models/marts/     # Analytical marts
└── requirements.txt
```

---

## dbt Models

**Staging**
- `stg_base_rate` — rate direction, month-on-month change
- `stg_exchange_rates` — GBP/USD and GBP/EUR with monthly % change
- `stg_mortgage_rate` — 2yr fixed rate with month-on-month change
- `stg_m4_money_supply` — monthly net flow with change

**Marts**
- `mart_monetary_policy` — base rate + mortgage rate + M4 joined
- `mart_gbp_fx` — exchange rates + base rate joined

---

## dbt Tests

14/14 passing:
- `not_null` on all key columns
- `unique` on all date columns
- `accepted_values` on `rate_direction` (hike/cut/hold)

---

## Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Run ETL
python3 -m etl.extract
python3 -m etl.transform
python3 -m etl.load

# Run dbt
cd boe_stats_pipeline
dbt run
dbt test
```

---

## Author

**Daud Abdi** — Data Engineer, London  
[GitHub](https://github.com/Daudsaid) · [LinkedIn](https://linkedin.com/in/daudabdi0506) · [Portfolio](https://daud-abdi-portfolio-site.vercel.app/)
