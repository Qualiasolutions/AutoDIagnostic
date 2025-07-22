#!/usr/bin/env python3
"""
OBD2 Dependencies Installation Script
=====================================

This script helps install the necessary dependencies for OBD2 diagnostics 
including both USB/cable and Bluetooth wireless connections.

Run with: python install_obd2_deps.py
"""

import os
import sys
import platform
import subprocess
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_command(command, description="", check=True):
    """Run a shell command and handle errors."""
    logger.info(f"Running: {description or command}")
    try:
        result = subprocess.run(command, shell=True, check=check, 
                               capture_output=True, text=True)
        if result.stdout:
            logger.info(f"Output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error: {e}")
        if e.stderr:
            logger.error(f"Error output: {e.stderr.strip()}")
        return False

def install_python_packages():
    """Install Python packages for OBD2 support."""
    logger.info("Installing Python packages...")
    
    packages = [
        "pyserial>=3.5",
        "python-obd>=0.7.1"
    ]
    
    # Add Bluetooth packages based on OS
    system = platform.system().lower()
    if system == "linux":
        packages.extend([
            "pybluez>=0.23",
            "bleak>=0.22.0"
        ])
    elif system in ["darwin", "windows"]:
        packages.append("bleak>=0.22.0")
    
    for package in packages:
        success = run_command(f"pip install {package}", f"Installing {package}")
        if not success:
            logger.warning(f"Failed to install {package}")
    
    logger.info("Python package installation completed")

def install_linux_dependencies():
    """Install Linux system dependencies for OBD2 and Bluetooth."""
    logger.info("Installing Linux system dependencies...")
    
    # Update package list
    run_command("sudo apt update", "Updating package list")
    
    # Install system packages
    packages = [
        "bluez",           # Bluetooth stack
        "bluez-tools",     # Bluetooth utilities
        "rfcomm",          # RFCOMM support
        "libbluetooth-dev", # Bluetooth development headers
        "python3-dev",     # Python development headers
    ]
    
    package_list = " ".join(packages)
    success = run_command(f"sudo apt install -y {package_list}", 
                         "Installing system packages")
    
    if success:
        logger.info("System packages installed successfully")
        
        # Enable Bluetooth service
        run_command("sudo systemctl enable bluetooth", "Enabling Bluetooth service")
        run_command("sudo systemctl start bluetooth", "Starting Bluetooth service")
        
        # Add user to dialout group for serial port access
        username = os.getenv("USER")
        if username:
            run_command(f"sudo usermod -a -G dialout {username}", 
                       "Adding user to dialout group")
            logger.info("Please log out and log back in for group changes to take effect")
    else:
        logger.error("Failed to install some system packages")

def setup_udev_rules():
    """Set up udev rules for OBD2 device access."""
    logger.info("Setting up udev rules for OBD2 devices...")
    
    udev_rules = '''# OBD2 USB Adapters
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{idVendor}=="067b", ATTRS{idProduct}=="2303", MODE="0666", GROUP="dialout"
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", MODE="0666", GROUP="dialout"

# Generic USB-Serial converters (often used for OBD2)
SUBSYSTEM=="tty", ATTRS{interface}=="USB Serial Port", MODE="0666", GROUP="dialout"
'''
    
    try:
        with open("/tmp/99-obd2.rules", "w") as f:
            f.write(udev_rules)
        
        success = run_command("sudo cp /tmp/99-obd2.rules /etc/udev/rules.d/", 
                             "Installing udev rules")
        if success:
            run_command("sudo udevadm control --reload-rules", "Reloading udev rules")
            run_command("sudo udevadm trigger", "Triggering udev")
            logger.info("Udev rules installed successfully")
        
        # Clean up
        os.remove("/tmp/99-obd2.rules")
        
    except Exception as e:
        logger.error(f"Failed to set up udev rules: {e}")

def test_bluetooth():
    """Test Bluetooth functionality."""
    logger.info("Testing Bluetooth functionality...")
    
    # Check if Bluetooth is available
    success = run_command("bluetoothctl --version", "Checking Bluetooth version", check=False)
    if not success:
        logger.warning("Bluetooth tools not available")
        return False
    
    # Check Bluetooth service status
    success = run_command("sudo systemctl is-active bluetooth", 
                         "Checking Bluetooth service status", check=False)
    if not success:
        logger.warning("Bluetooth service is not running")
        return False
    
    logger.info("Bluetooth appears to be working correctly")
    return True

def test_usb_serial():
    """Test USB/Serial port access."""
    logger.info("Testing USB/Serial port access...")
    
    try:
        import serial.tools.list_ports
        ports = list(serial.tools.list_ports.comports())
        
        if ports:
            logger.info(f"Found {len(ports)} serial ports:")
            for port in ports:
                logger.info(f"  - {port.device}: {port.description}")
        else:
            logger.info("No serial ports found (this is normal if no devices are connected)")
        
        return True
    except ImportError:
        logger.error("pyserial not installed or not working")
        return False

def show_usage_instructions():
    """Show usage instructions after installation."""
    print("\n" + "="*60)
    print("INSTALLATION COMPLETE!")
    print("="*60)
    print()
    print("USB/Cable Connection:")
    print("- Connect your ELM327 USB adapter to the OBD2 port")
    print("- Plugin the USB cable to your computer")
    print("- The device should appear as /dev/ttyUSB0 or similar")
    print()
    print("Bluetooth Connection:")
    print("- Ensure your ELM327 Bluetooth adapter is powered on")
    print("- Pair it with your computer using Bluetooth settings")
    print("- The device will appear in the connection list as 'OBDII' or 'ELM327'")
    print()
    print("Troubleshooting:")
    print("- If you get permission errors, run: sudo usermod -a -G dialout $USER")
    print("- Then log out and log back in")
    print("- For Bluetooth issues, try: sudo systemctl restart bluetooth")
    print("- Check dmesg output when plugging in USB adapters")
    print()
    print("Test the installation by running your AutoDiagnosticPro application!")
    print("="*60)

def main():
    """Main installation function."""
    logger.info("Starting OBD2 dependencies installation...")
    
    system = platform.system().lower()
    logger.info(f"Detected OS: {system}")
    
    # Install Python packages
    install_python_packages()
    
    # OS-specific installations
    if system == "linux":
        install_linux_dependencies()
        setup_udev_rules()
        
        # Test installations
        test_bluetooth()
        test_usb_serial()
        
    elif system == "darwin":  # macOS
        logger.info("For macOS:")
        logger.info("- Install Homebrew if not already installed")
        logger.info("- Run: brew install bluez (if available)")
        logger.info("- USB adapters should work out of the box")
        
    elif system == "windows":
        logger.info("For Windows:")
        logger.info("- USB drivers are usually installed automatically")
        logger.info("- Bluetooth should work through Windows Bluetooth stack")
        logger.info("- You may need to install specific drivers for your ELM327 adapter")
    
    else:
        logger.warning(f"Unsupported OS: {system}")
    
    show_usage_instructions()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        print(__doc__)
        sys.exit(0)
    
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Installation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Installation failed: {e}")
        sys.exit(1) 