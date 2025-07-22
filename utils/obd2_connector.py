"""
OBD2 Connector Module - Professional Grade
This module provides functionality to connect to a vehicle's OBD2 port via USB cable or Bluetooth
and interact with the vehicle's ECU using real OBD2 libraries.
"""

import logging
import random
import time
import os
import platform
from typing import Dict, List, Any, Optional, Union

# Try to import real OBD2 library
try:
    import obd
    from obd import OBDStatus
    import serial.tools.list_ports
    HAS_REAL_OBD = True
except ImportError:
    HAS_REAL_OBD = False
    logging.warning("python-obd library not available. Running in simulation mode only.")

# Try to import Bluetooth libraries
try:
    if platform.system().lower() == 'linux':
        import bluetooth
        HAS_BLUETOOTH = True
    else:
        # For Windows/Mac, try bleak for modern Bluetooth support
        import bleak
        HAS_BLUETOOTH = True
except ImportError:
    HAS_BLUETOOTH = False
    logging.warning("Bluetooth libraries not available. Bluetooth OBD2 adapters will not be detected.")

# Configure logging
logger = logging.getLogger(__name__)

class OBD2Connector:
    """
    Professional OBD2 connector for real vehicle diagnostics.
    Supports both real hardware and simulation for development.
    """
    
    def __init__(self, port: Optional[str] = None, simulate: bool = None):
        """
        Initialize the OBD2 connector.
        
        Args:
            port: The serial port to connect to (e.g., 'COM3' on Windows, '/dev/ttyUSB0' on Linux)
            simulate: Whether to simulate OBD2 connection. Auto-detects if None.
        """
        self.port = port
        # Auto-detect simulation mode if not specified
        if simulate is None:
            self.simulate = not HAS_REAL_OBD or os.getenv('OBD2_SIMULATION', 'false').lower() == 'true'
        else:
            self.simulate = simulate
            
        self.connected = False
        self.connection = None
        self.supported_commands = []
        
        # Connection parameters
        self.protocol = None
        self.ecu_name = None
        self.vin = None
        
        logger.info(f"OBD2Connector initialized - Port: {port}, Simulate: {self.simulate}, Real OBD Available: {HAS_REAL_OBD}")
    
    def scan_for_ports(self) -> List[Dict[str, str]]:
        """
        Scan for available OBD2 ports (both USB and Bluetooth).
        
        Returns:
            List of dictionaries with port information including port name, type, and description
        """
        if self.simulate:
            logger.info("Simulating port scan")
            return self._simulate_port_scan()
        
        ports = []
        
        # Scan for USB/Serial ports
        if HAS_REAL_OBD:
            ports.extend(self._scan_usb_ports())
        
        # Scan for Bluetooth ports
        if HAS_BLUETOOTH:
            ports.extend(self._scan_bluetooth_ports())
        
        # If no ports found, provide helpful message
        if not ports:
            logger.warning("No OBD2 ports detected. Please check connections.")
            return []
        
        logger.info(f"Found {len(ports)} potential OBD2 ports")
        return ports
    
    def _simulate_port_scan(self) -> List[Dict[str, str]]:
        """Simulate realistic port scanning with both USB and Bluetooth options."""
        system = platform.system().lower()
        ports = []
        
        # Simulate USB ports based on OS
        if 'windows' in system:
            usb_ports = ["COM3", "COM4", "COM8"]
        else:  # Linux/Mac
            usb_ports = ["/dev/ttyUSB0", "/dev/ttyUSB1", "/dev/ttyACM0"]
        
        for port in usb_ports:
            ports.append({
                "port": port,
                "type": "USB",
                "description": f"ELM327 USB OBD2 Adapter ({port})",
                "manufacturer": "Generic ELM327"
            })
        
        # Simulate Bluetooth devices
        bluetooth_devices = [
            {"port": "OBDII", "name": "OBDII", "address": "00:1D:A5:68:98:8B"},
            {"port": "ELM327", "name": "ELM327", "address": "00:1D:A5:68:98:8C"},
            {"port": "OBD2_BT", "name": "OBD2_BT", "address": "00:1D:A5:68:98:8D"}
        ]
        
        for device in bluetooth_devices[:2]:  # Simulate finding 2 BT devices
            ports.append({
                "port": f"rfcomm://{device['address']}",
                "type": "Bluetooth",
                "description": f"Bluetooth OBD2 Adapter ({device['name']})",
                "manufacturer": "Generic Bluetooth ELM327",
                "address": device['address']
            })
        
        return ports
    
    def _scan_usb_ports(self) -> List[Dict[str, str]]:
        """Scan for USB/Serial OBD2 adapters."""
        ports = []
        
        try:
            for port in serial.tools.list_ports.comports():
                port_info = {
                    "port": port.device,
                    "type": "USB",
                    "description": port.description,
                    "manufacturer": port.manufacturer or "Unknown"
                }
                
                # Check if it's likely an OBD2 adapter
                description_lower = port.description.lower()
                manufacturer_lower = (port.manufacturer or "").lower()
                
                if any(keyword in description_lower for keyword in 
                      ['elm327', 'obd', 'diagnostic', 'obdlink', 'scantool']):
                    port_info["description"] = f"OBD2 Adapter - {port.description}"
                    ports.append(port_info)
                elif any(keyword in manufacturer_lower for keyword in 
                        ['elm', 'obd', 'diagnostic', 'scantool', 'obdlink']):
                    port_info["description"] = f"Possible OBD2 Adapter - {port.description}"
                    ports.append(port_info)
                elif 'usb' in description_lower and 'serial' in description_lower:
                    # Include generic USB-Serial adapters as potential OBD2 devices
                    port_info["description"] = f"USB Serial Port - {port.description}"
                    ports.append(port_info)
            
            return ports
        except Exception as e:
            logger.error(f"Error scanning USB ports: {e}")
            return []
    
    def _scan_bluetooth_ports(self) -> List[Dict[str, str]]:
        """Scan for Bluetooth OBD2 adapters."""
        ports = []
        
        try:
            if platform.system().lower() == 'linux':
                return self._scan_bluetooth_linux()
            else:
                # For Windows/Mac, we'd use bleak or other methods
                # This is a simplified implementation
                logger.info("Bluetooth scanning not fully implemented for this OS")
                return []
        except Exception as e:
            logger.error(f"Error scanning Bluetooth devices: {e}")
            return []
    
    def _scan_bluetooth_linux(self) -> List[Dict[str, str]]:
        """Scan for Bluetooth devices on Linux."""
        ports = []
        
        try:
            import bluetooth
            
            logger.info("Scanning for Bluetooth devices...")
            nearby_devices = bluetooth.discover_devices(duration=8, lookup_names=True)
            
            for address, name in nearby_devices:
                # Check if device name suggests it's an OBD2 adapter
                name_lower = name.lower() if name else ""
                
                if any(keyword in name_lower for keyword in 
                      ['obd', 'elm327', 'obdii', 'diagnostic', 'car', 'auto']):
                    ports.append({
                        "port": f"rfcomm://{address}",
                        "type": "Bluetooth",
                        "description": f"Bluetooth OBD2 Adapter ({name})",
                        "manufacturer": "Bluetooth ELM327",
                        "address": address,
                        "name": name
                    })
                    
            return ports
        except Exception as e:
            logger.error(f"Error scanning Bluetooth on Linux: {e}")
            return []
    
    def connect(self) -> bool:
        """
        Connect to the vehicle's OBD2 port (USB or Bluetooth).
        
        Returns:
            True if connection is successful, False otherwise
        """
        if self.simulate:
            return self._simulate_connection()
        
        if not HAS_REAL_OBD:
            logger.error("Real OBD library not available")
            return False
        
        try:
            logger.info(f"Attempting real OBD2 connection on port: {self.port}")
            
            # Handle Bluetooth connections differently
            if self.port and self.port.startswith('rfcomm://'):
                return self._connect_bluetooth()
            else:
                return self._connect_usb()
                
        except Exception as e:
            logger.error(f"Error connecting to OBD2 port: {e}")
            self.connected = False
            return False
    
    def _connect_usb(self) -> bool:
        """Connect to USB/Serial OBD2 adapter."""
        try:
            # Create OBD connection
            if self.port:
                self.connection = obd.OBD(self.port, timeout=30)
            else:
                self.connection = obd.OBD(timeout=30)  # Auto-detect port
            
            # Check connection status
            if self.connection.status() == OBDStatus.CAR_CONNECTED:
                self.connected = True
                self.protocol = str(self.connection.protocol_name())
                self.port = self.connection.port_name()
                
                # Get supported commands
                self.supported_commands = list(self.connection.supported_commands)
                logger.info(f"Connected to vehicle via USB {self.port} using {self.protocol}")
                logger.info(f"Supported commands: {len(self.supported_commands)}")
                
                # Try to get VIN if available
                self._try_get_vin()
                
                return True
            else:
                logger.error(f"USB connection failed. Status: {self.connection.status()}")
                self.connected = False
                return False
        except Exception as e:
            logger.error(f"Error connecting via USB: {e}")
            return False
    
    def _connect_bluetooth(self) -> bool:
        """Connect to Bluetooth OBD2 adapter."""
        try:
            # Extract Bluetooth address from rfcomm:// URL
            bt_address = self.port.replace('rfcomm://', '')
            logger.info(f"Attempting Bluetooth connection to {bt_address}")
            
            # For Bluetooth connections, we need to create a serial port
            # This is platform-specific
            if platform.system().lower() == 'linux':
                # On Linux, create rfcomm connection
                bt_port = self._setup_rfcomm_connection(bt_address)
                if not bt_port:
                    return False
                
                # Now connect using the rfcomm port
                self.connection = obd.OBD(bt_port, timeout=30)
            else:
                # On Windows/Mac, python-obd might support Bluetooth directly
                # Try direct connection first
                self.connection = obd.OBD(bt_address, timeout=30)
            
            # Check connection status
            if self.connection.status() == OBDStatus.CAR_CONNECTED:
                self.connected = True
                self.protocol = str(self.connection.protocol_name())
                
                # Get supported commands
                self.supported_commands = list(self.connection.supported_commands)
                logger.info(f"Connected to vehicle via Bluetooth {bt_address} using {self.protocol}")
                logger.info(f"Supported commands: {len(self.supported_commands)}")
                
                # Try to get VIN if available
                self._try_get_vin()
                
                return True
            else:
                logger.error(f"Bluetooth connection failed. Status: {self.connection.status()}")
                self.connected = False
                return False
        except Exception as e:
            logger.error(f"Error connecting via Bluetooth: {e}")
            return False
    
    def _setup_rfcomm_connection(self, bt_address: str) -> Optional[str]:
        """Set up rfcomm connection on Linux for Bluetooth OBD2."""
        try:
            import subprocess
            
            # Find available rfcomm port
            rfcomm_port = "/dev/rfcomm0"
            
            # Release any existing connection
            try:
                subprocess.run(['sudo', 'rfcomm', 'release', 'rfcomm0'], 
                             capture_output=True, check=False)
            except:
                pass
            
            # Create new rfcomm connection
            result = subprocess.run([
                'sudo', 'rfcomm', 'connect', 'rfcomm0', bt_address, '1'
            ], capture_output=True, timeout=10)
            
            if result.returncode == 0:
                logger.info(f"Successfully created rfcomm connection to {bt_address}")
                return rfcomm_port
            else:
                logger.error(f"Failed to create rfcomm connection: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error setting up rfcomm connection: {e}")
            return None
    
    def _try_get_vin(self):
        """Try to retrieve VIN from vehicle."""
        try:
            if obd.commands.VIN in self.supported_commands:
                vin_response = self.connection.query(obd.commands.VIN)
                if not vin_response.is_null():
                    self.vin = str(vin_response.value)
        except Exception as e:
            logger.warning(f"Could not retrieve VIN: {e}")
    
    def _simulate_connection(self) -> bool:
        """Simulate a successful OBD2 connection for development."""
        logger.info("Simulating OBD2 connection")
        time.sleep(1)  # Simulate connection delay
        
        self.connected = True
        self.protocol = "ISO 15765-4 (CAN)"
        self.ecu_name = "Engine Control Module"
        self.vin = "1HGCM82633A123456"  # Sample VIN
        
        # Simulate supported commands
        self.supported_commands = [
            "ENGINE_LOAD", "COOLANT_TEMP", "SHORT_FUEL_TRIM_1", "LONG_FUEL_TRIM_1",
            "FUEL_PRESSURE", "INTAKE_PRESSURE", "RPM", "SPEED", "TIMING_ADVANCE",
            "INTAKE_TEMP", "MAF", "THROTTLE_POS", "O2_B1S1", "O2_B1S2"
        ]
        
        logger.info("Simulated OBD2 connection successful")
        return True
    
    def get_connection_status(self) -> Dict[str, Any]:
        """
        Get the current connection status and vehicle information.
        
        Returns:
            Dictionary with connection status and vehicle info
        """
        if not self.connected:
            return {"connected": False, "error": "Not connected to OBD2 port"}
        
        status = {
            "connected": True,
            "port": self.port,
            "protocol": self.protocol,
            "ecu_name": self.ecu_name,
            "supported_commands": len(self.supported_commands),
            "simulation_mode": self.simulate,
            "vehicle_info": {
                "vin": self.vin,
                "ecu_name": self.ecu_name,
                "protocol": self.protocol
            }
        }
        
        return status
    
    def scan_for_dtcs(self) -> List[Dict[str, str]]:
        """
        Scan for Diagnostic Trouble Codes (DTCs).
        
        Returns:
            List of DTC dictionaries
        """
        if not self.connected:
            logger.error("Not connected to OBD2 port")
            return []
        
        if self.simulate:
            return self._simulate_dtc_scan()
        
        if not HAS_REAL_OBD:
            logger.warning("Real OBD library not available")
            return []
        
        try:
            dtcs = []
            
            # Get stored DTCs
            if obd.commands.GET_DTC in self.supported_commands:
                response = self.connection.query(obd.commands.GET_DTC)
                if not response.is_null():
                    for dtc_tuple in response.value:
                        dtcs.append({
                            'code': dtc_tuple[0],
                            'description': self._get_dtc_description(dtc_tuple[0]),
                            'type': 'stored'
                        })
            
            # Get pending DTCs
            if hasattr(obd.commands, 'GET_CURRENT_DTC'):
                try:
                    response = self.connection.query(obd.commands.GET_CURRENT_DTC)
                    if not response.is_null():
                        for dtc_tuple in response.value:
                            dtcs.append({
                                'code': dtc_tuple[0],
                                'description': self._get_dtc_description(dtc_tuple[0]),
                                'type': 'pending'
                            })
                except:
                    pass  # Command might not be available
            
            logger.info(f"Found {len(dtcs)} DTCs")
            return dtcs
            
        except Exception as e:
            logger.error(f"Error scanning for DTCs: {e}")
            return []
    
    def _simulate_dtc_scan(self) -> List[Dict[str, str]]:
        """Simulate DTC scanning with realistic results."""
        logger.info("Simulating DTC scan")
        time.sleep(2)  # Simulate scan delay
        
        # Realistic DTC simulation
        potential_dtcs = [
            {"code": "P0301", "description": "Cylinder 1 Misfire Detected", "type": "stored"},
            {"code": "P0171", "description": "System Too Lean (Bank 1)", "type": "stored"},
            {"code": "P0420", "description": "Catalyst System Efficiency Below Threshold (Bank 1)", "type": "stored"},
            {"code": "P0442", "description": "Evaporative Emission Control System Leak Detected (Small Leak)", "type": "pending"},
            {"code": "P0113", "description": "Intake Air Temperature Circuit High Input", "type": "stored"},
            {"code": "P0131", "description": "O2 Sensor Circuit Low Voltage (Bank 1, Sensor 1)", "type": "stored"}
        ]
        
        # Return 0-3 random DTCs (70% chance of having DTCs)
        if random.random() < 0.7:
            num_dtcs = random.randint(1, 3)
            return random.sample(potential_dtcs, min(num_dtcs, len(potential_dtcs)))
        else:
            return []
    
    def read_live_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Read live sensor data from the vehicle.
        
        Returns:
            Dictionary of sensor readings
        """
        if not self.connected:
            logger.error("Not connected to OBD2 port")
            return {}
        
        if self.simulate:
            return self._simulate_live_data()
        
        if not HAS_REAL_OBD:
            logger.warning("Real OBD library not available")
            return {}
        
        try:
            sensor_data = {}
            
            # Define standard OBD2 PIDs to read
            pid_mapping = {
                obd.commands.RPM: "RPM",
                obd.commands.SPEED: "SPEED", 
                obd.commands.COOLANT_TEMP: "COOLANT_TEMP",
                obd.commands.INTAKE_TEMP: "INTAKE_TEMP",
                obd.commands.ENGINE_LOAD: "ENGINE_LOAD",
                obd.commands.THROTTLE_POS: "THROTTLE_POS",
                obd.commands.MAF: "MAF",
                obd.commands.FUEL_PRESSURE: "FUEL_PRESSURE",
                obd.commands.INTAKE_PRESSURE: "INTAKE_PRESSURE",
                obd.commands.TIMING_ADVANCE: "TIMING_ADVANCE",
                obd.commands.SHORT_FUEL_TRIM_1: "SHORT_FUEL_TRIM_1",
                obd.commands.LONG_FUEL_TRIM_1: "LONG_FUEL_TRIM_1"
            }
            
            # Query each supported PID
            for command, name in pid_mapping.items():
                if command in self.supported_commands:
                    try:
                        response = self.connection.query(command)
                        if not response.is_null():
                            sensor_data[name] = {
                                "value": float(response.value.magnitude) if hasattr(response.value, 'magnitude') else float(response.value),
                                "unit": str(response.unit) if response.unit else "",
                                "name": name.replace('_', ' ').title()
                            }
                    except Exception as e:
                        logger.warning(f"Error reading {name}: {e}")
            
            logger.info(f"Read {len(sensor_data)} sensor values")
            return sensor_data
            
        except Exception as e:
            logger.error(f"Error reading live data: {e}")
            return {}
    
    def _simulate_live_data(self) -> Dict[str, Dict[str, Any]]:
        """Simulate realistic live sensor data."""
        # Generate realistic sensor values with some variation
        base_values = {
            "RPM": (750, 50, "rpm"),
            "SPEED": (0, 2, "km/h"),
            "COOLANT_TEMP": (88, 5, "°C"),
            "INTAKE_TEMP": (25, 3, "°C"),
            "ENGINE_LOAD": (18, 5, "%"),
            "THROTTLE_POS": (16, 3, "%"),
            "MAF": (12, 2, "g/s"),
            "FUEL_PRESSURE": (395, 10, "kPa"),
            "INTAKE_PRESSURE": (98, 3, "kPa"),
            "TIMING_ADVANCE": (10, 2, "degrees"),
            "SHORT_FUEL_TRIM_1": (2, 3, "%"),
            "LONG_FUEL_TRIM_1": (1, 2, "%"),
            "BATTERY_VOLTAGE": (14.1, 0.2, "V"),
            "FUEL_LEVEL": (65, 0, "%")
        }
        
        sensor_data = {}
        for name, (base, variance, unit) in base_values.items():
            value = base + random.uniform(-variance, variance)
            sensor_data[name] = {
                "value": round(value, 2),
                "unit": unit,
                "name": name.replace('_', ' ').title()
            }
        
        return sensor_data
    
    def clear_dtcs(self) -> bool:
        """
        Clear diagnostic trouble codes from the vehicle.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.connected:
            logger.error("Not connected to OBD2 port")
            return False
        
        if self.simulate:
            logger.info("Simulating DTC clear")
            time.sleep(2)
            return True
        
        if not HAS_REAL_OBD:
            logger.warning("Real OBD library not available")
            return False
        
        try:
            # Send clear DTC command
            if obd.commands.CLEAR_DTC in self.supported_commands:
                response = self.connection.query(obd.commands.CLEAR_DTC)
                success = not response.is_null()
                if success:
                    logger.info("DTCs cleared successfully")
                return success
            else:
                logger.warning("Clear DTC command not supported")
                return False
        except Exception as e:
            logger.error(f"Error clearing DTCs: {e}")
            return False
    
    def read_freeze_frame_data(self, dtc_code: str) -> Dict[str, Any]:
        """
        Read freeze frame data for a specific DTC.
        
        Args:
            dtc_code: The DTC code to get freeze frame data for
            
        Returns:
            Dictionary with freeze frame data
        """
        if not self.connected:
            logger.error("Not connected to OBD2 port")
            return {}
        
        if self.simulate:
            return self._simulate_freeze_frame(dtc_code)
        
        # Real freeze frame reading would require more complex implementation
        # This is a simplified version
        logger.warning("Freeze frame reading not fully implemented for real hardware")
        return {}
    
    def _simulate_freeze_frame(self, dtc_code: str) -> Dict[str, Any]:
        """Simulate freeze frame data."""
        return {
            "dtc_code": dtc_code,
            "RPM": round(random.uniform(1500, 3000), 0),
            "SPEED": round(random.uniform(30, 80), 0),
            "COOLANT_TEMP": round(random.uniform(85, 105), 1),
            "THROTTLE_POS": round(random.uniform(20, 60), 1),
            "ENGINE_LOAD": round(random.uniform(30, 80), 1),
            "FUEL_TRIM_1": round(random.uniform(-15, 15), 1),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def disconnect(self) -> bool:
        """
        Disconnect from the vehicle's OBD2 port.
        
        Returns:
            True if disconnection is successful, False otherwise
        """
        try:
            if self.connection and not self.simulate:
                self.connection.close()
            
            self.connected = False
            self.connection = None
            logger.info("Disconnected from OBD2 port")
            return True
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
            return False
    
    def _get_dtc_description(self, code: str) -> str:
        """
        Get description for a DTC code.
        
        Args:
            code: DTC code (e.g., 'P0301')
            
        Returns:
            Human-readable description
        """
        # Basic DTC descriptions - in production this would use a comprehensive database
        descriptions = {
            'P0301': 'Cylinder 1 Misfire Detected',
            'P0302': 'Cylinder 2 Misfire Detected',
            'P0303': 'Cylinder 3 Misfire Detected',
            'P0304': 'Cylinder 4 Misfire Detected',
            'P0171': 'System Too Lean (Bank 1)',
            'P0172': 'System Too Rich (Bank 1)',
            'P0420': 'Catalyst System Efficiency Below Threshold (Bank 1)',
            'P0442': 'Evaporative Emission Control System Leak Detected (Small Leak)',
            'P0113': 'Intake Air Temperature Circuit High Input',
            'P0131': 'O2 Sensor Circuit Low Voltage (Bank 1, Sensor 1)',
            'P0300': 'Random/Multiple Cylinder Misfire Detected'
        }
        
        return descriptions.get(code, f'Unknown DTC: {code}')


def create_obd2_connector(port: Optional[str] = None, simulate: bool = None) -> OBD2Connector:
    """
    Factory function to create an OBD2Connector instance.
    
    Args:
        port: The serial port to connect to
        simulate: Force simulation mode (auto-detects if None)
        
    Returns:
        An OBD2Connector instance
    """
    logger.info(f"Creating OBD2Connector - Port: {port}, Simulate: {simulate}, Real OBD Available: {HAS_REAL_OBD}")
    return OBD2Connector(port=port, simulate=simulate)