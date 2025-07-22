# OBD2 Diagnostic Pro

A professional-grade OBD2 automotive diagnostic tool with AI-powered analysis for automotive technicians and enthusiasts. Direct USB connection to vehicle diagnostic ports for comprehensive vehicle health assessment and repair recommendations.

## Features

### Core OBD2 Functionality
- **Direct OBD2 Connection**: USB connection to vehicle's diagnostic port for real-time communication
- **DTC Analysis**: Read, analyze, and clear Diagnostic Trouble Codes with detailed explanations
- **Live Data Monitoring**: Real-time sensor readings with interactive charts and data logging
- **APS Calibration**: Advanced Accelerator Pedal Position Sensor calibration tools

### AI-Enhanced Diagnostics
- **Anthropic Claude Integration**: Professional diagnostic analysis and repair recommendations
- **OpenAI Support**: Alternative AI provider for diagnostic enhancement
- **Contextual Analysis**: Vehicle-specific insights and repair procedures
- **Cost Estimation**: Accurate repair cost estimates for both DIY and professional repairs

### Professional Features
- **Multi-Vehicle Support**: Database tracking of multiple vehicles and diagnostic sessions
- **Historical Data**: Complete diagnostic history with session management
- **Advanced Calibration**: ECU parameter adjustment and programming tools
- **Comprehensive Reporting**: Detailed analysis with safety warnings and severity assessment

## Installation

### Prerequisites
- Python 3.11+
- OBD2-to-USB adapter (ELM327-based recommended)
- Compatible vehicle (1996+ with OBD2 standard)

### Quick Setup

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd OBD2-Diagnostic-Pro
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   
   Or using uv (recommended):
   ```bash
   uv sync
   ```

3. **Environment Configuration**
   Create a `.env` file:
   ```bash
   # Database Configuration
   DATABASE_URL=sqlite:///app.db
   
   # Security
   SESSION_SECRET=your-secure-session-key
   
   # AI API Keys (at least one recommended)
   ANTHROPIC_API_KEY=your-anthropic-key
   OPENAI_API_KEY=your-openai-key
   
   # OBD2 Settings
   OBD2_SIMULATION=true  # Set to false for real hardware
   ```

4. **Install OBD2 Hardware Dependencies** (Optional - for real hardware):
   ```bash
   python install_obd2_deps.py
   ```
   This installs Bluetooth support, USB permissions, and system dependencies.

5. **Run the Application**
   ```bash
   python main.py
   ```
   
   Access at: `http://127.0.0.1:5000`

## Hardware Requirements

### OBD2 Adapter
- **USB/Cable (Most Reliable)**: ELM327 v1.5 or v2.1 USB adapter
- **Bluetooth/Wireless**: ELM327 v1.5+ Bluetooth adapter (now supported!)
- **Avoid**: Generic no-name adapters under $10 (often unreliable)
- **Compatibility**: Windows (COM ports), Linux (/dev/ttyUSB, rfcomm), macOS

### Vehicle Compatibility
- All vehicles manufactured after 1996 (OBD2 standard)
- Cars, light trucks, SUVs from major manufacturers
- Supports all OBD2 protocols (CAN, ISO, KWP, etc.)

## Professional Features

### DTC Code Analysis
- Read and interpret all standard OBD2 diagnostic codes
- AI-powered explanations and repair recommendations
- Freeze frame data capture for intermittent issues
- Code clearing with proper verification

### Live Data Monitoring
- Real-time sensor data streaming (RPM, temperature, fuel trim, etc.)
- Interactive charts with data logging
- Customizable refresh rates
- Export capabilities for analysis

### APS Calibration Tools
- Accelerator Pedal Position Sensor adjustment
- Throttle body relearn procedures
- Electronic throttle control system calibration
- Professional-grade ECU parameter writing

## Architecture

### Backend Stack
- **Flask**: Web framework with RESTful API design
- **SQLAlchemy**: ORM with PostgreSQL/SQLite support
- **PySerial**: Direct OBD2 hardware communication
- **Python-OBD**: Advanced OBD2 protocol handling

### Database Schema
- **Vehicle**: Vehicle information and specifications
- **OBDDiagnosticSession**: Diagnostic session tracking
- **DiagnosticTroubleCode**: DTC storage and history
- **SensorReading**: Real-time sensor data logging
- **DtcDatabase**: Comprehensive DTC reference database

### AI Integration
- **Anthropic Claude**: Primary AI provider for diagnostic analysis
- **OpenAI GPT-4**: Alternative provider with fallback support
- **Contextual Prompts**: Vehicle-specific diagnostic reasoning
- **Professional Insights**: Cost estimation and repair procedures

