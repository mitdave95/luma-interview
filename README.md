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

### Test with API keys
  `curl -H "X-API-Key: dev_test_key" http://localhost:8000/v1/account/quota`
  `curl -X POST -H "X-API-Key: dev_test_key" -H "Content-Type: application/json" -d '{"prompt": "A sunset over mountains"}' http://localhost:8000/v1/generate`

## API Documentation
  Visit http://localhost:8000/docs for interactive Swagger documentation.