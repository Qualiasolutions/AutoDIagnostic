"""
Diagnostic AI Module
This module uses AI models to enhance vehicle diagnostics and provide repair recommendations.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from openai import OpenAI
from anthropic import Anthropic

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class DiagnosticAI:
    """
    Class that provides AI-enhanced diagnostics using OpenAI and/or Anthropic.
    """
    
    def __init__(self, use_openai=True, use_anthropic=True):
        """
        Initialize the DiagnosticAI.
        
        Args:
            use_openai: Whether to use OpenAI for diagnostics
            use_anthropic: Whether to use Anthropic for diagnostics
        """
        self.use_openai = use_openai
        self.use_anthropic = use_anthropic
        
        # Initialize API clients
        self.openai_client = None
        self.anthropic_client = None
        
        if use_openai:
            openai_api_key = os.environ.get('OPENAI_API_KEY')
            if openai_api_key:
                self.openai_client = OpenAI(api_key=openai_api_key)
                logger.info("OpenAI client initialized")
            else:
                logger.warning("OpenAI API key not found in environment variables")
        
        if use_anthropic:
            anthropic_api_key = os.environ.get('ANTHROPIC_API_KEY')
            if anthropic_api_key:
                self.anthropic_client = Anthropic(api_key=anthropic_api_key)
                logger.info("Anthropic client initialized")
            else:
                logger.warning("Anthropic API key not found in environment variables")
        
        if not self.openai_client and not self.anthropic_client:
            logger.error("No AI clients available. Please provide API keys.")

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
                'analysis': 'No diagnostic trouble codes found.',
                'recommendations': [],
                'severity': 'none'
            }
        
        # Prepare the input for AI models
        prompt = self._generate_dtc_analysis_prompt(dtcs, vehicle_info)
        
        # Try Anthropic first if available
        if self.anthropic_client:
            try:
                analysis = self._analyze_with_anthropic(prompt)
                if analysis:
                    return analysis
            except Exception as e:
                logger.error(f"Error analyzing with Anthropic: {e}")
        
        # Fall back to OpenAI if available
        if self.openai_client:
            try:
                analysis = self._analyze_with_openai(prompt)
                if analysis:
                    return analysis
            except Exception as e:
                logger.error(f"Error analyzing with OpenAI: {e}")
        
        # If both fail or not available, return a basic analysis
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
        prompt = "You are an expert automotive diagnostic technician. "
        prompt += "Please analyze the following diagnostic trouble codes (DTCs) "
        prompt += f"for a {vehicle_info.get('year', 'unknown')} {vehicle_info.get('make', 'unknown')} {vehicle_info.get('model', 'unknown')} "
        prompt += f"with approximately {vehicle_info.get('mileage', 'unknown')} miles.\n\n"
        
        prompt += "Diagnostic Trouble Codes:\n"
        for i, dtc in enumerate(dtcs, 1):
            prompt += f"{i}. {dtc.get('code', 'Unknown')}"
            if dtc.get('description'):
                prompt += f" - {dtc.get('description')}"
            if dtc.get('type'):
                prompt += f" ({dtc.get('type')} code)"
            prompt += "\n"
        
        prompt += "\nPlease provide:\n"
        prompt += "1. A detailed analysis of what these codes indicate about the vehicle's condition\n"
        prompt += "2. Likely causes of these issues\n"
        prompt += "3. Recommended repair steps, from most likely/important to least\n"
        prompt += "4. An overall severity assessment (none, low, medium, high, critical)\n"
        prompt += "5. Estimated repair costs\n\n"
        
        prompt += "Format your response as a JSON object with the following structure:\n"
        prompt += "{\n"
        prompt += '  "analysis": "detailed explanation of the problem",\n'
        prompt += '  "likely_causes": ["cause 1", "cause 2", ...],\n'
        prompt += '  "recommendations": [\n'
        prompt += '    {"step": "step description", "difficulty": 1-5, "estimated_cost": "$XX-$YY", "professional_recommended": true/false},\n'
        prompt += '    ...\n'
        prompt += '  ],\n'
        prompt += '  "severity": "none|low|medium|high|critical",\n'
        prompt += '  "estimated_total_cost": "$XX-$YY"\n'
        prompt += "}\n"
        
        return prompt

    def _analyze_with_anthropic(self, prompt: str) -> Optional[Dict]:
        """
        Use Anthropic's Claude to analyze the diagnostic data.
        
        Args:
            prompt: The analysis prompt
            
        Returns:
            Analysis results as a dictionary, or None if failed
        """
        if not self.anthropic_client:
            return None
        
        try:
            # the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
                system="You are an expert automotive technician specializing in advanced diagnostics. Provide detailed, accurate analysis of vehicle issues using your knowledge of OBD2 systems. Always format responses as JSON."
            )
            
            # Extract the response content
            response_text = response.content[0].text
            
            # Parse the JSON response
            try:
                # Find JSON in the response if it's wrapped in text/markdown
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    return json.loads(json_str)
                else:
                    logger.error("No JSON found in Anthropic response")
                    return None
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing Anthropic response as JSON: {e}")
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
        if not self.openai_client:
            return None
        
        try:
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert automotive technician specializing in advanced diagnostics. Provide detailed, accurate analysis of vehicle issues using your knowledge of OBD2 systems. Always format responses as JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=2000
            )
            
            # Parse the JSON response
            try:
                return json.loads(response.choices[0].message.content)
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing OpenAI response as JSON: {e}")
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
        # Determine severity based on DTC types and counts
        severity = 'low'
        if any(dtc.get('type') == 'permanent' for dtc in dtcs):
            severity = 'high'
        elif len(dtcs) > 3:
            severity = 'medium'
        
        # Create a simple analysis
        analysis = "Multiple diagnostic trouble codes detected. "
        analysis += "These codes indicate potential issues with "
        
        # Check for common code prefixes
        code_prefixes = [dtc.get('code', '')[0:1] for dtc in dtcs if dtc.get('code')]
        if 'P' in code_prefixes:
            analysis += "the powertrain (engine or transmission). "
        if 'B' in code_prefixes:
            analysis += "the body/interior systems. "
        if 'C' in code_prefixes:
            analysis += "the chassis/braking systems. "
        if 'U' in code_prefixes:
            analysis += "the communication network. "
        
        analysis += "Please consult a professional mechanic for a complete diagnosis."
        
        # Create generic recommendations
        recommendations = [
            {
                "step": "Scan vehicle with professional diagnostic tool",
                "difficulty": 1,
                "estimated_cost": "$50-$100",
                "professional_recommended": True
            },
            {
                "step": "Inspect related components for visible damage",
                "difficulty": 2,
                "estimated_cost": "$0",
                "professional_recommended": False
            },
            {
                "step": "Consult with a certified mechanic",
                "difficulty": 1,
                "estimated_cost": "Varies",
                "professional_recommended": True
            }
        ]
        
        return {
            'analysis': analysis,
            'likely_causes': ["Multiple potential causes based on the DTCs detected"],
            'recommendations': recommendations,
            'severity': severity,
            'estimated_total_cost': "Unknown - requires professional diagnosis"
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
        # Prepare the input for AI models
        prompt = self._generate_sensor_analysis_prompt(sensor_data, vehicle_info)
        
        # Try Anthropic first if available
        if self.anthropic_client:
            try:
                analysis = self._analyze_with_anthropic(prompt)
                if analysis:
                    return analysis
            except Exception as e:
                logger.error(f"Error analyzing sensor data with Anthropic: {e}")
        
        # Fall back to OpenAI if available
        if self.openai_client:
            try:
                analysis = self._analyze_with_openai(prompt)
                if analysis:
                    return analysis
            except Exception as e:
                logger.error(f"Error analyzing sensor data with OpenAI: {e}")
        
        # If both fail or not available, return a basic analysis
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
        prompt = "You are an expert automotive diagnostic technician. "
        prompt += "Please analyze the following real-time sensor data "
        prompt += f"for a {vehicle_info.get('year', 'unknown')} {vehicle_info.get('make', 'unknown')} {vehicle_info.get('model', 'unknown')} "
        prompt += f"with approximately {vehicle_info.get('mileage', 'unknown')} miles.\n\n"
        
        prompt += "Sensor Readings:\n"
        for pid, data in sensor_data.items():
            if data.get('value') is not None:
                prompt += f"- {data.get('name', pid)}: {data.get('value')} {data.get('unit', '')}\n"
        
        prompt += "\nPlease provide:\n"
        prompt += "1. An analysis of the sensor readings and what they indicate about vehicle health\n"
        prompt += "2. Any abnormal readings and what they might indicate\n"
        prompt += "3. Recommended actions based on the sensor data\n"
        prompt += "4. Overall vehicle health assessment\n\n"
        
        prompt += "Format your response as a JSON object with the following structure:\n"
        prompt += "{\n"
        prompt += '  "analysis": "detailed explanation of the sensor data",\n'
        prompt += '  "abnormal_readings": [\n'
        prompt += '    {"sensor": "sensor name", "value": "reading", "explanation": "why this is abnormal"},\n'
        prompt += '    ...\n'
        prompt += '  ],\n'
        prompt += '  "recommendations": ["recommendation 1", "recommendation 2", ...],\n'
        prompt += '  "health_status": "excellent|good|fair|poor|critical"\n'
        prompt += "}\n"
        
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
        abnormal_readings = []
        health_status = "good"
        
        # Check for common abnormal readings
        for pid, data in sensor_data.items():
            if data.get('name') == 'Engine RPM' and data.get('value', 0) > 3000:
                abnormal_readings.append({
                    "sensor": "Engine RPM",
                    "value": str(data.get('value')),
                    "explanation": "RPM is unusually high for stationary diagnostics"
                })
            
            elif data.get('name') == 'Coolant Temperature' and data.get('value', 0) > 100:
                abnormal_readings.append({
                    "sensor": "Coolant Temperature",
                    "value": str(data.get('value')),
                    "explanation": "Engine temperature is above normal operating range"
                })
                health_status = "fair"
            
            elif data.get('name') == 'Engine Load' and data.get('value', 0) > 80:
                abnormal_readings.append({
                    "sensor": "Engine Load",
                    "value": str(data.get('value')),
                    "explanation": "Engine load is unusually high for current conditions"
                })
        
        # Create a basic analysis text
        analysis = "Basic sensor data analysis shows "
        if abnormal_readings:
            analysis += f"{len(abnormal_readings)} abnormal readings that may indicate issues. "
            health_status = "fair" if health_status == "good" else health_status
        else:
            analysis += "all readings within normal ranges. "
        
        # Generic recommendations
        recommendations = ["Continue to monitor sensor data for changes"]
        if abnormal_readings:
            recommendations.append("Investigate abnormal readings with a professional mechanic")
        
        return {
            'analysis': analysis,
            'abnormal_readings': abnormal_readings,
            'recommendations': recommendations,
            'health_status': health_status
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
        # Prepare the prompt for AI
        prompt = f"Generate a detailed repair guide for fixing the following issue on a "
        prompt += f"{vehicle_info.get('year', 'unknown')} {vehicle_info.get('make', 'unknown')} {vehicle_info.get('model', 'unknown')}: "
        prompt += f"{issue}\n\n"
        
        prompt += "Please include:\n"
        prompt += "1. A list of required tools and parts\n"
        prompt += "2. Step-by-step repair instructions\n"
        prompt += "3. Safety precautions\n"
        prompt += "4. Estimated time to complete\n"
        prompt += "5. Difficulty level (1-5, where 1 is easiest)\n\n"
        
        prompt += "Format your response as a JSON object with the following structure:\n"
        prompt += "{\n"
        prompt += '  "issue": "restate the issue",\n'
        prompt += '  "tools_required": ["tool 1", "tool 2", ...],\n'
        prompt += '  "parts_required": ["part 1", "part 2", ...],\n'
        prompt += '  "safety_precautions": ["precaution 1", "precaution 2", ...],\n'
        prompt += '  "repair_steps": ["step 1", "step 2", ...],\n'
        prompt += '  "estimated_time": "X hours",\n'
        prompt += '  "difficulty": 1-5,\n'
        prompt += '  "professional_recommended": true/false,\n'
        prompt += '  "notes": "additional information"\n'
        prompt += "}\n"
        
        # Try Anthropic first if available
        if self.anthropic_client:
            try:
                guide = self._repair_guide_with_anthropic(prompt)
                if guide:
                    return guide
            except Exception as e:
                logger.error(f"Error generating repair guide with Anthropic: {e}")
        
        # Fall back to OpenAI if available
        if self.openai_client:
            try:
                guide = self._repair_guide_with_openai(prompt)
                if guide:
                    return guide
            except Exception as e:
                logger.error(f"Error generating repair guide with OpenAI: {e}")
        
        # If both fail, return a basic guide
        return {
            "issue": issue,
            "tools_required": ["Basic mechanic's toolkit", "Diagnostic scanner"],
            "parts_required": ["Varies based on diagnosis"],
            "safety_precautions": [
                "Ensure vehicle is parked on level ground with parking brake engaged",
                "Disconnect battery before working on electrical components",
                "Allow engine to cool before working on hot components",
                "Use appropriate safety equipment (gloves, eye protection)"
            ],
            "repair_steps": [
                "Perform a complete diagnostic scan",
                "Consult with a professional mechanic",
                "Follow manufacturer's repair procedures"
            ],
            "estimated_time": "Varies based on specific issue",
            "difficulty": 3,
            "professional_recommended": True,
            "notes": "This is a generic guide. For specific repair instructions, please consult a professional mechanic or service manual."
        }

    def _repair_guide_with_anthropic(self, prompt: str) -> Optional[Dict]:
        """
        Use Anthropic's Claude to generate a repair guide.
        
        Args:
            prompt: The repair guide prompt
            
        Returns:
            Repair guide as a dictionary, or None if failed
        """
        if not self.anthropic_client:
            return None
        
        try:
            # the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
            response = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
                system="You are an expert automotive technician creating detailed repair guides. Focus on accurate, step-by-step instructions that are safe and follow manufacturer recommendations. Always format responses as JSON."
            )
            
            # Extract the response content
            response_text = response.content[0].text
            
            # Parse the JSON response
            try:
                # Find JSON in the response if it's wrapped in text/markdown
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    json_str = response_text[json_start:json_end]
                    return json.loads(json_str)
                else:
                    logger.error("No JSON found in Anthropic response")
                    return None
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing Anthropic response as JSON: {e}")
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
        if not self.openai_client:
            return None
        
        try:
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert automotive technician creating detailed repair guides. Focus on accurate, step-by-step instructions that are safe and follow manufacturer recommendations. Always format responses as JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                max_tokens=2000
            )
            
            # Parse the JSON response
            try:
                return json.loads(response.choices[0].message.content)
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing OpenAI response as JSON: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            return None