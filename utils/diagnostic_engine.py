"""
OBD2 Diagnostic Engine Module
Analyzes OBD2 diagnostic data including DTCs and sensor readings to provide
comprehensive vehicle diagnostics with AI enhancement.
"""

import logging
from typing import Dict, List, Any, Optional
import json

# Import AI module
from utils.diagnostic_ai import DiagnosticAI

# Configure logging
logger = logging.getLogger(__name__)


def analyze_obd2_data(dtcs, sensor_readings, vehicle_info):
    """
    Analyze OBD2 diagnostic data and return comprehensive results.
    
    Args:
        dtcs: List of Diagnostic Trouble Codes
        sensor_readings: List of sensor reading objects
        vehicle_info: Dictionary containing vehicle information
        
    Returns:
        Dictionary with diagnosis, recommendations, and severity
    """
    try:
        # Initialize the results dictionary
        results = {
            "diagnoses": [],
            "severity": "none",
            "diy_repairs": [],
            "professional_repairs": [],
            "safety_warnings": []
        }
        
        # Convert DTCs to analysis format
        dtc_list = []
        if dtcs:
            for dtc in dtcs:
                dtc_list.append({
                    'code': dtc.code,
                    'description': dtc.description,
                    'type': dtc.type
                })
        
        # Convert sensor readings to analysis format
        sensor_data = {}
        if sensor_readings:
            for reading in sensor_readings:
                sensor_data[reading.name] = {
                    'value': reading.value,
                    'unit': reading.unit,
                    'pid': reading.pid
                }
        
        # Determine severity based on DTCs
        severity = determine_severity(dtc_list)
        results["severity"] = severity
        
        # Generate diagnoses from DTCs
        if dtc_list:
            for dtc in dtc_list:
                # Create diagnosis from each DTC
                diagnosis = {
                    "name": dtc['code'],
                    "description": dtc['description'],
                    "confidence": 0.9,  # DTCs have high confidence
                    "severity": severity
                }
                results["diagnoses"].append(diagnosis)
        
        # Analyze sensor data for anomalies
        sensor_issues = analyze_sensor_anomalies(sensor_data)
        for issue in sensor_issues:
            results["diagnoses"].append(issue)
        
        # Generate basic repair recommendations
        if dtc_list:
            # Add professional repair recommendation
            results["professional_repairs"].append({
                "issue_name": "Diagnostic Trouble Codes Detected",
                "repair_name": "Professional Diagnostic Service",
                "description": f"Have a qualified technician perform detailed diagnosis for {len(dtc_list)} DTCs detected",
                "estimated_cost": "$80-$200"
            })
            
            # Add DTC clearing as DIY option
            results["diy_repairs"].append({
                "issue_name": "Clear Diagnostic Codes",
                "repair_name": "Clear DTCs",
                "description": "Clear diagnostic trouble codes after repairs are completed",
                "difficulty": 1,
                "estimated_cost": "$0",
                "steps": [
                    "Connect OBD2 scanner to vehicle",
                    "Turn ignition to ON position (engine off)",
                    "Select 'Clear DTCs' or 'Erase Codes' option",
                    "Confirm the clearing operation",
                    "Turn off ignition and restart engine",
                    "Verify codes are cleared"
                ]
            })
        
        # Add safety warnings based on severity and specific codes
        if severity in ["high", "critical"]:
            results["safety_warnings"].append({
                "text": "Vehicle has serious diagnostic codes that may affect safety and reliability. Have the vehicle inspected immediately.",
                "issue_name": "Critical Vehicle Issues"
            })
        
        # Check for specific critical codes
        critical_codes = ['P0301', 'P0302', 'P0303', 'P0304', 'P0305', 'P0306', 'P0307', 'P0308']
        misfire_codes = [dtc['code'] for dtc in dtc_list if dtc['code'] in critical_codes]
        if misfire_codes:
            results["safety_warnings"].append({
                "text": "Engine misfire detected. Continued driving may cause catalytic converter damage. Reduce speed and seek immediate repair.",
                "issue_name": "Engine Misfire"
            })
        
        # If no issues detected, add positive result
        if not dtc_list and not sensor_issues:
            results["diagnoses"].append({
                "name": "No Issues Detected",
                "description": "Vehicle's diagnostic system shows no trouble codes or sensor anomalies",
                "confidence": 0.95,
                "severity": "none"
            })
            results["severity"] = "none"
        
        # Use AI to enhance the diagnostic results
        ai_enhanced_results = enhance_with_ai(results, dtc_list, sensor_data, vehicle_info)
        if ai_enhanced_results:
            results.update(ai_enhanced_results)
        
        return results
    
    except Exception as e:
        logger.error(f"Error analyzing OBD2 data: {str(e)}")
        return {
            "diagnoses": [{
                "name": "Diagnostic Error",
                "description": f"An error occurred during diagnostic analysis: {str(e)}",
                "confidence": 0.5,
                "severity": "unknown"
            }],
            "severity": "unknown",
            "diy_repairs": [],
            "professional_repairs": [],
            "safety_warnings": [{
                "text": "The diagnostic system encountered an error. Please try again or consult a professional.",
                "issue_name": "System Error"
            }]
        }


