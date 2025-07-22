import os
import logging
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from werkzeug.middleware.proxy_fix import ProxyFix
from config import get_config
from database import db
from utils.diagnostic_engine import analyze_diagnostic_data

# Create Flask app with configuration
def create_app():
    app = Flask(__name__)
    config_class = get_config()
    app.config.from_object(config_class)
    
    # Initialize configuration
    config_class.init_app(app)
    
    # Add proxy fix for proper URL generation
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    return app

app = create_app()

# Initialize the database with the app
db.init_app(app)

# Import models to register them with SQLAlchemy
import models

# Initialize the DTC database
try:
    from utils.dtc_database import initialize_dtc_database
    with app.app_context():
        # Models are already imported above
        db.create_all()
        app.logger.info("Database tables created")
        
        # Initialize DTC database
        if initialize_dtc_database():
            app.logger.info("DTC database initialized successfully")
        else:
            app.logger.warning("Failed to initialize DTC database")
except Exception as e:
    app.logger.error(f"Error during database initialization: {e}")

@app.route('/')
def index():
    """Render the main OBD2 diagnostic page."""
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
    
    return redirect(url_for('obd2_connect'))

@app.route('/reset', methods=['GET', 'POST'])
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
    
    # Get diagnostic sessions for this vehicle
    from models import OBDDiagnosticSession
    diagnostic_sessions = OBDDiagnosticSession.query.filter_by(vehicle_id=vehicle_id).order_by(OBDDiagnosticSession.started_at.desc()).all()
    
    return render_template('obd2/dashboard.html', 
                          vehicle_info=vehicle,
                          diagnostic_sessions=diagnostic_sessions,
                          session=vehicle)

