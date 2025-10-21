# Example: Using the Dashboard

This directory contains usage examples for the Twilio Responder Dashboard.

## Quick Test

1. **Start the Twilio Responder API** (in the main directory):
   ```bash
   # Set up environment variables
   export TWILIO_ACCOUNT_SID="your_account_sid"
   export TWILIO_AUTH_TOKEN="your_auth_token"
   export TWILIO_PHONE_NUMBER="+1234567890"
   # ... other required variables
   
   # Run the Flask app
   python app.py
   ```

2. **Start the Dashboard** (in the dashboard directory):
   ```bash
   cd dashboard
   python3 -m http.server 8080
   ```

3. **Open the Dashboard**:
   - Navigate to `http://localhost:8080`
   - Configure the API URL to `http://localhost:5000`
   - Click "Save"

## Example Workflow

### Monitoring System Status

1. The dashboard will automatically fetch the system status every 30 seconds
2. You can manually refresh by clicking "🔄 Refresh Status"
3. Status indicators:
   - **Green (Ready)**: System is operational
   - **Yellow (In Use)**: Emergency in progress
   - **Red (Error)**: System error detected

### Triggering a Test Emergency

Fill in the form with test data:

```
Technician Phone: +12084039927
Customer Name: Test Customer
Callback Number: +15551234567
Incident Address: 123 Test Street, Test City, TS 12345
Emergency Description: Test emergency - no heat in building
```

Click "🚨 Trigger Emergency" and observe:
1. Response message confirms the trigger
2. System status changes to "In Use"
3. SMS and call are initiated to the technician

### Viewing Logs

#### Method 1: Send to Webhook

1. Go to [webhook.site](https://webhook.site)
2. Copy the webhook URL (looks like `https://webhook.site/xxxxx-xxx-xxx`)
3. Paste it in the "Webhook URL" field
4. Click "📤 Send Logs"
5. View the detailed logs on webhook.site

#### Method 2: Load Timeline

1. Click "🔄 Load Timeline"
2. View recent events directly in the dashboard
3. Each event shows timestamp and details

## API Endpoints Used

The dashboard interacts with these endpoints:

- `GET /api/status` - Returns JSON: `{"status": "Ready|In Use|Error", "message": "..."}`
- `POST /webhook` - Triggers emergency with JSON payload
- `GET /status` - HTML page with event timeline
- `GET /debug_firehose?webhook_url=...` - Sends logs to webhook

## Testing Scenarios

### Scenario 1: Check System Health

```javascript
// Manually test via browser console
fetch('http://localhost:5000/api/status')
  .then(r => r.json())
  .then(console.log);
```

Expected result:
```json
{
  "status": "Ready",
  "message": "System is online and waiting for calls."
}
```

### Scenario 2: Trigger Emergency

```javascript
// Test emergency trigger
fetch('http://localhost:5000/webhook', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    chosen_phone: '+12084039927',
    customer_name: 'Jane Doe',
    user_stated_callback_number: '+15551234567',
    incident_address: '123 Main St',
    emergency_description_text: 'No heat, urgent'
  })
})
.then(r => r.json())
.then(console.log);
```

Expected result:
```json
{
  "status": "success"
}
```

## Troubleshooting

### Dashboard shows "Connection Error"

**Cause**: Dashboard cannot reach the API
**Solution**:
1. Verify the Flask app is running: `curl http://localhost:5000/api/status`
2. Check the API URL in dashboard configuration
3. If using different domains, enable CORS in `app.py`

### Emergency trigger fails with 503

**Cause**: System is already processing an emergency
**Solution**: Wait for the current emergency to complete

### Timeline is empty

**Cause**: No emergencies have been processed yet
**Solution**: Trigger a test emergency first

## Advanced Usage

### Custom API URL

For production use, configure a real domain:

```
https://your-twilio-responder.example.com
```

Make sure:
- HTTPS is enabled
- CORS is configured if dashboard is on different domain
- Firewall allows connections

### Docker Deployment

Build and run the dashboard in Docker:

```bash
cd dashboard
docker build -t twilio-dashboard .
docker run -d -p 8080:80 twilio-dashboard
```

### Integration with CI/CD

Monitor the API in automated tests:

```bash
# Health check script
#!/bin/bash
STATUS=$(curl -s http://localhost:5000/api/status | jq -r '.status')
if [ "$STATUS" != "Ready" ]; then
  echo "System not ready: $STATUS"
  exit 1
fi
echo "System is ready"
```

## Security Notes

- **Do not expose the dashboard publicly without authentication**
- Use HTTPS in production
- Protect sensitive data (phone numbers, addresses)
- Consider using environment variables for the API URL
- Implement rate limiting on the API endpoints

## Next Steps

- Add authentication to the dashboard
- Implement WebSocket for real-time updates
- Create a mobile-responsive version
- Add notification sounds for status changes
- Implement user roles and permissions
