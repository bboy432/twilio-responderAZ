import subprocess
import os
import time
import requests
import atexit
import json
import platform
from flask import Flask, request, jsonify, render_template_string, redirect, url_for
import logging
from datetime import datetime, timedelta
import threading
import csv
import re
import socket

# It's good practice to wrap third-party library imports in a try-except block
try:
    from twilio.rest import Client
    from twilio.twiml.voice_response import VoiceResponse, Dial, Pause
except ImportError:
    print("Twilio library not found. Please install it using: pip install twilio")
    exit()

# --- NEW: Import the messaging module safely ---
try:
    from messages import send_status_report
    MESSAGING_MODULE_LOADED = True
except ImportError as e:
    MESSAGING_MODULE_LOADED = False
    logging.warning(f"Could not import from messages.py, status replies will be disabled. Error: {e}")


# Docker-friendly log path (inside container)
LOG_PATH = "/app/logs/app.log"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)

# --- Load Configuration from Environment Variables ---
try:
    TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
    TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')
    TWILIO_AUTOMATED_NUMBER = os.environ.get('TWILIO_AUTOMATED_NUMBER')
    TWILIO_TRANSFER_NUMBER = os.environ.get('TWILIO_TRANSFER_NUMBER')
    TRANSFER_TARGET_PHONE_NUMBER = os.environ.get('TRANSFER_TARGET_PHONE_NUMBER')
    PUBLIC_URL = os.environ.get('PUBLIC_URL')
    FLASK_PORT = int(os.environ.get('FLASK_PORT', 5000))
    RECIPIENT_EMAILS = os.environ.get('RECIPIENT_EMAILS', '') # <-- ADD THIS LINE

    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, TWILIO_AUTOMATED_NUMBER, TWILIO_TRANSFER_NUMBER, TRANSFER_TARGET_PHONE_NUMBER, PUBLIC_URL, FLASK_PORT]):
        raise ValueError("One or more required environment variables are missing.")

except Exception as e:
    logging.critical(f"CRITICAL ERROR: Could not load configuration from environment variables: {e}")
    exit()

# --- Contact Mapping ---
KNOWN_CONTACTS = {
    "+15207360648": "Sonia",
    "+15206960000": "Plumbing Emergency Silverado",
    "+12084039927": "AMS Technician",
    "+15313291106": "Christian Technician",
    "+15205492665": "HVAC Emergency Miracle Air"
}

app = Flask(__name__)
public_url = PUBLIC_URL

# --- Email Placeholder ---
def send_to_all(subject, body):
    email_recipients = [e.strip() for e in RECIPIENT_EMAILS.split(',') if e.strip()]
    if not email_recipients:
        logging.warning("Email sending skipped: RECIPIENT_EMAILS environment variable is not set.")
        return

    logging.info("--- SIMULATING EMAIL SEND ---")
    logging.info(f"Recipients: {', '.join(email_recipients)}")
    logging.info(f"Subject: {subject}")
    logging.info(f"Body:\n{body}")
    logging.info("--- END OF SIMULATED EMAIL ---")

# --- Global State Management ---
active_automated_call = None
automated_call_lock = threading.Lock()
waiting_calls = []
waiting_calls_lock = threading.Lock()
latest_chosen_phone = None # No one is on call by default
latest_phone_lock = threading.Lock()
emergency_data = None
emergency_data_lock = threading.Lock()
call_statuses = {
    'emergency_call': {'status': 'N/A', 'timestamp': None},
    'transfer_call': {'status': 'N/A', 'timestamp': None}
}
call_status_lock = threading.Lock()
transfer_attempts = {}
transfer_attempts_lock = threading.Lock()
MAX_TRANSFER_ATTEMPTS = 2


# --- Log Parsing and Status Functions ---
def get_network_info():
    """Gets the server's hostname and primary IP address."""
    try:
        hostname = socket.gethostname()
        ip_address = subprocess.check_output(['hostname', '-I']).decode('utf-8').split()[0]
        return hostname, ip_address
    except Exception as e:
        logging.error(f"Could not get network info: {e}")
        return "Unknown Host", "Unknown IP"

