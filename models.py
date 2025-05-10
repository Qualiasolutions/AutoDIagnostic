from datetime import datetime
# Import the db object from the app module
from app import db

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
    diagnostics = db.relationship('Diagnostic', backref='vehicle', lazy=True)
    
    def __repr__(self):
        return f'<Vehicle {self.make} {self.model} ({self.year})>'

class Diagnostic(db.Model):
    """Model for storing diagnostic sessions."""
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    overall_severity = db.Column(db.String(20), nullable=False, default='unknown')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    visual_analyses = db.relationship('VisualAnalysis', backref='diagnostic', lazy=True)
    audio_analyses = db.relationship('AudioAnalysis', backref='diagnostic', lazy=True)
    diagnoses = db.relationship('DiagnosisResult', backref='diagnostic', lazy=True)
    diy_repairs = db.relationship('DiyRepair', backref='diagnostic', lazy=True)
    professional_repairs = db.relationship('ProfessionalRepair', backref='diagnostic', lazy=True)
    safety_warnings = db.relationship('SafetyWarning', backref='diagnostic', lazy=True)
    
    def __repr__(self):
        return f'<Diagnostic #{self.id} Severity: {self.overall_severity}>'

class VisualAnalysis(db.Model):
    """Model for storing visual analysis results."""
    id = db.Column(db.Integer, primary_key=True)
    diagnostic_id = db.Column(db.Integer, db.ForeignKey('diagnostic.id'), nullable=False)
    issue_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), nullable=False, default='none')
    confidence = db.Column(db.Float, default=0.0)
    
    def __repr__(self):
        return f'<VisualAnalysis {self.issue_type}>'

class AudioAnalysis(db.Model):
    """Model for storing audio analysis results."""
    id = db.Column(db.Integer, primary_key=True)
    diagnostic_id = db.Column(db.Integer, db.ForeignKey('diagnostic.id'), nullable=False)
    symptom_name = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), nullable=False, default='none')
    confidence = db.Column(db.Float, default=0.0)
    transcript = db.Column(db.Text)
    
    def __repr__(self):
        return f'<AudioAnalysis {self.symptom_name}>'

class DiagnosisResult(db.Model):
    """Model for storing diagnosis results."""
    id = db.Column(db.Integer, primary_key=True)
    diagnostic_id = db.Column(db.Integer, db.ForeignKey('diagnostic.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), nullable=False, default='unknown')
    confidence = db.Column(db.Float, default=0.0)
    
    def __repr__(self):
        return f'<DiagnosisResult {self.name}>'

class DiyRepair(db.Model):
    """Model for storing DIY repair recommendations."""
    id = db.Column(db.Integer, primary_key=True)
    diagnostic_id = db.Column(db.Integer, db.ForeignKey('diagnostic.id'), nullable=False)
    issue_name = db.Column(db.String(100), nullable=False)
    repair_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    difficulty = db.Column(db.Integer)
    estimated_cost = db.Column(db.String(50))
    
    # Relationships
    steps = db.relationship('RepairStep', backref='repair', lazy=True)
    
    def __repr__(self):
        return f'<DiyRepair {self.repair_name}>'

class RepairStep(db.Model):
    """Model for storing repair steps."""
    id = db.Column(db.Integer, primary_key=True)
    repair_id = db.Column(db.Integer, db.ForeignKey('diy_repair.id'), nullable=False)
    step_number = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=False)
    
    def __repr__(self):
        return f'<RepairStep {self.step_number}>'

class ProfessionalRepair(db.Model):
    """Model for storing professional repair recommendations."""
    id = db.Column(db.Integer, primary_key=True)
    diagnostic_id = db.Column(db.Integer, db.ForeignKey('diagnostic.id'), nullable=False)
    issue_name = db.Column(db.String(100), nullable=False)
    repair_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    estimated_cost = db.Column(db.String(50))
    
    def __repr__(self):
        return f'<ProfessionalRepair {self.repair_name}>'

class SafetyWarning(db.Model):
    """Model for storing safety warnings."""
    id = db.Column(db.Integer, primary_key=True)
    diagnostic_id = db.Column(db.Integer, db.ForeignKey('diagnostic.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    issue_name = db.Column(db.String(100))
    
    def __repr__(self):
        return f'<SafetyWarning {self.id}>'

class OBDDiagnosticSession(db.Model):
    """Model for storing OBD diagnostic sessions."""
    id = db.Column(db.Integer, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=False)
    diagnostic_id = db.Column(db.Integer, db.ForeignKey('diagnostic.id'), nullable=True)
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