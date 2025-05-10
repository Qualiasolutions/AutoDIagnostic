"""
Diagnostic AI Module
This module uses AI models to enhance vehicle diagnostics and provide repair recommendations.
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Union

# Import AI libraries
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)


class DiagnosticAI:
    """
    Class that provides AI-enhanced diagnostics using OpenAI and/or Anthropic.
    """
    
    def __init__(self, use_openai: bool = True, use_anthropic: bool = True):
        """
        Initialize the DiagnosticAI.
        
        Args:
            use_openai: Whether to use OpenAI for diagnostics
            use_anthropic: Whether to use Anthropic for diagnostics
        """
        self.use_openai = use_openai and OPENAI_AVAILABLE
        self.use_anthropic = use_anthropic and ANTHROPIC_AVAILABLE
        
        # Check API keys
        if self.use_openai:
            openai_api_key = os.environ.get("OPENAI_API_KEY")
            if not openai_api_key:
                logger.warning("OpenAI API key not found, disabling OpenAI")
                self.use_openai = False
            else:
                self.openai_client = openai.OpenAI(api_key=openai_api_key)
                logger.info("OpenAI client initialized")
        
        if self.use_anthropic:
            anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not anthropic_api_key:
                logger.warning("Anthropic API key not found, disabling Anthropic")
                self.use_anthropic = False
            else:
                self.anthropic_client = anthropic.Anthropic(api_key=anthropic_api_key)
                logger.info("Anthropic client initialized")
        
        if not self.use_openai and not self.use_anthropic:
            logger.warning("No AI services available, will use basic analysis only")
    
    def analyze_dtcs(self, dtcs: List[Dict], vehicle_info: Dict) -> Dict:
        """
        Analyze Diagnostic Trouble Codes (DTCs) and provide repair recommendations.
        
        Args:
            dtcs: List of DTC dictionaries with code, type, and description
            vehicle_info: Dictionary with vehicle information
            
        Returns:
            Dictionary with analysis, recommendations, and severity
        """
        if not dtcs:
            return {
                "summary": "No diagnostic trouble codes detected.",
                "severity": "none",
                "likely_causes": [],
                "recommended_tests": [],
                "safety_concerns": None,
                "repair_options": {
                    "diy": [],
                    "professional": []
                }
            }
        
        # Generate the prompt for AI analysis
        prompt = self._generate_dtc_analysis_prompt(dtcs, vehicle_info)
        
        # Try using Anthropic first if available
        if self.use_anthropic:
            try:
                analysis = self._analyze_with_anthropic(prompt)
                if analysis:
                    logger.info("Successfully analyzed DTCs with Anthropic")
                    return analysis
            except Exception as e:
                logger.error(f"Error analyzing DTCs with Anthropic: {e}")
        
        # Fall back to OpenAI if available
        if self.use_openai:
            try:
                analysis = self._analyze_with_openai(prompt)
                if analysis:
                    logger.info("Successfully analyzed DTCs with OpenAI")
                    return analysis
            except Exception as e:
                logger.error(f"Error analyzing DTCs with OpenAI: {e}")
        
        # If all AI methods fail, provide a basic analysis
        logger.warning("AI analysis failed, using basic analysis")
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
        # Base information about the vehicle
        vehicle_str = f"Vehicle: {vehicle_info.get('year', 'Unknown')} {vehicle_info.get('make', 'Unknown')} {vehicle_info.get('model', 'Unknown')}\n"
        vehicle_str += f"Mileage: {vehicle_info.get('mileage', 'Unknown')}\n"
        if vehicle_info.get('vin'):
            vehicle_str += f"VIN: {vehicle_info.get('vin')}\n"
        
        # Format DTC information
        dtc_str = "Diagnostic Trouble Codes (DTCs):\n"
        for dtc in dtcs:
            dtc_str += f"- Code: {dtc.get('code', 'Unknown')}\n"
            dtc_str += f"  Description: {dtc.get('description', 'Unknown')}\n"
            dtc_str += f"  Type: {dtc.get('type', 'stored')}\n"
        
        # Create the full prompt
        prompt = f"""You are an expert automotive diagnostic AI assistant.
Please analyze the following diagnostic trouble codes (DTCs) for this vehicle:

{vehicle_str}
{dtc_str}

Based on these codes, please provide a comprehensive analysis that includes:

1. A brief summary of the issues detected
2. The overall severity of the issues (critical, high, medium, low, or none)
3. Likely causes of these issues
4. Recommended diagnostic tests to further pinpoint the problem
5. Any safety concerns that the driver should be aware of
6. Repair options, including:
   - DIY repairs (if feasible) with difficulty rating (1-5), estimated cost, tools required, and step-by-step instructions
   - Professional repairs that would be recommended, with estimated cost