def get_simple_status():
    """Determines the simple status: Ready or Error."""
    try:
        with open(LOG_PATH, "r") as f:
            for line in f:
                if "ERROR" in line.upper() or "CRITICAL" in line.upper():
                    # Check if the error is recent (e.g., in the last 5 minutes)
                    log_time_str = line.split(' - ')[0]
                    log_time = datetime.strptime(log_time_str, '%Y-%m-%d %H:%M:%S,%f')
                    if datetime.now() - log_time < timedelta(minutes=5):
                        return "Error", "A recent error was detected in the logs."
        return "Ready", "System is online and waiting for calls."
    except FileNotFoundError:
        return "Ready", "System is online and waiting for calls."
    except Exception:
        return "Error", "Could not read log file to determine status." 
def get_last_n_calls(n=3):
    """Parses the log file to get the last N handled calls."""
    all_events = parse_log_for_timeline()
    # Filter for events that represent a call being handled
    call_events = [e for e in all_events if e['title'] == "Webhook: Emergency Triggered"]
    return call_events[:n]

def parse_log_for_timeline():
    events = []
    error_keywords = ['error', 'failed', 'critical', 'warning', 'unavailable', 'unable']
    title_map = {
        "NEW WEBHOOK RECEIVED": "Webhook: Emergency Triggered",
        "INCOMING TWILIO CALL": "Telephony: Incoming Call",
        "INCOMING SMS": "SMS: Status Request",
        "TRANSFER STATUS UPDATE": "Telephony: Call Transfer Update",
        "AUTOMATED CALL STATUS UPDATE": "Telephony: Outbound Call Update",
        "ERRORS RESOLVED": "System: Logs Cleared"
    }
    try:
        with open(LOG_PATH, "r") as f:
            log_content = f.read()
        log_blocks = re.split(r'\n--- (.*?) ---\n', log_content)
        for i in range(1, len(log_blocks), 2):
            raw_title = log_blocks[i].strip()
            block_content = log_blocks[i+1].strip()
            
            match = re.search(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', block_content, re.MULTILINE)
            if not match: continue

            dt_object = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
            timestamp_12hr = dt_object.strftime('%b %d, %I:%M:%S %p')

            icon = "📄"
            if "WEBHOOK" in raw_title: icon = "🔗"
            if "INCOMING" in raw_title: icon = "📞"
            if "TRANSFER" in raw_title: icon = "↪️"
            if "AUTOMATED" in raw_title: icon = "🔔"
            if "SMS" in raw_title: icon = "💬"
            if "RESOLVED" in raw_title: icon = "✅"

            status = "success"
            if any(keyword in block_content.lower() for keyword in error_keywords):
                status = "error"

            events.append({
                "title": title_map.get(raw_title, raw_title.replace("UPDATE", "").strip()),
                "timestamp": timestamp_12hr,
                "icon": icon,
                "details": block_content,
                "status": status,
                "raw_timestamp": dt_object
            })
    except FileNotFoundError:
        events.append({"title": "Log file not found", "timestamp": datetime.now().strftime('%b %d, %I:%M:%S %p'), "icon": "❓", "details": "The app.log file will be created on the first event.", "status": "success", "raw_timestamp": datetime.now()})
    except Exception as e:
        events.append({"title": "Error parsing log", "timestamp": datetime.now().strftime('%b %d, %I:%M:%S %p'), "icon": "⚠️", "details": str(e), "status": "error", "raw_timestamp": datetime.now()})

    return sorted(events, key=lambda x: x['raw_timestamp'], reverse=True)


# --- Emergency Logic Functions ---
def set_automated_call_active(call_sid):
    global active_automated_call
    with automated_call_lock:
        active_automated_call = call_sid

def clear_automated_call():
    global active_automated_call
    with automated_call_lock:
        active_automated_call = None

def is_automated_call_active():
    with automated_call_lock:
        return active_automated_call is not None

def add_waiting_call(call_sid):
    with waiting_calls_lock:
        if call_sid not in waiting_calls:
            waiting_calls.append(call_sid)

def get_next_waiting_call():
    with waiting_calls_lock:
        return waiting_calls.pop(0) if waiting_calls else None

def update_chosen_phone(number):
    global latest_chosen_phone
    with latest_phone_lock:
        latest_chosen_phone = number

def get_current_phone():
    with latest_phone_lock:
        return latest_chosen_phone

def store_emergency_data(data):
    global emergency_data
    with emergency_data_lock:
        emergency_data = data

def update_call_status(call_type, status):
    with call_status_lock:
        call_statuses[call_type]['status'] = status
        call_statuses[call_type]['timestamp'] = datetime.now()

def get_transfer_attempts(call_sid):
    with transfer_attempts_lock:
        return transfer_attempts.get(call_sid, 0)

def increment_transfer_attempts(call_sid):
    with transfer_attempts_lock:
        transfer_attempts[call_sid] = transfer_attempts.get(call_sid, 0) + 1
    return transfer_attempts[call_sid]

def log_request_details(req):
    try:
        log_message = f"Request Details: {req.method} {req.url}\n"
        log_message += f"From: {req.remote_addr}\nHeaders: {dict(req.headers)}\n"
        if req.is_json:
            log_message += f"JSON Data: {req.get_json()}\n"
        log_message += f"Form Data: {dict(req.form)}\nQuery Params: {dict(req.args)}"
        logging.info(log_message)
    except Exception as e:
        logging.debug(f"Failed to log request details: {e}")

# --- Formatting and Helper Functions ---

def add_pauses_to_number(text):
    """Adds periods between characters to create pauses for TTS."""
    return '. '.join(list(text)) + '.'

def format_emergency_message(data):
    """Creates the detailed voice message for the emergency call."""
    try:
        target_number = get_current_phone()
        target_name = KNOWN_CONTACTS.get(target_number, "maintenance team")
        
        message_parts = [f"This is an emergency call from Axiom Property Management for {target_name}."]

        if data.get('customer_name'):
            message_parts.append(f"The customer's name is {data['customer_name']}.")
        
        if data.get('incident_address'):
            message_parts.append(f"The address is {data['incident_address']}.")

        if data.get('user_stated_callback_number'):
            message_parts.append(f"The callback number is {add_pauses_to_number(data['user_stated_callback_number'])}.")

        if data.get('emergency_description_text'):
            message_parts.append(f"The description of the emergency is: {data['emergency_description_text']}.")
        
        message_parts.append("This information will also be available in a text message.")

        full_message = ' '.join(message_parts)
        return full_message

    except Exception as e:
        logging.error(f"Error formatting emergency message: {e}")
        return "Emergency notification. Critical data was missing or an error occurred."

def format_emergency_sms(data):
    try:
        target_number = get_current_phone()
        target_name = KNOWN_CONTACTS.get(target_number, "Maintenance Team")
        return (
            f"❗Emergency Alert❗ from Axiom Property Management\nTo: {target_name}\n\n"
            f"Customer: {data.get('customer_name', 'N/A')}\nCallback: {data.get('user_stated_callback_number', 'N/A')}\n"
            f"Address: {data.get('incident_address', 'N/A')}\n\nEmergency Details:\n{data.get('emergency_description_text', 'N/A')}"
        )
    except KeyError as e:
        logging.error(f"Missing field for SMS: {e}")
        return "Emergency Alert - Details unavailable"

def format_final_email():
    if not emergency_data: return None, None
    target_number = get_current_phone()
    target_name = KNOWN_CONTACTS.get(target_number, "Maintenance Team")
    subject = f"❗EMERGENCY ALERT & CALL STATUS❗: Axiom - {target_name}"
    emergency_time = call_statuses['emergency_call']['timestamp']
    transfer_time = call_statuses['transfer_call']['timestamp']
    # Build time strings safely
    if emergency_time:
        try:
            emergency_time_str = emergency_time.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            emergency_time_str = str(emergency_time)
    else:
        emergency_time_str = ''

    if transfer_time:
        try:
            transfer_time_str = transfer_time.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            transfer_time_str = str(transfer_time)
    else:
        transfer_time_str = ''

    body = (
        "EMERGENCY NOTIFICATION & CALL STATUS\n"
        f"Assigned To: {target_name} ({target_number})\n\n"
        f"Customer: {emergency_data.get('customer_name', 'N/A')}\n"
        f"Callback Number: {emergency_data.get('user_stated_callback_number', 'N/A')}\n"
        f"Address: {emergency_data.get('incident_address', 'N/A')}\n\n"
        f"Emergency Description:\n{emergency_data.get('emergency_description_text', 'N/A')}\n\n"
        "CALL STATUS\n"
        f"Emergency Alert Call: {call_statuses['emergency_call']['status'] or 'N/A'}\n"
        f"Time: {emergency_time_str}\n\n"
        f"Transfer Call: {call_statuses['transfer_call']['status'] or 'N/A'}\n"
        f"Time: {transfer_time_str}\n\n"
        f"Original Alert Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    return subject, body

def send_sms_to_all_recipients(client, sms_message):
    recipients_str = os.environ.get('RECIPIENT_PHONES', '')
    if not recipients_str:
        logging.warning("RECIPIENT_PHONES environment variable not set. No SMS recipients to alert.")
        return

    phone_numbers = [p.strip() for p in recipients_str.split(',') if p.strip()]
    
    for phone_number in phone_numbers:
        try:
            client.messages.create(body=sms_message, from_=TWILIO_AUTOMATED_NUMBER, to=phone_number)
            logging.info(f"Sent alert SMS to recipient: {phone_number}")
        except Exception as e:
            logging.error(f"Failed to send SMS to {phone_number}: {e}")

def make_emergency_call(message, data):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        target_number = get_current_phone()
        sms_text = format_emergency_sms(data)
        client.messages.create(body=sms_text, from_=TWILIO_AUTOMATED_NUMBER, to=target_number)
        logging.info(f"Emergency SMS sent to primary target {target_number}")
        send_sms_to_all_recipients(client, sms_text)
        call = client.calls.create(
            twiml=f'<Response><Pause length="2"/><Say>{message}</Say><Hangup /></Response>',
            to=target_number, from_=TWILIO_AUTOMATED_NUMBER,
            status_callback=f"{public_url}/call_status", status_callback_event=['completed']
        )
        set_automated_call_active(call.sid)
        logging.info(f"Emergency call initiated to {target_number}! Call SID: {call.sid}")
        return True
    except Exception as e:
        logging.error(f"Error in emergency notification: {e}")
        return False


# --- Flask Routes ---
@app.route('/status', methods=['GET'])
def status_page():
    status, status_message = get_simple_status()
    last_3_calls = get_last_n_calls(3)

    template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="30">
    <title>System Status</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 40px; background-color: #f0f2f5; }
        .status-box { padding: 20px; border-radius: 12px; color: white; text-align: center; margin-bottom: 30px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .status-box h1 { margin: 0; font-size: 2.5em; }
        .status-box p { margin: 5px 0 0; opacity: 0.9; }
        .status-Ready { background-color: #28a745; }
        .status-In-Use { background-color: #ffc107; color: #333;}
        .status-Error { background-color: #dc3545; }
        .call-history { background-color: #fff; padding: 20px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
        .call-history h2 { margin-top: 0; }
        .call { border-bottom: 1px solid #eee; padding: 15px 0; }
        .call:last-child { border-bottom: none; }
        .call-time { font-weight: bold; margin-bottom: 8px; }
        .call-details { white-space: pre-wrap; font-family: monospace; background-color: #f8f9fa; padding: 10px; border-radius: 6px; }
    </style>
</head>
<body>
    <div class="status-box status-{{ status }}">
        <h1>{{ status }}</h1>
        <p>{{ status_message }}</p>
    </div>

    <div class="call-history">
        <h2>Recent Call History</h2>
        {% for call in last_3_calls %}
            <div class="call">
                <div class="call-time">{{ call.timestamp }}</div>
                <div class="call-details">{{ call.details }}</div>
            </div>
        {% else %}
            <p>No calls have been handled yet.</p>
        {% endfor %}
    </div>
</body>
</html>
    """
    return render_template_string(template, status=status, status_message=status_message, last_3_calls=last_3_calls)

@app.route('/api/status', methods=['GET'])
def api_status():
    status, status_message = get_simple_status()
    return jsonify({"status": status, "message": status_message})

@app.route('/resolve_errors', methods=['POST'])
def resolve_errors():
    log_path = LOG_PATH
    if os.path.exists(log_path):
        archive_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"app.log.resolved.{int(time.time())}")
        try:
            os.rename(log_path, archive_path)
            logging.info(f"--- ERRORS RESOLVED: Log archived to {archive_path} ---")
        except Exception as e:
            logging.error(f"Could not archive log file: {e}")
    return redirect(url_for('status_page'))

@app.route('/webhook', methods=['POST'])
def webhook_listener():
    logging.info("\n--- NEW WEBHOOK RECEIVED ---\n")
    log_request_details(request)
    try:
        data = request.get_json()
        store_emergency_data(data)
        if 'chosen_phone' in data: update_chosen_phone(data['chosen_phone'])
        message = format_emergency_message(data)
        if message: make_emergency_call(message, data)
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logging.error(f"Webhook error: {e}", exc_info=True)
        return jsonify({"status": "error"}), 500

@app.route('/sms_reply', methods=['POST'])
def sms_reply():
    logging.info("\n--- INCOMING SMS ---\n")
    log_request_details(request)
    if MESSAGING_MODULE_LOADED:
        from_number = request.form.get('From')
        send_status_report(from_number)
    else:
        logging.error("Messaging module not loaded. Cannot reply to SMS.")
    return '', 204

@app.route("/incoming_twilio_call", methods=['POST'])
def handle_incoming_twilio_call():
    logging.info("\n--- INCOMING TWILIO CALL ---\n")
    log_request_details(request)
    call_sid = request.values.get('CallSid')
    response = VoiceResponse()

    target_number = get_current_phone()

    if target_number is None:
        response.say("There is no on-call technician currently available. Please try again later.")
        response.hangup()
    elif is_automated_call_active():
        add_waiting_call(call_sid)
        response.say("Please hold while we complete an emergency notification.")
        response.play("http://com.twilio.music.classical.s3.amazonaws.com/BusyStrings.mp3", loop=1)
        response.redirect(url=f"{public_url}/incoming_twilio_call", method='POST')
    else:
        attempts = get_transfer_attempts(call_sid)
        if attempts < MAX_TRANSFER_ATTEMPTS:
            increment_transfer_attempts(call_sid)
            logging.info(f"Attempting transfer {attempts + 1} for {call_sid} to {target_number}")
            dial = Dial(timeout=20, action=f"{public_url}/transfer_status?call_sid={call_sid}", caller_id=TWILIO_TRANSFER_NUMBER)
            dial.number(target_number)
            response.append(dial)
        else:
            logging.warning(f"Max transfer attempts reached for {call_sid}.")
            response.say("We were unable to reach the maintenance team.")
            response.hangup()
            update_call_status('transfer_call', 'max-attempts-reached')
            subject, body = format_final_email()
            if subject and body: send_to_all(subject, body)
    
    return str(response), 200, {'Content-Type': 'application/xml'}

@app.route('/transfer_status', methods=['POST'])
def transfer_status():
    logging.info("\n--- TRANSFER STATUS UPDATE ---\n")
    log_request_details(request)
    status = request.values.get('DialCallStatus')
    call_sid = request.args.get('call_sid')
    update_call_status('transfer_call', status)
    response = VoiceResponse()
    if status == 'completed':
        logging.info(f"Transfer call {call_sid} completed successfully.")
        response.hangup()
    else:
        logging.warning(f"Transfer for {call_sid} not successful (Status: {status}). Retrying.")
        response.redirect(url=f"{public_url}/incoming_twilio_call", method='POST')
    if status == 'completed' or get_transfer_attempts(call_sid) >= MAX_TRANSFER_ATTEMPTS:
        subject, body = format_final_email()
        if subject and body:
            send_to_all(subject, body)
            logging.info("Final status email triggered.")
    return str(response), 200, {'Content-Type': 'application/xml'}

@app.route('/call_status', methods=['POST'])
def call_status():
    logging.info("\n--- AUTOMATED CALL STATUS UPDATE ---\n")
    log_request_details(request)
    call_sid = request.form.get('CallSid')
    status = request.form.get('CallStatus')
    if active_automated_call == call_sid and status == 'completed':
        update_call_status('emergency_call', status)
        logging.info(f"Automated alert call {call_sid} completed.")
        clear_automated_call()
        try:
            client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
            while True:
                waiting_call_sid = get_next_waiting_call()
                if not waiting_call_sid: break
                logging.info(f"Processing waiting call {waiting_call_sid}.")
                client.calls(waiting_call_sid).update(url=f"{public_url}/incoming_twilio_call", method='POST')
        except Exception as e:
            logging.error(f"Error processing waiting calls: {e}", exc_info=True)
    return '', 200

if __name__ == '__main__':
    logging.info("=====================================================")
    logging.info(f"Starting Flask App on http://0.0.0.0:{FLASK_PORT}")
    logging.info(f"Public URL (Set in Twilio): {public_url}")
    logging.info(f"Web Portal: {public_url}/status")
    logging.info(f"Messaging module loaded: {MESSAGING_MODULE_LOADED}")
    logging.info("=====================================================")
    try:
        app.run(host='0.0.0.0', port=FLASK_PORT, debug=False)
    except Exception as e:
        logging.critical(f"Failed to start Flask app: {e}", exc_info=True)
