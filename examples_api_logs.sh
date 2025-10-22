#!/bin/bash
# Example usage script for the new /api/logs endpoint
# This demonstrates how to retrieve logs without needing a webhook URL

echo "=========================================="
echo "API Logs Endpoint Usage Examples"
echo "=========================================="
echo ""

# Set the branch URL (replace with your actual branch URL)
BRANCH_URL="${1:-http://localhost:5000}"

echo "Testing against: $BRANCH_URL"
echo ""

# Example 1: Check if the endpoint is available
echo "1. Testing /api/logs endpoint (no parameters)"
echo "   Expected: 400 with usage examples"
echo "   ---"
curl -s "$BRANCH_URL/api/logs" | jq '.'
echo ""
echo ""

# Example 2: Get all logs
echo "2. Retrieve all logs"
echo "   Command: curl $BRANCH_URL/api/logs?all"
echo "   ---"
curl -s "$BRANCH_URL/api/logs?all" | jq '{status, count, log_count: (.logs | length)}'
echo ""
echo ""

# Example 3: Get recent 10 entries
echo "3. Retrieve 10 most recent log entries"
echo "   Command: curl $BRANCH_URL/api/logs?recent=10"
echo "   ---"
curl -s "$BRANCH_URL/api/logs?recent=10" | jq '{status, count, requested}'
echo ""
echo ""

# Example 4: Get recent 5 entries with full details
echo "4. Retrieve 5 most recent entries (with details)"
echo "   Command: curl $BRANCH_URL/api/logs?recent=5"
echo "   ---"
curl -s "$BRANCH_URL/api/logs?recent=5" | jq '.logs[0:2]'
echo "   ... (showing first 2 of 5)"
echo ""
echo ""

# Example 5: Error handling - invalid parameter
echo "5. Test error handling (invalid parameter)"
echo "   Command: curl $BRANCH_URL/api/logs?recent=invalid"
echo "   Expected: 400 error"
echo "   ---"
curl -s "$BRANCH_URL/api/logs?recent=invalid" | jq '.'
echo ""
echo ""

# Example 6: Clear logs
echo "6. Clear/archive logs using DELETE"
echo "   Command: curl -X DELETE $BRANCH_URL/api/logs"
echo "   Expected: Logs archived to timestamped file"
echo "   ---"
curl -s -X DELETE "$BRANCH_URL/api/logs" | jq '.'
echo ""
echo ""

echo "=========================================="
echo "Integration Examples"
echo "=========================================="
echo ""

echo "Python example:"
cat << 'EOF'
import requests

# Get recent logs
response = requests.get('http://localhost:5000/api/logs?recent=20')
logs = response.json()

if logs['status'] == 'success':
    for log in logs['logs']:
        print(f"{log['timestamp']} - {log['title']}")
        print(f"  Status: {log['status']}")
        print(f"  Details: {log['details'][:100]}...")

# Clear logs when needed
clear_response = requests.delete('http://localhost:5000/api/logs')
if clear_response.json()['status'] == 'success':
    print("Logs cleared successfully")
EOF

echo ""
echo ""

echo "PowerShell example:"
cat << 'EOF'
$response = Invoke-RestMethod -Uri "http://localhost:5000/api/logs?recent=20"
if ($response.status -eq "success") {
    foreach ($log in $response.logs) {
        Write-Host "$($log.timestamp) - $($log.title)"
        Write-Host "  Status: $($log.status)"
    }
}

# Clear logs when needed
$clearResponse = Invoke-RestMethod -Uri "http://localhost:5000/api/logs" -Method Delete
if ($clearResponse.status -eq "success") {
    Write-Host "Logs cleared successfully"
}
EOF

echo ""
echo ""

echo "=========================================="
echo "Key Benefits"
echo "=========================================="
echo "✓ Works without DEBUG_WEBHOOK_URL configured"
echo "✓ Retrieve logs programmatically via HTTP GET"
echo "✓ Clear logs programmatically via HTTP DELETE"
echo "✓ Filter by count (?recent=N) or get all (?all)"
echo "✓ JSON response format for easy integration"
echo "✓ Secure - no stack trace exposure"
echo "✓ Logs are archived (not deleted) when cleared"
echo ""
