"""
Image Processor Module
This module processes images using OpenCV to identify vehicle issues.
"""

import os
import cv2
import numpy as np
import logging
import base64
import tempfile
from typing import Dict, List, Optional, Any, Tuple
from io import BytesIO
from PIL import Image

# Import AI module
from utils.diagnostic_ai import DiagnosticAI

# Configure logging
logger = logging.getLogger(__name__)


def process_image(image_file, vehicle_info):
    """
    Process an image using OpenCV to identify vehicle issues.
    
    Args:
        image_file: The uploaded image file
        vehicle_info: Dictionary containing vehicle information
        
    Returns:
        Dictionary with identified issues
    """
    try:
        # Read the image file
        image_stream = image_file.read()
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
        temp_file.write(image_stream)
        temp_file.close()
        
        # Load image with OpenCV
        image = cv2.imread(temp_file.name)
        os.unlink(temp_file.name)  # Delete the temporary file
        
        if image is None:
            logger.error("Failed to load image")
            return {"error": "Failed to load image"}
        
        # Perform basic image preprocessing
        image = preprocess_image(image)
        
        # Detect potential issues
        results = detect_issues(image)
        
        # Get a base64 encoded string for display
        _, buffer = cv2.imencode('.jpg', image)
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        # Enhance results with AI analysis if available
        if vehicle_info:
            ai_results = analyze_with_ai(image_base64, results, vehicle_info)
            if ai_results:
                results.update(ai_results)
        
        return results
    
    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        return {"error": f"Error processing image: {str(e)}"}


def preprocess_image(image):
    """
    Preprocess the image for better analysis.
    
    Args:
        image: OpenCV image
        
    Returns:
        Preprocessed image
    """
    try:
        # Convert to RGB for analysis (OpenCV uses BGR)
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Resize image if it's too large (maintain aspect ratio)
        max_dimension = 1024
        height, width = rgb_image.shape[:2]
        if height > max_dimension or width > max_dimension:
            if height > width:
                new_height = max_dimension
                new_width = int(width * (max_dimension / height))
            else:
                new_width = max_dimension
                new_height = int(height * (max_dimension / width))
            
            rgb_image = cv2.resize(rgb_image, (new_width, new_height), interpolation=cv2.INTER_AREA)
        
        # Apply slight sharpening
        kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]], np.float32)
        sharpened = cv2.filter2D(rgb_image, -1, kernel)
        
        # Convert back to BGR for OpenCV
        processed_image = cv2.cvtColor(sharpened, cv2.COLOR_RGB2BGR)
        
        return processed_image
    
    except Exception as e:
        logger.error(f"Error preprocessing image: {str(e)}")
        return image  # Return original image if preprocessing fails


def detect_issues(image):
    """
    Detect potential vehicle issues in the image.
    
    Args:
        image: OpenCV image
        
    Returns:
        Dictionary with detected issues
    """
    results = {
        "detected_objects": [],
        "potential_issues": [],
        "confidence_scores": {}
    }
    
    try:
        # Convert to HSV color space for fluid analysis
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Detect fluids (oil, coolant, brake fluid)
        fluid_results = detect_fluids(hsv)
        if fluid_results:
            results["detected_objects"].extend(fluid_results["detected_objects"])
            results["potential_issues"].extend(fluid_results["potential_issues"])
            results["confidence_scores"].update(fluid_results["confidence_scores"])
        
        # Detect rust and corrosion
        rust_results = detect_rust(hsv)
        if rust_results:
            results["detected_objects"].extend(rust_results["detected_objects"])
            results["potential_issues"].extend(rust_results["potential_issues"])
            results["confidence_scores"].update(rust_results["confidence_scores"])
        
        # Detect cracks in parts
        crack_results = detect_cracks(image)
        if crack_results:
            results["detected_objects"].extend(crack_results["detected_objects"])
            results["potential_issues"].extend(crack_results["potential_issues"])
            results["confidence_scores"].update(crack_results["confidence_scores"])
        
    except Exception as e:
        logger.error(f"Error detecting issues: {str(e)}")
    
    return results


