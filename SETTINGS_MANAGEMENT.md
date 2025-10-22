# Settings Management Guide

This guide explains how to manage branch settings through the admin dashboard instead of editing environment variables in Portainer.

## Overview

Previously, all Twilio and notification settings had to be configured as environment variables in Portainer. Now, authorized users can edit these settings directly through the admin dashboard web interface. Settings are stored in the database and automatically synchronized with the branch instances.

## Permission Levels

Settings are now categorized into two permission levels:

### Basic Settings
Users with "Edit Basic Settings" permission can modify:
- **Recipient Phone Numbers**: SMS notification recipients
- **Recipient Emails**: Email notification recipients  
- **Feature Toggles**:
  - Enable/Disable SMS Text Notifications
  - Enable/Disable Email Notifications
  - Enable/Disable Automated Calls
  - Enable/Disable Call Transfer

### Advanced Settings
Users with "Edit Advanced Settings" permission (or admins) can modify:
- **Twilio Credentials**: Account SID and Auth Token
- **Phone Numbers**:
  - Primary Twilio Phone Number
  - Automated Call Number
  - Transfer Number
  - Transfer Target Number
- **Debug Settings**: Debug Webhook URL

## Features

### 1. Web-Based Settings Editor
- Edit Twilio credentials (Account SID, Auth Token)
- Configure phone numbers (Primary, Automated, Transfer numbers)
- Manage notification recipients (SMS and email)
- Update debug webhook URLs
- All from a user-friendly web interface

### 2. Real-Time Updates
- Settings are saved to the database immediately
- Branch instances automatically reload settings every 5 minutes
- Manual reload can be triggered via API
- SMS notifications sent to admin on settings changes

### 3. Security
- Admin users have full access to all settings
- Non-admin users can be granted specific permission levels:
  - **Basic Settings Permission**: Edit notification recipients and feature toggles
  - **Advanced Settings Permission**: Edit Twilio credentials and phone numbers
- Sensitive fields (tokens, credentials) are masked in the UI
- Password fields can be left blank to keep existing values
- All changes are logged with username and timestamp

### 4. Fallback to Environment Variables
- If the admin dashboard is unavailable, branches use environment variables
- Seamless failover ensures system continues working
- Database settings take priority over environment variables when available

## Accessing Settings

### For All Users

1. Log in to the admin dashboard at https://axiom-emergencies.com
2. Click on any branch card (Tucson, Pocatello, or Rexburg) that you have access to
3. Click the "⚙️ Settings" button
4. You will see sections based on your permissions:
   - Users with basic settings permission see notification recipients and feature toggles
   - Users with advanced settings permission see Twilio credentials and phone numbers
   - Admin users see all settings
5. Edit the settings you have permission to modify
6. Click "💾 Save Settings"

### Settings Page Sections

#### 🔐 Twilio Credentials (Advanced Settings)
- **Account SID**: Your Twilio Account SID (starts with AC...)
- **Auth Token**: Your Twilio Auth Token (leave blank to keep current)

#### 📞 Phone Numbers (Advanced Settings)
- **Twilio Phone Number**: Primary number for incoming calls
- **Automated Number**: Number used for automated calls to technicians
- **Transfer Number**: Number used for call transfers
- **Transfer Target Number**: Default number to transfer calls to

#### 📨 Notification Settings (Basic Settings)
- **Recipient Phone Numbers**: Comma-separated list of SMS recipients
- **Recipient Emails**: Comma-separated list of email recipients

#### 🎛️ Feature Toggles (Basic Settings)
- **Enable SMS Text Notifications**: Turn SMS notifications on/off
- **Enable Email Notifications**: Turn email notifications on/off
- **Enable Automated Calls**: Turn automated calls to technicians on/off
- **Enable Call Transfer**: Turn call transfer functionality on/off

#### 🐛 Debug Settings (Advanced Settings)
- **Debug Webhook URL**: Optional webhook URL for debugging events

## Technical Details

### Database Schema

Settings are stored in the `branch_settings` table:

```sql
CREATE TABLE branch_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    branch TEXT NOT NULL,
    setting_key TEXT NOT NULL,
    setting_value TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT,
    UNIQUE(branch, setting_key)
)
```

