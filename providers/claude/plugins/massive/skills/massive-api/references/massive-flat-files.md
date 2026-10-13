# Massive Flat Files: bulk data over S3

Bulk history (whole-market or long-range) is Flat Files, not paginated REST. Compressed CSVs over an **S3-compatible endpoint**. Requires **Starter tier or above** (Basic has none); history depth scales with the plan.

**Credentials are separate from the REST key.** Flat Files use a distinct **S3 Access Key + Secret** from the Dashboard, not `MASSIVE_API_KEY`.

- **Endpoint:** `https://files.massive.com`
- **Bucket:** `flatfiles`

## Contents

- Access methods (pick one)
- Path structure and format
- Per-asset-class coverage
- Publication delay

## Access methods (pick one)

A browser File Browser plus four S3-compatible clients, all using the same endpoint + your S3 keys.

**File Browser (dashboard)** - one-off downloads, no CLI. Nav drills asset class then dataset (only what your plan includes shows).

**AWS S3 CLI:**
```bash
aws configure set aws_access_key_id YOUR_S3_ACCESS_KEY_ID
aws configure set aws_secret_access_key YOUR_S3_SECRET_ACCESS_KEY
aws s3 ls s3://flatfiles/ --endpoint-url https://files.massive.com
aws s3 cp s3://flatfiles/us_stocks_sip/trades_v1/2025/11/2025-11-05.csv.gz . --endpoint-url https://files.massive.com
```

**Rclone:**
```bash
rclone config create s3massive s3 env_auth=false \
  access_key_id=YOUR_S3_ACCESS_KEY_ID secret_access_key=YOUR_S3_SECRET_ACCESS_KEY \
  endpoint=https://files.massive.com
rclone copy s3massive:flatfiles/us_stocks_sip/trades_v1/2025/11/2025-11-05.csv.gz .
```

**MinIO client (`mc`):**
```bash
mc alias set s3massive https://files.massive.com YOUR_S3_ACCESS_KEY_ID YOUR_S3_SECRET_ACCESS_KEY
mc cp s3massive/flatfiles/us_stocks_sip/trades_v1/2025/11/2025-11-05.csv.gz .
```

**Python (boto3)** - needs the endpoint and SigV4:
```python
import boto3
from botocore.config import Config
s3 = boto3.client("s3", endpoint_url="https://files.massive.com",
                  aws_access_key_id="...", aws_secret_access_key="...",
                  config=Config(signature_version="s3v4"))
s3.download_file("flatfiles", "us_stocks_sip/trades_v1/2025/11/2025-11-05.csv.gz", "./out.csv.gz")
```

## Path structure and format

Key pattern: `<asset_prefix>/<datatype>_v<N>/YYYY/MM/YYYY-MM-DD.csv.gz`.

- Asset prefixes: `us_stocks_sip`, `us_options_opra`, `us_indices`, `global_forex`, `global_crypto`. (Futures prefix: likely `us_futures`, unpublished - confirm in the File Browser.)
- Format: gzipped CSV, a consistent header row first. Timestamps (`window_start`) are Unix **nanoseconds** (see `massive-data-shapes`).

## Per-asset-class coverage

Not symmetric - know before you plan a pull:

- **Stocks, Options:** trades, quotes, minute aggs, day aggs (full set).
- **Crypto:** day/minute aggs, trades. **No quotes.**
- **Forex:** day/minute aggs, quotes. **No trades.**
- **Indices:** day/minute aggs, and tick values (no trades/quotes).
- **Futures:** trades, quotes, minute aggs, plus a **session-aggs** type, split per exchange (CME/CBOT/COMEX/NYMEX).

## Publication delay

Each trading day's files land the next morning ET (docs say ~11:00 AM ET; confirm current timing). Yesterday's file may not exist before then - a common "missing data" false alarm.
