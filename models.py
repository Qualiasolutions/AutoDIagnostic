from datetime import datetime
from app import db

class Vehicle(db.Model):
    """Model for storing vehicle information."""
    id = db.Column(db.Integer, primary_key=True)
    make = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    mileage = db.Column(db.Integer)
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