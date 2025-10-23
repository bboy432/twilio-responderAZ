# System Architecture

## Overview Diagram

```
                                  INTERNET
                                     |
                                     |
                          ┌──────────▼──────────┐
                          │  Cloudflare Tunnel  │
                          │   (SSL/TLS Proxy)   │
                          └──────────┬──────────┘
                                     |
                 ┌───────────────────┼──────────────────┐
                 |                   |                  |
        ┌────────▼────────┐  ┌──────▼──────┐  ┌───────▼────────┐
        │  axiom-emer...  │  │  tuc.axiom  │  │  poc.axiom...  │
        │  .com           │  │  -emer...   │  │  rex.axiom...  │
        └────────┬────────┘  └──────┬──────┘  └───────┬────────┘
                 |                   |                  |
                 |     Docker Network (twilio-net)      |
                 |                   |                  |
        ┌────────▼────────┐  ┌──────▼──────┐  ┌───────▼────────┐
        │ Admin Dashboard │  │ Branch: TUC │  │ Branch: POC/REX│
        │   Container     │  │  Container  │  │   Container    │
        │                 │  │             │  │                │
        │  - Auth System  │  │ - Twilio    │  │  - Twilio      │
        │  - User Mgmt    │  │ - Emergency │  │  - Emergency   │
        │  - Monitoring   │  │ - Logging   │  │  - Logging     │
        │  - Branch Ctrl  │  │ - Status    │  │  - Status      │
        └────────┬────────┘  └──────┬──────┘  └───────┬────────┘
                 |                   |                  |
        ┌────────▼────────┐  ┌──────▼──────┐  ┌───────▼────────┐
        │  SQLite DB      │  │  Log Files  │  │   Log Files    │
        │  - Users        │  │  - Timeline │  │   - Timeline   │
        │  - Permissions  │  │  - Events   │  │   - Events     │
        │  - Branch Status│  │  - Errors   │  │   - Errors     │
        └─────────────────┘  └─────────────┘  └────────────────┘
```

## Component Details

### Cloudflare Tunnel
- **Purpose**: Secure HTTPS ingress without exposing ports
- **Configuration**: Maps subdomains to internal containers
- **Security**: Automatic SSL/TLS, DDoS protection

### Admin Dashboard (Port 5000)
- **Tech Stack**: Flask, SQLite, Jinja2 templates
- **Authentication**: Session-based with SHA-256 password hashing
- **Features**:
  - Multi-branch monitoring
  - User/permission management
  - Branch enable/disable controls
  - SMS notifications via Twilio

### Branch Instances (TUC/POC/REX)
- **Tech Stack**: Flask, Twilio SDK, Python
- **Purpose**: Handle emergency calls for specific locations
- **Features**:
  - Receive incoming calls
  - Notify technicians via SMS/Call
  - Queue management
  - Conference calling
  - Status reporting

### Data Persistence
- **Admin DB**: `/app/data/admin.db` (SQLite)
- **Branch Logs**: `/app/logs/app.log` (per branch)
- **Volumes**: Docker volumes for persistence across restarts

## Request Flow

### Emergency Call Flow

```
1. Customer calls Twilio number
           |
           ▼
2. Twilio webhook → branch.axiom-emergencies.com/incoming_twilio_call
           |
           ▼
3. Branch app processes call
           |
           ├──▶ Send SMS to technician
           |
           ├──▶ Make automated call to technician
           |
           └──▶ Queue customer (hold music)
           |
           ▼
4. When technician call completes
           |
           ├──▶ Connect technician to customer
           |
           └──▶ Conference call established
           |
           ▼
5. Call ends → cleanup
           |
           ├──▶ Send summary email
           |
           └──▶ Clear emergency state
```

### Admin Dashboard Flow

```
1. User accesses axiom-emergencies.com
           |
           ▼
2. Check session authentication
           |
           ├──▶ Not authenticated → Redirect to /login
           |
           └──▶ Authenticated → Continue
                    |
                    ▼
3. Load dashboard
           |
           ├──▶ Query branch statuses (parallel)
           |     |
           |     ├──▶ TUC: http://twilio-app-tuc:5000/api/status
           |     ├──▶ POC: http://twilio-app-poc:5000/api/status
           |     └──▶ REX: http://twilio-app-rex:5000/api/status
           |
           ├──▶ Load user permissions
           |
           └──▶ Render dashboard.html
                    |
                    ▼
4. Auto-refresh every 30 seconds
           |
           └──▶ JavaScript polls /api/branch/<branch>/status
```

### Branch Disable Flow