def detect_fluids(hsv_image):
    """
    Detect fluid leaks in an HSV image.
    
    Args:
        hsv_image: HSV color space image
        
    Returns:
        Dictionary with detected fluid issues
    """
    results = {
        "detected_objects": [],
        "potential_issues": [],
        "confidence_scores": {}
    }
    
    try:
        # Define color ranges for common fluids
        # Oil (dark brown to black)
        lower_oil = np.array([0, 0, 0])
        upper_oil = np.array([180, 255, 50])
        
        # Coolant (green or orange-red)
        lower_coolant_green = np.array([40, 100, 100])
        upper_coolant_green = np.array([80, 255, 255])
        
        lower_coolant_orange = np.array([5, 100, 100])
        upper_coolant_orange = np.array([25, 255, 255])
        
        # Brake fluid (clear to yellow/amber)
        lower_brake = np.array([20, 100, 100])
        upper_brake = np.array([35, 255, 255])
        
        # Create masks for each fluid
        mask_oil = cv2.inRange(hsv_image, lower_oil, upper_oil)
        mask_coolant_green = cv2.inRange(hsv_image, lower_coolant_green, upper_coolant_green)
        mask_coolant_orange = cv2.inRange(hsv_image, lower_coolant_orange, upper_coolant_orange)
        mask_brake = cv2.inRange(hsv_image, lower_brake, upper_brake)
        
        # Apply morphological operations to clean up masks
        kernel = np.ones((5, 5), np.uint8)
        mask_oil = cv2.morphologyEx(mask_oil, cv2.MORPH_OPEN, kernel)
        mask_coolant_green = cv2.morphologyEx(mask_coolant_green, cv2.MORPH_OPEN, kernel)
        mask_coolant_orange = cv2.morphologyEx(mask_coolant_orange, cv2.MORPH_OPEN, kernel)
        mask_brake = cv2.morphologyEx(mask_brake, cv2.MORPH_OPEN, kernel)
        
        # Calculate percentage of image covered by each fluid
        total_pixels = hsv_image.shape[0] * hsv_image.shape[1]
        oil_coverage = cv2.countNonZero(mask_oil) / total_pixels
        coolant_green_coverage = cv2.countNonZero(mask_coolant_green) / total_pixels
        coolant_orange_coverage = cv2.countNonZero(mask_coolant_orange) / total_pixels
        brake_coverage = cv2.countNonZero(mask_brake) / total_pixels
        
        # Set thresholds for detection (these would be tuned in a real system)
        # For this demo, we'll use simple thresholds
        if oil_coverage > 0.05:
            confidence = min(1.0, oil_coverage * 5)  # Scale to 0-1 range
            results["detected_objects"].append("oil_leak")
            results["potential_issues"].append("Possible oil leak detected")
            results["confidence_scores"]["oil_leak"] = confidence
        
        if coolant_green_coverage > 0.03 or coolant_orange_coverage > 0.03:
            confidence = min(1.0, (coolant_green_coverage + coolant_orange_coverage) * 5)
            results["detected_objects"].append("coolant_leak")
            results["potential_issues"].append("Possible coolant leak detected")
            results["confidence_scores"]["coolant_leak"] = confidence
        
        if brake_coverage > 0.02:
            confidence = min(1.0, brake_coverage * 6)
            results["detected_objects"].append("brake_fluid_leak")
            results["potential_issues"].append("Possible brake fluid leak detected")
            results["confidence_scores"]["brake_fluid_leak"] = confidence
        
    except Exception as e:
        logger.error(f"Error detecting fluids: {str(e)}")
    
    return results


def detect_rust(hsv_image):
    """
    Detect rust and corrosion in an HSV image.
    
    Args:
        hsv_image: HSV color space image
        
    Returns:
        Dictionary with detected rust issues
    """
    results = {
        "detected_objects": [],
        "potential_issues": [],
        "confidence_scores": {}
    }
    
    try:
        # Define color range for rust (orange-brown)
        lower_rust = np.array([5, 100, 100])
        upper_rust = np.array([30, 255, 255])
        
        # Create mask for rust
        mask_rust = cv2.inRange(hsv_image, lower_rust, upper_rust)
        
        # Apply morphological operations to clean up mask
        kernel = np.ones((5, 5), np.uint8)
        mask_rust = cv2.morphologyEx(mask_rust, cv2.MORPH_OPEN, kernel)
        
        # Calculate percentage of image covered by rust
        total_pixels = hsv_image.shape[0] * hsv_image.shape[1]
        rust_coverage = cv2.countNonZero(mask_rust) / total_pixels
        
        # Set threshold for detection
        if rust_coverage > 0.03:
            confidence = min(1.0, rust_coverage * 4)  # Scale to 0-1 range
            results["detected_objects"].append("rust")
            results["potential_issues"].append("Rust or corrosion detected")
            results["confidence_scores"]["rust"] = confidence
        
    except Exception as e:
        logger.error(f"Error detecting rust: {str(e)}")
    
    return results


def detect_cracks(image):
    """
    Detect cracks in vehicle parts.
    
    Args:
        image: OpenCV image
        
    Returns:
        Dictionary with detected crack issues
    """
    results = {
        "detected_objects": [],
        "potential_issues": [],
        "confidence_scores": {}
    }
    
    try:
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Apply Canny edge detection
        edges = cv2.Canny(blurred, 50, 150)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Filter contours to find potential cracks
        crack_contours = []
        for contour in contours:
            # Calculate contour properties
            area = cv2.contourArea(contour)
            perimeter = cv2.arcLength(contour, True)
            
            # Calculate shape factor (ratio of perimeter squared to area)
            # Cracks tend to have high shape factors
            if area > 0:
                shape_factor = perimeter * perimeter / area
                
                # Check if contour might be a crack (high shape factor, small area)
                if shape_factor > 100 and area > 50 and area < 5000:
                    crack_contours.append(contour)
        
        # If cracks are detected
        if len(crack_contours) > 5:  # Threshold number of potential cracks
            confidence = min(1.0, len(crack_contours) / 50)  # Scale to 0-1 range
            results["detected_objects"].append("cracks")
            results["potential_issues"].append("Potential cracks detected in component")
            results["confidence_scores"]["cracks"] = confidence
        
    except Exception as e:
        logger.error(f"Error detecting cracks: {str(e)}")
    
    return results