### API Endpoints

#### Get Settings (Authenticated)
```
GET /api/branch/<branch>/settings
```
Returns settings with sensitive values masked.

#### Update Settings (Admin or Authorized Users)
```
POST /api/branch/<branch>/settings
Content-Type: application/json

{
  "TWILIO_PHONE_NUMBER": "+15205551234",
  "RECIPIENT_PHONES": "+15205551234,+15205555678",
  "enable_texts": "true"
}
```

Returns 200 OK if user has permission to edit the settings, 403 Forbidden otherwise.

#### Internal Settings Endpoint (No Auth)
```
GET /api/internal/branch/<branch>/settings
```
Used by branch instances to fetch their settings. Only accessible within the Docker network.

#### Reload Settings on Branch
```
POST /api/reload_settings
```
Triggers immediate reload of settings from admin dashboard.

### Settings Priority

1. **Database Settings** (highest priority)
   - Settings saved through the dashboard
   - Stored in admin database
   
2. **Environment Variables** (fallback)
   - Original Portainer/docker-compose settings
   - Used if database is unavailable

### How It Works

1. **On Startup**: Branch instances try to load settings from admin dashboard
2. **Every 5 Minutes**: Settings cache is automatically refreshed
3. **On Save**: Admin dashboard triggers immediate reload on the affected branch
4. **On Failure**: Branch falls back to environment variables

### Settings Cache

Branch instances maintain a local cache of settings:
- Cache is refreshed every 5 minutes
- Cache is updated immediately when settings are saved
- If admin dashboard is unreachable, cache retains last known values
- Environment variables are used as ultimate fallback

## Migration from Environment Variables

### Existing Deployments

If you have an existing deployment with environment variables set in Portainer:

1. Settings will continue to work using environment variables
2. Once you save settings through the dashboard, database values take priority
3. You can leave environment variables in place as a fallback
4. Or remove them after confirming database settings work

### New Deployments

For new deployments:

1. Set minimal required environment variables in Portainer
2. Configure all branch-specific settings through the dashboard
3. Settings are automatically stored in the database
4. No need to redeploy containers when changing settings

## Troubleshooting

### Settings Not Updating

1. Check that you're logged in as an admin user
2. Verify the branch instance is running
3. Check the branch logs for settings reload messages
4. Try manually reloading: `POST http://<branch-url>/api/reload_settings`

### Branch Can't Connect to Admin Dashboard

- Check that `ADMIN_DASHBOARD_URL` is set correctly in docker-compose
- Verify admin-dashboard container is running
- Branch will fall back to environment variables automatically

### Sensitive Values Not Saving

- Leave password/token fields blank to keep existing values
- Only fill them in when you want to update them
- Values are never displayed in the UI for security

## Best Practices

1. **Test in Development First**: Try settings changes in a test environment
2. **Document Changes**: Keep a record of what settings you change
3. **Use Strong Credentials**: Ensure Twilio tokens are kept secure
4. **Regular Backups**: The admin database contains all settings
5. **Monitor Notifications**: Admin receives SMS on all settings changes

## Security Considerations

- Admin users have full access to all settings
- Non-admin users can be granted granular permissions:
  - View branch dashboards
  - Trigger emergency notifications
  - Enable/disable branches
  - Edit basic settings (notification recipients, feature toggles)
  - Edit advanced settings (Twilio credentials, phone numbers)
- All changes are logged with username and timestamp
- Sensitive fields are masked in the UI
- Settings are transmitted over HTTPS in production
- Internal API endpoint is only accessible within Docker network

## Example: Updating Recipient Phone Numbers

1. Navigate to branch settings (e.g., Tucson)
2. Find "Recipient Phone Numbers" field
3. Update the comma-separated list: `+15205551234,+15205555678,+15205559999`
4. Click "Save Settings"
5. Confirm the success message
6. Changes take effect within 5 minutes (or immediately on next emergency)

## Future Enhancements

Potential improvements to settings management:

- [ ] Export/import settings as JSON
- [ ] Settings history and rollback
- [ ] Bulk update across all branches
- [ ] Settings validation and testing
- [ ] API key rotation automation
- [ ] Settings templates for quick setup
