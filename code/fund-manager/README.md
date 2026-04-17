# Fund Manager

Local trading dashboard — Go backend + Next.js frontend + SQLite + Redis.

## Dev

```bash
# Backend
cd backend && make run
# → http://127.0.0.1:8787

# Frontend (separate terminal)
cd frontend && npm run dev
# → http://127.0.0.1:3000
```

## Env

Reads `/home/lazywork/workspace/.env.local`. Required:
- `REDIS_HOST` (default: 127.0.0.1)
- `REDIS_PORT` (default: 6379)
- `REDIS_DB` (default: 0)

Optional:
- `FUND_API_PORT` (default: 8787)
- `FUND_DB_PATH` (default: ../data/fund.db)
- `FUND_API_URL` (used by Python client, default: http://127.0.0.1:8787/api/v1)

## Data

SQLite at `data/fund.db`. Migrations auto-apply on backend boot.

## Python client

```python
from tools.fund_api import api
api.get_holdings(date='2026-04-17')
api.post_signal({...})
```
