# TL Offline POS — Architecture

This document describes the architecture of the TL Offline POS system as implemented in this project (Edge + Cloud + Demo UI), including data flows, reliability patterns, security model, and operational workflows.

---

## 1) System Goals

### Primary goals
- **Offline-first operation** at the store/register (Edge): sales must continue even without internet.
- **No lost sales**: every successful checkout must produce a durable, syncable event.
- **Safe retries**: network failures must not create duplicate records in Cloud.
- **Multi-device ready**: multiple store devices can sync independently.
- **Sell-ready security**: per-device credentials, key rotation, and rate limiting.

### Secondary goals
- Simple, readable Python (minimal OOP).
- Fast and reliable APIs (transactional DB usage and deterministic flows).
- Demo-ready UI that exposes all features end-to-end.

---

## 2) Components

### 2.1 Edge Service (Store-side)
**Purpose:** Offline-first POS API that owns the transactional workflow for carts and checkout, produces outbox events, optionally runs local module processing (inventory), and syncs to Cloud.

**Runs on:** `http://localhost:8000` (typical local setup)

**Responsibilities**
- Products CRUD (barcode-based)
- Cart lifecycle (create, add/remove lines, totals)
- Checkout (creates Order + Order Lines + Outbox event atomically)
- Inventory ledger (receive stock; deduct stock via local event dispatch)
- Outbox (queue of unsent events)
- Local event dispatch (idempotent module processing)
- Sync push (send outbox events to Cloud ingest)

---

### 2.2 Cloud Service (Central)
**Purpose:** Receives events from Edge, stores them idempotently, exposes reporting APIs, and provides admin device management.

**Runs on:** `http://localhost:9000` (typical local setup)

**Responsibilities**
- Idempotent ingest of Edge events
- Device authentication (per-device keys)
- Key rotation support (current + next key with timing rules)
- Rate limiting per device on ingest
- Reporting endpoints (recent orders, daily totals, product sales)
- Admin endpoints for device management (protected by admin key)

---

### 2.3 Demo UI (Streamlit)
**Purpose:** A demo-ready UI to explore all features end-to-end and perform admin device operations safely.

**Runs on:** `http://localhost:8501` (default Streamlit)

**Pages**
- Products: create/update + lookup by barcode
- Cart: create cart + add/remove by barcode + live totals
- Checkout: checkout selected cart + show order/outbox event
- Local Events: dispatch + module-events log
- Sync: status + push to cloud
- Cloud Reports: recent orders + daily sales + product sales
- Admin (Cloud): device upsert + rotate + promote + revoke/enable

**Access control**
- Streamlit login enabled with **roles**:
  - `viewer`: operational pages only
  - `admin`: operational pages + admin device page
- Admin page is blocked unless role is admin.

---

## 3) Core Patterns

### 3.1 Outbox Pattern (Edge)
**Why:** Guarantee durable event creation at the same time as business transaction (checkout).

**Key property**
- Checkout writes the Order + Lines **and** writes an Outbox event **in a single DB transaction**.
- If checkout succeeds, the outbox event exists.
- If checkout fails/rolls back, no outbox event exists.

This enables “never lose a sale” and safe sync later.

---

### 3.2 Idempotent Ingest (Cloud)
**Why:** Edge may retry the same events due to timeouts, network drops, or reconnects.

**Approach**
- Cloud stores incoming events using a uniqueness constraint on:
  - `(device_id, outbox_event_id)`
- Ingest inserts with conflict handling so re-sends do not create duplicates.
- Cloud returns acknowledgements for received events so Edge can mark them as sent.

Outcome: “at-least-once delivery” from Edge becomes “effectively-once storage” in Cloud.

---

### 3.3 Local Module Dispatch (Edge)
**Why:** Some side-effects (like inventory deduction) should be applied locally and safely, and should be retryable.

