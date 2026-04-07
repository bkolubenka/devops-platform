#!/bin/bash
# DEPRECATED — This script is no longer used.
# Runner setup is now documented in .github/RUNNER_SETUP.md.
# Infrastructure is provisioned by bootstrap.yml (Docker, Nginx, SSL, UFW).
# This file is kept for historical reference only.
#
# Current deploy uses a self-hosted runner on the Hyper-V Ubuntu server
# and manual GitHub Actions dispatch.

set -e

echo "🔧 Setting up GitHub Actions runner with proper permissions..."

# Install required packages
apt update
apt install -y docker.io docker-compose-plugin certbot python3-certbot-nginx

# Start Docker service
systemctl start docker
systemctl enable docker

# Create actions-runner user if it doesn't exist
if ! id -u actions-runner > /dev/null 2>&1; then
    useradd -m -s /bin/bash actions-runner
    echo "Created actions-runner user"
fi

# Add actions-runner to docker group
usermod -aG docker actions-runner

# Give actions-runner passwordless sudo for deployment tasks
cat > /etc/sudoers.d/actions-runner <<EOF
actions-runner ALL=(ALL) NOPASSWD: ALL
EOF
chmod 0440 /etc/sudoers.d/actions-runner

# Create app directory structure
mkdir -p /home/actions-runner/apps/devops-platform
chown -R actions-runner:actions-runner /home/actions-runner/apps

echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Download and configure GitHub Actions runner as actions-runner user"
echo "2. The runner will now have passwordless sudo access for deployments"
echo "3. CI/CD will work automatically without password prompts"
