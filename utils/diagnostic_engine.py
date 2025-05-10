"""
Diagnostic Engine Module
Combines results from OBD2 data, image analysis, and audio analysis to provide
comprehensive vehicle diagnostics.
"""

import logging
from typing import Dict, List, Any, Optional
import json

# Import AI module
from utils.diagnostic_ai import DiagnosticAI

# Configure logging
logger = logging.getLogger(__name__)


def analyze_diagnostic_data(diagnostic_data, vehicle_info):
    """
    Analyze the collected diagnostic data and return results.
    
    Args:
        diagnostic_data: Dictionary containing image and voice analysis results
        vehicle_info: Dictionary containing vehicle information
        
    Returns:
        Dictionary with diagnosis, recommendations, and severity
    """
    try:
        # Initialize the results dictionary
        results = {
            "diagnoses": [],
            "severity": "unknown",
            "diy_repairs": [],
            "professional_repairs": [],
            "safety_warnings": []
        }
        
        # Extract data from image analysis
        image_results = diagnostic_data.get('image_results', {})
        voice_results = diagnostic_data.get('voice_results', {})
        obd_results = diagnostic_data.get('obd_results', {})
        
        # Combine all detected issues
        all_issues = []
        
        # Add issues from image analysis
        if image_results:
            image_issues = image_results.get('potential_issues', [])
            confirmed_issues = image_results.get('confirmed_issues', [])
            additional_issues = image_results.get('additional_issues', [])
            
            # Add all issues with their source
            for issue in image_issues:
                all_issues.append({
                    "source": "image",
                    "description": issue,
                    "confidence": image_results.get('confidence_scores', {}).get(issue.split(' - ')[0].lower().replace(' ', '_') if ' - ' in issue else 'unknown', 0.5)
                })
            
            for issue in confirmed_issues:
                all_issues.append({
                    "source": "image_ai",
                    "description": issue,
                    "confidence": 0.8  # AI-confirmed issues have higher confidence
                })
            
            for issue in additional_issues:
                all_issues.append({
                    "source": "image_ai",
                    "description": issue,
                    "confidence": 0.7
                })
            
            # Add recommendations
            recommendations = image_results.get('recommendations', [])
            for rec in recommendations:
                if "repair" in rec.lower() or "replace" in rec.lower() or "service" in rec.lower():
                    results["diy_repairs"].append({
                        "issue_name": "Visual Issue",
                        "repair_name": rec,
                        "description": rec,
                        "difficulty": 3  # Default difficulty
                    })
        
        # Add issues from voice analysis
        if voice_results:
            voice_issues = voice_results.get('potential_issues', [])
            confirmed_issues = voice_results.get('confirmed_issues', [])
            additional_issues = voice_results.get('additional_issues', [])
            
            # Add all issues with their source
            for issue in voice_issues:
                all_issues.append({
                    "source": "audio",
                    "description": issue,
                    "confidence": voice_results.get('confidence_scores', {}).get(issue.split(' - ')[0].lower().replace(' ', '_') if ' - ' in issue else 'unknown', 0.5)
                })
            
            for issue in confirmed_issues:
                all_issues.append({
                    "source": "audio_ai",
                    "description": issue,
                    "confidence": 0.8
                })
            
            for issue in additional_issues:
                all_issues.append({
                    "source": "audio_ai",
                    "description": issue,
                    "confidence": 0.7
                })
            
            # Add recommendations from voice analysis
            recommendations = voice_results.get('recommendations', [])
            for rec in recommendations:
                if "repair" in rec.lower() or "replace" in rec.lower() or "service" in rec.lower():
                    results["professional_repairs"].append({
                        "issue_name": "Audio-Detected Issue",
                        "repair_name": rec,
                        "description": rec
                    })
        
        # Add issues from OBD analysis
        if obd_results:
            dtcs = obd_results.get('dtcs', [])
            for dtc in dtcs:
                all_issues.append({
                    "source": "obd",
                    "description": f"{dtc.get('code')} - {dtc.get('description', 'Unknown')}",
                    "confidence": 0.9  # OBD codes have high confidence
                })
            
            sensor_issues = obd_results.get('sensor_issues', [])
            for issue in sensor_issues:
                all_issues.append({
                    "source": "obd",
                    "description": issue,
                    "confidence": 0.8
                })
            
            # Add DTC-based repairs
            dtc_repairs = obd_results.get('repairs', [])
            for repair in dtc_repairs:
                if repair.get('diy', False):
                    results["diy_repairs"].append({
                        "issue_name": repair.get('issue', 'OBD Detected Issue'),
                        "repair_name": repair.get('name', 'Repair'),
                        "description": repair.get('description', ''),
                        "difficulty": repair.get('difficulty', 3)
                    })
                else:
                    results["professional_repairs"].append({
                        "issue_name": repair.get('issue', 'OBD Detected Issue'),
                        "repair_name": repair.get('name', 'Repair'),
                        "description": repair.get('description', '')
                    })
        
        # Determine overall severity
        severity_levels = {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1,
            "none": 0,
            "unknown": -1
        }
        
        # Get severity from different sources
        image_severity = image_results.get('severity', 'unknown')
        voice_severity = voice_results.get('severity', 'unknown')
        obd_severity = obd_results.get('severity', 'unknown')
        
        # Convert to numeric values
        image_severity_val = severity_levels.get(image_severity, -1)
        voice_severity_val = severity_levels.get(voice_severity, -1)
        obd_severity_val = severity_levels.get(obd_severity, -1)
        
        # Get maximum severity value that is not unknown
        severity_values = [val for val in [image_severity_val, voice_severity_val, obd_severity_val] if val >= 0]
        
        if severity_values:
            max_severity_val = max(severity_values)
            # Convert back to string
            for level, value in severity_levels.items():
                if value == max_severity_val:
                    results["severity"] = level
                    break
        
        # Generate diagnoses by consolidating issues
        if all_issues:
            # Group similar issues
            issue_groups = group_similar_issues(all_issues)
            
            # Convert each group to a diagnosis result
            for group in issue_groups:
                # Calculate average confidence
                confidence = sum(issue["confidence"] for issue in group) / len(group)
                
                # Use the description from the issue with highest confidence
                max_confidence_issue = max(group, key=lambda x: x["confidence"])
                description = max_confidence_issue["description"]
                
                # Create diagnosis name (simplified version of description)
                name = simplify_description(description)
                
                # Add to results
                results["diagnoses"].append({
                    "name": name,
                    "description": description,
                    "confidence": confidence,
                    "severity": results["severity"]  # Use overall severity
                })
        
        # Add safety warnings
        safety_warnings = []
        if image_results.get('safety_concerns'):
            safety_warnings.append(image_results.get('safety_concerns'))
        if voice_results.get('safety_concerns'):
            safety_warnings.append(voice_results.get('safety_concerns'))
        if obd_results.get('safety_concerns'):
            safety_warnings.append(obd_results.get('safety_concerns'))
        
        # If severity is high or critical, add a general safety warning
        if results["severity"] in ["high", "critical"]:
            safety_warnings.append(
                "WARNING: Your vehicle has potentially serious issues. "
                "It may not be safe to drive. Consider having it towed to a repair facility."
            )
        
        # Add unique safety warnings to results
        for warning in safety_warnings:
            if warning and warning not in [w.get('text', '') for w in results["safety_warnings"]]:
                results["safety_warnings"].append({
                    "text": warning,
                    "issue_name": "Safety Concern"
                })
        
        # If no diagnoses were made but there are issues, add a general diagnosis
        if not results["diagnoses"] and all_issues:
            results["diagnoses"].append({
                "name": "Multiple Issues Detected",
                "description": "Multiple potential issues were detected but couldn't be narrowed down to specific diagnoses.",
                "confidence": 0.5,
                "severity": results["severity"]
            })
        
        # If there are no issues at all, add a "No issues detected" diagnosis
        if not all_issues:
            results["diagnoses"].append({
                "name": "No Issues Detected",
                "description": "No issues were detected in the diagnostic analysis.",
                "confidence": 0.9,
                "severity": "none"
            })
            results["severity"] = "none"
        
        # Use AI to enhance the diagnostic results if needed
        ai_enhanced_results = enhance_with_ai(results, all_issues, vehicle_info)
        if ai_enhanced_results:
            results.update(ai_enhanced_results)
        
        return results
    
    except Exception as e:
        logger.error(f"Error analyzing diagnostic data: {str(e)}")
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


