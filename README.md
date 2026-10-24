# ShopFlow Application Source

This package contains **application source code only** for the ShopFlow DevOps mini-project.

Students must build the complete DevOps platform around this application themselves.

## Included
- Frontend: static HTML/JavaScript
- Backend: Python Flask REST API
- Database integration: PostgreSQL
- Cache/dependency integration: Redis
- Small starter test suite

## Deliberately excluded
- Dockerfiles and Docker Compose
- Kubernetes manifests and Helm charts
- Terraform
- Ansible
- CI/CD workflows
- Prometheus/Grafana configuration
- ArgoCD/GitOps configuration
- Cloud/network infrastructure configuration
- Deployment scripts
- Production secrets

## Backend API
- `GET /` — application information
- `GET /health` — health endpoint
- `GET /ready` — checks PostgreSQL and Redis
- `GET /api/products` — list products
- `POST /api/products` — create a product
- `POST /api/orders` — place an order

### Example product
```json
{"name":"Laptop Stand","description":"Adjustable aluminum laptop stand","price":50000,"stock":15}
```

### Example order
```json
{"product_id":1,"quantity":2}
```

## Backend environment variables
```text
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
PORT=5000
```

## Database commands
From the backend directory:
```bash
flask --app app init-db
flask --app app seed
```

## Tests
```bash
pytest backend/test_smoke.py
```

The test suite is intentionally small. Students should extend testing as part of the DevOps project requirements.

## Student responsibility
Starting from this application, create the Docker, CI/CD, infrastructure, configuration, Kubernetes, security, observability, GitOps, reliability and documentation required by the accompanying project instructions.
