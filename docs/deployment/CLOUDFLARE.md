# Cloudflare Tunnel Configuration

## Overview
This configuration routes traffic from your domain to the Docker containers running the Twilio responder instances and admin dashboard.

## Prerequisites
1. Domain registered and managed in Cloudflare
2. Cloudflare account with tunnel capability
3. Cloudflare tunnel created

## Creating a Tunnel

### Via Cloudflare Dashboard
1. Log in to Cloudflare Dashboard
2. Go to **Zero Trust** → **Access** → **Tunnels**
3. Click **Create a tunnel**
4. Choose **Cloudflared** connector
5. Name: `axiom-emergencies`
6. Save the tunnel token (you'll need this for `CLOUDFLARE_TOKEN`)

### Via CLI
```bash
cloudflared tunnel create axiom-emergencies
```

## Configuration File

Create a file named `config.yml` for your tunnel:

```yaml
tunnel: <your-tunnel-id>
credentials-file: /etc/cloudflared/<tunnel-id>.json

ingress:
  # Main admin dashboard - root domain
  - hostname: axiom-emergencies.com
    service: http://twilio_responder_admin:5000
    originRequest:
      noTLSVerify: true
  
  # Tucson branch subdomain
  - hostname: tuc.axiom-emergencies.com
    service: http://twilio_responder_tuc:5000
    originRequest:
      noTLSVerify: true
  
  # Pocatello branch subdomain
  - hostname: poc.axiom-emergencies.com
    service: http://twilio_responder_poc:5000
    originRequest:
      noTLSVerify: true
  
  # Rexburg branch subdomain
  - hostname: rex.axiom-emergencies.com
    service: http://twilio_responder_rex:5000
    originRequest:
      noTLSVerify: true
  
  # Catch-all rule (required)
  - service: http_status:404
```

## DNS Configuration

In Cloudflare DNS, add these CNAME records:

| Type  | Name | Target                          | Proxy Status |
|-------|------|---------------------------------|--------------|
| CNAME | @    | <tunnel-id>.cfargotunnel.com    | Proxied      |
| CNAME | tuc  | <tunnel-id>.cfargotunnel.com    | Proxied      |
| CNAME | poc  | <tunnel-id>.cfargotunnel.com    | Proxied      |
| CNAME | rex  | <tunnel-id>.cfargotunnel.com    | Proxied      |

The `<tunnel-id>` is your Cloudflare tunnel ID.

## Using with Docker Compose

The `docker-compose.multi.yml` file includes a cloudflared service that automatically uses your tunnel token.

Just set the `CLOUDFLARE_TOKEN` environment variable:

```bash
CLOUDFLARE_TOKEN=your-tunnel-token-here
```

## Alternative: Ingress via Dashboard

Instead of using a config file, you can configure ingress rules via the Cloudflare Dashboard:

1. Go to your tunnel in the dashboard
2. Click **Configure**
3. Go to **Public Hostname** tab
4. Add each hostname:

### Main Dashboard
- Subdomain: (blank)
- Domain: axiom-emergencies.com
- Service Type: HTTP
- URL: twilio_responder_admin:5000

### Tucson Branch
- Subdomain: tuc
- Domain: axiom-emergencies.com
- Service Type: HTTP
- URL: twilio_responder_tuc:5000

### Pocatello Branch
- Subdomain: poc
- Domain: axiom-emergencies.com
- Service Type: HTTP
- URL: twilio_responder_poc:5000

### Rexburg Branch
- Subdomain: rex
- Domain: axiom-emergencies.com
- Service Type: HTTP
- URL: twilio_responder_rex:5000

## Docker Network

**Important**: The cloudflared container must be on the same Docker network as the application containers. The `docker-compose.multi.yml` file handles this automatically with the `twilio-net` network.

## Testing

After deployment, test each endpoint:

```bash
# Test admin dashboard
curl -I https://axiom-emergencies.com

# Test Tucson branch
curl -I https://tuc.axiom-emergencies.com/api/status

# Test Pocatello branch
curl -I https://poc.axiom-emergencies.com/api/status

# Test Rexburg branch
curl -I https://rex.axiom-emergencies.com/api/status
```

All should return HTTP 200 or appropriate response codes.

## Troubleshooting

### Tunnel Not Connecting
1. Check container logs: `docker logs twilio_responder_cloudflared`
2. Verify `CLOUDFLARE_TOKEN` is correct
3. Ensure tunnel exists in Cloudflare dashboard

### 502 Bad Gateway
1. Verify container names match ingress configuration
2. Check if application containers are running: `docker ps`
3. Verify containers are on same network: `docker network inspect twilio-net`

### DNS Not Resolving
1. Verify CNAME records in Cloudflare DNS
2. Wait for DNS propagation (up to 5 minutes)
3. Check proxy status is enabled (orange cloud)

### SSL/TLS Errors
1. Ensure Cloudflare SSL/TLS mode is set to "Flexible" or "Full"
2. Go to SSL/TLS settings in Cloudflare dashboard
3. Choose appropriate encryption mode

## Security Notes

1. **Always use HTTPS**: Cloudflare tunnel provides automatic SSL/TLS
2. **Restrict Access**: Consider adding Cloudflare Access policies
3. **Monitor Logs**: Regularly check tunnel logs for unusual activity
4. **Rotate Tokens**: Periodically regenerate tunnel tokens

## Multiple Tunnels Option

Alternatively, you can create separate tunnels for each branch:

```yaml
# Separate tunnels approach
services:
  cloudflared-tuc:
    image: cloudflare/cloudflared:latest
    command: tunnel --no-autoupdate run --token ${TUC_CLOUDFLARE_TOKEN}
    
  cloudflared-poc:
    image: cloudflare/cloudflared:latest
    command: tunnel --no-autoupdate run --token ${POC_CLOUDFLARE_TOKEN}
    
  cloudflared-rex:
    image: cloudflare/cloudflared:latest
    command: tunnel --no-autoupdate run --token ${REX_CLOUDFLARE_TOKEN}
    
  cloudflared-admin:
    image: cloudflare/cloudflared:latest
    command: tunnel --no-autoupdate run --token ${ADMIN_CLOUDFLARE_TOKEN}
```

This provides isolation but requires managing four separate tunnels.
