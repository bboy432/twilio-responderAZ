# 🚀 How to Deploy and Use This Fix

## What This Fix Does

This fix makes it **much easier to debug** why automated calls aren't working. Previously, when calls failed, you'd see:
```json
{"message":"Failed to initiate emergency call. Please check configuration and try again.","status":"error"}
```

But you couldn't see the actual error details in Portainer logs. Now you can!

## Deployment Steps

### Option 1: Using Docker Compose (Recommended)

```bash
# 1. Pull the latest changes
git pull

# 2. Rebuild and restart the containers
docker-compose -f docker-compose.multi.yml up -d --build

# 3. Check that containers are running
docker-compose -f docker-compose.multi.yml ps
```

### Option 2: Using Portainer

1. Go to your Portainer dashboard
2. Navigate to **Stacks**
3. Select your stack (e.g., `twilio-responder`)
4. Click **Update the stack**
5. Make sure "Re-pull image and redeploy" is checked
6. Click **Update**
7. Wait for containers to restart

## How to Use

### When a call fails, check Portainer logs:

1. Open Portainer
2. Go to **Containers**
3. Click on the relevant container (e.g., `twilio_responder_tuc`)
4. Click the **Logs** tab
5. Look for lines starting with `[ERROR]`

### Example Error Messages You'll See:

#### Missing Configuration:
```
[ERROR] emergency_call_config_error: {"error": "TWILIO_AUTOMATED_NUMBER is not configured"}
```
**Solution:** Add `TUC_TWILIO_AUTOMATED_NUMBER` to your `.env` file

#### Invalid Phone Format:
```
[ERROR] emergency_call_validation_error: {"error": "Invalid technician number format (missing country code): 8017104034"}
```
**Solution:** Use `+18017104034` instead of `8017104034`

#### Authentication Error:
```
[ERROR] call_initiation_error: {"error": "Failed to initiate call: Unable to create record: Authenticate", "to": "+18017104034"}
```
**Solution:** Check your Twilio credentials (ACCOUNT_SID and AUTH_TOKEN)

#### Unverified Number (Trial Account):
```
[ERROR] call_initiation_error: {"error": "Failed to initiate call: The number +15551234567 is unverified", "to": "+15551234567"}
```
**Solution:** Verify the number in Twilio Console or upgrade to a paid account

## Testing Your Deployment

### Step 1: Check Startup Messages

After deployment, check the container logs:
```bash
docker logs twilio_responder_tuc --tail 20
```

You should see:
```
=====================================================
Starting Flask App on http://0.0.0.0:5000
Public URL (Set in Twilio): https://tuc.axiom-emergencies.com
Web Portal: https://tuc.axiom-emergencies.com/status
Messaging module loaded: True
Detailed logs: /app/logs/app.log
Note: Error details are printed to stdout and also logged to the file above
=====================================================
```

### Step 2: Test with the Test Script

```bash
# Test a valid request
./test_webhook.sh https://tuc.axiom-emergencies.com +15551234567

# Watch logs in real-time while testing
docker logs -f twilio_responder_tuc
```

### Step 3: Trigger a Test Call

```bash
curl -X POST https://tuc.axiom-emergencies.com/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Test Customer",
    "user_stated_callback_number": "+15551234567",
    "incident_address": "123 Test St",
    "emergency_description_text": "Test emergency",
    "chosen_phone": "+18017104034"
  }'
```

Then immediately check Portainer logs to see if any `[ERROR]` messages appear.

## Troubleshooting Common Issues

### "Still seeing generic error message"

**Check:** Are you looking at the **container logs** in Portainer or the API response?
- API response will ALWAYS be generic (security)
- Container logs will have details

### "Not seeing [ERROR] messages"

**Check:** Did you rebuild the container after pulling changes?
```bash
docker-compose -f docker-compose.multi.yml up -d --build --force-recreate
```

### "Container won't start"

**Check:** Environment variables are properly set
```bash
docker exec twilio_responder_tuc env | grep TWILIO
```

### "Still can't figure out the issue"

**Next steps:**
1. Read [../features/DEBUGGING_CALLS.md](../features/DEBUGGING_CALLS.md) for detailed troubleshooting
2. Check all environment variables are set correctly
3. Verify Twilio account is active and has credits
4. Test with the test script: `./test_webhook.sh`

## What Changed Technically

### Code Changes (app.py):
- Modified `send_debug()` function to print error events to stdout
- Added 11 error event types that trigger stdout logging
- Updated startup message to remind about log locations

### Documentation Added:
- **[../features/DEBUGGING_CALLS.md](../features/DEBUGGING_CALLS.md)**: Complete debugging guide
- **[../archive/FIX_SUMMARY_DEBUGGING.md](../archive/FIX_SUMMARY_DEBUGGING.md)**: Technical details of the fix
- **DEPLOYMENT_GUIDE.md** (this file): How to deploy and use

### What Stayed the Same:
- ✅ API responses (still generic for security)
- ✅ Error handling logic (already fixed previously)
- ✅ Validation logic (already robust)
- ✅ Configuration requirements (no changes)
- ✅ File logging (still writes to `/app/logs/app.log`)

## Benefits of This Fix

### Before:
- ❌ Exec into container to read log file
- ❌ Hard to copy-paste errors
- ❌ Time-consuming debugging
- ❌ Needed terminal access

### After:
- ✅ View errors directly in Portainer UI
- ✅ Easy copy-paste from logs
- ✅ Fast debugging and resolution
- ✅ No terminal access needed

## Need Help?

1. **Read the docs first:**
   - [../features/DEBUGGING_CALLS.md](../features/DEBUGGING_CALLS.md) - Troubleshooting guide
   - [../archive/FIX_SUMMARY_DEBUGGING.md](../archive/FIX_SUMMARY_DEBUGGING.md) - Technical details

2. **Check the logs:**
   - Look for `[ERROR]` lines in Portainer
   - Compare with common errors in DEBUGGING_CALLS.md

3. **Test your config:**
   - Run `./test_webhook.sh`
   - Verify environment variables
   - Check Twilio account status

4. **Still stuck?**
   - Provide the specific `[ERROR]` message from logs
   - Include environment variables (redact sensitive values)
   - Mention which branch (TUC/POC/REX)

---

**This fix makes debugging 10x easier!** 🎉

Just deploy, test, and check Portainer logs for detailed error messages.
