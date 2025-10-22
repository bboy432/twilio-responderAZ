# Twilio Responder — Multi-Instance Emergency Response System

This is a Flask-based Twilio emergency response system that supports multiple independent branch instances with a centralized admin dashboard. Each branch operates independently with its own Twilio configuration, phone numbers, and recipients.

## 🚨 Multi-Instance Architecture

The system supports three branch locations:
- **Tucson (TUC)** - tuc.axiom-emergencies.com
- **Pocatello (POC)** - poc.axiom-emergencies.com
- **Rexburg (REX)** - rex.axiom-emergencies.com

Plus a centralized **Admin Dashboard** at axiom-emergencies.com for monitoring and management.

## 🚀 Quick Start

See **[QUICKSTART.md](QUICKSTART.md)** for step-by-step setup instructions.

```bash
# 1. Configure environment
cp .env.example .env
nano .env

# 2. Deploy
docker-compose -f docker-compose.multi.yml up -d

# 3. Access dashboard
# https://axiom-emergencies.com
# Login: axiomadmin / Dannyle44!
```

## 📖 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Get started in minutes
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete deployment guide
- **[DEBUGGING_CALLS.md](DEBUGGING_CALLS.md)** - 🆕 Troubleshoot call failures
- **[SETTINGS_MANAGEMENT.md](SETTINGS_MANAGEMENT.md)** - Manage settings through dashboard
- **[PORTAINER.md](PORTAINER.md)** - Portainer stack configuration
- **[CLOUDFLARE.md](CLOUDFLARE.md)** - Cloudflare tunnel setup
- **[admin-dashboard/README.md](admin-dashboard/README.md)** - Admin dashboard features
- **[API Reference](#api-reference)** - Below in this document

## 🎯 Features

### Admin Dashboard
1. **Multi-Branch Management** - Monitor all three branches from one dashboard
2. **User Management** - Create sub-accounts with branch-specific permissions
3. **Settings Management** - Edit Twilio and notification settings through web UI
4. **Branch Control** - Enable/disable branches with confirmation and SMS notifications
5. **Real-Time Status** - Live status updates for each branch (auto-refresh every 30s)
6. **Permission System** - Granular control over view, trigger, and disable permissions

### Each Branch Instance
- Independent Twilio configuration
- Separate phone numbers and recipients
- Individual emergency handling
- Real-time status monitoring
- Timeline and logging

### Security
- Session-based authentication
- Password hashing (SHA-256)
- Permission-based access control
- Double confirmation for critical actions
- SMS notifications for admin actions

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│         Cloudflare Tunnel (SSL/TLS)             │
└──────────────┬──────────────────────────────────┘
               │
    ┌──────────┼────────────┬────────────┬────────────┐
    │          │            │            │            │
┌───▼────┐ ┌──▼────┐  ┌────▼───┐  ┌────▼───┐  ┌────▼───┐
│  Root  │ │  TUC  │  │  POC   │  │  REX   │  │ Admin  │
│ Domain │ │ Branch│  │ Branch │  │ Branch │  │Dashboard│
└────────┘ └───────┘  └────────┘  └────────┘  └────────┘
              │             │           │           │
              └─────────────┴───────────┴───────────┘
                      Docker Network
```

---

## API Reference & Dashboard Integration Guide

This section describes the Flask-based Twilio Responder API and how to integrate its endpoints into a dashboard. It explains the available HTTP endpoints, expected payloads, webhook flows, debug tools, and practical tips for building a dashboard UI.

## 🎯 Quick Start - Dashboard

**NEW**: A ready-to-use monitoring dashboard is included in the `dashboard/` directory!

```bash
cd dashboard
python3 -m http.server 8080
# Open http://localhost:8080 in your browser
```

See [dashboard/README.md](dashboard/README.md) for full documentation.

## Quick overview
- App: Flask app that receives emergency webhooks, notifies technicians by SMS and call via Twilio, and manages a single active emergency at a time.
- Dashboard: A web-based monitoring interface for real-time status, emergency triggering, and log analysis (see `dashboard/` directory).
- Debugging: The app can post structured debug events to `DEBUG_WEBHOOK_URL` or a `webhook_url` provided to the debug endpoint.
- Logs: The application writes logs to `/app/logs/app.log` and exposes parsing utilities for timeline/summary extraction.

## Important environment variables
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` — Twilio credentials
- `TWILIO_PHONE_NUMBER`, `TWILIO_AUTOMATED_NUMBER`, `TWILIO_TRANSFER_NUMBER` — phone numbers used by Twilio flows
- `PUBLIC_URL` — Public URL where Twilio should post callbacks (e.g., https://yourdomain.com)
- `FLASK_PORT` — Port the Flask app listens on (default `5000`)
- `RECIPIENT_PHONES` — Comma-separated list of additional SMS recipients
- `RECIPIENT_EMAILS` — Comma-separated list of emails used for simulated email notifications
- `DEBUG_WEBHOOK_URL` — (Optional) If set, the app will POST structured debugging events to this URL. The application works fully without this variable - all events are logged locally regardless.

## Endpoints (for dashboard integration)
All endpoints are mounted at the app root (e.g., `https://yourdomain.com/`). Replace `{{BASE_URL}}` with your configured `PUBLIC_URL`.

### 1) POST /webhook
Starts the emergency workflow and notifies technicians.
- Method: POST
- Content-Type: application/json
- Request body example:
  {
    "chosen_phone": "+1208XXXXXXX",
    "customer_name": "Jane Doe",
    "user_stated_callback_number": "+1555XXXXXXX",
    "incident_address": "123 Main St, Town",
    "emergency_description_text": "No heat, urgent"
  }
- Response: 200 on success, 503 if an emergency is already active, 500 on server error

Dashboard usage:
- Use this endpoint to kick off an emergency. Show immediate status change in the UI (e.g., "Notifying technician...").
- Store the chosen `technician_number` for later correlation with call events.

### 2) POST /sms_reply
This endpoint is used by Twilio for incoming SMS messages containing status requests.
- Method: POST
- Twilio will send `From` and `Body` form fields
- The app attempts to reply via `messages.send_status_report(from_number)` if the `messages` module is available
- Response: 204 (no content)

Dashboard usage:
- If you want inbound SMS history, log incoming SMS events from `DEBUG_WEBHOOK_URL` events (the app posts `incoming_sms` events).

### 3) POST /incoming_twilio_call
Twilio posts call parameters here when a customer calls in. The app responds with TwiML to enqueue the caller.
- Method: POST (form-encoded)
- Parameters include `From`, `To`, `CallSid`, `CallStatus`
- Response: TwiML XML returned by the endpoint

Dashboard usage:
- Track `incoming_call` events (the app sends `incoming_call` debug events when enabled) and reflect queue state for `active_emergency`.

### 4) POST /technician_call_ended
Called by Twilio when the initial technician call ends. Used to progress the flow and potentially connect technician to waiting customer.
- Method: POST
- Query param: `emergency_id` (the app includes this in the `status_callback` when initiating calls)
- The app responds with 200

Dashboard usage:
- Use this endpoint's events (visible via `DEBUG_WEBHOOK_URL`) to update call progress: "Technician notified", "Connected", "Completed".

### 5) POST /conference_status
Conference callback endpoint for Twilio conference events (status, duration, participant count).
- Method: POST
- Query param: `emergency_id`
- The app sends `conference_status` debug events and clears the active emergency when done

Dashboard usage:
- Use these events to show final call statistics and let users see call duration and participants.

### 6) GET /status and GET /api/status
- `GET /status` — Rendered HTML status page that includes recent parsed call timeline.
- `GET /api/status` — JSON summary: `{status: "Ready|In Use|Error", message: "..."}`

Dashboard usage:
- Poll `/api/status` to show live health (e.g., green/yellow/red). Fetch `/status` or parse `parse_log_for_timeline()` output via `/debug_firehose` for recent events.

### 7) GET /api/logs
Retrieves application logs in JSON format for monitoring and debugging.
- Method: GET
- Query parameters:
  - `?all` — Returns all parsed log entries
  - `?recent=N` — Returns the N most recent log entries (e.g., `?recent=10`)
- Response format:
  ```json
  {
    "status": "success",
    "count": 10,
    "logs": [
      {
        "title": "Webhook: Emergency Triggered",
        "timestamp": "Jan 15, 03:45:12 PM",
        "icon": "🔗",
        "details": "...",
        "status": "success"
      }
    ]
  }
  ```
- Error responses: 400 (invalid parameters), 404 (no log file), 500 (server error)

Dashboard usage:
- Use `GET /api/logs?recent=20` to display recent activity in a timeline view.
- Use `GET /api/logs?all` to retrieve complete log history for analysis.
- The endpoint works without `DEBUG_WEBHOOK_URL` configured, making it suitable for production use.

### 8) GET|POST /debug_firehose
Sends the app logs and parsed timeline to a webhook URL. This is useful for on-demand debugging or for pulling recent events into a dashboard.
- Method: GET or POST
- Query parameter: `webhook_url` (preferred) — the full POST target (e.g., https://webhook.site/your-uuid)
- If `webhook_url` is not provided, the endpoint will use `DEBUG_WEBHOOK_URL` from the environment
- Payload posted to the webhook is JSON:
  {
    "event": "debug_firehose_log_dump",
    "timestamp": "...",
    "metadata": { "hostname": "...", "public_url": "..." },
    "timeline": [ ...parsed events... ],
    "raw_log_snippet": "..."
  }
- Response: JSON summary of the POST result and timeline count

Dashboard usage:
- Provide a "Send Logs to Debug Webhook" button. Allow the operator to paste the webhook POST URL (not the viewer URL with fragments) and click to send.
- Display the returned `timeline` in a human-friendly UI and store it if necessary.

## Debug / Event webhooks (what the app emits)
When `DEBUG_WEBHOOK_URL` is set, the app posts structured debug events for many internal actions. Example events include:
- `app_start`, `app_start_failure`
- `webhook_received`, `webhook_processing_error`
- `incoming_call`, `incoming_sms`
- `emergency_call_start`, `emergency_call_initiated`, `emergency_call_error`
- `sms_attempt`, `sms_sent`, `sms_error`
- `technician_call_initiated`, `conference_status`, `emergency_concluded`

Each event payload includes at least:
- `event` (string)
- `timestamp` (ISO 8601)
- `data` (object with contextual details)

Dashboard usage:
- Register a server-side endpoint to consume these webhooks for real-time updates, or use a webhook proxy (like webhook.site) for manual inspection.
- Events are useful to populate a timeline, show live status changes, and display error details.

## Best practices for dashboard integration
- Use server-to-server webhooks: have your dashboard backend receive the `DEBUG_WEBHOOK_URL` events and then push updates to front-end clients via WebSockets or Server-Sent Events.
- Correlate events by `emergency_id` when present. Many debug events include the `emergency_id` or call SID.
- For security, the app does not send signed webhooks; if you need integrity, add an HMAC signature check in the app (I can add that).
- Pagination: use the timeline parsing to show recent activity; request `/debug_firehose` for a full dump when needed.
- Avoid showing raw logs to general users; restrict that capability to operators.

## Example client snippets
### Trigger emergency (JavaScript, fetch)
```js
fetch(`${BASE_URL}/webhook`, {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    chosen_phone: '+1208XXXXXXX',
    customer_name: 'Jane Doe',
    user_stated_callback_number: '+1555XXXXXXX',
    incident_address: '123 Main St',
    emergency_description_text: 'No heat'
  })
})
.then(r => r.json()).then(console.log)
```

### Send logs to webhook (PowerShell)
```powershell
$webhook = 'https://webhook.site/<your-uuid>'
Invoke-WebRequest -Uri "$PUBLIC_URL/debug_firehose?webhook_url=$webhook" -Method Get
```

### Example dashboard flow
1. Operator clicks "Trigger Emergency" and sends `/webhook` with chosen phone and details.
2. Dashboard shows "Notifying technician..." and subscribes to events for updates.
3. Dashboard receives `sms_sent` and `emergency_call_initiated` webhook events and updates UI.
4. If operator wants logs, they click "Send Logs" and paste a webhook.post URL and call `/debug_firehose`.
5. Dashboard receives parsed timeline and displays call history and any recent errors.

## Security & deployment notes
- Keep Twilio credentials and `DEBUG_WEBHOOK_URL` secret. Use vaults or environment variable managers.
- If exposing `/debug_firehose` publicly, gate it behind authentication or only allow internal access; logs may contain sensitive data (phone numbers, addresses).
- If using Cloudflare Tunnel (cloudflared), ensure the ingress target matches the container name on the Docker network (e.g., `twilio_responder_app`).

## Next additions I can provide
- HMAC-signed debug webhooks for integrity verification
- Base64 or GZIP compressed log payloads for large logs
- A sample dashboard repository that demonstrates UI components consuming the events and calling the endpoints

If you'd like, I can now: add HMAC signing, provide the PowerShell script to deploy the cloudflared changes, or generate a minimal React dashboard that consumes the webhook events. Which do you want next?