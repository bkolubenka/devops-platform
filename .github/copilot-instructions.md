# Copilot Instructions

Keep changes aligned with the current VM-based deployment model.

## Project Facts

- FastAPI backend serves `/health` and `/api/*`.
- Static frontend is served by Nginx.
- Dev and prod Nginx configs are separate.
- Deploy runs on a self-hosted Linux runner on the VM and executes Ansible locally.
- Production app services are published to GHCR and pulled during deploy.
- Production runtime files are rendered under `/opt/devops-platform`; prod should not depend on a repo checkout on the server.
- GitHub Actions CI runs on every push and pull request, including `feat/*` branches.
- Deploy is manual and should not run from feature branches.
- `monitor-worker` is a non-critical service that records operational log entries for the incident assistant.
- Alembic migrations own schema and release-bound data changes.

## Working Rules

- Prefer small, verifiable changes.
- Do not invent features that are not in the repo.
- Keep `README.md`, `AGENTS.md`, workflows, Ansible, and compose files consistent.
- Preserve the `/`, `/api/*`, and `/health` routing contract.
- Keep healthchecks and Dockerfile entrypoints compatible with the actual image layout.
- Use `infra/ansible/group_vars/all.yml` for shared Ansible variables.
- Keep Postgres data persistent across deploys; normal deploys should not delete the volume.
- Keep the build metadata footer truthful to the current image tag, build id, and pinned component versions.
- Keep control-plane services restart-only from the UI.
- Keep Docker actions out of the API request path; workers should execute queued service actions.
- Keep log entries reusable by the assistant, but do not make autofill mandatory.

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