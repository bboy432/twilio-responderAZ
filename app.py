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

# Docker-friendly log path (inside container)
LOG_PATH = "/app/logs/app.log"

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
    # Early failure - logging may not be configured yet. Print so container logs show it.
    print(f"Could not import from messages.py, status replies will be disabled. Error: {e}")


# Helper function for debug webhooks
def send_debug(event_type, data=None):
    if not DEBUG_WEBHOOK_URL:
        # Still persist to local log even if no webhook is configured
        pass
    payload = {
        "event": event_type,
        "timestamp": datetime.now().isoformat(),
        "data": data or {}
    }

    # Print to stdout for Docker/Portainer logs (makes debugging much easier)
    # Only print error-related events to avoid log spam
    error_events = ['emergency_call_validation_error', 'emergency_call_config_error', 
                    'sms_send_error', 'call_initiation_error', 'webhook_call_failed',
                    'webhook_validation_error', 'webhook_processing_error', 'emergency_call_error',
                    'config_load_error', 'connect_config_error', 'connect_failure']
    if event_type in error_events:
        try:
            print(f"[ERROR] {event_type}: {json.dumps(data, default=str)}", flush=True)
        except Exception:
            print(f"[ERROR] {event_type}", flush=True)

    # Post to configured debug webhook if available
    try:
        if DEBUG_WEBHOOK_URL:
            requests.post(DEBUG_WEBHOOK_URL, json=payload, timeout=5)
    except Exception:
        # Don't raise for webhook delivery failures
        pass

    # Also append a structured block to the local app log so /debug_firehose can read it
    try:
        log_dir = os.path.dirname(LOG_PATH)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        # Build a block matching the parse_log_for_timeline delimiter
        block_title = event_type.upper()
        timestamp_line = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        block_content = json.dumps(payload, default=str, ensure_ascii=False, indent=2)
        with open(LOG_PATH, 'a', encoding='utf-8') as lf:
            lf.write(f"\n--- {block_title} ---\n")
            lf.write(f"{timestamp_line} - {block_content}\n")
    except Exception as e:
        # As a last resort, ensure logging doesn't interrupt the app
        try:
            print(f"Failed to write debug log: {e}")
        except:
            pass

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
    RECIPIENT_EMAILS = os.environ.get('RECIPIENT_EMAILS', '')
    DEBUG_WEBHOOK_URL = os.environ.get('DEBUG_WEBHOOK_URL', '')
    BRANCH_NAME = os.environ.get('BRANCH_NAME', 'default')
    ADMIN_DASHBOARD_URL = os.environ.get('ADMIN_DASHBOARD_URL', 'http://admin-dashboard:5000')
    
    # Debug line to check if RECIPIENT_PHONES is being loaded
    send_debug("env_debug", {"RECIPIENT_PHONES": os.environ.get('RECIPIENT_PHONES'), "BRANCH_NAME": BRANCH_NAME})

    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, TWILIO_AUTOMATED_NUMBER, TWILIO_TRANSFER_NUMBER, TRANSFER_TARGET_PHONE_NUMBER, PUBLIC_URL, FLASK_PORT]):
        raise ValueError("One or more required environment variables are missing.")

except Exception as e:
    # Critical config load failure - print and send webhook
    print(f"CRITICAL ERROR: Could not load configuration from environment variables: {e}")
    send_debug("config_load_error", {"error": str(e)})
    exit()


# Global settings cache
_settings_cache = {}
_settings_last_updated = None


def load_settings_from_admin():
    """Load settings from the admin dashboard database"""
    global _settings_cache, _settings_last_updated
    
    try:
        # Try to fetch settings from admin dashboard
        response = requests.get(f"{ADMIN_DASHBOARD_URL}/api/internal/branch/{BRANCH_NAME}/settings", timeout=5)
        if response.status_code == 200:
            settings = response.json()
            _settings_cache = settings
            _settings_last_updated = datetime.now()
            send_debug("settings_loaded_from_admin", {"branch": BRANCH_NAME, "keys": list(settings.keys())})
            return settings
    except Exception as e:
        send_debug("settings_load_error", {"error": str(e), "using_env_vars": True})
    
    # Fallback to environment variables
    return None


