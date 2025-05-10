"""
OBD2-to-USB Connector Module
This module handles the direct USB communication with vehicles through an OBD2-to-USB cable.
"""

import logging
import time
import serial
import serial.tools.list_ports
import threading
import queue
from typing import Dict, List, Tuple, Optional, Union

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class OBD2Connector:
    """
    Class to handle communication with a vehicle via OBD2-to-USB connection.
    This class handles the direct serial communication, protocol negotiation,
    command sending and response parsing.
    """
    
    # Common ELM327 AT commands
    AT_COMMANDS = {
        'reset': 'ATZ',                   # Reset adapter
        'echo_off': 'ATE0',               # Turn echo off
        'headers_off': 'ATH0',            # Turn headers off
        'linefeeds_off': 'ATL0',          # Turn linefeeds off
        'spaces_off': 'ATS0',             # Turn spaces off
        'adaptative_timing': 'ATAT1',     # Set adaptive timing
        'protocol_auto': 'ATSP0',         # Set protocol to auto
        'can_protocol': 'ATSP6',          # Set protocol to CAN (ISO 15765-4, 11-bit ID, 500 kbaud)
        'voltage': 'ATRV',                # Read voltage
        'identify': 'ATI',                # Identify the ELM327 device
        'describe_protocol': 'ATDP',      # Describe the current protocol
    }
    
    # Common OBD2 PIDs (Parameter IDs) for mode 01 (current data)
    OBD2_PIDS = {
        'supported_pids_1_20': '0100',    # PIDs supported [01-20]
        'status': '0101',                 # Status since DTCs cleared
        'engine_load': '0104',            # Calculated engine load
        'coolant_temp': '0105',           # Engine coolant temperature
        'fuel_pressure': '010A',          # Fuel pressure
        'intake_pressure': '010B',        # Intake manifold pressure
        'rpm': '010C',                    # Engine RPM
        'speed': '010D',                  # Vehicle speed
        'timing_advance': '010E',         # Timing advance
        'intake_temp': '010F',            # Intake air temperature
        'maf': '0110',                    # MAF air flow rate
        'throttle_pos': '0111',           # Throttle position
        'o2_sensors': '0113',             # O2 sensors present
        'fuel_level': '012F',             # Fuel level input
        'distance_mil': '0121',           # Distance traveled with MIL on
    }
    
    # OBD2 modes
    OBD2_MODES = {
        'current_data': '01',             # Show current data
        'freeze_frame': '02',             # Show freeze frame data
        'dtc': '03',                      # Show stored DTCs
        'clear_dtc': '04',                # Clear DTCs and stored values
        'o2_test_results': '05',          # O2 sensor test results
        'test_results': '06',             # Other test results
        'pending_dtc': '07',              # Show pending DTCs
        'control': '08',                  # Control operation
        'vehicle_info': '09',             # Request vehicle information
        'permanent_dtc': '0A'             # Permanent DTCs
    }
    
    def __init__(self, port=None, baudrate=38400, timeout=10):
        """
        Initialize the OBD2 connector.
        
        Args:
            port: Serial port to use. If None, will attempt to auto-detect.
            baudrate: Baud rate for serial communication.
            timeout: Serial communication timeout in seconds.
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.connection = None
        self.is_connected = False
        self.protocol = None
        self.command_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.worker_thread = None
        self.running = False

    def find_obd2_port(self) -> Optional[str]:
        """
        Auto-detect the OBD2 USB adapter port.
        Returns the port name if found, None otherwise.
        """
        logger.info("Searching for OBD2 USB adapters...")
        ports = list(serial.tools.list_ports.comports())
        
        # Common identifiers for ELM327 and similar OBD adapters
        obd_identifiers = [
            "ELM327", "OBD", "STN", "CH340", "CP2102", "FTDI"
        ]
        
        for port in ports:
            port_info = f"{port.device} - {port.description}"
            logger.debug(f"Found port: {port_info}")
            
            # Check if any identifier matches the port description
            if any(identifier.lower() in port.description.lower() for identifier in obd_identifiers):
                logger.info(f"Likely OBD2 adapter found at {port.device}: {port.description}")
                return port.device
        
        logger.warning("No OBD2 adapter found. Available ports:")
        for port in ports:
            logger.warning(f"  {port.device}: {port.description}")
        
        return None

    def connect(self) -> bool:
        """
        Connect to the OBD2 adapter and initialize it.
        Returns True if successful, False otherwise.
        """
        try:
            # If no port specified, try to find one
            if not self.port:
                self.port = self.find_obd2_port()
                if not self.port:
                    logger.error("No OBD2 port found")
                    return False
            
            logger.info(f"Connecting to OBD2 adapter on {self.port}")
            
            # Connect to the serial port
            self.connection = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                bytesize=8,
                parity='N',
                stopbits=1
            )
            
            # Initialize the adapter
            if not self._initialize_adapter():
                logger.error("Failed to initialize OBD2 adapter")
                self.disconnect()
                return False
            
            # Start worker thread for command processing
            self.running = True
            self.worker_thread = threading.Thread(target=self._command_worker)
            self.worker_thread.daemon = True
            self.worker_thread.start()
            
            self.is_connected = True
            logger.info("Successfully connected to OBD2 adapter")
            return True
            
        except serial.SerialException as e:
            logger.error(f"Serial connection error: {e}")
            return False
        except Exception as e:
            logger.error(f"Error connecting to OBD2 adapter: {e}")
            return False

    def disconnect(self):
        """Disconnect from the OBD2 adapter."""
        logger.info("Disconnecting from OBD2 adapter")
        self.running = False
        
        if self.worker_thread and self.worker_thread.is_alive():
            self.command_queue.put(None)  # Signal to stop the worker thread
            self.worker_thread.join(2.0)  # Wait for the thread to finish
        
        if self.connection and self.connection.is_open:
            self.connection.close()
        
        self.is_connected = False
        self.protocol = None
        logger.info("Disconnected from OBD2 adapter")

    def _initialize_adapter(self) -> bool:
        """
        Initialize the OBD2 adapter with required settings.
        Returns True if successful, False otherwise.
        """
        logger.info("Initializing OBD2 adapter...")
        
        # Reset the adapter
        if not self._send_command(self.AT_COMMANDS['reset'], 1.0):
            return False
        
        # Basic setup - turn off echo, headers, linefeeds, spaces
        commands = [
            self.AT_COMMANDS['echo_off'],
            self.AT_COMMANDS['headers_off'],
            self.AT_COMMANDS['linefeeds_off'],
            self.AT_COMMANDS['spaces_off'],
            self.AT_COMMANDS['adaptative_timing']
        ]
        
        for cmd in commands:
            if not self._send_command(cmd):
                return False
        
        # Check adapter identification
        response = self._send_command(self.AT_COMMANDS['identify'])
        if not response:
            return False
        
        logger.info(f"Adapter identification: {response}")
        
        # Try to auto-detect protocol
        if not self._send_command(self.AT_COMMANDS['protocol_auto']):
            return False
        
        # Check for vehicle connection by requesting supported PIDs
        response = self._send_command(self.OBD2_PIDS['supported_pids_1_20'])
        if not response or "NO DATA" in response:
            logger.warning("No vehicle data received, trying CAN protocol specifically")
            # Try to set CAN protocol and test again
            if not self._send_command(self.AT_COMMANDS['can_protocol']):
                return False
            
            response = self._send_command(self.OBD2_PIDS['supported_pids_1_20'])
            if not response or "NO DATA" in response:
                logger.error("No vehicle connection detected")
                return False
        
        # Get current protocol
        response = self._send_command(self.AT_COMMANDS['describe_protocol'])
        if response:
            self.protocol = response.strip()
            logger.info(f"Connected using protocol: {self.protocol}")
        
        logger.info("OBD2 adapter initialized successfully")
        return True

    def _send_command(self, command: str, delay: float = 0.1) -> Optional[str]:
        """
        Send a command to the OBD2 adapter and return the response.
        
        Args:
            command: The command to send
            delay: Time to wait after sending the command
            
        Returns:
            The response string or None if there was an error
        """
        if not self.connection or not self.connection.is_open:
            logger.error("Cannot send command: Not connected")
            return None
        
        try:
            # Clear any pending data
            self.connection.flushInput()
            
            # Send the command
            full_command = command + "\r"
            logger.debug(f"Sending command: {command}")
            self.connection.write(full_command.encode())
            
            # Wait a bit for processing
            time.sleep(delay)
            
            # Read the response
            response = ""
            while self.connection.in_waiting:
                char = self.connection.read().decode()
                response += char
            
            # Clean up the response
            clean_response = self._clean_response(response, command)
            logger.debug(f"Response: {clean_response}")
            
            return clean_response
            
        except Exception as e:
            logger.error(f"Error sending command {command}: {e}")
            return None

    def _clean_response(self, response: str, command: str) -> str:
        """
        Clean up the response string from the adapter.
        
        Args:
            response: The raw response from the adapter
            command: The command that was sent
            
        Returns:
            Cleaned response string
        """
        if not response:
            return ""
        
        # Split by carriage return/newline
        lines = response.replace('\r', '\n').replace('\n\n', '\n').split('\n')
        
        # Remove empty lines and echoed command
        lines = [line.strip() for line in lines if line.strip()]
        lines = [line for line in lines if line != command]
        
        # Join remaining lines
        return '\n'.join(lines)

    def _command_worker(self):
        """
        Worker thread to process commands in the queue.
        This allows for asynchronous command execution.
        """
        logger.debug("Command worker thread started")
        
        while self.running:
            try:
                # Get the next command from the queue
                item = self.command_queue.get(timeout=1.0)
                
                # Check for stop signal
                if item is None:
                    break
                
                command, callback = item
                
                # Send the command and get response
                response = self._send_command(command)
                
                # Put the response in the queue
                self.response_queue.put((command, response))
                
                # Call the callback if provided
                if callback and callable(callback):
                    callback(command, response)
                
                # Mark the task as done
                self.command_queue.task_done()
                
            except queue.Empty:
                # No commands in the queue, just continue
                continue
            except Exception as e:
                logger.error(f"Error in command worker: {e}")
        
        logger.debug("Command worker thread stopped")

    def queue_command(self, command: str, callback=None):
        """
        Queue a command to be sent to the OBD2 adapter.
        
        Args:
            command: The command to send
            callback: Optional callback function to call with the response
        """
        if not self.is_connected:
            logger.error("Cannot queue command: Not connected")
            return
        
        self.command_queue.put((command, callback))

    def get_vehicle_info(self) -> Dict:
        """
        Get basic information about the connected vehicle.
        
        Returns:
            Dictionary containing vehicle information
        """
        info = {
            'vin': None,
            'ecu_name': None,
            'protocol': self.protocol,
            'supported_pids': [],
        }
        
        # Get VIN (Vehicle Identification Number)
        vin_cmd = self.OBD2_MODES['vehicle_info'] + '02'
        response = self._send_command(vin_cmd)
        if response and '490201' in response.replace(' ', ''):
            # Extract the VIN - it's typically the hex representation of ASCII characters
            hex_vin = response.replace('490201', '').replace(' ', '')
            try:
                # Convert hex to ASCII
                vin = ''.join([chr(int(hex_vin[i:i+2], 16)) for i in range(0, len(hex_vin), 2)])
                # Remove non-printable characters
                vin = ''.join(c for c in vin if 32 <= ord(c) < 127)
                info['vin'] = vin
            except Exception as e:
                logger.error(f"Error decoding VIN: {e}")
        
        # Get ECU name
        ecu_cmd = self.OBD2_MODES['vehicle_info'] + '0A'
        response = self._send_command(ecu_cmd)
        if response and '49020A' in response.replace(' ', ''):
            # Extract the ECU name - similar to VIN, it's hex representation of ASCII
            hex_ecu = response.replace('49020A', '').replace(' ', '')
            try:
                # Convert hex to ASCII
                ecu_name = ''.join([chr(int(hex_ecu[i:i+2], 16)) for i in range(0, len(hex_ecu), 2)])
                # Remove non-printable characters
                ecu_name = ''.join(c for c in ecu_name if 32 <= ord(c) < 127)
                info['ecu_name'] = ecu_name
            except Exception as e:
                logger.error(f"Error decoding ECU name: {e}")
        
        # Get supported PIDs
        response = self._send_command(self.OBD2_PIDS['supported_pids_1_20'])
        if response and not "NO DATA" in response:
            # Parse supported PIDs
            try:
                # Extract the actual data part
                data_bytes = response.split(' ')
                if len(data_bytes) >= 6:  # At least 6 bytes (mode|pid|4 data bytes)
                    # Skip first 2 bytes (response code and PID)
                    pid_bytes = ''.join(data_bytes[2:6]).replace(' ', '')
                    
                    # Convert to binary representation
                    binary = bin(int(pid_bytes, 16))[2:].zfill(32)
                    
                    # Each bit represents a PID
                    for i in range(32):
                        if binary[i] == '1':
                            pid_num = i + 1
                            pid_hex = f"01{pid_num:02X}"
                            info['supported_pids'].append(pid_hex)
            except Exception as e:
                logger.error(f"Error parsing supported PIDs: {e}")
        
        return info

    def read_dtcs(self) -> List[Dict]:
        """
        Read Diagnostic Trouble Codes (DTCs) from the vehicle.
        
        Returns:
            List of dictionaries with DTC codes and descriptions
        """
        dtcs = []
        
        # Read stored DTCs
        response = self._send_command(self.OBD2_MODES['dtc'])
        if response and not "NO DATA" in response:
            dtcs.extend(self._parse_dtc_response(response, 'stored'))
        
        # Read pending DTCs
        response = self._send_command(self.OBD2_MODES['pending_dtc'])
        if response and not "NO DATA" in response:
            dtcs.extend(self._parse_dtc_response(response, 'pending'))
        
        # Read permanent DTCs
        response = self._send_command(self.OBD2_MODES['permanent_dtc'])
        if response and not "NO DATA" in response:
            dtcs.extend(self._parse_dtc_response(response, 'permanent'))
        
        return dtcs

    def _parse_dtc_response(self, response: str, dtc_type: str) -> List[Dict]:
        """
        Parse the DTC response from the adapter.
        
        Args:
            response: The response string from the adapter
            dtc_type: Type of DTC (stored, pending, permanent)
            
        Returns:
            List of DTCs with their descriptions
        """
        dtcs = []
        
        try:
            # Split the response by spaces to get the bytes
            bytes_list = response.replace('\r', ' ').replace('\n', ' ').split(' ')
            bytes_list = [b for b in bytes_list if b]  # Remove empty strings
            
            # The first byte is the mode + 40, second is the number of DTCs
            if len(bytes_list) < 2:
                return dtcs
            
            # Process DTCs - they're in pairs of bytes after the first two bytes
            i = 2
            while i + 1 < len(bytes_list):
                first_byte = bytes_list[i]
                second_byte = bytes_list[i+1]
                
                if len(first_byte) == 2 and len(second_byte) == 2:
                    # Construct the DTC
                    dtc_char = self._get_dtc_letter(int(first_byte[0], 16))
                    dtc_code = f"{dtc_char}{first_byte[1]}{second_byte}"
                    
                    dtcs.append({
                        'code': dtc_code,
                        'type': dtc_type,
                        'description': self._get_dtc_description(dtc_code)
                    })
                
                i += 2
        
        except Exception as e:
            logger.error(f"Error parsing DTC response: {e}")
        
        return dtcs

    def _get_dtc_letter(self, code: int) -> str:
        """Get the letter prefix for a DTC based on its code."""
        if code == 0:
            return "P0"  # Powertrain
        elif code == 1:
            return "P1"  # Manufacturer specific powertrain
        elif code == 2:
            return "P2"  # Powertrain
        elif code == 3:
            return "P3"  # Powertrain
        elif code == 4:
            return "C0"  # Chassis
        elif code == 5:
            return "C1"  # Manufacturer specific chassis
        elif code == 6:
            return "C2"  # Chassis
        elif code == 7:
            return "C3"  # Chassis
        elif code == 8:
            return "B0"  # Body
        elif code == 9:
            return "B1"  # Manufacturer specific body
        elif code == 10:
            return "B2"  # Body
        elif code == 11:
            return "B3"  # Body
        elif code == 12:
            return "U0"  # Network
        elif code == 13:
            return "U1"  # Manufacturer specific network
        elif code == 14:
            return "U2"  # Network
        elif code == 15:
            return "U3"  # Network
        else:
            return "X"   # Unknown

    def _get_dtc_description(self, code: str) -> str:
        """
        Get the description for a DTC code.
        This is a stub - in a real implementation, this would look up the description
        in a DTC database.
        """
        # In a full implementation, this would query a database of DTCs
        # For now, we'll just return a generic description
        return f"Description for {code}"

    def clear_dtcs(self) -> bool:
        """
        Clear all Diagnostic Trouble Codes and turn off the MIL (Check Engine Light).
        
        Returns:
            True if successful, False otherwise
        """
        response = self._send_command(self.OBD2_MODES['clear_dtc'])
        return response is not None and "OK" in response

    def read_sensor_data(self, pid: str) -> Dict:
        """
        Read sensor data for a specific PID.
        
        Args:
            pid: The PID to read (e.g., '010C' for RPM)
            
        Returns:
            Dictionary with the sensor data and metadata
        """
        result = {
            'pid': pid,
            'name': self._get_pid_name(pid),
            'value': None,
            'unit': self._get_pid_unit(pid),
            'raw_response': None
        }
        
        response = self._send_command(pid)
        if not response or "NO DATA" in response:
            return result
        
        result['raw_response'] = response
        
        # Parse the response based on the PID
        try:
            result['value'] = self._parse_pid_response(pid, response)
        except Exception as e:
            logger.error(f"Error parsing response for PID {pid}: {e}")
        
        return result

    def _get_pid_name(self, pid: str) -> str:
        """Get a human-readable name for a PID."""
        # Remove mode byte if present
        if pid.startswith('01'):
            pid_num = pid[2:]
        else:
            pid_num = pid
        
        # Common PID names
        pid_names = {
            '00': 'Supported PIDs 01-20',
            '01': 'Status since DTCs cleared',
            '04': 'Engine Load',
            '05': 'Coolant Temperature',
            '0A': 'Fuel Pressure',
            '0B': 'Intake Manifold Pressure',
            '0C': 'Engine RPM',
            '0D': 'Vehicle Speed',
            '0E': 'Timing Advance',
            '0F': 'Intake Air Temperature',
            '10': 'MAF Air Flow Rate',
            '11': 'Throttle Position',
            '2F': 'Fuel Level',
            # Add more as needed
        }
        
        return pid_names.get(pid_num, f"PID {pid_num}")

    def _get_pid_unit(self, pid: str) -> str:
        """Get the unit of measurement for a PID."""
        # Remove mode byte if present
        if pid.startswith('01'):
            pid_num = pid[2:]
        else:
            pid_num = pid
        
        # Common PID units
        pid_units = {
            '04': '%',              # Engine Load
            '05': '°C',             # Coolant Temperature
            '0A': 'kPa',            # Fuel Pressure
            '0B': 'kPa',            # Intake Manifold Pressure
            '0C': 'rpm',            # Engine RPM
            '0D': 'km/h',           # Vehicle Speed
            '0E': '° before TDC',   # Timing Advance
            '0F': '°C',             # Intake Air Temperature
            '10': 'g/s',            # MAF Air Flow Rate
            '11': '%',              # Throttle Position
            '2F': '%',              # Fuel Level
            # Add more as needed
        }
        
        return pid_units.get(pid_num, "")

    def _parse_pid_response(self, pid: str, response: str) -> Union[float, int, str]:
        """
        Parse the response for a specific PID.
        
        Args:
            pid: The PID that was requested
            response: The raw response from the adapter
            
        Returns:
            The parsed value (numeric or string)
        """
        # Remove mode byte if present
        if pid.startswith('01'):
            pid_num = pid[2:]
        else:
            pid_num = pid
        
        # Split the response by spaces
        bytes_list = response.replace('\r', ' ').replace('\n', ' ').split(' ')
        bytes_list = [b for b in bytes_list if b]  # Remove empty strings
        
        # The first byte is the mode + 40, second byte is the PID
        # The actual data starts from the third byte
        if len(bytes_list) < 3:
            return None
        
        # Extract data bytes (skip response code and PID)
        data_bytes = bytes_list[2:]
        
        # Parse different PIDs
        try:
            if pid_num == '04':  # Engine Load
                a = int(data_bytes[0], 16)
                return a * 100.0 / 255.0
                
            elif pid_num == '05':  # Coolant Temperature
                a = int(data_bytes[0], 16)
                return a - 40
                
            elif pid_num == '0C':  # Engine RPM
                a = int(data_bytes[0], 16)
                b = int(data_bytes[1], 16)
                return ((a * 256) + b) / 4.0
                
            elif pid_num == '0D':  # Vehicle Speed
                a = int(data_bytes[0], 16)
                return a
                
            elif pid_num == '11':  # Throttle Position
                a = int(data_bytes[0], 16)
                return a * 100.0 / 255.0
                
            # Add more PID parsers as needed
                
            else:
                # For unknown PIDs, just join the hex values
                return ' '.join(data_bytes)
                
        except Exception as e:
            logger.error(f"Error parsing PID {pid_num}: {e}")
            return None

    def read_all_sensor_data(self) -> Dict[str, Dict]:
        """
        Read data for all supported sensors.
        
        Returns:
            Dictionary of sensor data keyed by PID
        """
        all_data = {}
        
        # First get supported PIDs
        supported_pids_response = self._send_command(self.OBD2_PIDS['supported_pids_1_20'])
        if not supported_pids_response or "NO DATA" in supported_pids_response:
            logger.warning("Could not determine supported PIDs")
            # Try some common PIDs anyway
            pids_to_try = [
                self.OBD2_PIDS['engine_load'],
                self.OBD2_PIDS['coolant_temp'],
                self.OBD2_PIDS['rpm'],
                self.OBD2_PIDS['speed'],
                self.OBD2_PIDS['throttle_pos']
            ]
        else:
            # Parse supported PIDs
            try:
                # Extract the actual data part
                data_bytes = supported_pids_response.split(' ')
                if len(data_bytes) >= 6:  # At least 6 bytes (mode|pid|4 data bytes)
                    # Skip first 2 bytes (response code and PID)
                    pid_bytes = ''.join(data_bytes[2:6]).replace(' ', '')
                    
                    # Convert to binary representation
                    binary = bin(int(pid_bytes, 16))[2:].zfill(32)
                    
                    # Each bit represents a PID
                    pids_to_try = []
                    for i in range(32):
                        if binary[i] == '1':
                            pid_num = i + 1
                            pid_hex = f"01{pid_num:02X}"
                            pids_to_try.append(pid_hex)
            except Exception as e:
                logger.error(f"Error parsing supported PIDs: {e}")
                pids_to_try = []
        
        # Read each supported PID
        for pid in pids_to_try:
            sensor_data = self.read_sensor_data(pid)
            all_data[pid] = sensor_data
        
        return all_data

    def monitor_sensor(self, pid: str, callback, interval: float = 0.5):
        """
        Continuously monitor a sensor and call the callback with new values.
        
        Args:
            pid: The PID to monitor
            callback: Function to call with each new reading
            interval: Time between readings in seconds
        
        This is a non-blocking call that starts a monitoring thread.
        """
        if not self.is_connected:
            logger.error("Cannot monitor sensor: Not connected")
            return
        
        def monitor_thread(pid, callback, interval):
            logger.info(f"Starting monitoring of PID {pid}")
            while self.running:
                try:
                    sensor_data = self.read_sensor_data(pid)
                    callback(sensor_data)
                    time.sleep(interval)
                except Exception as e:
                    logger.error(f"Error in sensor monitoring thread: {e}")
                    break
            logger.info(f"Stopped monitoring of PID {pid}")
        
        # Start the monitoring thread
        thread = threading.Thread(
            target=monitor_thread,
            args=(pid, callback, interval)
        )
        thread.daemon = True
        thread.start()
        
        return thread