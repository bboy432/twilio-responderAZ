# Trigger Emergency Feature Implementation

## Problem Statement
The issue reported that "trigger emergency doesn't seem to be an option available in the dashboard". Upon investigation, we found that:
- The `can_trigger` permission existed in the database schema
- Users could be granted this permission in the User Management interface
- However, there was no UI or API endpoint to actually trigger emergencies from the admin dashboard

## Solution Overview
We added a complete trigger emergency feature to the admin dashboard that:
1. Respects existing permission system
2. Provides a user-friendly form interface
3. Validates all inputs before submission
4. Forwards requests to the branch instances
5. Sends notifications for audit trail

## Implementation Details

### Backend Changes

**File: `admin-dashboard/app.py`**

Added a new API endpoint `/api/branch/<branch>/trigger`:
- Checks if user is authenticated (`@login_required`)
- Validates branch parameter exists
- Checks user has `can_trigger` permission for that branch
- Validates all required fields in request body
- Forwards the emergency trigger to the branch's `/webhook` endpoint
- Sends SMS notification to administrator
- Returns appropriate success/error responses

Key features:
- Permission-based access control
- Input validation for all required fields
- Error handling for network timeouts and connection errors
- Audit trail via SMS notifications

### Frontend Changes

**File: `admin-dashboard/templates/branch_dashboard.html`**

Added a collapsible section "🚨 Trigger Emergency" that:
- Only displays if user has `can_trigger` permission or is admin
- Shows warning message about triggering test emergencies
- Contains a complete form with all required fields
- Uses proper HTML5 input types for validation
- Styled consistently with the rest of the dashboard

**File: `admin-dashboard/static/js/dashboard.js`**

Added `triggerEmergency()` function that:
- Validates phone number format (must start with +)
- Shows confirmation dialog before submitting
- Displays loading state during API call
- Shows success/error messages to user
- Clears form and refreshes page on success
- Handles network errors gracefully

## Security Considerations

1. **Permission Checks**: The `can_trigger` permission is checked at the API level, not just the UI level
2. **Input Validation**: All required fields are validated before processing
3. **Audit Trail**: SMS notifications are sent when emergencies are triggered
4. **Authentication**: All endpoints require user authentication
5. **No Code Injection**: All user inputs are properly escaped and validated

CodeQL security scan results: **0 alerts** ✅

## Usage Instructions

### For Administrators
1. Go to User Management
2. Create or edit a user
3. Check the "Trigger Emergencies" permission for the desired branch(es)
4. Save the user

### For Users with Permission
1. Login to admin dashboard
2. Click on a branch (e.g., "View Dashboard" for Tucson)
3. You'll see the "🚨 Trigger Emergency" section
4. Fill in all required fields:
   - Technician Phone (must start with +)
   - Customer Name
   - Callback Number (must start with +)
   - Incident Address
   - Emergency Description
5. Click "🚨 Trigger Emergency"
6. Confirm in the dialog
7. The system will trigger the emergency and notify the technician

## Testing

All tests passed:
- ✅ Python syntax validation
- ✅ API endpoint exists with proper validations
- ✅ JavaScript function exists with all required fields
- ✅ HTML template has complete form
- ✅ User management includes trigger permission
- ✅ CodeQL security scan (0 alerts)

## Files Modified
1. `admin-dashboard/app.py` - Added trigger emergency API endpoint
2. `admin-dashboard/templates/branch_dashboard.html` - Added trigger form UI
3. `admin-dashboard/static/js/dashboard.js` - Added trigger emergency function

## Backwards Compatibility
This change is fully backwards compatible:
- No database schema changes required (permission already existed)
- No breaking changes to existing functionality
- Users without permission won't see the new feature
- Existing API endpoints remain unchanged

## Future Enhancements
Possible future improvements:
- Add a "Recent Triggers" log on the dashboard
- Pre-fill form with default values from branch settings
- Add bulk trigger for multiple branches
- Add scheduled/automated triggers