Format your response as a JSON object with the following structure:
{{
  "summary": "Brief summary of the issues",
  "severity": "critical|high|medium|low|none",
  "likely_causes": ["Cause 1", "Cause 2", ...],
  "recommended_tests": ["Test 1", "Test 2", ...],
  "safety_concerns": "Description of safety concerns or null if none",
  "repair_options": {{
    "diy": [
      {{
        "name": "Repair name",
        "description": "Detailed description",
        "difficulty": 1-5,
        "cost": "$XX-$YY",
        "tools_required": ["Tool 1", "Tool 2", ...],
        "steps": ["Step 1", "Step 2", ...]
      }},
      ...
    ],
    "professional": [
      {{
        "name": "Repair name",
        "description": "Detailed description",
        "cost": "$XX-$YY",
        "specialist_type": "Type of specialist or null",
        "notes": "Additional notes or null"
      }},
      ...
    ]
  }}
}}

Ensure your response is accurate, helpful, and formatted exactly as the JSON structure above.
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
            # the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                temperature=0.2,
                system="You are an expert automotive diagnostic AI. Provide thorough, accurate analyses and repair recommendations based on diagnostic trouble codes and vehicle information. Format your response as JSON exactly as requested.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract JSON from the response
            if response:
                content = ""
                # Access the content safely, handling different response formats
                if hasattr(response, 'content') and response.content:
                    if isinstance(response.content, list) and len(response.content) > 0:
                        if hasattr(response.content[0], 'text'):
                            content = response.content[0].text
                        else:
                            content = str(response.content[0])
                    else:
                        content = str(response.content)
                elif hasattr(response, 'completion'):
                    content = response.completion
                
                # Find JSON in the content
                if content:
                    json_start = content.find("{")
                    json_end = content.rfind("}") + 1
                    if json_start >= 0 and json_end > json_start:
                        json_str = content[json_start:json_end]
                        try:
                            result = json.loads(json_str)
                            return result
                        except json.JSONDecodeError as e:
                            logger.error(f"Error parsing Anthropic JSON response: {e}")
                            logger.debug(f"Raw response: {content}")
            
            return None
        
        except Exception as e:
            logger.error(f"Error calling Anthropic API: {e}")
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
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                temperature=0.2,
                messages=[
                    {"role": "system", "content": "You are an expert automotive diagnostic AI. Provide thorough, accurate analyses and repair recommendations based on diagnostic trouble codes and vehicle information. Format your response as JSON exactly as requested."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            if response and response.choices and response.choices[0].message.content:
                try:
                    return json.loads(response.choices[0].message.content)
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing OpenAI JSON response: {e}")
                    logger.debug(f"Raw response: {response.choices[0].message.content}")
                    return None
            
            return None
        
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
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
        # Count DTCs by system
        powertrain_count = sum(1 for dtc in dtcs if dtc.get('code', '').startswith('P'))
        chassis_count = sum(1 for dtc in dtcs if dtc.get('code', '').startswith('C'))
        body_count = sum(1 for dtc in dtcs if dtc.get('code', '').startswith('B'))
        network_count = sum(1 for dtc in dtcs if dtc.get('code', '').startswith('U'))
        
        # Determine severity based on number and type of DTCs
        severity = "low"
        safety_concerns = None
        
        if powertrain_count > 3 or chassis_count > 2 or network_count > 1:
            severity = "high"
            safety_concerns = "Multiple systems are affected. Vehicle may not be safe to drive. Please consult a professional mechanic before driving."
        elif powertrain_count > 1 or chassis_count > 0:
            severity = "medium"
            safety_concerns = "Some critical systems may be affected. Drive with caution and have the vehicle inspected soon."
        
        # Generate summary
        summary = f"Found {len(dtcs)} diagnostic trouble code(s): "
        summary += f"{powertrain_count} powertrain, {chassis_count} chassis, {body_count} body, {network_count} network."
        
        # Basic likely causes
        likely_causes = ["Electronic control module detected a fault in one or more systems"]
        if powertrain_count > 0:
            likely_causes.append("Possible engine or transmission issues")
        if chassis_count > 0:
            likely_causes.append("Possible ABS, stability control, or suspension issues")
        if body_count > 0:
            likely_causes.append("Possible issues with body electronics, lighting, or climate control")
        if network_count > 0:
            likely_causes.append("Possible communication issues between control modules")
        
        # Basic recommended tests
        recommended_tests = [
            "Connect a professional-grade scan tool to read detailed information",
            "Verify that all connectors related to the affected systems are secure and free from corrosion",
            "Check for any related recalls or technical service bulletins (TSBs)"
        ]
        
        return {
            "summary": summary,
            "severity": severity,
            "likely_causes": likely_causes,
            "recommended_tests": recommended_tests,
            "safety_concerns": safety_concerns,
            "repair_options": {
                "diy": [
                    {
                        "name": "Basic Inspection",
                        "description": "Visually inspect related components for obvious issues",
                        "difficulty": 1,
                        "cost": "$0",
                        "tools_required": ["Flashlight", "Basic hand tools"],
                        "steps": [
                            "Visually inspect the affected systems for disconnected wires, broken components, or leaks",
                            "Check for loose connections at the battery terminals",
                            "Ensure all fuses related to the affected systems are intact",
                            "If you don't find any obvious issues, seek professional diagnosis"
                        ]
                    }
                ],
                "professional": [
                    {
                        "name": "Professional Diagnostic Service",
                        "description": "Have a professional mechanic or dealership perform a complete diagnostic",
                        "cost": "$80-$150",
                        "specialist_type": "Automotive Technician",
                        "notes": "A professional will have the specialized tools and knowledge to properly diagnose the issues"
                    }
                ]
            }
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
        if not sensor_data:
            return {
                "summary": "No sensor data available for analysis.",
                "issues_detected": [],
                "recommendations": []
            }
        
        # Generate the prompt for AI analysis
        prompt = self._generate_sensor_analysis_prompt(sensor_data, vehicle_info)
        
        # Try using Anthropic first if available
        if self.use_anthropic:
            try:
                analysis = self._analyze_with_anthropic(prompt)
                if analysis:
                    logger.info("Successfully analyzed sensor data with Anthropic")
                    return analysis
            except Exception as e:
                logger.error(f"Error analyzing sensor data with Anthropic: {e}")
        
        # Fall back to OpenAI if available
        if self.use_openai:
            try:
                analysis = self._analyze_with_openai(prompt)
                if analysis:
                    logger.info("Successfully analyzed sensor data with OpenAI")
                    return analysis
            except Exception as e:
                logger.error(f"Error analyzing sensor data with OpenAI: {e}")
        
        # If all AI methods fail, provide a basic analysis
        logger.warning("AI analysis failed, using basic analysis")
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
        # Base information about the vehicle
        vehicle_str = f"Vehicle: {vehicle_info.get('year', 'Unknown')} {vehicle_info.get('make', 'Unknown')} {vehicle_info.get('model', 'Unknown')}\n"
        vehicle_str += f"Mileage: {vehicle_info.get('mileage', 'Unknown')}\n"
        if vehicle_info.get('vin'):
            vehicle_str += f"VIN: {vehicle_info.get('vin')}\n"
        
        # Format sensor information
        sensor_str = "Sensor Readings:\n"
        for pid, data in sensor_data.items():
            sensor_str += f"- {data.get('name', pid)}: {data.get('value')} {data.get('unit', '')}\n"
        
        # Create the full prompt
        prompt = f"""You are an expert automotive diagnostic AI assistant.
Please analyze the following sensor data for this vehicle:

{vehicle_str}
{sensor_str}

Based on these sensor readings, please provide a comprehensive analysis that includes:

1. A brief summary of the vehicle's operating condition
2. Any issues or abnormal readings detected, with explanations
3. Recommendations for addressing any issues found

Format your response as a JSON object with the following structure:
{{
  "summary": "Brief summary of the vehicle's condition",
  "issues_detected": [
    {{
      "sensor": "Name of the sensor showing abnormal reading",
      "reading": "The abnormal reading",
      "expected_range": "The normal range for this sensor",
      "severity": "high|medium|low",
      "explanation": "Explanation of what this abnormal reading may indicate"
    }},
    ...
  ],
  "recommendations": [
    "Recommendation 1",
    "Recommendation 2",
    ...
  ]
}}

If all readings are normal, return an empty array for issues_detected.
Ensure your response is accurate, helpful, and formatted exactly as the JSON structure above.
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
        issues = []
        recommendations = []
        
        # Check for common issues based on sensor readings
        # These are very simplified rules and would be much more sophisticated in a real implementation
        
        # Check engine temperature
        for pid, data in sensor_data.items():
            if data.get('name') == 'Coolant Temperature':
                temp = data.get('value', 0)
                if temp > 105:  # Celsius
                    issues.append({
                        "sensor": "Coolant Temperature",
                        "reading": f"{temp} {data.get('unit', '°C')}",
                        "expected_range": "85-105 °C",
                        "severity": "high",
                        "explanation": "Engine is overheating. This can cause serious engine damage if not addressed."
                    })
                    recommendations.append("Stop driving immediately and allow the engine to cool down")
                    recommendations.append("Check coolant level and look for leaks")
                    recommendations.append("Inspect radiator, fan, and thermostat functionality")
                elif temp < 75 and temp != 0:  # Exclude 0 as it might be a sensor error
                    issues.append({
                        "sensor": "Coolant Temperature",
                        "reading": f"{temp} {data.get('unit', '°C')}",
                        "expected_range": "85-105 °C",
                        "severity": "low",
                        "explanation": "Engine may be running too cool. This can affect fuel efficiency and emissions."
                    })
                    recommendations.append("Check if the thermostat is stuck open")
                    recommendations.append("Ensure the temperature sensor is working correctly")
            
            # Check engine load
            elif data.get('name') == 'Engine Load':
                load = data.get('value', 0)
                if load > 85:
                    issues.append({
                        "sensor": "Engine Load",
                        "reading": f"{load} {data.get('unit', '%')}",
                        "expected_range": "20-80%",
                        "severity": "medium",
                        "explanation": "Engine is under heavy load. This could indicate a mechanical issue, clogged air filter, or other restriction."
                    })
                    recommendations.append("Check for clogged air filter or intake restrictions")
                    recommendations.append("Inspect for exhaust restrictions")
                    recommendations.append("Check for mechanical issues causing increased resistance")
            
            # Check RPM
            elif data.get('name') == 'Engine RPM':
                rpm = data.get('value', 0)
                if rpm > 1000 and rpm < 500:  # Assuming the vehicle is idling
                    issues.append({
                        "sensor": "Engine RPM",
                        "reading": f"{rpm} {data.get('unit', 'rpm')}",
                        "expected_range": "600-900 rpm at idle",
                        "severity": "low",
                        "explanation": "Irregular idle speed. This could indicate issues with the idle air control valve, throttle body, or fuel system."
                    })
                    recommendations.append("Clean the throttle body and check for carbon buildup")
                    recommendations.append("Inspect idle air control valve functionality")
                    recommendations.append("Check for vacuum leaks")
            
            # Check fuel trims
            elif data.get('name') in ['Short Term Fuel Trim - Bank 1', 'Long Term Fuel Trim - Bank 1']:
                trim = data.get('value', 0)
                if trim > 15 or trim < -15:
                    issues.append({
                        "sensor": data.get('name'),
                        "reading": f"{trim} {data.get('unit', '%')}",
                        "expected_range": "-10% to +10%",
                        "severity": "medium",
                        "explanation": "Fuel trim is out of normal range. Positive values indicate the system is running lean (too much air or not enough fuel). Negative values indicate rich condition (too much fuel or not enough air)."
                    })
                    if trim > 15:
                        recommendations.append("Check for vacuum leaks, faulty fuel injectors, or clogged fuel filter")
                        recommendations.append("Inspect the mass air flow (MAF) sensor and oxygen sensors")
                    else:
                        recommendations.append("Check for leaking fuel injectors or faulty fuel pressure regulator")
                        recommendations.append("Inspect oxygen sensors and MAF sensor")
        
        # Generate summary based on issues found
        if not issues:
            summary = "All sensor readings are within normal operating ranges. The vehicle appears to be running properly."
        else:
            severity_count = {
                "high": sum(1 for issue in issues if issue.get('severity') == 'high'),
                "medium": sum(1 for issue in issues if issue.get('severity') == 'medium'),
                "low": sum(1 for issue in issues if issue.get('severity') == 'low')
            }
            
            if severity_count["high"] > 0:
                summary = f"Critical issues detected. Found {len(issues)} abnormal sensor readings including {severity_count['high']} high severity issues."
            elif severity_count["medium"] > 0:
                summary = f"Performance issues detected. Found {len(issues)} abnormal sensor readings including {severity_count['medium']} medium severity issues."
            else:
                summary = f"Minor issues detected. Found {len(issues)} abnormal sensor readings with low severity."
        
        return {
            "summary": summary,
            "issues_detected": issues,
            "recommendations": recommendations
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
        # Generate the prompt for AI analysis
        prompt = f"""You are an expert automotive repair technician.
Please create a detailed repair guide for the following issue:

Issue: {issue}

Vehicle: {vehicle_info.get('year', 'Unknown')} {vehicle_info.get('make', 'Unknown')} {vehicle_info.get('model', 'Unknown')}
Mileage: {vehicle_info.get('mileage', 'Unknown')}

Please provide a comprehensive repair guide that includes:

1. A descriptive title for the repair
2. Difficulty level on a scale of 1-5 (1 being easiest, 5 being most difficult)
3. Estimated time to complete
4. Estimated cost of parts
5. Tools required
6. Parts required
7. Safety precautions
8. Detailed step-by-step instructions
9. Tips for success
10. Common mistakes to avoid

Format your response as a JSON object with the following structure:
{{
  "title": "Repair title",
  "difficulty": 1-5,
  "estimated_time": "X hours",
  "estimated_cost": "$X-$Y",
  "tools_required": ["Tool 1", "Tool 2", ...],
  "parts_required": ["Part 1", "Part 2", ...],
  "safety_precautions": ["Precaution 1", "Precaution 2", ...],
  "steps": ["Step 1", "Step 2", ...],
  "tips": ["Tip 1", "Tip 2", ...],
  "common_mistakes": ["Mistake 1", "Mistake 2", ...]
}}

Ensure your response is accurate, helpful, and formatted exactly as the JSON structure above.
"""
        
        # Try using Anthropic first if available
        if self.use_anthropic:
            try:
                guide = self._repair_guide_with_anthropic(prompt)
                if guide:
                    logger.info("Successfully generated repair guide with Anthropic")
                    return guide
            except Exception as e:
                logger.error(f"Error generating repair guide with Anthropic: {e}")
        
        # Fall back to OpenAI if available
        if self.use_openai:
            try:
                guide = self._repair_guide_with_openai(prompt)
                if guide:
                    logger.info("Successfully generated repair guide with OpenAI")
                    return guide
            except Exception as e:
                logger.error(f"Error generating repair guide with OpenAI: {e}")
        
        # If all AI methods fail, provide a basic guide
        logger.warning("AI repair guide generation failed, using basic template")
        return {
            "title": f"Repair guide for: {issue}",
            "difficulty": 3,
            "estimated_time": "Varies",
            "estimated_cost": "Varies",
            "tools_required": ["Basic hand tools", "Diagnostic scanner"],
            "parts_required": ["Depends on specific diagnosis"],
            "safety_precautions": [
                "Disconnect the battery before working on electrical components",
                "Allow the engine to cool before working on hot components",
                "Use proper jack stands when working underneath the vehicle",
                "Wear safety glasses and gloves"
            ],
            "steps": [
                "Consult a professional repair manual specific to your vehicle make, model, and year",
                "Perform a thorough diagnosis before replacing parts",
                "Follow manufacturer-recommended procedures"
            ],
            "tips": ["Consider seeking professional assistance for this repair"],
            "common_mistakes": ["Replacing parts without proper diagnosis", "Skipping safety precautions"]
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
            # the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=4000,
                temperature=0.3,
                system="You are an expert automotive repair technician. Provide detailed, accurate repair guides based on the specific vehicle and issue described.",
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Extract JSON from the response
            if response:
                content = ""
                # Access the content safely, handling different response formats
                if hasattr(response, 'content') and response.content:
                    if isinstance(response.content, list) and len(response.content) > 0:
                        if hasattr(response.content[0], 'text'):
                            content = response.content[0].text
                        else:
                            content = str(response.content[0])
                    else:
                        content = str(response.content)
                elif hasattr(response, 'completion'):
                    content = response.completion
                
                # Find JSON in the content
                if content:
                    json_start = content.find("{")
                    json_end = content.rfind("}") + 1
                    if json_start >= 0 and json_end > json_start:
                        json_str = content[json_start:json_end]
                        try:
                            result = json.loads(json_str)
                            return result
                        except json.JSONDecodeError as e:
                            logger.error(f"Error parsing Anthropic JSON response: {e}")
                            logger.debug(f"Raw response: {content}")
            
            return None
        
        except Exception as e:
            logger.error(f"Error calling Anthropic API: {e}")
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
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                temperature=0.3,
                messages=[
                    {"role": "system", "content": "You are an expert automotive repair technician. Provide detailed, accurate repair guides based on the specific vehicle and issue described."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            if response and response.choices and response.choices[0].message.content:
                try:
                    return json.loads(response.choices[0].message.content)
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing OpenAI JSON response: {e}")
                    logger.debug(f"Raw response: {response.choices[0].message.content}")
                    return None
            
            return None
        
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            return None