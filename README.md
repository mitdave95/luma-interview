# luma-interview

## Quick Start

### Setup
  `python3 -m venv .venv && source .venv/bin/activate`
  `make install`
  `make frontend-install`
  `make docker-up`  # Start Redis

### Run API
  `make dev`  # http://localhost:8000

### Run Frontend Server
  `make frontend-dev` # http://localhost:5173/

For scraping service, ANTHROPIC_API_KEY set in terminal
`export ANTHROPIC_API_KEY={YOUR_KEY}`

### Test with API keys
  `curl -H "X-API-Key: dev_test_key" http://localhost:8000/v1/account/quota`
  `curl -X POST -H "X-API-Key: dev_test_key" -H "Content-Type: application/json" -d '{"prompt": "A sunset over mountains"}' http://localhost:8000/v1/generate`

## API Documentation
  Visit http://localhost:8000/docs for interactive Swagger documentation.

# Technical Presentation: Luma Labs Enterprise API

**Tech Stack:**
- Backend: Python 3.11+, FastAPI, Redis, Playwright
- Frontend: React 19, TypeScript, Tailwind CSS
- AI: Claude API (Anthropic)
- Infrastructure: Docker, Docker Compose

---

# Part 1: API Architecture

## 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Request                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Rate Limit Middleware                        │
│              (Sliding Window Algorithm + Redis)                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Authentication Layer                          │
│                  (API Key Validation)                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Route Handlers                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Service Layer                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│     Priority Queue       │    │     In-Memory Storage    │
│   (Redis Sorted Sets)    │    │      (Singleton)         │
│                          │    │                          │
│                          │    └──────────────────────────┘
└──────────────────────────┘
              │
              ▼
┌──────────────────────────┐
│    Background Worker     │
│  (Async Job Processing)  │
│                          │
└──────────────────────────┘
```

---

## 1.2 Design Patterns & Why I Used Them

### Pattern 1: Dependency Injection (FastAPI's `Depends()`)

- Enables loose coupling between components
- Makes testing easy (can inject mocks)
- Centralizes authentication/authorization logic

---

### Pattern 2: Singleton Pattern for Global State

- Single source of truth for in-memory data
- Consistent state across requests
- Efficient resource management


---

### Pattern 3: State Machine for Job Status

- Prevents invalid state transitions
- Self-documenting valid workflows
- Easy to extend with new states

---

### Pattern 4: Sliding Window Rate Limiting

- More accurate than fixed window (no burst at window boundaries)
- Uses Redis sorted sets for O(log n) operations
- Atomic Lua scripts prevent race conditions

---

### Pattern 5: Weighted Fair Queuing

- Ensures higher-tier users get priority
- Prevents starvation of lower-tier users
- Configurable weights (10:5:1 ratio)

---

## 1.3 Tiered User Access

| Tier | Rate Limit | Max Duration | Can Generate | Can Batch |
|------|------------|--------------|--------------|-----------|
| Free | 10/min | - | No | No |
| Developer | 30/min | 30 sec | Yes | No |
| Pro | 100/min | 120 sec | Yes | Yes |
| Enterprise | 1000/min | 300 sec | Yes | Yes |

---

## 1.4 Error Handling Architecture

- Consistent error responses across API
- Automatic HTTP status code mapping
- Rich error details for debugging

```
LumaAPIError (500)
├── AuthenticationError (401)
│   ├── InvalidAPIKeyError
│   ├── ExpiredTokenError
│   └── MissingCredentialsError
├── AuthorizationError (403)
│   ├── InsufficientTierError
│   └── QuotaExceededError
├── RateLimitError (429)
│   └── TooManyRequestsError
├── ValidationError (400)
└── GenerationError (500)
```

---

## 1.5 API Endpoints Summary

| Endpoint | Method | Auth | Purpose |
|----------|--------|------|---------|
| `/health` | GET | None | Health check |
| `/v1/generate` | POST | Dev+ | Create generation job |
| `/v1/generate/batch` | POST | Pro+ | Batch generation |
| `/v1/jobs` | GET | Any | List user's jobs |
| `/v1/jobs/{id}` | GET | Any | Get job status |
| `/v1/jobs/{id}` | DELETE | Any | Cancel job |
| `/v1/videos` | GET | Any | List user's videos |
| `/v1/account` | GET | Any | Account details |
| `/ws/dashboard` | WS | None | Real-time updates |

---

# Part 2: Web Scraping Implementation

## 2.1 Scraping Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Client Request                             │
│                   POST /v1/scrape/playwright                    │
│                   { "url": "https://..." }                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Route Handler                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ScrapeService                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌──────────────────────────┐    ┌──────────────────────────┐
│   Playwright Browser     │    │      Claude API          │
│   (Docker Container)     │    │   (Anthropic)            │
│                          │    │                          │
│  - Headless Chrome       │    │  - HTML → Markdown       │
│  - JavaScript rendering  │    │  - Content extraction    │
│  - Full page content     │    │  - Ads/cruft removal     │
│                          │    │                          │
└──────────────────────────┘    └──────────────────────────┘
```

---

# Part 3: What Can Be Improved

## API Improvements

### 1. **Database Persistence**
- Current: In-memory storage (lost on restart)
- Improvement: PostgreSQL for jobs/videos, Redis for caching

### 2. **Real Authentication**
- Current: Mock auth with hardcoded API keys
- Improvement: JWT tokens, OAuth2, API key rotation

### 3. **Async Background Tasks**
- Current: Simple asyncio worker polling
- Improvement: Celery or ARQ for distributed task processing

### 4. **API Versioning**
- Current: Single `/v1` prefix
- Improvement: URL versioning with deprecation headers

### 5. **Request Validation**
- Current: Basic Pydantic validation
- Improvement: Custom validators, input sanitization

### 6. **Caching Layer**
- Current: No caching
- Improvement: Redis caching for video metadata, rate limit results

### 7. **Observability**
- Current: Basic logging
- Improvement: OpenTelemetry, Prometheus metrics, Jaeger tracing