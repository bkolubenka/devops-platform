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
- self-hosted deploy runner on the VM

## Source Of Truth

- Treat the current codebase as the source of truth.
- Keep code, workflows, Ansible, Docker Compose, and README aligned.
- Do not claim features exist unless they are present and working in the repository.

## Deployment Model

- Deployments are driven by `infra/ansible/playbook.yml`.
- GitHub Actions deploy runs on a self-hosted Linux runner installed on the VM.
- The deploy workflow executes Ansible locally on the VM through a generated local inventory.
- `BECOME_PASSWORD` is the current GitHub secret required for deploy.

## Working Rules

- Prefer small, working, verifiable changes over broad speculative rewrites.
- Avoid introducing manual server setup unless explicitly requested.
- Preserve the working `/`, `/api/*`, and `/health` routing behavior.
- Keep Ansible idempotent and readable.
- Prefer variables in `infra/ansible/group_vars/all.yml` over scattered hardcoding.
- Keep backend package/import layout compatible with the backend Docker image.
- Use healthchecks only with commands available inside the image.

## Be Careful About

- Dev and prod Nginx behavior are different concerns.
- Production domain and SSL behavior are not fully finalized yet.
- Documentation should reflect current implementation, not aspirational architecture.
- CI/CD changes should match the actual runner and deployment setup already in use.

## Good Next Steps

- move DB credentials and other config to env-based secrets management
- add database migrations
- split dev/prod Nginx configuration cleanly
- improve application usefulness before adding more infrastructure complexity
