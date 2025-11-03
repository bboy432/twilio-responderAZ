# Emergency Call System - How It Works

## 📞 What This System Does

This system handles emergency calls for Axiom Property Management. When an emergency happens, it:

1. **Notifies the technician** with an automated call containing emergency details
2. **Puts the customer on hold** with music while the technician listens to the notification
3. **Automatically connects** the customer to the technician after they've been informed

This is called a **"warm transfer"** because the technician knows about the emergency before talking to the customer.

---

## 🔄 Complete Call Flow (Simple Version)

### Step 1: Emergency Happens
Someone reports an emergency (water leak, broken AC, etc.)

### Step 2: System Calls Technician
- Technician's phone rings immediately
- They answer and hear: *"Emergency Alert. Customer: John Doe at 123 Main Street..."*
- Technician just listens (takes about 30-60 seconds)
- Call ends automatically

### Step 3: Customer Calls In
- Customer dials the emergency phone number
- They hear: *"Please hold while we notify the technician about your emergency"*
- Hold music plays 🎵

### Step 4: Automatic Connection
- When technician's notification ends, system makes another call to the technician
- Technician's phone rings again
- When they answer, customer is automatically connected
- **Now they're talking!** Technician already knows what the emergency is

---

## ⏱️ Timeline Example

```
TIME          WHAT'S HAPPENING
────────────────────────────────────────────────────────────────
0:00          Emergency reported via webhook
              
0:02          Tech's phone rings 📞
              Tech answers
              
0:03-0:35     Tech listens to emergency details
              (Automated message plays)
              
0:05          Customer dials emergency number 📞
              Customer hears: "Please hold..."
              Hold music plays 🎵
              
0:35          Tech's notification ends
              System starts warm transfer
              
0:37          Tech's phone rings again 📞
              Customer still on hold 🎵
              
0:40          Tech answers second call
              ✅ Customer and Tech are connected!
              They start talking about the emergency
```

**Total wait time for customer:** ~35 seconds of hold music

---

## 🎯 Two Operating Modes

### Mode 1: Transfer Mode (For Office Lines)
**When to use:** Transfer calls to a main office number

**How it works:**
- Customer on hold in queue
- System calls the office number
- Office person answers
- Customer automatically connected to whoever answered

**Configuration:**
```
enable_transfer_call = true
TRANSFER_TARGET_PHONE_NUMBER = +15205551234
```

### Mode 2: Queue Mode (For Specific Technicians)  
**When to use:** Connect customer to the specific assigned technician

**How it works:**
- Customer on hold in queue
- System calls the assigned technician
- Technician answers
- Customer automatically connected to that specific technician

**Configuration:**
```
enable_transfer_call = false
(This is the default)
```

---

## 📋 Detailed Technical Flow

### What Happens Behind the Scenes

#### 1. Webhook Trigger (`/webhook`)
```
POST /webhook
{
  "chosen_phone": "+15205551234",
  "customer_name": "John Doe",
  "incident_address": "123 Main St",
  "emergency_description_text": "Water leak in unit 5"
}

↓

System creates emergency record
Emergency ID: abc-123
Status: "informing_technician"
```

#### 2. Notification Call Initiated
```
System → Twilio API
"Make a call to +15205551234"

TwiML: <Response>
         <Pause length="2"/>
         <Say>Emergency Alert. Customer: John Doe...</Say>
         <Hangup/>
       </Response>

↓

Tech's phone rings
Tech answers and listens
Call lasts ~30-60 seconds
```

#### 3. Customer Calls In (`/incoming_twilio_call`)
```
Customer → Dials emergency number
↓
System checks: Is there an active emergency? YES
↓
TwiML: <Response>
         <Say>Please hold while we notify the technician...</Say>
         <Enqueue waitUrl="...music.mp3">abc-123</Enqueue>
       </Response>
↓
Customer in queue "abc-123" with hold music
Status updated: "customer_waiting"
Customer Call SID saved: CA123abc
```

