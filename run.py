#!/usr/bin/env python3
"""
Clean startup script for AutoDiagnosticPro
Suppresses graphics warnings that don't affect the app
"""
import os
import sys

# Suppress graphics-related warnings
os.environ['LIBVA_DRIVER_NAME'] = 'vdpau'
os.environ['MESA_GL_VERSION_OVERRIDE'] = '3.3'

# Import and run the main app
from main import app

if __name__ == '__main__':
    # Clear screen for clean output
    os.system('clear')
    
    print("🚗 Starting AutoDiagnosticPro...")
    print("📊 Initializing diagnostic systems...")
    
    # Get port from environment or use default
    port = int(os.environ.get('PORT', 5001))
    
    try:
        app.run(host='0.0.0.0', port=port, debug=True)
    except KeyboardInterrupt:
        print("\n🛑 AutoDiagnosticPro stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error starting application: {e}")
        sys.exit(1) 