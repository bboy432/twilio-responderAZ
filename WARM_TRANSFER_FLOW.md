# Warm Transfer Flow - How the Emergency Call System Works

## Overview

The system implements a **warm transfer** where the technician is notified first, then the customer is automatically connected after the notification completes. This ensures the technician is aware of the emergency before speaking with the customer.

---

## Complete Call Flow (Step-by-Step)

### Step 1: Emergency Webhook Triggered
**When:** An emergency is reported through the webhook endpoint
**What happens:**
- System receives emergency data via POST to `/webhook`
- Creates emergency record with unique ID
- Status set to `informing_technician`

```
POST /webhook
↓
Emergency Created (ID: abc-123)
Status: "informing_technician"
```

### Step 2: Immediate Notification Call to Technician
**When:** Immediately after webhook (within 1-2 seconds)
**What happens:**
- System makes automated call to technician's phone
- Plays emergency details message
- Technician listens to the full notification
- Call automatically ends after message completes (~30-60 seconds)

```
Webhook Complete
↓
IMMEDIATE: Automated Call → Technician Phone
↓
Technician Hears: "Emergency Alert. Customer: John Doe. Address: 123 Main St..."
↓
Message Plays (~30-60 seconds)
↓
Notification Call Ends
↓
Callback: /technician_call_ended
```

**Key Point:** This is a one-way notification. The technician just listens - they don't speak yet.

### Step 3: Customer Calls In (After a Few Seconds)
**When:** A few seconds after the webhook (manually or automatically)
**What happens:**
- Customer dials the emergency phone number
- System checks if emergency is active
- Customer hears: "Please hold while we notify the technician about your emergency"
- Customer is placed in queue with hold music
- Status changes to `customer_waiting`

```
A Few Seconds Later...
↓
Customer → Dials Emergency Number
↓
System: "Please hold while we notify the technician..."
↓
Customer → Queue (with hold music 🎵)
Status: "customer_waiting"
```

**Key Point:** The customer is on hold, waiting for the notification call to finish.

### Step 4: Notification Completes, Transfer Initiated
**When:** Notification call to technician ends
**What happens:**
- System receives callback at `/technician_call_ended`
- Detects customer is waiting in queue
- Initiates transfer using call redirect or dequeue

```
Notification Call Ends
↓
Callback: /technician_call_ended
↓
System Checks: Is customer waiting? YES
↓
Transfer Function Called
```

### Step 5: Customer Connected to Technician (Warm Transfer)
**When:** Transfer is initiated
**What happens:**

**Transfer Mode Enabled (`enable_transfer_call=true`):**
```
System → Modifies Customer Call (using call SID)
↓
New TwiML: <Dial><Number>+15205551234</Number>
↓
Customer Removed from Queue
↓
Transfer Target Phone Rings
↓
Transfer Target Answers
↓
Customer + Transfer Target Connected 🎉
```

**Queue Mode (Default, `enable_transfer_call=false`):**
```
System → Makes New Call to Technician
↓
TwiML: <Dial><Queue>emergency-abc-123</Queue>
↓
Dequeues Customer from Queue
↓
Technician + Customer Connected 🎉
```

### Step 6: Call Complete
**When:** Either party hangs up
**What happens:**
- System receives callback at `/transfer_complete` (transfer mode) or `/conference_status` (queue mode)
- Records call duration and status
- Sends final email notification
- Clears emergency state
- System ready for next emergency

```
Call Ends
↓
Callback Received
↓
Emergency Concluded
↓
System Ready ✅
```

---

## Timeline Diagram

```
Time →  0s        2s         5s              35s            37s           60s
        |         |          |               |              |             |
Webhook ━━━━━━━━━┓          |               |              |             |
                 ┃          |               |              |             |
Notification     ┗━━━━━━━━━━━━━━━━━━━━━━━━━━┓              |             |
Call to Tech     (Plays message ~30-60s)    ┃              |             |
                                             ┃              |             |
Customer                   ┏━━━━━━━━━━━━━━━━┛              |             |
Calls In                   ┃ (On Hold)                     |             |
                           ┃                                |             |
Transfer                                                    ┗━━━━━━━━━━━━━┓
Initiated                                                                 ┃
                                                                          ┃
Connected                                                                 ┗━━━━━━━→
Call                                                      (Conversation)
```

**Key Timing:**
- **0s:** Webhook received, emergency created
- **~2s:** Notification call starts to technician
- **~5s:** Customer calls in, placed on hold with music
- **~35s:** Notification call ends (callback received)
- **~37s:** Transfer initiated to connect customer to tech
- **37s+:** Customer and technician talking (actual emergency handled)

---

## Why This Is Called a "Warm Transfer"

A **warm transfer** means:
1. ✅ **Technician is informed first** - They know about the emergency before customer connects
2. ✅ **Customer doesn't speak to system** - Customer just waits on hold
3. ✅ **Seamless connection** - Customer doesn't hear transfer happening
4. ✅ **No manual intervention** - Everything is automated after webhook triggers

**Contrast with Cold Transfer:**
- Cold transfer: Customer transferred to tech without tech knowing about it first
- Warm transfer: Tech receives notification first, then customer is connected

