# Call Recording Feature Documentation

## Overview
The Call Recording feature allows administrators and authorized users to view and manage call recordings from Twilio through the branch dashboard interface. Each branch has its own recordings filtered by the branch's Twilio phone numbers.

## Features

### 1. Call Recordings Section
- **Location**: Branch Dashboard (collapsible section)
- **Access**: Users with `can_view` permission for the branch
- **Icon**: 📞 Call Recordings

### 2. Recording Display
Each recording shows:
- **From/To Numbers**: Formatted phone numbers
- **Date/Time**: When the recording was created
- **Duration**: Length of the recording in seconds
- **Status**: Recording status (completed, processing, etc.)
- **Audio Player**: Built-in HTML5 audio player for playback
- **Download Button**: Download the recording as MP3
- **Recording SID**: Twilio recording identifier

### 3. Pagination
- Navigate through recordings with Previous/Next buttons
- Configurable page size (5-50 recordings per page)
- Page number indicator

### 4. Settings
Two new settings in the Branch Settings page under "Basic Settings - Feature Toggles":

#### enable_call_recording
- **Type**: Checkbox
- **Default**: true
- **Purpose**: Show/hide the call recordings section in the branch dashboard
- **Label**: "Enable Call Recordings Display"

#### call_recording_page_size
- **Type**: Number
- **Default**: 20
- **Range**: 5-50 (increments of 5)
- **Purpose**: Control how many recordings are displayed per page
- **Label**: "Call Recordings Per Page"

## API Endpoint

### GET /api/branch/<branch>/recordings

Fetches call recordings for a specific branch from Twilio.

**Authentication**: Required (login_required decorator)

**Permissions**: User must have `can_view` permission for the branch

**Query Parameters**:
- `page` (optional, default: 0): Page number for pagination
- `page_size` (optional, default: 20): Number of recordings per page

**Response Format**:
```json
{
    "success": true,
    "recordings": [
        {
            "sid": "RExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "call_sid": "CAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "duration": "45",
            "date_created": "2024-01-15T10:30:00",
            "from": "+15201234567",
            "to": "+15551234567",
            "status": "completed",
            "uri": "/2010-04-01/Accounts/ACxxxx/Recordings/RExxxx.json",
            "media_url": "https://api.twilio.com/2010-04-01/Accounts/ACxxxx/Recordings/RExxxx.mp3"
        }
    ],
    "page": 0,
    "page_size": 20,
    "count": 15
}
```

**Error Responses**:
- `400`: Twilio credentials not configured
- `403`: Permission denied
- `404`: Invalid branch
- `500`: Failed to fetch recordings from Twilio

**Filtering Logic**:
Recordings are automatically filtered to show only calls where:
- The `from` number matches any of the branch's Twilio phone numbers, OR
- The `to` number matches any of the branch's Twilio phone numbers

Branch phone numbers include:
- `TWILIO_PHONE_NUMBER`
- `TWILIO_AUTOMATED_NUMBER`
- `TWILIO_TRANSFER_NUMBER`

## Implementation Details

### Backend (admin-dashboard/app.py)
- Added `get_call_recordings()` route handler
- Uses Twilio Python SDK to fetch recordings
- Implements branch-specific filtering
- Handles pagination
- Fetches call details for each recording

### Frontend JavaScript (admin-dashboard/static/js/dashboard.js)
- `loadCallRecordings(branchKey, page)`: Fetches recordings via API
- `displayRecordings(recordings, container)`: Renders recording items
- `updatePaginationControls(branchKey, currentPage, count, container)`: Updates pagination UI
- `loadCallRecordingsOnOpen(branchKey)`: Lazy-loads recordings when section is opened

### Templates

#### branch_dashboard.html
- Added collapsible section for call recordings
- Includes loading spinner with CSS animation
- Error message display area
- Recordings container with pagination controls

#### branch_settings.html
- Added two new settings fields
- Integrated with existing settings form
- Follows existing UI patterns

## Usage

### For Administrators

1. **Enable/Disable Feature**:
   - Navigate to Branch Settings
   - Find "Enable Call Recordings Display" checkbox
   - Check to enable, uncheck to disable
   - Click "Save Settings"

2. **Configure Page Size**:
   - Navigate to Branch Settings
   - Find "Call Recordings Per Page" field
   - Enter a number between 5 and 50
   - Click "Save Settings"

3. **View Recordings**:
   - Navigate to Branch Dashboard
   - Click on "📞 Call Recordings" section header
   - Recordings will load automatically
   - Use Previous/Next buttons to navigate pages

### For Users with View Permission

1. **View Recordings**:
   - Navigate to your assigned branch dashboard
   - Click on "📞 Call Recordings" section header
   - Browse recordings
   - Listen to recordings using the audio player
   - Download recordings if needed

## Security

### Permissions
- Only users with `can_view` permission can access recordings
- Recordings are filtered by branch-specific phone numbers
- Session-based authentication required

### Data Privacy
- Recordings contain sensitive information (phone numbers, voice)
- Only authorized users can access recordings
- Recordings are stored securely by Twilio
- Media URLs are generated on-demand

### Security Scan Results
- **CodeQL Analysis**: 0 alerts
- **Python**: No vulnerabilities found
- **JavaScript**: No vulnerabilities found

## Testing

Tests included:
1. Branch number filtering logic
2. Pagination parameter validation
3. Settings definition verification
4. Recording data format validation

All tests passed successfully.

## Troubleshooting

### Recordings Not Loading
- Check if Twilio credentials are configured for the branch
- Verify the user has `can_view` permission
- Check browser console for error messages
- Verify the branch has call recordings in Twilio

### No Recordings Displayed
- Verify the branch has made calls that were recorded
- Check if recording is enabled in Twilio
- Ensure the branch phone numbers are correctly configured
- Note: Recordings may take a few minutes to appear after a call

### Pagination Not Working
- Check if `call_recording_page_size` setting is configured
- Verify the page parameter is being passed correctly
- Check browser console for JavaScript errors

## Future Enhancements

Possible improvements:
1. Search/filter recordings by date range
2. Search by phone number
3. Export recordings list to CSV
4. Batch download multiple recordings
5. Recording transcription display (if available from Twilio)
6. Recording deletion capability
7. Recording notes/annotations

## Related Documentation

- [Twilio Recordings API](https://www.twilio.com/docs/voice/api/recording)
- [Admin Dashboard README](admin-dashboard/README.md)
- [Settings Management](SETTINGS_MANAGEMENT.md)
- [Branch Dashboard Documentation](admin-dashboard/templates/branch_dashboard.html)