def determine_severity(dtc_list):
    """
    Determine the overall severity based on DTC codes.
    
    Args:
        dtc_list: List of DTC dictionaries
        
    Returns:
        Severity level string
    """
    if not dtc_list:
        return "none"
    
    # Critical codes that require immediate attention
    critical_codes = [
        'P0301', 'P0302', 'P0303', 'P0304', 'P0305', 'P0306', 'P0307', 'P0308',  # Misfires
        'P0200', 'P0201', 'P0202', 'P0203', 'P0204', 'P0205', 'P0206', 'P0207',  # Injector circuits
        'P0340', 'P0341', 'P0342', 'P0343',  # Camshaft position sensor
        'P0335', 'P0336', 'P0337', 'P0338',  # Crankshaft position sensor
    ]
    
    # High severity codes
    high_codes = [
        'P0100', 'P0101', 'P0102', 'P0103',  # MAF sensor
        'P0110', 'P0111', 'P0112', 'P0113',  # Intake air temp
        'P0170', 'P0171', 'P0172', 'P0173', 'P0174', 'P0175',  # Fuel trim
        'P0300',  # Random misfire
    ]
    
    # Check for critical codes
    for dtc in dtc_list:
        if dtc['code'] in critical_codes:
            return "critical"
    
    # Check for high severity codes
    for dtc in dtc_list:
        if dtc['code'] in high_codes:
            return "high"
    
    # Default to medium for any DTCs present
    return "medium"


def analyze_sensor_anomalies(sensor_data):
    """
    Analyze sensor readings for anomalies.
    
    Args:
        sensor_data: Dictionary of sensor readings
        
    Returns:
        List of sensor-related diagnoses
    """
    issues = []
    
    try:
        # Check engine temperature
        if 'COOLANT_TEMP' in sensor_data:
            temp = sensor_data['COOLANT_TEMP']['value']
            if temp > 100:  # Over 100°C
                issues.append({
                    "name": "Engine Overheating",
                    "description": f"Engine coolant temperature is {temp}°C, which is above normal operating range",
                    "confidence": 0.8,
                    "severity": "high"
                })
            elif temp < 70:  # Under 70°C when warm
                issues.append({
                    "name": "Engine Not Reaching Operating Temperature",
                    "description": f"Engine coolant temperature is {temp}°C, which may indicate thermostat issues",
                    "confidence": 0.6,
                    "severity": "medium"
                })
        
        # Check RPM at idle
        if 'RPM' in sensor_data:
            rpm = sensor_data['RPM']['value']
            if rpm > 1200:  # High idle
                issues.append({
                    "name": "High Idle RPM",
                    "description": f"Engine is idling at {rpm} RPM, which is higher than normal (700-900 RPM)",
                    "confidence": 0.7,
                    "severity": "medium"
                })
            elif rpm < 500 and rpm > 0:  # Very low idle
                issues.append({
                    "name": "Low Idle RPM",
                    "description": f"Engine is idling at {rpm} RPM, which may cause stalling",
                    "confidence": 0.7,
                    "severity": "medium"
                })
        
        # Check fuel trims
        if 'SHORT_FUEL_TRIM_1' in sensor_data:
            stft = sensor_data['SHORT_FUEL_TRIM_1']['value']
            if abs(stft) > 10:  # More than 10% fuel trim
                trim_type = "lean" if stft > 0 else "rich"
                issues.append({
                    "name": f"Fuel System Running {trim_type.title()}",
                    "description": f"Short term fuel trim is {stft}%, indicating the engine is running {trim_type}",
                    "confidence": 0.8,
                    "severity": "medium"
                })
        
        # Check oxygen sensor voltage
        if 'O2_VOLTAGE' in sensor_data or 'OXYGEN_SENSOR_1' in sensor_data:
            o2_key = 'O2_VOLTAGE' if 'O2_VOLTAGE' in sensor_data else 'OXYGEN_SENSOR_1'
            o2_voltage = sensor_data[o2_key]['value']
            if o2_voltage < 0.1 or o2_voltage > 0.9:  # Stuck lean or rich
                condition = "lean" if o2_voltage < 0.1 else "rich"
                issues.append({
                    "name": f"Oxygen Sensor Stuck {condition.title()}",
                    "description": f"Oxygen sensor voltage is {o2_voltage}V, indicating it may be stuck {condition}",
                    "confidence": 0.7,
                    "severity": "medium"
                })
    
    except Exception as e:
        logger.error(f"Error analyzing sensor anomalies: {str(e)}")
    
    return issues


