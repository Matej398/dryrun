# Dryrun – Git push & webhook deployment

## Env / config

- **No `.env` file is used** to start the bot or dashboard. Config (e.g. Telegram token) is in the Python files.
- State and logs (`paper_state*.json`, `paper_trades*.json`, `paper_log*.txt`) are **not** in git (see `.gitignore`), so they stay on the VPS and are **not** overwritten when you deploy.

## 1. First-time push to GitHub (from VPS or from this machine)

From the **dryrun** project directory (VPS path: `/var/www/html/codelabhaven/projects/dryrun`):

```bash
cd /var/www/html/codelabhaven/projects/dryrun   # or your local path

# If git is not initialized yet
git init
git branch -M main
git remote add origin https://github.com/Matej398/dryrun.git

# Stage and commit (venv and state/log files are ignored by .gitignore)
git add .
git status   # confirm no venv, no .env, no paper_*.json / paper_*.txt
git commit -m "Initial commit: paper trader v3, dashboard, systemd units"

# Push (use your GitHub credentials or a personal access token)
git push -u origin main
```

If the GitHub repo already has a README and you get “unrelated histories”, use:

```bash
git pull origin main --allow-unrelated-histories
# resolve any conflicts, then:
git push -u origin main
```

## 2. GitHub webhook (auto-deploy on push)

1. **Upload the updated webhook handler**  
   Copy your updated `webhook-handler.php` (from Desktop) to the VPS where your other webhooks run (same place as for bodysense, doris_art, etc.).

2. **Add a webhook in GitHub**
   - Repo: https://github.com/Matej398/dryrun  
   - **Settings → Webhooks → Add webhook**
   - **Payload URL:** your existing webhook URL that runs `webhook-handler.php` (same as for other repos).
   - **Content type:** `application/json`
   - **Events:** “Just the push event”
   - Save.

3. **What the webhook does for `dryrun`**
   - Runs `git fetch origin main` and `git reset --hard origin/main` in `/var/www/html/codelabhaven/projects/dryrun`.
   - Restarts systemd services: **dryrun-bot** and **dryrun-dashboard** (so the new code is running without manual restart).

So: **push to `main` → webhook runs → code pulls → bot and dashboard restart automatically.**

## 3. Deploying from your machine (optional)

If you develop locally and want to deploy by pushing:

```bash
cd /path/to/dryrun
git add .
git commit -m "Your change"
git push origin main
```

The webhook on the VPS will pull and restart the services. No need to SSH and restart manually (unless the webhook is down).

## Security considerations

The sudoers configuration is designed with security in mind:

1. **Webhook signature verification**: The webhook handler verifies GitHub's HMAC-SHA256 signature, so only authentic GitHub webhooks are processed.

2. **Restricted sudo commands**: The sudoers file only allows:
   - Specific service restarts (e.g., `dryrun-bot`, not wildcards)
   - Git commands limited to specific repository paths (using `-C` flag)
   - NPM commands restricted to specific directories (using `--prefix`)

3. **No wildcards**: Commands don't use `*` wildcards that could be exploited.

4. **Read-only file permissions**: The sudoers file is set to `0440` (read-only) to prevent modification.

**Risk vs convenience trade-off**: Allowing www-data to run these commands is a calculated risk. If your web server is compromised, an attacker could restart services or pull code. However:
- They can't escalate to full root access
- They can't modify arbitrary files
- They can't run arbitrary commands
- The webhook secret prevents unauthorized webhook calls

If you need higher security, consider:
- Running the webhook handler as a dedicated user (not www-data)
- Using SSH keys with deploy keys instead of HTTPS
- Implementing IP whitelisting for GitHub webhook IPs
