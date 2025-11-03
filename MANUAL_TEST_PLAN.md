# Manual Test Plan for Call Flow Fix

## Issue Fixed
Customer gets application error when calling while tech is on phone, or when calling back after tech gets off the phone.

## Root Cause
Race condition in `handle_incoming_twilio_call` where synchronous connection attempts were made before returning TwiML response to Twilio. This caused:
1. API call delays that exceeded Twilio's timeout
2. Conflicts when technician was still on the initial notification call
3. Application errors that interrupted the call flow

## Changes Made
Removed immediate connection attempts from `handle_incoming_twilio_call` function:
- Line 1022-1024: Removed `transfer_customer_to_target` call when status is 'technician_informed'
- Line 1035-1036: Removed `connect_technician_to_customer` call when status is 'technician_informed'

Connection now only happens through the `technician_call_ended` callback, which is the proper asynchronous context.

## Test Scenarios

### Scenario 1: Customer calls while tech is on initial notification call
**Before Fix:**
- Customer calls in
- Code tries to connect while tech is busy
- API call fails or times out
- Customer gets "application error"

**After Fix:**
- Customer calls in
- Customer is queued with hold music
- TwiML returned immediately (no blocking)
- When tech hangs up, `technician_call_ended` callback connects them
- Customer hears hold music until connected

**Test Steps:**
1. Trigger emergency webhook
2. While tech's phone is ringing, have customer call the emergency number
3. Verify: Customer hears "Please hold..." and hold music (no error)
4. Tech answers and hangs up from notification call
5. Verify: Customer is connected to tech's callback

### Scenario 2: Customer calls right after tech hangs up from notification
**Before Fix:**
- Customer calls in
- Status is 'technician_informed'
- Code tries to make synchronous API call to connect
- Call delays TwiML response
- Customer gets "application error" or interrupted message

**After Fix:**
- Customer calls in
- Customer is queued with hold music
- TwiML returned immediately
- `technician_call_ended` callback already ran or will run shortly
- Connection happens through callback, not synchronously
- Customer hears hold music briefly then connects

**Test Steps:**
1. Trigger emergency webhook
2. Wait for tech's notification call to complete
3. Immediately after tech hangs up, have customer call
4. Verify: Customer hears hold music (no error message)
5. Verify: Customer connects to tech within a few seconds

### Scenario 3: Normal flow - customer calls after tech is informed
**Before & After:**
This scenario should work the same, as the callback mechanism handles the connection.

**Test Steps:**
1. Trigger emergency webhook
2. Wait for tech's notification call to complete (status becomes 'technician_informed')
3. Wait 5-10 seconds
4. Customer calls emergency number
5. Verify: Customer is queued and then connected to tech

### Scenario 4: Transfer mode enabled
**Test Steps:**
Same as above but with `enable_transfer_call` set to 'true'
- Verify customer is queued
- Verify transfer happens through callback, not synchronously
- Verify no application errors

## Expected Behavior (All Scenarios)
1. ✅ Customer never hears "application error"
2. ✅ Customer is immediately queued with hold music
3. ✅ TwiML response is returned quickly (< 1 second)
4. ✅ Connection happens asynchronously via callback
5. ✅ No race conditions or call conflicts

## Verification Commands
```bash
# Check logs for errors
docker logs twilio_responder_tuc | grep -i error

# Check for successful queue events
docker logs twilio_responder_tuc | grep customer_queued

# Verify no immediate connection attempts
docker logs twilio_responder_tuc | grep -A5 "incoming_call" | grep -i "connect"
# Should NOT see connection attempts immediately after incoming_call
```

## Docker Testing
```bash
# Build and run
docker-compose -f docker-compose.multi.yml up -d

# Test emergency trigger
./test_webhook.sh https://tuc.axiom-emergencies.com +15205551234

# Monitor logs
docker logs -f twilio_responder_tuc
```

## Success Criteria
- [ ] Customer can call during tech's notification without errors
- [ ] Customer can call immediately after tech hangs up without errors
- [ ] TwiML responses are returned immediately (no blocking)
- [ ] Connections happen properly through callback mechanism
- [ ] No race conditions in logs
- [ ] All existing functionality remains intact