def analyze_with_ai(image_base64, cv_results, vehicle_info):
    """
    Enhance detection results with AI analysis.
    
    Args:
        image_base64: Base64 encoded image string
        cv_results: Results from OpenCV detection
        vehicle_info: Dictionary with vehicle information
        
    Returns:
        Enhanced results with AI analysis
    """
    try:
        # Check if we have AI libraries available
        ai = DiagnosticAI()
        
        if not (ai.use_openai or ai.use_anthropic):
            logger.warning("No AI libraries available for image analysis")
            return None
        
        # Create a prompt that includes the OpenCV results and vehicle info
        prompt = f"""You are an expert automotive diagnostic AI assistant.
Please analyze the following vehicle image and detection results:

Vehicle: {vehicle_info.get('year', 'Unknown')} {vehicle_info.get('make', 'Unknown')} {vehicle_info.get('model', 'Unknown')}
Mileage: {vehicle_info.get('mileage', 'Unknown')}

OpenCV Detection Results:
Detected Objects: {', '.join(cv_results.get('detected_objects', ['None']))}
Potential Issues: {', '.join(cv_results.get('potential_issues', ['None']))}

Based on the image and these initial detections, please provide a comprehensive analysis that includes:

1. A detailed description of what you see in the image
2. Confirmation or correction of the detected issues
3. Additional issues or concerns that might not have been detected by the computer vision algorithm
4. The severity level of identified issues (critical, high, medium, low, or none)
5. Recommended next steps or repairs

Format your response as a JSON object with the following structure:
{
  "description": "Detailed description of the image",
  "confirmed_issues": ["Issue 1", "Issue 2", ...],
  "additional_issues": ["Issue 1", "Issue 2", ...],
  "severity": "critical|high|medium|low|none",
  "recommendations": ["Recommendation 1", "Recommendation 2", ...],
  "suggested_parts": ["Part 1", "Part 2", ...] (if applicable)
}

Ensure your response is accurate, helpful, and formatted exactly as the JSON structure above.
"""
        
        # Try with OpenAI first if available (better for image analysis)
        if ai.use_openai:
            try:
                analysis = analyze_image_with_openai(ai.openai_client, image_base64, prompt)
                if analysis:
                    return analysis
            except Exception as e:
                logger.error(f"Error analyzing image with OpenAI: {e}")
        
        # Fall back to Anthropic if available
        if ai.use_anthropic:
            try:
                analysis = analyze_image_with_anthropic(ai.anthropic_client, image_base64, prompt)
                if analysis:
                    return analysis
            except Exception as e:
                logger.error(f"Error analyzing image with Anthropic: {e}")
        
        return None
    
    except Exception as e:
        logger.error(f"Error in AI analysis: {str(e)}")
        return None


def analyze_image_with_openai(openai_client, image_base64, prompt):
    """
    Analyze image using OpenAI's GPT-4 Vision.
    
    Args:
        openai_client: OpenAI client instance
        image_base64: Base64 encoded image string
        prompt: Text prompt for analysis
        
    Returns:
        Analysis results as a dictionary
    """
    try:
        # Create the image message with the base64 image
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024
        # do not change this unless explicitly requested by the user
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            temperature=0.2,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"}
        )
        
        # Extract and parse the JSON response
        if response and response.choices and response.choices[0].message.content:
            try:
                import json
                return json.loads(response.choices[0].message.content)
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing OpenAI JSON response: {e}")
                logger.debug(f"Raw response: {response.choices[0].message.content}")
                return None
        
        return None
    
    except Exception as e:
        logger.error(f"Error calling OpenAI API: {e}")
        return None


def analyze_image_with_anthropic(anthropic_client, image_base64, prompt):
    """
    Analyze image using Anthropic's Claude.
    
    Args:
        anthropic_client: Anthropic client instance
        image_base64: Base64 encoded image string
        prompt: Text prompt for analysis
        
    Returns:
        Analysis results as a dictionary
    """
    try:
        # the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
        response = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            temperature=0.2,
            system="You are an expert automotive diagnostic AI. Provide thorough, accurate analysis of vehicle images. Format your response as JSON exactly as requested.",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_base64
                            }
                        }
                    ]
                }
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
                        import json
                        result = json.loads(json_str)
                        return result
                    except json.JSONDecodeError as e:
                        logger.error(f"Error parsing Anthropic JSON response: {e}")
                        logger.debug(f"Raw response: {content}")
        
        return None
    
    except Exception as e:
        logger.error(f"Error calling Anthropic API: {e}")
        return None