**Approach**
- Edge has a dispatch endpoint that processes pending outbox events into “module events”.
- Each module/event combination is processed idempotently (i.e., no double stock deduction).
- Inventory module listens to `order.paid` and inserts negative inventory movements.

---

### 3.4 Inventory Ledger Model (Edge)
**Why:** Ledger model provides auditability and avoids race conditions of mutable counters.

**Rules**
- Stock is not stored as a single mutable number.
- Every change is a row in `inventory_movements` with `qty_delta`.
- Current stock is computed as `SUM(qty_delta)` per product.

---

## 4) Data Model (Conceptual)

This section describes the conceptual tables/entities; exact column lists are defined in migrations in each app.

### 4.1 Edge (conceptual)
- **products**
  - barcode, name, price_cents, currency, is_active, timestamps
- **carts**
  - status (`open` etc.), timestamps
- **cart_items**
  - cart_id, product_id, qty, computed totals via queries
- **orders**
  - cart_id, status (`paid`), totals (subtotal/tax/total), currency, created_at
- **order_lines**
  - barcode, name, qty, unit_price_cents, line_total_cents
- **outbox_events**
  - event_type (e.g., `order.paid`)
  - aggregate_type (`order`)
  - aggregate_id (order id)
  - payload_json (includes totals; later includes `lines[]` for reporting)
  - sent_at (null until acknowledged by Cloud)
- **module_events** (or equivalent)
  - records module processing for idempotency
- **inventory_movements**
  - product_id, reason, qty_delta, references, created_at

### 4.2 Cloud (conceptual)
- **cloud_inbox_events**
  - device_id
  - outbox_event_id
  - event_type, aggregate_type, aggregate_id
  - payload_json
  - created_at (from Edge), received_at (Cloud time)
  - uniqueness on `(device_id, outbox_event_id)`
- **devices**
  - device_id (primary key)
  - is_active
  - api_key_current
  - api_key_next (optional during rotation)
  - next_valid_from (when next becomes valid)
  - current_valid_until (optional expiry to force cutover)
  - timestamps

---

## 5) API Surface (Key Endpoints)

### 5.1 Edge
**Health**
- `GET /health`
- `GET /health/db`

**Products**
- `POST /products` (create or update by barcode)
- `GET /products/{barcode}` (lookup)

**Carts**
- `POST /carts` (create)
- `GET /carts/{cart_id}` (cart + items + totals)
- `POST /carts/{cart_id}/items` (add/increase qty by barcode)
- `POST /carts/{cart_id}/items/remove` (remove/decrease qty by barcode)

**Checkout**
- `POST /carts/{cart_id}/checkout`
  - returns order, lines, and outbox event created
  - cart becomes not-open after checkout

**Local Events**
- `POST /outbox/dispatch?limit=N` (process pending events into modules; idempotent)
- `GET /module-events/recent?limit=N` (module processing log)

**Inventory**
- `POST /inventory/receive` (manual stock receive)
- `GET /inventory/stock/{barcode}` (stock view)

**Sync**
- `GET /sync/status` (unsent_count, last_push_at, last_error)
- `POST /sync/push?limit=N` (send to Cloud ingest, mark acked sent)

---

### 5.2 Cloud
**Health**
- `GET /health`
- `GET /health/db`

**Ingest**
- `POST /ingest`
  - **Requires headers**:
    - `X-Device-Id: <device_id>`
    - `X-API-Key: <device_api_key>`
  - Enforces:
    - device exists + active
    - key valid (current or next depending on timing)
    - rate limiting
    - idempotent storage by (device_id, outbox_event_id)

**Received debug**
- `GET /received/recent?limit=N` (recently received events)

**Reports**
- `GET /reports/orders/recent?limit=N`
- `GET /reports/sales/daily?days=N`
- `GET /reports/sales/products?limit=N`
  - product sales uses `payload.lines[]` present in `order.paid` payload

