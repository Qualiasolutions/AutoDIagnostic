/**
 * OBD2 Diagnostic Pro - Main JavaScript functionality
 */

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize Bootstrap popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Vehicle information form validation
    const vehicleForm = document.getElementById('vehicle-form');
    if (vehicleForm) {
        vehicleForm.addEventListener('submit', function(event) {
            if (!vehicleForm.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            vehicleForm.classList.add('was-validated');
        });
    }
    
    // OBD2 scan form submission
    const scanForm = document.getElementById('obd2-scan-form');
    if (scanForm) {
        scanForm.addEventListener('submit', function(event) {
            // Show loading indicator
            const submitButton = scanForm.querySelector('button[type="submit"]');
            if (submitButton) {
                const originalButtonText = submitButton.innerHTML;
                submitButton.disabled = true;
                submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Scanning...';
            }
        });
    }
    
    // Auto-refresh live data if on live data page
    if (window.location.pathname.includes('live-data')) {
        initializeLiveDataMonitoring();
    }
});

// Initialize live data monitoring
function initializeLiveDataMonitoring() {
    let refreshInterval = null;
    const refreshButton = document.getElementById('refresh-data-btn');
    const autoRefreshCheckbox = document.getElementById('auto-refresh');
    
    // Manual refresh button
    if (refreshButton) {
        refreshButton.addEventListener('click', function() {
            refreshLiveData();
        });
    }
    
    // Auto-refresh toggle
    if (autoRefreshCheckbox) {
        autoRefreshCheckbox.addEventListener('change', function() {
            if (this.checked) {
                // Start auto-refresh every 2 seconds
                refreshInterval = setInterval(refreshLiveData, 2000);
                refreshLiveData(); // Initial refresh
            } else {
                // Stop auto-refresh
                if (refreshInterval) {
                    clearInterval(refreshInterval);
                    refreshInterval = null;
                }
            }
        });
    }
}

// Refresh live sensor data
function refreshLiveData() {
    const loadingIndicator = document.getElementById('data-loading');
    const dataContainer = document.getElementById('sensor-data-container');
    const errorAlert = document.getElementById('data-error');
    
    if (loadingIndicator) loadingIndicator.style.display = 'block';
    if (errorAlert) errorAlert.style.display = 'none';
    
    fetch('/api/obd2/live-data')
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                updateSensorDisplay(data.data);
                updateLastRefreshTime(data.timestamp);
            } else {
                showDataError(data.error || 'Failed to fetch live data');
            }
        })
        .catch(error => {
            console.error('Error fetching live data:', error);
            showDataError('Network error while fetching data');
        })
        .finally(() => {
            if (loadingIndicator) loadingIndicator.style.display = 'none';
        });
}

// Update sensor data display
function updateSensorDisplay(sensorData) {
    const container = document.getElementById('sensor-data-container');
    if (!container) return;
    
    // Clear existing data
    container.innerHTML = '';
    
    // Display each sensor reading
    for (const [sensorName, data] of Object.entries(sensorData)) {
        const sensorCard = createSensorCard(sensorName, data);
        container.appendChild(sensorCard);
    }
}

// Create a sensor data card element
function createSensorCard(name, data) {
    const card = document.createElement('div');
    card.className = 'col-md-4 col-lg-3 mb-3';
    
    card.innerHTML = `
        <div class="card sensor-card">
            <div class="card-body text-center">
                <h6 class="card-title">${name}</h6>
                <div class="sensor-value h4">${data.value} <small class="text-muted">${data.unit}</small></div>
            </div>
        </div>
    `;
    
    return card;
}

// Update last refresh timestamp
function updateLastRefreshTime(timestamp) {
    const timestampElement = document.getElementById('last-refresh');
    if (timestampElement) {
        const date = new Date(timestamp);
        timestampElement.textContent = `Last updated: ${date.toLocaleTimeString()}`;
    }
}

// Show data error message
function showDataError(message) {
    const errorAlert = document.getElementById('data-error');
    if (errorAlert) {
        errorAlert.textContent = message;
        errorAlert.style.display = 'block';
    }
}

// Clear diagnostic trouble codes
function clearDTCs() {
    if (!confirm('Are you sure you want to clear all diagnostic trouble codes? This action cannot be undone.')) {
        return;
    }
    
    const clearButton = document.getElementById('clear-dtcs-btn');
    if (clearButton) {
        clearButton.disabled = true;
        clearButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Clearing...';
    }
    
    fetch('/api/obd2/clear-dtcs', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            alert('Diagnostic trouble codes cleared successfully.');
            // Refresh the page to show updated status
            window.location.reload();
        } else {
            alert('Error clearing DTCs: ' + (data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Error clearing DTCs:', error);
        alert('Network error while clearing DTCs');
    })
    .finally(() => {
        if (clearButton) {
            clearButton.disabled = false;
            clearButton.innerHTML = '<i class="fas fa-eraser me-2"></i>Clear DTCs';
        }
    });
}

// Format numbers for display
function formatNumber(value, decimals = 1) {
    return Number(value).toFixed(decimals);
}

// Format currency for display
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(amount);
}

// Validate form inputs
function validateForm(form) {
    const requiredFields = form.querySelectorAll('[required]');
    let isValid = true;
    
    requiredFields.forEach(field => {
        if (!field.value.trim()) {
            field.classList.add('is-invalid');
            isValid = false;
        } else {
            field.classList.remove('is-invalid');
        }
    });
    
    return isValid;
}