def enhance_with_ai(results, dtc_list, sensor_data, vehicle_info):
    """
    Enhance diagnostic results using AI analysis.
    
    Args:
        results: Current diagnostic results
        dtc_list: List of DTCs
        sensor_data: Dictionary of sensor readings
        vehicle_info: Vehicle information
        
    Returns:
        Enhanced results or None if AI is not available
    """
    try:
        # Check if we have AI libraries available
        ai = DiagnosticAI(use_openai=False, use_anthropic=True)
        
        if not ai.use_anthropic:
            logger.warning("No AI libraries available for diagnostic enhancement")
            return None
        
        # Format the current results for the AI
        dtcs_str = ""
        for dtc in dtc_list:
            dtcs_str += f"- {dtc['code']}: {dtc['description']} (Type: {dtc['type']})\n"
        
        sensor_str = ""
        for name, data in sensor_data.items():
            sensor_str += f"- {name}: {data['value']} {data['unit']}\n"
        
        diagnoses_str = ""
        for diagnosis in results["diagnoses"]:
            diagnoses_str += f"- {diagnosis['name']}: {diagnosis['description']}\n"
        
        # Create the prompt for AI enhancement
        prompt = f"""You are an expert automotive diagnostic technician analyzing OBD2 data.
Please enhance the following diagnostic results for a vehicle:

Vehicle: {vehicle_info.get('year', 'Unknown')} {vehicle_info.get('make', 'Unknown')} {vehicle_info.get('model', 'Unknown')}
Mileage: {vehicle_info.get('mileage', 'Unknown')}

Diagnostic Trouble Codes:
{dtcs_str if dtcs_str else "No DTCs detected"}

Sensor Readings:
{sensor_str if sensor_str else "No sensor anomalies detected"}

Current Analysis:
{diagnoses_str}

Current Severity: {results['severity']}

Your task is to provide professional diagnostic insights and improve the repair recommendations.

Please provide:
1. Enhanced diagnoses with professional technical analysis
2. Specific DIY repair procedures where appropriate
3. Professional repair recommendations with accurate cost estimates
4. Critical safety warnings if applicable

Format your response as a JSON object with the following structure:
{{
  "enhanced_diagnoses": [
    {{
      "name": "Diagnosis name",
      "description": "Professional technical description",
      "confidence": 0.0-1.0,
      "severity": "critical|high|medium|low|none"
    }}
  ],
  "enhanced_severity": "critical|high|medium|low|none",
  "enhanced_diy_repairs": [
    {{
      "issue_name": "Issue being repaired",
      "repair_name": "Specific repair procedure name",
      "description": "Detailed technical description",
      "difficulty": 1-5,
      "estimated_cost": "$XX-$YY",
      "steps": ["Specific step 1", "Specific step 2", "..."]
    }}
  ],
  "enhanced_professional_repairs": [
    {{
      "issue_name": "Issue being repaired", 
      "repair_name": "Professional repair procedure",
      "description": "Technical description of repair",
      "estimated_cost": "$XX-$YY"
    }}
  ],
  "enhanced_safety_warnings": [
    {{
      "text": "Safety warning text",
      "issue_name": "Related issue name"
    }}
  ]
}}

Provide only the JSON response with professional automotive expertise.
"""
        
        # Get AI analysis
        analysis = ai._analyze_with_anthropic(prompt)
        if analysis:
            logger.info("Successfully enhanced OBD2 diagnostics with AI")
            enhanced_results = {}
            
            # Update results with AI enhancements
            if analysis.get('enhanced_diagnoses'):
                enhanced_results['diagnoses'] = analysis['enhanced_diagnoses']
            
            if analysis.get('enhanced_severity'):
                enhanced_results['severity'] = analysis['enhanced_severity']
            
            if analysis.get('enhanced_diy_repairs'):
                enhanced_results['diy_repairs'] = analysis['enhanced_diy_repairs']
            
            if analysis.get('enhanced_professional_repairs'):
                enhanced_results['professional_repairs'] = analysis['enhanced_professional_repairs']
            
            if analysis.get('enhanced_safety_warnings'):
                enhanced_results['safety_warnings'] = analysis['enhanced_safety_warnings']
            
            return enhanced_results
        
        return None
    
    except Exception as e:
        logger.error(f"Error in AI enhancement: {str(e)}")
        return None


# Legacy function for backward compatibility
def analyze_diagnostic_data(diagnostic_data, vehicle_info):
    """
    Legacy function maintained for backward compatibility.
    Routes to OBD2-specific analysis.
    """
    # Extract OBD2 data if present
    obd_results = diagnostic_data.get('obd_results', {})
    dtcs = obd_results.get('dtcs', [])
    sensor_readings = obd_results.get('sensor_readings', [])
    
    return analyze_obd2_data(dtcs, sensor_readings, vehicle_info)