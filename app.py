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

    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, TWILIO_AUTOMATED_NUMBER, TWILIO_TRANSFER_NUMBER, TRANSFER_TARGET_PHONE_NUMBER, PUBLIC_URL, FLASK_PORT]):
        raise ValueError("One or more required environment variables are missing.")

except Exception as e:
    logging.critical(f"CRITICAL ERROR: Could not load configuration from environment variables: {e}")
    exit()

# --- General Configuration ---

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

# --- Placeholder for send_to_all function ---
try:
    from send_emails import send_to_all
except ImportError:
    logging.warning("Could not import 'send_to_all' from send_emails.py. Email notifications will be skipped.")
    def send_to_all(subject, body):
        logging.error("Email sending is not configured.")
        pass

# --- Global State Management ---
active_automated_call = None
automated_call_lock = threading.Lock()
waiting_calls = []
waiting_calls_lock = threading.Lock()
latest_chosen_phone = TRANSFER_TARGET_PHONE_NUMBER
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

def get_overall_status():
    """Checks recent logs for errors to determine overall status."""
    error_lines = []
    try:
        with open(LOG_PATH, "r") as f:
            for line in f:
                if "ERROR" in line.upper() or "CRITICAL" in line.upper():
                    error_lines.append(line.strip())
        if error_lines:
            return "error", "Errors Detected", error_lines
        
        try:
            result = subprocess.check_output(['systemctl', 'is-active', 'twilio-app.service']).decode('utf-8').strip()
            if result == 'active':
                return "ok", "Running", []
        except:
            pass
            
        return "ok", "Ready", []

    except FileNotFoundError:
        return "ok", "Ready", []
    except Exception as e:
        return "error", f"Log Unreadable: {e}", [str(e)]

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
    with automated_call_lock: active_automated_call = call_sid
def clear_automated_call():
    global active_automated_call
    with automated_call_lock: active_automated_call = None
def is_automated_call_active():
    with automated_call_lock: return active_automated_call is not None
def add_waiting_call(call_sid):
    with waiting_calls_lock:
        if call_sid not in waiting_calls:
            waiting_calls.append(call_sid)
def get_next_waiting_call():
    with waiting_calls_lock: return waiting_calls.pop(0) if waiting_calls else None
def update_chosen_phone(number):
    global latest_chosen_phone
    with latest_phone_lock: latest_chosen_phone = number
def get_current_phone():
    with latest_phone_lock: return latest_chosen_phone
def store_emergency_data(data):
    global emergency_data
    with emergency_data_lock: emergency_data = data
def update_call_status(call_type, status):
    with call_status_lock:
        call_statuses[call_type]['status'] = status
        call_statuses[call_type]['timestamp'] = datetime.now()
def get_transfer_attempts(call_sid):
    with transfer_attempts_lock: return transfer_attempts.get(call_sid, 0)
def increment_transfer_attempts(call_sid):
    with transfer_attempts_lock:
        transfer_attempts[call_sid] = transfer_attempts.get(call_sid, 0) + 1
    return transfer_attempts[call_sid]
def log_request_details(req):
    log_message = f"Request Details: {req.method} {req.url}\n"
    log_message += f"From: {req.remote_addr}\nHeaders: {dict(req.headers)}\n"
    log_message += f"Form Data: {dict(req.form)}\nQuery Params: {dict(req.args)}"
    logging.info(log_message)
def format_emergency_message(data):
    try:
        target_number = get_current_phone()
        target_name = KNOWN_CONTACTS.get(target_number, "maintenance team")
        message = (f"I'm transferring a call from Axiom Property Management after hours service to {target_name}. ")
        return message
    except KeyError as e:
        logging.error(f"Missing required field for emergency message: {e}")
        return "Emergency notification. Critical data missing."
