"""
OBD2 Connector Module
This module provides functionality to connect to a vehicle's OBD2 port via USB
and retrieve diagnostic information.
"""

import logging
import time
import re
import serial
import serial.tools.list_ports
from typing import Dict, List, Union, Optional, Tuple, Any

# Configure logging
logger = logging.getLogger(__name__)

# OBD2 Mode Commands
MODE1 = "01"  # Show current data
MODE2 = "02"  # Show freeze frame data
MODE3 = "03"  # Show stored diagnostic trouble codes
MODE4 = "04"  # Clear diagnostic trouble codes and stored values
MODE5 = "05"  # Test results, oxygen sensor monitoring
MODE6 = "06"  # Test results, other components
MODE7 = "07"  # Show pending diagnostic trouble codes
MODE9 = "09"  # Vehicle information
MODE10 = "0A"  # Permanent DTCs

# Common PIDs (Parameter IDs) for Mode 01
PID_SUPPORTED = "00"  # PIDs supported [01 - 20]
PID_STATUS = "01"  # Monitor status since DTCs cleared
PID_FREEZE_DTC = "02"  # DTC that triggered the freeze frame
PID_FUEL_STATUS = "03"  # Fuel system status
PID_ENGINE_LOAD = "04"  # Calculated engine load
PID_COOLANT_TEMP = "05"  # Engine coolant temperature
PID_SHORT_FUEL_TRIM_1 = "06"  # Short term fuel trim - Bank 1
PID_LONG_FUEL_TRIM_1 = "07"  # Long term fuel trim - Bank 1
PID_SHORT_FUEL_TRIM_2 = "08"  # Short term fuel trim - Bank 2
PID_LONG_FUEL_TRIM_2 = "09"  # Long term fuel trim - Bank 2
PID_FUEL_PRESSURE = "0A"  # Fuel pressure
PID_INTAKE_PRESSURE = "0B"  # Intake manifold absolute pressure
PID_RPM = "0C"  # Engine RPM
PID_SPEED = "0D"  # Vehicle speed
PID_TIMING_ADVANCE = "0E"  # Timing advance
PID_INTAKE_TEMP = "0F"  # Intake air temperature
PID_MAF = "10"  # Mass air flow sensor (MAF) air flow rate
PID_THROTTLE = "11"  # Throttle position
PID_COMMANDED_SECONDARY_AIR = "12"  # Commanded secondary air status
PID_OXYGEN_SENSORS_PRESENT = "13"  # Oxygen sensors present
PID_OXYGEN_SENSOR_1 = "14"  # Oxygen Sensor 1
PID_OXYGEN_SENSOR_2 = "15"  # Oxygen Sensor 2
PID_OXYGEN_SENSOR_3 = "16"  # Oxygen Sensor 3
PID_OXYGEN_SENSOR_4 = "17"  # Oxygen Sensor 4
PID_OXYGEN_SENSOR_5 = "18"  # Oxygen Sensor 5
PID_OXYGEN_SENSOR_6 = "19"  # Oxygen Sensor 6
PID_OXYGEN_SENSOR_7 = "1A"  # Oxygen Sensor 7
PID_OXYGEN_SENSOR_8 = "1B"  # Oxygen Sensor 8
PID_OBD_STANDARD = "1C"  # OBD standards the vehicle conforms to
PID_RUN_TIME = "1F"  # Run time since engine start

# Common PIDs for Mode 09 (Vehicle Information)
PID_VIN_COUNT = "01"  # VIN message count
PID_VIN = "02"  # Vehicle Identification Number (VIN)
PID_CALIBRATION_ID_COUNT = "03"  # Calibration ID message count
PID_CALIBRATION_ID = "04"  # Calibration IDs
PID_ECU_NAME_COUNT = "0A"  # ECU name message count
PID_ECU_NAME = "0B"  # ECU name

# DTC Letter Codes
DTC_LETTERS = {
    "0": "P",  # Powertrain
    "1": "C",  # Chassis
    "2": "B",  # Body
    "3": "U",  # Network
}

# OBD2 Response Error Codes
ERROR_CODES = {
    "7F": "Error",
    "NO DATA": "No Data",
    "BUS INIT: ERROR": "Bus Initialization Error",
    "?": "Unknown command",
    "SEARCHING": "Searching...",
    "CAN ERROR": "CAN Error",
}


