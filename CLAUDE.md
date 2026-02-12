# CLAUDE.md

## Project Overview

Educational e-commerce microservices demo implementing Saga, CQRS, Event Sourcing, and BFF patterns. The project is an order fulfillment system with inventory management, written primarily in Japanese.

**Stack**: Python 3.12 / FastAPI 0.115 (backend), React 18 (frontend), PostgreSQL 16 (databases), Redis 7 (Pub/Sub messaging), Docker Compose (orchestration).

## Architecture

```
Frontend (React :3000)
    │
    ▼
BFF Gateway (:8000)  ── aggregates all backend services
    │
    ├── Saga Orchestrator (:8003)
    │       ├── Order Service (:8001)  [CQRS + Event Sourcing, own PostgreSQL :5432]
    │       └── Inventory Service (:8002)  [CQRS + Event Sourcing, own PostgreSQL :5433]
    │
    └── Marketing Service (:8004)  [Read-only projections, own PostgreSQL :5434]
                │
                └── subscribes to Redis Pub/Sub "order_events" channel
```

Each service has its own database (database-per-service pattern). Services communicate via HTTP (synchronous, orchestrated by Saga) and Redis Pub/Sub (asynchronous events to Marketing).

## Repository Structure

```
├── services/
│   ├── order/app/        # CQRS + Event Sourcing for orders
│   │   ├── main.py       # FastAPI routes (commands + queries + events)
│   │   ├── commands.py   # Write-side: create_order, confirm_order, cancel_order
│   │   ├── queries.py    # Read-side: list_orders, get_order
│   │   ├── aggregate.py  # OrderAggregate - state from event replay
│   │   ├── event_store.py # append_event, load_events
│   │   └── events.py     # Event type definitions
│   ├── inventory/app/    # CQRS + Event Sourcing for inventory (parallel structure)
│   ├── saga/app/         # Saga orchestrator
│   │   ├── main.py       # POST /saga/place-order
│   │   └── orchestrator.py # OrderSagaOrchestrator (create→reserve→confirm/cancel)
│   ├── bff/app/          # Backend for Frontend - API gateway
│   │   └── main.py       # Aggregates all services, serves frontend
│   └── marketing/app/    # CQRS read-side projection (no commands)
│       ├── main.py       # Read-only query endpoints
│       ├── subscriber.py # Redis Pub/Sub listener (background task)
│       ├── projections.py # Event-to-read-model handlers
│       └── queries.py    # Marketing analytics queries
├── frontend/src/
│   ├── App.js            # Main React app with tab navigation
│   └── components/       # ProductList, OrderForm, OrderHistory, EventLog, SagaLog, MarketingDashboard
├── db/init/
│   ├── order.sql         # event_store + orders_read_model tables
│   ├── inventory.sql     # event_store + inventory_read_model + seed data
│   └── marketing.sql     # Projection tables (snapshots, summaries, daily stats)
├── docker-compose.yml    # Full stack: 3 DBs + Redis + 5 services + frontend
└── .github/workflows/ci.yml
```

## Development Commands

### Start the full stack
```bash
docker compose up --build
```

### Lint Python services (CI uses Ruff)
```bash
# Lint check
ruff check services/order/
ruff check services/inventory/
ruff check services/saga/
ruff check services/bff/

# Format check
ruff format --check services/order/

# Auto-fix lint issues
ruff check --fix services/order/

# Auto-format
ruff format services/order/
```

Note: The marketing service is not included in CI lint checks. Only `order`, `inventory`, `saga`, and `bff` are linted.

### Build frontend
```bash
cd frontend && npm install && npm run build
```

### Verify Docker images build
```bash
docker compose build
```

## CI Pipeline

GitHub Actions (`.github/workflows/ci.yml`) runs on push/PR to `main`:

1. **backend-lint** - Runs `ruff check` and `ruff format --check` on each Python service (order, inventory, saga, bff) with Python 3.12
2. **frontend-build** - `npm install` + `npm run build` with Node 20
3. **docker-build** - `docker compose build` (depends on lint + frontend passing)

## Key Patterns and Conventions

### Event Sourcing
- All state changes in Order and Inventory services are stored as immutable events in an `event_store` table
- Aggregates are reconstructed by replaying events via `from_events()` class method
- Optimistic concurrency via `UNIQUE(aggregate_id, version)` constraint
- Events published to Redis Pub/Sub after persistence

### CQRS
- Each service separates commands (writes) from queries (reads)
- Write operations go through `commands.py` → event store + read model update
- Read operations go through `queries.py` → denormalized read model
- Marketing service is a pure read-side projection with no command endpoints

### Saga Orchestration
- The Saga service orchestrates the order placement flow:
  1. CreateOrder → Order Service
  2. ReserveInventory → Inventory Service
  3. On success: ConfirmOrder / On failure: CancelOrder (compensation)
- Uses httpx.AsyncClient for synchronous HTTP calls between services
- Maintains a saga_log tracking each step's status

### BFF (Backend for Frontend)
- Single entry point for the React frontend
- Aggregates data from all backend services
- Uses `asyncio.gather()` for parallel service calls
- Handles business logic like total price calculation

### Python Conventions
- Async-first: all services use `async/await` with asyncpg and aioredis
- FastAPI with Pydantic models for request/response validation
- SQLAlchemy 2.0 async with `asyncpg` driver
- Environment-based configuration via `os.environ`
- Each service runs via `uvicorn` on internal port 8000

### Frontend Conventions
- React 18 with functional components and hooks
- Plain `fetch` API for HTTP requests (no axios)
- Single `App.js` with tab-based navigation
- Communicates only with BFF via `REACT_APP_BFF_URL`

## Service Ports

| Service            | External Port | Internal Port |
|--------------------|---------------|---------------|
| Frontend (React)   | 3000          | 3000          |
| BFF                | 8000          | 8000          |
| Order Service      | 8001          | 8000          |
| Inventory Service  | 8002          | 8000          |
| Saga Service       | 8003          | 8000          |
| Marketing Service  | 8004          | 8000          |
| Order DB           | 5432          | 5432          |
| Inventory DB       | 5433          | 5432          |
| Marketing DB       | 5434          | 5432          |
| Redis              | 6379          | 6379          |

## Environment Variables

All Python services read `DATABASE_URL` and `REDIS_URL` from the environment. The Saga service and BFF additionally read service URLs (`ORDER_SERVICE_URL`, `INVENTORY_SERVICE_URL`, etc.). The frontend uses `REACT_APP_BFF_URL`. All values are set in `docker-compose.yml`.

## Database Schema Notes

- **Order DB**: `event_store` (immutable events) + `orders_read_model` (denormalized current state)
- **Inventory DB**: `event_store` + `inventory_read_model` with `available` as a generated column (`quantity - reserved`). Seeded with 5 sample products.
- **Marketing DB**: No event store. Five projection tables: `marketing_order_snapshot`, `customer_summary`, `product_popularity`, `product_customer_map`, `daily_sales_summary`. All use UPSERT for idempotency.

## Testing

There are no automated tests (unit or integration) in this repository. CI validates code quality via Ruff linting/formatting and verifies that Docker images build successfully.
