# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OBD2 Diagnostic Pro is a professional-grade Flask-based web application that provides comprehensive OBD2 automotive diagnostics with AI enhancement:

1. **Direct OBD2 Connection**: USB connection to vehicle's diagnostic port for real-time communication
2. **DTC Analysis**: Professional diagnostic trouble code analysis with AI explanations
3. **Live Data Monitoring**: Real-time sensor readings with interactive monitoring
4. **APS Calibration**: Advanced ECU parameter adjustment and calibration tools
5. **AI Enhancement**: Anthropic Claude and OpenAI integration for intelligent analysis

The application is designed for automotive technicians and enthusiasts who need professional-grade OBD2 diagnostic capabilities with modern AI-powered insights.

## Development Commands

### Running the Application
```bash
# Development server (main entry point)
python main.py

# Alternative Flask app runner
python app.py

# Production with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### Package Management
```bash
# Install dependencies
pip install -r requirements.txt

# Or using uv (preferred - uv.lock present)
uv sync
uv run python main.py
```

### Environment Variables
Required environment variables:
- `DATABASE_URL`: PostgreSQL/SQLite connection string
- `SESSION_SECRET`: Flask session encryption key  
- `ANTHROPIC_API_KEY`: Anthropic Claude API key (recommended)
- `OPENAI_API_KEY`: OpenAI API key (optional)
- `OBD2_SIMULATION`: Enable simulation mode for development

## Architecture Overview

### Core Application Structure
- **`app.py`**: Main Flask application with OBD2 routes and database initialization
- **`main.py`**: Application entry point (imports and runs app.py)
- **`models.py`**: SQLAlchemy database models for OBD2 data

### Key Components

#### Database Layer (`models.py`)
The application uses a focused database schema with these main entities:
- **Vehicle**: Store vehicle information (make, model, year, VIN, etc.)
- **OBDDiagnosticSession**: OBD2 scan sessions with connection tracking
- **DiagnosticTroubleCode**: DTC codes from OBD2 scans with metadata
- **SensorReading**: Real-time sensor data from vehicle systems
- **DtcDatabase**: Comprehensive reference database of all possible DTCs

#### Processing Utilities (`utils/`)
- **`diagnostic_engine.py`**: Core OBD2 diagnostic logic with AI enhancement
- **`diagnostic_ai.py`**: AI integration for Anthropic Claude and OpenAI APIs
- **`obd2_connector.py`**: Direct OBD2 USB connection and vehicle communication

#### Web Interface
- **Templates**: Professional HTML templates for OBD2 interface (`templates/obd2/`)
- **Static Assets**: CSS, JavaScript for real-time diagnostics (`static/`)
- **Frontend Features**: Live data monitoring, DTC analysis, calibration tools

### Application Flow

1. **Vehicle Connection**: User connects OBD2 adapter and enters vehicle information
2. **OBD2 Communication**: Direct USB/serial connection to vehicle diagnostic port
3. **Data Collection**: Automatic DTC scanning and real-time sensor monitoring
4. **AI Analysis**: Enhanced diagnostic analysis using Anthropic Claude
5. **Professional Results**: Comprehensive diagnostic reports with repair recommendations

### Key Integration Points

#### OBD2 System
- Real USB connection to vehicle diagnostic port via ELM327 adapters
- Automatic port scanning and protocol detection
- DTC (Diagnostic Trouble Code) reading, analysis, and clearing
- Live sensor data monitoring with configurable refresh rates
- Advanced ECU parameter adjustment (APS calibration, etc.)

#### AI Integration
- Primary: Anthropic Claude for professional diagnostic analysis
- Secondary: OpenAI GPT-4 as alternative provider
- Intelligent DTC interpretation with repair recommendations
- Cost estimation and procedure guidance

#### Database Design
- Focused OBD2 diagnostic data model
- Multi-vehicle support with session tracking
- Historical diagnostic data for trend analysis
- Comprehensive DTC reference database

## Important Implementation Notes

### Error Handling
- All AI calls have graceful fallback to basic analysis
- OBD2 connection errors handled with retry logic
- Database operations wrapped with proper error handling

### Session Management
- Flask sessions store vehicle info and diagnostic state
- OBD2 session tracking for multi-step diagnostics
- Professional workflow maintained across requests

### Modular Design
- OBD2 connector supports both real hardware and simulation
- AI enhancement is optional and gracefully degrades
- Database auto-creation for easy deployment

### Development vs Production
- OBD2 simulation mode for development without hardware
- Real-time data streaming with WebSocket support
- Professional-grade error logging and monitoring
- Configuration management for different environments

## Latest Architecture (2025)

### Fully Functional OBD2 Features
- ✅ Complete OBD2 integration with USB/serial communication
- ✅ Professional DTC analysis with AI enhancement
- ✅ Real-time sensor data monitoring with charts
- ✅ Advanced APS calibration and ECU programming
- ✅ Multi-vehicle database with session tracking
- ✅ Comprehensive diagnostic reporting
- ✅ Hardware simulation for development
- ✅ Professional web interface with Bootstrap 5

### Key Routes and APIs
- `/obd2/connect` - Vehicle connection interface
- `/obd2/scan` - Diagnostic scanning with real-time progress
- `/obd2/live-data-monitoring` - Real-time sensor monitoring
- `/obd2/aps-calibration` - ECU parameter adjustment
- `/api/obd2/scan-ports` - Available OBD2 port detection
- `/api/obd2/live-data` - Live sensor data API
- `/api/obd2/clear-dtcs` - DTC clearing functionality
- `/obd2/results/<session_id>` - Comprehensive diagnostic results

### Professional Focus
- **Automotive Technicians**: Complete diagnostic workflow
- **Enthusiasts**: DIY guidance with professional insights
- **Fleet Management**: Multi-vehicle tracking and analysis
- **Educational**: Learning tool for automotive diagnostics

### Hardware Support
- **ELM327 USB Adapters**: Primary recommended hardware
- **Multi-Protocol**: CAN, ISO, KWP, PWM support
- **Universal Compatibility**: Works with all OBD2 vehicles (1996+)
- **Cross-Platform**: Windows, Linux, macOS support

### AI Enhancement
- **Contextual Analysis**: Vehicle-specific diagnostic reasoning
- **Repair Recommendations**: Professional and DIY repair procedures
- **Cost Estimation**: Accurate repair cost predictions
- **Safety Warnings**: Critical issue identification and alerts

This professional OBD2 diagnostic tool provides comprehensive vehicle analysis with modern AI capabilities, designed for both professional technicians and automotive enthusiasts.