# DevOps Platform

Containerized fullstack pet project deployed to an Ubuntu VM with Ansible, Docker Compose, Nginx, PostgreSQL, and GitHub Actions.

## What This Project Shows

- FastAPI backend with portfolio and demo AI endpoints
- static frontend served separately from the backend
- PostgreSQL-backed persistence
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
    database.py
    models.py
    requirements.txt
    Dockerfile
  frontend/
    index.html
    Dockerfile
  nginx/
    default.conf

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
- `/api/portfolio/projects`
- `/api/portfolio/skills`
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
ansible-playbook -i infra/ansible/inventory.ini infra/ansible/playbook.yml --ask-become-pass
```

GitHub Actions deploy:

- runs on a self-hosted runner installed on the VM
- executes the Ansible playbook locally on that VM
- is triggered manually with `workflow_dispatch`

Branch policy:

- CI runs on every push and pull request, including `feat/*` branches
- deploy does not run on feature branches

Required GitHub secret:

- `BECOME_PASSWORD`

## Notes

- `docker-compose.dev.yaml` is the active working environment
- `docker-compose.prod.yaml` is the production-oriented compose file and should be treated as evolving configuration
- SSL/domain configuration exists in the repo, but should be finalized only when a real domain is ready

## Next Improvements

- move hardcoded development database credentials to env files
- add database migrations
- replace demo AI endpoint with a real model-backed service
- split Nginx config cleanly for dev vs prod
- add monitoring and backups
