# Transfer Call Fix - Deployment Checklist

Quick reference for deploying the transfer call fix to your environment.

## Pre-Deployment

- [ ] Review the implementation summary: `TRANSFER_CALL_FIX_SUMMARY.md`
- [ ] Review the feature documentation: `TRANSFER_CALL_FEATURE.md`
- [ ] Backup current database (if any)
- [ ] Note current git commit hash for rollback if needed

## Deployment Steps

### 1. Pull Latest Code

```bash
cd /path/to/twilio-responderAZ
git fetch origin
git checkout copilot/fix-transfer-calls-issue
git pull origin copilot/fix-transfer-calls-issue
```

### 2. Rebuild Docker Containers

```bash
docker-compose -f docker-compose.multi.yml build --no-cache
```

### 3. Restart Services

```bash
docker-compose -f docker-compose.multi.yml down
docker-compose -f docker-compose.multi.yml up -d
```

### 4. Verify Services Started

```bash
docker ps | grep twilio_responder
# Should see all containers running
```

### 5. Check Logs for Errors

```bash
# Check each branch
docker logs twilio_responder_tuc --tail 50
docker logs twilio_responder_poc --tail 50
docker logs twilio_responder_rex --tail 50
docker logs twilio_responder_admin --tail 50
```

Look for:
- ✅ "Starting Flask App on..." messages
- ❌ Any CRITICAL ERROR messages
- ❌ Any Python exceptions

## Configuration (If Using Transfer Feature)

### Option 1: Via Admin Dashboard

1. [ ] Log in to admin dashboard: `https://axiom-emergencies.com`
2. [ ] Navigate to the branch you want to configure
3. [ ] Click "Settings" or "Configure"
4. [ ] Under **Advanced Settings**:
   - [ ] Set "Transfer Target Phone Number" (e.g., `+15205551234`)
   - [ ] Optionally set "Transfer Number" for caller ID (e.g., `+15205559876`)
5. [ ] Under **Basic Settings**:
   - [ ] Toggle "Enable Call Transfer" to `true`
6. [ ] Click "Save Settings"
7. [ ] Wait 5 minutes for settings to reload (or trigger manual reload)

### Option 2: Via Environment Variables

1. [ ] Edit your `.env` file or docker-compose configuration:

```bash
# For Tucson branch
TUC_TRANSFER_TARGET_PHONE_NUMBER=+15205551234
TUC_TWILIO_TRANSFER_NUMBER=+15205559876
```

2. [ ] Restart the affected container:

```bash
docker-compose -f docker-compose.multi.yml restart twilio-app-tuc
```

3. [ ] Enable the feature via admin dashboard (toggle "Enable Call Transfer")

## Testing

### Test 1: Verify Services are Running

```bash
# Test status endpoint for each branch
curl https://tuc.axiom-emergencies.com/api/status
curl https://poc.axiom-emergencies.com/api/status
curl https://rex.axiom-emergencies.com/api/status

# Expected: {"status":"Ready","message":"System is online and waiting for calls."}
```

### Test 2: Check Transfer Settings (If Enabled)

```bash
# Check logs for transfer configuration
docker logs twilio_responder_tuc | grep -i transfer
```

### Test 3: Trigger Test Emergency (Optional)

**Note**: This will send actual SMS/calls to configured numbers.

```bash
# Use test webhook script
./test_webhook.sh https://tuc.axiom-emergencies.com +15205551234
```

### Test 4: Test Transfer Call (If Enabled)

**Note**: Only do this if you've configured and enabled transfer mode.

1. [ ] Trigger a test emergency
2. [ ] Call the emergency number from your phone
3. [ ] Verify you hear: "Please hold while we transfer your call."
4. [ ] Verify call connects to the transfer target number
5. [ ] After call ends, check logs:

```bash
docker logs twilio_responder_tuc | grep -E "(call_transfer_initiated|transfer_complete)"
```

Expected log events:
```
call_transfer_initiated - emergency_id, transfer_target, transfer_from
transfer_complete - dial_call_status, dial_call_duration
```

### Test 5: Test Original Behavior (If Transfer Disabled)

1. [ ] Ensure transfer mode is disabled
2. [ ] Trigger a test emergency
3. [ ] Call the emergency number
4. [ ] Verify you hear: "Please hold while we connect you to the emergency technician."
5. [ ] Verify queue behavior works (hold music, technician connection)

## Verification Checklist

- [ ] All containers are running (`docker ps`)
- [ ] No errors in logs
- [ ] Status endpoints return 200 OK
- [ ] Admin dashboard accessible
- [ ] Settings can be viewed/edited
- [ ] Transfer feature works (if enabled)
- [ ] Original queue behavior works (if transfer disabled)

