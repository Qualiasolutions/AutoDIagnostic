import cv2
import numpy as np
import logging
import json
import os
from werkzeug.utils import secure_filename
import tempfile

def process_image(image_file, vehicle_info):
    """
    Process an image using OpenCV to identify vehicle issues.
    
    Args:
        image_file: The uploaded image file
        vehicle_info: Dictionary containing vehicle information
        
    Returns:
        Dictionary with identified issues
    """
    logging.debug("Processing image...")
    
    # Save the uploaded file to a temporary location
    temp_dir = tempfile.gettempdir()
    filename = secure_filename(image_file.filename)
    temp_path = os.path.join(temp_dir, filename)
    image_file.save(temp_path)
    
    # Load the image with OpenCV
    image = cv2.imread(temp_path)
    if image is None:
        os.remove(temp_path)
        raise ValueError("Unable to read image file")
    
    # Convert image to different color spaces for analysis
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    # Load diagnostic data from JSON file
    with open('static/data/diagnostic_data.json', 'r') as f:
        diagnostic_data = json.load(f)
    
    results = {
        'issues': [],
        'confidence': {},
        'areas_of_interest': []
    }
    
    # Detect red warning lights (dashboard)
    red_lower = np.array([0, 100, 100])
    red_upper = np.array([10, 255, 255])
    red_mask = cv2.inRange(hsv, red_lower, red_upper)
    red_results = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    red_contours = red_results[0] if len(red_results) == 2 else red_results[1]
    
    if len(red_contours) > 0:
        results['issues'].append({
            'type': 'warning_light',
            'description': 'Possible warning light detected',
            'severity': 'medium'
        })
        results['confidence']['warning_light'] = 0.75
        
        # Add areas of interest (bounding boxes of warning lights)
        for contour in red_contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w * h > 100:  # Ignore tiny areas
                results['areas_of_interest'].append({
                    'x': int(x),
                    'y': int(y),
                    'width': int(w),
                    'height': int(h),
                    'type': 'warning_light'
                })
    
    # Detect fluid leaks (under car)
    # This is a simplified version - actual implementation would be more complex
    # Look for dark patches against light backgrounds
    ret, thresh = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
    leak_results = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    leak_contours = leak_results[0] if len(leak_results) == 2 else leak_results[1]
    
    large_dark_areas = 0
    for contour in leak_contours:
        area = cv2.contourArea(contour)
        if area > 5000:  # Large dark area - potential fluid leak
            large_dark_areas += 1
            x, y, w, h = cv2.boundingRect(contour)
            results['areas_of_interest'].append({
                'x': int(x),
                'y': int(y),
                'width': int(w),
                'height': int(h),
                'type': 'potential_leak'
            })
    
    if large_dark_areas > 0:
        results['issues'].append({
            'type': 'fluid_leak',
            'description': 'Possible fluid leak detected',
            'severity': 'high'
        })
        results['confidence']['fluid_leak'] = 0.6
    
    # Clean up the temporary file
    os.remove(temp_path)
    
    # If no issues detected, add a note
    if not results['issues']:
        results['issues'].append({
            'type': 'no_visual_issues',
            'description': 'No obvious visual issues detected',
            'severity': 'none'
        })
    
    return results