#### 4. Notification Ends (Callback)
```
Notification call completes
↓
Twilio → POST /technician_call_ended?emergency_id=abc-123
↓
System checks: Is customer waiting? YES
Status: "customer_waiting"
↓
Trigger transfer function
```

#### 5. Transfer Initiated (`transfer_customer_to_target`)
```
System → Twilio API
"Make a new call to transfer target"

TwiML: <Response>
         <Say>Connecting you to the customer now.</Say>
         <Dial action="/transfer_complete">
           <Queue>abc-123</Queue>
         </Dial>
       </Response>

↓

Transfer target phone rings
When they answer: Customer dequeued and connected
```

#### 6. Connected!
```
Customer (was in queue) ←→ Transfer Target (answered second call)

They can now talk to each other
Technician already knows emergency details
```

#### 7. Call Ends
```
Either party hangs up
↓
Twilio → POST /transfer_complete?emergency_id=abc-123
↓
System logs call duration and status
Sends final email notification
Clears emergency record
System ready for next emergency
```

---

## 🔍 Why It Works This Way

### Why Not Connect Immediately?
**Problem:** If we connected customer directly, technician wouldn't know what the emergency is.

**Solution:** Send notification first, then connect. (Warm transfer)

### Why Does Customer Wait on Hold?
**Reason:** The technician needs time to listen to the emergency details first.

**Duration:** Usually 30-60 seconds (length of notification message)

**What They Hear:** Classical hold music, not silence

### Why Two Calls to the Technician?
**Call #1 (Notification):** One-way message with emergency details

**Call #2 (Transfer):** Two-way conversation with the customer

This ensures the technician is always prepared before talking to the customer.

### Why Use Queues?
**Reason:** Twilio queues are designed for holding callers and connecting them to representatives.

**How It Works:**
- Customer enters queue (like a waiting room)
- System makes a call that "dequeues" them (pulls them out)
- Both parties connected via the dequeue operation

**Why Not Update Call Directly?**
- You **cannot** modify TwiML on a call that's in a queue
- Must use the queue dequeue method (`<Dial><Queue>`)

---

## 🚨 What Could Go Wrong

### Problem: Customer Gets "Application Error"
**Cause:** System tried to update a queued call's TwiML (not allowed by Twilio)

**Fix:** Use proper dequeue method (✅ Fixed in this version)

### Problem: Customer Hears "No Active Emergency"
**Possible Causes:**
1. Webhook wasn't triggered yet
2. Notification call failed and emergency was cleared
3. Previous emergency wasn't cleaned up properly

**Fix:** Check that webhook completed successfully before customer calls

### Problem: Transfer Never Happens
**Possible Causes:**
1. Notification callback (`/technician_call_ended`) not received
2. Customer hung up before notification ended
3. Network/Twilio API issues

**Debug:** Check logs for:
- `technician_call_ended` event
- `customer_waiting_status` = true
- `initiating_transfer_after_notification` event

### Problem: Customer Waits Forever
**Possible Causes:**
1. Notification call is very long
2. Transfer call creation failed
3. Transfer target doesn't answer

**Fix:** 
- Set reasonable timeout on transfer dial (30 seconds)
- Monitor for stuck emergencies
- Manual intervention if needed

---

## 🔧 Configuration Settings

### Required Settings
```
TWILIO_ACCOUNT_SID          Your Twilio account ID
TWILIO_AUTH_TOKEN           Your Twilio API token
TWILIO_AUTOMATED_NUMBER     Twilio number that makes calls (+15205559999)
PUBLIC_URL                  Your server URL (must be HTTPS)
```

### Transfer Mode Settings (Optional)
```
enable_transfer_call              true/false (default: false)
TRANSFER_TARGET_PHONE_NUMBER      Where to transfer calls (+15205551234)
TWILIO_TRANSFER_NUMBER            Caller ID for transfer (optional)
```

### Where to Configure
- **Admin Dashboard:** Log in at axiom-emergencies.com
- **Settings Page:** Each branch has its own settings
- **Environment Variables:** Can also set via `.env` file

---

## 📊 Monitoring & Debugging

### Key Debug Events

