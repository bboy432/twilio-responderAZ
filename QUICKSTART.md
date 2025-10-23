# Quick Start Guide

Get the multi-instance Twilio responder system up and running quickly.

## Prerequisites

- Docker and Docker Compose installed
- Cloudflare account with domain configured
- Twilio accounts for each branch
- Access to the server/Portainer

## Step-by-Step Setup

### 1. Clone Repository (if not already done)

```bash
git clone https://github.com/bboy432/twilio-responderAZ.git
cd twilio-responderAZ
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
nano .env
```

Fill in all the values for:
- **TUC_** prefixed variables (Tucson branch)
- **POC_** prefixed variables (Pocatello branch)
- **REX_** prefixed variables (Rexburg branch)
- **ADMIN_** prefixed variables (Admin dashboard)
- **CLOUDFLARE_TOKEN** (Cloudflare tunnel token)

### 3. Set Up Cloudflare Tunnel

#### Option A: Via Cloudflare Dashboard
1. Go to Cloudflare Zero Trust → Tunnels
2. Create tunnel named `axiom-emergencies`
3. Copy the token to `.env` as `CLOUDFLARE_TOKEN`
4. Add public hostnames:
   - `axiom-emergencies.com` → `http://twilio_responder_admin:5000`
   - `tuc.axiom-emergencies.com` → `http://twilio_responder_tuc:5000`
   - `poc.axiom-emergencies.com` → `http://twilio_responder_poc:5000`
   - `rex.axiom-emergencies.com` → `http://twilio_responder_rex:5000`

#### Option B: Via CLI
See [docs/deployment/CLOUDFLARE.md](docs/deployment/CLOUDFLARE.md) for detailed CLI instructions.

### 4. Deploy with Docker Compose

```bash
docker-compose -f docker-compose.multi.yml up -d
```

Or in Portainer:
1. Go to Stacks → Add Stack
2. Upload `docker-compose.multi.yml`
3. Add environment variables from `.env`
4. Deploy

### 5. Configure Twilio Webhooks

For each branch, configure webhooks in Twilio console:

#### Tucson (TUC)
- Incoming Call: `https://tuc.axiom-emergencies.com/incoming_twilio_call`
- SMS: `https://tuc.axiom-emergencies.com/sms_reply`

#### Pocatello (POC)
- Incoming Call: `https://poc.axiom-emergencies.com/incoming_twilio_call`
- SMS: `https://poc.axiom-emergencies.com/sms_reply`

#### Rexburg (REX)
- Incoming Call: `https://rex.axiom-emergencies.com/incoming_twilio_call`
- SMS: `https://rex.axiom-emergencies.com/sms_reply`

### 6. Access Admin Dashboard

1. Go to https://axiom-emergencies.com
2. Login with:
   - Username: `axiomadmin`
   - Password: `Dannyle44!`
3. **IMMEDIATELY CHANGE PASSWORD** via user management

### 7. Test Each Branch

Visit each branch to verify it's working:
- https://tuc.axiom-emergencies.com/status
- https://poc.axiom-emergencies.com/status
- https://rex.axiom-emergencies.com/status

You should see "Ready" status on each.

## Common Issues

### Containers Not Starting
```bash
# Check logs
docker logs twilio_responder_tuc
docker logs twilio_responder_poc
docker logs twilio_responder_rex
docker logs twilio_responder_admin
```

### Cannot Access URLs
- Verify Cloudflare tunnel is running: `docker logs twilio_responder_cloudflared`
- Check DNS records in Cloudflare dashboard
- Wait 2-5 minutes for DNS propagation

### Branch Shows Offline in Dashboard
- Verify container is running: `docker ps`
- Check environment variables are set correctly
- Restart container: `docker restart twilio_responder_<branch>`

## Next Steps

1. **Create Additional Users**: Go to Users page in admin dashboard
2. **Set Permissions**: Configure what each user can access
3. **Test Emergency Flow**: Trigger a test emergency from each branch
4. **Configure Monitoring**: Set up alerts for branch status changes
5. **Backup Database**: Schedule regular backups of admin database

## Getting Help

- Check [docs/deployment/DEPLOYMENT.md](docs/deployment/DEPLOYMENT.md) for detailed configuration
- Review [admin-dashboard/README.md](admin-dashboard/README.md) for dashboard features
- Check container logs for errors
- Verify all environment variables are set correctly

## Security Checklist

- [ ] Changed default admin password
- [ ] Generated random FLASK_SECRET_KEY
- [ ] Secured .env file (not committed to git)
- [ ] Configured HTTPS only (via Cloudflare)
- [ ] Limited user permissions appropriately
- [ ] Set up database backup schedule
- [ ] Verified SMS notifications working

## Quick Commands

```bash
# View all container status
docker ps

# View logs for all services
docker-compose -f docker-compose.multi.yml logs -f

# Restart a specific branch
docker restart twilio_responder_tuc

# Stop all services
docker-compose -f docker-compose.multi.yml down

# Start all services
docker-compose -f docker-compose.multi.yml up -d

# Rebuild and restart (after code changes)
docker-compose -f docker-compose.multi.yml up -d --build

# Backup admin database
docker cp twilio_responder_admin:/app/data/admin.db ./backup-$(date +%Y%m%d).db
```

## Environment Variables Quick Reference

Minimum required variables (per branch):
- `<BRANCH>_TWILIO_ACCOUNT_SID`
- `<BRANCH>_TWILIO_AUTH_TOKEN`
- `<BRANCH>_TWILIO_PHONE_NUMBER`
- `<BRANCH>_TWILIO_AUTOMATED_NUMBER`
- `<BRANCH>_TWILIO_TRANSFER_NUMBER`
- `<BRANCH>_TRANSFER_TARGET_PHONE_NUMBER`
- `<BRANCH>_PUBLIC_URL`
- `<BRANCH>_RECIPIENT_PHONES`

For admin:
- `ADMIN_FLASK_SECRET_KEY` (generate random)
- `ADMIN_TWILIO_ACCOUNT_SID`
- `ADMIN_TWILIO_AUTH_TOKEN`
- `ADMIN_TWILIO_PHONE_NUMBER`
- `CLOUDFLARE_TOKEN`

## Support

If you encounter issues:
1. Check logs: `docker-compose -f docker-compose.multi.yml logs`
2. Verify environment variables
3. Check Cloudflare tunnel status
4. Review Twilio webhook configuration
5. Test each component individually
