"""
Speech Processor Module
This module processes voice recordings to identify vehicle issues based on sounds.
"""

import os
import logging
import tempfile
import json
import numpy as np
import librosa
from typing import Dict, List, Optional, Any
import speech_recognition as sr

# Import AI module
from utils.diagnostic_ai import DiagnosticAI

# Configure logging
logger = logging.getLogger(__name__)


def process_speech(audio_file, vehicle_info):
    """
    Process an audio file to identify vehicle issues based on sounds.
    
    Args:
        audio_file: The uploaded audio file
        vehicle_info: Dictionary containing vehicle information
        
    Returns:
        Dictionary with identified issues
    """
    try:
        # Save the audio file temporarily
        audio_stream = audio_file.read()
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_file.write(audio_stream)
        temp_file.close()
        
        results = {
            "transcript": "",
            "detected_sounds": [],
            "potential_issues": [],
            "confidence_scores": {}
        }
        
        # Process the audio in two ways:
        # 1. Extract speech content using speech recognition
        transcript = extract_speech(temp_file.name)
        if transcript:
            results["transcript"] = transcript
        
        # 2. Analyze engine sounds using audio processing
        sound_analysis = analyze_engine_sounds(temp_file.name)
        if sound_analysis:
            results.update(sound_analysis)
        
        # Clean up
        os.unlink(temp_file.name)
        
        # Enhance results with AI analysis if available
        if transcript or sound_analysis.get("detected_sounds"):
            ai_results = analyze_with_ai(results, vehicle_info)
            if ai_results:
                results.update(ai_results)
        
        return results
    
    except Exception as e:
        logger.error(f"Error processing audio: {str(e)}")
        return {"error": f"Error processing audio: {str(e)}"}


def extract_speech(audio_file):
    """
    Extract speech content using speech recognition.
    
    Args:
        audio_file: Path to the audio file
        
    Returns:
        Transcribed text or None if no speech recognized
    """
    try:
        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_file) as source:
            # Adjust for ambient noise
            recognizer.adjust_for_ambient_noise(source)
            # Record the audio
            audio_data = recognizer.record(source)
            
            # Try to recognize speech
            try:
                # First try with Google (more accurate but requires internet)
                text = recognizer.recognize_google(audio_data)
                logger.info(f"Google Speech Recognition: {text}")
                return text
            except sr.RequestError:
                # Fall back to local Sphinx if internet is not available
                try:
                    text = recognizer.recognize_sphinx(audio_data)
                    logger.info(f"Sphinx Speech Recognition: {text}")
                    return text
                except:
                    logger.warning("Speech recognition failed")
                    return None
            except:
                logger.warning("No speech detected in audio")
                return None
    
    except Exception as e:
        logger.error(f"Error extracting speech: {str(e)}")
        return None


