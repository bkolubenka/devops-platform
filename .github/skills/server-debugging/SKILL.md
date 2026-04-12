---
name: server-debugging
description: "Use when debugging this project's servers, deployments, or terminals on vm-1, vps-1, or WSL. Start by identifying the current execution context and whether the terminal is already on the target machine before assuming SSH is needed."
---

# Server Debugging

Use this skill for server-side issues in this repository, especially when the active terminal may already be on vm-1, vps-1, or inside WSL.

## Start State

Before changing anything, identify where you are now.

This step is mandatory. Do not run server checks, SSH commands, Ansible commands, or service commands until this context check is completed and reported.

Run these checks in the current terminal:

```bash
hostname
whoami
pwd
uname -a
test -d /mnt/c && echo WSL || echo Native-Linux
systemd-detect-virt 2>/dev/null || true
git rev-parse --show-toplevel 2>/dev/null || true
```

Interpretation:

- If `hostname` is `vm-1`, stay on the machine and debug locally.
- If `hostname` is `vps-1`, stay on the VPS and debug locally.
- If the shell is WSL, treat it as the development workstation and use SSH or local services as appropriate.
- If the terminal is already on the target server, do not SSH again just to repeat the same checks.

## Ways To Reach Hosts

Use the simplest path that matches the current shell:

- From WSL on the workstation, reach `vm-1` with `ssh make@192.168.10.22`.
- From WSL on the workstation, reach `vps-1` with `ssh make@204.168.184.213`.
- If the current shell is already on `vm-1` or `vps-1`, stay local and inspect the host directly.
- If you need a quick inventory-wide reachability check, use `ansible -i infra/ansible/inventory.ini all -m ping`.
- If you need a deeper health check, use `ansible -i infra/ansible/inventory.ini <host> -m shell -a '<command>'`.
- If you are on Windows outside WSL, open WSL first and use the same SSH commands from there.

## Repository-Specific Context

- `vm-1` is the local/home development server.
- `vps-1` is the production VPS.
- Dev and prod Nginx are different and must be checked in the correct place.
- Production changes must be validated through Ansible and the active host config, not by editing generated files on the server.

## Debugging Flow

1. Confirm the target host and current host.
2. Check the active process or service state relevant to the issue.
3. Inspect the live config on the target machine, not only the repo copy.
4. Reproduce the failure with a minimal command (`curl`, `nginx -t`, `docker compose ps`, `journalctl`, etc.).
5. Compare the live result with the repository source of truth.
6. Fix the root cause in the repo or automation, then redeploy.

## Useful Checks

```bash
docker compose ps
docker ps
sudo nginx -t
sudo systemctl status nginx --no-pager
curl -isk https://example.test/health | sed -n '1,20p'
journalctl -u nginx -n 100 --no-pager
```

Use the smallest command set that proves the failure mode.

## Safety Rules

- Do not assume the terminal is local.
- Do not re-run SSH into a machine that is already the active shell.
- Do not edit generated server files directly when the repo or Ansible template is the source of truth.
- Prefer read-only inspection first, then fix the repo and redeploy.
