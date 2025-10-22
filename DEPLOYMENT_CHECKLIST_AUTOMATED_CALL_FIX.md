# Deployment Checklist - Automated Call Fix

## Pre-Deployment

- [ ] Review all code changes in the PR
- [ ] Verify no merge conflicts exist
- [ ] Read `AUTOMATED_CALL_FIX.md` documentation
- [ ] Backup current `.env` file
- [ ] Note current container versions/image IDs

## Deployment Steps

### 1. Pull Latest Changes

```bash
cd /path/to/twilio-responderAZ
git pull origin main  # or your target branch
```

### 2. Review Environment Variables

Ensure these are set correctly in your `.env` file:

**For each branch (TUC, POC, REX):**
- `{BRANCH}_TWILIO_ACCOUNT_SID` - Must be set
- `{BRANCH}_TWILIO_AUTH_TOKEN` - Must be set
- `{BRANCH}_TWILIO_AUTOMATED_NUMBER` - Must be set and start with `+`
- `{BRANCH}_RECIPIENT_PHONES` - Must start with `+`

Example check:
```bash
grep TWILIO_AUTOMATED_NUMBER .env
grep RECIPIENT_PHONES .env
```

### 3. Stop Current Containers

```bash
docker-compose -f docker-compose.multi.yml down
```

### 4. Rebuild Images

```bash
docker-compose -f docker-compose.multi.yml build --no-cache
```

### 5. Start Containers

```bash
docker-compose -f docker-compose.multi.yml up -d
```

### 6. Verify Startup

```bash
# Check all containers are running
docker ps | grep twilio_responder

# Check logs for any startup errors
docker logs twilio_responder_tuc --tail 50
docker logs twilio_responder_poc --tail 50
docker logs twilio_responder_rex --tail 50
```

## Post-Deployment Testing

### 1. Quick Health Check

```bash
# Test each branch
curl https://tuc.axiom-emergencies.com/api/status
curl https://poc.axiom-emergencies.com/api/status
curl https://rex.axiom-emergencies.com/api/status
```

Expected: All should return `{"status": "Ready", ...}`

### 2. Run Automated Tests

```bash
# Test Tucson branch
./test_webhook.sh https://tuc.axiom-emergencies.com

# Test Pocatello branch
./test_webhook.sh https://poc.axiom-emergencies.com

# Test Rexburg branch
./test_webhook.sh https://rex.axiom-emergencies.com
```

Expected results:
- ✅ Test 1 PASSED: Call initiated successfully
- ✅ Test 2 PASSED: Correctly rejected missing phone
- ✅ Test 3 PASSED: Correctly rejected empty request
- ✅ Test 4 PASSED: Status endpoint working

### 3. Manual Test with Real Number (Optional)

**⚠️ IMPORTANT: Only do this with permission and a test number!**

```bash
curl -X POST https://tuc.axiom-emergencies.com/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Test Customer",
    "user_stated_callback_number": "5551234567",
    "incident_address": "Test Address",
    "emergency_description_text": "Deployment test",
    "chosen_phone": "+1XXXXXXXXXX"
  }'
```

Verify:
- [ ] API returns 200 status
- [ ] Response includes "Emergency call initiated successfully"
- [ ] Test phone receives SMS
- [ ] Test phone receives call
- [ ] System returns to "Ready" state after call

### 4. Monitor Logs

Leave logs running for a few minutes to catch any delayed errors:

```bash
docker logs -f twilio_responder_tuc
```

Watch for:
- Any ERROR or CRITICAL log lines
- Successful emergency_call_initiated events
- No unexpected exceptions

## Validation Checklist

- [ ] All containers running and healthy
- [ ] Status endpoints return 200
- [ ] Automated tests all pass
- [ ] No errors in container logs
- [ ] Emergency triggers work correctly
- [ ] Invalid requests are rejected with 400
- [ ] System returns to "Ready" after emergency
- [ ] Admin dashboard can access all branches

## Rollback Procedure

If issues are found:

```bash
# 1. Stop current containers
docker-compose -f docker-compose.multi.yml down

# 2. Checkout previous version
git checkout <previous-commit-hash>

# 3. Rebuild
docker-compose -f docker-compose.multi.yml build --no-cache

# 4. Start
docker-compose -f docker-compose.multi.yml up -d

# 5. Verify
docker ps
docker logs twilio_responder_tuc --tail 50
```

## Common Issues

### Issue: Containers won't start

**Check:**
```bash
docker logs twilio_responder_tuc
```

**Common causes:**
- Missing environment variables
- Port conflicts
- Database migration issues

### Issue: Test 1 fails (call initiation)

**Check:**
```bash
docker logs twilio_responder_tuc | grep -A 5 "emergency_call"
```

**Common causes:**
- Twilio credentials not set
- Phone number format invalid (missing +)
- TWILIO_AUTOMATED_NUMBER not configured
- Twilio account balance/status

### Issue: Generic "Configuration error" in logs

The new version logs detailed errors via `send_debug()`. Check:

1. Container logs: `docker logs twilio_responder_tuc`
2. DEBUG_WEBHOOK_URL if configured
3. Look for events: `emergency_call_validation_error`, `emergency_call_config_error`

## Success Criteria

✅ Deployment is successful when:

1. All containers are running
2. All automated tests pass
3. No errors in logs for 5 minutes
4. Can trigger test emergency successfully
5. System properly validates and rejects invalid requests
6. Admin dashboard shows all branches online

## Support

If you encounter issues:

1. Check `AUTOMATED_CALL_FIX.md` for detailed troubleshooting
2. Review `TROUBLESHOOTING.md` for common problems
3. Check container logs for specific error messages
4. Verify environment variables are correctly set

## Notes

- The fix improves error handling and validation
- Error messages are now logged internally but not exposed to API callers (security)
- System will reject invalid requests instead of failing silently
- Emergency state is properly cleaned up on failures
- All changes are backward compatible with existing functionality