@app.route('/obd2/scan', methods=['GET', 'POST'])
def obd2_scan():
    """Start an OBD2 diagnostic scan."""
    if request.method == 'GET':
        # Render the scan page
        if 'vehicle_id' not in session:
            return redirect(url_for('obd2_connect'))
        
        vehicle_id = session['vehicle_id']
        
        # Get vehicle from database
        from models import Vehicle
        vehicle = Vehicle.query.get(vehicle_id)
        
        if not vehicle:
            return redirect(url_for('obd2_connect'))
        
        # Check if we have a session ID in the regular session
        session_id = session.get('obd_session_id')
        
        return render_template('obd2/scan.html', 
                              vehicle_info=vehicle, 
                              session_id=session_id)
    elif request.method == 'POST':
        if 'vehicle_id' not in session:
            return jsonify({'error': 'No vehicle selected'}), 400
        
        vehicle_id = session['vehicle_id']
        
        # Get USB connection parameters
        port = request.form.get('port')
        
        try:
            # Import the OBD2 connector
            from utils.obd2_connector import create_obd2_connector
            
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
            connector = create_obd2_connector(port=port)
            connection_success = connector.connect()
            
            if not connection_success:
                session_obj.success = False
                session_obj.notes = 'Failed to connect to vehicle'
                db.session.commit()
                app.logger.error("Failed to connect to OBD2 port")
                return jsonify({'error': 'Could not connect to vehicle OBD port'}), 500
            
            # Get vehicle info from OBD
            connection_status = connector.get_connection_status()
            vehicle_info = connection_status.get('vehicle_info', {})
            
            # Update vehicle in database
            from models import Vehicle
            vehicle = Vehicle.query.get(vehicle_id)
            if vehicle and vehicle_info:
                if vehicle_info.get('vin'):
                    vehicle.vin = vehicle_info.get('vin')
                if vehicle_info.get('ecu_name'):
                    vehicle.ecu_name = vehicle_info.get('ecu_name')
                if vehicle_info.get('protocol'):
                    vehicle.protocol = vehicle_info.get('protocol')
                db.session.commit()
            
            # Get DTCs
            dtcs = connector.scan_for_dtcs()
            
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
            sensor_data = connector.read_live_data()
            
            # Store sensor readings in database
            from models import SensorReading
            for key, data in sensor_data.items():
                if data.get('value') is not None:
                    reading = SensorReading(
                        session_id=session_obj.id,
                        pid=key,
                        name=key,
                        value=float(data.get('value')),
                        unit=data.get('unit', ''),
                        raw_response=str(data)
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

@app.route('/api/obd2/scan-ports', methods=['GET'])
def api_scan_ports():
    """API endpoint to scan for available OBD2 ports."""
    try:
        # Import the OBD2 connector
        from utils.obd2_connector import create_obd2_connector
        
        # Create a connector without specifying a port
        connector = create_obd2_connector()
        
        # Scan for ports
        ports = connector.scan_for_ports()
        
        return jsonify({'success': True, 'ports': ports})
    except Exception as e:
        app.logger.error(f"Error scanning for ports: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/obd2/clear-dtcs', methods=['POST'])
def api_clear_dtcs():
    """API endpoint to clear diagnostic trouble codes."""
    if 'vehicle_id' not in session:
        return jsonify({'error': 'No vehicle selected'}), 400
    
    try:
        # Import the OBD2 connector
        from utils.obd2_connector import create_obd2_connector
        
        # Create a connector
        connector = create_obd2_connector()
        
        # Connect to vehicle
        connection_success = connector.connect()
        if not connection_success:
            return jsonify({'error': 'Could not connect to vehicle'}), 500
        
        # Clear DTCs
        success = connector.clear_dtcs()
        
        # Disconnect
        connector.disconnect()
        
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Failed to clear DTCs'}), 500
    except Exception as e:
        app.logger.error(f"Error clearing DTCs: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/obd2/aps-calibration')
def obd2_aps_calibration():
    """APS Calibration Tool for adjusting Accelerator Pedal Position Sensor settings."""
    if 'vehicle_id' not in session:
        return redirect(url_for('obd2_connect'))
    
    vehicle_id = session['vehicle_id']
    
    # Get vehicle from database
    from models import Vehicle
    vehicle = Vehicle.query.get(vehicle_id)
    
    if not vehicle:
        return redirect(url_for('obd2_connect'))
    
    return render_template('obd2/aps_calibration.html', vehicle_info=vehicle)

@app.route('/obd2/live-data-monitoring')
def obd2_live_data_monitoring():
    """Live data monitoring page for real-time sensor readings."""
    if 'vehicle_id' not in session:
        return redirect(url_for('obd2_connect'))
    
    vehicle_id = session['vehicle_id']
    
    # Get vehicle from database
    from models import Vehicle
    vehicle = Vehicle.query.get(vehicle_id)
    
    if not vehicle:
        return redirect(url_for('obd2_connect'))
    
    return render_template('obd2/live_data.html', vehicle_info=vehicle)

@app.route('/api/obd2/live-data', methods=['GET'])
def api_live_data():
    """API endpoint to get live sensor data from the vehicle."""
    if 'vehicle_id' not in session:
        return jsonify({'error': 'No vehicle selected'}), 400
    
    try:
        # Import the OBD2 connector
        from utils.obd2_connector import create_obd2_connector
        
        # Create a connector
        connector = create_obd2_connector()
        
        # Connect to vehicle
        connection_success = connector.connect()
        if not connection_success:
            return jsonify({'error': 'Could not connect to vehicle'}), 500
        
        # Read live data
        sensor_data = connector.read_live_data()
        
        # Disconnect
        connector.disconnect()
        
        return jsonify({
            'success': True,
            'data': sensor_data,
            'timestamp': __import__('datetime').datetime.now().isoformat()
        })
    except Exception as e:
        app.logger.error(f"Error reading live data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/obd2/aps/read', methods=['GET'])
def api_read_aps():
    """API endpoint to read current APS values from the vehicle."""
    if 'vehicle_id' not in session:
        return jsonify({'error': 'No vehicle selected'}), 400
    
    try:
        # Import the OBD2 connector
        from utils.obd2_connector import create_obd2_connector
        
        # Create a connector
        connector = create_obd2_connector()
        
        # Connect to vehicle
        connection_success = connector.connect()
        if not connection_success:
            return jsonify({'error': 'Could not connect to vehicle'}), 500
        
        # Read APS values (these would be real APS PIDs in production)
        aps_data = connector.read_sensor_data(['APS1', 'APS2'])
        
        # Disconnect
        connector.disconnect()
        
        return jsonify({
            'success': True,
            'aps_data': aps_data
        })
    except Exception as e:
        app.logger.error(f"Error reading APS: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/obd2/aps/calibrate', methods=['POST'])
def api_calibrate_aps():
    """API endpoint to write new APS calibration values to the vehicle ECU."""
    if 'vehicle_id' not in session:
        return jsonify({'error': 'No vehicle selected'}), 400
    
    try:
        # Get calibration parameters from request
        aps1_min = request.form.get('aps1_min')
        aps1_max = request.form.get('aps1_max')
        aps2_min = request.form.get('aps2_min')
        aps2_max = request.form.get('aps2_max')
        
        # Validate parameters
        if not all([aps1_min, aps1_max, aps2_min, aps2_max]):
            return jsonify({'error': 'Missing calibration parameters'}), 400
        
        # Import the OBD2 connector
        from utils.obd2_connector import create_obd2_connector
        
        # Create a connector
        connector = create_obd2_connector()
        
        # Connect to vehicle
        connection_success = connector.connect()
        if not connection_success:
            return jsonify({'error': 'Could not connect to vehicle'}), 500
        
        # Write calibration values to ECU
        # This would use actual OBD2 commands in production
        calibration_results = connector.write_calibration_data({
            'APS1_MIN': float(aps1_min),
            'APS1_MAX': float(aps1_max),
            'APS2_MIN': float(aps2_min),
            'APS2_MAX': float(aps2_max)
        })
        
        # Disconnect
        connector.disconnect()
        
        return jsonify({
            'success': True,
            'results': calibration_results
        })
    except Exception as e:
        app.logger.error(f"Error calibrating APS: {str(e)}")
        return jsonify({'error': str(e)}), 500

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
    results = {}
    if dtcs:
        try:
            # Import the AI module
            from utils.diagnostic_ai import DiagnosticAI
            
            # Convert DTCs to format expected by AI
            dtc_list = [{'code': dtc.code, 'description': dtc.description, 'type': dtc.type} for dtc in dtcs]
            
            # Only proceed if vehicle is not None
            if vehicle:
                # Get vehicle info
                vehicle_info = {
                    'make': vehicle.make,
                    'model': vehicle.model,
                    'year': vehicle.year,
                    'mileage': vehicle.mileage,
                    'vin': vehicle.vin if vehicle.vin else None
                }
                
                # Create AI instance and analyze
                ai = DiagnosticAI(use_openai=False, use_anthropic=True)
                results = ai.analyze_dtcs(dtc_list, vehicle_info)
        except Exception as e:
            app.logger.error(f"Error analyzing DTCs: {str(e)}")
            results = {}
    
    return render_template(
        'obd2/results.html',
        session=session_obj,
        vehicle_info=vehicle,
        dtcs=dtcs,
        sensor_readings=sensor_readings,
        results=results
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
