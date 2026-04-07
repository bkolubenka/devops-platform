# AGENTS.md

Guidance for coding agents working in this repository.

## Project Summary

This repository is a VM-based DevOps pet project with:

- FastAPI backend
- static frontend
- PostgreSQL
- host-managed Nginx reverse proxy on prod (Docker Nginx on dev)
- two-phase Ansible deployment: `bootstrap.yml` (one-time infra) + `playbook.yml` (app deploy)
- GitHub Actions CI with bootstrap, publish, deploy, and auto-deploy workflows
- GHCR-backed production images for app services
- self-hosted deploy runners (`vps-1` on VPS, `vm-1` on local VM)
- monitor-worker demo service and operational log
- Prometheus + Grafana + Node Exporter observability with provisioned dashboards and anonymous Viewer access
- Alembic migrations for schema and release-bound data changes

## Source Of Truth

- Treat the current codebase as the source of truth.
- Keep code, workflows, Ansible, Docker Compose, and README aligned.
- Do not claim features exist unless they are present and working in the repository.

## Two-Phase Deployment Model

Infrastructure is split into two Ansible playbooks:

### bootstrap.yml — One-time server setup
- Installs Docker CE, Docker Compose plugin, host Nginx, certbot, UFW
- Issues SSL certificates via Cloudflare DNS-01 (or standalone HTTP-01 fallback)
- Configures UFW firewall (ports 22, 80, 443)
- Sets up certbot auto-renewal cron (reloads nginx on success)
- Run once on a fresh VPS or when infrastructure components change
- Triggered via GitHub Actions: `Actions → Bootstrap Infrastructure → Run workflow`
- Required secret: `CF_API_TOKEN` for DNS-01 challenge

### playbook.yml — App deployment
- Dev: clones repo, builds containers from source, starts Docker Nginx
- Prod: renders templates, pulls GHCR images, runs migrations, starts stack, validates and reloads host Nginx
- Prod **requires** SSL certificates to already exist (fails with guidance to run `bootstrap.yml` if missing)
- Prod **requires** `DB_PASSWORD` and `SECRET_KEY` (no fallback defaults)

## Deployment Model

- Dev deploys run on `vm-1` (local Hyper-V Ubuntu server); Ansible executes locally.
- Prod deploys run on any available self-hosted runner (`vps-1` preferred). When the runner is `vps-1`, Ansible runs locally; otherwise it connects to the VPS via SSH.
- Auto-deploy to prod triggers after successful `Publish Images` on `main` (any self-hosted runner).
- Required GitHub secrets: `DB_PASSWORD`, `SECRET_KEY`, `CF_API_TOKEN`, `SSH_PRIVATE_KEY`, `SSH_HOST`, `SSH_USER`. `BECOME_PASSWORD` is optional when the deploy user has passwordless sudo.
- Production app services are pulled from GHCR; dev still builds from source locally.
- GHCR authentication is performed by Ansible on the target host.
- Prod runtime files are rendered into `/opt/devops-platform`; prod should not depend on an app git checkout on the server.
- SSL is live on `kydyrov.dev` via Let's Encrypt + Cloudflare DNS-01 (issued by `bootstrap.yml`, not `playbook.yml`).
- CI runs on every push and pull request, including `feat/*` branches.
- Deploy does not run from feature branches.

## Nginx Architecture

- **Production**: Nginx runs on the host (installed by `bootstrap.yml`). Config is rendered from `infra/ansible/templates/prod.conf.j2` to `/etc/nginx/conf.d/kydyrov.dev.conf`. App containers bind to `127.0.0.1` and are only reachable through host Nginx.
- **Dev**: Nginx runs as a Docker container inside the compose stack, using `apps/devops-platform/nginx/dev.conf`. The file `apps/devops-platform/nginx/prod.conf` is a reference only — it is NOT used in production.
- The deploy playbook runs `nginx -t` before reloading to prevent broken configs from taking effect.

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
- The system must work on a fresh VM with a single `bootstrap.yml` run followed by `playbook.yml`.
- Do NOT assume the server has preinstalled dependencies.
- SSL certificates are managed by `bootstrap.yml`, NOT by `playbook.yml`. Do not add certbot tasks to the deploy playbook.

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

- Dev and prod Nginx are fundamentally different: dev uses Docker Nginx, prod uses host Nginx.
- Production SSL is live (`kydyrov.dev`); changes to cert issuance affect `bootstrap.yml`, not `playbook.yml`.
- Grafana is configured for anonymous Viewer access; changes to auth settings affect public dashboard visibility.
- The deploy workflow auto-truncates image tags to 12 chars; do not change this without also updating publish-images.yml.
- Documentation should reflect current implementation, not aspirational architecture.
- CI/CD changes should match the actual runner and deployment setup already in use.
- `apps/devops-platform/nginx/prod.conf` is NOT the active prod config — it's a reference file. The real config is `infra/ansible/templates/prod.conf.j2`.
- Production secrets (`DB_PASSWORD`, `SECRET_KEY`) have no defaults and are required.

## Good Next Steps

- add subdomain routing for multi-service support (e.g. `api.kydyrov.dev`)
- create app template skeleton for onboarding new services
- add more Grafana dashboards (node-exporter host panels, per-service detail, database metrics)
- extend incident history before adding a real LLM or RAG layer
- add targeted tests for incident autofill and service actions

## Observability Rules

- Prometheus scrape config lives in `infra/monitoring/prometheus.yml` — update it when adding new metric endpoints.
- Grafana dashboards are provisioned from `infra/monitoring/grafana/dashboards/` — export JSON from Grafana and commit it.
- Node Exporter is part of both dev and prod compose stacks; it runs in host PID namespace with root filesystem mounted read-only.
- Grafana has anonymous Viewer access enabled; do not change this without considering public dashboard visibility.
- New scrape targets must be in the Docker Compose network so Prometheus can reach them by container name.
- Keep Prometheus retention at 7 days to stay within the 40 GB disk budget.

## Healthcheck Rules

- The `/health` endpoint includes a database connectivity check and returns `{"status": "ok", "database": "ok"}` when healthy.
- Docker Compose healthchecks and the Ansible deploy playbook rely on `status == "ok"` in the health response.
- When extending the healthcheck, add new component keys (e.g. `"cache": "ok"`) and set `status` to `"degraded"` if any fail.
- Do not add slow or external dependency checks to `/health` — it is polled frequently by healthchecks and load balancers.

## Adding a New Service

When adding a new service to the platform:

1. Add it to both `docker-compose.dev.yaml` and `docker-compose.prod.yaml.j2`
2. For prod: bind to `127.0.0.1:<port>`, join `app_network`, add to Nginx template upstream/location
3. For dev: add to Docker Nginx `dev.conf` with Docker DNS resolution
4. Add GHCR image build step to `publish-images.yml`
5. Add image manifest check to the Ansible playbook
6. Add Prometheus scrape target to `infra/monitoring/prometheus.yml` if the service exposes metrics
7. Register the service via the API or portal so the monitor-worker can probe it
