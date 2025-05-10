"""
Diagnostic AI Module
This module uses AI models to enhance vehicle diagnostics and provide repair recommendations.
"""

import json
import logging
import os
import sys
from typing import Dict, List, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

class DiagnosticAI:
    """
    Class that provides AI-enhanced diagnostics using OpenAI and/or Anthropic.
    """
    
    def __init__(self, use_openai: bool = False, use_anthropic: bool = True):
        """
        Initialize the DiagnosticAI.
        
        Args:
            use_openai: Whether to use OpenAI for diagnostics
            use_anthropic: Whether to use Anthropic for diagnostics
        """
        self.use_openai = use_openai
        self.use_anthropic = use_anthropic
        
        # Check if API keys are available
        if use_openai:
            self.openai_key = os.environ.get('OPENAI_API_KEY')
            if not self.openai_key:
                logger.warning("OPENAI_API_KEY not set. OpenAI functions will not work.")
                self.use_openai = False
        
        if use_anthropic:
            self.anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
            if not self.anthropic_key:
                logger.warning("ANTHROPIC_API_KEY not set. Anthropic functions will not work.")
                self.use_anthropic = False
        
        if not self.use_openai and not self.use_anthropic:
            logger.warning("No AI service enabled. AI diagnostics will not be available.")
    
    def analyze_dtcs(self, dtcs: List[Dict], vehicle_info: Dict) -> Dict:
        """
        Analyze Diagnostic Trouble Codes (DTCs) and provide repair recommendations.
        
        Args:
            dtcs: List of DTC dictionaries with code, type, and description
            vehicle_info: Dictionary with vehicle information
            
        Returns:
            Dictionary with analysis, recommendations, and severity
        """
        # Generate the prompt for analysis
        prompt = self._generate_dtc_analysis_prompt(dtcs, vehicle_info)
        
        # Try to analyze with Anthropic first, then with OpenAI, then fall back to basic analysis
        if self.use_anthropic:
            try:
                analysis = self._analyze_with_anthropic(prompt)
                if analysis:
                    logger.info("Successfully analyzed DTCs with Anthropic")
                    return analysis
            except Exception as e:
                logger.error(f"Error analyzing DTCs with Anthropic: {e}")
        
        if self.use_openai:
            try:
                analysis = self._analyze_with_openai(prompt)
                if analysis:
                    logger.info("Successfully analyzed DTCs with OpenAI")
                    return analysis
            except Exception as e:
                logger.error(f"Error analyzing DTCs with OpenAI: {e}")
        
        # Fallback to basic analysis without AI
        logger.warning("Falling back to basic DTC analysis without AI")
        return self._basic_dtc_analysis(dtcs)
    
    def _generate_dtc_analysis_prompt(self, dtcs: List[Dict], vehicle_info: Dict) -> str:
        """
        Generate a prompt for the AI to analyze DTCs.
        
        Args:
            dtcs: List of DTCs
            vehicle_info: Vehicle information
            
        Returns:
            Prompt string for AI analysis
        """
        # Format vehicle info
        year = vehicle_info.get('year', 'Unknown')
        make = vehicle_info.get('make', 'Unknown')
        model = vehicle_info.get('model', 'Unknown')
        mileage = vehicle_info.get('mileage', 'Unknown')
        vin = vehicle_info.get('vin', 'Unknown')
        
        # Format DTCs
        dtc_details = []
        for dtc in dtcs:
            dtc_details.append(f"- {dtc.get('code')}: {dtc.get('description', 'Unknown description')} (Type: {dtc.get('type', 'stored')})")
        
        dtc_list = "\n".join(dtc_details) if dtc_details else "No DTCs provided"
        
        # Generate the prompt
        prompt = f"""You are an expert automotive diagnostic assistant. You're analyzing DTCs (Diagnostic Trouble Codes) for a vehicle and will provide a detailed analysis.

Vehicle Information:
- Year: {year}
- Make: {make}
- Model: {model}
- Mileage: {mileage}
- VIN: {vin}

Diagnostic Trouble Codes:
{dtc_list}

Based on these DTCs and the vehicle information, please provide:
1. A detailed analysis of the likely problems in the vehicle
2. The severity of the issues (critical, high, medium, low, or none)
3. Recommended repair options, including DIY fixes where possible
4. Estimated costs for repairs
5. Any safety warnings the owner should be aware of

Format your response as a JSON object with the following structure:
{
  "diagnoses": [
    {
      "name": "Short name of the diagnosis",
      "description": "Detailed description of the problem",
      "confidence": 0.0-1.0,
      "severity": "critical|high|medium|low|none"
    }
  ],
  "severity": "critical|high|medium|low|none",
  "diy_repairs": [
    {
      "issue_name": "Name of the issue being repaired",
      "repair_name": "Name of the repair procedure",
      "description": "Detailed description of the repair",
      "difficulty": 1-5,
      "estimated_cost": "$XX-$YY",
      "steps": ["Step 1", "Step 2", "..."]
    }
  ],
  "professional_repairs": [
    {
      "issue_name": "Name of the issue being repaired",
      "repair_name": "Name of the repair procedure",
      "description": "Detailed description of the repair",
      "estimated_cost": "$XX-$YY"
    }
  ],
  "safety_warnings": [
    {
      "text": "Warning text",
      "issue_name": "Related issue"
    }
  ]
}

Provide only the JSON response, with no additional text before or after.
"""
        return prompt
    
    def _analyze_with_anthropic(self, prompt: str) -> Optional[Dict]:
        """
        Use Anthropic's Claude to analyze the diagnostic data.
        
        Args:
            prompt: The analysis prompt
            
        Returns:
            Analysis results as a dictionary, or None if failed
        """
        try:
            # Import Anthropic
            import anthropic
            from anthropic import Anthropic
            
            # Initialize the client
            client = Anthropic(api_key=self.anthropic_key)
            
            # Call Claude to analyze the data
            # the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract the JSON response
            if response.content and len(response.content) > 0:
                content_block = response.content[0]
                if hasattr(content_block, 'text'):
                    response_text = content_block.text
                    # Try to parse the JSON response
                    try:
                        return json.loads(response_text)
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing Anthropic JSON response: {e}")
                        # Try to extract just the JSON part
                        import re
                        json_match = re.search(r'({[\s\S]*})', response_text)
                        if json_match:
                            try:
                                return json.loads(json_match.group(1))
                            except json.JSONDecodeError:
                                logger.error("Failed to parse extracted JSON from Anthropic response")
            
            logger.error("Failed to get valid response from Anthropic")
            return None
            
        except Exception as e:
            logger.error(f"Error using Anthropic for analysis: {e}")
            return None
    
    def _analyze_with_openai(self, prompt: str) -> Optional[Dict]:
        """
        Use OpenAI's GPT models to analyze the diagnostic data.
        
        Args:
            prompt: The analysis prompt
            
        Returns:
            Analysis results as a dictionary, or None if failed
        """
        try:
            # Import OpenAI
            from openai import OpenAI
            
            # Initialize the client
            client = OpenAI(api_key=self.openai_key)
            
            # Call OpenAI to analyze the data
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert automotive diagnostic assistant."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # Extract the JSON response
            if response.choices and len(response.choices) > 0:
                message = response.choices[0].message
                content = message.content
                
                if content:
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing OpenAI JSON response: {e}")
            
            logger.error("Failed to get valid response from OpenAI")
            return None
            
        except Exception as e:
            logger.error(f"Error using OpenAI for analysis: {e}")
            return None
    
    def _basic_dtc_analysis(self, dtcs: List[Dict]) -> Dict:
        """
        Provide a basic analysis of DTCs without using AI.
        This is a fallback when AI is not available.
        
        Args:
            dtcs: List of DTCs
            
        Returns:
            Basic analysis as a dictionary
        """
        # Basic severity assessment
        severity = "medium"  # Default severity
        
        # Look for known critical codes
        critical_prefixes = ['P0', 'P2']  # These are often more serious
        for dtc in dtcs:
            code = dtc.get('code', '')
            if any(code.startswith(prefix) for prefix in critical_prefixes):
                severity = "high"
                break
        
        # Create diagnoses
        diagnoses = []
        for dtc in dtcs:
            diagnoses.append({
                "name": dtc.get('code', 'Unknown Code'),
                "description": dtc.get('description', 'Unknown issue'),
                "confidence": 0.8,
                "severity": severity
            })
        
        # Create safety warnings
        safety_warnings = []
        if severity == "high":
            safety_warnings.append({
                "text": "These diagnostic codes may indicate serious issues. Please have your vehicle inspected by a professional mechanic.",
                "issue_name": "Potential Safety Issue"
            })
        
        # Create a basic repair recommendation
        diy_repairs = []
        professional_repairs = [{
            "issue_name": "Multiple diagnostic codes",
            "repair_name": "Professional diagnostic service",
            "description": "Have a professional mechanic perform a complete diagnostic scan and inspection",
            "estimated_cost": "$80-$150"
        }]
        
        return {
            "diagnoses": diagnoses,
            "severity": severity,
            "diy_repairs": diy_repairs,
            "professional_repairs": professional_repairs,
            "safety_warnings": safety_warnings
        }
    
    def analyze_sensor_data(self, sensor_data: Dict, vehicle_info: Dict) -> Dict:
        """
        Analyze real-time sensor data and provide insights.
        
        Args:
            sensor_data: Dictionary of sensor readings
            vehicle_info: Dictionary with vehicle information
            
        Returns:
            Dictionary with analysis and recommendations
        """
        # Generate the prompt for analysis
        prompt = self._generate_sensor_analysis_prompt(sensor_data, vehicle_info)
        
        # Try to analyze with Anthropic first, then with OpenAI, then fall back to basic analysis
        if self.use_anthropic:
            try:
                analysis = self._analyze_with_anthropic(prompt)
                if analysis:
                    logger.info("Successfully analyzed sensor data with Anthropic")
                    return analysis
            except Exception as e:
                logger.error(f"Error analyzing sensor data with Anthropic: {e}")
        
        if self.use_openai:
            try:
                analysis = self._analyze_with_openai(prompt)
                if analysis:
                    logger.info("Successfully analyzed sensor data with OpenAI")
                    return analysis
            except Exception as e:
                logger.error(f"Error analyzing sensor data with OpenAI: {e}")
        
        # Fallback to basic analysis without AI
        logger.warning("Falling back to basic sensor data analysis without AI")
        return self._basic_sensor_analysis(sensor_data)
    
    def _generate_sensor_analysis_prompt(self, sensor_data: Dict, vehicle_info: Dict) -> str:
        """
        Generate a prompt for the AI to analyze sensor data.
        
        Args:
            sensor_data: Dictionary of sensor readings
            vehicle_info: Vehicle information
            
        Returns:
            Prompt string for AI analysis
        """
        # Format vehicle info
        year = vehicle_info.get('year', 'Unknown')
        make = vehicle_info.get('make', 'Unknown')
        model = vehicle_info.get('model', 'Unknown')
        mileage = vehicle_info.get('mileage', 'Unknown')
        
        # Format sensor data
        sensor_readings = []
        for key, data in sensor_data.items():
            value = data.get('value', 'Unknown')
            unit = data.get('unit', '')
            sensor_readings.append(f"- {key}: {value} {unit}")
        
        sensor_list = "\n".join(sensor_readings) if sensor_readings else "No sensor data provided"
        
        # Generate the prompt
        prompt = f"""You are an expert automotive diagnostic assistant. You're analyzing live sensor data from a vehicle's OBD2 system and will provide insights.

Vehicle Information:
- Year: {year}
- Make: {make}
- Model: {model}
- Mileage: {mileage}

Sensor Readings:
{sensor_list}

Based on these sensor readings and the vehicle information, please provide:
1. An analysis of whether these readings are normal or indicate potential issues
2. Any anomalies or concerning values in the data
3. Possible issues that might be developing based on these readings
4. Recommended actions the owner should take

Format your response as a JSON object with the following structure:
{{
  "analysis": "Overall analysis of the sensor data",
  "anomalies": [
    {{
      "sensor": "Name of sensor with anomalous reading",
      "reading": "The reading value",
      "normal_range": "The normal range for this sensor",
      "severity": "critical|high|medium|low|none",
      "possible_causes": ["Cause 1", "Cause 2"]
    }}
  ],
  "potential_issues": [
    {{
      "name": "Name of potential issue",
      "description": "Description of the issue",
      "confidence": 0.0-1.0,
      "related_sensors": ["Sensor 1", "Sensor 2"]
    }}
  ],
  "recommendations": [
    "Recommendation 1",
    "Recommendation 2"
  ],
  "severity": "critical|high|medium|low|none"
}}

Provide only the JSON response, with no additional text before or after.
"""
        return prompt
    
    def _basic_sensor_analysis(self, sensor_data: Dict) -> Dict:
        """
        Provide a basic analysis of sensor data without using AI.
        This is a fallback when AI is not available.
        
        Args:
            sensor_data: Dictionary of sensor readings
            
        Returns:
            Basic analysis as a dictionary
        """
        # Basic analysis of common sensors
        analysis = "Sensor readings appear to be within normal ranges."
        anomalies = []
        potential_issues = []
        severity = "none"
        
        # Check engine temperature
        if 'coolant_temp' in sensor_data:
            temp_value = sensor_data['coolant_temp'].get('value', 0)
            if temp_value > 100:  # Over 100°C is concerning
                anomalies.append({
                    "sensor": "Engine Coolant Temperature",
                    "reading": f"{temp_value} °C",
                    "normal_range": "80-95 °C",
                    "severity": "high",
                    "possible_causes": ["Low coolant level", "Faulty thermostat", "Cooling system issue"]
                })
                potential_issues.append({
                    "name": "Engine Overheating",
                    "description": "Engine temperature is higher than normal operating range",
                    "confidence": 0.8,
                    "related_sensors": ["coolant_temp"]
                })
                severity = "high"
                analysis = "Engine temperature is higher than normal. This could indicate cooling system issues."
        
        # Check engine RPM
        if 'rpm' in sensor_data:
            rpm_value = sensor_data['rpm'].get('value', 0)
            if rpm_value > 1000 and 'speed' in sensor_data:
                speed_value = sensor_data['speed'].get('value', 0)
                if speed_value < 5:  # High RPM but not moving
                    anomalies.append({
                        "sensor": "Engine RPM",
                        "reading": f"{rpm_value} RPM",
                        "normal_range": "700-900 RPM (idle)",
                        "severity": "medium",
                        "possible_causes": ["Vacuum leak", "Idle control issue", "Throttle body problem"]
                    })
                    potential_issues.append({
                        "name": "High Idle RPM",
                        "description": "Engine is idling at a higher than normal RPM",
                        "confidence": 0.7,
                        "related_sensors": ["rpm", "speed"]
                    })
                    if severity != "high":
                        severity = "medium"
                    analysis = "Engine is idling at a higher than normal RPM, which could indicate vacuum leaks or idle control issues."
        
        # Generate recommendations
        recommendations = ["Monitor the vehicle for any changes in performance or warning lights"]
        
        if severity == "high":
            recommendations.append("Have your vehicle inspected by a professional mechanic as soon as possible")
        elif severity == "medium":
            recommendations.append("Consider having your vehicle checked during your next service appointment")
        
        return {
            "analysis": analysis,
            "anomalies": anomalies,
            "potential_issues": potential_issues,
            "recommendations": recommendations,
            "severity": severity
        }
    
    def generate_repair_guide(self, issue: str, vehicle_info: Dict) -> Dict:
        """
        Generate a detailed repair guide for a specific issue.
        
        Args:
            issue: Description of the issue to fix
            vehicle_info: Dictionary with vehicle information
            
        Returns:
            Dictionary with repair steps, tools needed, and difficulty
        """
        # Generate the prompt for analysis
        prompt = f"""You are an expert automotive repair technician. You're creating a detailed repair guide for a specific issue.

Vehicle Information:
- Year: {vehicle_info.get('year', 'Unknown')}
- Make: {vehicle_info.get('make', 'Unknown')}
- Model: {vehicle_info.get('model', 'Unknown')}
- Mileage: {vehicle_info.get('mileage', 'Unknown')}

Issue to Fix: {issue}

Please provide a detailed repair guide including:
1. A list of necessary tools and parts
2. Step-by-step instructions
3. Safety precautions
4. Estimated time required
5. Difficulty level (1-5, where 1 is easiest)
6. Estimated cost range for parts

Format your response as a JSON object with the following structure:
{{
  "repair_name": "Name of the repair procedure",
  "description": "Overall description of the repair",
  "tools_needed": ["Tool 1", "Tool 2", "..."],
  "parts_needed": [
    {{
      "name": "Part name",
      "estimated_cost": "$XX-$YY",
      "part_number": "OEM or aftermarket part number (if available)"
    }}
  ],
  "difficulty": 1-5,
  "estimated_time": "X-Y hours",
  "safety_precautions": ["Precaution 1", "Precaution 2", "..."],
  "steps": ["Step 1", "Step 2", "..."],
  "tips": ["Tip 1", "Tip 2", "..."]
}}

Provide only the JSON response, with no additional text before or after.
"""
        
        # Try with Anthropic first
        if self.use_anthropic:
            try:
                repair_guide = self._repair_guide_with_anthropic(prompt)
                if repair_guide:
                    logger.info("Successfully generated repair guide with Anthropic")
                    return repair_guide
            except Exception as e:
                logger.error(f"Error generating repair guide with Anthropic: {e}")
        
        # Then try with OpenAI
        if self.use_openai:
            try:
                repair_guide = self._repair_guide_with_openai(prompt)
                if repair_guide:
                    logger.info("Successfully generated repair guide with OpenAI")
                    return repair_guide
            except Exception as e:
                logger.error(f"Error generating repair guide with OpenAI: {e}")
        
        # If all else fails, return a basic message
        logger.warning("Unable to generate repair guide. No AI services available.")
        return {
            "repair_name": issue,
            "description": "Unable to generate a detailed repair guide. Please consult a professional mechanic.",
            "tools_needed": ["Unknown"],
            "parts_needed": [{"name": "Unknown", "estimated_cost": "Unknown"}],
            "difficulty": 3,
            "estimated_time": "Unknown",
            "safety_precautions": ["Always disconnect the battery before working on electrical components",
                                 "Use proper safety equipment including gloves and eye protection"],
            "steps": ["Consult a repair manual or professional mechanic for this repair"],
            "tips": ["This repair may require specialized tools or knowledge"]
        }
    
    def _repair_guide_with_anthropic(self, prompt: str) -> Optional[Dict]:
        """
        Use Anthropic's Claude to generate a repair guide.
        
        Args:
            prompt: The repair guide prompt
            
        Returns:
            Repair guide as a dictionary, or None if failed
        """
        try:
            # Import Anthropic
            import anthropic
            from anthropic import Anthropic
            
            # Initialize the client
            client = Anthropic(api_key=self.anthropic_key)
            
            # Call Claude to generate the repair guide
            # the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
            response = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract the JSON response
            if response.content and len(response.content) > 0:
                content_block = response.content[0]
                if hasattr(content_block, 'text'):
                    response_text = content_block.text
                    # Try to parse the JSON response
                    try:
                        return json.loads(response_text)
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing Anthropic JSON response: {e}")
                        # Try to extract just the JSON part
                        import re
                        json_match = re.search(r'({[\s\S]*})', response_text)
                        if json_match:
                            try:
                                return json.loads(json_match.group(1))
                            except json.JSONDecodeError:
                                logger.error("Failed to parse extracted JSON from Anthropic response")
            
            logger.error("Failed to get valid response from Anthropic")
            return None
            
        except Exception as e:
            logger.error(f"Error using Anthropic for repair guide: {e}")
            return None
    
    def _repair_guide_with_openai(self, prompt: str) -> Optional[Dict]:
        """
        Use OpenAI's GPT models to generate a repair guide.
        
        Args:
            prompt: The repair guide prompt
            
        Returns:
            Repair guide as a dictionary, or None if failed
        """
        try:
            # Import OpenAI
            from openai import OpenAI
            
            # Initialize the client
            client = OpenAI(api_key=self.openai_key)
            
            # Call OpenAI to generate the repair guide
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert automotive repair technician."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            # Extract the JSON response
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                if content:
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing OpenAI JSON response: {e}")
            
            logger.error("Failed to get valid response from OpenAI")
            return None
            
        except Exception as e:
            logger.error(f"Error using OpenAI for repair guide: {e}")
            return None