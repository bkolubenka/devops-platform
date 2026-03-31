# Copilot Instructions

Keep changes aligned with the current VM-based deployment model.

## VPS Specs (Production)

- Provider: Hetzner, plan CX23
- Name: `devops-platform-prod-1` (ID #125238914)
- IP: `204.168.184.213`, IPv6: `2a01:4f9:c013:37bc::/64`
- Resources: 2 vCPU · 4 GB RAM · 40 GB local disk
- Traffic: 20 TB/mo out · datacenter `hel1-dc2` (Helsinki, EU-central)
- Budget: €3.49/mo — keep memory footprint low; prefer short retention and lightweight services.

## Project Facts

- FastAPI backend serves `/health` and `/api/*`.
- Static frontend is served by Nginx.
- Dev and prod Nginx configs are separate.
- Deploy runs on self-hosted runners with smart routing:
  - Dev deploys use `vm-1` runner (local VirtualBox VM); Ansible runs locally.
  - Prod deploys use any available self-hosted runner; if `vps-1`, Ansible runs locally; otherwise connects via SSH.
- Runners are registered with labels matching their names (`vm-1`, `vps-1`).
- Production app services are published to GHCR and pulled during deploy.
- Production runtime files are rendered under `/opt/devops-platform`; prod should not depend on a repo checkout on the server.
- GitHub Actions CI runs on every push and pull request, including `feat/*` branches.
- Deploy is manual and should not run from feature branches.
- Auto-deploy to prod happens after successful `Publish Images` on main (any self-hosted runner).
- GHCR authentication is performed by Ansible on the target host.
- SSL is live on `kydyrov.dev` via Let's Encrypt + Cloudflare DNS-01.
- Required secrets: `BECOME_PASSWORD`, `DB_PASSWORD`, `SECRET_KEY`, `CF_API_TOKEN`, `SSH_PRIVATE_KEY`, `SSH_HOST`, `SSH_USER`.
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