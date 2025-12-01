// Dashboard JavaScript

// Shared utility: Toggle collapsible sections
function toggleCollapsible(sectionId) {
    const content = document.getElementById(sectionId + '-content');
    const toggle = document.getElementById(sectionId + '-toggle');
    
    if (content.classList.contains('open')) {
        content.classList.remove('open');
        toggle.classList.remove('open');
    } else {
        content.classList.add('open');
        toggle.classList.add('open');
    }
}

function refreshDashboard() {
    window.location.reload();
}

function disableBranch(branchKey, branchName) {
    if (!confirm(`⚠️ WARNING: Are you sure you want to DISABLE the ${branchName} branch?\n\nThis will prevent all emergency calls from being processed for this location.\n\nAn SMS notification will be sent to the administrator.`)) {
        return;
    }
    
    // Second confirmation
    if (!confirm(`FINAL CONFIRMATION: Disable ${branchName} branch?`)) {
        return;
    }
    
    fetch(`/api/branch/${branchKey}/disable`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ confirm: true })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(`✓ ${data.message}\n\nAn SMS notification has been sent.`);
            window.location.reload();
        } else {
            alert(`Error: ${data.error}`);
        }
    })
    .catch(error => {
        alert(`Error: ${error}`);
    });
}

function enableBranch(branchKey, branchName) {
    if (!confirm(`Enable ${branchName} branch?\n\nThis will allow emergency calls to be processed again.`)) {
        return;
    }
    
    fetch(`/api/branch/${branchKey}/enable`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({})
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(`✓ ${data.message}\n\nAn SMS notification has been sent.`);
            window.location.reload();
        } else {
            alert(`Error: ${data.error}`);
        }
    })
    .catch(error => {
        alert(`Error: ${error}`);
    });
}

function restartBranch(branchKey, branchName) {
    if (!confirm(`⚠️ RESTART CONTAINER: Are you sure you want to RESTART the ${branchName} branch container?\n\nThis will temporarily interrupt service for approximately 10-30 seconds while the container restarts.\n\nAny active emergency calls may be affected.\n\nAn SMS notification will be sent to the administrator.`)) {
        return;
    }
    
    // Second confirmation
    if (!confirm(`FINAL CONFIRMATION: Restart ${branchName} container?\n\nThis action cannot be undone.`)) {
        return;
    }
    
    // Show processing message
    alert('Restarting container... Please wait. This may take 10-30 seconds.');
    
    fetch(`/api/branch/${branchKey}/restart`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ confirm: true })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert(`✓ ${data.message}\n\nThe container has been restarted successfully.\n\nAn SMS notification has been sent.`);
            // Wait a moment before reloading to give container time to start
            setTimeout(() => {
                window.location.reload();
            }, 3000);
        } else {
            alert(`Error: ${data.error || data.message}`);
        }
    })
    .catch(error => {
        alert(`Error: ${error}`);
    });
}

function triggerEmergency(event, branchKey, branchName) {
    event.preventDefault();
    
    // Get form data
    const techPhone = document.getElementById('techPhone').value.trim();
    const customerName = document.getElementById('customerName').value.trim();
    const callbackNumber = document.getElementById('callbackNumber').value.trim();
    const address = document.getElementById('address').value.trim();
    const description = document.getElementById('description').value.trim();
    
    // Validation
    if (!techPhone.startsWith('+')) {
        alert('Error: Technician phone must start with + (e.g., +12084039927)');
        return;
    }
    
    if (!callbackNumber.startsWith('+')) {
        alert('Error: Callback number must start with + (e.g., +15551234567)');
        return;
    }
    
    // Confirmation
    if (!confirm(`⚠️ TRIGGER EMERGENCY: Are you sure you want to trigger an emergency on ${branchName} branch?\n\nTechnician ${techPhone} will be notified via SMS and call.\n\nCustomer: ${customerName}\nAddress: ${address}\n\nAn SMS notification will be sent to the administrator.`)) {
        return;
    }
    
    // Show processing message
    const submitButton = event.target.querySelector('button[type="submit"]');
    const originalText = submitButton.textContent;
    submitButton.disabled = true;
    submitButton.textContent = '⏳ Triggering emergency...';
    
    // Prepare payload
    const payload = {
        chosen_phone: techPhone,
        customer_name: customerName,
        user_stated_callback_number: callbackNumber,
        incident_address: address,
        emergency_description_text: description
    };
    
    fetch(`/api/branch/${branchKey}/trigger`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    })
    .then(response => response.json())
    .then(data => {
        submitButton.disabled = false;
        submitButton.textContent = originalText;
        
        if (data.success) {
            alert(`✓ ${data.message}\n\nThe emergency has been triggered successfully.\n\nAn SMS notification has been sent to the administrator.`);
            // Clear the form
            document.getElementById('emergencyForm').reset();
            // Reload the page to show updated status
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            alert(`✗ Failed to trigger emergency:\n${data.error}`);
        }
    })
    .catch(error => {
        submitButton.disabled = false;
        submitButton.textContent = originalText;
        alert(`✗ Error triggering emergency: ${error}`);
    });
}

// Auto-refresh status every 30 seconds
let autoRefreshInterval;

function startAutoRefresh() {
    autoRefreshInterval = setInterval(() => {
        updateBranchStatuses();
    }, 30000); // 30 seconds
}

