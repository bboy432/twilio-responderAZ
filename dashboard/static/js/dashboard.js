// Configuration Management
let config = {
    apiUrl: 'http://localhost:5000'
};

// Load config from localStorage on startup
function loadConfig() {
    const savedConfig = localStorage.getItem('dashboardConfig');
    if (savedConfig) {
        config = JSON.parse(savedConfig);
        document.getElementById('apiUrl').value = config.apiUrl;
    }
}

function saveConfig() {
    const apiUrl = document.getElementById('apiUrl').value.trim();
    if (!apiUrl) {
        showResponse('Error: API URL cannot be empty', 'error');
        return;
    }
    
    // Remove trailing slash if present
    config.apiUrl = apiUrl.replace(/\/$/, '');
    localStorage.setItem('dashboardConfig', JSON.stringify(config));
    showResponse('Configuration saved successfully!', 'success');
}

// Display Response Helper
function showResponse(message, type = 'info') {
    const responseArea = document.getElementById('responseArea');
    const timestamp = new Date().toLocaleString();
    
    let className = '';
    if (type === 'success') className = 'success-message';
    if (type === 'error') className = 'error-message';
    
    const messageElement = document.createElement('div');
    messageElement.className = className;
    messageElement.textContent = `[${timestamp}] ${message}`;
    
    responseArea.innerHTML = '';
    responseArea.appendChild(messageElement);
}