def get_setting(key, default=''):
    """Get a setting value, checking cache first, then environment variables"""
    global _settings_cache, _settings_last_updated
    
    # Refresh cache every 5 minutes
    if _settings_last_updated is None or (datetime.now() - _settings_last_updated).seconds > 300:
        load_settings_from_admin()
    
    # Check cache first
    if _settings_cache and key in _settings_cache:
        return _settings_cache[key]
    
    # Fallback to environment variable
    return os.environ.get(key, default)


def get_twilio_client():
    """Get Twilio client with current settings"""
    account_sid = get_setting('TWILIO_ACCOUNT_SID', TWILIO_ACCOUNT_SID)
    auth_token = get_setting('TWILIO_AUTH_TOKEN', TWILIO_AUTH_TOKEN)
    return Client(account_sid, auth_token)


# Initialize settings on startup
load_settings_from_admin()

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
        send_debug("email_skipped", {"reason": "RECIPIENT_EMAILS not set"})
        return

    # Note: Email sending is currently simulated. 
    # To enable actual email delivery, configure an SMTP server or email service.
    send_debug("email_notification", {"recipients": email_recipients, "subject": subject, "body": body, "note": "Email logging enabled - actual delivery not configured"})

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
        send_debug("network_info_error", {"error": str(e)})
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
                    # Only process lines that start with a valid timestamp
                    log_time_str = line.split(' - ')[0]
                    try:
                        log_time = datetime.strptime(log_time_str, '%Y-%m-%d %H:%M:%S,%f')
                    except ValueError:
                        try:
                            log_time = datetime.strptime(log_time_str, '%Y-%m-%d %H:%M:%S')
                        except ValueError:
                            # Skip lines that don't have a valid timestamp
                            continue
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

            # Parse timestamp - handle both with and without milliseconds
            try:
                dt_object = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S,%f')
            except ValueError:
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
        send_debug("request_details", {"details": log_message})
    except Exception as e:
        send_debug("request_log_failed", {"error": str(e)})

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
        send_debug("format_message_error", {"error": str(e)})
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
        send_debug("format_sms_keyerror", {"error": str(e)})
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
    recipients_str = get_setting('RECIPIENT_PHONES', os.environ.get('RECIPIENT_PHONES', ''))
    
    send_debug("sms_attempt", {
        "recipients_from_env": recipients_str,
        "twilio_number": get_setting('TWILIO_AUTOMATED_NUMBER', TWILIO_AUTOMATED_NUMBER),
        "message": sms_message
    })
    
    if not recipients_str:
        send_debug("sms_recipients_not_set", {"message": "RECIPIENT_PHONES not set"})
        return

    phone_numbers = [p.strip() for p in recipients_str.split(',') if p.strip()]
    
    automated_number = get_setting('TWILIO_AUTOMATED_NUMBER', TWILIO_AUTOMATED_NUMBER)
    
    for phone_number in phone_numbers:
        try:
            if not phone_number.startswith('+'):
                phone_number = '+' + phone_number
                send_debug("number_formatted", {"number": phone_number})
            
            message = client.messages.create(body=sms_message, from_=automated_number, to=phone_number)
            send_debug("sms_sent", {"to": phone_number, "sid": message.sid})
        except Exception as e:
            send_debug("sms_error", {"to": phone_number, "error": str(e)})