def analyze_engine_sounds(audio_file):
    """
    Analyze engine sounds to identify potential issues.
    
    Args:
        audio_file: Path to the audio file
        
    Returns:
        Dictionary with detected sound patterns and potential issues
    """
    results = {
        "detected_sounds": [],
        "potential_issues": [],
        "confidence_scores": {}
    }
    
    try:
        # Load the audio file
        y, sr = librosa.load(audio_file, sr=None)
        
        # Extract audio features
        # 1. Spectral Centroid (brightness of sound)
        spectral_centroids = librosa.feature.spectral_centroid(y=y, sr=sr)[0]
        
        # 2. Spectral Rolloff (amount of high frequency)
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)[0]
        
        # 3. Zero Crossing Rate (noisiness)
        zero_crossing_rate = librosa.feature.zero_crossing_rate(y)[0]
        
        # 4. MFCC (timbre characteristics)
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        
        # Calculate statistics for each feature
        centroid_mean = np.mean(spectral_centroids)
        centroid_std = np.std(spectral_centroids)
        rolloff_mean = np.mean(spectral_rolloff)
        zcr_mean = np.mean(zero_crossing_rate)
        zcr_std = np.std(zero_crossing_rate)
        
        # Check for knocking sounds (high ZCR variance, specific frequency pattern)
        if zcr_std > 0.1 and detect_pattern(y, sr, "knocking"):
            confidence = min(1.0, zcr_std * 5)  # Scale to 0-1 range
            results["detected_sounds"].append("knocking")
            results["potential_issues"].append("Engine knocking detected - potential issues with pistons, bearings, or detonation")
            results["confidence_scores"]["knocking"] = confidence
        
        # Check for whining/squealing (high frequency components)
        if rolloff_mean > 0.8 * sr / 2 and detect_pattern(y, sr, "whining"):
            confidence = min(1.0, (rolloff_mean / (sr / 2)) * 0.8)
            results["detected_sounds"].append("whining")
            results["potential_issues"].append("High-pitched whining detected - potential issues with belt, pump, or bearing")
            results["confidence_scores"]["whining"] = confidence
        
        # Check for rattling (rapid variations in amplitude)
        if detect_pattern(y, sr, "rattling"):
            confidence = 0.7  # Set a default confidence
            results["detected_sounds"].append("rattling")
            results["potential_issues"].append("Rattling sound detected - potential loose components or mounting issues")
            results["confidence_scores"]["rattling"] = confidence
        
        # Check for rough idle (irregular low-frequency oscillations)
        if detect_pattern(y, sr, "rough_idle"):
            confidence = 0.65  # Set a default confidence
            results["detected_sounds"].append("rough_idle")
            results["potential_issues"].append("Rough idle detected - potential issues with fuel system or ignition")
            results["confidence_scores"]["rough_idle"] = confidence
        
    except Exception as e:
        logger.error(f"Error analyzing engine sounds: {str(e)}")
    
    return results


def detect_pattern(y, sr, pattern_type):
    """
    Detect specific sound patterns in audio data.
    
    Args:
        y: Audio time series
        sr: Sample rate
        pattern_type: Type of pattern to detect
        
    Returns:
        True if pattern is detected, False otherwise
    """
    try:
        if pattern_type == "knocking":
            # Knocking typically occurs at regular intervals
            # Look for periodic peaks in the frequency domain between 2-7 kHz
            
            # Short-time Fourier transform
            D = np.abs(librosa.stft(y))
            
            # Convert to dB scale
            D_db = librosa.amplitude_to_db(D, ref=np.max)
            
            # Get frequency bins corresponding to 2-7 kHz
            freqs = librosa.fft_frequencies(sr=sr)
            mask = (freqs >= 2000) & (freqs <= 7000)
            
            # Check if there are consistent peaks in this range
            if np.mean(D_db[:, mask]) > -30:  # Threshold for energy in knocking range
                # Check for periodicity
                onset_env = librosa.onset.onset_strength(y=y, sr=sr)
                tempo, _ = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
                
                # Engine knocking usually happens at engine RPM frequencies
                if 30 <= tempo <= 80:  # RPM range converted to BPM
                    return True
        
        elif pattern_type == "whining":
            # Whining typically has strong high-frequency components
            
            # Compute the power spectrogram
            D = np.abs(librosa.stft(y))**2
            
            # Compute the spectral contrast (difference between peaks and valleys)
            contrast = librosa.feature.spectral_contrast(S=D, sr=sr)
            
            # High contrast in upper frequencies suggests whining
            if np.mean(contrast[4:]) > 10:  # Look at upper frequency bands
                return True
        
        elif pattern_type == "rattling":
            # Rattling has rapid amplitude variations
            
            # Compute RMS energy in small windows
            frame_length = int(sr * 0.025)  # 25ms frames
            hop_length = int(sr * 0.010)    # 10ms hop
            
            # Get RMS energy
            rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
            
            # Calculate the variations in RMS
            rms_diff = np.diff(rms)
            
            # Many sign changes and high variance indicates rattling
            sign_changes = np.sum(np.diff(np.signbit(rms_diff)))
            
            if sign_changes > len(rms_diff) * 0.3 and np.std(rms) > 0.05:
                return True
        
        elif pattern_type == "rough_idle":
            # Rough idle has irregular low-frequency variations
            
            # Filter to get only low frequencies (< 500 Hz)
            y_low = librosa.effects.preemphasis(y, coef=0.95, return_zf=False)
            
            # Get amplitude envelope
            frame_length = int(sr * 0.1)  # 100ms frames
            hop_length = int(sr * 0.05)   # 50ms hop
            
            # Get RMS energy
            rms = librosa.feature.rms(y=y_low, frame_length=frame_length, hop_length=hop_length)[0]
            
            # Calculate variance of RMS
            rms_var = np.var(rms)
            
            # High variance in low-frequency energy indicates rough idle
            if rms_var > 0.01:
                return True
        
        return False
    
    except Exception as e:
        logger.error(f"Error detecting pattern {pattern_type}: {str(e)}")
        return False


