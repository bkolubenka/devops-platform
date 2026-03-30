# Self-Hosted Runner Setup

This project uses two self-hosted GitHub Actions runners for deployment:

- `vm-1`: Local VirtualBox VM for dev environment
- `vps-1`: Remote VPS for prod environment

## Runner Labels and Requirements

The workflows use runner names as labels to ensure:
- **Dev deploys** run on `vm-1` (local runner only)
- **Prod deploys** run on `vps-1` (remote runner only)
- Auto-deploy pushes to `vps-1` when images are published

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

- **Manual `deploy.yml` dispatch**:
  - When `deploy_env=dev`: uses `vm-1`
  - When `deploy_env=prod`: uses `vps-1`
  
- **Auto `auto-deploy-prod.yml`**: Always uses `vps-1` (triggered after Publish Images succeeds on main)

## Troubleshooting

- **Runner not appearing**: Verify registration token is valid and not expired. Get new token from Settings > Actions > Runners > New self-hosted runner.
- **Deploy fails with "No runners found for..."**: Check runner names match exactly (`vm-1`, `vps-1`). Verify runner service is running.
- **Sudo password prompt during deploy**: Confirm passwordless sudo is configured and `BECOME_PASSWORD` secret is set in GitHub.

## References

- [GitHub Actions self-hosted runners](https://docs.github.com/en/actions/hosting-your-own-runners)
- [Adding self-hosted runners](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/adding-self-hosted-runners)