## API Endpoints

### OBD2 Diagnostic API
```bash
# Port Management
GET  /api/obd2/scan-ports        # List available OBD2 ports
POST /obd2/scan                  # Perform diagnostic scan

# DTC Management  
POST /api/obd2/clear-dtcs        # Clear diagnostic codes

# Live Data
GET  /api/obd2/live-data         # Real-time sensor data

# APS Calibration
GET  /api/obd2/aps/read          # Read APS sensor values
POST /api/obd2/aps/calibrate     # Write APS calibration
```

### Web Interface
```bash
/                                # Landing page
/obd2                           # OBD2 dashboard
/obd2/connect                   # Vehicle connection
/obd2/scan                      # Diagnostic scanning
/obd2/live-data-monitoring      # Live data interface
/obd2/aps-calibration          # APS calibration tools
/obd2/results/<session_id>     # Diagnostic results
```

## Configuration

### Environment Variables
- `DATABASE_URL`: Database connection string
- `SESSION_SECRET`: Flask session encryption key
- `ANTHROPIC_API_KEY`: Anthropic Claude API access
- `OPENAI_API_KEY`: OpenAI API access (optional)
- `OBD2_SIMULATION`: Hardware simulation mode
- `LOG_LEVEL`: Application logging level

### OBD2 Settings
- **Simulation Mode**: Full functionality without hardware for development
- **Hardware Mode**: Direct vehicle communication via USB/serial
- **Timeout Settings**: Configurable connection timeouts
- **Protocol Detection**: Automatic OBD2 protocol identification

## Professional Usage

### For Automotive Technicians
- Complete diagnostic workflow integration
- Professional-grade DTC analysis
- Advanced calibration and programming tools
- Comprehensive reporting for customers

### For Enthusiasts
- DIY repair guidance with step-by-step instructions
- Cost-effective diagnostic capabilities
- Educational insights into vehicle systems
- Historical tracking of vehicle health

### For Fleet Management
- Multi-vehicle tracking and management
- Preventive maintenance scheduling
- Cost analysis and reporting
- Compliance monitoring

## OBD2 Connection Troubleshooting

### Generic/No Ports Found
If port scanning shows generic results or no ports:

1. **For USB Adapters:**
   ```bash
   # Check if device is detected
   lsusb  # Linux
   dmesg | tail -20  # Check for device messages
   
   # Fix permissions
   sudo usermod -a -G dialout $USER
   # Log out and log back in
   ```

2. **For Bluetooth Adapters:**
   ```bash
   # Ensure Bluetooth is running
   sudo systemctl status bluetooth
   sudo systemctl restart bluetooth
   
   # Pair the device first
   bluetoothctl
   > scan on
   > pair XX:XX:XX:XX:XX:XX  # Your adapter's MAC
   > connect XX:XX:XX:XX:XX:XX
   > exit
   ```

3. **Common Issues:**
   - **Permission denied**: Add user to dialout group
   - **Device not found**: Check USB cable/Bluetooth pairing
   - **Connection timeout**: Try different USB port or restart Bluetooth

### Testing Your Setup
```bash
# Test USB ports
python -c "import serial.tools.list_ports; print([p.device for p in serial.tools.list_ports.comports()])"

# Test Bluetooth (Linux)
bluetoothctl devices
```

## Development

### Development Mode
```bash
# Enable simulation mode
export OBD2_SIMULATION=true

# Run with debug
python main.py
```

### Testing
- Full simulation environment for development
- Mock DTC codes and sensor data
- Error condition testing
- Hardware compatibility verification

## Security Considerations

### Production Deployment
- Use HTTPS for all communications
- Implement proper session management
- Regular security updates
- Secure database connections

### Data Privacy
- Vehicle data stored locally by default
- AI processing may transmit data to external APIs
- Implement data retention policies
- User consent for data processing

## Support

### Troubleshooting
1. **Connection Issues**: Check OBD2 adapter and vehicle ignition
2. **Port Detection**: Verify correct COM port or device path
3. **AI Integration**: Confirm API keys and internet connectivity
4. **Database Issues**: Check permissions and connection string

### Logs
Application logs stored in `logs/app.log` with automatic rotation.

## License

Professional automotive diagnostic tool for educational and commercial use. Ensure compliance with local regulations regarding vehicle diagnostics and data handling.

## Contributing

1. Follow existing code patterns and style
2. Add comprehensive error handling
3. Update documentation for new features
4. Test with both simulated and real hardware
5. Maintain backward compatibility

---

**Professional OBD2 Diagnostic Tool** - Advanced automotive diagnostics with AI enhancement