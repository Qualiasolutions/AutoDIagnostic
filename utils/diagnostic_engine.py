import json
import logging
import os

def analyze_diagnostic_data(diagnostic_data, vehicle_info):
    """
    Analyze the collected diagnostic data and return results.
    
    Args:
        diagnostic_data: Dictionary containing image and voice analysis results
        vehicle_info: Dictionary containing vehicle information
        
    Returns:
        Dictionary with diagnosis, recommendations, and severity
    """
    logging.debug("Analyzing diagnostic data...")
    
    # Load diagnostic knowledge base
    with open('static/data/diagnostic_data.json', 'r') as f:
        knowledge_base = json.load(f)
    
    # Extract image and voice results
    image_results = diagnostic_data.get('image_results', {})
    voice_results = diagnostic_data.get('voice_results', {})
    
    # Combine issues from both sources
    visual_issues = []
    if 'issues' in image_results:
        visual_issues = image_results['issues']
    
    audio_symptoms = []
    if 'symptoms' in voice_results:
        audio_symptoms = voice_results['symptoms']
    
    # Match issues and symptoms to the knowledge base
    potential_problems = []
    
    # Map to track how many symptoms match each issue
    issue_matches = {}
    
    # First, check for direct matches from visual issues
    for issue in visual_issues:
        if issue['type'] != 'no_visual_issues':
            for kb_issue in knowledge_base['issues']:
                if any(t.lower() == issue['type'].lower() for t in kb_issue['indicators']):
                    issue_id = kb_issue['id']
                    if issue_id not in issue_matches:
                        issue_matches[issue_id] = {
                            'issue': kb_issue,
                            'matches': 0,
                            'confidence': 0.0
                        }
                    # Increase match count and confidence
                    issue_matches[issue_id]['matches'] += 1
                    confidence = image_results.get('confidence', {}).get(issue['type'], 0.5)
                    issue_matches[issue_id]['confidence'] = max(
                        issue_matches[issue_id]['confidence'], 
                        confidence
                    )
    
    # Then, check for matches from audio symptoms
    for symptom in audio_symptoms:
        if symptom['name'] != 'no_symptoms_described':
            for kb_issue in knowledge_base['issues']:
                for kb_symptom in kb_issue['symptoms']:
                    if kb_symptom['name'].lower() == symptom['name'].lower():
                        issue_id = kb_issue['id']
                        if issue_id not in issue_matches:
                            issue_matches[issue_id] = {
                                'issue': kb_issue,
                                'matches': 0,
                                'confidence': 0.0
                            }
                        # Increase match count and confidence
                        issue_matches[issue_id]['matches'] += 1
                        confidence = voice_results.get('confidence', {}).get(symptom['name'], 0.5)
                        issue_matches[issue_id]['confidence'] = max(
                            issue_matches[issue_id]['confidence'], 
                            confidence
                        )
    
    # Convert matches to potential problems, sorted by confidence and match count
    for issue_id, data in issue_matches.items():
        potential_problems.append({
            'id': issue_id,
            'name': data['issue']['name'],
            'description': data['issue']['description'],
            'severity': data['issue']['severity'],
            'confidence': data['confidence'],
            'match_count': data['matches'],
            'repair_options': data['issue']['repair_options'],
            'safety_warnings': data['issue']['safety_warnings'] if 'safety_warnings' in data['issue'] else []
        })
    
    # Sort problems by confidence and match count
    potential_problems.sort(key=lambda x: (x['confidence'], x['match_count']), reverse=True)
    
    # Prepare the final analysis results
    results = {
        'diagnosis': [],
        'diy_repairs': [],
        'professional_repairs': [],
        'safety_warnings': [],
        'visual_issues': visual_issues,
        'audio_symptoms': audio_symptoms,
        'transcript': voice_results.get('transcript', '')
    }
    
    # Add top 3 most likely problems to diagnosis
    for problem in potential_problems[:3]:
        results['diagnosis'].append({
            'name': problem['name'],
            'description': problem['description'],
            'severity': problem['severity'],
            'confidence': problem['confidence']
        })
        
        # Categorize repair options
        for repair in problem['repair_options']:
            if repair['diy_difficulty'] <= 3:  # Easy to moderate DIY repair
                results['diy_repairs'].append({
                    'issue_name': problem['name'],
                    'repair_name': repair['name'],
                    'description': repair['description'],
                    'difficulty': repair['diy_difficulty'],
                    'estimated_cost': repair['estimated_cost'],
                    'steps': repair['steps']
                })
            else:  # Professional repair recommended
                results['professional_repairs'].append({
                    'issue_name': problem['name'],
                    'repair_name': repair['name'],
                    'description': repair['description'],
                    'estimated_cost': repair['estimated_cost']
                })
        
        # Add safety warnings
        for warning in problem.get('safety_warnings', []):
            if warning not in [w['text'] for w in results['safety_warnings']]:
                results['safety_warnings'].append({
                    'text': warning,
                    'issue_name': problem['name']
                })
    
    # If no problems were diagnosed, provide a generic message
    if not results['diagnosis']:
        results['diagnosis'].append({
            'name': 'Inconclusive',
            'description': 'Not enough information to make a confident diagnosis. Consider providing more details or consulting a professional mechanic.',
            'severity': 'unknown',
            'confidence': 0.0
        })
    
    # Get overall severity (highest severity of any diagnosed issue)
    severity_levels = {
        'low': 1,
        'medium': 2,
        'high': 3,
        'critical': 4,
        'unknown': 0
    }
    
    severity_scores = [severity_levels.get(d['severity'], 0) for d in results['diagnosis']]
    highest_severity_score = max(severity_scores) if severity_scores else 0
    
    severity_map = {v: k for k, v in severity_levels.items()}
    results['overall_severity'] = severity_map.get(highest_severity_score, 'unknown')
    
    return results
