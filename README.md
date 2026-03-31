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
- build metadata footer with app version, image tag, build id, and pinned component versions
- Nginx reverse proxy on the VM
- Ansible-based deployment
- GitHub Actions CI
- self-hosted GitHub Actions deploy runner on the VM

## Current Architecture

```text
GitHub Actions
    ↓
Self-hosted runner (vm-1 or vps-1)
    ↓
Ansible (local or SSH to VPS)
    ↓
Docker Compose
    ↓
Nginx (HTTPS on prod)
  ├─ /        -> frontend
  ├─ /api/*   -> FastAPI backend
  └─ /health  -> backend health check
```

- `monitor-worker` is a separate demo worker container that records operational log sweeps into the incident log.
- `action-runner` is a hidden executor container that processes queued service-action jobs so the API never talks to Docker directly.

## Tech Stack

- Python 3.11
- FastAPI
- SQLAlchemy
- PostgreSQL
- Nginx
- Docker / Docker Compose
- Ansible
- GitHub Actions

## Project Structure

```text
app/
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
    Dockerfile
  nginx/
    dev.conf
    prod.conf

infra/
  ansible/
    ansible.cfg
    inventory.ini
    playbook.yml
    group_vars/
      all.yml

.github/workflows/
  ci.yml
  deploy.yml
  auto-deploy-prod.yml
  publish-images.yml
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
docker compose --env-file .env.dev -f docker-compose.dev.yaml up --build
```

Then open:

- `http://localhost/`
- `http://localhost/health`
- `http://localhost/api/portfolio/projects`

## Tests

```bash
cd app
DATABASE_URL=sqlite:// python -m pytest backend/tests/ -v
```

Tests use an in-memory SQLite database — no Postgres required. CI runs them automatically on every push.

## VM Deploy

Manual deploy:

```bash
DEPLOY_ENV=dev DEPLOY_REPO_REF=main ansible-playbook -i infra/ansible/inventory.ini infra/ansible/playbook.yml --ask-become-pass
```

Canonical commands (current inventory groups):

```bash
# Dev deploy to VPS host group
DEPLOY_ENV=dev ansible-playbook -i infra/ansible/inventory.ini infra/ansible/playbook.yml --limit vps --ask-become-pass -e "repo_url=https://github.com/bkolubenka/devops-platform.git repo_version=main"

# Dev deploy to VM host group
DEPLOY_ENV=dev ansible-playbook -i infra/ansible/inventory.ini infra/ansible/playbook.yml --limit vm --ask-become-pass

# Prod deploy to VPS host group (use published 12-char SHA image tag)
DEPLOY_ENV=prod DEPLOY_IMAGE_TAG=<sha12> DEPLOY_DB_PASSWORD=<db_password> DEPLOY_SECRET_KEY=<secret_key> ansible-playbook -i infra/ansible/inventory.ini infra/ansible/playbook.yml --limit vps --ask-become-pass
```

Notes:

- `repo_url` already has a safe default in `infra/ansible/group_vars/all.yml`; pass `-e repo_url=...` only when overriding it for a specific run.
- Do not use placeholder URLs like `https://github.com/your/repo.git`.
- For prod, `DEPLOY_IMAGE_TAG` must match the published GHCR tag format (`^[0-9a-f]{12}$`).
- The prod tag must come from a successful `Publish Images` run on `main` (the workflow `sha_short` output).

SSL (production):

- Domain `kydyrov.dev` and `www.kydyrov.dev` are live with Let's Encrypt certificates.
- Certificates are issued automatically during deploy via certbot Cloudflare DNS-01 challenge (requires `CF_API_TOKEN` secret).
- Certbot renewal cron runs daily at 12:00 UTC, copies renewed certs into the runtime directory, and restarts nginx.
- Cloudflare SSL/TLS mode should be set to `Full (strict)` with proxy enabled.

GitHub Actions deploy:

- runs on self-hosted runners with smart routing:
  - **Dev deploys** → `vm-1` runner (local VirtualBox VM), Ansible runs locally
  - **Prod deploys** → any available self-hosted runner; if runner is `vps-1`, Ansible runs locally; otherwise Ansible connects to the VPS via SSH
- is triggered manually with `workflow_dispatch` (dev or prod selector)
- also supports automatic prod deploy after successful `Publish Images` on `main` (any self-hosted runner)
- auto deploy uses the published commit SHA (short tag) as the production image tag
- GHCR authentication is performed by Ansible on the target host (not the runner)
- keeps dev source-based and repo-synced on the VM
- renders prod runtime files under `/opt/devops-platform`
- pulls GHCR app images for prod and deploys them without destructive `down/prune` steps
- records `current_release.env` and `previous_release.env` on the server for rollback metadata
- SSL certificates are issued via certbot with Cloudflare DNS-01 challenge
- See [.github/RUNNER_SETUP.md](.github/RUNNER_SETUP.md) for runner registration and labeling instructions

Branch policy:

- CI runs on every push and pull request, including `feat/*` branches
- deploy does not run on feature branches
- feature branches cannot trigger auto-deploy (main-only)

Required GitHub secrets:

- `BECOME_PASSWORD` — Ansible become (sudo) password
- `DB_PASSWORD` — PostgreSQL password
- `SECRET_KEY` — FastAPI secret key
- `CF_API_TOKEN` — Cloudflare API token for DNS-01 SSL issuance
- `SSH_PRIVATE_KEY` — SSH key for remote Ansible when runner is not `vps-1`
- `SSH_HOST` — VPS IP address
- `SSH_USER` — SSH user on the VPS

## Operational Flow

- `monitor-worker` runs every minute and records health summaries or service-state changes in `/api/incidents`
- the API queues service-action intent, and `action-runner` executes allowed actions asynchronously
- service action outcomes are written back to the same log so the AI assistant can reuse them later
- logged incidents or events can be selected in the Incident Assistant to autofill the form, but manual analysis still works without a selection

## Notes

- `docker-compose.dev.yaml` is the active working environment
- `docker-compose.prod.yaml` is registry-backed for backend, frontend, monitor-worker, and the hidden action-runner
- Postgres data lives in a named volume and is preserved across deploys
- Schema and release-bound data changes should be done through Alembic migrations
- dev startup runs `alembic upgrade head` inside the backend container; that is convenient for single-instance local work, while prod uses a separate one-shot migration step
- Production deploys should use immutable SHA image tags rather than mutable tags like `main`
- SSL is live on `kydyrov.dev` with Let's Encrypt certificates issued via Cloudflare DNS-01

## Security Notes

- `monitor-worker` and `action-runner` mount `/var/run/docker.sock`, which gives high-privilege Docker control inside those containers
- values in `.env.dev` are development-only defaults and must not be reused for production secrets

## Next Improvements

- move development defaults from `.env.dev` to a non-committed local env workflow
- replace the demo AI endpoint with a real model-backed service or RAG layer
- split Nginx config cleanly for dev vs prod
- add targeted tests for incident autofill and service actions
