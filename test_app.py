#!/usr/bin/env python3
"""
OBD2 Diagnostic Pro - Comprehensive Test Suite
Tests all major functionality of the application including OBD2 connections,
AI integration, database operations, and web interfaces.
"""

import pytest
import os
import sys
import tempfile
from unittest.mock import Mock, patch
from flask import Flask
import json

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from database import db
from models import Vehicle, OBDDiagnosticSession, DiagnosticTroubleCode, SensorReading
from utils.obd2_connector import OBD2Connector, create_obd2_connector
from utils.diagnostic_ai import DiagnosticAI
from utils.diagnostic_engine import analyze_obd2_data
from utils.dtc_database import initialize_dtc_database

class TestOBD2DiagnosticPro:
    """Comprehensive test suite for OBD2 Diagnostic Pro."""
    
    @pytest.fixture
    def app(self):
        """Create test app with temporary database."""
        # Create temporary database
        db_fd, db_path = tempfile.mkstemp()
        
        # Configure test app
        app = create_app()
        app.config.update({
            'TESTING': True,
            'DATABASE_URL': f'sqlite:///{db_path}',
            'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
            'WTF_CSRF_ENABLED': False,
            'OBD2_SIMULATION': True
        })
        
        with app.app_context():
            db.create_all()
            initialize_dtc_database()
        
        yield app
        
        # Cleanup
        os.close(db_fd)
        os.unlink(db_path)
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    @pytest.fixture
    def runner(self, app):
        """Create test runner."""
        return app.test_cli_runner()

    def test_app_creation(self, app):
        """Test app creation and configuration."""
        assert app.config['TESTING'] is True
        assert 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']

    def test_index_page(self, client):
        """Test the main index page."""
        response = client.get('/')
        assert response.status_code == 200
        assert b'OBD2 Diagnostic Pro' in response.data
        assert b'Professional OBD2 Diagnostics' in response.data

    def test_obd2_index(self, client):
        """Test OBD2 dashboard page."""
        response = client.get('/obd2')
        assert response.status_code == 200
        assert b'OBD2 Dashboard' in response.data

    def test_obd2_connect_get(self, client):
        """Test OBD2 connect page GET request."""
        response = client.get('/obd2/connect')
        assert response.status_code == 200
        assert b'Connect Your Vehicle' in response.data or b'Vehicle Information' in response.data

    def test_obd2_connect_post(self, client, app):
        """Test OBD2 connect page POST request."""
        with app.app_context():
            response = client.post('/obd2/connect', data={
                'make': 'Toyota',
                'model': 'Camry',
                'year': '2020',
                'mileage': '50000'
            })
            assert response.status_code == 302  # Redirect after successful POST
            
            # Check if vehicle was created in database
            vehicle = Vehicle.query.filter_by(make='Toyota', model='Camry').first()
            assert vehicle is not None
            assert vehicle.year == 2020

    def test_vehicle_info_processing(self, client, app):
        """Test vehicle information processing."""
        with app.app_context():
            response = client.post('/vehicle-info', data={
                'make': 'Honda',
                'model': 'Civic',
                'year': '2019',
                'mileage': '40000'
            })
            assert response.status_code == 302  # Should redirect

    def test_obd2_connector_initialization(self):
        """Test OBD2 connector initialization."""
        # Test with simulation
        connector = create_obd2_connector(simulate=True)
        assert connector is not None
        assert connector.simulate is True
        
        # Test port scanning
        ports = connector.scan_for_ports()
        assert isinstance(ports, list)
        assert len(ports) > 0

    def test_obd2_connection_simulation(self):
        """Test OBD2 connection in simulation mode."""
        connector = create_obd2_connector(simulate=True)
        
        # Test connection
        result = connector.connect()
        assert result is True
        assert connector.connected is True
        
        # Test connection status
        status = connector.get_connection_status()
        assert status['connected'] is True
        assert 'protocol' in status
        assert 'vehicle_info' in status

    def test_obd2_dtc_scanning(self):
        """Test DTC scanning functionality."""
        connector = create_obd2_connector(simulate=True)
        connector.connect()
        
        dtcs = connector.scan_for_dtcs()
        assert isinstance(dtcs, list)
        # DTCs may or may not be present in simulation
        for dtc in dtcs:
            assert 'code' in dtc
            assert 'description' in dtc
            assert 'type' in dtc

    def test_obd2_live_data(self):
        """Test live data reading."""
        connector = create_obd2_connector(simulate=True)
        connector.connect()
        
        live_data = connector.read_live_data()
        assert isinstance(live_data, dict)
        
        # Check for common sensors
        expected_sensors = ['RPM', 'COOLANT_TEMP', 'ENGINE_LOAD']
        for sensor in expected_sensors:
            if sensor in live_data:
                assert 'value' in live_data[sensor]
                assert 'unit' in live_data[sensor]

    def test_live_data_api(self, client, app):
        """Test live data API endpoint."""
        with app.app_context():
            # First create a vehicle and session
            client.post('/vehicle-info', data={
                'make': 'Test',
                'model': 'Vehicle', 
                'year': '2020',
                'mileage': '1000'
            })
            
            response = client.get('/api/obd2/live-data')
            assert response.status_code in [200, 400]  # 400 if no vehicle selected
            
            if response.status_code == 200:
                data = response.get_json()
                assert 'success' in data

    def test_obd2_scan_ports_api(self, client):
        """Test OBD2 port scanning API."""
        response = client.get('/api/obd2/scan-ports')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'success' in data
        if data['success']:
            assert 'ports' in data
            assert isinstance(data['ports'], list)

    def test_clear_dtcs_api(self, client, app):
        """Test clear DTCs API endpoint."""
        with app.app_context():
            # Create a test session
            client.post('/vehicle-info', data={
                'make': 'Test',
                'model': 'Vehicle',
                'year': '2020', 
                'mileage': '1000'
            })
            
            response = client.post('/api/obd2/clear-dtcs')
            # Should return 400 if no vehicle selected, or 200/500 based on operation
            assert response.status_code in [200, 400, 500]

    def test_diagnostic_ai_initialization(self):
        """Test AI diagnostic system initialization."""
        # Test with both providers disabled (should work in fallback mode)
        ai = DiagnosticAI(use_openai=False, use_anthropic=False)
        assert ai is not None
        
        # Test with simulation
        if os.getenv('ANTHROPIC_API_KEY') or os.getenv('OPENAI_API_KEY'):
            ai_real = DiagnosticAI()
            assert ai_real is not None

    def test_diagnostic_engine_obd2_analysis(self, app):
        """Test OBD2 diagnostic analysis engine."""
        with app.app_context():
            # Create mock DTC and sensor data
            mock_dtcs = [
                Mock(code='P0301', description='Cylinder 1 Misfire', type='stored'),
                Mock(code='P0171', description='System Too Lean Bank 1', type='stored')
            ]
            
            mock_sensors = [
                Mock(name='RPM', value=800, unit='rpm', pid='010C'),
                Mock(name='COOLANT_TEMP', value=90, unit='°C', pid='0105')
            ]
            
            vehicle_info = {
                'make': 'Toyota',
                'model': 'Camry',
                'year': 2020,
                'mileage': 50000
            }
            
            # Test analysis
            results = analyze_obd2_data(mock_dtcs, mock_sensors, vehicle_info)
            
            assert isinstance(results, dict)
            assert 'diagnoses' in results
            assert 'severity' in results
            assert 'diy_repairs' in results
            assert 'professional_repairs' in results
            assert 'safety_warnings' in results
            
            # Should detect the DTCs
            assert len(results['diagnoses']) >= 2
            assert results['severity'] in ['low', 'medium', 'high', 'critical']

    def test_dtc_database_initialization(self, app):
        """Test DTC database initialization."""
        with app.app_context():
            from utils.dtc_database import get_dtc_info, search_dtcs
            
            # Test getting specific DTC info
            p0301_info = get_dtc_info('P0301')
            assert p0301_info is not None
            assert p0301_info['code'] == 'P0301'
            assert 'misfire' in p0301_info['description'].lower()
            
            # Test searching DTCs
            misfire_codes = search_dtcs('misfire')
            assert isinstance(misfire_codes, list)
            assert len(misfire_codes) > 0

    def test_database_models(self, app):
        """Test database models and relationships."""
        with app.app_context():
            # Create test vehicle
            vehicle = Vehicle(
                make='Test',
                model='Vehicle',
                year=2020,
                mileage=10000,
                vin='TEST123456789'
            )
            db.session.add(vehicle)
            db.session.commit()
            
            # Create diagnostic session
            session = OBDDiagnosticSession(
                vehicle_id=vehicle.id,
                connection_type='USB',
                protocol='CAN',
                success=True
            )
            db.session.add(session)
            db.session.commit()
            
            # Create DTC
            dtc = DiagnosticTroubleCode(
                session_id=session.id,
                code='P0301',
                description='Cylinder 1 Misfire',
                type='stored'
            )
            db.session.add(dtc)
            
            # Create sensor reading
            sensor = SensorReading(
                session_id=session.id,
                pid='010C',
                name='RPM',
                value=850.0,
                unit='rpm'
            )
            db.session.add(sensor)
            db.session.commit()
            
            # Test relationships
            assert len(vehicle.obd_sessions) == 1
            assert len(session.dtcs) == 1
            assert len(session.sensor_readings) == 1
            assert session.dtcs[0].code == 'P0301'

    def test_error_handling(self, client):
        """Test error handling in various scenarios."""
        # Test accessing protected routes without setup
        response = client.get('/obd2/dashboard')
        # Should redirect to connect page or show empty dashboard
        assert response.status_code in [200, 302]
        
        # Test invalid API calls
        response = client.get('/api/obd2/live-data')
        data = response.get_json()
        # Should handle gracefully even without vehicle setup
        assert response.status_code in [200, 400]

    def test_session_management(self, client, app):
        """Test session management functionality."""
        with client.session_transaction() as sess:
            sess['vehicle_info'] = {
                'make': 'Honda',
                'model': 'Accord',
                'year': 2019,
                'mileage': 30000
            }
            sess['vehicle_id'] = 1
        
        # Test that session data persists
        response = client.get('/obd2/dashboard')
        assert response.status_code == 200

    def test_reset_functionality(self, client):
        """Test session reset functionality."""
        # Set some session data
        with client.session_transaction() as sess:
            sess['vehicle_info'] = {'make': 'Test'}
            sess['vehicle_id'] = 1
        
        # Reset session
        response = client.get('/reset')
        assert response.status_code == 302  # Should redirect
        
        # Verify session is cleared
        with client.session_transaction() as sess:
            assert 'vehicle_info' not in sess
            assert 'vehicle_id' not in sess

    def test_responsive_design_elements(self, client):
        """Test that pages contain responsive design elements."""
        response = client.get('/')
        html = response.data.decode()
        
        # Check for Bootstrap and responsive elements
        assert 'bootstrap' in html.lower() or 'container' in html
        assert 'meta name="viewport"' in html

    def test_security_headers(self, client):
        """Test basic security considerations."""
        response = client.get('/')
        
        # Check that dangerous headers are not present
        assert 'X-Powered-By' not in response.headers
        
        # Basic security checks
        assert response.status_code == 200

def run_comprehensive_tests():
    """Run all tests with verbose output."""
    print("🚀 Starting OBD2 Diagnostic Pro Test Suite")
    print("=" * 50)
    
    # Run pytest with verbose output
    pytest_args = [
        __file__,
        '-v',
        '--tb=short',
        '--color=yes'
    ]
    
    exit_code = pytest.main(pytest_args)
    
    print("\n" + "=" * 50)
    if exit_code == 0:
        print("✅ All tests passed! OBD2 Diagnostic Pro is ready for use.")
    else:
        print("❌ Some tests failed. Please review the output above.")
    
    return exit_code

if __name__ == '__main__':
    # Set environment for testing
    os.environ['OBD2_SIMULATION'] = 'true'
    os.environ['FLASK_ENV'] = 'testing'
    
    # Run tests
    exit_code = run_comprehensive_tests()
    sys.exit(exit_code) 