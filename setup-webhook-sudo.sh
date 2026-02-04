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
www-data ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart dryrun-bot
www-data ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart dryrun-dashboard
www-data ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart doris_art
www-data ALL=(ALL) NOPASSWD: /usr/bin/git fetch *
www-data ALL=(ALL) NOPASSWD: /usr/bin/git reset *
www-data ALL=(ALL) NOPASSWD: /usr/bin/npm install
www-data ALL=(ALL) NOPASSWD: /usr/bin/npm run build
www-data ALL=(ALL) NOPASSWD: /usr/bin/pm2 restart *
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
