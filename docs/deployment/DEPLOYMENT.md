# Multi-Instance Deployment Guide

This guide explains how to deploy the multi-instance Twilio Responder system with three separate branches (Tucson, Pocatello, and Rexburg) and a centralized admin dashboard.

## Architecture Overview

The system consists of:
- **3 Branch Instances**: Independent Twilio responder applications for TUC, POC, and REX
- **Admin Dashboard**: Centralized management interface at axiom-emergencies.com
- **Cloudflare Tunnel**: Secure ingress for all services

## URL Structure

- `axiom-emergencies.com` - Main admin dashboard
- `tuc.axiom-emergencies.com` - Tucson branch
- `poc.axiom-emergencies.com` - Pocatello branch
- `rex.axiom-emergencies.com` - Rexburg branch

## Prerequisites

1. **Docker & Docker Compose** installed on your server
2. **Portainer** (optional but recommended for management)
3. **Cloudflare account** with domain configured
4. **Twilio accounts** for each branch

## Setup Instructions

### 1. Configure Cloudflare Tunnel

Create a Cloudflare Tunnel with the following ingress rules:

```yaml
tunnel: <your-tunnel-id>
credentials-file: /etc/cloudflared/credentials.json

ingress:
  # Main admin dashboard
  - hostname: axiom-emergencies.com
    service: http://twilio_responder_admin:5000
  
  # Tucson branch
  - hostname: tuc.axiom-emergencies.com
    service: http://twilio_responder_tuc:5000
  
  # Pocatello branch
  - hostname: poc.axiom-emergencies.com
    service: http://twilio_responder_poc:5000
  
  # Rexburg branch
  - hostname: rex.axiom-emergencies.com
    service: http://twilio_responder_rex:5000
  
  # Catch-all rule
  - service: http_status:404
```

### 2. Environment Variables

Copy the `.env.example` file to `.env` and fill in your values:

```bash
cp .env.example .env
nano .env
```

Required variables for each branch:
- `<BRANCH>_TWILIO_ACCOUNT_SID` - Twilio Account SID
- `<BRANCH>_TWILIO_AUTH_TOKEN` - Twilio Auth Token
- `<BRANCH>_TWILIO_PHONE_NUMBER` - Main phone number
- `<BRANCH>_TWILIO_AUTOMATED_NUMBER` - Automated calling number
- `<BRANCH>_TWILIO_TRANSFER_NUMBER` - Transfer number
- `<BRANCH>_TRANSFER_TARGET_PHONE_NUMBER` - Target for transfers
- `<BRANCH>_PUBLIC_URL` - Public URL for the branch
- `<BRANCH>_RECIPIENT_PHONES` - Comma-separated SMS recipients
- `<BRANCH>_RECIPIENT_EMAILS` - Email recipients (currently simulated)

Admin dashboard variables:
- `ADMIN_FLASK_SECRET_KEY` - Random secret key for sessions
- `ADMIN_TWILIO_ACCOUNT_SID` - Twilio account for notifications
- `ADMIN_TWILIO_AUTH_TOKEN` - Twilio auth token
- `ADMIN_TWILIO_PHONE_NUMBER` - Phone number for sending notifications

### 3. Deploy with Docker Compose

```bash
# Build and start all services
docker-compose -f docker-compose.multi.yml up -d

# View logs
docker-compose -f docker-compose.multi.yml logs -f

# Stop all services
docker-compose -f docker-compose.multi.yml down
```

### 4. Deploy with Portainer

1. Log in to Portainer
2. Go to **Stacks** > **Add Stack**
3. Name: `twilio-responder-multi`
4. Upload `docker-compose.multi.yml`
5. Add environment variables from `.env` file
6. Click **Deploy the stack**

### 5. Configure Twilio Webhooks

For each branch, configure the Twilio phone number webhooks:

**Incoming Call Webhook:**
- URL: `https://<branch>.axiom-emergencies.com/incoming_twilio_call`
- Method: POST

**SMS Webhook:**
- URL: `https://<branch>.axiom-emergencies.com/sms_reply`
- Method: POST

## Admin Dashboard Features

