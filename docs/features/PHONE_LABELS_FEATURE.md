# Phone Number Labels Feature

## Overview
The admin dashboard now supports adding user-friendly names/labels to recipient phone numbers. This makes it easier to identify who each phone number belongs to in the UI.

## How to Use

### In the Admin Dashboard

1. Navigate to your branch settings (e.g., `/branch/tuc/settings`)
2. Scroll to the "Recipient Phone Numbers" section
3. You'll see a dynamic interface with rows for each phone number:
   - **Name field**: Enter a friendly name (e.g., "John Doe", "On-Call Manager")
   - **Phone field**: Enter the phone number (e.g., "+15551234567")
4. Click **"+ Add Phone Number"** to add more recipients
5. Click **"Remove"** to delete a recipient
6. Click **"Save Settings"** to save your changes

### Data Format

The phone numbers are stored in JSON format:
```json
[
  {"name": "John Doe", "number": "+15551234567"},
  {"name": "Jane Smith", "number": "+15559876543"},
  {"name": "On-Call Manager", "number": "+15551111111"}
]
```

**Note**: The names are UI-only for display purposes. The backend systems only use the phone numbers when sending SMS notifications.

## Backward Compatibility

This feature is fully backward compatible with existing deployments. If you have phone numbers stored in the old comma-separated format (e.g., `+15551234567,+15559876543`), they will continue to work. The system automatically:

1. Detects which format is being used
2. Parses it appropriately
3. Extracts the phone numbers for SMS delivery

When you edit and save phone numbers in the new format, they will be converted to the JSON format automatically.

## Technical Details

### For Developers

**Frontend (branch_settings.html)**
- Dynamic JavaScript-based UI for adding/removing phone number rows
- Collects data and serializes to JSON before form submission
- Parses both JSON and CSV formats on page load for editing

**Backend (app.py)**
- `send_sms_to_all_recipients()` function updated to handle both formats
- Uses `json.loads()` with exception handling to safely parse data
- Falls back to CSV parsing if JSON parsing fails
- Extracts only `number` field from JSON objects (ignores `name` field)

### Data Flow

1. User enters names and phone numbers in the UI
2. JavaScript collects all rows and creates JSON array
3. JSON is stored in the `RECIPIENT_PHONES` setting
4. When sending SMS, backend parses JSON and extracts phone numbers
5. SMS is sent to each phone number (names are not used by backend)

## Example Use Cases

- **Property Management**: "Silverado Plumber", "HVAC Tech - Miracle Air"
- **Team Members**: "John Doe", "Jane Smith", "On-Call Manager"
- **Departments**: "Maintenance Lead", "Emergency Contact", "Backup Tech"

This makes it much easier to manage multiple recipients without having to remember or look up which phone number belongs to whom!
