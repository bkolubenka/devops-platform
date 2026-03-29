# Copilot Instructions

Keep changes aligned with the current VM-based deployment model.

## Project Facts

- FastAPI backend serves `/health` and `/api/*`.
- Static frontend is served by Nginx.
- Dev and prod Nginx configs are separate.
- Deploy runs on a self-hosted Linux runner on the VM and executes Ansible locally.
- GitHub Actions CI runs on every push and pull request, including `feat/*` branches.
- Deploy is manual and should not run from feature branches.

## Working Rules

- Prefer small, verifiable changes.
- Do not invent features that are not in the repo.
- Keep `README.md`, `AGENTS.md`, workflows, Ansible, and compose files consistent.
- Preserve the `/`, `/api/*`, and `/health` routing contract.
- Keep healthchecks and Dockerfile entrypoints compatible with the actual image layout.
- Use `infra/ansible/group_vars/all.yml` for shared Ansible variables.