---

## Two Operating Modes

### Mode 1: Transfer Mode (Recommended)
**Setting:** `enable_transfer_call = true`

**Use Case:** Transfer customer to a general phone line (e.g., main office number)

**How It Works:**
- Uses Twilio's call modification API (`client.calls().update()`)
- Directly dials the `TRANSFER_TARGET_PHONE_NUMBER`
- More reliable than queue-based dequeue

**Configuration:**
```
enable_transfer_call = true
TRANSFER_TARGET_PHONE_NUMBER = +15205551234
TWILIO_TRANSFER_NUMBER = +15205559999 (optional, for caller ID)
```

### Mode 2: Queue Mode (Original Behavior)
**Setting:** `enable_transfer_call = false` (default)

**Use Case:** Connect customer to specific technician assigned to emergency

**How It Works:**
- Uses Twilio queue to hold customer
- Makes new call to technician to dequeue customer
- Technician and customer connected in queue-based conference

**Configuration:**
```
enable_transfer_call = false
(No additional settings needed)
```

---

## Common Questions

### Q: What if customer calls before notification call starts?
**A:** Customer is placed on hold immediately. They will wait for notification to complete.

### Q: What if customer hangs up before transfer?
**A:** System detects customer is no longer in queue. Transfer is not attempted. Emergency remains logged.

### Q: What if notification call fails?
**A:** Emergency is cleared, webhook returns error. Customer calling in will hear "no active emergency."

### Q: Can I skip the notification call?
**A:** No. The notification call is required to inform the technician. This is the "warm" part of warm transfer.

### Q: How long is customer on hold?
**A:** Typically 30-60 seconds - the length of the notification message to the technician.

### Q: What does customer hear while on hold?
**A:** Classical music (BusyStrings.mp3 from Twilio)

---

## Debug Events to Monitor

Watch for these debug events in logs:

**Successful Warm Transfer:**
```
1. webhook_received - Emergency webhook triggered
2. emergency_call_initiated - Notification call to tech started
3. incoming_call - Customer calls in
4. customer_queued_for_transfer - Customer on hold
5. technician_call_ended - Notification complete
6. initiating_transfer_after_notification - Transfer starting
7. transfer_call_redirected - Customer call modified
8. transfer_complete - Call connected successfully
9. emergency_concluded - All done
```

**Problem Indicators:**
- `transfer_redirect_error` - Call modification failed
- `falling_back_to_dequeue_method` - Using backup method
- `transfer_error` - Transfer couldn't complete
- `no_active_emergency` - Customer called but no emergency active

---

## Testing the Warm Transfer

### Manual Test Procedure

1. **Trigger webhook:**
   ```bash
   curl -X POST https://your-branch.com/webhook \
     -H "Content-Type: application/json" \
     -d '{
       "chosen_phone": "+15205551234",
       "customer_name": "Test Customer",
       "user_stated_callback_number": "+15205555678",
       "incident_address": "123 Test St",
       "emergency_description_text": "Test emergency"
     }'
   ```

2. **Wait 2 seconds** - Notification call starts

3. **Call emergency number** from test phone

4. **Listen:** You should hear "Please hold while we notify the technician..."

5. **Wait ~30-60 seconds** - Hold music plays

6. **Transfer:** After notification ends, your call connects to transfer target

7. **Verify:** Check logs for successful transfer events

### Expected Timeline
- **T+0s:** Webhook POST
- **T+2s:** Technician phone rings (notification)
- **T+5s:** Customer calls in, hears hold message
- **T+35s:** Notification ends
- **T+37s:** Customer transferred, phone rings at transfer target
- **T+40s:** Transfer target answers, connected to customer

---

## Troubleshooting

### Customer Gets "Application Error"
**Cause:** System state is corrupted or timing issue
**Fix:** 
- Check if notification call is still in progress
- Verify emergency state hasn't been cleared
- Check Twilio logs for error details

### Transfer Never Happens
**Cause:** Notification callback not received or customer call SID missing
**Fix:**
- Verify `/technician_call_ended` callback is configured in Twilio
- Check `customer_call_sid` is stored in emergency state
- Ensure PUBLIC_URL is accessible by Twilio

### Customer Hears "No Active Emergency"
**Cause:** Webhook never triggered or emergency was cleared
**Fix:**
- Verify webhook was called successfully
- Check if emergency was cleared due to previous error
- Confirm timing - customer might be calling too early

---

## Summary

The warm transfer flow ensures technicians are always informed before speaking with customers:

1. **Webhook** → Emergency created
2. **Notification** → Tech receives automated call with details
3. **Customer calls** → Placed on hold with music
4. **Notification ends** → Callback received
5. **Transfer** → Customer automatically connected to tech
6. **Connected** → Tech and customer speak about emergency

This creates a professional, efficient emergency response where the technician always has context before the conversation begins.

---

**Status:** ✅ Production Ready  
**Mode:** Warm Transfer (Notification-First)  
**Timing:** ~30-60 seconds from webhook to connection  
**Documentation:** Complete
