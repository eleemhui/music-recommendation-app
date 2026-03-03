# Architectural Patterns

Patterns confirmed to appear in multiple files across the codebase.

---

## 1. Singleton via Module-Level Lazy Getter

Global `None`-initialized variable with a getter that initializes on first call. Used for expensive resources that should be shared across requests.

- `api/app/embedder.py:3-10` — `_model: SentenceTransformer | None`
- `api/app/db.py:5-12` — `_pool: SimpleConnectionPool | None`

Pattern shape:
```python
_resource: ResourceType | None = None

def get_resource() -> ResourceType:
    global _resource
    if _resource is None:
        _resource = ResourceType(...)
    return _resource
```

Follow this pattern for any new shared/expensive backend resource.

---

## 2. Service Layer Separation

HTTP concerns live in `main.py` only. Business logic lives in dedicated modules (`recommender.py`, `embedder.py`). Routes delegate immediately to service functions.

- `api/app/main.py:46-50` — thin route handler
- `api/app/recommender.py:6-39` — recommendation logic
- `api/app/embedder.py:13-21` — embedding logic

Routes do: validate input, call service, return result. Services do: orchestrate sub-services, query DB, transform data. No DB queries or ML calls belong in `main.py`.

---

## 3. Connection Borrow/Return (Resource Pool Pattern)

DB connections are borrowed from the pool with `get_conn()` and always returned via `finally`. Never hold connections across function boundaries.

- `api/app/recommender.py:11-26`
- `api/app/db.py` — `get_conn` / `put_conn`

```python
conn = get_conn()
try:
    with conn.cursor() as cur:
        cur.execute(...)
        results = cur.fetchall()
finally:
    put_conn(conn)
```

---

## 4. Two-Phase Initialization (Fast Path / Slow Path)

Check for precomputed artifacts first; fall back to on-the-fly computation only if absent. Log which path was taken.

- `api/app/seed.py:126-138` — dispatch logic
- `api/app/seed.py:60-87` — fast path (`.npz` files)
- `api/app/seed.py:94-119` — slow path (CSV + live embedding)

If adding new data sources or init steps, maintain this pattern: fast-path check → early return or fallback.

---

## 5. Batch Processing with Commit Checkpoints

Large data operations split into fixed-size batches; each batch commits independently to avoid large transactions and enable progress visibility.

- `api/app/seed.py:40-53` — `COMMIT_BATCH = 10_000`, loop with offset
- `api/app/embedder.py:18-21` — `batch_size=64` for model inference
- `api/app/precompute.py:69-91` — chunk-based NPZ splitting

Batch sizes are module-level constants (`COMMIT_BATCH`, `BATCH_SIZE`, `--chunk` CLI arg). Progress is logged after each batch.

---

## 6. Environment-Based Configuration

All runtime config (DB credentials, URLs) comes from environment variables. No hardcoded values in source. The `.env.example` is the canonical reference.

- `api/app/db.py:11` — `os.environ["DATABASE_URL"]` (fails fast if missing)
- `docker-compose.yml:21-22` — injects env vars into containers
- `.env.example` — documents all required variables

Use `os.environ["KEY"]` (not `.get()`) for required config so missing values fail at startup, not at request time.

---

## 7. Pydantic Models for All HTTP I/O

Every request body and response body is a Pydantic `BaseModel` with field constraints. FastAPI's `response_model` enforces the output shape.

- `api/app/main.py:29-38` — `RecommendRequest`, `Song`

```python
class RecommendRequest(BaseModel):
    phrase: str = Field(..., min_length=1, max_length=500)
    n: int = Field(default=5, ge=3, le=5)
```

Add new endpoints with a request model and a response model. Do not use raw `dict` or untyped `Any` for endpoint I/O.

---

## 8. Reverse Proxy for API Calls (Dev + Prod Parity)

Frontend never hardcodes the API host. In development, Vite proxies; in production, Nginx proxies. The frontend code calls relative paths only (`/recommend`, `/health`).

- `frontend/nginx.conf:7-12` — production proxy rules
- `frontend/vite.config.ts:6-10` — dev proxy config

When adding a new backend route that the frontend needs to call, add it to both `nginx.conf` and `vite.config.ts`.

---

## 9. React State Colocation

All async API state (`results`, `loading`, `error`) lives in `App.tsx`. Child components receive data and callbacks as props; they hold only local UI state (e.g., controlled input value).

- `frontend/src/App.tsx:7-10` — root state
- `frontend/src/components/SearchBar.tsx:9` — local form state only

Do not introduce a global state manager (Redux, Zustand) unless the component tree grows deep enough to require it. Prop-drilling is intentional at this scale.

---

## 10. Consistent Logging Format

All backend loggers use the same formatter: `%(asctime)s %(levelname)-8s %(message)s` with `datefmt="%Y/%m/%d %H:%M:%S"`.

- `api/app/main.py:8-17` — configures uvicorn loggers
- `api/app/seed.py:21-26` — module-level logger setup

New modules should create a module-level `log = logging.getLogger(__name__)` and apply the same formatter. Do not use `print()` in production code paths (it exists in `precompute.py` as that script runs outside Docker).