def group_similar_issues(issues):
    """
    Group similar issues together.
    
    Args:
        issues: List of issue dictionaries
        
    Returns:
        List of groups (each group is a list of similar issues)
    """
    if not issues:
        return []
    
    # Initialize groups with the first issue
    groups = [[issues[0]]]
    
    # For each remaining issue
    for issue in issues[1:]:
        # Check if it's similar to any existing group
        added = False
        for group in groups:
            # Check if the issue is similar to any issue in this group
            for existing_issue in group:
                if are_issues_similar(issue["description"], existing_issue["description"]):
                    group.append(issue)
                    added = True
                    break
            if added:
                break
        
        # If not similar to any existing group, create a new group
        if not added:
            groups.append([issue])
    
    return groups


def are_issues_similar(desc1, desc2):
    """
    Determine if two issue descriptions are similar.
    
    Args:
        desc1: First issue description
        desc2: Second issue description
        
    Returns:
        True if similar, False otherwise
    """
    # Convert to lowercase
    desc1 = desc1.lower()
    desc2 = desc2.lower()
    
    # Check if either description contains the other
    if desc1 in desc2 or desc2 in desc1:
        return True
    
    # Split into words and check for common important words
    words1 = set(desc1.split())
    words2 = set(desc2.split())
    
    # Common noise words to ignore
    noise_words = {"a", "an", "the", "is", "are", "was", "were", "to", "in", "on", "at", "of", "for", "with"}
    
    # Remove noise words
    words1 = words1 - noise_words
    words2 = words2 - noise_words
    
    # Calculate similarity based on common words
    if not words1 or not words2:
        return False
    
    # Count common words
    common_words = words1.intersection(words2)
    
    # Calculate Jaccard similarity
    similarity = len(common_words) / (len(words1) + len(words2) - len(common_words))
    
    # Threshold for similarity
    return similarity > 0.3


