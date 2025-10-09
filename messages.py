import subprocess
import os
import time
import logging
from datetime import datetime, timedelta
import csv
import sys

try:
    from twilio.rest import Client
    import psutil
except ImportError:
    # If run as a service, it might not have the venv path.
    # This ensures the libraries can be found.
    sys.path.append('/home/server/twilio-server/venv/lib/python3.13/site-packages')
    from twilio.rest import Client
    import psutil

# --- Configuration ---
# ==============================================================================
# S E C U R I T Y   W A R N I N G
# ==============================================================================
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')
# The number that will RECEIVE the startup and status texts
RECIPIENT_NUMBER = "+18017104034"
# ==============================================================================

# Configure logging
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'messages.log')
logging.basicConfig(
    filename=log_file_path,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- System Info Helper Functions ---
def get_cpu_temperature():
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", 'r') as f:
            return f"{int(f.read()) / 1000.0:.1f}°C"
    except: return "N/A"

def get_uptime():
    try:
        uptime_seconds = time.time() - psutil.boot_time()
        uptime_delta = timedelta(seconds=uptime_seconds)
        days = uptime_delta.days
        hours, remainder = divmod(uptime_delta.seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        return f"{days}d {hours}h {minutes}m"
    except: return "N/A"

def get_cpu_history():
    LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cpu_log.csv')
    try:
        with open(LOG_FILE, 'r') as f:
            reader = csv.reader(f); next(reader)
            cpu_data = [float(row[1]) for row in reader]
        if not cpu_data: return "No data", "No data"
        avg_cpu = sum(cpu_data) / len(cpu_data)
        last_hour_data = cpu_data[-12:]
        avg_last_hour = sum(last_hour_data) / len(last_hour_data) if last_hour_data else 0
        return f"{avg_last_hour:.1f}% (1hr)", f"{avg_cpu:.1f}% (All)"
    except: return "No data", "No data"

def get_ip_address():
    try:
        return subprocess.check_output(['hostname', '-I']).decode('utf-8').split()[0]
    except: return "Unknown IP"

# --- Core Messaging Functions ---
def send_startup_sms():
    """Sends a notification that the server has started."""
    ip_address = get_ip_address()
    message_body = f"Server Startup Notification: Online at IP {ip_address}"
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=message_body,
            from_=TWILIO_PHONE_NUMBER,
            to=RECIPIENT_NUMBER
        )
        logging.info(f"Startup SMS sent. SID: {message.sid}")
    except Exception as e:
        logging.error(f"Failed to send startup SMS: {e}")

def send_status_report(from_number):
    """Gathers system stats and sends them as an SMS reply."""
    temp = get_cpu_temperature()
    uptime = get_uptime()
    cpu_now = f"{psutil.cpu_percent(interval=1):.1f}%"
    avg_1hr, avg_all = get_cpu_history()
    mem = psutil.virtual_memory()
    mem_stat = f"{mem.used/1024**2:.0f}/{mem.total/1024**2:.0f}MB ({mem.percent}%)"
    
    reply_body = (
        f"SERVER STATUS\n"
        f"Uptime: {uptime}\n"
        f"Temp: {temp}\n"
        f"CPU Now: {cpu_now}\n"
        f"CPU Avg: {avg_1hr} / {avg_all}\n"
        f"Memory: {mem_stat}"
    )
    
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        client.messages.create(
            from_=TWILIO_PHONE_NUMBER,
            to=from_number,
            body=reply_body
        )
        logging.info(f"Sent status report to {from_number}")
    except Exception as e:
        logging.error(f"Failed to send status report: {e}")


# --- Main execution block for running this script directly ---
if __name__ == '__main__':
    # This allows us to call the script from the command line for startup.
    # Example: python3 messages.py startup
    if len(sys.argv) > 1 and sys.argv[1] == 'startup':
        logging.info("--- Running Startup SMS Script ---")
        send_startup_sms()
        logging.info("--- Script Finished ---")
    else:
        print("This script is intended to be imported or run with the 'startup' argument.")