def make_emergency_call(emergency_id, emergency_data):
    """Initiates the detailed call to the technician."""
    send_debug("emergency_call_start", {
        "emergency_id": emergency_id,
        "emergency_data": emergency_data
    })
    try:
        # Validate required configuration
        technician_number = emergency_data.get('technician_number')
        if not technician_number:
            error_msg = "Technician number is missing from emergency data"
            send_debug("emergency_call_validation_error", {"error": error_msg})
            return False, error_msg
        
        if not technician_number.startswith('+'):
            error_msg = f"Invalid technician number format (missing country code): {technician_number}"
            send_debug("emergency_call_validation_error", {"error": error_msg})
            return False, error_msg
        
        # Get Twilio configuration
        account_sid = get_setting('TWILIO_ACCOUNT_SID', TWILIO_ACCOUNT_SID)
        auth_token = get_setting('TWILIO_AUTH_TOKEN', TWILIO_AUTH_TOKEN)
        automated_number = get_setting('TWILIO_AUTOMATED_NUMBER', TWILIO_AUTOMATED_NUMBER)
        
        # Validate Twilio configuration
        if not account_sid or not auth_token:
            error_msg = "Twilio credentials (ACCOUNT_SID or AUTH_TOKEN) are not configured"
            send_debug("emergency_call_config_error", {"error": error_msg})
            return False, error_msg
        
        if not automated_number:
            error_msg = "TWILIO_AUTOMATED_NUMBER is not configured"
            send_debug("emergency_call_config_error", {"error": error_msg})
            return False, error_msg
        
        if not automated_number.startswith('+'):
            error_msg = f"Invalid automated number format (missing country code): {automated_number}"
            send_debug("emergency_call_config_error", {"error": error_msg})
            return False, error_msg
        
        client = get_twilio_client()
        send_debug("twilio_client_created", {"technician_number": technician_number})
        
        # Send SMS
        sms_text = format_emergency_sms(emergency_data)
        try:
            sms_message = client.messages.create(body=sms_text, from_=automated_number, to=technician_number)
            send_debug("primary_sms_sent", {"to": technician_number, "sid": sms_message.sid})
        except Exception as sms_error:
            error_msg = f"Failed to send SMS: {str(sms_error)}"
            send_debug("sms_send_error", {"error": error_msg, "to": technician_number})
            # Continue with call even if SMS fails
        
        send_sms_to_all_recipients(client, sms_text)

        # Make call
        message = format_emergency_message(emergency_data)
        try:
            call = client.calls.create(
                twiml=f'<Response><Pause length="2"/><Say>{message}</Say><Hangup /></Response>',
                to=technician_number, from_=automated_number,
                status_callback=f"{public_url}/technician_call_ended?emergency_id={emergency_id}",
                status_callback_event=['completed']
            )
            
            send_debug("emergency_call_initiated", {"to": technician_number, "call_sid": call.sid})
            update_active_emergency('technician_call_sid', call.sid)
            return True, "Call initiated successfully"
        except Exception as call_error:
            error_msg = f"Failed to initiate call: {str(call_error)}"
            send_debug("call_initiation_error", {"error": error_msg, "to": technician_number})
            return False, error_msg
            
    except Exception as e:
        error_msg = f"Unexpected error in make_emergency_call: {str(e)}"
        send_debug("emergency_call_error", {"error": error_msg, "type": str(type(e))})
        return False, error_msg



# --- Flask Routes ---
@app.route('/status', methods=['GET'])
def status_page():
    status, status_message = get_simple_status()
    last_3_calls = get_last_n_calls(3)
    # Replace spaces with hyphens in status for CSS class name
    status_class = status.replace(' ', '-')

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
    <div class="status-box status-{{ status_class }}">
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
    return render_template_string(template, status=status, status_class=status_class, status_message=status_message, last_3_calls=last_3_calls)

@app.route('/api/status', methods=['GET'])
def api_status():
    status, status_message = get_simple_status()
    return jsonify({"status": status, "message": status_message})


@app.route('/api/reload_settings', methods=['POST'])
def reload_settings():
    """Reload settings from admin dashboard"""
    try:
        settings = load_settings_from_admin()
        if settings:
            return jsonify({"status": "success", "message": "Settings reloaded successfully", "keys": list(settings.keys())}), 200
        else:
            return jsonify({"status": "success", "message": "Using environment variables"}), 200
    except Exception as e:
        # Log the full error internally but don't expose to external users
        send_debug("settings_reload_error", {"error": str(e)})
        return jsonify({"status": "error", "message": "Failed to reload settings"}), 500

