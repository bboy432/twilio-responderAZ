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

import uuid

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
# This dictionary will hold the state of the single, active emergency.
# It is keyed by a unique emergency_id.
active_emergency = {}
active_emergency_lock = threading.Lock()


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
    """Determines the simple status: Ready, In Use, or Error."""
    if get_active_emergency():
        return "In Use", "An emergency call is being processed."

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
def get_active_emergency():
    """Safely gets the active emergency data."""
    with active_emergency_lock:
        return active_emergency.copy()

def set_active_emergency(data):
    """Safely sets the active emergency data."""
    with active_emergency_lock:
        global active_emergency
        active_emergency = data

def update_active_emergency(key, value):
    """Safely updates a specific key in the active emergency data."""
    with active_emergency_lock:
        if active_emergency:
            active_emergency[key] = value

def clear_active_emergency():
    """Safely clears the active emergency data."""
    with active_emergency_lock:
        global active_emergency
        active_emergency = {}


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

def format_emergency_message(emergency_data):
    """Creates the detailed voice message for the emergency call."""
    try:
        technician_number = emergency_data.get('technician_number')
        target_name = KNOWN_CONTACTS.get(technician_number, "maintenance team")
        
        message_parts = [f"This is an emergency call from Axiom Property Management for {target_name}."]

        if emergency_data.get('customer_name'):
            message_parts.append(f"The customer's name is {emergency_data['customer_name']}.")
        
        if emergency_data.get('incident_address'):
            message_parts.append(f"The address is {emergency_data['incident_address']}.")

        if emergency_data.get('user_stated_callback_number'):
            message_parts.append(f"The callback number is {add_pauses_to_number(emergency_data['user_stated_callback_number'])}.")

        if emergency_data.get('emergency_description_text'):
            message_parts.append(f"The description of the emergency is: {emergency_data['emergency_description_text']}.")
        
        message_parts.append("This information will also be available in a text message.")

        full_message = ' '.join(message_parts)
        return full_message

    except Exception as e:
        logging.error(f"Error formatting emergency message: {e}")
        return "Emergency notification. Critical data was missing or an error occurred."

def format_emergency_sms(emergency_data):
    try:
        technician_number = emergency_data.get('technician_number')
        target_name = KNOWN_CONTACTS.get(technician_number, "Maintenance Team")
        return (
            f"❗Emergency Alert❗ from Axiom Property Management\nTo: {target_name}\n\n"
            f"Customer: {emergency_data.get('customer_name', 'N/A')}\nCallback: {emergency_data.get('user_stated_callback_number', 'N/A')}\n"
            f"Address: {emergency_data.get('incident_address', 'N/A')}\n\nEmergency Details:\n{emergency_data.get('emergency_description_text', 'N/A')}"
        )
    except KeyError as e:
        logging.error(f"Missing field for SMS: {e}")
        return "Emergency Alert - Details unavailable"

