# Quick Reference - Emergency Call System

## 🚨 What Happens When Someone Reports an Emergency

```
┌─────────────────────────────────────────────────────────────────┐
│                    EMERGENCY REPORTED                           │
│                    (Webhook Triggered)                          │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1: Tech's Phone Rings (Notification Call)                │
│  ────────────────────────────────────────────                   │
│  • Automated call with emergency details                        │
│  • Tech just listens (30-60 seconds)                           │
│  • "Emergency Alert. Customer: John Doe at..."                 │
│  • Call ends automatically                                      │
└────────────────────┬────────────────────────────────────────────┘
                     │
                     │ (Tech is listening...)
                     │
                     ├──────────────────────────────────────┐
                     │                                      │
                     ▼                                      ▼
┌─────────────────────────────────────┐  ┌──────────────────────────────┐
│  STEP 2: Customer Calls In          │  │  Tech Still Listening to     │
│  ───────────────────────────────     │  │  Notification...             │
│  • Dials emergency number            │  │                              │
│  • Hears: "Please hold..."           │  └──────────────────────────────┘
│  • Hold music plays 🎵               │                 │
└──────────────┬──────────────────────┘                 │
               │                                        │
               │ (Customer waiting...)                  │
               │                                        ▼
               │                         ┌──────────────────────────────┐
               │                         │  Notification Call Ends      │
               │                         │  ────────────────────────    │
               │                         │  • Tech heard all details    │
               │                         │  • System triggers transfer  │
               │                         └──────────────┬───────────────┘
               │                                        │
               │                                        ▼
               │                         ┌──────────────────────────────┐
               │                         │  STEP 3: Tech's Phone Rings  │
               │                         │  (Second Call - Transfer)    │
               │                         │  ────────────────────────    │
               │                         │  • New call to tech          │
               │                         │  • When answered, customer   │
               │                         │    is dequeued and connected │
               │                         └──────────────┬───────────────┘
               │                                        │
               │                                        ▼
               └────────────────────────────────────────┤
                                                        │
                                                        ▼
                         ┌────────────────────────────────────────────┐
                         │  STEP 4: Connected!                        │
                         │  ─────────────────────                     │
                         │  🎉 Tech + Customer talking                │
                         │  Tech already knows emergency details      │
                         └────────────────────────────────────────────┘
```

## ⏱️ Typical Timeline

| Time  | Event                           | Who            |
|-------|---------------------------------|----------------|
| 0:00  | Emergency reported              | System         |
| 0:02  | Tech's phone rings (Call #1)    | Tech           |
| 0:03  | Tech answers and listens        | Tech           |
| 0:05  | Customer calls emergency number | Customer       |
| 0:06  | Customer on hold with music 🎵  | Customer       |
| 0:35  | Notification ends (Call #1)     | Tech           |
| 0:36  | System initiates transfer       | System         |
| 0:37  | Tech's phone rings (Call #2)    | Tech           |
| 0:40  | Tech answers Call #2            | Tech           |
| 0:40  | Customer + Tech connected! 🎉   | Both           |

**Total customer wait time:** ~35 seconds

## 📞 Two Calls, One Emergency

### Call #1: Notification (One-Way)
- **Purpose:** Inform tech about emergency
- **What tech hears:** Automated message with details
- **Duration:** 30-60 seconds
- **What tech does:** Just listen, takes notes
- **Ends:** Automatically

### Call #2: Transfer (Two-Way)
- **Purpose:** Connect tech to customer
- **What tech hears:** Ring, then customer on the line
- **Duration:** Until someone hangs up
- **What tech does:** Talks to customer about emergency
- **Ends:** When call is complete

## 🎯 Why Two Calls?

**Without warm transfer (bad):**
```
Customer calls → Tech answers → "What's the emergency?"
❌ Tech has no context
```

**With warm transfer (good):**
```
System calls tech → Tech listens to details
Customer calls → On hold
Notification ends → Tech called again → Connected to customer
✅ Tech already knows what's happening
```

## 🔧 Two Operating Modes

### Transfer Mode
```
Customer → Queue → Dequeue → Transfer Target Phone
```
- Use when: Transferring to general office line
- Setting: `enable_transfer_call = true`
- Connects to: Whoever answers the transfer target number

### Queue Mode  
```
Customer → Queue → Dequeue → Specific Technician
```
- Use when: Connecting to assigned technician
- Setting: `enable_transfer_call = false` (default)
- Connects to: The technician assigned to this emergency

## 🚨 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Customer hears "No active emergency" | Webhook must be triggered first |
| Customer gets application error | Fixed in this update! (Was trying to update queued calls) |
| Transfer never happens | Check notification callback is configured |
| Customer waits forever | Check if notification call completed |

## 📚 Full Documentation

- **[HOW_IT_WORKS.md](HOW_IT_WORKS.md)** - Complete detailed guide
- **[WARM_TRANSFER_FLOW.md](WARM_TRANSFER_FLOW.md)** - Technical documentation
- **[FIX_SUMMARY.md](FIX_SUMMARY.md)** - What was fixed and why

## 🧪 Quick Test

1. POST to `/webhook` endpoint
2. Answer notification call when tech phone rings
3. Call emergency number from another phone
4. Wait ~30 seconds on hold
5. Answer when tech phone rings again
6. Verify you're connected to the "customer" call

**Expected:** Smooth warm transfer with no errors

---

**Quick Answer:** The system calls the tech first to inform them, then connects the customer after they've been informed. This is called a "warm transfer" and it works now!