@app.route('/api/logs', methods=['GET'])
def api_logs():
    """Returns logs from the application.
    
    Query parameters:
    - all: Returns all logs (no parameter value needed, just ?all)
    - recent: Returns recent N entries (e.g., ?recent=10)
    
    Returns JSON with timeline events or raw log content.
    """
    try:
        # Parse query parameters
        if 'all' in request.args:
            # Return all parsed timeline events
            timeline = parse_log_for_timeline()
            return jsonify({
                "status": "success",
                "count": len(timeline),
                "logs": timeline
            }), 200
        
        elif 'recent' in request.args:
            # Return recent N entries
            try:
                count = int(request.args.get('recent', 10))
                if count <= 0:
                    return jsonify({"status": "error", "message": "recent parameter must be a positive integer"}), 400
            except ValueError:
                return jsonify({"status": "error", "message": "recent parameter must be a valid integer"}), 400
            
            timeline = parse_log_for_timeline()
            recent_logs = timeline[:count]  # Already sorted by most recent first
            
            return jsonify({
                "status": "success",
                "count": len(recent_logs),
                "requested": count,
                "logs": recent_logs
            }), 200
        
        else:
            # No parameters provided - return usage info
            return jsonify({
                "status": "error",
                "message": "Missing query parameter. Use ?all or ?recent=N",
                "examples": [
                    "/api/logs?all - Returns all log entries",
                    "/api/logs?recent=10 - Returns 10 most recent log entries"
                ]
            }), 400
            
    except FileNotFoundError:
        return jsonify({
            "status": "error",
            "message": "Log file not found. Logs will be created when events occur."
        }), 404
    except Exception as e:
        send_debug("api_logs_error", {"error": str(e)})
        return jsonify({
            "status": "error",
            "message": "An error occurred while retrieving logs"
        }), 500


@app.route('/resolve_errors', methods=['POST'])
def resolve_errors():
    log_path = LOG_PATH
    if os.path.exists(log_path):
        archive_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), f"app.log.resolved.{int(time.time())}")
        try:
            os.rename(log_path, archive_path)
            send_debug("errors_resolved", {"archive_path": archive_path})
        except Exception as e:
            send_debug("archive_error", {"error": str(e)})
    return redirect(url_for('status_page'))


@app.route('/debug_firehose', methods=['POST', 'GET'])
def debug_firehose():
    """Posts a log dump and parsed timeline to a webhook URL.

    Usage:
      /debug_firehose?webhook_url=<url>
    or set DEBUG_WEBHOOK_URL in the environment and call /debug_firehose

    The handler will post a JSON payload with:
      - timeline: parsed event list (from parse_log_for_timeline)
      - raw_log: truncated raw log (first ~100KB)
      - metadata: environment and timestamp
    """
    # Accept either explicit webhook_url param or the configured DEBUG_WEBHOOK_URL
    target = request.args.get('webhook_url') or request.args.get('webhook') or DEBUG_WEBHOOK_URL
    if not target:
        return jsonify({"error": "No webhook URL configured. Set DEBUG_WEBHOOK_URL or pass webhook_url param."}), 400

    # Read & parse logs
    timeline = parse_log_for_timeline()
    raw_log = ''
    try:
        with open(LOG_PATH, 'r', encoding='utf-8', errors='replace') as f:
            raw_log = f.read()
    except FileNotFoundError:
        raw_log = ''
    except Exception as e:
        raw_log = f"Error reading log: {e}"

    # Truncate raw log to avoid huge payloads (100KB)
    MAX_BYTES = 100 * 1024
    raw_log_snippet = raw_log[:MAX_BYTES]

    # Ensure timeline is JSON-serializable (convert datetime objects)
    serializable_timeline = []
    for ev in timeline:
        ev_copy = ev.copy()
        if isinstance(ev_copy.get('raw_timestamp'), datetime):
            ev_copy['raw_timestamp'] = ev_copy['raw_timestamp'].isoformat()
        serializable_timeline.append(ev_copy)

    payload = {
        "event": "debug_firehose_log_dump",
        "timestamp": datetime.now().isoformat(),
        "metadata": {
            "hostname": socket.gethostname(),
            "public_url": public_url
        },
        "timeline": serializable_timeline,
        "raw_log_snippet": raw_log_snippet
    }

    results = []
    try:
        r = requests.post(target, json=payload, timeout=20)
        results.append({"posted_to": target, "status_code": getattr(r, 'status_code', None)})
    except Exception as e:
        results.append({"posted_to": target, "error": str(e)})

    return jsonify({"target": target, "results": results, "timeline_count": len(timeline)})

