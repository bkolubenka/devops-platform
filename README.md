# DevOps Platform

[![CI](https://github.com/bkolubenka/devops-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/bkolubenka/devops-platform/actions/workflows/ci.yml)
[![Deploy](https://github.com/bkolubenka/devops-platform/actions/workflows/deploy.yml/badge.svg)](https://github.com/bkolubenka/devops-platform/actions/workflows/deploy.yml)

Containerized fullstack pet project deployed to an Ubuntu VM with Ansible, Docker Compose, Nginx, PostgreSQL, and GitHub Actions.

## What This Project Shows

- FastAPI backend with portfolio, service catalog, overview, incident log, and incident-assistant AI endpoints
- static frontend served separately from the backend
- PostgreSQL-backed persistence
- Alembic migrations for schema and release data changes
- CRUD management for projects, services, and incidents, with `/api/incidents` also serving as the operational log for monitor-worker sweeps and service-action events
- service-aware incident assistant with deterministic runbook guidance and incident autofill
- monitor-worker demo service that records platform health summaries and state transitions
- worker-mediated service actions so the API queues intent and a separate runner executes it
- GHCR-backed production images for app services
- Prometheus + Grafana + Node Exporter observability stack with provisioned dashboards and embedded live metrics
- build metadata footer with app version, image tag, build id, and pinned component versions
- host-managed Nginx reverse proxy on prod (Docker Nginx on dev)
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
Host Nginx (prod) / Docker Nginx (dev)
  ├─ /        -> frontend (127.0.0.1:8080)
  ├─ /api/*   -> FastAPI backend (127.0.0.1:8000)
  ├─ /health  -> backend health check
  ├─ /grafana/ -> Grafana UI (127.0.0.1:3000)
  └─ /prometheus/ -> Prometheus UI (127.0.0.1:9090)
```

Production Nginx runs on the host (installed by `bootstrap.yml`), not inside Docker.
App containers bind to `127.0.0.1` and are only reachable through the host Nginx reverse proxy.

- `monitor-worker` is a separate demo worker container that records operational log sweeps into the incident log.
- `action-runner` is a hidden executor container that processes queued service-action jobs so the API never talks to Docker directly.
- `node-exporter` exposes host-level metrics (CPU, memory, disk, network) for Prometheus.

## Tech Stack

- Python 3.11
- FastAPI
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
    index.html
    shared-nav.js
    resume/
      index.html
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
    templates/
      docker-compose.prod.yaml.j2
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

## Local Run

```bash
cd apps/devops-platform
docker compose --env-file .env.dev -f docker-compose.dev.yaml up --build
```

Then open:

- `http://localhost/`
- `http://localhost/health`
- `http://localhost/api/portfolio/projects`
- `http://localhost/grafana/`
- `http://localhost/prometheus/`

Dev uses a Docker Nginx container (port 80) that proxies to app containers via Docker DNS.

## Tests

```bash
cd apps/devops-platform
DATABASE_URL=sqlite:// python -m pytest backend/tests/ -v
```

Tests use an in-memory SQLite database — no Postgres required. CI runs them automatically on every push.

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
- Dev: clone repo, build containers from source, start Docker Nginx
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
  - **Dev deploys** → `vm-1` runner (local VirtualBox VM), Ansible runs locally
  - **Prod deploys** → any available self-hosted runner; if runner is `vps-1`, Ansible runs locally; otherwise Ansible connects to the VPS via SSH
- auto deploy uses the published commit SHA (short tag) as the production image tag
- GHCR authentication is performed by Ansible on the target host (not the runner)
- keeps dev source-based and repo-synced on the VM
- renders prod runtime files under `/opt/devops-platform`
- pulls GHCR app images for prod and deploys them without destructive `down/prune` steps
- records `current_release.env` and `previous_release.env` on the server for rollback metadata
- See [.github/RUNNER_SETUP.md](.github/RUNNER_SETUP.md) for runner registration and labeling instructions

Branch policy:

- CI runs on every push and pull request, including `feat/*` branches
- deploy does not run on feature branches
- feature branches cannot trigger auto-deploy (main-only)

Required GitHub secrets:

| Secret | Used by | Purpose |
|---|---|---|
| `BECOME_PASSWORD` | deploy, bootstrap | Ansible become (sudo) password |
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

- `docker-compose.dev.yaml` is the active working environment; dev uses Docker Nginx inside the compose stack
- `docker-compose.prod.yaml` is rendered from `infra/ansible/templates/docker-compose.prod.yaml.j2`; prod does **not** include an Nginx container — host Nginx handles all traffic
- `apps/devops-platform/nginx/prod.conf` is a reference file only; the actual prod config is rendered from `infra/ansible/templates/prod.conf.j2` to `/etc/nginx/conf.d/kydyrov.dev.conf`
- frontend navigation is shared from `apps/devops-platform/frontend/shared-nav.js` and rendered by both `index.html` and `resume/index.html`
- Postgres data lives in a named volume and is preserved across deploys
- Schema and release-bound data changes should be done through Alembic migrations
- dev startup runs `alembic upgrade head` inside the backend container; that is convenient for single-instance local work, while prod uses a separate one-shot migration step
- Production deploys must use immutable SHA image tags; the deploy workflow rejects `main` as an image tag
- SSL is live on `kydyrov.dev` with Let's Encrypt certificates issued via `bootstrap.yml`
- Production secrets (`DB_PASSWORD`, `SECRET_KEY`) are required and have no defaults — deploy fails if not provided

## Security Notes

- `monitor-worker` and `action-runner` mount `/var/run/docker.sock`, which gives high-privilege Docker control inside those containers
- values in `.env.dev` are development-only defaults and must not be reused for production secrets
- production `db_password` and `secret_key` have no fallback defaults; they must be provided via GitHub Secrets or environment variables
- UFW firewall on prod restricts inbound to ports 22, 80, 443 only (configured by `bootstrap.yml`)

## Next Improvements

- replace the demo AI endpoint with a real model-backed service or RAG layer
- add targeted tests for incident autofill and service actions
- add more Grafana dashboards (per-service detail, database metrics, node-exporter host panels)
- add subdomain routing for multi-service support (e.g. `api.kydyrov.dev`)
- create app template skeleton for onboarding new services
