# AGENTS.md

Guidance for coding agents working in this repository.

## Project Summary

This repository is a VM-based DevOps pet project with:

- FastAPI backend
- static frontend
- PostgreSQL
- Nginx reverse proxy
- Ansible deployment
- GitHub Actions CI
- GHCR-backed production images for app services
- self-hosted deploy runner on the VM
- monitor-worker demo service and operational log
- Alembic migrations for schema and release-bound data changes

## Source Of Truth

- Treat the current codebase as the source of truth.
- Keep code, workflows, Ansible, Docker Compose, and README aligned.
- Do not claim features exist unless they are present and working in the repository.

## Deployment Model

- Deployments are driven by `infra/ansible/playbook.yml`.
- GitHub Actions deploy runs on a self-hosted Linux runner installed on the VM.
- The deploy workflow executes Ansible locally on the VM through a generated local inventory and is triggered manually.
- `BECOME_PASSWORD` is the current GitHub secret required for deploy.
- Production app services are pulled from GHCR; dev still builds from source locally.
- Prod runtime files are rendered into `/opt/devops-platform`; prod should not depend on an app git checkout on the server.
- CI runs on every push and pull request, including `feat/*` branches.
- Deploy does not run from feature branches.

## Working Rules

- Prefer small, working, verifiable changes over broad speculative rewrites.
- Avoid introducing manual server setup unless explicitly requested.
- Preserve the working `/`, `/api/*`, and `/health` routing behavior.
- Keep Ansible idempotent and readable.
- Prefer variables in `infra/ansible/group_vars/all.yml` over scattered hardcoding.
- Keep backend package/import layout compatible with the backend Docker image.
- Use healthchecks only with commands available inside the image.
- Keep Postgres data persistent across deploys; do not remove the named volume in normal deploys.
- Keep the build metadata footer aligned with the actual deploy tag, build id, and pinned component versions.
- Keep the monitor-worker stoppable/startable without making the control plane inaccessible.
- Keep the API limited to recording service-action intent; async workers should execute Docker actions.
- Treat service actions and monitor-worker sweeps as reusable operational history for the incident assistant.

## Be Careful About

- Dev and prod Nginx behavior are different concerns.
- Production domain and SSL behavior are not fully finalized yet.
- Documentation should reflect current implementation, not aspirational architecture.
- CI/CD changes should match the actual runner and deployment setup already in use.

## Good Next Steps

- move DB credentials and other config to env-based secrets management
- extend or add Alembic migrations for schema and release-bound data changes
- split dev/prod Nginx configuration cleanly
- improve application usefulness before adding more infrastructure complexity
- extend incident history before adding a real LLM or RAG layer