def simplify_description(description):
    """
    Create a simplified name from a description.
    
    Args:
        description: Full issue description
        
    Returns:
        Simplified name
    """
    # Remove everything after a dash or colon
    for separator in [' - ', ': ', ':', '.']:
        if separator in description:
            description = description.split(separator)[0]
    
    # Limit length
    if len(description) > 50:
        description = description[:47] + '...'
    
    return description


def enhance_with_ai(results, all_issues, vehicle_info):
    """
    Enhance diagnostic results using AI.
    
    Args:
        results: Current diagnostic results
        all_issues: List of all detected issues
        vehicle_info: Dictionary with vehicle information
        
    Returns:
        Enhanced results or None if AI is not available
    """
    try:
        # Check if we have AI libraries available
        ai = DiagnosticAI()
        
        if not (ai.use_openai or ai.use_anthropic):
            logger.warning("No AI libraries available for diagnostic enhancement")
            return None
        
        # Format the current results and issues for the AI
        issues_str = ""
        for issue in all_issues:
            issues_str += f"- {issue['description']} (source: {issue['source']}, confidence: {issue['confidence']})\n"
        
        diagnoses_str = ""
        for diagnosis in results["diagnoses"]:
            diagnoses_str += f"- {diagnosis['name']}: {diagnosis['description']} (confidence: {diagnosis['confidence']})\n"
        
        # Create the prompt for AI
        prompt = f"""You are an expert automotive diagnostic AI assistant.
Please enhance the following diagnostic results for a vehicle:

Vehicle: {vehicle_info.get('year', 'Unknown')} {vehicle_info.get('make', 'Unknown')} {vehicle_info.get('model', 'Unknown')}
Mileage: {vehicle_info.get('mileage', 'Unknown')}

Detected Issues:
{issues_str}

Current Diagnoses:
{diagnoses_str}

Overall Severity: {results['severity']}

Your task is to review the collected data, improve the diagnoses by adding professional insights, and provide better repair recommendations.

Please provide:
1. Refined diagnoses with more accurate descriptions and severity levels
2. Additional DIY repairs the vehicle owner might attempt (if applicable)
3. Professional repair recommendations that might be needed
4. Important safety warnings the vehicle owner should be aware of

Format your response as a JSON object with the following structure:
{{
  "enhanced_diagnoses": [
    {{
      "name": "Diagnosis name",
      "description": "Detailed description",
      "confidence": 0.0-1.0,
      "severity": "critical|high|medium|low|none"
    }},
    ...
  ],
  "enhanced_severity": "critical|high|medium|low|none",
  "enhanced_diy_repairs": [
    {{
      "issue_name": "Issue being repaired",
      "repair_name": "Name of repair procedure",
      "description": "Detailed description",
      "difficulty": 1-5,
      "estimated_cost": "$XX-$YY",
      "steps": ["Step 1", "Step 2", ...]
    }},
    ...
  ],
  "enhanced_professional_repairs": [
    {{
      "issue_name": "Issue being repaired",
      "repair_name": "Name of repair procedure",
      "description": "Detailed description",
      "estimated_cost": "$XX-$YY"
    }},
    ...
  ],
  "enhanced_safety_warnings": [
    {{
      "text": "Safety warning text",
      "issue_name": "Related issue"
    }},
    ...
  ]
}}

Ensure your response is accurate, helpful, and formatted exactly as the JSON structure above.
"""
        
        # Try with Anthropic first if available
        if ai.use_anthropic:
            try:
                analysis = ai._analyze_with_anthropic(prompt)
                if analysis:
                    logger.info("Successfully enhanced diagnostics with Anthropic")
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
            except Exception as e:
                logger.error(f"Error enhancing diagnostics with Anthropic: {e}")
        
        # Fall back to OpenAI if available
        if ai.use_openai:
            try:
                analysis = ai._analyze_with_openai(prompt)
                if analysis:
                    logger.info("Successfully enhanced diagnostics with OpenAI")
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
            except Exception as e:
                logger.error(f"Error enhancing diagnostics with OpenAI: {e}")
        
        return None
    
    except Exception as e:
        logger.error(f"Error in AI enhancement: {str(e)}")
        return None