**Successful Flow:**
```
1. webhook_received               ← Emergency triggered
2. emergency_call_initiated       ← Notification call started
3. incoming_call                  ← Customer called in
4. customer_queued_for_transfer   ← Customer on hold
5. technician_call_ended          ← Notification complete
6. initiating_transfer_after_notification
7. using_queue_dequeue_method     ← Transfer started
8. transfer_call_initiated_dequeue
9. transfer_complete              ← Customer connected
10. emergency_concluded           ← All done
```

**Problem Indicators:**
```
❌ no_active_emergency            No emergency when customer called
❌ transfer_config_error          Settings not configured
❌ transfer_error                 Transfer couldn't start
❌ call_initiation_error          Couldn't make notification call
```

### Where to See Logs
- **Admin Dashboard:** Real-time event log
- **Branch Dashboard:** Timeline view
- **Server Logs:** Docker logs or `/api/logs` endpoint
- **Twilio Console:** Call logs and debugger

---

## 🧪 Testing Instructions

### Quick Test (5 Minutes)

**Step 1: Trigger Webhook**
```bash
curl -X POST https://tuc.axiom-emergencies.com/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "chosen_phone": "+15205551234",
    "customer_name": "Test Customer",
    "user_stated_callback_number": "+15205555678",
    "incident_address": "123 Test Street",
    "emergency_description_text": "Test emergency - water leak"
  }'
```

**Step 2: Answer Notification Call**
- Your phone (+15205551234) will ring
- Answer it
- Listen to the emergency details message
- Call ends automatically after ~30 seconds

**Step 3: Call As Customer**
- Dial the emergency phone number
- You should hear: "Please hold while we notify the technician..."
- Hold music should play

**Step 4: Wait for Transfer**
- After notification ends (~30 seconds)
- Your phone will ring again
- Answer it
- You should be connected to the "customer" (the hold music will stop)

**Step 5: Verify**
- Check admin dashboard for successful transfer event
- Check timeline shows complete flow
- Emergency should be cleared

### Expected Timeline
- T+0s: POST webhook
- T+2s: Your phone rings (notification)
- T+5s: You call emergency number (as customer)
- T+35s: Notification ends
- T+37s: Your phone rings again (transfer)
- T+40s: You answer, customer connected

---

## 💡 Best Practices

### For Users
1. **Wait for hold music** - Don't hang up if you hear music
2. **Be patient** - Transfer takes 30-60 seconds (notification length)
3. **Check logs** - Use admin dashboard to monitor calls

### For Technicians
1. **Answer notification call** - Even if you can't help, listen to details
2. **Expect second call** - You'll receive two calls per emergency
3. **Have pen ready** - Write down details during notification

### For Administrators
1. **Test regularly** - Do a test call weekly
2. **Monitor logs** - Check for errors in admin dashboard
3. **Keep settings updated** - Verify phone numbers are current
4. **Configure timeouts** - Adjust based on your notification length

---

## 📝 Summary

**What happens:**
1. Emergency → Webhook triggered
2. Tech phone rings → Listens to details (30-60s)
3. Customer calls → On hold with music
4. Notification ends → Transfer initiated
5. Tech phone rings again → Answers and connects to customer
6. They talk → Emergency handled

**Why it works:**
- ✅ Technician always informed first (warm transfer)
- ✅ Customer doesn't wait alone (hold music)
- ✅ Automatic connection (no manual steps)
- ✅ Reliable queue-based system (proven Twilio method)

**Key point:**
> The system uses Twilio **queues** to hold the customer and **dequeue** to connect them. You cannot modify a call's TwiML while it's in a queue - you must dequeue it using `<Dial><Queue>`.

---

## 🛠️ Recent Fix (This Update)

**Problem:** System tried to use `call.update(twiml=...)` on queued calls, which Twilio doesn't allow.

**Solution:** Removed the call redirect attempt and use proper queue dequeue method directly.

**Result:** Warm transfers now work reliably without errors.

---

**Questions?** Check the admin dashboard or contact support.

**Status:** ✅ System Working  
**Last Updated:** 2025-11-03  
**Version:** Warm Transfer (Queue Dequeue Method)
