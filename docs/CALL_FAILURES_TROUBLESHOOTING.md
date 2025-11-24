# Call Failures Troubleshooting Guide

This document provides troubleshooting guidance for common call failure scenarios in the Twilio emergency responder system. Based on recent fixes and known issues, this guide will help you diagnose and resolve problems.

## Table of Contents

- [Overview](#overview)
- [Issue 1: Warm Transfer / Queue Updates](#issue-1-warm-transfer--queue-updates)
- [Issue 2: Silent Failures in Automated Calls](#issue-2-silent-failures-in-automated-calls)
- [Troubleshooting Steps](#troubleshooting-steps)
- [Related Documentation](#related-documentation)

---

## Overview

There are two major documented issues that could cause call failures in this system:

1. **Warm Transfer / Queue Updates** - Issues with transferring calls or moving them out of a queue
2. **Silent Failures in Automated Calls** - Calls not initiating when triggered via the webhook

Both issues have been addressed in recent updates. This guide explains what was fixed and how to diagnose remaining issues.

---

## Issue 1: Warm Transfer / Queue Updates

### Most Likely Cause

If your issue involves transferring calls or moving them out of a queue, the system previously used a method that Twilio does not support.

### The Problem

The system tried to use `call.update(twiml=...)` on a call that was sitting in a queue. **Twilio forbids modifying TwiML for queued calls.**

### The Symptom

- Calls would disconnect or fail to transfer
- Customer might hear "Application Error"
- Often without a clear error on the frontend

### The Solution

The logic was changed to use a **"Queue Dequeue" method** (dialing the queue directly) instead of updating the call. This is the proper way to connect queued callers in Twilio.

**How it works now:**
```
Customer → Queue → Wait for notification to end
                    ↓
                   Make new call to tech
                    ↓
                   New call TwiML: <Dial><Queue>
                    ↓
                   Customer dequeued and connected
                    ✅ Works reliably
```

### Key Point

> You **cannot** modify a call's TwiML while it's in a queue - you must dequeue it using `<Dial><Queue>`.

### Reference Documentation

- [HOW_IT_WORKS.md](../HOW_IT_WORKS.md) - Complete explanation of the warm transfer flow
- [FIX_SUMMARY.md](../FIX_SUMMARY.md) - Summary of the queue dequeue fix

---

## Issue 2: Silent Failures in Automated Calls

### The Problem

If your issue is that calls simply aren't initiating when triggered via the webhook, the problem might be silent failures.

Previous versions of `make_emergency_call()` and the `/webhook` endpoint lacked comprehensive validation. Calls could fail silently if configuration was missing, leaving the system in an inconsistent state.

### The Symptom

- Webhook returns success but no call is made
- System appears to accept the request but nothing happens
- No clear error messages in the API response (by design for security)

### The Solution

Recent updates added **strict validation** for:

- `customer_name`
- Phone numbers (must start with `+` and include country code)
- Emergency descriptions
- Twilio configuration (credentials, automated number)

If these are missing or invalid, the API now returns a specific error instead of failing silently. Detailed error information is logged for debugging.

### Reference Documentation

- [docs/archive/FIX_SUMMARY.md](archive/FIX_SUMMARY.md) - Detailed summary of the silent failure fixes

---

## Troubleshooting Steps

To diagnose the exact cause of call failures, follow these steps:

### Step 1: Check Portainer/System Logs

Look for `[ERROR]` messages in your container logs. The recent fixes added detailed logging to reveal why a call failed.

**Using Portainer:**
1. Open Portainer
2. Go to **Containers**
3. Click on the relevant container (e.g., `twilio_responder_tuc`)
4. Click the **Logs** tab
5. Look for lines starting with `[ERROR]`

**Using Docker CLI:**
```bash
# View recent logs
docker logs twilio_responder_tuc --tail 100

# Follow logs in real-time
docker logs -f twilio_responder_tuc

# Search for errors
docker logs twilio_responder_tuc 2>&1 | grep "\[ERROR\]"
```

**Common error messages:**
- `emergency_call_validation_error` - Invalid phone number format
- `emergency_call_config_error` - Missing Twilio configuration
- `call_initiation_error` - Twilio API call failed
- `webhook_call_failed` - Overall call initiation failed

### Step 2: Run the Test Script

The repo includes a deployment test script. Run the following command to see if it triggers a call or returns an error:

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

**Replace:**
- `tuc.axiom-emergencies.com` with your branch URL
- `+18017104034` with the technician's phone number

**Expected responses:**
- `200 OK` with `{"status": "success", ...}` - Call initiated successfully
- `400 Bad Request` - Missing required fields (check the error message)
- `500 Internal Server Error` - Configuration or Twilio API issue (check logs)
- `503 Service Unavailable` - System is busy with another emergency

You can also use the included test script:
```bash
./test_webhook.sh https://tuc.axiom-emergencies.com +15551234567
```

### Step 3: Verify Credentials

Ensure branch-specific Twilio credentials are configured correctly in your settings:

1. **Check via Admin Dashboard:**
   - Log in to the admin dashboard at axiom-emergencies.com
   - Navigate to Settings for your branch
   - Verify the following are configured:
     - `TWILIO_ACCOUNT_SID`
     - `TWILIO_AUTH_TOKEN`
     - `TWILIO_AUTOMATED_NUMBER`

2. **Check via Docker:**
   ```bash
   docker exec twilio_responder_tuc env | grep TWILIO
   ```

3. **Verify phone number format:**
   - ✅ Correct: `+15551234567`
   - ❌ Incorrect: `5551234567`, `1-555-123-4567`, `(555) 123-4567`

### Step 4: Check Twilio Account Status

1. Log in to [Twilio Console](https://console.twilio.com)
2. Verify your account is active
3. Check that you have available credits/balance
4. Verify your phone numbers are active
5. For trial accounts, ensure destination numbers are verified

---

## Related Documentation

| Document | Description |
|----------|-------------|
| [HOW_IT_WORKS.md](../HOW_IT_WORKS.md) | Complete explanation of the warm transfer system |
| [FIX_SUMMARY.md](../FIX_SUMMARY.md) | Summary of the queue dequeue fix |
| [docs/archive/FIX_SUMMARY.md](archive/FIX_SUMMARY.md) | Detailed summary of the silent failure fixes |
| [docs/deployment/DEPLOYMENT_GUIDE.md](deployment/DEPLOYMENT_GUIDE.md) | Deployment and testing guide |
| [docs/features/DEBUGGING_CALLS.md](features/DEBUGGING_CALLS.md) | Quick guide for debugging call issues |
| [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md) | General troubleshooting guide |

---

## Quick Reference: Error Messages

| Error Type | Likely Cause | Solution |
|------------|--------------|----------|
| "Missing chosen_phone" | Webhook request missing required field | Include `chosen_phone` in the request body |
| "Invalid technician number format" | Phone number doesn't start with `+` | Use E.164 format: `+15551234567` |
| "TWILIO_AUTOMATED_NUMBER not configured" | Missing configuration | Add the automated number in admin dashboard |
| "Twilio credentials not configured" | Missing ACCOUNT_SID or AUTH_TOKEN | Configure credentials in admin dashboard |
| "Unable to create record: Authenticate" | Invalid Twilio credentials | Verify ACCOUNT_SID and AUTH_TOKEN |
| "The number is unverified" | Trial account limitation | Verify the number or upgrade Twilio account |
| "Application Error" (customer hears) | TwiML error, often queue-related | Check if using latest code with queue dequeue fix |

---

## Need More Help?

If these steps don't resolve your issue:

1. Check all related documentation listed above
2. Review the complete [TROUBLESHOOTING.md](TROUBLESHOOTING.md) guide
3. Examine the full error message in container logs
4. Verify all environment variables and settings are correct
5. Test with the included test script: `./test_webhook.sh`

---

**Last Updated:** November 2025  
**Related Issues:** Warm transfer fixes, Silent failure fixes
