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
- self-hosted deploy runners (`vps-1` on VPS, `vm-1` on local VM)
- monitor-worker demo service and operational log
- Alembic migrations for schema and release-bound data changes

## Source Of Truth

- Treat the current codebase as the source of truth.
- Keep code, workflows, Ansible, Docker Compose, and README aligned.
- Do not claim features exist unless they are present and working in the repository.

## Deployment Model

- Deployments are driven by `infra/ansible/playbook.yml`.
- Dev deploys run on `vm-1` (local VirtualBox VM); Ansible executes locally.
- Prod deploys run on any available self-hosted runner (`vps-1` preferred). When the runner is `vps-1`, Ansible runs locally; otherwise it connects to the VPS via SSH.
- Auto-deploy to prod triggers after successful `Publish Images` on `main` (any self-hosted runner).
- Required GitHub secrets: `BECOME_PASSWORD`, `DB_PASSWORD`, `SECRET_KEY`, `CF_API_TOKEN`, `SSH_PRIVATE_KEY`, `SSH_HOST`, `SSH_USER`.
- Production app services are pulled from GHCR; dev still builds from source locally.
- GHCR authentication is performed by Ansible on the target host.
- Prod runtime files are rendered into `/opt/devops-platform`; prod should not depend on an app git checkout on the server.
- SSL is live on `kydyrov.dev` via Let's Encrypt + Cloudflare DNS-01.
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

## Infrastructure Rules (Strict)

- Do NOT suggest manual fixes on the server.
- All infrastructure changes MUST be implemented via Ansible.
- If something is missing on the server (e.g. docker compose plugin), update the playbook instead of suggesting manual installation.
- The system must work on a fresh VM with a single Ansible run.
- Do NOT assume the server has preinstalled dependencies.

## Docker Rules

- Use `docker compose` (v2) only. Never use `docker-compose`.
- The Ansible playbook must install docker compose plugin.
- Do NOT suggest container cleanup commands as part of normal workflow:
  - docker rm
  - docker system prune
- Do NOT introduce destructive operations into deployment.

## Deployment Behavior

- Prefer permanent fixes over temporary workarounds.
- Do NOT suggest one-time manual fixes.
- Deployment must remain idempotent.
- Fix root causes in infrastructure code, not runtime hacks.

## Be Careful About

- Dev and prod Nginx behavior are different concerns.
- Production SSL is live (`kydyrov.dev`); changes to cert issuance or Nginx TLS config affect a running site.
- Documentation should reflect current implementation, not aspirational architecture.
- CI/CD changes should match the actual runner and deployment setup already in use.

## Good Next Steps

- move DB credentials and other config to env-based secrets management
- extend or add Alembic migrations for schema and release-bound data changes
- split dev/prod Nginx configuration cleanly
- improve application usefulness before adding more infrastructure complexity
- extend incident history before adding a real LLM or RAG layer