@app.route('/webhook', methods=['POST'])
def webhook_listener():
    """Starts the emergency workflow."""
    send_debug("webhook_received", {"method": request.method, "url": request.url})
    log_request_details(request)
    send_debug("webhook_state_check", {})
    if get_active_emergency():
        current_emergency = get_active_emergency()
        send_debug("webhook_while_active", {"active_emergency": current_emergency})
        return jsonify({"status": "error", "message": "System is busy."}), 503

    try:
        data = request.get_json()
        
        # Validate request data
        if not data:
            send_debug("webhook_validation_error", {"error": "No JSON data received"})
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        if not data.get('chosen_phone'):
            send_debug("webhook_validation_error", {"error": "Missing chosen_phone"})
            return jsonify({"status": "error", "message": "Missing required field: chosen_phone"}), 400
        
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

        # Attempt to make the emergency call
        success, message = make_emergency_call(emergency_id, emergency_data)
        
        if not success:
            # Call failed, clear the emergency state and return error
            clear_active_emergency()
            send_debug("webhook_call_failed", {"emergency_id": emergency_id, "error": message})
            # Don't expose detailed error messages to external users for security
            return jsonify({"status": "error", "message": "Failed to initiate emergency call. Please check configuration and try again."}), 500
        
        return jsonify({"status": "success", "message": "Emergency call initiated successfully"}), 200

    except Exception as e:
        # Make sure to clear emergency state on any error
        clear_active_emergency()
        send_debug("webhook_processing_error", {"error": str(e)})
        # Don't expose detailed error messages to external users for security
        return jsonify({"status": "error", "message": "An error occurred processing the emergency request."}), 500


@app.route('/sms_reply', methods=['POST'])
def sms_reply():
    send_debug("incoming_sms", {"from": request.form.get('From'), "body": request.form.get('Body')})
    log_request_details(request)
    if MESSAGING_MODULE_LOADED:
        from_number = request.form.get('From')
        send_status_report(from_number)
    else:
        send_debug("messaging_module_missing", {"message": "Messaging module not loaded. Cannot reply to SMS."})
    return '', 204

@app.route("/incoming_twilio_call", methods=['POST'])
def handle_incoming_twilio_call():
    """Handles the incoming call from the customer."""
    send_debug("incoming_call", {
        "from": request.values.get('From'),
        "to": request.values.get('To'),
        "call_sid": request.values.get('CallSid'),
        "call_status": request.values.get('CallStatus')
    })
    
    response = VoiceResponse()
    emergency = get_active_emergency()
    send_debug("emergency_state", {"emergency": emergency})

    if not emergency:
        send_debug("no_active_emergency")
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

        send_debug("customer_queued", {"emergency_id": emergency_id})

        # If technician is ready, connect them right away
        if emergency.get('status') == 'technician_informed':
            connect_technician_to_customer(emergency_id, emergency.get('technician_number'))
            
    except Exception as e:
        send_debug("queue_setup_error", {"error": str(e), "type": str(type(e)), "repr": repr(e)})
        response.say("We apologize, but there was an error connecting your call. Please try again.")
        response.hangup()

    send_debug("incoming_twiml", {"twiml": str(response)})
    return str(response), 200, {'Content-Type': 'application/xml'}


@app.route("/technician_call_ended", methods=['POST'])
def technician_call_ended():
    """Callback for when the initial technician call ends."""
    emergency_id = request.args.get('emergency_id')
    send_debug("technician_call_ended", {
        "emergency_id": emergency_id,
        "call_sid": request.values.get('CallSid'),
        "call_status": request.values.get('CallStatus'),
        "duration": request.values.get('CallDuration'),
        "price": request.values.get('Price')
    })
    
    emergency = get_active_emergency()
    send_debug("emergency_state", {"emergency": emergency})

    if not emergency or emergency.get('id') != emergency_id:
        send_debug("emergency_mismatch", {
            "received_id": emergency_id,
            "active_emergency_id": emergency.get('id') if emergency else None
        })
        return '', 200

    # First, check if a customer is already on hold.
    customer_is_waiting = emergency.get('status') == 'customer_waiting'
    send_debug("customer_waiting_status", {"customer_is_waiting": customer_is_waiting})

    # Now, update the status to show the technician has been informed.
    update_active_emergency('status', 'technician_informed')

    # If a customer was waiting, connect the technician now.
    if customer_is_waiting:
        connect_technician_to_customer(emergency_id, emergency.get('technician_number'))

    return '', 200


