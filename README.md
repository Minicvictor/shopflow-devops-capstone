# ShopFlow DevOps Capstone

> Containerized cloud-native deployment of the ShopFlow e-commerce platform on Kubernetes (Minikube), with CI/CD, GitOps, observability, DevSecOps and SRE practices.

![Architecture](architecture-diagram.png)

## Table of contents
1. [Project overview and problem statement](#1-project-overview-and-problem-statement)
2. [Architecture](#2-architecture)
3. [Technology choices and justification](#3-technology-choices-and-justification)
4. [Repository structure](#4-repository-structure)
5. [Local deployment](#5-local-deployment)
6. [CI/CD explanation](#6-cicd-explanation)
7. [Kubernetes architecture](#7-kubernetes-architecture)
8. [GitOps workflow](#8-gitops-workflow)
9. [Monitoring and logging](#9-monitoring-and-logging)
10. [Security controls](#10-security-controls)
11. [SLIs, SLOs and error budget](#11-slis-slos-and-error-budget)
12. [Incident response and runbook](#12-incident-response-and-runbook)
13. [Failure-testing evidence](#13-failure-testing-evidence)
14. [Rollback procedure](#14-rollback-procedure)
15. [Lessons learned](#15-lessons-learned)


---

## 1. Project overview and problem statement

ShopFlow is a small e-commerce platform. The development team supplied a working application made of an Nginx frontend, a Flask backend API, a PostgreSQL database and a Redis cache.

**The problem:** the application worked on a developer machine, but had:
- no automated tests or quality gates
- no security scanning, and database credentials hard-coded in the repository
- containers running as root, with no health checks or versioned image tags
- no repeatable deployment and no way to roll back a bad release
- no monitoring, central logging, alerting or incident process

**The goal:** take the application through a professional DevOps lifecycle so that it is **repeatable, automated, secure, observable, recoverable and well documented**.

**Scope:** Track A (local Kubernetes with Minikube). AWS (Terraform, Ansible, EC2) is not part of this submission.

**Application endpoints**

| Endpoint | Purpose |
|---|---|
| `GET /api/products` | List products |
| `POST /api/products` | Create a product (`name`, `price`, `stock`, optional `description`) |
| `POST /api/orders` | Create an order (`product_id`, `quantity`) |
| `GET /health` | Application and dependency health (liveness) |
| `GET /ready` | Readiness check |
| `GET /metrics` | Prometheus metrics |

## 2. Architecture

The diagram at the top (`architecture-diagram.png`) shows the full system. The same architecture as text-based Mermaid, rendered by GitHub:

```mermaid
flowchart LR
    Dev["Developer<br/>WSL laptop<br/>Docker Compose"] -->|push / PR| GH["GitHub repo<br/>main protected"]
    GH -->|trigger| CI["GitHub Actions CI<br/>lint, pytest, Gitleaks<br/>pip-audit, Trivy, build"]
    GH -->|ArgoCD watches k8s/ on main| Argo

    subgraph MK["Minikube cluster (Docker driver)"]
        Argo["ArgoCD<br/>auto sync, prune, self-heal"]

        subgraph SF["namespace: shopflow"]
            FE["frontend<br/>nginx-unprivileged :8080"]
            BB["backend-blue (live)<br/>Flask, HPA"]
            BG["backend-green (preview)<br/>Flask, HPA"]
            PG[("PostgreSQL<br/>PVC")]
            RD[("Redis")]
        end

        subgraph MON["namespace: monitoring"]
            PR["Prometheus<br/>alerts + SLO rules"]
            KSM["kube-state-metrics<br/>cAdvisor"]
            LK["Loki + Promtail"]
            GF["Grafana<br/>dashboard + Explore"]
        end

        Argo -->|deploys| SF
        FE -->|API calls| BB
        BB -->|SQL| PG
        BB -->|cache| RD
        BB -->|/metrics| PR
        KSM --> PR
        SF -->|pod logs| LK
        PR --> GF
        LK --> GF
    end
```

In summary:

1. A developer pushes a branch and opens a pull request on GitHub.
2. GitHub Actions lints, tests and scans the code and images.
3. After merge to `main`, ArgoCD (running in Minikube) detects the change in `k8s/` and syncs the cluster.
4. In the `shopflow` namespace, the frontend serves the page, and the backend (blue and green slots) talks to PostgreSQL (persistent volume) and Redis.
5. In the `monitoring` namespace, Prometheus, kube-state-metrics, Loki, Promtail and Grafana collect and display metrics and logs.

| Component | Image / version | Role |
|---|---|---|
| Frontend | `shopflow-frontend:1.0.0` (nginx-unprivileged, port 8080) | Serves the single-page UI |
| Backend | `shopflow-backend:1.x` (Python 3.11-slim, Flask, port 5000) | REST API, exposes `/metrics` |
| PostgreSQL | `postgres:16-alpine` | Persistent data (PVC) |
| Redis | `redis:7-alpine` | Cache |
| ArgoCD | stable manifests | GitOps controller |
| Prometheus | `v2.54.1` | Metrics and alert rules |
| Grafana | `11.2.0` | Dashboards and log exploration |
| Loki and Promtail | `2.9.8` | Centralized, searchable logs |
| kube-state-metrics | `v2.13.0` | Kubernetes workload metrics |

## 3. Technology choices and justification

| Choice | Why it was chosen |
|---|---|
| **Git and GitHub** | Pull requests, review history and branch protection give an auditable change process. |
| **Docker and Docker Compose** | Identical images run locally and in Kubernetes; Compose gives a one-command local stack. |
| **Hardened images** (slim Python, nginx-unprivileged, non-root users) | Smaller attack surface and compliance with least privilege. |
| **GitHub Actions** | CI lives beside the code and needs no extra infrastructure. |
| **Gitleaks, pip-audit, Trivy** | Cover secrets, dependencies and container images as automated gates. |
| **Minikube (Track A)** | A real Kubernetes API with no cloud cost; the brief states EKS is not required. |
| **Single-file-per-component manifests** | Easy to read, review and sync with ArgoCD. |
| **ArgoCD** | Git is the single source of truth; built-in drift detection, self-heal and history. |
| **Blue-green deployment** | Needs only core Kubernetes (two Deployments and a Service selector), so it suits a memory-limited cluster. A canary would require a traffic-splitting tool. |
| **Prometheus and Grafana** | Standard open-source metrics stack with alerting and dashboards. |
| **Loki and Promtail** | Lightweight log stack that reuses Grafana, so one UI covers metrics and logs. |
| **Kubernetes RBAC and NetworkPolicy** | Least-privilege access and restricted network exposure. |

## 4. Repository structure

```
.
├── .github/workflows/ci.yml     # CI pipeline
├── backend/                     # Flask API, Dockerfile, requirements, tests
├── frontend/                    # index.html and Dockerfile
├── docker-compose.yml           # Local run
├── .env.example                 # Compose variables (real .env is git-ignored)
├── backend/config.env.example   # Backend variables (real file is git-ignored)
├── k8s/                         # Kubernetes manifests (ArgoCD source of truth)
├── gitops/argocd-app.yaml       # ArgoCD Application
├── monitoring/                  # Prometheus, alerts, Grafana, Loki, Promtail, dashboard
├── docs/                        # Detailed documentation
├── architecture-diagram.png
└── README.md
```

### Git workflow and branching strategy
- `main` is protected; no direct pushes. All changes arrive by pull request.
- Branch names: `feature/<name>`, `fix/<name>`, `docs/<name>`, `release/<name>`, `test/<name>`.
- Conventional commit messages: `feat:`, `fix:`, `docs:`, `ci:`, `chore:`.
- CI must pass before merging; branches are deleted after merge.
- An intentional merge conflict in the README was created and resolved during Phase 2.

## 5. Local deployment

### Prerequisites
Docker (with Compose v2), Git, curl.

### Run with Docker Compose
```bash
git clone https://github.com/Minicvictor/shopflow-devops-capstone.git
cd shopflow-devops-capstone

cp .env.example .env                              # set POSTGRES_PASSWORD
cp backend/config.env.example backend/config.env  # use the same password in DATABASE_URL

docker compose up --build -d
docker compose ps                                  # wait for "healthy"
```

### Verify
```bash
curl http://localhost:5000/health
curl http://localhost:5000/ready
curl http://localhost:5000/metrics | head
curl -X POST http://localhost:5000/api/products \
  -H "Content-Type: application/json" \
  -d '{"name":"Test Item","description":"demo","price":1500,"stock":20}'
curl http://localhost:5000/api/products
```
Open http://localhost:8080 to use the frontend. The page calls the API on `localhost:5000`, so that port must stay published.

### Docker engineering summary
- Backend: `python:3.11-slim`, dependencies installed with no cache, pip/setuptools/wheel removed after install, non-root user (uid 10001), `HEALTHCHECK` on `/health`.
- Frontend: `nginxinc/nginx-unprivileged` (non-root, port 8080), `apk upgrade` to patch OS packages, `HEALTHCHECK`.
- Versioned tags (`1.0.0`) instead of `latest`; `.dockerignore` in both images.
- Configuration through environment variables; secrets are never baked into images or committed.
- Compose: pinned Postgres and Redis versions, health checks, `depends_on` with `service_healthy`, named volume for PostgreSQL.

### Run on Kubernetes (Minikube)
```bash
minikube start --driver=docker --cpus=2 --memory=4000
minikube addons enable metrics-server

# Build images inside Minikube's Docker daemon
eval $(minikube docker-env)
docker build -t shopflow-backend:1.0.0 ./backend
docker tag shopflow-backend:1.0.0 shopflow-backend:1.1.0
docker build -t shopflow-frontend:1.0.0 ./frontend

# Namespace and Secret (never committed)
kubectl create namespace shopflow
export $(grep -v '^#' .env | xargs)
kubectl create secret generic shopflow-secret -n shopflow \
  --from-literal=POSTGRES_USER="$POSTGRES_USER" \
  --from-literal=POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  --from-literal=DATABASE_URL="postgresql+psycopg2://$POSTGRES_USER:$POSTGRES_PASSWORD@postgres:5432/$POSTGRES_DB"

kubectl apply -f k8s/
kubectl get pods -n shopflow -w

# Access (two terminals)
kubectl port-forward -n shopflow svc/backend 5000:5000
kubectl port-forward -n shopflow svc/frontend 8080:80
```
Image names are `shopflow-backend` and `shopflow-frontend`. Because images are built inside Minikube, manifests use `imagePullPolicy: Never`.

## 6. CI/CD explanation

Workflow: `.github/workflows/ci.yml`. It runs on every push to `main` and every pull request targeting `main`, with read-only token permissions.

| Job | Steps | Fails when |
|---|---|---|
| **Lint and test** | Checkout, set up Python 3.11, install dependencies, flake8, pytest against Postgres and Redis service containers | Serious lint errors (syntax errors, undefined names) or any failing test |
| **Security scans** | Gitleaks over full history, pip-audit on `requirements.txt`, Trivy filesystem scan (HIGH/CRITICAL, unfixed ignored) | A leaked secret, a vulnerable dependency, or a HIGH/CRITICAL finding |
| **Build and scan images** | Build backend and frontend images, Trivy image scan on each | A HIGH/CRITICAL fixed vulnerability in either image |

`Build and scan images` only runs after the first two jobs pass, so a failed gate stops the pipeline. Branch protection on `main` requires all three checks.

**Gates proven in practice:** the pipeline blocked a build on HIGH-severity Alpine package vulnerabilities (zlib and tiff) in the frontend image. They were fixed by upgrading OS packages in the Dockerfile.

**Deployment** is not done by CI. After merge, ArgoCD applies the change (see GitOps below). This keeps CI free of cluster credentials.

## 7. Kubernetes architecture

All application objects live in the `shopflow` namespace.

| Object | Details |
|---|---|
| **Namespace** | `shopflow` |
| **ConfigMap** | `shopflow-config`: non-sensitive values (Redis URL, port) |
| **Secret** | `shopflow-secret`: database user, password and URL; created from `.env` at deploy time, never stored in Git |
| **Frontend** | Deployment (1 replica, port 8080) and NodePort Service |
| **Backend** | Two Deployments, `backend-blue` and `backend-green`; Services `backend` (live) and `backend-preview` (idle slot) |
| **PostgreSQL** | Deployment with a PersistentVolumeClaim (1 Gi) and ClusterIP Service |
| **Redis** | Deployment and ClusterIP Service |
| **Probes** | Backend: readiness `/ready`, liveness `/health`. Frontend: HTTP `/`. Postgres and Redis: TCP checks |
| **Resources** | CPU and memory requests and limits on every container |
| **HPA** | One per backend slot, CPU target 70% |
| **PodDisruptionBudget** | `backend-pdb`, `minAvailable: 1` for backend pods |
| **Labels and selectors** | `app` for all workloads; `version: blue|green` for backend slots |
| **RBAC** | Token-less ServiceAccounts for backend and frontend; read-only viewer Role |
| **NetworkPolicy** | Only the backend may reach Postgres and Redis (see limitation in section 10) |

**Blue-green deployment design**
- Two backend slots run side by side. The `backend` Service selects the live slot through its `version` label.
- A new version is deployed to the **idle** slot and validated through `backend-preview` (`/health`, `/ready`, `/api/products`, `/metrics`).
- Traffic is moved by changing one selector line in `k8s/backend-service.yaml` through a pull request.
- The previous slot stays running as the instant rollback target.
- Slots use the `Recreate` strategy so a bad version cannot hide behind old pods.
- Limitation: traffic moves 100% at once; a canary would need Argo Rollouts or a service mesh.

## 8. GitOps workflow

ArgoCD runs in the `argocd` namespace. The Application (`gitops/argocd-app.yaml`) tracks the `k8s/` folder on `main`.

| Setting | Effect |
|---|---|
| `automated.prune: true` | Objects removed from Git are removed from the cluster |
| `automated.selfHeal: true` | Manual `kubectl` changes are reverted to the Git state |
| `ignoreDifferences` on backend replicas | The HPA can change replica counts without ArgoCD fighting it |
| Secrets not in Git | `shopflow-secret` is created manually and is not managed or pruned by ArgoCD |

**Workflow**
1. Change a manifest on a branch.
2. Open a pull request; CI runs.
3. Merge to `main`.
4. ArgoCD detects the change (polling every 3 minutes, or on a forced refresh) and syncs the cluster.
5. The cluster state matches Git; ArgoCD shows Synced and Healthy.

**Drift detection:** scaling the frontend to 3 replicas with `kubectl` made ArgoCD report OutOfSync with a diff against Git; syncing restored the declared state.

**Limitation:** secrets are bootstrapped by hand. A production setup would use Sealed Secrets or an external secrets operator.

## 9. Monitoring and logging

### Metrics (Prometheus)
Scrape targets: the backend pods (`/metrics`), cAdvisor (CPU and memory per container) and kube-state-metrics (restarts and workload health).

### Dashboard (Grafana, "ShopFlow Overview")
| Panel | Question it answers |
|---|---|
| Request rate | How much traffic is there? |
| HTTP errors (4xx/5xx) | Are requests failing? |
| Request latency p95 | Are responses slow? |
| Pod restarts | Is anything crash-looping? |
| CPU usage | Are pods near their limits? |
| Memory usage | Is anything close to OOM? |
| Workload health | Are the expected replicas available? |

### Alerts
| Alert | Condition | Severity |
|---|---|---|
| `BackendDown` | No backend pods scraped for 1 minute | critical |
| `HighErrorRate` | More than 5% of requests return 5xx for 2 minutes | critical |
| `HighLatencyP95` | p95 latency above 1 second for 5 minutes | warning |
| `PodRestartingFrequently` | More than 2 restarts in 10 minutes | warning |
| `PodNotReady` | A pod not ready for 2 minutes | warning |
| `ErrorBudgetFastBurn` | Availability error budget burning faster than 6x | critical |

### Centralized logging (Loki and Promtail)
Promtail runs as a DaemonSet and ships logs from the `shopflow` namespace to Loki. Logs are searched in Grafana **Explore** with the Loki data source, for example:
```
{namespace="shopflow", app="backend"} |~ "(?i)error|exception|refused"
```
To investigate an incident: find the first error timestamp in Loki, then line it up with the dashboard panels and the alerts page for the same time window.

**Limitation:** Loki stores data in an `emptyDir`, so logs are lost when the Loki pod restarts.

## 10. Security controls

| Control | Implementation |
|---|---|
| Secret scanning | Gitleaks in CI over full history |
| Dependency scanning | pip-audit and Trivy filesystem scan in CI |
| Container image scanning | Trivy on both images; CI fails on HIGH/CRITICAL |
| Non-root containers | Backend uid 10001, frontend uid 101; `runAsNonRoot` enforced in Kubernetes |
| Privilege hardening | `allowPrivilegeEscalation: false`, all capabilities dropped, seccomp `RuntimeDefault` |
| Kubernetes RBAC | Backend and frontend ServiceAccounts have no API token mounted; a read-only viewer Role has no access to Secrets |
| Network exposure | PostgreSQL and Redis use ClusterIP only; NetworkPolicies allow only the backend to connect |
| Credentials | `.env` and `config.env` are git-ignored; `.example` files are committed; the Kubernetes Secret is created at deploy time |

### Documented findings
1. **Hard-coded database credentials in the starter** (`docker-compose.yml`, `backend/config.env`). *Fix:* moved to git-ignored files, committed `.example` files, Kubernetes Secret created from the environment, Gitleaks added to CI. *Residual risk:* old throwaway values may remain in Git history.
2. **HIGH-severity vulnerabilities in frontend image packages** (zlib CVE-2026-22184 and tiff CVE-2026-4775), caught by Trivy in CI. *Fix:* `apk upgrade` in the frontend Dockerfile; CI scans every build.
3. **Databases published on the host in Docker Compose** (ports 5433 and 6378). *Fix:* Kubernetes uses ClusterIP and NetworkPolicies. *Limitation:* Minikube's default network plugin does not enforce NetworkPolicy; enforcement needs a policy-aware CNI such as Calico, so these policies are defined but not enforced on the default setup.

### Accepted risks
- Containers use a writable root filesystem (Nginx and Python need temporary paths).
- Scanner images such as `aquasec/trivy:latest` are not pinned.
- IAM least privilege applies only to cloud resources and is not applicable to this local deployment.

## 11. SLIs, SLOs and error budget

| Category | SLI | SLO (30 days) |
|---|---|---|
| Availability | Requests that do not return HTTP 5xx / all requests | **99.5%** |
| Latency | Requests answered in under 500 ms / all requests | **95%** |

Measured by Prometheus recording rules: `sli:availability:ratio_rate5m`, `sli:availability:ratio_rate1h` and `sli:latency_under_500ms:ratio_rate5m`.

### Error budget
- Allowed failure: 100% − 99.5% = **0.5%** of requests.
- In time: 30 days × 24 h × 60 min = 43,200 min; 43,200 × 0.005 = **216 minutes** of full outage per 30 days.
- In requests: at 1,000,000 requests per 30 days, **5,000** failures are allowed.
- Latency: up to 5% of requests may exceed 500 ms.
- Burn rate = observed error ratio / 0.005. A burn rate of 1 consumes exactly the whole budget in 30 days; `ErrorBudgetFastBurn` fires above 6.

### Error budget policy
| Budget remaining | Action |
|---|---|
| More than 50% | Normal feature work and releases |
| 10% to 50% | Releases need extra validation through the preview service |
| Less than 10% | Reliability work only; releases limited to fixes |
| Exhausted | Release freeze until the budget recovers; post-incident review |

## 12. Incident response and runbook

### Severity levels
| Level | Definition | Example | Response target |
|---|---|---|---|
| SEV1 | Application fully down or data at risk | No backend endpoints, database unavailable | Acknowledge in 5 min |
| SEV2 | Major degradation or fast SLO burn | Error rate above 5%, p95 above 1 s | Acknowledge in 15 min |
| SEV3 | Minor problem with a workaround | One pod restarting | Within the working day |
| SEV4 | Cosmetic or informational | Dashboard panel broken | Backlog |

### On-call and ownership
- One primary and one secondary on-call engineer per week, rotating among team members.
- The primary acknowledges alerts, leads the response and communicates status. The secondary assists and takes over if the primary does not respond within 15 minutes.
- Each component (backend and database, frontend and manifests, CI/CD and GitOps, monitoring and logging) has a named owner (see `docs/sre.md`).

### Incident response steps
1. **Detect:** an alert fires or a symptom is reported.
2. **Acknowledge and classify:** assign a severity and an incident lead.
3. **Communicate:** short status with next update time.
4. **Investigate:** dashboard, then pod status, then Loki logs.
5. **Mitigate first:** restore service (roll back, restart, scale) before finding the full cause.
6. **Verify recovery:** health endpoints, dashboard and a real request succeed.
7. **Close and review:** record the timeline; write a blameless post-incident review within 2 working days.

### First five minutes
```bash
kubectl get pods -n shopflow -L version
kubectl get endpoints backend -n shopflow
kubectl get events -n shopflow --sort-by=.lastTimestamp | tail -15
curl http://localhost:5000/health
```

### Runbook scenarios
| Scenario | Detection | Mitigation |
|---|---|---|
| **Backend down (SEV1)** | `BackendDown`, empty endpoints | Revert the release PR in Git; ArgoCD restores the previous slot |
| **Database unavailable (SEV1)** | `HighErrorRate`, `PodNotReady`, connection errors in Loki | Restore the Postgres pod or replica count; data persists on the PVC |
| **High errors or latency (SEV2)** | `HighErrorRate`, `HighLatencyP95`, `ErrorBudgetFastBurn` | Check HPA scaling and resource usage; roll back if a release caused it |
| **Pod crash loop (SEV3)** | `PodRestartingFrequently` | Read `--previous` logs; raise limits if OOMKilled or revert the change |

Full runbook: [docs/runbook.md](docs/runbook.md). SRE detail: [docs/sre.md](docs/sre.md).

## 13. Failure-testing evidence

Four failures were injected on Minikube. A probe pod inside the cluster requested `/health` and `/api/products` every second to measure impact. Each incident follows **symptom → detection → investigation → root cause → mitigation → recovery → prevention**.

| # | Failure injected | Detected by | Recovery | Result |
|---|---|---|---|---|
| 1 | Backend pod deleted | Probe output, Grafana pod panel | Kubernetes recreated the pod | `<fill in observed seconds of impact>` |
| 2 | Broken release (image exits on start) switched live | `BackendDown` alert, ArgoCD Degraded, empty endpoints | Reverted the release PR in Git | `<fill in time to recover>` |
| 3 | Increased traffic from load generators | HPA target above 70%, Grafana CPU and request panels | HPA added replicas automatically | `<fill in replica counts>` |
| 4 | PostgreSQL scaled to zero (dependency unavailable) | `PodNotReady` / `HighErrorRate`, Loki connection errors | Scaled Postgres back to 1; data intact on PVC | `<fill in time to recover>` |

Complete timelines, screenshots and commands: [docs/failure-testing.md](docs/failure-testing.md).

### Evidence index
| Evidence | Location |
|---|---|
| Docker Compose and image build | `screenshots/` |
| CI runs (green and intentionally red) | GitHub **Actions** tab |
| Pull requests incl. merge conflict and revert | GitHub **Pull requests** tab |
| Kubernetes objects, PVC, HPA, PDB | `screenshots/` |
| Prometheus targets, alerts; Grafana dashboard; Loki query | `screenshots/` |
| ArgoCD Synced, drift and history | `screenshots/` |
| Security scans | CI logs and `screenshots/` |

## 14. Rollback procedure

Rollback is a Git operation; do not hand-edit the cluster, because ArgoCD self-heal reverts manual changes.

1. Find the release pull request (`git log --oneline -10`).
2. On the merged PR page click **Revert** and merge the generated revert PR.
3. Force a sync (or wait up to three minutes):
   ```bash
   kubectl annotate application shopflow -n argocd argocd.argoproj.io/refresh=hard --overwrite
   ```
4. Verify:
   ```bash
   kubectl get endpoints backend -n shopflow
   kubectl get pods -n shopflow -l app=backend -L version
   ```
5. Restart your port-forward and confirm `curl http://localhost:5000/health` returns 200.

For a blue-green release the revert moves the Service selector back to the known-good slot, which was kept running.

## 15. Lessons learned

**What went well**
- Making Git the single source of truth (pull requests plus ArgoCD) turned deployments and rollbacks into a single revert.
- CI scanners caught real vulnerabilities before release.
- The preview Service made it possible to validate a version before it received traffic.
- Writing the runbook before the failure tests made incidents quicker to diagnose.

**Problems and fixes**
| Problem | Cause | Fix |
|---|---|---|
| Frontend connection reset on 8080 | Old Dockerfile still listened on 80 | Rebuilt on nginx-unprivileged (8080) and matched the port mapping |
| Backend could not reach Redis | Config used the host-published port 6378 | Used the container port 6379 |
| CI could not resolve the Trivy action | Action tag or its dependency did not exist | Ran Trivy from its Docker image |
| Image pulls timed out | WSL and Docker DNS | Set public DNS servers; loaded images into Minikube |
| `kubectl` timeouts and TLS handshake errors | Minikube starved of memory by the full monitoring stack | Scaled down unused components and raised memory |
| Manifest parse errors | Indentation mistakes in hand-edited YAML | Replaced files wholesale and validated YAML before applying |

**What I would change**
- Use a container registry instead of building images inside Minikube.
- Keep two replicas on the live slot at all times.
- Add Alertmanager so alerts page a person.
- Use Sealed Secrets or an external secrets operator.
- Use a CNI that enforces NetworkPolicy.
- Persist Loki and Grafana data.

## Repository: https://github.com/Minicvictor/shopflow-devops-capstone
