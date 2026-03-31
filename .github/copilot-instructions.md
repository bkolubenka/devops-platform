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
- **Production Nginx runs on the host** (installed by `bootstrap.yml`), NOT inside Docker. Config is rendered from `infra/ansible/templates/prod.conf.j2` to `/etc/nginx/conf.d/kydyrov.dev.conf`.
- **Dev Nginx runs as a Docker container** inside the compose stack, using `apps/devops-platform/nginx/dev.conf`.
- `apps/devops-platform/nginx/prod.conf` is a reference file only — it is NOT used in production.
- Infrastructure uses a two-phase model: `bootstrap.yml` (one-time server setup) + `playbook.yml` (app deploy).
- `bootstrap.yml` installs Docker, host Nginx, certbot, UFW, issues SSL certificates.
- `playbook.yml` deploys the app; it does NOT issue SSL certificates (fails if missing, with guidance to run bootstrap).
- Deploy runs on self-hosted runners with smart routing:
  - Dev deploys use `vm-1` runner (local VirtualBox VM); Ansible runs locally.
  - Prod deploys use any available self-hosted runner; if `vps-1`, Ansible runs locally; otherwise connects via SSH.
- Runners are registered with labels matching their names (`vm-1`, `vps-1`).
- Production app services are published to GHCR and pulled during deploy.
- Production containers bind to `127.0.0.1` ports (8000, 8080, 3000, 9090) and are only reachable through host Nginx.
- Production runtime files are rendered under `/opt/devops-platform`; prod should not depend on a repo checkout on the server.
- GitHub Actions CI runs on every push and pull request, including `feat/*` branches.
- Deploy is manual and should not run from feature branches.
- Auto-deploy to prod happens after successful `Publish Images` on main (any self-hosted runner).
- GHCR authentication is performed by Ansible on the target host.
- SSL is live on `kydyrov.dev` via Let's Encrypt + Cloudflare DNS-01 (issued by `bootstrap.yml`).
- Required secrets: `BECOME_PASSWORD`, `DB_PASSWORD`, `SECRET_KEY`, `CF_API_TOKEN`, `SSH_PRIVATE_KEY`, `SSH_HOST`, `SSH_USER`.
- Production `db_password` and `secret_key` have NO fallback defaults — deploy fails if not provided.
- `monitor-worker` is a non-critical service that records operational log entries for the incident assistant.
- `node-exporter` exposes host-level metrics (CPU, memory, disk, network) scraped by Prometheus.
- Prometheus + Grafana + Node Exporter observability is provisioned automatically; Grafana has anonymous Viewer access enabled.
- The deploy workflow auto-truncates `DEPLOY_IMAGE_TAG` to 12 chars to match the GHCR tag format.
- Alembic migrations own schema and release-bound data changes.
- UFW firewall on prod restricts inbound to ports 22, 80, 443 (configured by `bootstrap.yml`).

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
- SSL changes belong in `bootstrap.yml`, NOT in `playbook.yml`.
- Prod Nginx config changes belong in `infra/ansible/templates/prod.conf.j2`, NOT in `apps/devops-platform/nginx/prod.conf`.

## Infrastructure Rules (Strict)

- Do NOT suggest manual fixes on the server.
- All infrastructure changes MUST be implemented via Ansible.
- If something is missing on the server (e.g. docker compose plugin), update the playbook instead of suggesting manual installation.
- The system must work on a fresh VM with `bootstrap.yml` followed by `playbook.yml`.
- Do NOT assume the server has preinstalled dependencies.
- SSL certificate issuance is handled by `bootstrap.yml` only. Do not add certbot tasks to `playbook.yml`.

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