## Monitoring (First 24 Hours)

### Check These Regularly

```bash
# View live logs
docker-compose -f docker-compose.multi.yml logs -f --tail 50

# Check for errors
docker logs twilio_responder_tuc | grep -i error
docker logs twilio_responder_poc | grep -i error
docker logs twilio_responder_rex | grep -i error

# Check transfer activity (if enabled)
docker logs twilio_responder_tuc | grep -i transfer
```

### Success Indicators

- ✅ No error messages in logs
- ✅ Status endpoints responding
- ✅ Transfer calls completing successfully (if enabled)
- ✅ Original behavior working (if transfer disabled)
- ✅ Email notifications sent
- ✅ Emergency state cleaned up after calls

### Failure Indicators

- ❌ "transfer_config_error" in logs
- ❌ "call_handling_error" in logs
- ❌ Python exceptions/stack traces
- ❌ Containers restarting
- ❌ Status endpoints timing out

## Rollback (If Needed)

If you encounter critical issues:

```bash
# Note current commit for future reference
git log --oneline -1

# Rollback to previous version
git checkout 811c4e9  # Or your previous commit hash

# Rebuild and restart
docker-compose -f docker-compose.multi.yml build --no-cache
docker-compose -f docker-compose.multi.yml down
docker-compose -f docker-compose.multi.yml up -d

# Verify rollback successful
docker ps
docker logs twilio_responder_tuc --tail 50
```

## Common Issues and Solutions

### Issue: "transfer_config_error" in logs

**Cause**: Transfer target number not configured or invalid format

**Solution**:
1. Check `TRANSFER_TARGET_PHONE_NUMBER` is set
2. Verify it starts with `+` and includes country code
3. Example correct format: `+15205551234`

### Issue: Transfer not working

**Cause**: Feature not enabled

**Solution**:
1. Log into admin dashboard
2. Check "Enable Call Transfer" is toggled to `true`
3. Wait 5 minutes or trigger settings reload:
```bash
curl -X POST https://tuc.axiom-emergencies.com/api/reload_settings
```

### Issue: Original queue behavior not working

**Cause**: Broken by changes (shouldn't happen - backwards compatible)

**Solution**:
1. Check logs for specific errors
2. Disable transfer mode: Set "Enable Call Transfer" to `false`
3. If still broken, rollback (see above)

### Issue: App won't start (missing env vars)

**Cause**: New validation might be too strict (shouldn't happen - we made transfer optional)

**Solution**:
1. Check all required vars are set:
   - `TWILIO_ACCOUNT_SID`
   - `TWILIO_AUTH_TOKEN`
   - `TWILIO_PHONE_NUMBER`
   - `TWILIO_AUTOMATED_NUMBER`
   - `PUBLIC_URL`
   - `FLASK_PORT`
2. Transfer numbers are optional (don't need to be set)

## Support

### Get Help

1. Check logs:
```bash
docker logs twilio_responder_<branch> --tail 100
```

2. Review documentation:
   - `TRANSFER_CALL_FEATURE.md` - Feature guide
   - `TRANSFER_CALL_FIX_SUMMARY.md` - Implementation details
   - `TROUBLESHOOTING.md` - General troubleshooting

3. Check debug webhook (if configured):
   - Look for `call_transfer_initiated` events
   - Look for `transfer_config_error` events
   - Check `transfer_complete` callbacks

4. Test Twilio Configuration:
   - Log into Twilio Console
   - Check phone number settings
   - Verify webhook URLs are correct
   - Check for any Twilio errors

## Post-Deployment

After 24-48 hours of stable operation:

- [ ] Review logs for any patterns or issues
- [ ] Verify all emergency calls handled correctly
- [ ] Document any lessons learned
- [ ] Consider this deployment successful
- [ ] Update runbooks if needed

---

## Summary

This fix implements the transfer call feature that was configured but never actually coded. The changes are:

- ✅ Minimal and surgical (~85 lines of code changed)
- ✅ Backward compatible (existing behavior preserved)
- ✅ Well tested (unit tests, security scans passed)
- ✅ Fully documented (3 comprehensive docs)
- ✅ Rollback ready (simple git checkout)

**Expected Outcome**: Transfer calls will work when enabled, original queue behavior works when disabled.

---

**Date**: 2025-10-23  
**PR**: copilot/fix-transfer-calls-issue  
**Issue**: "after repeated fixes the transfer calls still dont work"  
**Root Cause**: Feature was not implemented at all  
**Status**: ✅ FIXED
