import os
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from utils.image_processor import process_image
from utils.speech_processor import process_speech
from utils.diagnostic_engine import analyze_diagnostic_data

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "automotive-diagnostic-assistant-key")

@app.route('/')
def index():
    """Render the main page with the camera and voice input options."""
    return render_template('index.html')

@app.route('/vehicle-info', methods=['POST'])
def vehicle_info():
    """Process vehicle information and store in session."""
    make = request.form.get('make')
    model = request.form.get('model')
    year = request.form.get('year')
    mileage = request.form.get('mileage')
    
    # Store vehicle info in session
    session['vehicle_info'] = {
        'make': make,
        'model': model,
        'year': year,
        'mileage': mileage
    }
    
    return redirect(url_for('diagnostic'))

@app.route('/diagnostic')
def diagnostic():
    """Render the diagnostic page with camera and voice input."""
    # Check if vehicle info exists in session
    if 'vehicle_info' not in session:
        return redirect(url_for('index'))
    
    vehicle_info = session['vehicle_info']
    return render_template('diagnostic.html', vehicle_info=vehicle_info)

@app.route('/process-image', methods=['POST'])
def process_image_route():
    """Process an image from the camera and return diagnostic information."""
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    
    image_file = request.files['image']
    vehicle_info = session.get('vehicle_info', {})
    
    try:
        # Process the image using OpenCV
        image_results = process_image(image_file, vehicle_info)
        
        # Store results in session
        if 'diagnostic_data' not in session:
            session['diagnostic_data'] = {}
        
        session['diagnostic_data']['image_results'] = image_results
        return jsonify({'success': True, 'results': image_results})
    
    except Exception as e:
        logging.error(f"Error processing image: {str(e)}")
        return jsonify({'error': f'Error processing image: {str(e)}'}), 500

@app.route('/process-voice', methods=['POST'])
def process_voice_route():
    """Process voice input and return diagnostic information."""
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio provided'}), 400
    
    audio_file = request.files['audio']
    vehicle_info = session.get('vehicle_info', {})
    
    try:
        # Process the audio using SpeechRecognition
        voice_results = process_speech(audio_file, vehicle_info)
        
        # Store results in session
        if 'diagnostic_data' not in session:
            session['diagnostic_data'] = {}
        
        session['diagnostic_data']['voice_results'] = voice_results
        return jsonify({'success': True, 'results': voice_results})
    
    except Exception as e:
        logging.error(f"Error processing voice: {str(e)}")
        return jsonify({'error': f'Error processing voice: {str(e)}'}), 500

@app.route('/analyze', methods=['POST'])
def analyze():
    """Analyze the collected data and provide diagnostic results."""
    if 'diagnostic_data' not in session:
        return redirect(url_for('diagnostic'))
    
    diagnostic_data = session['diagnostic_data']
    vehicle_info = session.get('vehicle_info', {})
    
    # Combine data from image and voice analysis
    analysis_results = analyze_diagnostic_data(diagnostic_data, vehicle_info)
    
    # Store analysis results in session
    session['analysis_results'] = analysis_results
    
    return redirect(url_for('results'))

@app.route('/results')
def results():
    """Display the diagnostic results and recommendations."""
    if 'analysis_results' not in session:
        return redirect(url_for('diagnostic'))
    
    analysis_results = session['analysis_results']
    vehicle_info = session.get('vehicle_info', {})
    
    return render_template('results.html', 
                           analysis_results=analysis_results,
                           vehicle_info=vehicle_info)

@app.route('/reset', methods=['POST'])
def reset():
    """Reset the diagnostic session."""
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