def format_final_email(emergency_data):
    if not emergency_data: return None, None
    technician_number = emergency_data.get('technician_number')
    target_name = KNOWN_CONTACTS.get(technician_number, "Maintenance Team")
    subject = f"❗EMERGENCY ALERT & CALL STATUS❗: Axiom - {target_name}"
    
    body = (
        "EMERGENCY NOTIFICATION & CALL STATUS\n"
        f"Assigned To: {target_name} ({technician_number})\n\n"
        f"Customer: {emergency_data.get('customer_name', 'N/A')}\n"
        f"Callback Number: {emergency_data.get('user_stated_callback_number', 'N/A')}\n"
        f"Address: {emergency_data.get('incident_address', 'N/A')}\n\n"
        f"Emergency Description:\n{emergency_data.get('emergency_description_text', 'N/A')}\n\n"
        f"Call Status: {emergency_data.get('conference_status', 'N/A')}\n"
        f"Call Duration: {emergency_data.get('conference_duration', 'N/A')} seconds\n\n"
        f"Original Alert Time: {emergency_data.get('timestamp', datetime.now()).strftime('%Y-%m-%d %H:%M:%S')}"
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

def make_emergency_call(emergency_id, emergency_data):
    """Initiates the detailed call to the technician."""
    logging.info(f"\n--- INITIATING EMERGENCY CALL ---\nEmergency ID: {emergency_id}\nData: {json.dumps(emergency_data, default=str, indent=2)}")
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        technician_number = emergency_data.get('technician_number')
        logging.info(f"Creating Twilio client for emergency call to: {technician_number}")
        
        # Send SMS
        sms_text = format_emergency_sms(emergency_data)
        client.messages.create(body=sms_text, from_=TWILIO_AUTOMATED_NUMBER, to=technician_number)
        logging.info(f"Emergency SMS sent to primary target {technician_number}")
        send_sms_to_all_recipients(client, sms_text)

        # Make call
        message = format_emergency_message(emergency_data)
        call = client.calls.create(
            twiml=f'<Response><Pause length="2"/><Say>{message}</Say><Hangup /></Response>',
            to=technician_number, from_=TWILIO_AUTOMATED_NUMBER,
            status_callback=f"{public_url}/technician_call_ended?emergency_id={emergency_id}",
            status_callback_event=['completed']
        )
        
        logging.info(f"Emergency call initiated to {technician_number}! Call SID: {call.sid}")
        update_active_emergency('technician_call_sid', call.sid)
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
    """Starts the emergency workflow."""
    logging.info("\n--- NEW WEBHOOK RECEIVED ---\n")
    log_request_details(request)
    
    logging.info("Checking system state before processing webhook...")
    if get_active_emergency():
        current_emergency = get_active_emergency()
        logging.error(f"Webhook received while emergency is active:\nActive Emergency ID: {current_emergency.get('id')}\nStatus: {current_emergency.get('status')}\nTimestamp: {current_emergency.get('timestamp')}")
        return jsonify({"status": "error", "message": "System is busy."}), 503

    try:
        data = request.get_json()
        emergency_id = str(uuid.uuid4())
        
        emergency_data = {
            "id": emergency_id,
            "timestamp": datetime.now(),
            "status": "informing_technician",
            "technician_number": data.get('chosen_phone'),
            "customer_name": data.get('customer_name'),
            "user_stated_callback_number": data.get('user_stated_callback_number'),
            "incident_address": data.get('incident_address'),
            "emergency_description_text": data.get('emergency_description_text'),
            "customer_call_sid": None,
            "technician_call_sid": None,
            "conference_status": None,
            "conference_duration": None
        }
        set_active_emergency(emergency_data)

        make_emergency_call(emergency_id, emergency_data)
        
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
    """Handles the incoming call from the customer."""
    logging.info("\n--- INCOMING TWILIO CALL ---\n")
    log_request_details(request)
    
    logging.info(f"Call Details:\nFrom: {request.values.get('From')}\nTo: {request.values.get('To')}\nCallSID: {request.values.get('CallSid')}\nCall Status: {request.values.get('CallStatus')}")
    
    response = VoiceResponse()
    emergency = get_active_emergency()
    logging.info(f"Current Emergency State: {json.dumps(emergency, default=str, indent=2)}")

    if not emergency:
        response.say("There is no active emergency. Please hang up.")
        response.hangup()
        return str(response), 200, {'Content-Type': 'application/xml'}

    emergency_id = emergency.get('id')
    update_active_emergency('status', 'customer_waiting')
    update_active_emergency('customer_call_sid', request.values.get('CallSid'))

    try:
        response.say("Please hold while we connect you to the emergency technician.")
        
        # Put the customer in a queue with hold music
        enqueueTwiml = response.enqueue(emergency_id)
        enqueueTwiml.wait_url = "http://com.twilio.music.classical.s3.amazonaws.com/BusyStrings.mp3"
        
        logging.info(f"Customer placed in queue: {emergency_id}")
        
        # If technician is ready, connect them right away
        if emergency.get('status') == 'technician_informed':
            connect_technician_to_customer(emergency_id, emergency.get('technician_number'))
            
    except Exception as e:
        logging.error(f"Error setting up call queue: {str(e)}\nType: {type(e)}\nFull error: {repr(e)}")
        response.say("We apologize, but there was an error connecting your call. Please try again.")
        response.hangup()

    logging.info(f"DEBUG: Generated TwiML for incoming call: {str(response)}")
    return str(response), 200, {'Content-Type': 'application/xml'}


@app.route("/technician_call_ended", methods=['POST'])
def technician_call_ended():
    """Callback for when the initial technician call ends."""
    logging.info("\n--- TECHNICIAN CALL ENDED ---\n")
    log_request_details(request)
    
    emergency_id = request.args.get('emergency_id')
    logging.info(f"Technician Call Details:\nEmergency ID: {emergency_id}\nCall SID: {request.values.get('CallSid')}\nCall Status: {request.values.get('CallStatus')}\nCall Duration: {request.values.get('CallDuration')} seconds\nCall Price: {request.values.get('Price')}")
    
    emergency = get_active_emergency()
    logging.info(f"Current Emergency State:\n{json.dumps(emergency, default=str, indent=2)}")

    if not emergency or emergency.get('id') != emergency_id:
        logging.warning(f"Callback for unknown or mismatched emergency ID: {emergency_id}")
        return '', 200

    # First, check if a customer is already on hold.
    customer_is_waiting = emergency.get('status') == 'customer_waiting'
    logging.info(f"Customer waiting status: {customer_is_waiting}")

    # Now, update the status to show the technician has been informed.
    update_active_emergency('status', 'technician_informed')

    # If a customer was waiting, connect the technician now.
    if customer_is_waiting:
        connect_technician_to_customer(emergency_id, emergency.get('technician_number'))

    return '', 200


def connect_technician_to_customer(emergency_id, technician_number):
    """Makes a new call to the technician and connects them to the waiting customer."""
    try:
        logging.info(f"\n--- CONNECTING TECHNICIAN TO CUSTOMER ---\nEmergency ID: {emergency_id}\nTechnician: {technician_number}\nKnown Contact: {KNOWN_CONTACTS.get(technician_number, 'Unknown')}")
        
        # Validate configuration
        if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_AUTOMATED_NUMBER]):
            raise ValueError("Missing required Twilio configuration")
            
        # Validate phone number
        if not technician_number or not technician_number.startswith('+'):
            raise ValueError(f"Invalid technician number format: {technician_number}")
            
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        logging.info("Successfully created Twilio client for customer connection")
        
        # Create TwiML to connect technician to the queue
        dequeue_twiml = f'''
        <Response>
            <Say>You are being connected to a customer with an emergency.</Say>
            <Dial>
                <Queue>{emergency_id}</Queue>
            </Dial>
        </Response>
        '''
        logging.info(f"Generated dequeue TwiML: {dequeue_twiml}")
        
        # Make the call to the technician
        call = client.calls.create(
            twiml=dequeue_twiml,
            to=technician_number,
            from_=TWILIO_AUTOMATED_NUMBER,
            status_callback=f"{public_url}/call_status?emergency_id={emergency_id}",
            status_callback_event=['completed']
        )
        logging.info(f"Initiated technician call. Call SID: {call.sid}")
        return True
        
    except ValueError as ve:
        logging.error(f"Configuration error in call connection: {ve}")
        return False
    except Exception as e:
        logging.error(f"Failed to connect technician to customer: {str(e)}\nType: {type(e)}\nFull error: {repr(e)}")
        return False
        logging.info(f"Initiated technician conference call. Call SID: {call.sid}")
        return True
        
    except ValueError as ve:
        logging.error(f"Configuration error in conference connection: {ve}")
        return False
    except Exception as e:
        logging.error(f"Failed to connect technician to conference: {str(e)}\nType: {type(e)}\nFull error: {repr(e)}")
        return False


