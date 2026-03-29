# DevOps Platform

Full-cycle DevOps pet project for deploying a containerized fullstack application to an Ubuntu VM with Infrastructure as Code, reverse proxying, and CI/CD.

## Overview

This project demonstrates a practical deployment workflow:

- `FastAPI` backend
- static frontend served in a separate container
- `Nginx` reverse proxy
- `Docker` and `docker-compose`
- `Ansible` for server provisioning and deployment
- `GitHub Actions` for CI and deployment
- self-hosted GitHub Actions runner on the VM

Current routing:

- `/` -> frontend
- `/api/*` -> FastAPI backend
- `/health` -> backend health endpoint through Nginx

## Architecture

```text
GitHub Actions
    ↓
Self-hosted runner on Ubuntu VM
    ↓
Ansible
    ↓
Docker Compose
    ↓
Nginx -> Frontend + FastAPI
```

Runtime flow:

```text
Browser
  ↓
Nginx :80
  ├─ /        -> frontend container
  ├─ /api/*   -> backend container
  └─ /health  -> backend container
```

## Tech Stack

- Python 3.11
- FastAPI
- Uvicorn
- Nginx
- Docker
- Docker Compose
- Ansible
- GitHub Actions

## Project Structure

```text
app/
  backend/
    Dockerfile
    main.py
    requirements.txt
  frontend/
    index.html
  nginx/
    default.conf

infra/
  ansible/
    group_vars/
      all.yml
    inventory.ini
    playbook.yml

.github/
  workflows/
    ci.yml
    deploy.yml
```

## Features

- Provision Docker and Docker Compose with Ansible
- Copy project files to the VM and redeploy remotely
- Build and run backend/frontend containers with Docker Compose
- Route traffic through Nginx on port `80`
- Validate deployment with `/health`
- Run CI checks on GitHub Actions
- Deploy from GitHub Actions through a self-hosted runner on the VM

## Application Endpoints

- `GET /` -> frontend page
- `GET /health` -> `{"status": "ok"}`
- `GET /api/health` -> `{"status": "ok"}`

## Local Deployment With Ansible

Run from the project root:

```bash
ansible-playbook -i infra/ansible/inventory.ini infra/ansible/playbook.yml --ask-become-pass
```

## CI/CD

### CI

The CI workflow validates:

- Python syntax for the backend
- Ansible playbook syntax

### Deploy

The deploy workflow:

- runs on a self-hosted runner installed on the VM
- creates a local Ansible inventory with `ansible_connection=local`
- executes the deploy playbook directly on the VM

Required GitHub Actions secret:

- `BECOME_PASSWORD`

## Ansible Variables

Main variables are stored in [`infra/ansible/group_vars/all.yml`](infra/ansible/group_vars/all.yml):

- `app_name`
- `app_base_dir`
- `app_dir`
- `compose_file`
- `backend_internal_port`
- `nginx_host_port`
- `healthcheck_url`

## Current Status

Implemented:

- backend container
- frontend container
- Nginx reverse proxy
- Ansible-based deployment
- health checks
- self-hosted GitHub Actions deploy

Planned next:

- environment-based app configuration
- PostgreSQL integration
- monitoring
- production hardening

## Resume Value

This project demonstrates hands-on experience with:

- Infrastructure as Code
- containerized deployments
- reverse proxy configuration
- self-hosted CI/CD runners
- remote service validation
- practical VM-based DevOps workflows