def format_emergency_sms(data):
    try:
        target_number = get_current_phone()
        target_name = KNOWN_CONTACTS.get(target_number, "Maintenance Team")
        return (
            f"❗Emergency Alert❗ from Axiom Property Management\nTo: {target_name}\n\n"
            f"Customer: {data['customer_name']}\nCallback: {data['user_stated_callback_number']}\n"
            f"Address: {data['incident_address']}\n\nEmergency Details:\n{data['emergency_description_text']}"
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
    # Build time strings separately to avoid nested f-string/quote issues
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
    events = parse_log_for_timeline()
    hostname, ip_address = get_network_info()
    overall_status, status_text, error_lines = get_overall_status()
    template = """<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <meta http-equiv="refresh" content="60">
        <title>Server Timeline</title>
        <link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🖥️</text></svg>">
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 0; background-color: #f0f2f5; color: #1c1e21; }
            .container { max-width: 900px; margin: 2em auto; padding: 0 1em; }
            .main-header { padding: 20px; background-color: #fff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 25px; }
            .server-info { display: flex; justify-content: space-between; align-items: center; }
            .server-name { font-size: 24px; font-weight: bold; color: #050505; }
            .server-ip { font-size: 14px; color: #606770; font-family: "SF Mono", "Fira Code", monospace; }
            .status-header { display: flex; align-items: center; margin-top: 10px; }
            .status-header.error-true { cursor: pointer; }
            .status-light { height: 12px; width: 12px; border-radius: 50%; margin-right: 8px; animation: pulse-ok 2s infinite; }
            .status-light.ok { background-color: #31a24c; }
            .status-light.error { background-color: #f02849; animation-name: pulse-error; }
            @keyframes pulse-ok { 0% { box-shadow: 0 0 0 0 rgba(49, 162, 76, 0.4); } 70% { box-shadow: 0 0 0 10px rgba(49, 162, 76, 0); } 100% { box-shadow: 0 0 0 0 rgba(49, 162, 76, 0); } }
            @keyframes pulse-error { 0% { box-shadow: 0 0 0 0 rgba(240, 40, 73, 0.7); } 70% { box-shadow: 0 0 0 10px rgba(240, 40, 73, 0); } 100% { box-shadow: 0 0 0 0 rgba(240, 40, 73, 0); } }
            .status-text { font-size: 14px; font-weight: bold; }
            .status-text.ok { color: #31a24c; }
            .status-text.error { color: #f02849; }
            .timeline { border-left: 3px solid #ccd0d5; padding: 0 0 20px 20px; position: relative;}
            .event { background-color: #fff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; position: relative;}
            .event-summary { padding: 15px; cursor: pointer; display: flex; align-items: center; border-radius: 8px;}
            .event-summary:hover { background-color: #f5f6f7; }
            .event-status-dot { height: 10px; width: 10px; border-radius: 50%; margin-right: 12px; flex-shrink: 0; }
            .event-status-dot.success { background-color: #31a24c; }
            .event-status-dot.error { background-color: #f02849; }
            .event-icon { font-size: 24px; margin-right: 15px; }
            .event-title { font-weight: bold; font-size: 16px; color: #050505;}
            .event-time { font-size: 12px; color: #606770; margin-top: 4px;}
            .event-details { max-height: 0; overflow: hidden; transition: max-height 0.3s ease-out; background-color: #f5f6f7; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px;}
            .event-details.show { max-height: 500px; }
            .event-details pre { margin: 0; padding: 15px; white-space: pre-wrap; word-wrap: break-word; font-family: "SF Mono", "Fira Code", monospace; font-size: 13px; color: #333; }
            .timeline-dot { content: ''; position: absolute; left: -11.5px; top: 25px; height: 20px; width: 20px; background: #fff; border-radius: 50%; border: 3px solid #ccd0d5; }
            .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; overflow: auto; background-color: rgba(0,0,0,0.5); }
            .modal-content { background-color: #fefefe; margin: 10% auto; padding: 20px; border: 1px solid #888; width: 80%; max-width: 700px; border-radius: 8px; }
            .close { color: #aaa; float: right; font-size: 28px; font-weight: bold; }
            .close:hover, .close:focus { color: black; text-decoration: none; cursor: pointer; }
            .modal-content h2 { margin-top: 0; }
            .modal-content pre { background-color: #f5f5f5; border: 1px solid #ddd; padding: 10px; max-height: 300px; overflow-y: auto; }
            .resolve-button { background-color: #1877f2; color: white; padding: 10px 15px; border: none; border-radius: 5px; cursor: pointer; margin-top: 15px; }
            .resolve-button:hover { background-color: #166fe5; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="main-header">
                <div class="server-info">
                    <span class="server-name">{{ hostname }}</span>
                    <span class="server-ip">{{ ip_address }}</span>
                </div>
                <div class="status-header error-{{ overall_status == 'error' }}" id="status-header-clickable">
                    <div class="status-light {{ overall_status }}"></div>
                    <span class="status-text {{ overall_status }}">{{ status_text }}</span>
                </div>
            </div>
            <div id="timeline-view">
                <div class="timeline">
                    {% for event in events %}
                    <div class="event">
                        <div class="timeline-dot"></div>
                        <div class="event-summary">
                            <span class="event-status-dot {{ event.status }}"></span>
                            <span class="event-icon">{{ event.icon }}</span>
                            <div>
                                <div class="event-title">{{ event.title }}</div>
                                <div class="event-time">{{ event.timestamp }}</div>
                            </div>
                        </div>
                        <div class="event-details"><pre>{{ event.details }}</pre></div>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
        <div id="errorModal" class="modal">
          <div class="modal-content">
            <span class="close">&times;</span>
            <h2>Detected Errors</h2>
            <pre id="error-details"></pre>
            <form action="/resolve_errors" method="post" style="text-align: right;">
                <button type="submit" class="resolve-button">Mark as Resolved & Archive Log</button>
            </form>
          </div>
        </div>
        <script>
            document.addEventListener('DOMContentLoaded', function() {
                document.querySelectorAll('.event-summary').forEach(summary => {
                    summary.addEventListener('click', () => { summary.nextElementSibling.classList.toggle('show'); });
                });
                const modal = document.getElementById("errorModal");
                const statusHeader = document.getElementById("status-header-clickable");
                if (statusHeader.classList.contains('error-true')) {
                    statusHeader.onclick = function() {
                        document.getElementById("error-details").textContent = {{ error_lines|tojson }}.join('\n');
                        modal.style.display = "block";
                    }
                }
                document.getElementsByClassName("close")[0].onclick = function() { modal.style.display = "none"; }
                window.onclick = function(event) { if (event.target == modal) { modal.style.display = "none"; } }
            });
        </script>
    </body>
    </html>"""
    return render_template_string(template, events=events, hostname=hostname, ip_address=ip_address, overall_status=overall_status, status_text=status_text, error_lines=error_lines)

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
    if is_automated_call_active():
        add_waiting_call(call_sid)
        response.say("Please hold while we complete an emergency notification.")
        response.play("http://com.twilio.music.classical.s3.amazonaws.com/BusyStrings.mp3", loop=1)
        response.redirect(url=f"{public_url}/incoming_twilio_call", method='POST')
    else:
        attempts = get_transfer_attempts(call_sid)
        if attempts < MAX_TRANSFER_ATTEMPTS:
            increment_transfer_attempts(call_sid)
            target_number = get_current_phone()
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