@app.route("/conference_status", methods=['POST'])
def conference_status():
    """Callback for when the conference ends."""
    logging.info("\n--- CONFERENCE STATUS UPDATE ---\n")
    log_request_details(request)
    
    emergency_id = request.args.get('emergency_id')
    logging.info(f"Conference Details:\nEmergency ID: {emergency_id}\nStatus Event: {request.values.get('StatusCallbackEvent')}\nConference SID: {request.values.get('ConferenceSid')}\nDuration: {request.values.get('Duration')} seconds\nParticipant Count: {request.values.get('ParticipantCount')}")
    
    emergency = get_active_emergency()
    logging.info(f"Current Emergency State:\n{json.dumps(emergency, default=str, indent=2)}")

    if not emergency or emergency.get('id') != emergency_id:
        logging.warning(f"Callback for unknown or mismatched emergency ID: {emergency_id}")
        return '', 200

    update_active_emergency('conference_status', request.values.get('StatusCallbackEvent'))
    update_active_emergency('conference_duration', request.values.get('Duration'))

    # Send final email
    subject, body = format_final_email(get_active_emergency())
    if subject and body:
        send_to_all(subject, body)
        logging.info("Final status email triggered.")

    # Clean up
    clear_active_emergency()
    logging.info(f"Emergency {emergency_id} concluded and cleaned up.")

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
