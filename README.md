```markdown
# TL Offline POS (Edge + Cloud + Demo UI)

Offline-first Point of Sale (PoS) system built for real stores: local checkout even without internet, reliable sync to cloud, inventory ledger, central reporting, per-device security with key rotation, rate limiting, and a Streamlit demo UI with role-based access.

---

## What’s in this repo?

This project has **three runnable apps**:

- **Edge** (`pos/apps/edge/app`)  
  Store/register-side API. Works offline. Handles products, carts, checkout, inventory, outbox, local event dispatch, and pushes events to cloud.

- **Cloud** (`pos/apps/cloud/app`)  
  Central ingest + storage (idempotent) + reporting + device management (admin endpoints), protected by per-device keys and rate limiting.

- **Demo UI (Streamlit)** (`pos/apps/demo_ui`)  
  A beautiful demo interface to explore all features:
  Products → Cart → Checkout → Local Events → Sync → Cloud Reports  
  Includes **Admin page** for device key management, protected by UI login + admin role.

---

## Architecture (high level)

```

Customer
↓
Edge (FastAPI + Postgres)
↓  (Outbox events created atomically during checkout)
Local Dispatch (modules; inventory ledger)
↓
Sync Push (/sync/push)
↓
Cloud Ingest (/ingest)  [idempotent + device auth + rate limits]
↓
Cloud Reports
↓
Streamlit Demo UI

```

---

## Tech stack

- Python (uv-based workflow)
- FastAPI (Edge & Cloud)
- PostgreSQL (Edge DB + Cloud DB)
- Streamlit (Demo UI)
- Outbox pattern + Idempotent ingest
- Inventory ledger (stock = sum of movements)
- Per-device keys + key rotation + ingest rate limiting
- Streamlit login + role-based admin access

---

## Prerequisites

- **Python 3.12+** recommended
- **uv** installed  
  - Install guide: https://github.com/astral-sh/uv
- **PostgreSQL 14+** running locally or on a server
- Windows PowerShell or Linux/macOS shell

> In PowerShell, prefer `Invoke-RestMethod` for API calls (instead of curl aliases).

---

## Repo layout

```

pos/
apps/
edge/
app/
api/
infra/
migrations/
modules/
main.py
.env
...
cloud/
app/
api/
infra/
migrations/
main.py
.env
...
demo_ui/
app.py
pages/
infra/
pyproject.toml
.env
.env.example

````

---

# Quickstart (Local)

## 1) Create databases

Create two databases:

- `pos_edge`
- `pos_cloud`

If you’re using psql as an admin user:

```sql
CREATE DATABASE pos_edge;
CREATE DATABASE pos_cloud;
````

> Note: On Windows, `CREATE DATABASE ...` must be run inside **psql**, not directly in PowerShell.

---

## 2) Configure Cloud

Go to Cloud app directory:

```powershell
cd pos\apps\cloud\app
```

Create/edit `.env`:

```env
POS_DB_DSN=postgresql://pos:pos@localhost:5432/pos_cloud

# Admin key for device management endpoints:
CLOUD_ADMIN_API_KEY=change-me-admin-long-random

# Rate limit per device (per minute):
CLOUD_RATE_LIMIT_PER_MIN=120
CLOUD_RATE_LIMIT_BURST=30
```

Install dependencies with uv (recommended):

```powershell
uv sync
```

If your project doesn’t have a lockfile yet, use:

```powershell
uv pip install -e .
```

Run Cloud:

```powershell
python .\main.py
```

Cloud runs on:

* [http://localhost:9000](http://localhost:9000)
* Swagger: [http://localhost:9000/docs](http://localhost:9000/docs)

Health checks:

```powershell
Invoke-RestMethod "http://localhost:9000/health"
Invoke-RestMethod "http://localhost:9000/health/db"
```

---

## 3) Configure Edge

Go to Edge app directory:

```powershell
cd pos\apps\edge\app
```

Create/edit `.env`:

```env
POS_DB_DSN=postgresql://pos:pos@localhost:5432/pos_edge

# Device identity for cloud ingest:
POS_DEVICE_ID=edge-001

# Cloud base URL:
POS_CLOUD_URL=http://localhost:9000

# Per-device key (set after device is created in Cloud):
POS_CLOUD_API_KEY=edge-secret-1
```

Install dependencies with uv:

```powershell
uv sync
```

(or `uv pip install -e .` if no lockfile)

Run Edge:

```powershell
python .\main.py
```

Edge runs on:

* [http://localhost:8000](http://localhost:8000)
* Swagger: [http://localhost:8000/docs](http://localhost:8000/docs)

Health checks:

```powershell
Invoke-RestMethod "http://localhost:8000/health"
Invoke-RestMethod "http://localhost:8000/health/db"
```

---

## 4) Create device in Cloud (required for sync)

Cloud ingest requires **per-device authentication**.

In PowerShell:

```powershell
$admin="change-me-admin-long-random"

Invoke-RestMethod -Method Post "http://localhost:9000/admin/devices/upsert" `
  -Headers @{ "X-Admin-Key" = $admin } `
  -ContentType "application/json" `
  -Body '{"device_id":"edge-001","api_key_current":"edge-secret-1","is_active":true}'
```

Now ensure Edge `.env` matches:

```env
POS_DEVICE_ID=edge-001
POS_CLOUD_API_KEY=edge-secret-1
```

Restart Edge after changing `.env` (Ctrl+C then run `python .\main.py`).

---

## 5) Configure and run Demo UI (Streamlit)