function updateBranchStatuses() {
    const branchCards = document.querySelectorAll('.branch-card');
    
    branchCards.forEach(card => {
        const branchKey = card.dataset.branch;
        if (!branchKey) return;
        
        fetch(`/api/branch/${branchKey}/status`)
            .then(response => response.json())
            .then(data => {
                // Update status badge
                const statusBadge = card.querySelector('.status-badge');
                if (statusBadge) {
                    statusBadge.className = 'status-badge status-' + (data.online ? 'online' : 'offline');
                    statusBadge.textContent = data.status;
                }
                
                // Update message
                const message = card.querySelector('.branch-message');
                if (message) {
                    message.textContent = data.message;
                }
                
                // Update disabled state
                if (!data.enabled) {
                    card.classList.add('disabled');
                } else {
                    card.classList.remove('disabled');
                }
            })
            .catch(error => {
                console.error(`Error updating ${branchKey}:`, error);
            });
    });
    
    // Update timestamp
    const lastUpdate = document.getElementById('lastUpdate');
    if (lastUpdate) {
        lastUpdate.textContent = new Date().toLocaleString();
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Start auto-refresh if on dashboard
    if (document.querySelector('.branches-grid')) {
        startAutoRefresh();
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
});

// Call Recordings Functions
let currentRecordingsPage = 0;
let isLoadingRecordings = false;

function loadCallRecordings(branchKey, page = 0) {
    if (isLoadingRecordings) return;
    isLoadingRecordings = true;
    
    const recordingsContainer = document.getElementById('recordings-container');
    const loadingIndicator = document.getElementById('recordings-loading');
    const errorMessage = document.getElementById('recordings-error');
    const paginationControls = document.getElementById('recordings-pagination');
    
    // Show loading state
    if (loadingIndicator) loadingIndicator.style.display = 'block';
    if (errorMessage) errorMessage.style.display = 'none';
    
    fetch(`/api/branch/${branchKey}/recordings?page=${page}&page_size=20`)
        .then(response => response.json())
        .then(data => {
            isLoadingRecordings = false;
            if (loadingIndicator) loadingIndicator.style.display = 'none';
            
            if (data.success && data.recordings) {
                currentRecordingsPage = page;
                displayRecordings(data.recordings, recordingsContainer);
                updatePaginationControls(branchKey, page, data.count, paginationControls);
            } else {
                if (errorMessage) {
                    errorMessage.textContent = data.error || 'Failed to load recordings';
                    errorMessage.style.display = 'block';
                }
                if (recordingsContainer) {
                    recordingsContainer.innerHTML = '<p style="text-align: center; color: #666;">No recordings available</p>';
                }
            }
        })
        .catch(error => {
            isLoadingRecordings = false;
            if (loadingIndicator) loadingIndicator.style.display = 'none';
            if (errorMessage) {
                errorMessage.textContent = 'Error loading recordings: ' + error.message;
                errorMessage.style.display = 'block';
            }
            console.error('Error loading recordings:', error);
        });
}

function displayRecordings(recordings, container) {
    if (!container) return;
    
    if (recordings.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #666; padding: 20px;">No call recordings found for this branch</p>';
        return;
    }
    
    let html = '<div class="recordings-list">';
    
    recordings.forEach(recording => {
        const dateCreated = recording.date_created ? new Date(recording.date_created).toLocaleString() : 'Unknown';
        const duration = recording.duration ? `${recording.duration} seconds` : 'N/A';
        
        html += `
            <div class="recording-item" style="background: #f8f9fa; padding: 15px; margin-bottom: 10px; border-radius: 8px; border-left: 4px solid #007bff;">
                <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px;">
                    <div style="flex: 1;">
                        <div style="font-weight: bold; margin-bottom: 5px;">📞 ${recording.from} → ${recording.to}</div>
                        <div style="color: #666; font-size: 0.9em;">
                            <span>📅 ${dateCreated}</span>
                            <span style="margin-left: 15px;">⏱️ ${duration}</span>
                            <span style="margin-left: 15px;">📊 ${recording.status}</span>
                        </div>
                    </div>
                </div>
                <div style="margin-top: 10px;">
                    <audio controls style="width: 100%; max-width: 400px;">
                        <source src="${recording.media_url}" type="audio/mpeg">
                        Your browser does not support the audio element.
                    </audio>
                    <div style="margin-top: 8px;">
                        <a href="${recording.media_url}" download class="btn btn-secondary" style="font-size: 0.85em; padding: 5px 12px; display: inline-block;">
                            ⬇️ Download
                        </a>
                        <span style="margin-left: 10px; color: #999; font-size: 0.85em;">SID: ${recording.sid}</span>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    container.innerHTML = html;
}

function updatePaginationControls(branchKey, currentPage, count, container) {
    if (!container) return;
    
    let html = '<div style="display: flex; gap: 10px; justify-content: center; margin-top: 15px;">';
    
    if (currentPage > 0) {
        html += `<button onclick="loadCallRecordings('${branchKey}', ${currentPage - 1})" class="btn btn-secondary">← Previous</button>`;
    }
    
    html += `<span style="padding: 8px 15px; background: #f8f9fa; border-radius: 4px;">Page ${currentPage + 1}</span>`;
    
    if (count >= 20) {
        html += `<button onclick="loadCallRecordings('${branchKey}', ${currentPage + 1})" class="btn btn-secondary">Next →</button>`;
    }
    
    html += '</div>';
    container.innerHTML = html;
}
