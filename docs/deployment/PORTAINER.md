# Portainer Stack Configuration for Twilio Responder Multi-Instance

This stack deploys three independent Twilio responder instances (Tucson, Pocatello, Rexburg) and a centralized admin dashboard.

## Stack File

Use `docker-compose.multi.yml` as the stack file in Portainer.

## Environment Variables

Add these environment variables in Portainer's stack editor:

### Tucson Branch
```
TUC_TWILIO_ACCOUNT_SID=
TUC_TWILIO_AUTH_TOKEN=
TUC_TWILIO_PHONE_NUMBER=
TUC_TWILIO_AUTOMATED_NUMBER=
TUC_TWILIO_TRANSFER_NUMBER=
TUC_TRANSFER_TARGET_PHONE_NUMBER=
TUC_PUBLIC_URL=https://tuc.axiom-emergencies.com
TUC_RECIPIENT_PHONES=
TUC_RECIPIENT_EMAILS=
TUC_DEBUG_WEBHOOK_URL=
```

### Pocatello Branch
```
POC_TWILIO_ACCOUNT_SID=
POC_TWILIO_AUTH_TOKEN=
POC_TWILIO_PHONE_NUMBER=
POC_TWILIO_AUTOMATED_NUMBER=
POC_TWILIO_TRANSFER_NUMBER=
POC_TRANSFER_TARGET_PHONE_NUMBER=
POC_PUBLIC_URL=https://poc.axiom-emergencies.com
POC_RECIPIENT_PHONES=
POC_RECIPIENT_EMAILS=
POC_DEBUG_WEBHOOK_URL=
```

### Rexburg Branch
```
REX_TWILIO_ACCOUNT_SID=
REX_TWILIO_AUTH_TOKEN=
REX_TWILIO_PHONE_NUMBER=
REX_TWILIO_AUTOMATED_NUMBER=
REX_TWILIO_TRANSFER_NUMBER=
REX_TRANSFER_TARGET_PHONE_NUMBER=
REX_PUBLIC_URL=https://rex.axiom-emergencies.com
REX_RECIPIENT_PHONES=
REX_RECIPIENT_EMAILS=
REX_DEBUG_WEBHOOK_URL=
```

### Admin Dashboard
```
ADMIN_FLASK_SECRET_KEY=
ADMIN_TWILIO_ACCOUNT_SID=
ADMIN_TWILIO_AUTH_TOKEN=
ADMIN_TWILIO_PHONE_NUMBER=
```

### Cloudflare
```
CLOUDFLARE_TOKEN=
```

## Deployment Steps

1. In Portainer, go to **Stacks** → **Add Stack**
2. Name: `twilio-responder-multi`
3. Build method: **Upload**
4. Upload: `docker-compose.multi.yml`
5. Click on **Environment variables** section
6. Add all variables listed above with your actual values
7. Click **Deploy the stack**

## Post-Deployment

1. Wait for all containers to start (check in Containers view)
2. Access admin dashboard at https://axiom-emergencies.com
3. Login with:
   - Username: `axiomadmin`
   - Password: `Dannyle44!`
4. Configure Twilio webhooks for each branch
5. **Optional**: Edit branch settings through the dashboard (see [../features/SETTINGS_MANAGEMENT.md](../features/SETTINGS_MANAGEMENT.md))
6. Create additional users if needed

## Managing Settings

You have two options for managing settings:

### Option 1: Through Dashboard (Recommended)
- Settings can be edited through the web interface
- Changes take effect automatically
- No container restart required
- See [../features/SETTINGS_MANAGEMENT.md](../features/SETTINGS_MANAGEMENT.md) for details

### Option 2: Through Portainer (Legacy)
- Edit environment variables in the stack
- Click "Update the stack" to apply changes
- Requires container restart
- Use this only if dashboard is unavailable

## Container Names

- `twilio_responder_tuc` - Tucson branch
- `twilio_responder_poc` - Pocatello branch  
- `twilio_responder_rex` - Rexburg branch
- `twilio_responder_admin` - Admin dashboard
- `twilio_responder_cloudflared` - Cloudflare tunnel

## Viewing Logs in Portainer

1. Go to **Containers**
2. Click on a container name
3. Click **Logs** tab
4. Enable **Auto-refresh logs**

## Managing the Stack

- **Update**: Modify environment variables and click **Update the stack**
- **Restart**: Click **Stop** then **Start** in Containers view
- **Remove**: Go to Stacks, select stack, click **Delete**
