# Phone Transfer Fix - Quick Test Guide

## What Changed
Fixed phone transfers to use Twilio call redirect instead of unreliable queue dequeue.

## Quick Test (5 minutes)

### Prerequisites
- Admin dashboard access
- Test phone numbers
- Transfer mode enabled

### Steps

1. **Configure transfer mode** (via admin dashboard):
   ```
   enable_transfer_call = true
   TRANSFER_TARGET_PHONE_NUMBER = +15551234567  (your test number)
   ```

2. **Trigger emergency**:
   ```bash
   curl -X POST https://your-branch.com/webhook \
     -H "Content-Type: application/json" \
     -d '{
       "chosen_phone": "+15551234567",
       "customer_name": "Test Customer",
       "incident_address": "123 Test St"
     }'
   ```

3. **Call as customer**:
   - Call the emergency phone number
   - You should hear: "Please hold while we notify the technician"
   - You'll be placed on hold with music

4. **Wait for notification**:
   - Notification call completes (~30 seconds)
   - Your transfer target phone should ring

5. **Answer transfer call**:
   - When you answer, you should be connected to the waiting customer
   - Call should work normally

### Expected Behavior

**Before the fix**:
- ❌ Transfer might fail silently
- ❌ Customer stuck in queue
- ❌ Transfer target never receives call
- ❌ Or: both calls happen simultaneously (race condition)

**After the fix**:
- ✅ Customer waits in queue with music
- ✅ Notification completes first
- ✅ Customer call redirected to transfer target
- ✅ Transfer target receives call
- ✅ Customer and target connected

### Debug Events to Monitor

Look for these in your debug webhook:

```
customer_queued_for_transfer
  ↓
technician_call_ended
  ↓
initiating_transfer_after_notification
  ↓
transfer_call_redirected  ← Key success event
  ↓
transfer_complete
```

### If Something Goes Wrong

Check logs for these events:
- `transfer_redirect_twilio_error` - Redirect failed, check Twilio error
- `falling_back_to_dequeue_method` - Using fallback (still works, just older method)
- `transfer_error` - Configuration or state issue

### Rollback

If critical issues:
```bash
git revert HEAD~3..HEAD
git push
docker-compose restart
```

---

**Expected Result**: Transfers should work reliably every time.  
**If Still Failing**: Check debug logs and file issue with full context.