// Status Monitoring
async function refreshStatus() {
    try {
        showResponse('Fetching status...', 'info');
        
        const response = await fetch(`${config.apiUrl}/api/status`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        // Update status display
        const statusText = document.getElementById('statusText');
        const statusMessage = document.getElementById('statusMessage');
        const lastUpdated = document.getElementById('lastUpdated');
        
        statusText.textContent = data.status || 'Unknown';
        statusText.className = `status-text status-${data.status || 'Unknown'}`;
        statusMessage.textContent = data.message || 'No message available';
        lastUpdated.textContent = new Date().toLocaleString();
        
        showResponse(`Status retrieved: ${data.status}`, 'success');
    } catch (error) {
        showResponse(`Error fetching status: ${error.message}`, 'error');
        
        // Update UI to show error state
        const statusText = document.getElementById('statusText');
        const statusMessage = document.getElementById('statusMessage');
        
        statusText.textContent = 'Connection Error';
        statusText.className = 'status-text status-Error';
        statusMessage.textContent = `Could not connect to ${config.apiUrl}`;
    }
}

// Trigger Emergency
async function triggerEmergency() {
    try {
        const techPhone = document.getElementById('techPhone').value.trim();
        const customerName = document.getElementById('customerName').value.trim();
        const callbackNumber = document.getElementById('callbackNumber').value.trim();
        const address = document.getElementById('address').value.trim();
        const description = document.getElementById('description').value.trim();
        
        // Validation
        if (!techPhone || !customerName || !callbackNumber || !address || !description) {
            showResponse('Error: All fields are required', 'error');
            return;
        }
        
        if (!techPhone.startsWith('+')) {
            showResponse('Error: Technician phone must start with + (e.g., +12084039927)', 'error');
            return;
        }
        
        if (!callbackNumber.startsWith('+')) {
            showResponse('Error: Callback number must start with + (e.g., +15551234567)', 'error');
            return;
        }
        
        showResponse('Triggering emergency...', 'info');
        
        const payload = {
            chosen_phone: techPhone,
            customer_name: customerName,
            user_stated_callback_number: callbackNumber,
            incident_address: address,
            emergency_description_text: description
        };
        
        const response = await fetch(`${config.apiUrl}/webhook`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showResponse(`✓ Emergency triggered successfully!\nStatus: ${result.status}`, 'success');
            // Refresh status after triggering
            setTimeout(refreshStatus, 1000);
        } else {
            showResponse(`✗ Failed to trigger emergency:\n${result.message || response.statusText}`, 'error');
        }
    } catch (error) {
        showResponse(`✗ Error triggering emergency: ${error.message}`, 'error');
    }
}

// Debug Webhook
async function sendLogsToWebhook() {
    try {
        const webhookUrl = document.getElementById('webhookUrl').value.trim();
        
        if (!webhookUrl) {
            showResponse('Error: Webhook URL is required', 'error');
            return;
        }
        
        if (!webhookUrl.startsWith('http://') && !webhookUrl.startsWith('https://')) {
            showResponse('Error: Webhook URL must start with http:// or https://', 'error');
            return;
        }
        
        showResponse('Sending logs to webhook...', 'info');
        
        const response = await fetch(`${config.apiUrl}/debug_firehose?webhook_url=${encodeURIComponent(webhookUrl)}`, {
            method: 'GET'
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showResponse(`✓ Logs sent successfully!\nTimeline events: ${result.timeline_count}\nTarget: ${result.target}`, 'success');
        } else {
            showResponse(`✗ Failed to send logs: ${result.error || response.statusText}`, 'error');
        }
    } catch (error) {
        showResponse(`✗ Error sending logs: ${error.message}`, 'error');
    }
}

// Load Timeline
async function loadTimeline() {
    try {
        showResponse('Loading timeline...', 'info');
        
        // Create a temporary webhook to capture the timeline
        // In a production setup, you'd use a proper backend
        // For now, we'll fetch directly from debug_firehose
        
        // First try to get the status page which includes timeline data
        const response = await fetch(`${config.apiUrl}/status`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const html = await response.text();
        
        // Parse the HTML to extract timeline events
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const callElements = doc.querySelectorAll('.call');
        
        const timelineContainer = document.getElementById('timeline');
        timelineContainer.innerHTML = '';
        
        if (callElements.length === 0) {
            timelineContainer.innerHTML = '<p class="placeholder">No recent events found</p>';
            showResponse('No timeline events available', 'info');
            return;
        }
        
        callElements.forEach(callElement => {
            const timeElement = callElement.querySelector('.call-time');
            const detailsElement = callElement.querySelector('.call-details');
            
            if (timeElement && detailsElement) {
                const eventDiv = document.createElement('div');
                eventDiv.className = 'timeline-event';
                
                // Check for errors in the details
                const details = detailsElement.textContent;
                if (details.toLowerCase().includes('error') || details.toLowerCase().includes('failed')) {
                    eventDiv.classList.add('error');
                } else {
                    eventDiv.classList.add('success');
                }
                
                eventDiv.innerHTML = `
                    <div class="event-header">
                        <div class="event-title">
                            <span>📞</span>
                            <span>Emergency Event</span>
                        </div>
                        <div class="event-timestamp">${timeElement.textContent}</div>
                    </div>
                    <div class="event-details">${details}</div>
                `;
                
                timelineContainer.appendChild(eventDiv);
            }
        });
        
        showResponse(`Timeline loaded: ${callElements.length} events`, 'success');
    } catch (error) {
        showResponse(`Error loading timeline: ${error.message}`, 'error');
        document.getElementById('timeline').innerHTML = '<p class="placeholder error-message">Failed to load timeline</p>';
    }
}

// Auto-refresh status
function startAutoRefresh() {
    // Refresh status every 30 seconds
    setInterval(refreshStatus, 30000);
}

// Initialize on page load
window.addEventListener('DOMContentLoaded', () => {
    loadConfig();
    refreshStatus();
    startAutoRefresh();
    
    // Add enter key support for forms
    document.getElementById('apiUrl').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') saveConfig();
    });
    
    document.getElementById('webhookUrl').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendLogsToWebhook();
    });
    
    // Add enter key support for emergency form (except textarea)
    const formInputs = ['techPhone', 'customerName', 'callbackNumber', 'address'];
    formInputs.forEach(id => {
        document.getElementById(id).addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                triggerEmergency();
            }
        });
    });
});
