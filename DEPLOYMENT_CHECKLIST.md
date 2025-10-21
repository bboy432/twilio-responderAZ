# Deployment Checklist

Use this checklist when deploying the multi-instance Twilio responder system to ensure all components are properly configured.

## Pre-Deployment

### Requirements Verification
- [ ] Docker installed (version 20.10+)
- [ ] Docker Compose installed (or Docker with compose plugin)
- [ ] Portainer installed (optional but recommended)
- [ ] Cloudflare account with domain configured
- [ ] Three Twilio accounts (or subaccounts) for TUC, POC, REX
- [ ] Server/VPS with adequate resources:
  - [ ] Minimum 2GB RAM
  - [ ] 2 CPU cores
  - [ ] 20GB disk space
  - [ ] Stable internet connection

### Twilio Configuration (Per Branch)
For each branch (TUC, POC, REX):
- [ ] Twilio account/subaccount created
- [ ] Phone numbers purchased:
  - [ ] Main phone number
  - [ ] Automated calling number
  - [ ] Transfer number
- [ ] Phone numbers verified for voice capability
- [ ] Phone numbers verified for SMS capability
- [ ] Account has sufficient balance

### Cloudflare Setup
- [ ] Domain added to Cloudflare
- [ ] Domain DNS managed by Cloudflare
- [ ] SSL/TLS mode set to "Flexible" or "Full"
- [ ] Tunnel created in Zero Trust dashboard
- [ ] Tunnel token copied and saved securely

## Configuration

### Environment Variables Setup
- [ ] Copied `.env.example` to `.env`
- [ ] Configured TUC branch variables:
  - [ ] `TUC_TWILIO_ACCOUNT_SID`
  - [ ] `TUC_TWILIO_AUTH_TOKEN`
  - [ ] `TUC_TWILIO_PHONE_NUMBER`
  - [ ] `TUC_TWILIO_AUTOMATED_NUMBER`
  - [ ] `TUC_TWILIO_TRANSFER_NUMBER`
  - [ ] `TUC_TRANSFER_TARGET_PHONE_NUMBER`
  - [ ] `TUC_PUBLIC_URL`
  - [ ] `TUC_RECIPIENT_PHONES`
  - [ ] `TUC_RECIPIENT_EMAILS`
- [ ] Configured POC branch variables (same as above with POC_ prefix)
- [ ] Configured REX branch variables (same as above with REX_ prefix)
- [ ] Configured admin dashboard variables:
  - [ ] `ADMIN_FLASK_SECRET_KEY` (generated random key)
  - [ ] `ADMIN_TWILIO_ACCOUNT_SID`
  - [ ] `ADMIN_TWILIO_AUTH_TOKEN`
  - [ ] `ADMIN_TWILIO_PHONE_NUMBER`
  - [ ] `TUC_PUBLIC_URL`
  - [ ] `POC_PUBLIC_URL`
  - [ ] `REX_PUBLIC_URL`
- [ ] Configured Cloudflare:
  - [ ] `CLOUDFLARE_TOKEN`

### Secret Generation
- [ ] Generated strong `ADMIN_FLASK_SECRET_KEY`:
  ```bash
  python3 -c "import secrets; print(secrets.token_hex(32))"
  ```
