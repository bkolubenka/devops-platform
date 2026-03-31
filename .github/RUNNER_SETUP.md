# Self-Hosted Runner Setup

This project uses two self-hosted GitHub Actions runners for deployment:

- `vm-1`: Local VirtualBox VM for dev environment
- `vps-1`: Remote VPS for prod environment

## Runner Labels and Requirements

The workflows use runner names as labels to ensure:
- **Dev deploys** run on `vm-1` (local runner only)
- **Prod deploys** run on any available self-hosted runner; if runner is `vps-1`, Ansible runs locally; otherwise connects via SSH
- **Auto-deploy** runs on any available self-hosted runner after Publish Images succeeds on main
- **Bootstrap** runs on any available self-hosted runner (same SSH routing as prod deploy)

This prevents accidental cross-environment deployments and respects network isolation (dev cannot deploy to prod runner due to network constraints).

## How to Register Runners

### Prerequisites

Each runner needs:
- Python 3.11+
- Ansible
- Docker & Docker Compose v2
- Passwordless sudo for the runner user (see below)

### 1. Register `vm-1` (Local VM)

On your local VirtualBox VM, register as the `actions-runner` user:

```bash
# On the VM as root or sudoer
curl -o actions-runner-linux-x64-2.315.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.315.0/actions-runner-linux-x64-2.315.0.tar.gz
tar xzf actions-runner-linux-x64-2.315.0.tar.gz

# Switch to actions-runner user
su - actions-runner

# Go to runner directory and configure
cd actions-runner
./config.sh --url https://github.com/YOUR_USERNAME/devops-platform \
            --token YOUR_REGISTRATION_TOKEN \
            --name vm-1 \
            --runnergroup default \
            --labels "vm-1,self-hosted,linux" \
            --unattended

# Install as service
sudo ./svc.sh install
sudo ./svc.sh start
```

### 2. Register `vps-1` (Remote VPS)

On your remote VPS, register similarly:

```bash
# On the VPS as root or sudoer
curl -o actions-runner-linux-x64-2.315.0.tar.gz -L https://github.com/actions/runner/releases/download/v2.315.0/actions-runner-linux-x64-2.315.0.tar.gz
tar xzf actions-runner-linux-x64-2.315.0.tar.gz

# Switch to actions-runner user
su - actions-runner

# Go to runner directory and configure
cd actions-runner
./config.sh --url https://github.com/YOUR_USERNAME/devops-platform \
            --token YOUR_REGISTRATION_TOKEN \
            --name vps-1 \
            --runnergroup default \
            --labels "vps-1,self-hosted,linux" \
            --unattended

# Install as service
sudo ./svc.sh install
sudo ./svc.sh start
```

### 3. Enable Passwordless Sudo for Actions Runner

On each machine, configure passwordless sudo for the `actions-runner` user:

```bash
# Create sudoers config
sudo tee /etc/sudoers.d/actions-runner > /dev/null <<EOF
actions-runner ALL=(ALL) NOPASSWD: ALL
EOF

sudo chmod 0440 /etc/sudoers.d/actions-runner
```

## Verifying Runner Registration

Visit your GitHub repository's **Settings > Actions > Runners** to confirm both runners appear as:
- `vm-1` - Idle/Active
- `vps-1` - Idle/Active

## Workflow Routing

After proper registration:

| Workflow | Trigger | Runner |
|---|---|---|
| `ci.yml` | push, PR | `ubuntu-latest` (GitHub-hosted) |
| `publish-images.yml` | push to `main` | `ubuntu-latest` (GitHub-hosted) |
| `deploy.yml` (dev) | manual dispatch | `vm-1` |
| `deploy.yml` (prod) | manual dispatch | any `self-hosted` |
| `auto-deploy-prod.yml` | after Publish Images | any `self-hosted, linux` |
| `bootstrap.yml` | manual dispatch | any `self-hosted, linux` |

For prod/bootstrap: if the runner is `vps-1`, Ansible runs locally; otherwise Ansible connects to the VPS via SSH using `SSH_PRIVATE_KEY`, `SSH_HOST`, and `SSH_USER` secrets.

## Fresh Server Setup

For a new VPS, after registering the runner:

1. **Bootstrap**: Go to Actions → Bootstrap Infrastructure → Run workflow
   - This installs Docker, host Nginx, UFW, SSL certificates
2. **Deploy**: Go to Actions → Deploy → Run workflow (select `prod`)
   - This deploys the application stack

Bootstrap only needs to run once (or when infrastructure components change).

## Troubleshooting

- **Runner not appearing**: Verify registration token is valid and not expired. Get new token from Settings > Actions > Runners > New self-hosted runner.
- **Deploy fails with "No runners found for..."**: Check runner names match exactly (`vm-1`, `vps-1`). Verify runner service is running.
- **Sudo password prompt during deploy**: Confirm passwordless sudo is configured and `BECOME_PASSWORD` secret is set in GitHub.
- **SSL certificates missing on deploy**: Run Bootstrap Infrastructure workflow first. The deploy playbook does NOT issue certificates.
- **Nginx config fails**: The deploy playbook runs `nginx -t` before reloading. Check the rendered config at `/etc/nginx/conf.d/kydyrov.dev.conf`.

## References

- [GitHub Actions self-hosted runners](https://docs.github.com/en/actions/hosting-your-own-runners)
- [Adding self-hosted runners](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/adding-self-hosted-runners)
