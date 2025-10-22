#!/bin/bash
# Manual test script for the webhook endpoint
# This helps verify the automated call sending fixes

echo "========================================"
echo "Emergency Call Webhook Test Script"
echo "========================================"
echo ""

# Check if URL argument is provided
if [ -z "$1" ]; then
    echo "Usage: $0 <webhook_url> [phone_number]"
    echo ""
    echo "Example:"
    echo "  $0 https://tuc.axiom-emergencies.com +15551234567"
    echo "  $0 http://localhost:5000"
    echo ""
    exit 1
fi

WEBHOOK_URL="$1"
PHONE_NUMBER="${2:-+18017104034}"  # Default from test-emergency.json

echo "Testing webhook at: $WEBHOOK_URL/webhook"
echo "Using phone number: $PHONE_NUMBER"
echo ""

# Test 1: Valid request
echo "Test 1: Valid emergency call request"
echo "-------------------------------------"
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -d "{
        \"customer_name\": \"Test Customer\",
        \"user_stated_callback_number\": \"5551234567\",
        \"incident_address\": \"123 Main St, Test City\",
        \"emergency_description_text\": \"Testing automated call fix\",
        \"chosen_phone\": \"$PHONE_NUMBER\"
    }" \
    "$WEBHOOK_URL/webhook")

HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
RESPONSE_BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS/d')

echo "Response: $RESPONSE_BODY"
echo "HTTP Status: $HTTP_STATUS"

if [ "$HTTP_STATUS" = "200" ]; then
    echo "✅ Test 1 PASSED: Call initiated successfully"
else
    echo "❌ Test 1 FAILED: Expected 200, got $HTTP_STATUS"
    echo "Response: $RESPONSE_BODY"
fi
echo ""

# Wait a bit before next test
sleep 2

# Test 2: Missing phone number
echo "Test 2: Missing required field (chosen_phone)"
echo "-------------------------------------"
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -d "{
        \"customer_name\": \"Test Customer\",
        \"emergency_description_text\": \"Test without phone\"
    }" \
    "$WEBHOOK_URL/webhook")

HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
RESPONSE_BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS/d')

echo "Response: $RESPONSE_BODY"
echo "HTTP Status: $HTTP_STATUS"

if [ "$HTTP_STATUS" = "400" ]; then
    echo "✅ Test 2 PASSED: Correctly rejected missing phone"
else
    echo "❌ Test 2 FAILED: Expected 400, got $HTTP_STATUS"
fi
echo ""

# Test 3: Empty request
echo "Test 3: Empty request body"
echo "-------------------------------------"
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -d "{}" \
    "$WEBHOOK_URL/webhook")

HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
RESPONSE_BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS/d')

echo "Response: $RESPONSE_BODY"
echo "HTTP Status: $HTTP_STATUS"

if [ "$HTTP_STATUS" = "400" ]; then
    echo "✅ Test 3 PASSED: Correctly rejected empty request"
else
    echo "❌ Test 3 FAILED: Expected 400, got $HTTP_STATUS"
fi
echo ""

# Test 4: Check status endpoint
echo "Test 4: Check system status"
echo "-------------------------------------"
RESPONSE=$(curl -s -w "\nHTTP_STATUS:%{http_code}" \
    "$WEBHOOK_URL/api/status")

HTTP_STATUS=$(echo "$RESPONSE" | grep "HTTP_STATUS" | cut -d: -f2)
RESPONSE_BODY=$(echo "$RESPONSE" | sed '/HTTP_STATUS/d')

echo "Response: $RESPONSE_BODY"
echo "HTTP Status: $HTTP_STATUS"

if [ "$HTTP_STATUS" = "200" ]; then
    echo "✅ Test 4 PASSED: Status endpoint working"
else
    echo "❌ Test 4 FAILED: Expected 200, got $HTTP_STATUS"
fi
echo ""

echo "========================================"
echo "Test Summary"
echo "========================================"
echo "All tests completed. Review results above."
echo ""
echo "Note: Test 1 will only succeed if:"
echo "  - Twilio credentials are properly configured"
echo "  - Phone number format is valid (starts with +)"
echo "  - TWILIO_AUTOMATED_NUMBER is configured"
echo ""
echo "Check container logs for detailed error messages:"
echo "  docker logs twilio_responder_tuc"
echo "  docker logs twilio_responder_poc"
echo "  docker logs twilio_responder_rex"
