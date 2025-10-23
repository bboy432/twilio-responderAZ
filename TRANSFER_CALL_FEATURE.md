# Transfer Call Feature Documentation

## Overview

The transfer call feature allows incoming customer calls to be automatically transferred to a configured phone number instead of being queued to connect with a specific technician. This is useful when you want calls to go to a general line (like a main office number) rather than directly to emergency technicians.

## Configuration

### Required Settings

To enable and use the transfer call feature, configure the following:

1. **Enable Transfer Call** (`enable_transfer_call`)
   - Type: Boolean (`true` or `false`)
   - Default: `false`
   - Location: Admin Dashboard → Basic Settings
   - Description: Enables/disables the transfer call mode

2. **Transfer Target Phone Number** (`TRANSFER_TARGET_PHONE_NUMBER`)
   - Type: Phone Number (E.164 format)
   - Required: Yes (when transfer mode is enabled)
   - Location: Admin Dashboard → Advanced Settings or Environment Variables
   - Description: The phone number to transfer calls to
   - Example: `+15205551234`
   - **Must start with `+` and include country code**

3. **Transfer Number** (`TWILIO_TRANSFER_NUMBER`) [Optional]
   - Type: Phone Number (E.164 format)
   - Required: No
   - Location: Admin Dashboard → Advanced Settings or Environment Variables
   - Description: The caller ID to show when transferring (Twilio number)
   - Example: `+15205559876`
   - If not set or invalid, no caller ID will be used

## How It Works

### When Transfer Mode is Enabled (`enable_transfer_call=true`)

1. Customer calls the emergency number
2. System checks for active emergency
3. If emergency exists:
   - Customer hears: "Please hold while we transfer your call."
   - Call is transferred to `TRANSFER_TARGET_PHONE_NUMBER`
   - Transfer uses Twilio Dial with 30-second timeout
   - When transfer completes, system logs call details and cleans up

### When Transfer Mode is Disabled (`enable_transfer_call=false`)

1. Customer calls the emergency number
2. System checks for active emergency
3. If emergency exists:
   - Customer hears: "Please hold while we connect you to the emergency technician."
   - Customer is placed in queue with hold music
   - System connects customer to the specific technician assigned to the emergency
   - Original queue-based behavior

## Call Flow Diagram

### Transfer Mode Enabled
```
Customer Call → Twilio → /incoming_twilio_call
                            ↓
                     [Transfer Mode Check]
                            ↓
                   "Transferring your call..."
                            ↓
                  Dial: TRANSFER_TARGET_PHONE_NUMBER
                            ↓
                    [Call Connected]
                            ↓
                    [Call Ends]
                            ↓
                  /transfer_complete callback
                            ↓
                  Update emergency record
                            ↓
                  Send email notification
                            ↓
                  Cleanup emergency state
```

### Transfer Mode Disabled
```
Customer Call → Twilio → /incoming_twilio_call
                            ↓
                     [Transfer Mode Check]
                            ↓
                   "Connecting to technician..."
                            ↓
                  Enqueue: Customer in queue
                            ↓
                    [Technician Notified]
                            ↓
                  Dial: Connect to Queue
                            ↓
                    [Conference Call]
                            ↓
                  /conference_status callback
```

## Error Handling

The feature includes comprehensive error handling:

1. **Missing Configuration**
   - Error: `TRANSFER_TARGET_PHONE_NUMBER` not set
   - Response: "We apologize, but the transfer service is not properly configured."
   - Call is hung up
   - Error logged to debug logs

2. **Invalid Phone Format**
   - Error: Target number doesn't start with `+`
   - Response: "We apologize, but the transfer service is not properly configured."
   - Call is hung up
   - Error logged to debug logs

3. **Transfer Failure**
   - Timeout: 30 seconds (configurable in code)
   - Callback still received at `/transfer_complete`
   - Status logged and emergency cleaned up

## Enabling the Feature

### Via Admin Dashboard

1. Log in to the admin dashboard
2. Navigate to the branch settings page
3. Under "Basic Settings", find "Enable Call Transfer"
4. Toggle to `true`
5. Under "Advanced Settings", set "Transfer Target Phone Number"
6. Click "Save Settings"
7. System will automatically reload settings within 5 minutes