Go to:

```powershell
cd pos\apps\demo_ui
```

Copy `.env.example` → `.env` and edit:

```env
EDGE_URL=http://localhost:8000
CLOUD_URL=http://localhost:9000
CLOUD_ADMIN_API_KEY=change-me-admin-long-random

UI_AUTH_ENABLED=true

UI_ADMIN_USERNAME=admin
UI_ADMIN_PASSWORD=change-this-admin-password

UI_VIEWER_USERNAME=viewer
UI_VIEWER_PASSWORD=change-this-viewer-password
```

Install dependencies:

```powershell
uv sync
```

Run UI:

```powershell
streamlit run .\app.py
```

Open:

* [http://localhost:8501](http://localhost:8501)

Login:

* Viewer: can use Products/Cart/Checkout/Sync/Reports
* Admin: also can access **Admin (Cloud) — Devices**

---

# Demo flow (end-to-end)

## A) Create product (Edge)

```powershell
Invoke-RestMethod -Method Post "http://localhost:8000/products" `
  -ContentType "application/json" `
  -Body '{"barcode":"123456","name":"Tea","price_cents":250,"currency":"PKR","is_active":true}'
```

## B) Create cart → add item → checkout

```powershell
$cart = (Invoke-RestMethod -Method Post "http://localhost:8000/carts").id

Invoke-RestMethod -Method Post "http://localhost:8000/carts/$cart/items" `
  -ContentType "application/json" `
  -Body '{"barcode":"123456","qty":2}' | Out-Null

Invoke-RestMethod -Method Post "http://localhost:8000/carts/$cart/checkout" | ConvertTo-Json -Depth 10
```

## C) Dispatch local events (inventory module)

```powershell
Invoke-RestMethod -Method Post "http://localhost:8000/outbox/dispatch?limit=50" | ConvertTo-Json -Depth 10
```

## D) Sync push to Cloud

```powershell
Invoke-RestMethod -Method Post "http://localhost:8000/sync/push?limit=50" | ConvertTo-Json -Depth 10
```

## E) Verify Cloud received events

```powershell
Invoke-RestMethod "http://localhost:9000/received/recent?limit=10" | ConvertTo-Json -Depth 10
```

## F) Cloud reports

```powershell
Invoke-RestMethod "http://localhost:9000/reports/orders/recent?limit=10" | ConvertTo-Json -Depth 10
Invoke-RestMethod "http://localhost:9000/reports/sales/daily?days=7" | ConvertTo-Json -Depth 10
Invoke-RestMethod "http://localhost:9000/reports/sales/products?limit=10" | ConvertTo-Json -Depth 10
```

---

# Inventory (ledger model)

Inventory is stored as **movements** (audit-friendly):

* Receive stock: positive movement
* Sale: negative movement (created on `order.paid` during local dispatch)
* Stock = SUM(qty_delta)

Receive stock:

```powershell
Invoke-RestMethod -Method Post "http://localhost:8000/inventory/receive" `
  -ContentType "application/json" `
  -Body '{"barcode":"123456","qty":10}' | ConvertTo-Json -Depth 10
```

Check stock:

```powershell
Invoke-RestMethod "http://localhost:8000/inventory/stock/123456" | ConvertTo-Json -Depth 10
```

---

# Device security (sell-ready)

## Per-device keys

Cloud requires these headers on ingest:

* `X-Device-Id`
* `X-API-Key`

Edge sends them automatically during `/sync/push`.

## Key rotation (zero downtime)

Using the Streamlit **Admin (Cloud) — Devices** page:

1. Rotate key (sets `api_key_next`, optionally expire current later)
2. Update Edge `.env` to new key and restart Edge
3. Verify `/sync/push` works
4. Promote next → current

This allows safe rotation without breaking stores.

## Rate limiting

Cloud enforces per-device limits on ingest:

* `CLOUD_RATE_LIMIT_PER_MIN`
* `CLOUD_RATE_LIMIT_BURST`

If exceeded, Cloud returns **429**.

---

# Troubleshooting

## “Not Found” on an endpoint

* Make sure you restarted the correct service after code changes.
* Check Swagger:

  * Edge: [http://localhost:8000/docs](http://localhost:8000/docs)
  * Cloud: [http://localhost:9000/docs](http://localhost:9000/docs)

## Edge cannot push (sync issues)

Check Edge status:

```powershell
Invoke-RestMethod "http://localhost:8000/sync/status" | ConvertTo-Json -Depth 10
```

Common causes:

* 401: device missing/wrong key
* 429: rate limit exceeded
* connection errors: wrong `POS_CLOUD_URL` or Cloud not running

## Cloud device admin fails with 401

Your request must include:

* `X-Admin-Key` matching `CLOUD_ADMIN_API_KEY`

---

# Production deployment notes

* Run Edge per store/register device (local Postgres recommended)
* Run Cloud on a server with HTTPS (reverse proxy: nginx/caddy)
* Keep `CLOUD_ADMIN_API_KEY` secret
* Put Streamlit behind additional protection if public (reverse proxy auth / SSO)
* Current ingest rate limiter is **in-memory** (great for single instance)

  * For multi-instance cloud scaling, switch limiter storage to Redis.

---

# License

Add your license here.

---

# Support / Maintenance

Recommended ops checks:

* Edge: `/health`, `/health/db`, `/sync/status`
* Cloud: `/health`, `/health/db`, `/received/recent`, reports endpoints
* Use Streamlit dashboard to demo full workflow and manage devices safely

```