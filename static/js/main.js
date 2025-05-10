/**
 * Main JavaScript functionality for automotive diagnostic assistant
 */

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tool tips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
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
    
    // Toggle between camera and voice input
    const inputToggleButtons = document.querySelectorAll('[data-toggle-input]');
    inputToggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const targetInput = this.getAttribute('data-toggle-input');
            
            // Hide all input sections
            document.querySelectorAll('.input-section').forEach(section => {
                section.style.display = 'none';
            });
            
            // Show the selected input section
            document.getElementById(`${targetInput}-section`).style.display = 'block';
            
            // Update active button state
            inputToggleButtons.forEach(btn => {
                btn.classList.remove('active');
            });
            this.classList.add('active');
        });
    });
    
    // Analysis form submission
    const analysisForm = document.getElementById('analysis-form');
    if (analysisForm) {
        analysisForm.addEventListener('submit', function(event) {
            // Show loading indicator
            const submitButton = document.querySelector('#analysis-form button[type="submit"]');
            const originalButtonText = submitButton.innerHTML;
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
            
            // The form will be submitted normally to the server
        });
    }
});

// Expand/collapse repair steps
function toggleRepairSteps(buttonElement) {
    const targetId = buttonElement.getAttribute('data-target');
    const targetElement = document.getElementById(targetId);
    
    if (targetElement.style.display === 'none' || !targetElement.style.display) {
        targetElement.style.display = 'block';
        buttonElement.textContent = 'Hide Steps';
        buttonElement.classList.remove('btn-primary');
        buttonElement.classList.add('btn-secondary');
    } else {
        targetElement.style.display = 'none';
        buttonElement.textContent = 'Show Steps';
        buttonElement.classList.remove('btn-secondary');
        buttonElement.classList.add('btn-primary');
    }
}

// Filter repairs by DIY/Professional
function filterRepairs(filterType) {
    const diySection = document.getElementById('diy-repairs-section');
    const professionalSection = document.getElementById('professional-repairs-section');
    const allButton = document.getElementById('filter-all');
    const diyButton = document.getElementById('filter-diy');
    const profButton = document.getElementById('filter-professional');
    
    // Reset active state on all buttons
    [allButton, diyButton, profButton].forEach(btn => {
        if (btn) btn.classList.remove('active');
    });
    
    if (filterType === 'diy') {
        if (diySection) diySection.style.display = 'block';
        if (professionalSection) professionalSection.style.display = 'none';
        if (diyButton) diyButton.classList.add('active');
    } else if (filterType === 'professional') {
        if (diySection) diySection.style.display = 'none';
        if (professionalSection) professionalSection.style.display = 'block';
        if (profButton) profButton.classList.add('active');
    } else {
        // Show all
        if (diySection) diySection.style.display = 'block';
        if (professionalSection) professionalSection.style.display = 'block';
        if (allButton) allButton.classList.add('active');
    }
}