def analyze_with_ai(audio_results, vehicle_info):
    """
    Enhance audio analysis results with AI.
    
    Args:
        audio_results: Results from audio processing
        vehicle_info: Dictionary with vehicle information
        
    Returns:
        Enhanced results with AI analysis
    """
    try:
        # Check if we have AI libraries available
        ai = DiagnosticAI()
        
        if not (ai.use_openai or ai.use_anthropic):
            logger.warning("No AI libraries available for audio analysis")
            return None
        
        # Create a prompt that includes the audio results and vehicle info
        prompt = f"""You are an expert automotive diagnostic AI assistant specializing in sound analysis.
Please analyze the following audio diagnostic results from a vehicle:

Vehicle: {vehicle_info.get('year', 'Unknown')} {vehicle_info.get('make', 'Unknown')} {vehicle_info.get('model', 'Unknown')}
Mileage: {vehicle_info.get('mileage', 'Unknown')}

Audio Analysis Results:
- Detected Sounds: {', '.join(audio_results.get('detected_sounds', ['None']))}
- Potential Issues from Sound Analysis: {', '.join(audio_results.get('potential_issues', ['None']))}

Transcript from Voice Recording:
"{audio_results.get('transcript', 'No speech detected')}"

Based on these audio analysis results and the transcript (if available), please provide a comprehensive analysis that includes:

1. A detailed interpretation of the detected sounds and what they might indicate
2. Confirmation or refinement of the potential issues identified
3. Additional issues that might be related to these sounds that weren't explicitly detected
4. The severity level of identified issues (critical, high, medium, low, or none)
5. Probable root causes of the problems
6. Recommended diagnostic steps and repairs

Format your response as a JSON object with the following structure:
{{
  "analysis": "Detailed analysis of the sounds and transcript",
  "confirmed_issues": ["Issue 1", "Issue 2", ...],
  "additional_issues": ["Issue 1", "Issue 2", ...],
  "severity": "critical|high|medium|low|none",
  "probable_causes": ["Cause 1", "Cause 2", ...],
  "recommendations": ["Recommendation 1", "Recommendation 2", ...]
}}

Ensure your response is accurate, helpful, and formatted exactly as the JSON structure above.
"""
        
        # Try with OpenAI first if available
        if ai.use_openai:
            try:
                analysis = ai._analyze_with_openai(prompt)
                if analysis:
                    return analysis
            except Exception as e:
                logger.error(f"Error analyzing audio with OpenAI: {e}")
        
        # Fall back to Anthropic if available
        if ai.use_anthropic:
            try:
                analysis = ai._analyze_with_anthropic(prompt)
                if analysis:
                    return analysis
            except Exception as e:
                logger.error(f"Error analyzing audio with Anthropic: {e}")
        
        return None
    
    except Exception as e:
        logger.error(f"Error in AI analysis: {str(e)}")
        return None