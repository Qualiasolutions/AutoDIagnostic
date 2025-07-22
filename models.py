from datetime import datetime
from database import db

class Vehicle(db.Model):
    """Model for storing vehicle information."""
    id = db.Column(db.Integer, primary_key=True)
    make = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    mileage = db.Column(db.Integer)
    vin = db.Column(db.String(17))  # Vehicle Identification Number
    ecu_name = db.Column(db.String(100))  # ECU Name from OBD
    protocol = db.Column(db.String(50))  # OBD protocol used
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    obd_sessions = db.relationship('OBDDiagnosticSession', backref='vehicle', lazy=True)
    
    def __repr__(self):
        return f'<Vehicle {self.make} {self.model} ({self.year})>'

class OBDDiagnosticSession(db.Model):
    """Model for storing OBD diagnostic sessions."""
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    connection_type = db.Column(db.String(50), default='USB')  # USB, Bluetooth, WiFi
    protocol = db.Column(db.String(50))  # OBD protocol used
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)
    success = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    
    # Relationships
    dtcs = db.relationship('DiagnosticTroubleCode', backref='session', lazy=True)
    sensor_readings = db.relationship('SensorReading', backref='session', lazy=True)
    
    def __repr__(self):
        return f'<OBDDiagnosticSession #{self.id}>'

class DiagnosticTroubleCode(db.Model):
    """Model for storing diagnostic trouble codes (DTCs)."""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('obd_diagnostic_session.id'), nullable=False)
    code = db.Column(db.String(10), nullable=False)  # e.g., P0301
    description = db.Column(db.Text)
    type = db.Column(db.String(20))  # stored, pending, permanent
    detected_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<DTC {self.code}>'

class SensorReading(db.Model):
    """Model for storing sensor readings from OBD."""
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('obd_diagnostic_session.id'), nullable=False)
    pid = db.Column(db.String(10), nullable=False)  # Parameter ID (e.g., 010C for RPM)
    name = db.Column(db.String(50))  # Human-readable name
    value = db.Column(db.Float)  # Sensor value
    unit = db.Column(db.String(20))  # Unit of measurement
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    raw_response = db.Column(db.String(100))  # Raw response from OBD adapter
    
    def __repr__(self):
        return f'<SensorReading {self.name}: {self.value} {self.unit}>'

class DtcDatabase(db.Model):
    """Model for storing the database of all possible DTCs."""
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), nullable=False, unique=True)  # e.g., P0301
    description = db.Column(db.Text, nullable=False)  # Standard description
    likely_causes = db.Column(db.Text)  # Common causes
    symptoms = db.Column(db.Text)  # Common symptoms
    notes = db.Column(db.Text)  # Additional notes
    severity = db.Column(db.String(20))  # low, medium, high, critical
    
    def __repr__(self):
        return f'<DtcDatabase {self.code}>'