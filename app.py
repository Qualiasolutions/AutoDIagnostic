import os
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from utils.image_processor import process_image
from utils.speech_processor import process_speech
from utils.diagnostic_engine import analyze_diagnostic_data

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Database setup with SQLAlchemy
class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "automotive-diagnostic-assistant-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # For proper URL generation with https

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Initialize the database with the app
db.init_app(app)

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

# OBD2 USB Connection Routes
@app.route('/obd2')
def obd2_index():
    """Render the OBD2 diagnostic landing page."""
    return render_template('obd2/index.html')

@app.route('/obd2/connect', methods=['GET', 'POST'])
def obd2_connect():
    """Connect to a vehicle via OBD2-USB cable."""
    if request.method == 'POST':
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
        
        # Create or get vehicle from database
        from models import Vehicle
        
        vehicle = Vehicle.query.filter_by(
            make=make,
            model=model,
            year=year
        ).first()
        
        if not vehicle:
            vehicle = Vehicle(
                make=make,
                model=model,
                year=year,
                mileage=mileage
            )
            db.session.add(vehicle)
            db.session.commit()
        
        # Store vehicle ID in session
        session['vehicle_id'] = vehicle.id
        
        return redirect(url_for('obd2_dashboard'))
    
    return render_template('obd2/connect.html')

@app.route('/obd2/dashboard')
def obd2_dashboard():
    """Show the OBD2 diagnostic dashboard."""
    if 'vehicle_id' not in session:
        return redirect(url_for('obd2_connect'))
    
    vehicle_id = session['vehicle_id']
    
    # Get vehicle from database
    from models import Vehicle
    vehicle = Vehicle.query.get(vehicle_id)
    
    if not vehicle:
        return redirect(url_for('obd2_connect'))
    
    return render_template('obd2/dashboard.html', vehicle=vehicle)

@app.route('/obd2/scan', methods=['POST'])
def obd2_scan():
    """Start an OBD2 diagnostic scan."""
    if 'vehicle_id' not in session:
        return jsonify({'error': 'No vehicle selected'}), 400
    
    vehicle_id = session['vehicle_id']
    
    # Get USB connection parameters
    port = request.form.get('port')
    
    try:
        # Import the OBD2 connector
        from utils.obd2_connector import OBD2Connector
        
        # Create a new diagnostic session
        from models import OBDDiagnosticSession
        
        session_obj = OBDDiagnosticSession(
            vehicle_id=vehicle_id,
            connection_type='USB',
            notes='Initiated from web interface'
        )
        db.session.add(session_obj)
        db.session.commit()
        
        # Store session ID in session
        session['obd_session_id'] = session_obj.id
        
        # Initialize connection (this would be async in production)
        # For demo purposes, we're doing it synchronously
        connector = OBD2Connector(port=port)
        connection_success = connector.connect()
        
        if not connection_success:
            session_obj.success = False
            session_obj.notes = 'Failed to connect to vehicle'
            db.session.commit()
            return jsonify({'error': 'Could not connect to vehicle OBD port'}), 500
        
        # Get vehicle info from OBD
        vehicle_info = connector.get_vehicle_info()
        
        # Update vehicle in database
        from models import Vehicle
        vehicle = Vehicle.query.get(vehicle_id)
        if vehicle and vehicle_info:
            vehicle.vin = vehicle_info.get('vin', vehicle.vin)
            vehicle.ecu_name = vehicle_info.get('ecu_name', vehicle.ecu_name)
            vehicle.protocol = vehicle_info.get('protocol', vehicle.protocol)
            db.session.commit()
        
        # Get DTCs
        dtcs = connector.read_dtcs()
        
        # Store DTCs in database
        from models import DiagnosticTroubleCode
        for dtc in dtcs:
            dtc_obj = DiagnosticTroubleCode(
                session_id=session_obj.id,
                code=dtc.get('code', 'Unknown'),
                description=dtc.get('description', ''),
                type=dtc.get('type', 'stored')
            )
            db.session.add(dtc_obj)
        
        # Get sensor data
        sensor_data = connector.read_all_sensor_data()
        
        # Store sensor readings in database
        from models import SensorReading
        for pid, data in sensor_data.items():
            if data.get('value') is not None:
                reading = SensorReading(
                    session_id=session_obj.id,
                    pid=pid,
                    name=data.get('name', pid),
                    value=data.get('value'),
                    unit=data.get('unit', ''),
                    raw_response=data.get('raw_response', '')
                )
                db.session.add(reading)
        
        # Mark session as successful
        session_obj.success = True
        session_obj.notes = f"Successfully scanned vehicle: {len(dtcs)} DTCs, {len(sensor_data)} sensors"
        db.session.commit()
        
        # Disconnect from vehicle
        connector.disconnect()
        
        # Return success
        return jsonify({
            'success': True, 
            'session_id': session_obj.id,
            'dtc_count': len(dtcs),
            'sensor_count': len(sensor_data)
        })
    
    except Exception as e:
        app.logger.error(f"Error during OBD2 scan: {str(e)}")
        return jsonify({'error': f'Error during scan: {str(e)}'}), 500

@app.route('/obd2/results/<int:session_id>')
def obd2_results(session_id):
    """Show the results of an OBD2 diagnostic scan."""
    # Get session from database
    from models import OBDDiagnosticSession, DiagnosticTroubleCode, SensorReading, Vehicle
    
    session_obj = OBDDiagnosticSession.query.get(session_id)
    if not session_obj:
        return redirect(url_for('obd2_dashboard'))
    
    # Get vehicle
    vehicle = Vehicle.query.get(session_obj.vehicle_id)
    
    # Get DTCs and sensor readings
    dtcs = DiagnosticTroubleCode.query.filter_by(session_id=session_id).all()
    sensor_readings = SensorReading.query.filter_by(session_id=session_id).all()
    
    # If we have DTCs, analyze them with AI
    dtc_analysis = None
    if dtcs:
        try:
            # Import the AI module
            from utils.diagnostic_ai import DiagnosticAI
            
            # Convert DTCs to format expected by AI
            dtc_list = [{'code': dtc.code, 'description': dtc.description, 'type': dtc.type} for dtc in dtcs]
            
            # Get vehicle info
            vehicle_info = {
                'make': vehicle.make,
                'model': vehicle.model,
                'year': vehicle.year,
                'mileage': vehicle.mileage,
                'vin': vehicle.vin
            }
            
            # Create AI instance and analyze
            ai = DiagnosticAI()
            dtc_analysis = ai.analyze_dtcs(dtc_list, vehicle_info)
        except Exception as e:
            app.logger.error(f"Error analyzing DTCs: {str(e)}")
            dtc_analysis = None
    
    return render_template(
        'obd2/results.html',
        session=session_obj,
        vehicle=vehicle,
        dtcs=dtcs,
        sensor_readings=sensor_readings,
        dtc_analysis=dtc_analysis
    )

# Initialize the database tables
with app.app_context():
    # Import models to ensure they're registered with SQLAlchemy
    import models
    db.create_all()
    app.logger.info("Database tables created")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