### Via Environment Variables

Add to your `.env` file or Docker environment:

```bash
TUC_TRANSFER_TARGET_PHONE_NUMBER=+15205551234
TUC_TWILIO_TRANSFER_NUMBER=+15205559876
```

Then update the `enable_transfer_call` setting via the admin dashboard.

## Testing

### Manual Testing

1. **Enable transfer mode** in admin dashboard
2. **Trigger an emergency** via the webhook endpoint
3. **Call the emergency number** from a test phone
4. Verify:
   - You hear "Please hold while we transfer your call."
   - Call connects to the transfer target number
   - Call completes and emergency is cleaned up
   - Check logs for `call_transfer_initiated` and `transfer_complete` events

### Expected Log Events

When transfer call is working correctly, you should see these debug events:

```
incoming_call - Customer calls emergency number
emergency_state - Active emergency found
call_transfer_initiated - Transfer started
  - emergency_id
  - transfer_target
  - transfer_from
incoming_twiml - TwiML with <Dial><Number>...</Number></Dial>
transfer_complete - Transfer finished
  - dial_call_status (completed, busy, no-answer, etc.)
  - dial_call_duration
emergency_concluded - Emergency cleaned up
```

## Troubleshooting

### Transfer not working

1. **Check if feature is enabled:**
   ```bash
   # Via API
   curl https://your-branch.com/api/logs?recent=10
   # Look for "enable_transfer_call": "true"
   ```

2. **Verify target number format:**
   - Must start with `+`
   - Must include country code
   - Example: `+15205551234` (correct) vs `5205551234` (wrong)

3. **Check debug logs:**
   ```bash
   docker logs twilio_responder_tuc | grep -i transfer
   ```

4. **Common errors:**
   - `transfer_config_error`: Missing or invalid configuration
   - `call_handling_error`: Exception during call processing

### No callback received

1. **Verify PUBLIC_URL is correct:**
   - Must be accessible by Twilio servers
   - Must use HTTPS (not HTTP) in production
   - Example: `https://tuc.axiom-emergencies.com`

2. **Check Twilio webhook logs:**
   - Log into Twilio Console
   - Go to your phone number configuration
   - Check webhook error logs

## Security Considerations

1. **Phone Number Validation**: System validates all phone numbers before use
2. **Error Messages**: Generic error messages to callers, detailed logs internally
3. **Caller ID**: Optional; only used if properly formatted
4. **Timeout**: 30-second timeout prevents indefinite hanging calls

## Backwards Compatibility

- Existing queue-based behavior is preserved when transfer mode is disabled
- No changes required to existing configuration
- Feature can be toggled on/off without code changes
- All existing emergency workflows continue to work

## API Reference

### Endpoints

#### `/incoming_twilio_call` (Modified)
- **Method**: POST
- **Purpose**: Handles incoming customer calls
- **New Behavior**: Checks `enable_transfer_call` setting and either transfers or queues

#### `/transfer_complete` (New)
- **Method**: POST
- **Purpose**: Callback when transfer call completes
- **Parameters**: 
  - `emergency_id` (query string)
  - `DialCallStatus` (form data from Twilio)
  - `DialCallDuration` (form data from Twilio)

### Settings

| Setting | Type | Default | Location |
|---------|------|---------|----------|
| `enable_transfer_call` | boolean | `false` | Basic Settings |
| `TRANSFER_TARGET_PHONE_NUMBER` | string | - | Advanced Settings |
| `TWILIO_TRANSFER_NUMBER` | string | - | Advanced Settings |

## Development Notes

### Code Location
- Main logic: `app.py` route `/incoming_twilio_call` (function `handle_incoming_twilio_call`)
- Callback: `app.py` route `/transfer_complete` (function `transfer_complete`)

### Dependencies
- `twilio.twiml.voice_response.Dial` - Used for call transfer
- `twilio.twiml.voice_response.VoiceResponse` - TwiML generation

### Testing
- Unit tests: `/tmp/test_transfer_logic.py`
- Integration tests: Use existing `test_webhook.sh` script