**Admin device management**
- Requires header: `X-Admin-Key: <CLOUD_ADMIN_API_KEY>`
- `POST /admin/devices/upsert` (create/update device, set current key, active flag)
- `POST /admin/devices/{device_id}/rotate` (set next key + schedule/expiry rules)
- `POST /admin/devices/{device_id}/promote` (next → current, clears rotation fields)

---

## 6) Security Model

### 6.1 Per-device keys
- Each Edge device has a unique `device_id` and `api_key`.
- Cloud authenticates ingest requests using:
  - `X-Device-Id`
  - `X-API-Key`

Advantages:
- Device isolation: compromise of one key affects only one device.
- Easy revocation: disable device in Cloud.

---

### 6.2 Key rotation (zero downtime)
Cloud supports two keys simultaneously:
- `api_key_current` (existing)
- `api_key_next` (new key for rotation window)

Rotation sequence:
1) Admin sets `api_key_next` and scheduling:
   - `next_valid_from` (when the next key becomes valid)
   - optional `current_valid_until` (when current key expires)
2) Update Edge to new key
3) Verify sync works
4) Promote next → current

---

### 6.3 Rate limiting on ingest
Cloud rate limits **per device_id** to protect:
- cloud stability
- DB performance
- abuse and buggy retry loops

Implementation in this project is an in-memory limiter suitable for single-instance Cloud.
(For multi-instance horizontal scaling, replace with shared storage like Redis.)

---

### 6.4 Streamlit UI access control
The Streamlit app includes:
- Login gate (enabled via env setting)
- Roles:
  - `viewer`
  - `admin`
- Admin-only access to device management page.

This prevents accidental exposure of device key management in demos and hosted environments.

---

## 7) Operational Flows

### 7.1 Store sale (offline-capable)
1) Product exists locally on Edge
2) Create cart
3) Add items by barcode
4) Checkout:
   - writes order + lines + outbox event atomically
5) (Optional) local dispatch:
   - inventory module consumes `order.paid` and inserts stock movements

Internet not required up to this point.

---

### 7.2 Sync to Cloud (when internet is available)
1) Edge calls `/sync/push`
2) Edge sends unsent outbox events to Cloud `/ingest` with headers:
   - `X-Device-Id`
   - `X-API-Key`
3) Cloud ingests idempotently and returns acked ids
4) Edge marks those outbox rows as sent

---

### 7.3 Reporting
Cloud stores events and computes:
- recent orders
- daily sales totals
- product sales totals (using payload lines)

Streamlit reports page calls Cloud report endpoints.

---

### 7.4 Device onboarding & management
Admin can:
- upsert device with current key
- rotate keys
- promote key after verification
- revoke/enable device

This can be done via:
- Cloud admin endpoints
- Streamlit Admin (Cloud) page (admin role required)

---

## 8) Deployment Topologies

### 8.1 Local demo (single machine)
- Edge + Postgres (pos_edge)
- Cloud + Postgres (pos_cloud)
- Streamlit UI

All on localhost.

### 8.2 Store deployment (real world)
- Edge runs on each register/store device (local DB)
- Cloud runs on a hosted server
- Edge syncs to Cloud when online
- Streamlit UI optionally hosted for operations, behind access control

---

## 9) Key Properties Achieved (from verified runs)
- Checkout produces `order.paid` and blocks modifications after checkout (“cart is not open”).
- Sync push acknowledges events and Cloud stores them.
- Cloud reporting works and aggregates consistent totals over time.
- Inventory ledger updates correctly based on local dispatch and remains idempotent under repeated dispatch calls.
- Device authentication works with per-device keys, and rotation can be performed without downtime.
- Streamlit UI is demo-ready and admin device management is protected by login and admin role.

---

## 10) Future Hardening Notes (not required for current demo)
- Replace in-memory rate limiting with Redis for multi-instance Cloud.
- Add connection pooling to reduce DB overhead.
- Add background sync worker on Edge for automated periodic push.
- Add receipt/invoice numbering (per device/day).
- Extend tax and multi-currency enforcement rules.

---