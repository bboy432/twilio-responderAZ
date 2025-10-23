# Migration Guide: Environment Variables to Dashboard Configuration

This guide will help you migrate from environment variable-based configuration to dashboard-based configuration.

## Overview

**What Changed:**
- Branch instances (TUC, POC, REX) no longer read Twilio and notification settings from environment variables
- All operational configuration now comes exclusively from the admin dashboard database
- Environment variables serve only as initial defaults for the admin dashboard

**Why This Change:**
- ✓ No need to redeploy containers when changing settings
- ✓ Centralized configuration management through web UI
- ✓ Better security (credentials stored in database, not env vars)
- ✓ Easier to manage multi-branch deployments
- ✓ Audit trail of configuration changes

## Migration Steps

### Step 1: Verify Current Setup

1. Log in to your Portainer instance
2. Check the stack environment variables for your branches
3. Document current values (screenshot recommended)

### Step 2: Verify Admin Dashboard Access

1. Access your admin dashboard: `https://axiom-emergencies.com`
2. Log in with admin credentials (see your secure credential store or initial setup documentation)
3. Verify you can see all three branches (Tucson, Pocatello, Rexburg)

### Step 3: Migrate Each Branch

For each branch (TUC, POC, REX):

1. **Load Current Settings:**
   - Click on the branch card in the admin dashboard
   - Click "⚙️ Settings" button
   - You should see all current environment variables loaded as defaults

2. **Review Settings:**
   - Verify all values are correct
   - Check that phone numbers are properly formatted (+1XXXXXXXXXX)
   - Ensure Twilio credentials are accurate

3. **Save to Database:**
   - Click "💾 Save Settings" at the bottom
   - Wait for confirmation message
   - Settings are now stored in the database

4. **Verify Branch Still Works:**
   - Go back to the main dashboard
   - Check that the branch status shows "Ready" (green)
   - Try triggering a test emergency (optional)

### Step 4: Update Docker Compose (Recommended)

After successfully migrating all branches, you can simplify your docker-compose configuration:

**Before (docker-compose.yml):**
```yaml
twilio-app-tuc:
  environment:
    - BRANCH_NAME=tuc
    - ADMIN_DASHBOARD_URL=http://admin-dashboard:5000
    - PUBLIC_URL=https://tuc.axiom-emergencies.com
    - FLASK_PORT=5000
    # All these can now be removed:
    - TWILIO_ACCOUNT_SID=${TUC_TWILIO_ACCOUNT_SID}
    - TWILIO_AUTH_TOKEN=${TUC_TWILIO_AUTH_TOKEN}
    - TWILIO_PHONE_NUMBER=${TUC_TWILIO_PHONE_NUMBER}
    - TWILIO_AUTOMATED_NUMBER=${TUC_TWILIO_AUTOMATED_NUMBER}
    - TWILIO_TRANSFER_NUMBER=${TUC_TWILIO_TRANSFER_NUMBER}
    - TRANSFER_TARGET_PHONE_NUMBER=${TUC_TRANSFER_TARGET_PHONE_NUMBER}
    - RECIPIENT_PHONES=${TUC_RECIPIENT_PHONES}
    - RECIPIENT_EMAILS=${TUC_RECIPIENT_EMAILS}
    - DEBUG_WEBHOOK_URL=${TUC_DEBUG_WEBHOOK_URL}
```

**After (simplified):**
```yaml
twilio-app-tuc:
  environment:
    - BRANCH_NAME=tuc
    - ADMIN_DASHBOARD_URL=http://admin-dashboard:5000
    - PUBLIC_URL=https://tuc.axiom-emergencies.com
    - FLASK_PORT=5000
    # All other settings come from admin dashboard!
```

### Step 5: Clean Up .env File (Optional)

You can remove or comment out the operational environment variables from your `.env` file:

```bash
# Bootstrap variables (keep these)
TUC_PUBLIC_URL=https://tuc.axiom-emergencies.com
POC_PUBLIC_URL=https://poc.axiom-emergencies.com
REX_PUBLIC_URL=https://rex.axiom-emergencies.com

# Optional: Keep as backup/documentation, but not used by branches
# TUC_TWILIO_ACCOUNT_SID=...
# TUC_TWILIO_AUTH_TOKEN=...
# etc.
```

### Step 6: Redeploy (Optional)

If you cleaned up the docker-compose and .env files:

```bash
# Verify you're in the correct directory and branch
cd /path/to/twilio-responderAZ
git status

# Pull the latest changes
git pull

# Restart the stack
docker-compose -f docker-compose.multi.yml down
docker-compose -f docker-compose.multi.yml up -d
```

Note: This is optional - the system works fine with or without the env vars in docker-compose.

## Validation

After migration, verify each branch:

1. **Check Status:**
   - Admin dashboard shows "Ready" status for each branch
   - No error messages in branch logs

2. **Test Emergency:**
   - Trigger a test emergency from the dashboard
   - Verify SMS and call are sent correctly
   - Check that all notifications go to correct recipients

3. **Test Settings Changes:**
   - Update a setting (e.g., add a recipient phone number)
   - Save changes
   - Trigger another test emergency
   - Verify the change took effect

## Rollback (If Needed)

If you encounter issues:

1. **Keep Environment Variables:**
   - Don't remove env vars from Portainer yet
   - The admin dashboard will continue to use them as defaults

2. **Contact Support:**
   - Check branch logs for error messages
   - Review admin dashboard settings for any typos
   - Verify admin dashboard container is running

## Common Issues

### Branch Shows Offline
- **Cause:** Admin dashboard is not accessible
- **Fix:** Check that admin-dashboard container is running
- **Check:** `docker ps | grep admin-dashboard`

### "Configuration not found in admin dashboard"
- **Cause:** Settings not saved to database yet
- **Fix:** Open branch settings in admin dashboard and click Save

### SMS/Calls Not Sending
- **Cause:** Twilio credentials incorrect in database
- **Fix:** Re-enter credentials in admin dashboard settings

### "Twilio credentials not configured"
- **Cause:** Settings not loaded from admin dashboard
- **Fix:** 
  1. Check admin dashboard is accessible
  2. Verify settings are saved in database
  3. Wait 5 minutes for cache refresh or restart branch container

## New Deployments

For brand new deployments after this change:

1. **Set Minimal Bootstrap Environment Variables:**
   ```yaml
   environment:
     - BRANCH_NAME=tuc
     - ADMIN_DASHBOARD_URL=http://admin-dashboard:5000
     - PUBLIC_URL=https://tuc.axiom-emergencies.com
     - FLASK_PORT=5000  # Optional, defaults to 5000 if not set
   ```
   
   Note: Only `BRANCH_NAME`, `ADMIN_DASHBOARD_URL`, and `PUBLIC_URL` are strictly required. `FLASK_PORT` is optional and defaults to 5000.

2. **Configure via Dashboard:**
   - Log in to admin dashboard
   - Go to branch settings
   - Enter all Twilio and notification settings
   - Click Save

3. **No Redeploy Needed:**
   - All future changes via dashboard
   - No container restarts required

## Benefits of New Approach

1. **No Downtime:** Change settings without redeploying containers
2. **Web-Based:** Friendly UI instead of editing YAML files
3. **Audit Trail:** See who changed what and when
4. **Validation:** Dashboard validates settings before saving
5. **Centralized:** Manage all branches from one place
6. **Secure:** Credentials in database, not plain text in docker-compose

## Questions?

- Check the [SETTINGS_MANAGEMENT.md](SETTINGS_MANAGEMENT.md) for detailed settings documentation
- Review [README.md](README.md) for updated environment variable information
- Contact your system administrator for support
