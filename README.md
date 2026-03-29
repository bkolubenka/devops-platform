# DevOps Platform

Containerized fullstack pet project deployed to an Ubuntu VM with Ansible, Docker Compose, Nginx, PostgreSQL, and GitHub Actions.

## What This Project Shows

- FastAPI backend with portfolio, service catalog, overview, operational log, and incident-assistant AI endpoints
- static frontend served separately from the backend
- PostgreSQL-backed persistence
- Alembic migrations for schema and release data changes
- CRUD management for projects, services, incidents, and operational log entries
- service-aware incident assistant with deterministic runbook guidance and incident autofill
- monitor-worker demo service that records platform health summaries and state transitions
- Nginx reverse proxy on the VM
- Ansible-based deployment
- GitHub Actions CI
- self-hosted GitHub Actions deploy runner on the VM

## Current Architecture

```text
GitHub Actions
    ↓
Self-hosted runner on Ubuntu VM
    ↓
Ansible
    ↓
Docker Compose
    ↓
Nginx
  ├─ /        -> frontend
  ├─ /api/*   -> FastAPI backend
  └─ /health  -> backend health check
```

- `monitor-worker` is a separate demo worker container that records operational log sweeps and incident history.

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
```

## Application Routes

- `/` -> frontend
- `/health` -> health check through Nginx
- `/api/health` -> backend health check
- `/api/overview`
- `/api/portfolio/projects`
- `/api/portfolio/skills`
- `/api/services`
- `/api/services/{id}/actions`
- `/api/incidents`
- `/api/incidents/{id}`
- `/api/ai/incidents/analyze`
- `/api/ai/generate-text`
- `/api/ai/models`

## Local Run

```bash
docker-compose -f docker-compose.dev.yaml up --build
```

Then open:

- `http://localhost/`
- `http://localhost/health`
- `http://localhost/api/portfolio/projects`

## VM Deploy

Manual deploy:

```bash
DEPLOY_ENV=dev DEPLOY_REPO_REF=main ansible-playbook -i infra/ansible/inventory.ini infra/ansible/playbook.yml --ask-become-pass
```

GitHub Actions deploy:

- runs on a self-hosted runner installed on the VM
- executes the Ansible playbook locally on that VM
- is triggered manually with `workflow_dispatch`
- updates application code on the VM via `git pull` strategy instead of Ansible file copy

Branch policy:

- CI runs on every push and pull request, including `feat/*` branches
- deploy does not run on feature branches

Required GitHub secret:

- `BECOME_PASSWORD`

## Operational Flow

- `monitor-worker` runs every minute and records health summaries or service-state changes in the incident log
- service action outcomes are written back to the same log so the AI assistant can reuse them later
- logged incidents or events can be selected in the Incident Assistant to autofill the form, but manual analysis still works without a selection

## Notes

- `docker-compose.dev.yaml` is the active working environment
- `docker-compose.prod.yaml` is the production-oriented compose file and should be treated as evolving configuration
- Postgres data lives in a named volume and is preserved across deploys
- Schema and release-bound data changes should be done through Alembic migrations
- SSL/domain configuration exists in the repo, but should be finalized only when a real domain is ready

## Next Improvements

- move hardcoded development database credentials to env files
- replace the demo AI endpoint with a real model-backed service or RAG layer
- split Nginx config cleanly for dev vs prod
- add targeted tests for incident autofill and service actions
