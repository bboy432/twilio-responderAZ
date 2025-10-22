// Dashboard JavaScript

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