- [ ] Saved `.env` file in secure location
- [ ] Added `.env` to `.gitignore` (verify it's not committed)

### Cloudflare Tunnel Configuration
- [ ] Created ingress rules for all subdomains:
  - [ ] `axiom-emergencies.com` → `http://twilio_responder_admin:5000`
  - [ ] `tuc.axiom-emergencies.com` → `http://twilio_responder_tuc:5000`
  - [ ] `poc.axiom-emergencies.com` → `http://twilio_responder_poc:5000`
  - [ ] `rex.axiom-emergencies.com` → `http://twilio_responder_rex:5000`
- [ ] Added DNS CNAME records:
  - [ ] `@` → `<tunnel-id>.cfargotunnel.com` (Proxied)
  - [ ] `tuc` → `<tunnel-id>.cfargotunnel.com` (Proxied)
  - [ ] `poc` → `<tunnel-id>.cfargotunnel.com` (Proxied)
  - [ ] `rex` → `<tunnel-id>.cfargotunnel.com` (Proxied)

## Deployment

### Docker Compose Deployment
- [ ] Navigated to project directory
- [ ] Verified `.env` file is present
- [ ] Built images:
  ```bash
  docker-compose -f docker-compose.multi.yml build
  ```
- [ ] Started containers:
  ```bash
  docker-compose -f docker-compose.multi.yml up -d
  ```
- [ ] Verified all containers are running:
  ```bash
  docker ps
  ```
  Should see 5 containers:
  - [ ] `twilio_responder_admin`
  - [ ] `twilio_responder_tuc`
  - [ ] `twilio_responder_poc`
  - [ ] `twilio_responder_rex`
  - [ ] `twilio_responder_cloudflared`

### OR Portainer Deployment
- [ ] Logged into Portainer
- [ ] Created new stack named `twilio-responder-multi`
- [ ] Uploaded `docker-compose.multi.yml`
- [ ] Added all environment variables from `.env`
- [ ] Deployed stack
- [ ] Verified all containers are running in Portainer UI

### Verify Logs
- [ ] Checked admin dashboard logs:
  ```bash
  docker logs twilio_responder_admin --tail 50
  ```
- [ ] Checked TUC branch logs:
  ```bash
  docker logs twilio_responder_tuc --tail 50
  ```
- [ ] Checked POC branch logs:
  ```bash
  docker logs twilio_responder_poc --tail 50
  ```
- [ ] Checked REX branch logs:
  ```bash
  docker logs twilio_responder_rex --tail 50
  ```
- [ ] Checked Cloudflare tunnel logs:
  ```bash
  docker logs twilio_responder_cloudflared --tail 50
  ```
- [ ] No critical errors found in any logs

## Testing

### DNS and Connectivity Tests
- [ ] Tested DNS resolution:
  ```bash
  nslookup axiom-emergencies.com
  nslookup tuc.axiom-emergencies.com
  nslookup poc.axiom-emergencies.com
  nslookup rex.axiom-emergencies.com
  ```
- [ ] Verified HTTPS access:
  - [ ] `https://axiom-emergencies.com` loads (redirect to login)
  - [ ] `https://tuc.axiom-emergencies.com/status` loads
  - [ ] `https://poc.axiom-emergencies.com/status` loads
  - [ ] `https://rex.axiom-emergencies.com/status` loads
- [ ] Verified SSL certificates are valid (no browser warnings)

### Admin Dashboard Tests
- [ ] Accessed `https://axiom-emergencies.com`
- [ ] Login page loads correctly
- [ ] Logged in with default credentials:
  - Username: `axiomadmin`
  - Password: `Dannyle44!`
- [ ] Dashboard displays all three branches
- [ ] All branches show status (Ready/Online)
- [ ] Clicked on each branch card to view individual dashboards:
  - [ ] TUC branch dashboard loads
  - [ ] POC branch dashboard loads
  - [ ] REX branch dashboard loads
- [ ] Tested auto-refresh (wait 30 seconds, status updates)

### Branch Status Tests
For each branch (TUC, POC, REX):
- [ ] Visited `https://<branch>.axiom-emergencies.com/status`
- [ ] Page shows "Ready" status
- [ ] Recent call history section displays (may be empty)
- [ ] API endpoint works:
  ```bash
  curl https://<branch>.axiom-emergencies.com/api/status
  ```
  Returns JSON with status: "Ready"

### Twilio Webhook Configuration
For each branch (TUC, POC, REX):
- [ ] Logged into Twilio console
- [ ] Navigated to phone number settings
- [ ] Configured Voice webhook:
  - URL: `https://<branch>.axiom-emergencies.com/incoming_twilio_call`
  - Method: HTTP POST
  - [ ] Saved and verified
- [ ] Configured SMS webhook:
  - URL: `https://<branch>.axiom-emergencies.com/sms_reply`
  - Method: HTTP POST
  - [ ] Saved and verified
- [ ] Tested with Twilio's "Test" button if available

### Emergency Flow Test (Optional but Recommended)
For one branch (e.g., TUC):
- [ ] Prepared test data (test phone numbers)
- [ ] Triggered test emergency via API or dashboard
- [ ] Verified SMS received by test recipient
- [ ] Verified call received by test technician
- [ ] Verified logs show emergency flow
- [ ] Emergency concluded successfully

## Post-Deployment

### Security Configuration
- [ ] Changed default admin password:
  - [ ] Logged into admin dashboard
  - [ ] Created new admin user with strong password
  - [ ] Tested login with new user
  - [ ] Deleted or disabled default admin (or changed password via env var)
- [ ] Created test user account
- [ ] Configured test user permissions
- [ ] Tested login with test user
- [ ] Verified permission restrictions work

### User Management Setup
- [ ] Accessed user management page
- [ ] Created users for team members
- [ ] Assigned appropriate permissions per branch:
  - [ ] View permissions
  - [ ] Trigger permissions
  - [ ] Disable permissions
- [ ] Tested each user account

### Backup Configuration
- [ ] Created backup directory:
  ```bash
  mkdir -p /backup/twilio-responder
  ```
- [ ] Backed up admin database:
  ```bash
  docker cp twilio_responder_admin:/app/data/admin.db /backup/twilio-responder/admin.db
  ```
- [ ] Backed up environment file:
  ```bash
  cp .env /backup/twilio-responder/.env.backup
  ```
- [ ] Set up automated backup schedule (cron job):
  ```bash
  # Example: Daily at 2 AM
  0 2 * * * docker cp twilio_responder_admin:/app/data/admin.db /backup/twilio-responder/admin-$(date +\%Y\%m\%d).db
  ```

### Monitoring Setup
- [ ] Set up uptime monitoring (Cloudflare, UptimeRobot, etc.)
- [ ] Configured alerts for:
  - [ ] Container restarts
  - [ ] High CPU/memory usage
  - [ ] Failed requests
  - [ ] Branch offline status
- [ ] Tested alert notifications

### Documentation
- [ ] Documented server access credentials (in password manager)
- [ ] Documented Cloudflare tunnel details
- [ ] Documented Twilio account information
- [ ] Shared access information with team (securely)
- [ ] Added notes about any custom configurations

## Verification

### Final Checks
- [ ] All containers running and healthy
- [ ] All URLs accessible via HTTPS
- [ ] Admin dashboard functioning correctly
- [ ] All three branches showing "Ready" status
- [ ] User authentication working
- [ ] Permission system working
- [ ] SMS notifications working
- [ ] Branch enable/disable functionality working
- [ ] Twilio webhooks configured correctly
- [ ] Logs showing no errors
- [ ] Backups created and tested
- [ ] Team members can access and use system

### Performance Checks
- [ ] Dashboard loads in < 3 seconds
- [ ] Branch status updates in < 5 seconds
- [ ] No memory leaks (monitor over 24 hours)
- [ ] No high CPU usage (< 20% average)
- [ ] Disk usage reasonable (< 5GB total)

## Rollback Plan

If issues occur:
- [ ] Documented current state before making changes
- [ ] Created backup of database and configuration
- [ ] Tested rollback procedure:
  ```bash
  # Stop containers
  docker-compose -f docker-compose.multi.yml down
  
  # Restore backup if needed
  docker cp /backup/twilio-responder/admin.db twilio_responder_admin:/app/data/admin.db
  
  # Restart containers
  docker-compose -f docker-compose.multi.yml up -d
  ```

## Support Contacts

- [ ] Documented support contacts:
  - Cloudflare support: _______________
  - Twilio support: _______________
  - Server hosting support: _______________
  - Internal team contacts: _______________

## Sign-Off

- [ ] Deployment completed by: _______________ Date: _______________
- [ ] Verified by: _______________ Date: _______________
- [ ] Customer/stakeholder approval: _______________ Date: _______________

---

## Post-Deployment Monitoring (First 24 Hours)

- [ ] Hour 1: Check all services running
- [ ] Hour 6: Review logs for any errors
- [ ] Hour 12: Verify memory/CPU usage stable
- [ ] Hour 24: Full system test including emergency flow
- [ ] Hour 24: Create incident report if any issues

## Post-Deployment Monitoring (First Week)

- [ ] Day 1: Full functionality test
- [ ] Day 3: Review logs and performance
- [ ] Day 7: Create performance report
- [ ] Day 7: Schedule training session for users

## Notes Section

Use this space for deployment-specific notes, issues encountered, and resolutions:

```
Date: _______________
Notes:
_______________________________________________
_______________________________________________
_______________________________________________
_______________________________________________
```
