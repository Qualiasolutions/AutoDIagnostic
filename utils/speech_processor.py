import speech_recognition as sr
import tempfile
import os
import logging
import json
from werkzeug.utils import secure_filename

def process_speech(audio_file, vehicle_info):
    """
    Process audio file using SpeechRecognition to extract symptoms.
    
    Args:
        audio_file: The uploaded audio file
        vehicle_info: Dictionary containing vehicle information
        
    Returns:
        Dictionary with identified symptoms
    """
    logging.debug("Processing speech...")
    
    # Save the uploaded file to a temporary location
    temp_dir = tempfile.gettempdir()
    filename = secure_filename(audio_file.filename)
    temp_path = os.path.join(temp_dir, filename)
    audio_file.save(temp_path)
    
    # Initialize speech recognizer
    r = sr.Recognizer()
    
    # Load symptom keywords from diagnostic data
    with open('static/data/diagnostic_data.json', 'r') as f:
        diagnostic_data = json.load(f)
    
    symptom_keywords = {}
    for issue in diagnostic_data['issues']:
        for symptom in issue['symptoms']:
            symptom_keywords[symptom['name']] = symptom['keywords']
    
    results = {
        'symptoms': [],
        'confidence': {},
        'transcript': ""
    }
    
    try:
        # Process audio file
        with sr.AudioFile(temp_path) as source:
            audio_data = r.record(source)
            # Convert speech to text
            transcript = r.recognize_google(audio_data)
            results['transcript'] = transcript
            
            # Analyze transcript for symptom keywords
            transcript_lower = transcript.lower()
            for symptom, keywords in symptom_keywords.items():
                for keyword in keywords:
                    if keyword.lower() in transcript_lower:
                        # Found a symptom keyword
                        if symptom not in [s['name'] for s in results['symptoms']]:
                            results['symptoms'].append({
                                'name': symptom,
                                'description': f"User mentioned '{keyword}'",
                                'severity': 'medium'  # Default severity
                            })
                            results['confidence'][symptom] = 0.8
    
    except sr.UnknownValueError:
        results['error'] = "Could not understand audio"
    except sr.RequestError as e:
        results['error'] = f"Could not request results; {e}"
    except Exception as e:
        results['error'] = f"Error processing speech: {str(e)}"
    
    # Clean up the temporary file
    os.remove(temp_path)
    
    # If no symptoms detected, add a note
    if not results['symptoms'] and 'error' not in results:
        results['symptoms'].append({
            'name': 'no_symptoms_described',
            'description': 'No specific symptoms were described',
            'severity': 'none'
        })
    
    return results
