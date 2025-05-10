/**
 * Voice processing functionality for automotive diagnostic assistant
 */

// Global variables for voice recording
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let recordingTimer = null;
let recordingTimeSeconds = 0;

// Initialize voice recording functionality
function initVoiceRecording() {
    // Get DOM elements
    const startRecordBtn = document.getElementById('start-record');
    const stopRecordBtn = document.getElementById('stop-record');
    const recordingStatus = document.getElementById('recording-status');
    const recordingTime = document.getElementById('recording-time');
    const submitAudioBtn = document.getElementById('submit-audio');
    
    // Add event listeners to buttons
    if (startRecordBtn) {
        startRecordBtn.addEventListener('click', startRecording);
    }
    
    if (stopRecordBtn) {
        stopRecordBtn.addEventListener('click', stopRecording);
    }
    
    if (submitAudioBtn) {
        submitAudioBtn.addEventListener('click', submitRecording);
    }
}

// Start recording audio
async function startRecording() {
    try {
        // Request access to the microphone
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        
        // Reset recording state
        audioChunks = [];
        isRecording = true;
        recordingTimeSeconds = 0;
        
        // Create media recorder
        mediaRecorder = new MediaRecorder(stream);
        
        // Set up event handlers
        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };
        
        mediaRecorder.onstop = () => {
            // Stream is kept alive for potential additional recordings
            console.log('Recording stopped');
        };
        
        // Start recording
        mediaRecorder.start();
        
        // Start timer
        startRecordingTimer();
        
        // Update UI
        document.getElementById('start-record').style.display = 'none';
        document.getElementById('stop-record').style.display = 'inline-block';
        document.getElementById('recording-status').className = 'alert alert-danger';
        document.getElementById('recording-status').textContent = 'Recording in progress...';
        document.getElementById('recording-guidance').style.display = 'block';
        document.getElementById('submit-audio').disabled = true;
        
    } catch (error) {
        console.error('Error accessing microphone:', error);
        document.getElementById('recording-status').className = 'alert alert-danger';
        document.getElementById('recording-status').textContent = 'Error accessing microphone: ' + error.message;
    }
}

// Stop recording audio
function stopRecording() {
    if (mediaRecorder && isRecording) {
        // Stop recording
        mediaRecorder.stop();
        isRecording = false;
        
        // Stop the timer
        stopRecordingTimer();
        
        // Stop all tracks to release the microphone
        mediaRecorder.stream.getTracks().forEach(track => track.stop());
        
        // Update UI
        document.getElementById('start-record').style.display = 'inline-block';
        document.getElementById('start-record').textContent = 'Record Again';
        document.getElementById('stop-record').style.display = 'none';
        document.getElementById('recording-status').className = 'alert alert-success';
        document.getElementById('recording-status').textContent = 'Recording complete! Click "Submit Description" to analyze.';
        document.getElementById('submit-audio').disabled = false;
    }
}

// Start the recording timer
function startRecordingTimer() {
    recordingTimeSeconds = 0;
    updateRecordingTimeDisplay();
    
    recordingTimer = setInterval(() => {
        recordingTimeSeconds++;
        updateRecordingTimeDisplay();
        
        // Automatically stop recording after 60 seconds
        if (recordingTimeSeconds >= 60) {
            stopRecording();
        }
    }, 1000);
}

// Stop the recording timer
function stopRecordingTimer() {
    if (recordingTimer) {
        clearInterval(recordingTimer);
        recordingTimer = null;
    }
}

// Update the recording time display
function updateRecordingTimeDisplay() {
    const minutes = Math.floor(recordingTimeSeconds / 60);
    const seconds = recordingTimeSeconds % 60;
    const displayTime = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    document.getElementById('recording-time').textContent = displayTime;
}

// Submit the recorded audio for analysis
function submitRecording() {
    if (audioChunks.length === 0) {
        document.getElementById('recording-status').className = 'alert alert-warning';
        document.getElementById('recording-status').textContent = 'No recording to submit. Please record your description first.';
        return;
    }
    
    // Show loading state
    const submitBtn = document.getElementById('submit-audio');
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
    document.getElementById('recording-status').textContent = 'Analyzing audio...';
    
    // Create audio blob
    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
    
    // Create FormData object
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.webm');
    
    // Send to server
    fetch('/process-voice', {
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
            displayVoiceResults(data.results);
            
            // Update status
            document.getElementById('recording-status').textContent = 'Audio analysis complete!';
            document.getElementById('recording-status').className = 'alert alert-success';
            
            // Enable the "Continue" button to proceed to next step
            document.getElementById('continue-btn').style.display = 'block';
        } else {
            // Handle error in results
            document.getElementById('recording-status').textContent = 'Error: ' + (data.error || 'Unknown error');
            document.getElementById('recording-status').className = 'alert alert-danger';
        }
    })
    .catch(error => {
        // Handle network or other errors
        console.error('Error uploading audio:', error);
        document.getElementById('recording-status').textContent = 'Error: ' + error.message;
        document.getElementById('recording-status').className = 'alert alert-danger';
    })
    .finally(() => {
        // Reset button state
        submitBtn.disabled = false;
        submitBtn.innerHTML = 'Submit Description';
    });
}

// Display the voice analysis results
function displayVoiceResults(results) {
    const resultsElement = document.getElementById('voice-results');
    
    // Clear previous results
    resultsElement.innerHTML = '';
    
    // Add transcript if available
    if (results.transcript) {
        const transcriptHeader = document.createElement('h4');
        transcriptHeader.textContent = 'Your Description:';
        resultsElement.appendChild(transcriptHeader);
        
        const transcriptBox = document.createElement('div');
        transcriptBox.className = 'alert alert-secondary';
        transcriptBox.textContent = results.transcript;
        resultsElement.appendChild(transcriptBox);
    }
    
    // Check if there are any symptoms
    if (results.symptoms && results.symptoms.length > 0) {
        // Create header
        const header = document.createElement('h4');
        header.textContent = 'Detected Symptoms:';
        resultsElement.appendChild(header);
        
        // Create list of symptoms
        const symptomsList = document.createElement('ul');
        symptomsList.className = 'list-group';
        
        results.symptoms.forEach(symptom => {
            const symptomItem = document.createElement('li');
            symptomItem.className = 'list-group-item';
            
            // Set background color based on severity
            if (symptom.severity === 'high') {
                symptomItem.classList.add('list-group-item-danger');
            } else if (symptom.severity === 'medium') {
                symptomItem.classList.add('list-group-item-warning');
            } else if (symptom.severity === 'none') {
                symptomItem.classList.add('list-group-item-success');
            }
            
            symptomItem.innerHTML = `<strong>${symptom.name.replace('_', ' ')}</strong>: ${symptom.description}`;
            symptomsList.appendChild(symptomItem);
        });
        
        resultsElement.appendChild(symptomsList);
    } else {
        // No symptoms detected
        resultsElement.innerHTML = '<div class="alert alert-info">No specific symptoms detected from your description.</div>';
    }
    
    // Show the results container
    document.getElementById('results-container').style.display = 'block';
}

// Initialize when the DOM is fully loaded
document.addEventListener('DOMContentLoaded', initVoiceRecording);
