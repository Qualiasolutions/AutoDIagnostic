"""
DTC Database Module - Comprehensive Diagnostic Trouble Code Reference
This module provides a comprehensive database of OBD2 diagnostic trouble codes
with descriptions, symptoms, likely causes, and repair recommendations.
"""

import logging
from typing import Dict, List, Any, Optional
from models import DtcDatabase
from database import db

# Configure logging
logger = logging.getLogger(__name__)

class DTCDatabaseManager:
    """
    Manager class for the DTC database with comprehensive diagnostic codes.
    """
    
    def __init__(self):
        """Initialize the DTC database manager."""
        logger.info("Initializing DTC Database Manager")
    
    def initialize_database(self) -> bool:
        """
        Initialize the DTC database with common diagnostic trouble codes.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if database is already populated
            existing_count = DtcDatabase.query.count()
            if existing_count > 0:
                logger.info(f"DTC database already contains {existing_count} codes")
                return True
            
            logger.info("Populating DTC database with standard codes")
            
            # Get the comprehensive DTC data
            dtc_data = self._get_comprehensive_dtc_data()
            
            # Insert all DTCs into the database
            for dtc_info in dtc_data:
                dtc = DtcDatabase(
                    code=dtc_info['code'],
                    description=dtc_info['description'],
                    likely_causes=dtc_info.get('likely_causes', ''),
                    symptoms=dtc_info.get('symptoms', ''),
                    notes=dtc_info.get('notes', ''),
                    severity=dtc_info.get('severity', 'medium')
                )
                db.session.add(dtc)
            
            # Commit all changes
            db.session.commit()
            
            total_codes = DtcDatabase.query.count()
            logger.info(f"Successfully populated DTC database with {total_codes} codes")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing DTC database: {e}")
            db.session.rollback()
            return False
    
    def get_dtc_info(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive information for a specific DTC code.
        
        Args:
            code: The DTC code (e.g., 'P0301')
            
        Returns:
            Dictionary with DTC information or None if not found
        """
        try:
            dtc = DtcDatabase.query.filter_by(code=code.upper()).first()
            if dtc:
                return {
                    'code': dtc.code,
                    'description': dtc.description,
                    'likely_causes': dtc.likely_causes,
                    'symptoms': dtc.symptoms,
                    'severity': dtc.severity,
                    'notes': dtc.notes
                }
            return None
        except Exception as e:
            logger.error(f"Error getting DTC info for {code}: {e}")
            return None
    
    def search_dtcs(self, query: str) -> List[Dict[str, Any]]:
        """
        Search DTCs by code or description.
        
        Args:
            query: Search query string
            
        Returns:
            List of matching DTC dictionaries
        """
        try:
            query = query.upper()
            dtcs = DtcDatabase.query.filter(
                (DtcDatabase.code.contains(query)) |
                (DtcDatabase.description.contains(query))
            ).limit(50).all()
            
            results = []
            for dtc in dtcs:
                results.append({
                    'code': dtc.code,
                    'description': dtc.description,
                    'severity': dtc.severity
                })
            
            return results
        except Exception as e:
            logger.error(f"Error searching DTCs: {e}")
            return []
    
    def get_dtcs_by_severity(self, severity: str) -> List[Dict[str, Any]]:
        """
        Get DTCs by severity level.
        
        Args:
            severity: Severity level ('critical', 'high', 'medium', 'low')
            
        Returns:
            List of DTC dictionaries
        """
        try:
            dtcs = DtcDatabase.query.filter_by(severity=severity).all()
            results = []
            for dtc in dtcs:
                results.append({
                    'code': dtc.code,
                    'description': dtc.description,
                    'severity': dtc.severity
                })
            return results
        except Exception as e:
            logger.error(f"Error getting DTCs by severity: {e}")
            return []
    
    def _get_comprehensive_dtc_data(self) -> List[Dict[str, Any]]:
        """
        Get comprehensive DTC data for database population.
        
        Returns:
            List of DTC dictionaries with complete information
        """
        return [
            # Powertrain Codes (P0xxx)
            {
                'code': 'P0101',
                'description': 'Mass Airflow (MAF) Circuit Range/Performance',
                'severity': 'medium',
                'likely_causes': 'Dirty/faulty MAF sensor, air filter clogged, vacuum leaks, wiring issues',
                'symptoms': 'Poor fuel economy, rough idle, hesitation during acceleration, black exhaust smoke',
                'notes': 'Clean MAF sensor first before replacement'
            },
            {
                'code': 'P0102',
                'description': 'Mass Airflow (MAF) Circuit Low Input',
                'severity': 'medium',
                'likely_causes': 'Faulty MAF sensor, wiring short to ground, ECM issue',
                'symptoms': 'Engine stalling, poor acceleration, rough idle',
                'notes': 'Check wiring and connections before replacing sensor'
            },
            {
                'code': 'P0103',
                'description': 'Mass Airflow (MAF) Circuit High Input',
                'severity': 'medium',
                'likely_causes': 'Faulty MAF sensor, wiring short to power, ECM issue',
                'symptoms': 'Poor fuel economy, rough idle, engine hesitation',
                'notes': 'Verify proper voltage supply to MAF sensor'
            },
            {
                'code': 'P0110',
                'description': 'Intake Air Temperature (IAT) Circuit Malfunction',
                'severity': 'low',
                'likely_causes': 'Faulty IAT sensor, wiring issues, poor connections',
                'symptoms': 'Poor fuel economy, rough idle, hard starting in cold weather',
                'notes': 'Often integrated with MAF sensor'
            },
            {
                'code': 'P0113',
                'description': 'Intake Air Temperature (IAT) Circuit High Input',
                'severity': 'low',
                'likely_causes': 'Open circuit in IAT sensor, faulty sensor, ECM problem',
                'symptoms': 'Rich fuel mixture, poor fuel economy, rough idle',
                'notes': 'Check resistance of IAT sensor at different temperatures'
            },
            {
                'code': 'P0116',
                'description': 'Engine Coolant Temperature (ECT) Circuit Range/Performance',
                'severity': 'medium',
                'likely_causes': 'Faulty ECT sensor, thermostat stuck, cooling system issues',
                'symptoms': 'Poor fuel economy, overheating, rough idle when cold',
                'notes': 'Verify coolant level and thermostat operation'
            },
            {
                'code': 'P0117',
                'description': 'Engine Coolant Temperature (ECT) Circuit Low Input',
                'severity': 'medium',
                'likely_causes': 'Faulty ECT sensor, short to ground in wiring',
                'symptoms': 'Rich fuel mixture, poor fuel economy, black exhaust smoke',
                'notes': 'ECM thinks engine is always cold'
            },
            {
                'code': 'P0118',
                'description': 'Engine Coolant Temperature (ECT) Circuit High Input',
                'severity': 'medium',
                'likely_causes': 'Faulty ECT sensor, open circuit in wiring',
                'symptoms': 'Poor fuel economy, hard starting when warm, overheating',
                'notes': 'ECM thinks engine is always hot'
            },
            {
                'code': 'P0120',
                'description': 'Throttle Position Sensor (TPS) Circuit Malfunction',
                'severity': 'high',
                'likely_causes': 'Faulty TPS, wiring issues, throttle body problems',
                'symptoms': 'Poor acceleration, rough idle, stalling, erratic RPM',
                'notes': 'Critical for proper engine operation'
            },
            {
                'code': 'P0121',
                'description': 'Throttle Position Sensor (TPS) Circuit Range/Performance',
                'severity': 'high',
                'likely_causes': 'Faulty TPS, throttle body carbon buildup, wiring issues',
                'symptoms': 'Poor acceleration, hesitation, rough idle',
                'notes': 'May require throttle body cleaning and TPS adjustment'
            },
            {
                'code': 'P0130',
                'description': 'Oxygen Sensor Circuit Malfunction (Bank 1, Sensor 1)',
                'severity': 'medium',
                'likely_causes': 'Faulty oxygen sensor, exhaust leaks, wiring issues',
                'symptoms': 'Poor fuel economy, failed emissions test, rough idle',
                'notes': 'Primary O2 sensor affects fuel trim'
            },
            {
                'code': 'P0131',
                'description': 'Oxygen Sensor Circuit Low Voltage (Bank 1, Sensor 1)',
                'severity': 'medium',
                'likely_causes': 'Faulty O2 sensor, exhaust leak, fuel system running lean',
                'symptoms': 'Poor fuel economy, hesitation, rough idle',
                'notes': 'Check for vacuum leaks and exhaust leaks'
            },
            {
                'code': 'P0132',
                'description': 'Oxygen Sensor Circuit High Voltage (Bank 1, Sensor 1)',
                'severity': 'medium',
                'likely_causes': 'Faulty O2 sensor, fuel system running rich, contaminated sensor',
                'symptoms': 'Poor fuel economy, black exhaust smoke, rough idle',
                'notes': 'May be caused by fuel injector problems'
            },
            {
                'code': 'P0133',
                'description': 'Oxygen Sensor Circuit Slow Response (Bank 1, Sensor 1)',
                'severity': 'medium',
                'likely_causes': 'Aging O2 sensor, exhaust leaks, sensor contamination',
                'symptoms': 'Poor fuel economy, failed emissions test, hesitation',
                'notes': 'O2 sensor may need replacement due to age/mileage'
            },
            {
                'code': 'P0171',
                'description': 'System Too Lean (Bank 1)',
                'severity': 'medium',
                'likely_causes': 'Vacuum leaks, MAF sensor issues, fuel pump problems, clogged fuel filter',
                'symptoms': 'Poor acceleration, rough idle, backfiring, poor fuel economy',
                'notes': 'Check for vacuum leaks first'
            },
            {
                'code': 'P0172',
                'description': 'System Too Rich (Bank 1)',
                'severity': 'medium',
                'likely_causes': 'Faulty O2 sensor, leaking fuel injectors, high fuel pressure, dirty air filter',
                'symptoms': 'Poor fuel economy, black exhaust smoke, rough idle, fouled spark plugs',
                'notes': 'May cause catalytic converter damage if not repaired'
            },
            {
                'code': 'P0174',
                'description': 'System Too Lean (Bank 2)',
                'severity': 'medium',
                'likely_causes': 'Vacuum leaks, MAF sensor issues, fuel system problems',
                'symptoms': 'Poor acceleration, rough idle, backfiring',
                'notes': 'Similar to P0171 but affects Bank 2'
            },
            {
                'code': 'P0175',
                'description': 'System Too Rich (Bank 2)',
                'severity': 'medium',
                'likely_causes': 'Faulty O2 sensor, fuel system issues, dirty air filter',
                'symptoms': 'Poor fuel economy, black exhaust smoke, rough idle',
                'notes': 'Similar to P0172 but affects Bank 2'
            },
            {
                'code': 'P0300',
                'description': 'Random/Multiple Cylinder Misfire Detected',
                'severity': 'critical',
                'likely_causes': 'Faulty spark plugs/coils, fuel system issues, vacuum leaks, timing problems',
                'symptoms': 'Rough idle, poor acceleration, engine shaking, check engine light flashing',
                'notes': 'Can cause catalytic converter damage - repair immediately'
            },
            {
                'code': 'P0301',
                'description': 'Cylinder 1 Misfire Detected',
                'severity': 'critical',
                'likely_causes': 'Faulty spark plug, ignition coil, fuel injector, compression issues',
                'symptoms': 'Rough idle, loss of power, engine shaking, poor fuel economy',
                'notes': 'Check spark plug and coil for cylinder 1 first'
            },
            {
                'code': 'P0302',
                'description': 'Cylinder 2 Misfire Detected',
                'severity': 'critical',
                'likely_causes': 'Faulty spark plug, ignition coil, fuel injector, compression issues',
                'symptoms': 'Rough idle, loss of power, engine shaking, poor fuel economy',
                'notes': 'Check spark plug and coil for cylinder 2 first'
            },
            {
                'code': 'P0303',
                'description': 'Cylinder 3 Misfire Detected',
                'severity': 'critical',
                'likely_causes': 'Faulty spark plug, ignition coil, fuel injector, compression issues',
                'symptoms': 'Rough idle, loss of power, engine shaking, poor fuel economy',
                'notes': 'Check spark plug and coil for cylinder 3 first'
            },
            {
                'code': 'P0304',
                'description': 'Cylinder 4 Misfire Detected',
                'severity': 'critical',
                'likely_causes': 'Faulty spark plug, ignition coil, fuel injector, compression issues',
                'symptoms': 'Rough idle, loss of power, engine shaking, poor fuel economy',
                'notes': 'Check spark plug and coil for cylinder 4 first'
            },
            {
                'code': 'P0305',
                'description': 'Cylinder 5 Misfire Detected',
                'severity': 'critical',
                'likely_causes': 'Faulty spark plug, ignition coil, fuel injector, compression issues',
                'symptoms': 'Rough idle, loss of power, engine shaking, poor fuel economy',
                'notes': 'Check spark plug and coil for cylinder 5 first'
            },
            {
                'code': 'P0306',
                'description': 'Cylinder 6 Misfire Detected',
                'severity': 'critical',
                'likely_causes': 'Faulty spark plug, ignition coil, fuel injector, compression issues',
                'symptoms': 'Rough idle, loss of power, engine shaking, poor fuel economy',
                'notes': 'Check spark plug and coil for cylinder 6 first'
            },
            {
                'code': 'P0325',
                'description': 'Knock Sensor 1 Circuit Malfunction (Bank 1)',
                'severity': 'medium',
                'likely_causes': 'Faulty knock sensor, wiring issues, ECM problems',
                'symptoms': 'Engine knock/ping, reduced power, poor fuel economy',
                'notes': 'Can cause engine damage if knock detection fails'
            },
            {
                'code': 'P0335',
                'description': 'Crankshaft Position Sensor Circuit Malfunction',
                'severity': 'critical',
                'likely_causes': 'Faulty crankshaft position sensor, wiring issues, timing belt problems',
                'symptoms': 'Engine won\'t start, stalling, rough idle, no spark/fuel',
                'notes': 'Critical sensor - engine may not run'
            },
            {
                'code': 'P0340',
                'description': 'Camshaft Position Sensor Circuit Malfunction',
                'severity': 'high',
                'likely_causes': 'Faulty camshaft position sensor, timing belt/chain issues, wiring problems',
                'symptoms': 'Hard starting, stalling, rough idle, reduced power',
                'notes': 'May affect fuel injection timing'
            },
            {
                'code': 'P0401',
                'description': 'Exhaust Gas Recirculation (EGR) Flow Insufficient',
                'severity': 'medium',
                'likely_causes': 'Clogged EGR valve, carbon buildup, faulty EGR solenoid',
                'symptoms': 'Engine knock, poor fuel economy, failed emissions test',
                'notes': 'EGR valve cleaning often resolves this code'
            },
            {
                'code': 'P0402',
                'description': 'Exhaust Gas Recirculation (EGR) Flow Excessive',
                'severity': 'medium',
                'likely_causes': 'Stuck open EGR valve, faulty EGR solenoid, vacuum leaks',
                'symptoms': 'Rough idle, stalling, poor acceleration',
                'notes': 'EGR valve may be stuck open'
            },
            {
                'code': 'P0420',
                'description': 'Catalyst System Efficiency Below Threshold (Bank 1)',
                'severity': 'medium',
                'likely_causes': 'Faulty catalytic converter, O2 sensor issues, exhaust leaks, engine misfires',
                'symptoms': 'Poor fuel economy, failed emissions test, sulfur smell',
                'notes': 'Often caused by other engine problems - fix root cause first'
            },
            {
                'code': 'P0430',
                'description': 'Catalyst System Efficiency Below Threshold (Bank 2)',
                'severity': 'medium',
                'likely_causes': 'Faulty catalytic converter, O2 sensor issues, exhaust leaks',
                'symptoms': 'Poor fuel economy, failed emissions test, sulfur smell',
                'notes': 'Similar to P0420 but affects Bank 2'
            },
            {
                'code': 'P0440',
                'description': 'Evaporative Emission Control System Malfunction',
                'severity': 'low',
                'likely_causes': 'Loose gas cap, EVAP canister issues, purge valve problems',
                'symptoms': 'Fuel smell, failed emissions test, gas tank pressure issues',
                'notes': 'Check gas cap first - often the simple fix'
            },
            {
                'code': 'P0441',
                'description': 'Evaporative Emission Control System Incorrect Purge Flow',
                'severity': 'low',
                'likely_causes': 'Faulty purge valve, EVAP canister issues, vacuum leaks',
                'symptoms': 'Rough idle, fuel smell, poor fuel economy',
                'notes': 'Purge valve may be stuck open or closed'
            },
            {
                'code': 'P0442',
                'description': 'Evaporative Emission Control System Leak Detected (Small Leak)',
                'severity': 'low',
                'likely_causes': 'Loose gas cap, small EVAP system leaks, faulty charcoal canister',
                'symptoms': 'Fuel smell, failed emissions test',
                'notes': 'Small leak in EVAP system - check gas cap and lines'
            },
            {
                'code': 'P0446',
                'description': 'Evaporative Emission Control System Vent Control Circuit Malfunction',
                'severity': 'low',
                'likely_causes': 'Faulty EVAP vent solenoid, wiring issues, blocked vent',
                'symptoms': 'Difficulty filling gas tank, fuel smell',
                'notes': 'EVAP vent valve may be stuck closed'
            },
            {
                'code': 'P0455',
                'description': 'Evaporative Emission Control System Leak Detected (Large Leak)',
                'severity': 'medium',
                'likely_causes': 'Missing/loose gas cap, cracked EVAP lines, faulty canister',
                'symptoms': 'Strong fuel smell, failed emissions test',
                'notes': 'Large leak in EVAP system - check all components'
            },
            {
                'code': 'P0456',
                'description': 'Evaporative Emission Control System Leak Detected (Very Small Leak)',
                'severity': 'low',
                'likely_causes': 'Loose gas cap, very small EVAP leaks, gas cap seal',
                'symptoms': 'Slight fuel smell, failed emissions test',
                'notes': 'Often gas cap related - very small leak'
            },
            {
                'code': 'P0500',
                'description': 'Vehicle Speed Sensor Malfunction',
                'severity': 'medium',
                'likely_causes': 'Faulty VSS, wiring issues, transmission problems',
                'symptoms': 'Speedometer not working, transmission shift issues, ABS problems',
                'notes': 'May affect transmission shift points'
            },
            {
                'code': 'P0505',
                'description': 'Idle Air Control System Malfunction',
                'severity': 'medium',
                'likely_causes': 'Dirty/faulty IAC valve, carbon buildup, vacuum leaks',
                'symptoms': 'Rough/erratic idle, stalling, high/low idle RPM',
                'notes': 'Clean throttle body and IAC valve first'
            },
            {
                'code': 'P0506',
                'description': 'Idle Air Control System RPM Lower Than Expected',
                'severity': 'medium',
                'likely_causes': 'Dirty IAC valve, vacuum leaks, carbon buildup',
                'symptoms': 'Low idle RPM, stalling, rough idle',
                'notes': 'Idle speed too low'
            },
            {
                'code': 'P0507',
                'description': 'Idle Air Control System RPM Higher Than Expected',
                'severity': 'medium',
                'likely_causes': 'Dirty IAC valve, vacuum leaks, throttle body issues',
                'symptoms': 'High idle RPM, racing engine at idle',
                'notes': 'Idle speed too high'
            },
            {
                'code': 'P0600',
                'description': 'Serial Communication Link Malfunction',
                'severity': 'high',
                'likely_causes': 'ECM internal failure, wiring issues, module communication problems',
                'symptoms': 'Various system malfunctions, multiple warning lights',
                'notes': 'May require ECM replacement or reprogramming'
            },
            {
                'code': 'P0605',
                'description': 'Internal Control Module ROM Error',
                'severity': 'critical',
                'likely_causes': 'ECM internal failure, corrupted software, power supply issues',
                'symptoms': 'Engine may not run, multiple system failures',
                'notes': 'Serious ECM problem - professional diagnosis required'
            },
            {
                'code': 'P0700',
                'description': 'Transmission Control System Malfunction',
                'severity': 'high',
                'likely_causes': 'Transmission internal problems, TCM issues, wiring problems',
                'symptoms': 'Transmission shifting problems, no shifting, harsh shifts',
                'notes': 'Indicates transmission system problem - scan TCM for specific codes'
            },
            {
                'code': 'P0705',
                'description': 'Transmission Range Sensor Circuit Malfunction (PRNDL Input)',
                'severity': 'high',
                'likely_causes': 'Faulty neutral safety switch, wiring issues, shifter problems',
                'symptoms': 'Won\'t start in park, backup lights not working, shifting issues',
                'notes': 'Also called Park/Neutral Position switch'
            },
            {
                'code': 'P0715',
                'description': 'Input/Turbine Speed Sensor Circuit Malfunction',
                'severity': 'high',
                'likely_causes': 'Faulty input speed sensor, wiring issues, transmission problems',
                'symptoms': 'Harsh/delayed shifting, speedometer issues, no shift',
                'notes': 'Critical for transmission operation'
            },
            {
                'code': 'P0720',
                'description': 'Output Speed Sensor Circuit Malfunction',
                'severity': 'high',
                'likely_causes': 'Faulty output speed sensor, wiring issues, final drive problems',
                'symptoms': 'Harsh/erratic shifting, speedometer problems, ABS issues',
                'notes': 'Used for transmission shift control and speedometer'
            }
        ]


# Create global instance
dtc_database = DTCDatabaseManager()

def get_dtc_info(code: str) -> Optional[Dict[str, Any]]:
    """
    Get DTC information for a specific code.
    
    Args:
        code: DTC code string
        
    Returns:
        DTC information dictionary or None
    """
    return dtc_database.get_dtc_info(code)

def search_dtcs(query: str) -> List[Dict[str, Any]]:
    """
    Search DTCs by query string.
    
    Args:
        query: Search query
        
    Returns:
        List of matching DTC dictionaries
    """
    return dtc_database.search_dtcs(query)

def initialize_dtc_database() -> bool:
    """
    Initialize the DTC database with standard codes.
    
    Returns:
        True if successful, False otherwise
    """
    return dtc_database.initialize_database() 