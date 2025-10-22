# Debugging Automated Call Issues - Quick Guide

## The Problem

When the automated emergency call system fails, you might see this generic error:
```json
{"message":"Failed to initiate emergency call. Please check configuration and try again.","status":"error"}
```

**This is by design for security** - we don't expose detailed error messages to external API callers. However, the detailed error information IS available in the logs.

## Where to Find Detailed Error Information

### Option 1: Portainer Container Logs (EASIEST)

With the latest fix, detailed error messages are now printed to **stdout**, which means they appear in Portainer's container logs.

**How to check:**
1. Open Portainer
2. Go to Containers
3. Click on your container (e.g., `twilio_responder_tuc`)
4. Click the **Logs** tab
5. Look for lines starting with `[ERROR]`

**Example error output:**
```
[ERROR] emergency_call_config_error: {"error": "TWILIO_AUTOMATED_NUMBER is not configured"}
[ERROR] call_initiation_error: {"error": "Failed to initiate call: Unable to create record: Authenticate", "to": "+18017104034"}
[ERROR] webhook_call_failed: {"emergency_id": "abc-123", "error": "Invalid technician number format (missing country code): 8017104034"}
```

### Option 2: Docker Command Line

If you're using Docker directly:

```bash
# View recent logs
docker logs twilio_responder_tuc --tail 100

# Follow logs in real-time
docker logs -f twilio_responder_tuc

# Search for errors
docker logs twilio_responder_tuc 2>&1 | grep "\[ERROR\]"
```

### Option 3: App Log File (Inside Container)

The detailed logs are also written to `/app/logs/app.log` inside the container:

```bash
# View the log file
docker exec twilio_responder_tuc cat /app/logs/app.log

# Follow the log file
docker exec twilio_responder_tuc tail -f /app/logs/app.log
```

## Common Error Messages and Solutions

### Error: "Twilio credentials (ACCOUNT_SID or AUTH_TOKEN) are not configured"

**Cause:** The Twilio credentials are missing or empty.

**Solution:**
1. Check your `.env` file has:
   ```
   TUC_TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   TUC_TWILIO_AUTH_TOKEN=your_auth_token_here
   ```
2. Restart the container:
   ```bash
   docker-compose -f docker-compose.multi.yml restart twilio-app-tuc
   ```

### Error: "TWILIO_AUTOMATED_NUMBER is not configured"

**Cause:** The automated phone number (used for outbound calls) is missing.

**Solution:**
1. Add to `.env` file:
   ```
   TUC_TWILIO_AUTOMATED_NUMBER=+15551234567
   ```
2. Restart the container

### Error: "Invalid technician number format (missing country code)"

**Cause:** The phone number doesn't start with `+` and country code.

**Solution:**
- Use: `+15551234567` ✅
- Not: `5551234567` ❌
- Not: `1-555-123-4567` ❌

### Error: "Unable to create record: Authenticate"

**Cause:** Twilio credentials are invalid or the account is suspended.

**Solution:**
1. Log in to Twilio Console: https://console.twilio.com
2. Verify your account status
3. Check that ACCOUNT_SID and AUTH_TOKEN are correct
4. Verify the phone number is active in your Twilio account

### Error: "Unable to create record: The number is unverified"

**Cause:** You're using a Twilio trial account and the destination number hasn't been verified.

**Solution:**
1. Go to Twilio Console > Phone Numbers > Verified Caller IDs
2. Add and verify the technician's phone number
3. OR upgrade to a paid Twilio account

### Error: "Failed to send SMS: ..."

**Note:** SMS failures don't prevent calls from being attempted. The system will continue to make the voice call even if SMS fails.

**Solution:**
- Check that `TWILIO_AUTOMATED_NUMBER` has SMS capabilities
- Verify the destination number can receive SMS

## Testing Your Configuration

Use the test script to verify your setup:

```bash
# Test the webhook endpoint
./test_webhook.sh https://tuc.axiom-emergencies.com +15551234567

# Watch the logs while testing
docker logs -f twilio_responder_tuc
```

## What Changed in This Fix

**Before:**
- Detailed errors only written to `/app/logs/app.log`
- Users had to exec into container to read log file
- Portainer logs only showed generic messages

**After:**
- Detailed errors ALSO printed to stdout (Portainer-visible)
- Easy debugging directly from Portainer UI
- Still logs to `/app/logs/app.log` for historical tracking

## Error Events That Are Logged

The following error types are now printed to stdout:
- `emergency_call_validation_error` - Phone number validation failed
- `emergency_call_config_error` - Configuration missing or invalid
- `sms_send_error` - SMS delivery failed
- `call_initiation_error` - Twilio call creation failed
- `webhook_call_failed` - Overall emergency call failed
- `webhook_validation_error` - Request validation failed
- `webhook_processing_error` - Unexpected error processing request
- `emergency_call_error` - Unexpected error in call function
- `config_load_error` - Configuration loading failed
- `connect_config_error` - Configuration error connecting to customer
- `connect_failure` - Failed to connect technician to customer

## Still Having Issues?

If you've checked the logs and still can't resolve the issue:

1. **Capture the full error message** from Portainer logs
2. **Verify your Twilio account** is active and has credits
3. **Test with a verified phone number** first
4. **Check the test script** passes: `./test_webhook.sh`
5. **Use DEBUG_WEBHOOK_URL** if you need real-time event monitoring

## Debug Webhook (Advanced)

For real-time monitoring, set up a debug webhook:

1. Create a webhook receiver at https://webhook.site
2. Copy the unique URL
3. Add to your `.env`:
   ```
   TUC_DEBUG_WEBHOOK_URL=https://webhook.site/your-unique-id
   ```
4. Restart container
5. All debug events will be POSTed to this URL in real-time

---

**Remember:** The API still returns generic error messages for security. Always check the logs for detailed error information!