def connect_technician_to_customer(emergency_id, technician_number):
    """Makes a new call to the technician and connects them to the waiting customer."""
    try:
        send_debug("connect_tech_start", {
            "emergency_id": emergency_id,
            "technician_number": technician_number,
            "known_contact": KNOWN_CONTACTS.get(technician_number, 'Unknown')
        })
        
        # Get current settings
        account_sid = get_setting('TWILIO_ACCOUNT_SID', TWILIO_ACCOUNT_SID)
        auth_token = get_setting('TWILIO_AUTH_TOKEN', TWILIO_AUTH_TOKEN)
        automated_number = get_setting('TWILIO_AUTOMATED_NUMBER', TWILIO_AUTOMATED_NUMBER)
        
        # Validate configuration
        if not all([account_sid, auth_token, automated_number]):
            send_debug("config_error", {"message": "Missing required Twilio configuration"})
            raise ValueError("Missing required Twilio configuration")
            
        # Validate phone number
        if not technician_number or not technician_number.startswith('+'):
            send_debug("validation_error", {"message": f"Invalid technician number format: {technician_number}"})
            raise ValueError(f"Invalid technician number format: {technician_number}")
            
        client = Client(account_sid, auth_token)
        send_debug("twilio_client_created", {"for": "customer_connection"})
        
        # Create TwiML to connect technician to the queue
        dequeue_twiml = f'''
        <Response>
            <Say>You are being connected to a customer with an emergency.</Say>
            <Dial>
                <Queue>{emergency_id}</Queue>
            </Dial>
        </Response>
        '''
        send_debug("dequeue_twiml", {"twiml": dequeue_twiml})
        
        # Make the call to the technician
        call = client.calls.create(
            twiml=dequeue_twiml,
            to=technician_number,
            from_=automated_number,
            status_callback=f"{public_url}/conference_status?emergency_id={emergency_id}",
            status_callback_event=['completed']
        )
        send_debug("technician_call_initiated", {"call_sid": call.sid})
        return True
        
    except ValueError as ve:
        send_debug("connect_config_error", {"error": str(ve)})
        return False
    except Exception as e:
        send_debug("connect_failure", {"error": str(e), "type": str(type(e)), "repr": repr(e)})
        return False


@app.route("/conference_status", methods=['POST'])
def conference_status():
    """Callback for when the conference ends."""
    emergency_id = request.args.get('emergency_id')
    send_debug("conference_status", {
        "emergency_id": emergency_id,
        "status_event": request.values.get('StatusCallbackEvent'),
        "conference_sid": request.values.get('ConferenceSid'),
        "duration": request.values.get('Duration'),
        "participant_count": request.values.get('ParticipantCount')
    })
    
    emergency = get_active_emergency()
    send_debug("emergency_state", {"emergency": emergency})

    if not emergency or emergency.get('id') != emergency_id:
        send_debug("emergency_mismatch", {
            "received_id": emergency_id,
            "active_emergency_id": emergency.get('id') if emergency else None
        })
        return '', 200

    update_active_emergency('conference_status', request.values.get('StatusCallbackEvent'))
    update_active_emergency('conference_duration', request.values.get('Duration'))

    # Send final email
    subject, body = format_final_email(get_active_emergency())
    if subject and body:
        send_to_all(subject, body)
        send_debug("final_status_email", {"subject": subject})

    # Clean up
    clear_active_emergency()
    send_debug("emergency_concluded", {"emergency_id": emergency_id})

    return '', 200

if __name__ == '__main__':
    print("=====================================================")
    print(f"Starting Flask App on http://0.0.0.0:{FLASK_PORT}")
    print(f"Public URL (Set in Twilio): {public_url}")
    print(f"Web Portal: {public_url}/status")
    print(f"Messaging module loaded: {MESSAGING_MODULE_LOADED}")
    print(f"Detailed logs: {LOG_PATH}")
    print("Note: Error details are printed to stdout and also logged to the file above")
    print("=====================================================")
    send_debug("app_start", {"public_url": public_url, "port": FLASK_PORT, "messaging_loaded": MESSAGING_MODULE_LOADED})
    try:
        app.run(host='0.0.0.0', port=FLASK_PORT, debug=False)
    except Exception as e:
        print(f"Failed to start Flask app: {e}")
        send_debug("app_start_failure", {"error": str(e)})