```
1. Admin clicks "Disable Branch" button
           |
           ▼
2. JavaScript confirmation dialog 1
           |
           ├──▶ Cancel → Abort
           |
           └──▶ Confirm → Continue
                    |
                    ▼
3. JavaScript confirmation dialog 2 (final)
           |
           ├──▶ Cancel → Abort
           |
           └──▶ Confirm → Continue
                    |
                    ▼
4. POST /api/branch/<branch>/disable
           |
           ├──▶ Check user permissions
           |     |
           |     └──▶ Denied → Return 403
           |
           └──▶ Allowed → Continue
                    |
                    ▼
5. Update database: is_enabled=0
           |
           ▼
6. Send SMS notification to +18017104034
           |
           ▼
7. Return success JSON
           |
           ▼
8. JavaScript reloads page
```

## Network Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      Internet                            │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ HTTPS (443)
                     │
┌────────────────────▼────────────────────────────────────┐
│              Cloudflare Edge Network                     │
│  - DDoS Protection                                       │
│  - SSL/TLS Termination                                   │
│  - DNS Resolution                                        │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Cloudflare Tunnel (encrypted)
                     │
┌────────────────────▼────────────────────────────────────┐
│              Host Server / Portainer                     │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │        Docker Network: twilio-net                │   │
│  │        Subnet: 172.18.0.0/16 (example)           │   │
│  │                                                  │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌──────────┐│   │
│  │  │ cloudflared │  │    admin    │  │   tuc    ││   │
│  │  │  (tunnel)   │◄─┤  dashboard  │  │  branch  ││   │
│  │  └─────────────┘  │             │  │          ││   │
│  │                   │  Port 5000  │  │Port 5000 ││   │
│  │                   └─────────────┘  └──────────┘│   │
│  │                                                  │   │
│  │  ┌─────────────┐  ┌─────────────┐              │   │
│  │  │     poc     │  │     rex     │              │   │
│  │  │   branch    │  │   branch    │              │   │
│  │  │             │  │             │              │   │
│  │  │  Port 5000  │  │  Port 5000  │              │   │
│  │  └─────────────┘  └─────────────┘              │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │         Docker Volumes (Persistent)              │   │
│  │  - admin_data   (SQLite database)                │   │
│  │  - tuc_logs     (Branch logs)                    │   │
│  │  - poc_logs     (Branch logs)                    │   │
│  │  - rex_logs     (Branch logs)                    │   │
│  └──────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────┘
```

## Data Flow

### Emergency Data Flow
```
Customer Call → Twilio → Branch Instance → Twilio (notify tech) → Branch Logs
                                        ↓
                                   Admin Dashboard (status query)
```

### Admin Action Flow
```
Admin Browser → Admin Dashboard → SQLite DB
                    ↓
                Branch API (status check)
                    ↓
                Twilio API (SMS notification)
```

## Security Layers

```
┌─────────────────────────────────────────────────────┐
│ Layer 1: Cloudflare (Edge Security)                 │
│  - DDoS Protection                                   │
│  - WAF Rules                                         │
│  - Bot Protection                                    │
└────────────────────┬────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────┐
│ Layer 2: Cloudflare Tunnel (Transport Security)     │
│  - End-to-end encryption                            │
│  - No exposed ports                                  │
│  - Mutual TLS                                        │
└────────────────────┬────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────┐
│ Layer 3: Docker Network (Container Isolation)       │
│  - Private network                                   │
│  - Container-to-container only                      │
│  - No direct internet access                        │
└────────────────────┬────────────────────────────────┘
                     ▼
┌─────────────────────────────────────────────────────┐
│ Layer 4: Application (Auth & Authorization)         │
│  - Session-based authentication                     │
│  - Password hashing (SHA-256)                       │
│  - Permission-based access control                  │
│  - CSRF protection                                  │
└─────────────────────────────────────────────────────┘
```

## Scaling Considerations

The current architecture supports:
- **Horizontal Scaling**: Add more branches by duplicating service config
- **Vertical Scaling**: Increase container resources via deploy limits
- **Geographic Distribution**: Deploy separate stacks per region
- **High Availability**: Use Docker Swarm or Kubernetes for redundancy

### Example: Adding a 4th Branch

```yaml
# In docker-compose.multi.yml
services:
  twilio-app-slc:  # Salt Lake City
    build: .
    container_name: twilio_responder_slc
    environment:
      - BRANCH_NAME=slc
      - TWILIO_ACCOUNT_SID=${SLC_TWILIO_ACCOUNT_SID}
      # ... other SLC_ prefixed variables
```

Then add to Cloudflare tunnel:
- `slc.axiom-emergencies.com` → `http://twilio_responder_slc:5000`

And update admin dashboard `BRANCHES` dictionary in `app.py`.
