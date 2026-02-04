#!/bin/bash
# Run this on your VPS to allow webhook handler to restart services without password
# Usage: sudo bash setup-webhook-sudo.sh

if [ "$EUID" -ne 0 ]; then 
  echo "Please run as root: sudo bash setup-webhook-sudo.sh"
  exit 1
fi

echo "Setting up passwordless sudo for webhook deployments..."

# Create sudoers file for webhook
cat > /etc/sudoers.d/webhook-deploy << 'EOF'
# Allow web server (www-data) to restart services for webhook deployments
# Security: Limited to specific services and commands only

# Systemd service restarts (specific services only)
www-data ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart dryrun-bot
www-data ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart dryrun-dashboard
www-data ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart doris_art

# Git commands (restricted to specific repos)
www-data ALL=(ALL) NOPASSWD: /usr/bin/git -C /var/www/html/codelabhaven/projects/dryrun fetch origin main
www-data ALL=(ALL) NOPASSWD: /usr/bin/git -C /var/www/html/codelabhaven/projects/dryrun reset --hard origin/main
www-data ALL=(ALL) NOPASSWD: /usr/bin/git -C /var/www/html/codelabhaven/projects/bodysense fetch origin main
www-data ALL=(ALL) NOPASSWD: /usr/bin/git -C /var/www/html/codelabhaven/projects/bodysense reset --hard origin/main
www-data ALL=(ALL) NOPASSWD: /usr/bin/git -C /var/www/html/codelabhaven/projects/doris_art fetch origin main
www-data ALL=(ALL) NOPASSWD: /usr/bin/git -C /var/www/html/codelabhaven/projects/doris_art reset --hard origin/main
www-data ALL=(ALL) NOPASSWD: /usr/bin/git -C /var/www/html/codelabhaven/projects/movie_night fetch origin main
www-data ALL=(ALL) NOPASSWD: /usr/bin/git -C /var/www/html/codelabhaven/projects/movie_night reset --hard origin/main
www-data ALL=(ALL) NOPASSWD: /usr/bin/git -C /var/www/html/codelabhaven/projects/crypto_folio fetch origin main
www-data ALL=(ALL) NOPASSWD: /usr/bin/git -C /var/www/html/codelabhaven/projects/crypto_folio reset --hard origin/main
www-data ALL=(ALL) NOPASSWD: /usr/bin/git -C /var/www/html/codelabhaven/projects/cmdhub fetch origin main
www-data ALL=(ALL) NOPASSWD: /usr/bin/git -C /var/www/html/codelabhaven/projects/cmdhub reset --hard origin/main
www-data ALL=(ALL) NOPASSWD: /usr/bin/git -C /var/www/html/codelabhaven/projects/nyan fetch origin main
www-data ALL=(ALL) NOPASSWD: /usr/bin/git -C /var/www/html/codelabhaven/projects/nyan reset --hard origin/main
www-data ALL=(ALL) NOPASSWD: /usr/bin/git -C /var/www/html/codelabhaven/projects/pixly fetch origin main
www-data ALL=(ALL) NOPASSWD: /usr/bin/git -C /var/www/html/codelabhaven/projects/pixly reset --hard origin/main
www-data ALL=(ALL) NOPASSWD: /usr/bin/git -C /var/www/html/codelabhaven/projects/deployment_guide fetch origin main
www-data ALL=(ALL) NOPASSWD: /usr/bin/git -C /var/www/html/codelabhaven/projects/deployment_guide reset --hard origin/main
www-data ALL=(ALL) NOPASSWD: /usr/bin/git -C /var/www/html/codelabhaven fetch origin main
www-data ALL=(ALL) NOPASSWD: /usr/bin/git -C /var/www/html/codelabhaven reset --hard origin/main

# NPM and PM2 (specific directory only for doris_art)
www-data ALL=(ALL) NOPASSWD: /usr/bin/npm --prefix /var/www/html/codelabhaven/projects/doris_art install
www-data ALL=(ALL) NOPASSWD: /usr/bin/npm --prefix /var/www/html/codelabhaven/projects/doris_art run build
www-data ALL=(ALL) NOPASSWD: /usr/bin/pm2 restart doris_art
EOF

# Set correct permissions
chmod 0440 /etc/sudoers.d/webhook-deploy

# Verify syntax
if visudo -c -f /etc/sudoers.d/webhook-deploy; then
  echo "✅ Sudoers file created successfully!"
  echo "Webhook deployments can now restart services without password."
else
  echo "❌ Error in sudoers file! Removing..."
  rm /etc/sudoers.d/webhook-deploy
  exit 1
fi
