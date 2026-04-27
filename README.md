# REML - Real Estate ML

![Python](https://img.shields.io/badge/Python-3.12-blue.svg)
![Prefect](https://img.shields.io/badge/Prefect-3.x-cyan.svg)
![MLflow](https://img.shields.io/badge/MLflow-2.x-orange.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)
![Terraform](https://img.shields.io/badge/Terraform-1.7+-purple.svg)
![Yandex Cloud](https://img.shields.io/badge/Yandex%20Cloud-OK-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Development-yellow.svg)

MLOps pipeline for real estate investment ROI prediction

## Stack

- Cloud: Yandex Cloud (Terraform)
- Orchestration: Prefect
- Tracking: MLflow
- Inference: FastAPI + vLLM (GPU)
- Monitoring: Prometheus + Grafana

## Ingestion (CIAN-like historical backfill)

### 1. Initialize DB objects (schemas, tables, indexes, checkpoints)

```bash
export REML_DB_DSN='postgresql://user:pass@host:5432/reml_test'
python3 scripts/init_db.py
```

### 2. Required environment variables

```bash
export REML_DB_DSN='postgresql://user:pass@host:5432/reml_test'
export CIAN_LOGIN='your_login'
export CIAN_TOKEN='your_token'
# Optional:
export CIAN_ENDPOINT='https://rest-app.net/api-cian/ads'
export CIAN_TIMEOUT_SECONDS='30'
export CIAN_MAX_RETRIES='3'
```

### 3. Run historical backfill flow

```bash
python3 flows/historical_backfill.py \
  --schema sale \
  --start-date 2026-04-01 \
  --end-date 2026-04-27 \
  --window-days 1 \
  --daily-quota 10000 \
  --category-id 1 \
  --region-id 1
```

For rent use `--schema rent`. `deal_id` is derived automatically from schema:
- `sale -> 1`
- `rent -> 2`

### 4. Run tests

```bash
python3 -m pytest
```

### Security note

If API token was exposed in terminal/chat history, rotate it immediately and keep the new token only in secrets/environment variables.
