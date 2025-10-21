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
