# Twilio Responder Dashboard

A web-based monitoring dashboard for the Twilio Emergency Responder system. This dashboard provides real-time monitoring, emergency triggering, and log analysis capabilities through the responder's built-in API.

## Features

- **Real-time System Status Monitoring**: View the current state of the emergency responder system (Ready, In Use, Error)
- **Emergency Triggering**: Manually trigger test emergencies with full details
- **Debug Log Access**: Send logs to webhook URLs for analysis
- **Event Timeline**: View recent emergency events and call history
- **Auto-refresh**: Automatic status updates every 30 seconds
- **Responsive Design**: Works on desktop, tablet, and mobile devices

## Quick Start

### Option 1: Direct File Access (Simplest)

1. Open `dashboard/index.html` directly in your web browser
2. Configure the API URL to point to your Twilio Responder instance
3. Start monitoring!

### Option 2: Using a Simple HTTP Server

```bash
# Navigate to the dashboard directory
cd dashboard

# Python 3
python3 -m http.server 8080

# Python 2
python -m SimpleHTTPServer 8080

# Node.js (with http-server installed)
npx http-server -p 8080

# Then open http://localhost:8080 in your browser
```

### Option 3: Deploy with Docker (Production)

```bash
cd dashboard
docker build -t twilio-dashboard .
docker run -d -p 8080:80 --name twilio-dashboard twilio-dashboard
```

## Configuration

### Setting the API URL

1. Open the dashboard in your browser
2. In the "Configuration" section, enter your Twilio Responder API URL
   - For local testing: `http://localhost:5000`
   - For production: `https://your-domain.com`
3. Click "Save" - the configuration is saved in browser localStorage

### CORS Considerations

If you're accessing the dashboard from a different origin than the API, you may need to enable CORS on the Twilio Responder application. Add this to `app.py`:

```python
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
```

Then add `flask-cors` to `requirements.txt`:

```bash
echo "flask-cors" >> requirements.txt
```

## Using the Dashboard

### Monitoring System Status

The status card shows:
- **Ready** (Green): System is online and waiting for calls
- **In Use** (Yellow): An emergency call is currently being processed
- **Error** (Red): A recent error was detected in the logs

Click "🔄 Refresh Status" to manually update the status, or wait for the automatic 30-second refresh.

### Triggering an Emergency

1. Fill in all required fields:
   - **Technician Phone**: Must start with + (e.g., `+12084039927`)
   - **Customer Name**: The customer's name
   - **Callback Number**: Must start with + (e.g., `+15551234567`)
   - **Incident Address**: Full address of the emergency
   - **Emergency Description**: Detailed description of the issue

2. Click "🚨 Trigger Emergency"

3. The system will:
   - Send an SMS to the technician
   - Make an automated call with the emergency details
   - Update the system status to "In Use"

### Viewing Debug Logs

#### Send Logs to Webhook

1. Get a webhook URL from a service like [webhook.site](https://webhook.site)
2. Paste the webhook URL in the "Webhook URL" field
3. Click "📤 Send Logs"
4. View the logs in the webhook service's dashboard

The log dump includes:
- Parsed timeline events
- Raw log snippet (up to 100KB)
- System metadata (hostname, public URL)

#### Load Timeline

Click "🔄 Load Timeline" to view recent emergency events directly in the dashboard. Events are displayed in chronological order with:
- Event icon and title
- Timestamp
- Full event details
- Status indicator (success/error)

## API Endpoints Used

The dashboard interacts with these Twilio Responder API endpoints:

- `GET /api/status` - System health check
- `GET /status` - HTML status page with timeline
- `POST /webhook` - Trigger emergency workflow
- `GET /debug_firehose` - Send logs to webhook URL

For complete API documentation, see the main [README.md](../README.md) file.

## Architecture

```
dashboard/
├── index.html              # Main dashboard HTML
├── static/
│   ├── css/
│   │   └── dashboard.css   # Styling
│   └── js/
│       └── dashboard.js    # Dashboard logic
├── Dockerfile              # Docker configuration (optional)
└── README.md              # This file
```

### Technology Stack

- **Pure HTML/CSS/JavaScript**: No frameworks required
- **Vanilla JavaScript**: No dependencies, works in all modern browsers
- **localStorage**: Configuration persistence
- **Fetch API**: HTTP requests to the Twilio Responder API

## Deployment

### Static Hosting (Recommended)

The dashboard is a static website and can be deployed to any static hosting service:

- **GitHub Pages**: Push to a `gh-pages` branch
- **Netlify**: Drag and drop the `dashboard` folder
- **Vercel**: Deploy from Git repository
- **AWS S3 + CloudFront**: Static website hosting
- **Firebase Hosting**: `firebase deploy`

### Docker Deployment

Create a `Dockerfile` in the `dashboard` directory:

```dockerfile
FROM nginx:alpine
COPY . /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

Build and run:

```bash
docker build -t twilio-dashboard .
docker run -d -p 8080:80 twilio-dashboard
```

## Security Considerations

1. **HTTPS**: Always use HTTPS in production to protect API credentials
2. **Authentication**: The dashboard has no built-in authentication. Protect it with:
   - Web server basic auth
   - OAuth2 proxy
   - VPN access only
3. **API URL**: Don't expose your production API URL publicly
4. **Webhook URLs**: Webhook.site and similar services are for debugging only

## Troubleshooting

### "Connection Error" Status

- Verify the API URL is correct
- Check if the Twilio Responder is running
- Ensure CORS is enabled if accessing from a different domain
- Check browser console for detailed error messages

### Emergency Trigger Fails

- Ensure phone numbers start with `+` and include country code
- Verify all fields are filled in
- Check that the system status is "Ready" (not already in use)
- Review the response area for specific error messages

### Timeline Not Loading

- Ensure the Twilio Responder has processed at least one emergency
- Check that the `/status` endpoint is accessible
- Verify the API URL configuration

## Development

To modify the dashboard:

1. Edit `index.html` for structure changes
2. Edit `static/css/dashboard.css` for styling
3. Edit `static/js/dashboard.js` for functionality
4. Open `index.html` in a browser (no build step needed)

### Adding New Features

The dashboard uses a modular approach:

```javascript
// Add a new API call
async function newFeature() {
    try {
        const response = await fetch(`${config.apiUrl}/new-endpoint`);
        const data = await response.json();
        // Process data...
        showResponse('Success!', 'success');
    } catch (error) {
        showResponse(`Error: ${error.message}`, 'error');
    }
}
```

## License

This dashboard is part of the twilio-responderAZ project. See the main repository for license information.

## Support

For issues or questions:
1. Check the main [README.md](../README.md) for API documentation
2. Review browser console for JavaScript errors
3. Verify API endpoint accessibility with curl or Postman
4. Open an issue on the GitHub repository

## Contributing

Contributions welcome! Please:
1. Test changes in multiple browsers
2. Maintain the vanilla JavaScript approach (no frameworks)
3. Keep the design responsive
4. Update this README with new features

---

**Note**: This dashboard is designed to work with the twilio-responderAZ Flask application. Ensure that application is running and accessible before using this dashboard.
