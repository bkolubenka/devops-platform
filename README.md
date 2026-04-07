# DevOps Platform

[![CI](https://github.com/bkolubenka/devops-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/bkolubenka/devops-platform/actions/workflows/ci.yml)
[![Deploy](https://github.com/bkolubenka/devops-platform/actions/workflows/deploy.yml/badge.svg)](https://github.com/bkolubenka/devops-platform/actions/workflows/deploy.yml)

Containerized full-stack DevOps platform deployed on an Ubuntu VPS, integrating CI/CD, observability, and operational workflows using Ansible, Docker Compose, Nginx, PostgreSQL, and GitHub Actions.

## What This Project Shows

- FastAPI backend with portfolio, service catalog, overview, incident log, and incident-assistant AI endpoints
- Vite-built React + TypeScript frontend served separately from the backend
- PostgreSQL-backed persistence
- Alembic migrations for schema and release data changes
- CRUD management for projects, services, and incidents, with `/api/incidents` also serving as the operational log for monitor-worker sweeps and service-action events
- service-aware incident assistant with deterministic runbook guidance and incident autofill
- monitor-worker demo service that records platform health summaries and state transitions
- environment-aware service probing so monitor-worker and the overview API only check services that exist in the current environment (e.g. Docker Nginx is skipped in production where host Nginx is used)
- worker-mediated service actions so the API queues intent and a separate runner executes it
- GHCR-backed production images for app services
- Prometheus + Grafana + Node Exporter observability stack with provisioned dashboards and embedded live metrics
- build metadata footer with app version, image tag, build id, and pinned component versions
- host-managed Nginx reverse proxy on prod and home dev TLS edge (Docker Nginx behind it on dev)
- two-phase infrastructure: `bootstrap.yml` for one-time server setup + `playbook.yml` for app deploys
- Ansible-based deployment
- GitHub Actions CI with bootstrap, publish, deploy, and auto-deploy workflows
- self-hosted GitHub Actions deploy runners on the VM/VPS

## Current Architecture

```text
GitHub Actions
  ↓
Self-hosted runner (vm-1 or vps-1)
  ↓
Ansible (local or SSH to VPS)
  ↓
Docker Compose (app containers)
  ↓
Host Nginx (prod) / Host TLS edge + Docker Nginx (dev)
  ├─ /        -> frontend (127.0.0.1:8080)
  ├─ /api/*   -> FastAPI backend (127.0.0.1:8000)
  ├─ /health  -> backend health check
  ├─ /grafana/ -> Grafana UI (127.0.0.1:3000)
  └─ /prometheus/ -> Prometheus UI (127.0.0.1:9090)
```

Production Nginx runs on the host (installed by `bootstrap.yml`), not inside Docker.
App containers bind to `127.0.0.1` and are only reachable through the host Nginx reverse proxy.
The dev VM now also uses a host TLS edge, so `https://local.kydyrov.dev` is reachable publicly on port 443 and proxies into the Docker compose stack.

- `monitor-worker` is a separate demo worker container that records operational log sweeps into the incident log.
- `action-runner` is a hidden executor container that processes queued service-action jobs so the API never talks to Docker directly.
- `node-exporter` exposes host-level metrics (CPU, memory, disk, network) for Prometheus.

## Tech Stack

- Python 3.11
- FastAPI
- React 18
- TypeScript
- Vite
- SQLAlchemy
- PostgreSQL
- Nginx (host-managed on prod, Docker container on dev)
- Docker / Docker Compose
- Ansible
- GitHub Actions
- Prometheus / Grafana / Node Exporter

## Project Structure

```text
apps/devops-platform/
  backend/
    main.py
    monitor_worker.py
    database.py
    models.py
    alembic.ini
    alembic/
      env.py
      versions/
    requirements.txt
    Dockerfile
  frontend/
    src/
    public/
      resume/
    index.html
    package.json
    vite.config.ts
    Dockerfile
  nginx/
    dev.conf          ← used by Docker Nginx in dev
    prod.conf         ← reference only; prod uses host Nginx via template
  docker-compose.dev.yaml
  .env.dev

infra/
  ansible/
    ansible.cfg
    inventory.ini
    bootstrap.yml     ← one-time server setup (Docker, Nginx, SSL, UFW)
    playbook.yml      ← app deployment (dev and prod)
    group_vars/
      all.yml
    tasks/
      verify_ingress_smoke.yml  ← reusable post-deploy smoke checks
    templates/
      docker-compose.prod.yaml.j2
      local-dev.conf.j2  ← dev host TLS edge rendered to /etc/nginx/conf.d/
      prod.conf.j2    ← host Nginx config rendered to /etc/nginx/conf.d/
      ssl-params.conf.j2
      prod.env.j2
      release.env.j2
  monitoring/
    prometheus.yml
    grafana/
      dashboards/
        platform-overview.json
      provisioning/
        dashboards/default.yml
        datasources/prometheus.yml

.github/workflows/
  ci.yml
  deploy.yml
  auto-deploy-prod.yml
  publish-images.yml
  bootstrap.yml       ← manual workflow for server bootstrapping
```

## Application Routes

- `GET /` -> frontend
- `GET /health` -> health check through Nginx
- `GET /api/health` -> backend health check
- `GET /api/overview`
- `GET /api/portfolio/projects`
- `GET /api/portfolio/projects/{id}`
- `POST /api/portfolio/projects`
- `PUT /api/portfolio/projects/{id}`
- `DELETE /api/portfolio/projects/{id}`
- `GET /api/portfolio/skills`
- `POST /api/portfolio/skills`
- `GET /api/services`
- `GET /api/services/{id}`
- `POST /api/services`
- `PUT /api/services/{id}`
- `DELETE /api/services/{id}`
- `POST /api/services/{id}/actions`
- `GET /api/service-action-jobs`
- `GET /api/incidents`
- `GET /api/incidents/{id}`
- `POST /api/incidents`
- `PUT /api/incidents/{id}`
- `DELETE /api/incidents/{id}`
- `POST /api/ai/incidents/analyze`
- `POST /api/ai/generate-text`
- `GET /api/ai/models`

## Quickstart

### 1. Clone and start dev

```bash
git clone https://github.com/bkolubenka/devops-platform.git
cd devops-platform/apps/devops-platform
docker compose --env-file .env.dev -f docker-compose.dev.yaml up --build
```

Open:

- `http://localhost/` — portal UI
- `http://localhost/health` — health check (includes DB connectivity)
- `http://localhost/api/portfolio/projects` — API
- `http://localhost/grafana/` — Grafana dashboards
- `http://localhost/prometheus/` — Prometheus targets

Dev uses `.env.dev` for all configuration. No secrets setup required for local development.

On WSL, the default dev stack intentionally skips `node-exporter` because the host-root bind mount is not portable there. If you are running on a native Linux host and want host metrics in dev, enable it explicitly:

```bash
docker compose --env-file .env.dev -f docker-compose.dev.yaml --profile host-observability up --build
```

### 2. Run tests

```bash
cd apps/devops-platform
DATABASE_URL=sqlite:// python -m pytest backend/tests/ -v
```

Tests use an in-memory SQLite database — no Postgres required. CI runs them automatically on every push.

### 3. Set up secrets for prod

Before deploying to production, configure these GitHub repository secrets:

| Secret | How to get it |
|---|---|
| `BECOME_PASSWORD` | Optional: sudo password for the deploy user (only needed if passwordless sudo is not configured) |
| `DB_PASSWORD` | Generate a strong random password for PostgreSQL |
| `SECRET_KEY` | Generate a random string (e.g. `openssl rand -hex 32`) |
| `CF_API_TOKEN` | Create a Cloudflare API token with DNS edit permissions for your zone |
| `SSH_PRIVATE_KEY` | SSH private key that can connect to the VPS |
| `SSH_HOST` | VPS IP address (e.g. `204.168.184.213`) |
| `SSH_USER` | SSH user on the VPS (e.g. `make`) |

### 4. Bootstrap + Deploy

```bash
# 1. One-time: Go to Actions → Bootstrap Infrastructure → Run workflow
# 2. Deploy:   Go to Actions → Deploy → Run workflow (select prod, provide SHA tag)
```

Both manual workflows use GitHub's built-in branch selector, so you can run them from a feature branch or tag without an extra `ref` field. Bootstrap also exposes `deploy_env` and defaults to `prod`.

See [Infrastructure: Bootstrap vs Deploy](#infrastructure-bootstrap-vs-deploy) for manual commands.

## Incident Assistant (Optional Ollama)

The incident assistant remains deterministic by default (keyword + runbook based).
You can optionally enrich the response with Ollama using existing incident history as context.

Environment variables:

- `INCIDENT_ASSISTANT_USE_OLLAMA=true` to enable Ollama enrichment
- `OLLAMA_BASE_URL=http://127.0.0.1:11434` (default)
- `OLLAMA_MODEL=llama3.1:8b` (default)
- `OLLAMA_TIMEOUT_SECONDS=8` (default, clamped to 1..30)

If Ollama is unavailable or returns invalid output, the API automatically falls back to the deterministic runbook response.

## Observability

- Backend exposes Prometheus metrics at `/metrics`.
- `monitor-worker` exposes probe metrics at `:9000/metrics`.
- `node-exporter` exposes host-level metrics (CPU, memory, disk, network) at `:9100/metrics`.
- Prometheus scrapes backend, monitor-worker, and node-exporter every 30 seconds.
- Grafana dashboards and datasource are provisioned from `infra/monitoring/grafana/`.
- Grafana allows anonymous read-only access (Viewer role); admin account retains full control.
- The Observability tab on the portal embeds the Grafana dashboard inline via iframe (kiosk mode).
- Dashboard panels: HTTP request rate, error rate, p95 latency, incidents created, requests by endpoint, service probe success rate, probe latency p95, incident assistant mode.
- Scanner/bot endpoints (`.env`, `.php`) are filtered from the requests-by-endpoint panel.

Production access:

- `https://kydyrov.dev/grafana/d/devops-platform-overview/devops-platform-overview` (dashboard)
- `https://kydyrov.dev/prometheus/targets`

Both are routed through host Nginx on 443; production does not expose 3000/9090 publicly.

### Healthcheck Contract

The `/health` and `/api/health` endpoints return JSON with the overall status and per-component checks:

```json
{
  "status": "ok",
  "database": "ok"
}
```

- `status` — `"ok"` when all checks pass, `"degraded"` if any component is unhealthy.
- `database` — `"ok"` if the DB responds to `SELECT 1`, `"error"` otherwise.

Docker Compose healthchecks for `backend` and `nginx` use this endpoint. The Ansible deploy playbook polls `/health` after starting the stack and expects `"status": "ok"`.

**Extending the healthcheck:** To add a new component check, add a try/except block in the `health()` function in `backend/main.py`, return the component status as a new key, and set `overall` to `"degraded"` if it fails.

### Monitoring Setup

**Prometheus scrape targets** are defined in `infra/monitoring/prometheus.yml`:

| Job | Target | Metrics path |
|---|---|---|
| `backend` | `backend:8000` | `/metrics` |
| `monitor-worker` | `monitor-worker:9000` | `/metrics` |
| `node-exporter` | `node-exporter:9100` | `/metrics` |

To add a new scrape target:
1. Add a new job entry to `infra/monitoring/prometheus.yml`
2. The container name must be DNS-resolvable within the Docker Compose network
3. For prod, ensure the service is in the `app_network` in `docker-compose.prod.yaml.j2`

**Grafana dashboards** are provisioned automatically:
- Dashboard JSON: `infra/monitoring/grafana/dashboards/platform-overview.json`
- Provisioning config: `infra/monitoring/grafana/provisioning/dashboards/default.yml`
- Datasource config: `infra/monitoring/grafana/provisioning/datasources/prometheus.yml`

To add a new dashboard:
1. Create the dashboard in Grafana UI, then export as JSON
2. Save the JSON to `infra/monitoring/grafana/dashboards/`
3. It will be auto-provisioned on next deploy (the provisioning config scans the folder)

**Node Exporter** exposes host-level metrics (CPU, memory, disk, network) inside both dev and prod compose stacks. It mounts the host root filesystem read-only at `/host` and runs in the host PID namespace for accurate metrics.

## Infrastructure: Bootstrap vs Deploy

The infrastructure is split into two Ansible playbooks:

### bootstrap.yml — One-time server setup

Run once on a fresh VPS (or when infrastructure components change):

```bash
# Via GitHub Actions: Actions → Bootstrap Infrastructure → Run workflow
# Or manually:
DEPLOY_CF_API_TOKEN=<token> ansible-playbook -i infra/ansible/inventory.ini infra/ansible/bootstrap.yml --limit vps --ask-become-pass
```

Bootstrap handles:
- Docker CE + Docker Compose plugin installation
- Host Nginx installation and enablement
- UFW firewall (ports 22, 80, 443)
- SSL certificate issuance via certbot Cloudflare DNS-01 (or standalone HTTP-01 fallback)
- Auto-renewal cron (daily 12:00 UTC, reloads nginx on renewal)

### playbook.yml — App deployment

Run for every deploy (dev or prod):

```bash
# Dev deploy
DEPLOY_ENV=dev ansible-playbook -i infra/ansible/inventory.ini infra/ansible/playbook.yml --limit vm --ask-become-pass

# Prod deploy (use published 12-char SHA image tag)
DEPLOY_ENV=prod DEPLOY_IMAGE_TAG=<sha12> DEPLOY_DB_PASSWORD=<pw> DEPLOY_SECRET_KEY=<key> ansible-playbook -i infra/ansible/inventory.ini infra/ansible/playbook.yml --limit vps --ask-become-pass
```

Deploy handles:
- Dev: clone repo, build containers from source, start Docker Nginx, expose local.kydyrov.dev through host TLS edge
- Prod: render compose/env/nginx templates, pull GHCR images, run migrations, start stack, validate host nginx config (`nginx -t`), reload host nginx
- Prod requires SSL certificates to already exist (fails with guidance to run `bootstrap.yml` if missing)

Notes:

- `repo_url` already has a safe default in `infra/ansible/group_vars/all.yml`; pass `-e repo_url=...` only when overriding it for a specific run.
- Do not use placeholder URLs like `https://github.com/your/repo.git`.
- For prod, `DEPLOY_IMAGE_TAG` must be a SHA hex string (7-40 chars); the deploy workflow auto-truncates it to 12 chars to match the published GHCR tag format.
- The prod tag must come from a successful `Publish Images` run on `main` (the workflow `sha_short` output).

SSL (production):

- Domain `kydyrov.dev` and `www.kydyrov.dev` are live with Let's Encrypt certificates.
- Certificates are issued by `bootstrap.yml` via certbot Cloudflare DNS-01 challenge (requires `CF_API_TOKEN` secret).
- Certbot renewal cron runs daily at 12:00 UTC and reloads host nginx on success.
- Cloudflare SSL/TLS mode should be set to `Full (strict)` with proxy enabled.
- The deploy playbook checks that certificates exist but does **not** issue them — run `bootstrap.yml` first.

GitHub Actions workflows:

| Workflow | Trigger | Runner | Purpose |
|---|---|---|---|
| `ci.yml` | push, PR | `ubuntu-latest` | Lint, test, build, smoke test |
| `publish-images.yml` | push to `main` | `ubuntu-latest` | Build and push GHCR images |
| `deploy.yml` | manual dispatch | `vm-1` (dev) / `self-hosted` (prod) | Deploy app |
| `auto-deploy-prod.yml` | after Publish Images | `self-hosted` | Auto-deploy prod on main |
| `bootstrap.yml` | manual dispatch | `self-hosted` | One-time server bootstrap |

Deploy details:

- runs on self-hosted runners with smart routing:
  - **Dev deploys** → `vm-1` runner (local Hyper-V Ubuntu server), Ansible runs locally
  - **Prod deploys** → any available self-hosted runner; if runner is `vps-1`, Ansible runs locally; otherwise Ansible connects to the VPS via SSH
- auto deploy uses the published commit SHA (short tag) as the production image tag
- GHCR authentication is performed by Ansible on the target host (not the runner)
- keeps dev source-based and repo-synced on the VM
- renders prod runtime files under `/opt/devops-platform`
- pulls GHCR app images for prod and deploys them without destructive `down/prune` steps
- records `current_release.env` and `previous_release.env` on the server for rollback metadata
- See [.github/RUNNER_SETUP.md](.github/RUNNER_SETUP.md) for runner registration and labeling instructions

Home VM DDNS:

- `local.kydyrov.dev` is intended to point to the home VM, not the VPS.
- The updater lives in [infra/ddns/cloudflare_ddns.py](infra/ddns/cloudflare_ddns.py) and uses only the Python standard library.
- Install it on the home VM with [infra/ansible/ddns.yml](infra/ansible/ddns.yml) using `ansible-playbook -i localhost, -c local infra/ansible/ddns.yml`.
- The Ansible playbook places the script under `/usr/local/lib/devops-platform-ddns/`, installs the systemd timer, renders `/etc/default/cloudflare-ddns`, and starts the updater once immediately.
- The shell installer [infra/ddns/install-cloudflare-ddns.sh](infra/ddns/install-cloudflare-ddns.sh) is still available as a fallback.
- Configure `/etc/default/cloudflare-ddns` from [infra/ddns/cloudflare-ddns.env.example](infra/ddns/cloudflare-ddns.env.example) with your Cloudflare API token, zone name, and record name.
- The timer updates the Cloudflare A record whenever the home WAN IPv4 changes.

Branch policy:

- CI runs on every push and pull request, including `feat/*` branches
- deploy does not run on feature branches
- feature branches cannot trigger auto-deploy (main-only)

Required GitHub secrets:

| Secret | Used by | Purpose |
|---|---|---|
| `BECOME_PASSWORD` | deploy, bootstrap | Optional: Ansible become (sudo) password when passwordless sudo is unavailable |
| `DB_PASSWORD` | deploy | PostgreSQL password (prod only) |
| `SECRET_KEY` | deploy | FastAPI secret key (prod only) |
| `CF_API_TOKEN` | bootstrap | Cloudflare API token for DNS-01 SSL issuance |
| `SSH_PRIVATE_KEY` | deploy, bootstrap | SSH key for remote Ansible when runner is not `vps-1` |
| `SSH_HOST` | deploy, bootstrap | VPS IP address |
| `SSH_USER` | deploy, bootstrap | SSH user on the VPS |

## Operational Flow

- `monitor-worker` runs every minute and records health summaries or service-state changes in `/api/incidents`
- the API queues service-action intent, and `action-runner` executes allowed actions asynchronously
- service action outcomes are written back to the same log so the AI assistant can reuse them later
- logged incidents or events can be selected in the Incident Assistant to autofill the form, but manual analysis still works without a selection

## Notes

- `docker-compose.dev.yaml` is the active working environment; dev uses Docker Nginx behind a host TLS edge on the VM
- `local.kydyrov.dev` is the public HTTPS entrypoint for the dev VM, with the host edge terminating TLS on 443 and forwarding into Docker Nginx
- `docker-compose.prod.yaml` is rendered from `infra/ansible/templates/docker-compose.prod.yaml.j2`; prod does **not** include an Nginx container — host Nginx handles all traffic
- `apps/devops-platform/nginx/prod.conf` is a reference file only; the actual prod config is rendered from `infra/ansible/templates/prod.conf.j2` to `/etc/nginx/conf.d/kydyrov.dev.conf`
- frontend is a Vite + React + TypeScript app; `/resume/` is handled by the SPA and the PDF is shipped from `apps/devops-platform/frontend/public/resume/`
- Postgres data lives in a named volume and is preserved across deploys
- Schema and release-bound data changes should be done through Alembic migrations
- services have an `environment` field (`dev`, `production`, or `all`); the overview API and monitor-worker only probe services whose environment matches the runtime `ENVIRONMENT` or is `all`
- dev startup runs `alembic upgrade head` inside the backend container; that is convenient for single-instance local work, while prod uses a separate one-shot migration step
- Production deploys must use immutable SHA image tags; the deploy workflow rejects `main` as an image tag
- SSL is live on `kydyrov.dev` with Let's Encrypt certificates issued via `bootstrap.yml`
- Production secrets (`DB_PASSWORD`, `SECRET_KEY`) are required and have no defaults — deploy fails if not provided

## Security Notes

- `monitor-worker` and `action-runner` mount `/var/run/docker.sock`, which gives high-privilege Docker control inside those containers
- values in `.env.dev` are development-only defaults and must not be reused for production secrets
- production `db_password` and `secret_key` have no fallback defaults; they must be provided via GitHub Secrets or environment variables
- UFW firewall on prod restricts inbound to ports 22, 80, 443 only (configured by `bootstrap.yml`)

## How to Add a New Service

Adding a new service to the platform involves these steps:

### 1. Create the service code

Place the service under `apps/devops-platform/` (or a new `apps/<service-name>/` directory for a standalone app). Include a `Dockerfile` and a health endpoint.

### 2. Add to Docker Compose

**Dev** (`apps/devops-platform/docker-compose.dev.yaml`):
```yaml
  my-service:
    build:
      context: .
      dockerfile: my-service/Dockerfile
    container_name: my_service
    restart: unless-stopped
    expose:
      - "8001"
    depends_on:
      db:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8001/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 20s
```

**Prod** (`infra/ansible/templates/docker-compose.prod.yaml.j2`):
```yaml
  my-service:
    image: ghcr.io/${GHCR_OWNER}/devops-platform-my-service:${IMAGE_TAG}
    container_name: my_service_prod
    restart: unless-stopped
    ports:
      - "127.0.0.1:8001:8001"
    networks:
      - app_network
```

### 3. Add Nginx routing

**Dev** (`apps/devops-platform/nginx/dev.conf`): Add a `location` block with Docker DNS resolution.

**Prod** (`infra/ansible/templates/prod.conf.j2`): Add an `upstream` block and a `location` block:
```nginx
upstream app_my_service {
    server 127.0.0.1:8001;
}

# Inside the server block:
location /my-service/ {
    proxy_pass http://app_my_service;
    ...
}
```

### 4. Add Prometheus monitoring

Add a scrape target to `infra/monitoring/prometheus.yml` if the service exposes metrics.

### 5. Add CI/CD

- Add the Dockerfile build + push step to `publish-images.yml`
- Add the image manifest check to the playbook's GHCR verification loop
- Ensure the service's Docker Compose healthcheck is compatible with the image

### 6. Register in the platform

Create the service via the API (`POST /api/services`) or the portal UI so the monitor-worker can probe it.

## Troubleshooting

### Common issues

**Deploy fails with "SSL certificates not found"**
Run the Bootstrap Infrastructure workflow first: Actions → Bootstrap Infrastructure → Run workflow. The deploy playbook does not issue certificates — it only checks they exist.

**Deploy fails with "Production deploys must use an immutable SHA tag"**
Provide the 12-char SHA tag from a successful `Publish Images` run. Do not use `main` as the image tag.

**Health check fails during deploy**
The playbook polls `/health` up to 15 times (4s apart). If backend startup takes longer:
- Check container logs: `docker compose -f docker-compose.prod.yaml logs backend`
- Verify DB is healthy: `docker inspect --format='{{.State.Health.Status}}' devops_db_prod`
- Ensure `DB_PASSWORD` and `SECRET_KEY` secrets are correctly set

**Nginx config test fails (`nginx -t`)**
The rendered config at `/etc/nginx/conf.d/kydyrov.dev.conf` has a syntax error. Review the template at `infra/ansible/templates/prod.conf.j2`. The playbook runs `nginx -t` before reload to prevent broken configs.

**Grafana shows "No data"**
- Check Prometheus targets: `http://localhost/prometheus/targets` (dev) or `https://kydyrov.dev/prometheus/targets` (prod)
- Ensure the backend container is healthy and exposing `/metrics` on port 8000
- Verify the Grafana datasource points to `http://prometheus:9090` (inside Docker network)

**Monitor-worker not recording sweeps**
- Verify the container is running: `docker ps | grep monitor_worker`
- Check logs: `docker logs monitor_worker` (dev) or `docker logs monitor_worker_prod` (prod)
- The worker requires the Docker socket mount (`/var/run/docker.sock`) to probe containers

**CI smoke tests fail with timeout**
The smoke tests wait up to 120 seconds. If containers start slowly on the CI runner, check that the Docker Compose build completes and all healthchecks pass.

**DB migration fails**
- Dev: migration runs inside the backend container on startup (`alembic upgrade head`)
- Prod: migration runs as a one-shot `docker compose run --rm backend alembic ...` step before the stack starts
- If it fails, check the Alembic migration files in `backend/alembic/versions/`

## Next Improvements

- replace the demo AI endpoint with a real model-backed service or RAG layer
- add targeted tests for incident autofill and service actions
- add more Grafana dashboards (per-service detail, database metrics, node-exporter host panels)
- add subdomain routing for multi-service support (e.g. `api.kydyrov.dev`)
- create app template skeleton for onboarding new services