class OBD2Connector:
    """Class for interfacing with a vehicle's OBD2 port via USB."""

    def __init__(self, port: Optional[str] = None, baudrate: int = 38400, timeout: int = 10):
        """
        Initialize the OBD2 connector.
        
        Args:
            port: Serial port of the OBD2 adapter (e.g., '/dev/ttyUSB0')
            baudrate: Baud rate for the serial connection
            timeout: Connection timeout in seconds
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_connection = None
        self.connected = False
        self.protocol = None
        self.supported_pids = {}
        self.dtc_count = 0
        
        logger.info(f"Initializing OBD2Connector on port {port}")
    
    def find_obd_ports(self) -> List[str]:
        """
        Find available OBD2 adapters connected via USB.
        
        Returns:
            List of available serial ports
        """
        available_ports = []
        logger.info("Searching for OBD2 adapters...")
        
        # List all serial ports
        ports = serial.tools.list_ports.comports()
        
        for port in ports:
            # Common identifiers for OBD2 adapters
            if any(identifier in port.description.lower() for identifier in ["obd", "elm327", "obdii", "adapter"]):
                logger.info(f"Found potential OBD2 adapter: {port.device} - {port.description}")
                available_ports.append(port.device)
            elif "usb" in port.device.lower() or "ttyUSB" in port.device:
                # Add USB serial devices as potential adapters
                logger.info(f"Found potential USB device: {port.device} - {port.description}")
                available_ports.append(port.device)
        
        return available_ports
    
    def connect(self) -> bool:
        """
        Connect to the OBD2 adapter.
        
        Returns:
            True if connection successful, False otherwise
        """
        # If port not specified, try to find one
        if not self.port:
            ports = self.find_obd_ports()
            if not ports:
                logger.error("No OBD2 adapters found")
                return False
            self.port = ports[0]
            logger.info(f"Auto-selected port: {self.port}")
        
        try:
            # Open serial connection
            logger.info(f"Connecting to OBD2 adapter on {self.port} at {self.baudrate} baud")
            self.serial_connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                bytesize=8,
                parity='N',
                stopbits=1
            )
            
            # Reset the adapter
            self.serial_connection.reset_input_buffer()  # Modern equivalent of flushInput
            time.sleep(0.5)
            
            # Initialize the adapter
            self._send_command("ATZ")  # Reset
            time.sleep(1)
            
            self._send_command("ATE0")  # Echo off
            self._send_command("ATL0")  # Linefeeds off
            self._send_command("ATS0")  # Spaces off
            self._send_command("ATH0")  # Headers off
            self._send_command("ATAT1")  # Adaptive timing on
            self._send_command("ATSP0")  # Auto-protocol detection
            
            # Try to establish connection with the vehicle
            response = self._send_command("0100")  # Request supported PIDs
            if "NO DATA" in response or "ERROR" in response:
                logger.error("No response from vehicle. Check if ignition is on.")
                return False
            
            # Get current protocol
            protocol_response = self._send_command("ATDP")
            self.protocol = protocol_response
            logger.info(f"Connected using protocol: {self.protocol}")
            
            # Get supported PIDs
            self._get_supported_pids()
            
            self.connected = True
            logger.info("Successfully connected to vehicle")
            return True
            
        except serial.SerialException as e:
            logger.error(f"Serial connection error: {e}")
            return False
        except Exception as e:
            logger.error(f"Error connecting to OBD2 adapter: {e}")
            return False
    
    def disconnect(self) -> bool:
        """
        Disconnect from the OBD2 adapter.
        
        Returns:
            True if disconnection successful, False otherwise
        """
        if self.serial_connection and self.serial_connection.is_open:
            try:
                # Reset the adapter
                self._send_command("ATZ")
                time.sleep(0.5)
                
                # Close the connection
                self.serial_connection.close()
                self.connected = False
                logger.info("Disconnected from OBD2 adapter")
                return True
            except Exception as e:
                logger.error(f"Error disconnecting from OBD2 adapter: {e}")
                return False
        return True
    
    def _send_command(self, command: str) -> str:
        """
        Send a command to the OBD2 adapter and get the response.
        
        Args:
            command: Command to send
            
        Returns:
            Response string
        """
        if not self.serial_connection or not self.serial_connection.is_open:
            logger.error("Serial connection not open")
            return "ERROR"
        
        try:
            # Clear any pending data
            self.serial_connection.reset_input_buffer()
            
            # Send the command with carriage return
            full_command = f"{command}\r"
            self.serial_connection.write(full_command.encode())
            
            # Read the response
            response = ""
            start_time = time.time()
            
            while True:
                # Check for timeout
                if time.time() - start_time > self.timeout:
                    logger.warning(f"Command {command} timed out")
                    break
                
                # Read a line
                if self.serial_connection.in_waiting:
                    line = self.serial_connection.readline().decode('utf-8', errors='ignore').strip()
                    
                    # Skip echo and empty lines
                    if not line or line == command:
                        continue
                    
                    # Check for prompt
                    if line == ">":
                        break
                    
                    # Add to response
                    response += line + " "
                else:
                    time.sleep(0.01)  # Small delay to prevent CPU hogging
            
            # Clean up the response
            response = response.strip()
            logger.debug(f"Command: {command}, Response: {response}")
            
            return response
            
        except Exception as e:
            logger.error(f"Error sending command {command}: {e}")
            return "ERROR"
    
    def _parse_pid_response(self, response: str, pid: str) -> Optional[str]:
        """
        Parse the response from a PID request.
        
        Args:
            response: Response string
            pid: The PID that was requested
            
        Returns:
            Parsed data or None if error
        """
        if not response or any(error in response for error in ERROR_CODES.keys()):
            return None
        
        # Remove whitespace and check for empty response
        response = response.replace(" ", "")
        if not response:
            return None
        
        # Check if response starts with the requested mode+pid
        expected_prefix = "41" + pid  # 41 = response to mode 01 command
        if not response.startswith(expected_prefix):
            logger.warning(f"Unexpected response format for PID {pid}: {response}")
            # Try to extract data anyway, removing any headers
            data_start = response.find(expected_prefix)
            if data_start >= 0:
                response = response[data_start:]
            else:
                return None
        
        # Extract the data part
        data = response[4:]  # Skip mode+pid (4 characters)
        return data
    
    def _get_supported_pids(self) -> None:
        """
        Query the vehicle for supported PIDs and store them.
        """
        pid_ranges = ["00", "20", "40", "60", "80", "A0", "C0", "E0"]
        
        for range_start in pid_ranges:
            response = self._send_command(f"01{range_start}")
            data = self._parse_pid_response(response, range_start)
            
            if not data:
                continue
            
            # Convert hex data to binary representation
            try:
                # For each pair of hex characters
                binary = ""
                for i in range(0, len(data), 2):
                    if i+1 < len(data):
                        hex_pair = data[i:i+2]
                        value = int(hex_pair, 16)
                        binary += format(value, '08b')
                
                # Set supported PIDs based on binary digits
                start_pid = int(range_start, 16) + 1
                for i, bit in enumerate(binary):
                    if bit == '1':
                        pid_value = format(start_pid + i, '02X')
                        self.supported_pids[pid_value] = True
                        logger.debug(f"PID {pid_value} is supported")
            
            except Exception as e:
                logger.error(f"Error parsing supported PIDs for range {range_start}: {e}")
    
    def is_pid_supported(self, pid: str) -> bool:
        """
        Check if a specific PID is supported.
        
        Args:
            pid: Parameter ID to check
            
        Returns:
            True if supported, False otherwise
        """
        return pid in self.supported_pids
    
    def get_vehicle_info(self) -> Dict[str, str]:
        """
        Get vehicle information (VIN, ECU name, etc.).
        
        Returns:
            Dictionary of vehicle information
        """
        vehicle_info = {}
        
        # Get VIN
        vin_response = self._send_command("0902")
        if vin_response and "NO DATA" not in vin_response and "ERROR" not in vin_response:
            try:
                # Extract VIN from response
                vin = ""
                
                # Split the response into lines and process each line
                for line in vin_response.split():
                    # Remove any headers or prefixes
                    if "49" in line:  # 49 is the response code for mode 09
                        # Find the data portion after the PID
                        data_index = line.find("49020")
                        if data_index >= 0:
                            # Skip the prefix (49020)
                            data = line[data_index + 5:]
                            
                            # Convert hex pairs to ASCII
                            for i in range(0, len(data), 2):
                                if i+1 < len(data):
                                    hex_char = data[i:i+2]
                                    if hex_char != "00":  # Skip null characters
                                        try:
                                            ascii_char = chr(int(hex_char, 16))
                                            if ascii_char.isprintable():
                                                vin += ascii_char
                                        except ValueError:
                                            pass
                
                # Clean up the VIN (should be 17 characters)
                vin = re.sub(r'[^A-Z0-9]', '', vin.upper())
                if len(vin) >= 17:
                    vin = vin[:17]  # Take only first 17 characters
                    vehicle_info["vin"] = vin
                    logger.info(f"Retrieved VIN: {vin}")
            except Exception as e:
                logger.error(f"Error parsing VIN: {e}")
        
        # Get ECU name
        ecu_response = self._send_command("090B")
        if ecu_response and "NO DATA" not in ecu_response and "ERROR" not in ecu_response:
            try:
                # Extract ECU name from response
                ecu_name = ""
                
                # Split the response into lines and process each line
                for line in ecu_response.split():
                    # Remove any headers or prefixes
                    if "49" in line:  # 49 is the response code for mode 09
                        # Find the data portion after the PID
                        data_index = line.find("490B")
                        if data_index >= 0:
                            # Skip the prefix (490B)
                            data = line[data_index + 4:]
                            
                            # Convert hex pairs to ASCII
                            for i in range(0, len(data), 2):
                                if i+1 < len(data):
                                    hex_char = data[i:i+2]
                                    if hex_char != "00":  # Skip null characters
                                        try:
                                            ascii_char = chr(int(hex_char, 16))
                                            if ascii_char.isprintable():
                                                ecu_name += ascii_char
                                        except ValueError:
                                            pass
                
                # Clean up the ECU name
                ecu_name = re.sub(r'[^A-Za-z0-9 _-]', '', ecu_name).strip()
                if ecu_name:
                    vehicle_info["ecu_name"] = ecu_name
                    logger.info(f"Retrieved ECU name: {ecu_name}")
            except Exception as e:
                logger.error(f"Error parsing ECU name: {e}")
        
        # Add protocol information
        if self.protocol:
            vehicle_info["protocol"] = self.protocol
        
        return vehicle_info
    
    def read_dtcs(self) -> List[Dict[str, str]]:
        """
        Read Diagnostic Trouble Codes (DTCs) from the vehicle.
        
        Returns:
            List of dictionaries with DTC information
        """
        dtcs = []
        
        # Get stored DTCs (Mode 03)
        stored_response = self._send_command("03")
        stored_dtcs = self._parse_dtcs(stored_response, "stored")
        dtcs.extend(stored_dtcs)
        
        # Get pending DTCs (Mode 07)
        pending_response = self._send_command("07")
        pending_dtcs = self._parse_dtcs(pending_response, "pending")
        dtcs.extend(pending_dtcs)
        
        # Get permanent DTCs (Mode 0A)
        permanent_response = self._send_command("0A")
        permanent_dtcs = self._parse_dtcs(permanent_response, "permanent")
        dtcs.extend(permanent_dtcs)
        
        # Store the total DTC count
        self.dtc_count = len(dtcs)
        logger.info(f"Retrieved {self.dtc_count} DTCs")
        
        return dtcs
    
    def _parse_dtcs(self, response: str, dtc_type: str) -> List[Dict[str, str]]:
        """
        Parse DTC codes from response string.
        
        Args:
            response: Response string from OBD command
            dtc_type: Type of DTC (stored, pending, permanent)
            
        Returns:
            List of dictionaries with DTC information
        """
        dtcs = []
        
        if not response or "NO DATA" in response or "ERROR" in response:
            return dtcs
        
        try:
            # Remove spaces and split by line
            response = response.replace(" ", "")
            
            # Expected response pattern differs by mode
            if dtc_type == "stored":
                prefix = "43"  # Response to mode 03
            elif dtc_type == "pending":
                prefix = "47"  # Response to mode 07
            elif dtc_type == "permanent":
                prefix = "4A"  # Response to mode 0A
            else:
                logger.error(f"Unknown DTC type: {dtc_type}")
                return dtcs
            
            # Find the prefix position
            prefix_pos = response.find(prefix)
            if prefix_pos == -1:
                logger.warning(f"Response doesn't contain expected prefix {prefix}: {response}")
                return dtcs
            
            # Extract data part (after prefix)
            data = response[prefix_pos + len(prefix):]
            
            # Parse DTCs (each DTC is 4 characters)
            for i in range(0, len(data), 4):
                if i + 3 < len(data):
                    dtc_hex = data[i:i+4]
                    
                    # Skip if DTC is 0000 (no error)
                    if dtc_hex == "0000":
                        continue
                    
                    # Convert to standard DTC format
                    try:
                        # First character indicates DTC type (P, C, B, U)
                        dtc_type_char = DTC_LETTERS.get(dtc_hex[0], "P")
                        
                        # Second character is the code group
                        dtc_group = dtc_hex[1]
                        
                        # Last two characters are the specific code
                        dtc_specific = dtc_hex[2:4]
                        
                        # Format the full DTC
                        dtc_code = f"{dtc_type_char}{dtc_group}{dtc_specific}"
                        
                        # Get description (would come from a database in a real implementation)
                        description = self._get_dtc_description(dtc_code)
                        
                        # Add to list
                        dtcs.append({
                            "code": dtc_code,
                            "description": description,
                            "type": dtc_type
                        })
                        
                        logger.info(f"Found {dtc_type} DTC: {dtc_code} - {description}")
                    except Exception as e:
                        logger.error(f"Error parsing DTC {dtc_hex}: {e}")
        
        except Exception as e:
            logger.error(f"Error parsing DTCs: {e}")
        
        return dtcs
    
    def _get_dtc_description(self, dtc_code: str) -> str:
        """
        Get the description for a DTC code.
        This would normally query a database of DTC codes.
        
        Args:
            dtc_code: The DTC code (e.g., P0301)
            
        Returns:
            Description string
        """
        # In a real implementation, this would query a database
        # For demo purposes, we'll provide descriptions for some common codes
        dtc_descriptions = {
            "P0100": "Mass or Volume Air Flow Circuit Malfunction",
            "P0101": "Mass or Volume Air Flow Circuit Range/Performance Problem",
            "P0102": "Mass or Volume Air Flow Circuit Low Input",
            "P0103": "Mass or Volume Air Flow Circuit High Input",
            "P0104": "Mass or Volume Air Flow Circuit Intermittent",
            "P0105": "Manifold Absolute Pressure/Barometric Pressure Circuit Malfunction",
            "P0106": "Manifold Absolute Pressure/Barometric Pressure Circuit Range/Performance Problem",
            "P0107": "Manifold Absolute Pressure/Barometric Pressure Circuit Low Input",
            "P0108": "Manifold Absolute Pressure/Barometric Pressure Circuit High Input",
            "P0109": "Manifold Absolute Pressure/Barometric Pressure Circuit Intermittent",
            "P0110": "Intake Air Temperature Circuit Malfunction",
            "P0111": "Intake Air Temperature Circuit Range/Performance Problem",
            "P0112": "Intake Air Temperature Circuit Low Input",
            "P0113": "Intake Air Temperature Circuit High Input",
            "P0114": "Intake Air Temperature Circuit Intermittent",
            "P0115": "Engine Coolant Temperature Circuit Malfunction",
            "P0116": "Engine Coolant Temperature Circuit Range/Performance Problem",
            "P0117": "Engine Coolant Temperature Circuit Low Input",
            "P0118": "Engine Coolant Temperature Circuit High Input",
            "P0119": "Engine Coolant Temperature Circuit Intermittent",
            "P0120": "Throttle/Pedal Position Sensor/Switch A Circuit Malfunction",
            "P0121": "Throttle/Pedal Position Sensor/Switch A Circuit Range/Performance Problem",
            "P0122": "Throttle/Pedal Position Sensor/Switch A Circuit Low Input",
            "P0123": "Throttle/Pedal Position Sensor/Switch A Circuit High Input",
            "P0124": "Throttle/Pedal Position Sensor/Switch A Circuit Intermittent",
            "P0125": "Insufficient Coolant Temperature for Closed Loop Fuel Control",
            "P0126": "Insufficient Coolant Temperature for Stable Operation",
            "P0127": "Intake Air Temperature Too High",
            "P0128": "Coolant Thermostat (Coolant Temperature Below Thermostat Regulating Temperature)",
            "P0129": "Barometric Pressure Too Low",
            "P0130": "O2 Sensor Circuit Malfunction (Bank 1 Sensor 1)",
            "P0131": "O2 Sensor Circuit Low Voltage (Bank 1 Sensor 1)",
            "P0132": "O2 Sensor Circuit High Voltage (Bank 1 Sensor 1)",
            "P0133": "O2 Sensor Circuit Slow Response (Bank 1 Sensor 1)",
            "P0134": "O2 Sensor Circuit No Activity Detected (Bank 1 Sensor 1)",
            "P0135": "O2 Sensor Heater Circuit Malfunction (Bank 1 Sensor 1)",
            "P0136": "O2 Sensor Circuit Malfunction (Bank 1 Sensor 2)",
            "P0137": "O2 Sensor Circuit Low Voltage (Bank 1 Sensor 2)",
            "P0138": "O2 Sensor Circuit High Voltage (Bank 1 Sensor 2)",
            "P0139": "O2 Sensor Circuit Slow Response (Bank 1 Sensor 2)",
            "P0140": "O2 Sensor Circuit No Activity Detected (Bank 1 Sensor 2)",
            "P0141": "O2 Sensor Heater Circuit Malfunction (Bank 1 Sensor 2)",
            "P0142": "O2 Sensor Circuit Malfunction (Bank 1 Sensor 3)",
            "P0143": "O2 Sensor Circuit Low Voltage (Bank 1 Sensor 3)",
            "P0144": "O2 Sensor Circuit High Voltage (Bank 1 Sensor 3)",
            "P0145": "O2 Sensor Circuit Slow Response (Bank 1 Sensor 3)",
            "P0146": "O2 Sensor Circuit No Activity Detected (Bank 1 Sensor 3)",
            "P0147": "O2 Sensor Heater Circuit Malfunction (Bank 1 Sensor 3)",
            "P0148": "Fuel Delivery Error",
            "P0149": "Fuel Timing Error",
            "P0150": "O2 Sensor Circuit Malfunction (Bank 2 Sensor 1)",
            "P0151": "O2 Sensor Circuit Low Voltage (Bank 2 Sensor 1)",
            "P0152": "O2 Sensor Circuit High Voltage (Bank 2 Sensor 1)",
            "P0153": "O2 Sensor Circuit Slow Response (Bank 2 Sensor 1)",
            "P0154": "O2 Sensor Circuit No Activity Detected (Bank 2 Sensor 1)",
            "P0155": "O2 Sensor Heater Circuit Malfunction (Bank 2 Sensor 1)",
            "P0156": "O2 Sensor Circuit Malfunction (Bank 2 Sensor 2)",
            "P0157": "O2 Sensor Circuit Low Voltage (Bank 2 Sensor 2)",
            "P0158": "O2 Sensor Circuit High Voltage (Bank 2 Sensor 2)",
            "P0159": "O2 Sensor Circuit Slow Response (Bank 2 Sensor 2)",
            "P0160": "O2 Sensor Circuit No Activity Detected (Bank 2 Sensor 2)",
            "P0161": "O2 Sensor Heater Circuit Malfunction (Bank 2 Sensor 2)",
            "P0162": "O2 Sensor Circuit Malfunction (Bank 2 Sensor 3)",
            "P0163": "O2 Sensor Circuit Low Voltage (Bank 2 Sensor 3)",
            "P0164": "O2 Sensor Circuit High Voltage (Bank 2 Sensor 3)",
            "P0165": "O2 Sensor Circuit Slow Response (Bank 2 Sensor 3)",
            "P0166": "O2 Sensor Circuit No Activity Detected (Bank 2 Sensor 3)",
            "P0167": "O2 Sensor Heater Circuit Malfunction (Bank 2 Sensor 3)",
            "P0168": "Fuel Temperature Too High",
            "P0169": "Incorrect Fuel Composition",
            "P0170": "Fuel Trim Malfunction (Bank 1)",
            "P0171": "System Too Lean (Bank 1)",
            "P0172": "System Too Rich (Bank 1)",
            "P0173": "Fuel Trim Malfunction (Bank 2)",
            "P0174": "System Too Lean (Bank 2)",
            "P0175": "System Too Rich (Bank 2)",
            "P0176": "Fuel Composition Sensor Circuit Malfunction",
            "P0177": "Fuel Composition Sensor Circuit Range/Performance",
            "P0178": "Fuel Composition Sensor Circuit Low Input",
            "P0179": "Fuel Composition Sensor Circuit High Input",
            "P0180": "Fuel Temperature Sensor A Circuit Malfunction",
            "P0301": "Cylinder 1 Misfire Detected",
            "P0302": "Cylinder 2 Misfire Detected",
            "P0303": "Cylinder 3 Misfire Detected",
            "P0304": "Cylinder 4 Misfire Detected",
            "P0305": "Cylinder 5 Misfire Detected",
            "P0306": "Cylinder 6 Misfire Detected",
            "P0420": "Catalyst System Efficiency Below Threshold (Bank 1)",
            "P0430": "Catalyst System Efficiency Below Threshold (Bank 2)",
            "P0440": "Evaporative Emission Control System Malfunction",
            "P0442": "Evaporative Emission Control System Leak Detected (Small Leak)",
            "P0446": "Evaporative Emission Control System Vent Control Circuit Malfunction",
            "P0456": "Evaporative Emission Control System Leak Detected (Very Small Leak)",
            "P0700": "Transmission Control System Malfunction",
        }
        
        return dtc_descriptions.get(dtc_code, "Unknown code description")
    
    def clear_dtcs(self) -> bool:
        """
        Clear all Diagnostic Trouble Codes (DTCs) and freeze frame data.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.connected:
            logger.error("Not connected to vehicle")
            return False
        
        try:
            response = self._send_command("04")  # Mode 04 - Clear DTCs
            
            # Check if clear was successful
            if "44" in response:
                logger.info("Successfully cleared DTCs")
                return True
            else:
                logger.warning(f"Failed to clear DTCs: {response}")
                return False
        except Exception as e:
            logger.error(f"Error clearing DTCs: {e}")
            return False
    
    def read_pid(self, pid: str) -> Optional[Dict[str, Any]]:
        """
        Read a specific PID from the vehicle.
        
        Args:
            pid: Parameter ID to read
            
        Returns:
            Dictionary with sensor data or None if not supported/error
        """
        if not self.connected:
            logger.error("Not connected to vehicle")
            return None
        
        # Check if PID is supported
        if not self.is_pid_supported(pid):
            logger.warning(f"PID {pid} is not supported by this vehicle")
            return None
        
        try:
            # Send the command
            response = self._send_command(f"01{pid}")
            data = self._parse_pid_response(response, pid)
            
            if not data:
                return None
            
            # Parse the data according to the PID
            result = self._decode_pid(pid, data)
            
            if result:
                result['raw_response'] = response
                return result
            
            return None
        
        except Exception as e:
            logger.error(f"Error reading PID {pid}: {e}")
            return None
    
    def _decode_pid(self, pid: str, data: str) -> Dict[str, Union[float, int, str]]:
        """
        Decode PID data based on the PID type.
        
        Args:
            pid: Parameter ID
            data: Hex data from response
            
        Returns:
            Dictionary with decoded values
        """
        try:
            # Convert hex data to bytes
            data_bytes = []
            for i in range(0, len(data), 2):
                if i+1 < len(data):
                    hex_pair = data[i:i+2]
                    data_bytes.append(int(hex_pair, 16))
            
            # Return dictionary with format {name, value, unit}
            result = {
                'name': 'Unknown',
                'value': 0,
                'unit': ''
            }
            
            # Decode based on PID
            if pid == PID_ENGINE_LOAD:
                result['name'] = 'Engine Load'
                result['value'] = data_bytes[0] * 100.0 / 255.0
                result['unit'] = '%'
            elif pid == PID_COOLANT_TEMP:
                result['name'] = 'Coolant Temperature'
                result['value'] = data_bytes[0] - 40
                result['unit'] = '°C'
            elif pid == PID_SHORT_FUEL_TRIM_1:
                result['name'] = 'Short Term Fuel Trim - Bank 1'
                result['value'] = (data_bytes[0] - 128) * 100.0 / 128.0
                result['unit'] = '%'
            elif pid == PID_LONG_FUEL_TRIM_1:
                result['name'] = 'Long Term Fuel Trim - Bank 1'
                result['value'] = (data_bytes[0] - 128) * 100.0 / 128.0
                result['unit'] = '%'
            elif pid == PID_SHORT_FUEL_TRIM_2:
                result['name'] = 'Short Term Fuel Trim - Bank 2'
                result['value'] = (data_bytes[0] - 128) * 100.0 / 128.0
                result['unit'] = '%'
            elif pid == PID_LONG_FUEL_TRIM_2:
                result['name'] = 'Long Term Fuel Trim - Bank 2'
                result['value'] = (data_bytes[0] - 128) * 100.0 / 128.0
                result['unit'] = '%'
            elif pid == PID_FUEL_PRESSURE:
                result['name'] = 'Fuel Pressure'
                result['value'] = data_bytes[0] * 3
                result['unit'] = 'kPa'
            elif pid == PID_INTAKE_PRESSURE:
                result['name'] = 'Intake Manifold Pressure'
                result['value'] = data_bytes[0]
                result['unit'] = 'kPa'
            elif pid == PID_RPM:
                result['name'] = 'Engine RPM'
                result['value'] = ((data_bytes[0] * 256) + data_bytes[1]) / 4.0
                result['unit'] = 'rpm'
            elif pid == PID_SPEED:
                result['name'] = 'Vehicle Speed'
                result['value'] = data_bytes[0]
                result['unit'] = 'km/h'
            elif pid == PID_TIMING_ADVANCE:
                result['name'] = 'Timing Advance'
                result['value'] = (data_bytes[0] - 128) / 2.0
                result['unit'] = '°'
            elif pid == PID_INTAKE_TEMP:
                result['name'] = 'Intake Air Temperature'
                result['value'] = data_bytes[0] - 40
                result['unit'] = '°C'
            elif pid == PID_MAF:
                result['name'] = 'Mass Air Flow'
                result['value'] = ((data_bytes[0] * 256) + data_bytes[1]) / 100.0
                result['unit'] = 'g/s'
            elif pid == PID_THROTTLE:
                result['name'] = 'Throttle Position'
                result['value'] = data_bytes[0] * 100.0 / 255.0
                result['unit'] = '%'
            elif pid == PID_RUN_TIME:
                result['name'] = 'Run Time Since Engine Start'
                result['value'] = (data_bytes[0] * 256) + data_bytes[1]
                result['unit'] = 's'
            else:
                result['name'] = f'PID {pid}'
                result['value'] = ' '.join([format(b, '02X') for b in data_bytes])
                result['unit'] = 'hex'
            
            return result
        
        except Exception as e:
            logger.error(f"Error decoding PID {pid}: {e}")
            # Return a default result instead of None
            return {
                'name': f'PID {pid}',
                'value': 0,
                'unit': 'error'
            }
    
    def read_all_sensor_data(self) -> Dict[str, Dict[str, Any]]:
        """
        Read all supported sensor data from the vehicle.
        
        Returns:
            Dictionary of PID to sensor data mappings
        """
        if not self.connected:
            logger.error("Not connected to vehicle")
            return {}
        
        sensor_data = {}
        
        # Determine which PIDs to try
        # This is a subset of common PIDs that provide useful information
        pids_to_try = [
            PID_ENGINE_LOAD,
            PID_COOLANT_TEMP,
            PID_SHORT_FUEL_TRIM_1,
            PID_LONG_FUEL_TRIM_1,
            PID_SHORT_FUEL_TRIM_2,
            PID_LONG_FUEL_TRIM_2,
            PID_FUEL_PRESSURE,
            PID_INTAKE_PRESSURE,
            PID_RPM,
            PID_SPEED,
            PID_TIMING_ADVANCE,
            PID_INTAKE_TEMP,
            PID_MAF,
            PID_THROTTLE,
            PID_RUN_TIME
        ]
        
        # Read each PID
        for pid in pids_to_try:
            if self.is_pid_supported(pid):
                result = self.read_pid(pid)
                if result:
                    sensor_data[pid] = result
                    logger.info(f"Read {result['name']}: {result['value']} {result['unit']}")
            else:
                logger.debug(f"PID {pid} not supported")
        
        return sensor_data
    
    def get_freeze_frame_data(self, dtc_code: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Get freeze frame data for a specific DTC or the first stored freeze frame.
        
        Args:
            dtc_code: Optional DTC code to get freeze frame for
            
        Returns:
            Dictionary of freeze frame data
        """
        if not self.connected:
            logger.error("Not connected to vehicle")
            return {}
        
        freeze_frame_data = {}
        
        try:
            # If specific DTC provided, need to format the command
            # Most vehicles don't support this feature but we'll try
            command = "02"
            if dtc_code:
                # Extract numeric portion of DTC
                if len(dtc_code) == 5 and dtc_code[0] in "PCBU":
                    dtc_type = {"P": "0", "C": "1", "B": "2", "U": "3"}[dtc_code[0]]
                    numeric = dtc_code[1:]
                    hex_dtc = f"{dtc_type}{numeric}"
                    command = f"02{PID_FREEZE_DTC}{hex_dtc}"
            
            # Send the command - in most cases, vehicles will ignore the DTC
            # and return freeze frame data for the first DTC that set the CEL
            response = self._send_command(command)
            
            if not response or "NO DATA" in response or "ERROR" in response:
                logger.warning("No freeze frame data available")
                return {}
            
            # Decode freeze frame data
            # Similar to regular PIDs but with mode 02 instead of 01
            # This would be more complex in a full implementation
            # For now, just return the raw response
            freeze_frame_data['raw'] = response
            
            return freeze_frame_data
            
        except Exception as e:
            logger.error(f"Error getting freeze frame data: {e}")
            return {}