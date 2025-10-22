# Automated Call Fix - Testing Guide

## Problem Fixed

The automated emergency call system was failing silently when calls could not be initiated. The webhook endpoint would return "success" even when:
- Twilio credentials were missing or invalid
- Phone numbers were incorrectly formatted
- Required configuration was missing
- Twilio API calls failed

This left the system in an inconsistent state and made debugging difficult.

## Changes Made

### 1. Enhanced Validation

The system now validates:
- Technician phone number exists and has country code (+)
- Twilio credentials (ACCOUNT_SID, AUTH_TOKEN) are configured
- Automated phone number exists and has country code (+)
- Request body is not empty
- Required field `chosen_phone` is present

### 2. Improved Error Handling

- SMS sending failures no longer block call attempts
- Call initiation failures are caught and reported
- Specific error messages identify the exact problem
- Emergency state is cleared on failure (prevents stuck state)
- Detailed debug events are logged for troubleshooting
- **Security**: Error details are logged internally but generic messages are returned to API callers

### 3. Better API Responses

- Success responses include confirmation message
- Error responses use generic messages for security (details in logs)
- HTTP status codes properly reflect the outcome:
  - 200: Success
  - 400: Bad request (validation error)
  - 500: Server error (call failed)
  - 503: System busy (emergency already active)

## Testing the Fix

### Automated Testing

Use the provided test script:

```bash
# Test local instance
./test_webhook.sh http://localhost:5000

# Test deployed instance
./test_webhook.sh https://tuc.axiom-emergencies.com +15551234567
```

The script tests:
1. Valid emergency call request
2. Missing required field (chosen_phone)
3. Empty request body
4. System status endpoint

### Manual Testing

#### 1. Test with valid data:

```bash
curl -X POST https://tuc.axiom-emergencies.com/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Test Customer",
    "user_stated_callback_number": "5551234567",
    "incident_address": "123 Main St",
    "emergency_description_text": "Test emergency",
    "chosen_phone": "+15551234567"
  }'
```

Expected response:
```json
{
  "status": "success",
  "message": "Emergency call initiated successfully"
}
```

#### 2. Test with invalid phone format:

```bash
curl -X POST https://tuc.axiom-emergencies.com/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "chosen_phone": "5551234567"
  }'
```

Expected response:
```json
{
  "status": "error",
  "message": "Failed to initiate emergency call. Please check configuration and try again."
}
```

**Note**: For security reasons, detailed error messages are only available in server logs, not in API responses. Use `docker logs` or `DEBUG_WEBHOOK_URL` to see specific errors.

#### 3. Test with missing phone:

```bash
curl -X POST https://tuc.axiom-emergencies.com/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "customer_name": "Test Customer"
  }'
```

Expected response:
```json
{
  "status": "error",
  "message": "Missing required field: chosen_phone"
}
```

## Debugging

### Check Logs

View detailed error messages in container logs:

```bash
# For Tucson branch
docker logs twilio_responder_tuc --tail 100

# For Pocatello branch
docker logs twilio_responder_poc --tail 100

# For Rexburg branch
docker logs twilio_responder_rex --tail 100
```

### Debug Events

If `DEBUG_WEBHOOK_URL` is configured, the following events are now logged:

- `emergency_call_validation_error` - Validation failures
- `emergency_call_config_error` - Configuration issues
- `sms_send_error` - SMS delivery failures
- `call_initiation_error` - Call creation failures
- `webhook_validation_error` - Request validation errors
- `webhook_call_failed` - Overall call failure

### Common Issues and Solutions

#### Issue: "Twilio credentials are not configured"

**Solution:**
1. Check environment variables in docker-compose:
   ```bash
   docker exec twilio_responder_tuc env | grep TWILIO
   ```
2. Verify `.env` file has correct values:
   - `TUC_TWILIO_ACCOUNT_SID`
   - `TUC_TWILIO_AUTH_TOKEN`
3. Restart container after updating:
   ```bash
   docker-compose -f docker-compose.multi.yml restart twilio-app-tuc
   ```

#### Issue: "Invalid technician number format (missing country code)"

**Solution:**
- Ensure phone numbers start with `+` and country code
- Example: `+15551234567` (not `5551234567`)
- Update in webhook request or admin dashboard settings

#### Issue: "TWILIO_AUTOMATED_NUMBER is not configured"

**Solution:**
1. Add to `.env` file:
   ```
   TUC_TWILIO_AUTOMATED_NUMBER=+15551234567
   ```
2. Or configure in admin dashboard settings
3. Restart container

#### Issue: Call fails but SMS works

**Solution:**
- Check Twilio account balance
- Verify phone number has voice capabilities
- Check Twilio account status (not suspended)
- Review Twilio error logs in dashboard

## Verifying the Fix in Production

After deployment, verify:

1. **Check system status:**
   ```bash
   curl https://tuc.axiom-emergencies.com/api/status
   ```

2. **Test emergency trigger:**
   ```bash
   ./test_webhook.sh https://tuc.axiom-emergencies.com
   ```

3. **Monitor logs:**
   ```bash
   docker logs -f twilio_responder_tuc
   ```

4. **Test with real phone number** (with permission):
   - Trigger emergency with valid technician number
   - Verify call and SMS are received
   - Check response is 200 with success message

## Rollback Plan

If issues occur after deployment:

```bash
# Rollback to previous version
docker-compose -f docker-compose.multi.yml down
git checkout <previous-commit>
docker-compose -f docker-compose.multi.yml up -d --build
```

## Support

For issues or questions:
1. Check this guide first
2. Review container logs
3. Test with the test script
4. Check Twilio dashboard for API errors
5. Verify environment variables are correct