### Authentication
- Default username: `axiomadmin`
- Default password: `Dannyle44!`
- Change password after first login via user management

### User Management
1. **Create Users**: Admins can create sub-accounts
2. **Set Permissions**: Control access per branch
   - View: See branch dashboard
   - Trigger: Initiate emergencies
   - Disable: Enable/disable branch

### Branch Management
- **View Status**: Real-time status of all branches
- **Disable Branch**: Temporarily disable a branch (requires confirmation)
- **Enable Branch**: Re-enable a disabled branch
- **SMS Notifications**: Automatic SMS to +18017104034 when branches are disabled/enabled

### Permissions System

Admin users have full access. Regular users can be assigned:
- Branch-specific view permissions
- Branch-specific trigger permissions
- Branch-specific disable/enable permissions

## Branch Status Monitoring

Each branch reports:
- **Ready**: System online, waiting for calls
- **In Use**: Currently processing an emergency
- **Error**: Recent error detected
- **Offline**: Cannot connect to branch

Auto-refresh every 30 seconds on the dashboard.

## Security Considerations

1. **Change Default Credentials**: Immediately change the default admin password
2. **Secure Environment Variables**: Store `.env` file securely, never commit to git
3. **Use Strong Secret Keys**: Generate random values for `ADMIN_FLASK_SECRET_KEY`
4. **HTTPS Only**: All traffic goes through Cloudflare Tunnel with SSL
5. **Database Backups**: Regularly backup `/app/data/admin.db`

## Backup and Restore

### Backup Database
```bash
docker cp twilio_responder_admin:/app/data/admin.db ./backup/admin.db.$(date +%Y%m%d)
```

### Restore Database
```bash
docker cp ./backup/admin.db.YYYYMMDD twilio_responder_admin:/app/data/admin.db
docker restart twilio_responder_admin
```

### Backup Branch Logs
```bash
# Tucson logs
docker cp twilio_responder_tuc:/app/logs ./backup/tuc_logs_$(date +%Y%m%d)

# Pocatello logs
docker cp twilio_responder_poc:/app/logs ./backup/poc_logs_$(date +%Y%m%d)

# Rexburg logs
docker cp twilio_responder_rex:/app/logs ./backup/rex_logs_$(date +%Y%m%d)
```

## Troubleshooting

### Branch Shows Offline
1. Check container status: `docker ps`
2. View logs: `docker logs twilio_responder_<branch>`
3. Verify environment variables in container
4. Check network connectivity between containers

### Cannot Login to Admin Dashboard
1. Verify container is running: `docker ps | grep admin`
2. Check logs: `docker logs twilio_responder_admin`
3. Reset admin password by recreating the database

### SMS Notifications Not Sending
1. Verify `ADMIN_TWILIO_*` variables are set correctly
2. Check Twilio account has SMS capabilities
3. Verify phone number format includes country code: `+1...`

### Cloudflare Tunnel Issues
1. Verify tunnel token is correct
2. Check ingress rules match container names
3. Ensure containers are on the same Docker network
4. View cloudflared logs: `docker logs twilio_responder_cloudflared`

## Maintenance

### Update Application
```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.multi.yml up -d --build
```

### Scale Resources
Modify `docker-compose.multi.yml` to add resource limits:

```yaml
services:
  twilio-app-tuc:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
```

### Monitor Resource Usage
```bash
docker stats
```

## Support

For issues or questions:
1. Check logs first: `docker-compose -f docker-compose.multi.yml logs`
2. Review environment variables
3. Verify Twilio webhook configuration
4. Check Cloudflare tunnel status

## Migration from Single Instance

If migrating from the original single-instance setup:

1. Backup your current `.env` file
2. Create new `.env` with branch-specific variables
3. Export data from current instance if needed
4. Deploy new multi-instance stack
5. Update Twilio webhooks to new URLs
6. Test each branch individually
7. Shut down old instance after verification

## Version History

- **v1.0** - Initial multi-instance release with admin dashboard
  - 3 independent branch instances
  - Centralized admin dashboard
  - User management with permissions
  - Branch enable/disable functionality
  - SMS notifications for admin actions
