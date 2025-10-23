# Settings Management Guide

This guide explains how to manage branch settings through the admin dashboard instead of editing environment variables in Portainer.

## Overview

**Branch instances are now configured 100% through the admin dashboard web interface.** Environment variables are no longer used for operational configuration - they serve only as optional initial defaults.

Authorized users can edit all Twilio and notification settings directly through the admin dashboard. Settings are stored in the database and automatically synchronized with the branch instances every 5 minutes (or immediately after saving).

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

### 4. Environment Variables as Initial Defaults Only
- Environment variables (e.g., `TUC_TWILIO_ACCOUNT_SID`) serve as initial defaults
- The admin dashboard uses these defaults when loading settings for the first time
- Once settings are saved via the dashboard, database values take precedence
- Branch instances do NOT read environment variables directly - all config comes from admin dashboard
- If the admin dashboard is unavailable, branches cannot function (by design for centralized management)

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

1. **Database Settings** (used by branch instances)
   - Settings saved through the dashboard
   - Stored in admin database
   - This is the ONLY source branch instances read from
   
2. **Environment Variables** (initial defaults for admin dashboard only)
   - Used by admin dashboard as defaults when settings are not yet in database
   - NOT read by branch instances directly
   - Example: `TUC_TWILIO_ACCOUNT_SID` becomes default for Tucson branch's TWILIO_ACCOUNT_SID

### How It Works

1. **On Startup**: Branch instances load settings from admin dashboard (required)
2. **Every 5 Minutes**: Settings cache is automatically refreshed from admin dashboard
3. **On Save**: Admin dashboard updates database, branch picks up changes within 5 minutes
4. **On Failure**: If admin dashboard is unreachable, branch cannot function (ensure high availability)

### Settings Cache

Branch instances maintain a local cache of settings:
- Cache is refreshed every 5 minutes from admin dashboard
- If admin dashboard is unreachable during refresh, cache retains last known values
- No environment variable fallback (all configuration must come from admin dashboard)

## Migration from Environment Variables

### Existing Deployments

If you have an existing deployment with environment variables set in Portainer:

1. **Phase 1 - Automatic Migration**: Admin dashboard reads existing env vars as defaults
2. **Phase 2 - Save to Database**: Open each branch's settings in admin dashboard and click "Save"
3. **Phase 3 - Verify**: Check that branches work correctly with database settings
4. **Phase 4 - Cleanup (Optional)**: Remove operational env vars from Portainer, keep only:
   - `BRANCH_NAME` (e.g., `tuc`, `poc`, `rex`)
   - `ADMIN_DASHBOARD_URL` (e.g., `http://admin-dashboard:5000`)
   - `PUBLIC_URL` (e.g., `https://tuc.axiom-emergencies.com`)
   - `FLASK_PORT` (optional, default: 5000)

### New Deployments

For new deployments:

1. Set **only** bootstrap environment variables in docker-compose:
   - `BRANCH_NAME`
   - `ADMIN_DASHBOARD_URL`
   - `PUBLIC_URL`
   - `FLASK_PORT` (optional)
2. Optionally set initial defaults (e.g., `TUC_TWILIO_ACCOUNT_SID`) for admin dashboard
3. Configure all branch settings through the admin dashboard web interface
4. Settings are stored in database and automatically synchronized
5. No need to redeploy containers when changing settings

## Troubleshooting

### Settings Not Updating

1. Check that you're logged in as an admin user
2. Verify the branch instance is running
3. Check the branch logs for settings reload messages
4. Try manually reloading: `POST http://<branch-url>/api/reload_settings`

### Branch Can't Connect to Admin Dashboard

- Check that `ADMIN_DASHBOARD_URL` is set correctly in docker-compose
- Verify admin-dashboard container is running
- Check Docker network connectivity between containers
- Branch instances REQUIRE admin dashboard for configuration (no env var fallback)

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
