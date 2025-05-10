/**
 * Camera handling functionality for automotive diagnostic assistant
 */

// Global variables for camera and image capture
let videoElement;
let canvasElement;
let captureBtn;
let imagePreview;
let uploadBtn;
let videoStream = null;

// Initialize camera functionality
function initCamera() {
    // Get DOM elements
    videoElement = document.getElementById('video');
    canvasElement = document.getElementById('canvas');
    captureBtn = document.getElementById('capture-btn');
    imagePreview = document.getElementById('image-preview');
    uploadBtn = document.getElementById('upload-btn');
    
    // Camera start/stop buttons
    const startCameraBtn = document.getElementById('start-camera');
    const stopCameraBtn = document.getElementById('stop-camera');
    
    if (startCameraBtn) {
        startCameraBtn.addEventListener('click', startCamera);
    }
    
    if (stopCameraBtn) {
        stopCameraBtn.addEventListener('click', stopCamera);
    }
    
    // Set up capture button
    if (captureBtn) {
        captureBtn.addEventListener('click', captureImage);
    }
    
    // Set up upload button
    if (uploadBtn) {
        uploadBtn.addEventListener('click', uploadImage);
    }
}

// Start the camera
async function startCamera() {
    try {
        // Request access to the camera
        videoStream = await navigator.mediaDevices.getUserMedia({
            video: {
                facingMode: 'environment', // Use rear camera if available
                width: { ideal: 1280 },
                height: { ideal: 720 }
            }
        });
        
        // Show the video stream
        videoElement.srcObject = videoStream;
        videoElement.style.display = 'block';
        
        // Enable capture button
        captureBtn.disabled = false;
        
        // Show guidance
        document.getElementById('camera-guidance').style.display = 'block';
        
        // Hide any previous image preview
        imagePreview.style.display = 'none';
        
        // Update UI to show camera is active
        document.getElementById('camera-status').textContent = 'Camera is active. Position camera to capture the issue.';
        document.getElementById('camera-status').className = 'alert alert-success';
        
        // Toggle button visibility
        document.getElementById('start-camera').style.display = 'none';
        document.getElementById('stop-camera').style.display = 'inline-block';
        
    } catch (error) {
        console.error('Error accessing camera:', error);
        document.getElementById('camera-status').textContent = 'Error accessing camera: ' + error.message;
        document.getElementById('camera-status').className = 'alert alert-danger';
    }
}

// Stop the camera
function stopCamera() {
    if (videoStream) {
        // Stop all video tracks
        videoStream.getTracks().forEach(track => track.stop());
        videoStream = null;
        
        // Hide video element
        videoElement.style.display = 'none';
        videoElement.srcObject = null;
        
        // Disable capture button
        captureBtn.disabled = true;
        
        // Update UI
        document.getElementById('camera-status').textContent = 'Camera stopped.';
        document.getElementById('camera-status').className = 'alert alert-warning';
        
        // Toggle button visibility
        document.getElementById('start-camera').style.display = 'inline-block';
        document.getElementById('stop-camera').style.display = 'none';
        document.getElementById('camera-guidance').style.display = 'none';
    }
}

// Capture an image from the video stream
function captureImage() {
    if (videoStream) {
        // Set canvas dimensions to match video
        canvasElement.width = videoElement.videoWidth;
        canvasElement.height = videoElement.videoHeight;
        
        // Draw the current video frame to the canvas
        const context = canvasElement.getContext('2d');
        context.drawImage(videoElement, 0, 0, canvasElement.width, canvasElement.height);
        
        // Convert canvas to image
        const imageDataUrl = canvasElement.toDataURL('image/jpeg');
        
        // Display the captured image
        imagePreview.src = imageDataUrl;
        imagePreview.style.display = 'block';
        
        // Enable upload button
        uploadBtn.disabled = false;
        
        // Update UI
        document.getElementById('camera-status').textContent = 'Image captured! Click "Analyze Image" to process it.';
        document.getElementById('camera-status').className = 'alert alert-info';
    }
}

// Upload the captured image for analysis
function uploadImage() {
    // Show loading state
    uploadBtn.disabled = true;
    uploadBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
    document.getElementById('camera-status').textContent = 'Analyzing image...';
    
    // Convert data URL to blob
    const imageDataUrl = imagePreview.src;
    const blob = dataURLtoBlob(imageDataUrl);
    
    // Create FormData object
    const formData = new FormData();
    formData.append('image', blob, 'captured-image.jpg');
    
    // Send to server
    fetch('/process-image', {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        // Handle success
        if (data.success) {
            // Update UI with results
            displayImageResults(data.results);
            
            // Update status
            document.getElementById('camera-status').textContent = 'Image analysis complete!';
            document.getElementById('camera-status').className = 'alert alert-success';
            
            // Enable the "Continue" button to proceed to next step
            document.getElementById('continue-btn').style.display = 'block';
        } else {
            // Handle error in results
            document.getElementById('camera-status').textContent = 'Error: ' + (data.error || 'Unknown error');
            document.getElementById('camera-status').className = 'alert alert-danger';
        }
    })
    .catch(error => {
        // Handle network or other errors
        console.error('Error uploading image:', error);
        document.getElementById('camera-status').textContent = 'Error: ' + error.message;
        document.getElementById('camera-status').className = 'alert alert-danger';
    })
    .finally(() => {
        // Reset button state
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = 'Analyze Image';
    });
}

// Display the image analysis results
function displayImageResults(results) {
    const resultsElement = document.getElementById('image-results');
    
    // Clear previous results
    resultsElement.innerHTML = '';
    
    // Check if there are any issues
    if (results.issues && results.issues.length > 0) {
        // Create header
        const header = document.createElement('h4');
        header.textContent = 'Detected Issues:';
        resultsElement.appendChild(header);
        
        // Create list of issues
        const issuesList = document.createElement('ul');
        issuesList.className = 'list-group';
        
        results.issues.forEach(issue => {
            const issueItem = document.createElement('li');
            issueItem.className = 'list-group-item';
            
            // Set background color based on severity
            if (issue.severity === 'high') {
                issueItem.classList.add('list-group-item-danger');
            } else if (issue.severity === 'medium') {
                issueItem.classList.add('list-group-item-warning');
            } else if (issue.severity === 'none') {
                issueItem.classList.add('list-group-item-success');
            }
            
            issueItem.innerHTML = `<strong>${issue.type.replace('_', ' ')}</strong>: ${issue.description}`;
            issuesList.appendChild(issueItem);
        });
        
        resultsElement.appendChild(issuesList);
    } else {
        // No issues detected
        resultsElement.innerHTML = '<div class="alert alert-info">No specific issues detected from the image.</div>';
    }
    
    // Show the results container
    document.getElementById('results-container').style.display = 'block';
}

// Helper function to convert data URL to Blob
function dataURLtoBlob(dataURL) {
    const parts = dataURL.split(';base64,');
    const contentType = parts[0].split(':')[1];
    const raw = window.atob(parts[1]);
    const rawLength = raw.length;
    const uInt8Array = new Uint8Array(rawLength);
    
    for (let i = 0; i < rawLength; ++i) {
        uInt8Array[i] = raw.charCodeAt(i);
    }
    
    return new Blob([uInt8Array], { type: contentType });
}

// Initialize when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', initCamera);
