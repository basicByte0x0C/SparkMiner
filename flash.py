#!/usr/bin/env python3
"""
SparkMiner - Universal Build & Flash Tool
==========================================

All-in-one interactive tool supporting multiple ESP32 boards.
Adding new boards is simple - just add an entry to BOARDS dict.

Usage:
    python flash.py                    # Interactive mode
    python flash.py --board cyd-2usb   # Select board directly
    python flash.py --list             # List available boards
    python flash.py --build            # Build only
    python flash.py --flash COM5       # Flash to specific port
    python flash.py --all              # Build, flash, and monitor
"""

import os
import sys
import subprocess
import argparse
import time
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple

# ============================================================
# Board Definitions
# ============================================================
# To add a new board:
#   1. Add entry to BOARDS dict with unique key
#   2. Add corresponding environment in platformio.ini
#   3. That's it!
# ============================================================

@dataclass
class BoardConfig:
    """Configuration for a supported board"""
    name: str                    # Display name
    env: str                     # PlatformIO environment name
    chip: str                    # ESP chip type (esp32, esp32s3, esp32c3, etc.)
    description: str             # Short description
    flash_baud: int = 921600     # Flash baud rate
    monitor_baud: int = 115200   # Monitor baud rate
    flash_mode: str = "dio"      # Flash mode (dio, qio, etc.)
    flash_freq: str = "80m"      # Flash frequency
    needs_boot_mode: bool = True # Requires manual bootloader mode
    port_changes_on_reset: bool = False  # Port changes after reset (ESP32-S3)
    boot_button: str = "BOOT"    # Boot button name
    reset_button: str = "RESET"  # Reset button name


# Board registry - add new boards here!
BOARDS: Dict[str, BoardConfig] = {
    # ============================================================
    # CYD - Cheap Yellow Display Variants
    # ============================================================
    "cyd-1usb": BoardConfig(
        name="CYD 1-USB (ILI9341)",
        env="esp32-2432s028",
        chip="esp32",
        description="ESP32-2432S028 with single USB port, ILI9341 display",
        flash_freq="40m",
        needs_boot_mode=False,  # ESP32 usually auto-resets
    ),
    "cyd-1usb-st7789": BoardConfig(
        name="CYD 1-USB (ST7789)",
        env="esp32-2432s028-st7789",
        chip="esp32",
        description="ESP32-2432S028 variant with ST7789 display driver",
        flash_freq="40m",
        needs_boot_mode=False,
    ),
    "cyd-2usb": BoardConfig(
        name="CYD 2-USB",
        env="esp32-2432s028-2usb",
        chip="esp32",
        description="ESP32-2432S028 with dual USB ports (flash via USB-to-Serial port)",
        flash_freq="40m",
        needs_boot_mode=False,
    ),

    # ============================================================
    # ESP32-S3 Display Boards
    # ============================================================
    "freenove-s3": BoardConfig(
        name="Freenove ESP32-S3 Display",
        env="esp32-s3-2432s028",
        chip="esp32s3",
        description="Freenove FNK0104 with 2.8\" ILI9341, SD_MMC, USB-C",
        needs_boot_mode=True,
        port_changes_on_reset=True,  # S3 often changes COM port after reset
    ),

    # ============================================================
    # Headless Boards (no display)
    # ============================================================
    "esp32-headless": BoardConfig(
        name="ESP32 Headless",
        env="esp32-headless",
        chip="esp32",
        description="Generic ESP32 without display (serial output only)",
        flash_freq="40m",
        needs_boot_mode=False,
    ),
    "esp32-s3-devkit": BoardConfig(
        name="ESP32-S3 DevKit",
        env="esp32-s3-devkit",
        chip="esp32s3",
        description="ESP32-S3 DevKitC-1 headless with PSRAM",
        needs_boot_mode=True,
        port_changes_on_reset=True,
    ),
    "esp32-s3-mini": BoardConfig(
        name="ESP32-S3 Mini",
        env="esp32-s3-mini",
        chip="esp32s3",
        description="Wemos/Lolin S3 Mini with RGB LED",
        needs_boot_mode=True,
        port_changes_on_reset=True,
    ),
}

# Board groups for menu organization
BOARD_GROUPS = {
    "CYD (Cheap Yellow Display)": ["cyd-1usb", "cyd-2usb", "cyd-1usb-st7789"],
    "ESP32-S3 Display": ["freenove-s3"],
    "Headless (No Display)": ["esp32-headless", "esp32-s3-devkit", "esp32-s3-mini"],
}


# ============================================================
# Terminal Colors
# ============================================================
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


def color(text: str, c: str) -> str:
    """Wrap text in color codes"""
    return f"{c}{text}{Colors.ENDC}"


# ============================================================
# Utility Functions
# ============================================================

def get_script_dir() -> Path:
    """Get the directory where this script is located"""
    return Path(__file__).parent.resolve()


def get_python_path() -> str:
    """Get the path to Python executable (prefer venv)"""
    script_dir = get_script_dir()
    venv_python = script_dir / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    # Try Unix-style venv
    venv_python_unix = script_dir / ".venv" / "bin" / "python"
    if venv_python_unix.exists():
        return str(venv_python_unix)
    return sys.executable


def get_pio_cmd() -> List[str]:
    """Get the PlatformIO command as a list"""
    return [get_python_path(), "-m", "platformio"]


def check_pio_installed() -> bool:
    """Check if PlatformIO is installed"""
    try:
        result = subprocess.run(
            get_pio_cmd() + ["--version"],
            capture_output=True, text=True
        )
        return result.returncode == 0
    except Exception:
        return False


def run_command(cmd: List[str], description: str = None, capture: bool = False):
    """Run a command and handle output"""
    if description:
        print(f"\n{color('[INFO]', Colors.BLUE)} {description}")

    try:
        if capture:
            return subprocess.run(cmd, capture_output=True, text=True, cwd=get_script_dir())
        else:
            return subprocess.run(cmd, cwd=get_script_dir())
    except FileNotFoundError:
        print(f"{color('[ERROR]', Colors.RED)} Command not found: {cmd[0]}")
        return None
    except KeyboardInterrupt:
        print(f"\n{color('[CANCELLED]', Colors.YELLOW)} Operation cancelled by user")
        return None


def wait_for_user(prompt: str = "Press ENTER when ready..."):
    """Wait for user to press Enter"""
    input(f"\n{color('[?]', Colors.CYAN)} {prompt}")


# ============================================================
# Banner & Instructions
# ============================================================

def print_banner(board: BoardConfig = None):
    """Print the SparkMiner banner"""
    if board:
        board_line = f"|    Board: {board.name:<47}|"
        env_line = f"|    Environment: {board.env:<41}|"
    else:
        board_line = "|    Select a board to get started                      |"
        env_line = "|                                                         |"

    banner = f"""
+=========================================================+
|                                                         |
|    SparkMiner - Universal Flash Tool                    |
|                                                         |
{board_line}
{env_line}
|                                                         |
+=========================================================+
"""
    print(color(banner, Colors.CYAN))


def print_bootloader_instructions(board: BoardConfig):
    """Print instructions for entering bootloader/download mode"""
    print(f"\n{color('=' * 60, Colors.YELLOW)}")
    print(f"{color(f' {board.chip.upper()} DOWNLOAD MODE INSTRUCTIONS', Colors.BOLD)}")
    print(f"{color('=' * 60, Colors.YELLOW)}")

    if board.chip == "esp32s3":
        print(f"""
  To put the {board.chip.upper()} into download/bootloader mode:

    1. HOLD the {board.boot_button} button (do not release)
    2. While holding {board.boot_button}, press and release the {board.reset_button} button
    3. Release the {board.boot_button} button

  The board is now in download mode and ready to flash.

  NOTE: The display will be blank/off in download mode - this is normal!
""")
    else:
        print(f"""
  The ESP32 usually auto-resets into download mode.

  If flashing fails, try:

    1. HOLD the {board.boot_button} button while plugging in USB
    2. Or: Hold {board.boot_button}, press {board.reset_button}, release {board.boot_button}

  Some boards may require manual boot mode entry.
""")
    print(f"{color('=' * 60, Colors.YELLOW)}")


def print_reset_instructions(board: BoardConfig):
    """Print instructions for resetting after flash"""
    print(f"\n{color('=' * 60, Colors.GREEN)}")
    print(f"{color(' FLASH COMPLETE - RESET REQUIRED', Colors.BOLD)}")
    print(f"{color('=' * 60, Colors.GREEN)}")
    print(f"""
  The firmware has been flashed successfully!

  To start the new firmware:

    >>> Press the {board.reset_button} button on the board <<<

  The device should restart and SparkMiner will start.
""")
    print(f"{color('=' * 60, Colors.GREEN)}")


# ============================================================
# Serial Port Handling
# ============================================================

def list_serial_ports() -> List[Tuple[str, str]]:
    """List available serial ports"""
    if not check_pio_installed():
        return []

    result = run_command(get_pio_cmd() + ["device", "list", "--serial"], capture=True)
    if not result or result.returncode != 0:
        return []

    ports = []
    current_port = None
    current_desc = ""

    for line in result.stdout.split('\n'):
        line = line.strip()
        if line.startswith("COM") or line.startswith("/dev/"):
            if current_port:
                ports.append((current_port, current_desc))
            current_port = line
            current_desc = ""
        elif current_port and "Description:" in line:
            current_desc = line.replace("Description:", "").strip()

    if current_port:
        ports.append((current_port, current_desc))

    return ports


def is_usb_serial_port(port: str, desc: str) -> bool:
    """Check if a port is likely a USB serial port (not Bluetooth)"""
    desc_upper = desc.upper()
    if "BLUETOOTH" in desc_upper:
        return False
    if any(x in desc_upper for x in ["USB", "CP210", "CH340", "JTAG", "ESP", "FTDI", "SILICON LABS"]):
        return True
    if "SERIAL" in desc_upper and "BLUETOOTH" not in desc_upper:
        return True
    return False


def filter_usb_ports(ports: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
    """Filter port list to only USB serial ports"""
    return [(p, d) for p, d in ports if is_usb_serial_port(p, d)]


def select_port(board: BoardConfig, for_flashing: bool = False) -> Optional[str]:
    """Interactive port selection"""
    print(f"\n{color('[INFO]', Colors.BLUE)} Scanning for serial ports...")
    ports = list_serial_ports()

    if not ports:
        print(f"{color('[WARNING]', Colors.YELLOW)} No serial ports detected!")

        if for_flashing and board.needs_boot_mode:
            print(f"\n{color('[TIP]', Colors.CYAN)} The device might not be in download mode yet.")
            print_bootloader_instructions(board)
            wait_for_user("Put board in download mode, then press ENTER to scan again...")
            ports = list_serial_ports()

        if not ports:
            print("\nTroubleshooting:")
            print("  1. Connect the device via USB")
            print("  2. Try a different USB cable (data cable, not charge-only)")
            print("  3. Install CP2102/CH340 drivers if needed")
            print("  4. Try a different USB port")

            manual = input(f"\n{color('[?]', Colors.CYAN)} Enter port manually (or press Enter to cancel): ").strip()
            return manual if manual else None

    # Filter to USB ports for display
    usb_ports = filter_usb_ports(ports)
    display_ports = usb_ports if usb_ports else ports

    print(f"\n{color('Available Ports:', Colors.GREEN)}")
    print("-" * 60)

    for i, (port, desc) in enumerate(display_ports, 1):
        if is_usb_serial_port(port, desc):
            print(f"  {color(f'[{i}]', Colors.CYAN)} {color(port, Colors.GREEN)} - {desc}")
        else:
            print(f"  [{i}] {port} - {desc}")

    print("-" * 60)

    while True:
        try:
            choice = input(f"\n{color('[?]', Colors.CYAN)} Select port (1-{len(display_ports)}) or enter port name: ").strip()

            if not choice:
                return None

            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(display_ports):
                    return display_ports[idx][0]
                print(f"{color('[ERROR]', Colors.RED)} Invalid selection!")
            else:
                # Assume direct port name
                return choice.upper() if choice.upper().startswith("COM") else choice

        except (ValueError, IndexError):
            print(f"{color('[ERROR]', Colors.RED)} Invalid input!")


def find_new_port(board: BoardConfig, old_port: str) -> Optional[str]:
    """Handle COM port change after reset (common on ESP32-S3)"""
    if not board.port_changes_on_reset:
        return old_port

    print(f"\n{color('[INFO]', Colors.BLUE)} Checking if port {old_port} is still available...")
    print(f"{color('[INFO]', Colors.BLUE)} Waiting for device to enumerate...")
    time.sleep(3)

    ports = list_serial_ports()
    usb_ports = filter_usb_ports(ports)
    usb_port_names = [p[0] for p in usb_ports]

    if old_port in usb_port_names:
        print(f"{color('[OK]', Colors.GREEN)} Port {old_port} is available")
        return old_port

    print(f"{color('[WARNING]', Colors.YELLOW)} Port {old_port} is no longer available!")
    print(f"{color('[INFO]', Colors.CYAN)} {board.chip.upper()} often changes COM ports after reset.")

    if not usb_ports:
        print(f"{color('[TIP]', Colors.YELLOW)} No USB serial ports detected. Device may still be resetting.")
        wait_for_user(f"Press {board.reset_button} on the board, wait 3 seconds, then press ENTER...")
        time.sleep(2)
        ports = list_serial_ports()
        usb_ports = filter_usb_ports(ports)

    if not usb_ports:
        print(f"{color('[ERROR]', Colors.RED)} No USB serial ports found!")
        return None

    if len(usb_ports) == 1:
        new_port = usb_ports[0][0]
        print(f"{color('[INFO]', Colors.GREEN)} Found device on {new_port}")
        return new_port

    # Multiple ports - let user choose
    print(f"\n{color('Available USB Serial Ports:', Colors.GREEN)}")
    print("-" * 60)
    for i, (p, desc) in enumerate(usb_ports, 1):
        print(f"  {color(f'[{i}]', Colors.CYAN)} {color(p, Colors.GREEN)} - {desc}")
    print("-" * 60)

    while True:
        choice = input(f"\n{color('[?]', Colors.CYAN)} Select the new port (1-{len(usb_ports)}): ").strip()
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(usb_ports):
                return usb_ports[idx][0]
        print(f"{color('[ERROR]', Colors.RED)} Invalid selection!")


# ============================================================
# Board Selection
# ============================================================

def select_board() -> Optional[BoardConfig]:
    """Interactive board selection menu"""
    print(f"\n{color('Select Your Board:', Colors.GREEN)}")
    print("=" * 60)

    board_list = []
    idx = 1

    for group_name, board_keys in BOARD_GROUPS.items():
        print(f"\n  {color(group_name, Colors.CYAN)}")
        print(f"  {'-' * 40}")

        for key in board_keys:
            if key in BOARDS:
                board = BOARDS[key]
                board_list.append((key, board))
                print(f"    {color(f'[{idx}]', Colors.CYAN)} {board.name}")
                print(f"        {color(board.description, Colors.DIM)}")
                idx += 1

    print("\n" + "=" * 60)

    while True:
        choice = input(f"\n{color('[?]', Colors.CYAN)} Select board (1-{len(board_list)}) or 'q' to quit: ").strip()

        if choice.lower() == 'q':
            return None

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(board_list):
                key, board = board_list[idx]
                print(f"\n{color('[OK]', Colors.GREEN)} Selected: {board.name}")
                return board

        print(f"{color('[ERROR]', Colors.RED)} Invalid selection!")


def get_board_by_key(key: str) -> Optional[BoardConfig]:
    """Get board config by key (case-insensitive, partial match)"""
    key_lower = key.lower()

    # Exact match
    if key_lower in BOARDS:
        return BOARDS[key_lower]

    # Partial match
    for board_key, board in BOARDS.items():
        if key_lower in board_key or key_lower in board.env.lower():
            return board

    return None


# ============================================================
# Build, Flash, Monitor
# ============================================================

def check_firmware_exists(board: BoardConfig) -> Dict:
    """Check if firmware files exist for a board"""
    script_dir = get_script_dir()
    build_dir = script_dir / ".pio" / "build" / board.env

    factory_bin = None
    firmware_bin = build_dir / "firmware.bin"

    # Check for factory bin in firmware folder
    firmware_dirs = list((script_dir / "firmware").glob("*")) if (script_dir / "firmware").exists() else []
    for fw_dir in sorted(firmware_dirs, reverse=True):
        factory = fw_dir / f"{board.env}_factory.bin"
        if factory.exists():
            factory_bin = factory
            break

    return {
        "build_firmware": firmware_bin if firmware_bin.exists() else None,
        "factory_bin": factory_bin,
        "build_dir": build_dir
    }


def build_firmware(board: BoardConfig) -> bool:
    """Build the firmware for a board"""
    if not check_pio_installed():
        print(f"{color('[ERROR]', Colors.RED)} PlatformIO not found!")
        return False

    print(f"\n{color('=' * 60, Colors.CYAN)}")
    print(f"{color(' Building SparkMiner', Colors.BOLD)}")
    print(f"{color('=' * 60, Colors.CYAN)}")
    print(f"  Board: {board.name}")
    print(f"  Environment: {board.env}")
    print(f"  Chip: {board.chip}")
    print(f"{color('=' * 60, Colors.CYAN)}\n")

    result = run_command(get_pio_cmd() + ["run", "-e", board.env])

    if result and result.returncode == 0:
        print(f"\n{color('[SUCCESS]', Colors.GREEN)} Build completed successfully!")

        fw = check_firmware_exists(board)
        if fw["factory_bin"]:
            size = fw["factory_bin"].stat().st_size
            print(f"  Factory: {fw['factory_bin'].name} ({size:,} bytes)")
        return True
    else:
        print(f"\n{color('[ERROR]', Colors.RED)} Build failed!")
        return False


def flash_firmware(board: BoardConfig, port: str, interactive: bool = True) -> bool:
    """Flash firmware to the device"""
    if not port:
        print(f"{color('[ERROR]', Colors.RED)} No port specified!")
        return False

    fw = check_firmware_exists(board)
    firmware_file = fw["factory_bin"] or fw["build_firmware"]

    if not firmware_file:
        print(f"{color('[ERROR]', Colors.RED)} No firmware found! Run build first.")
        return False

    print(f"\n{color('=' * 60, Colors.CYAN)}")
    print(f"{color(' Flashing SparkMiner', Colors.BOLD)}")
    print(f"{color('=' * 60, Colors.CYAN)}")
    print(f"  Board: {board.name}")
    print(f"  Port: {port}")
    print(f"  Firmware: {firmware_file.name}")
    print(f"  Size: {firmware_file.stat().st_size:,} bytes")
    print(f"  Baud: {board.flash_baud}")
    print(f"{color('=' * 60, Colors.CYAN)}")

    if interactive and board.needs_boot_mode:
        print_bootloader_instructions(board)
        wait_for_user("Put the board in DOWNLOAD MODE, then press ENTER to flash...")

    print(f"\n{color('[FLASH]', Colors.YELLOW)} Flashing firmware...")

    # Factory bin goes at 0x0, regular firmware at 0x10000
    flash_addr = "0x0" if "factory" in str(firmware_file) else "0x10000"

    cmd = [
        get_python_path(), "-m", "esptool",
        "--chip", board.chip,
        "--port", port,
        "--baud", str(board.flash_baud),
        "--before", "default_reset",
        "--after", "hard_reset",
        "write_flash",
        "-z",
        "--flash-mode", board.flash_mode,
        "--flash-freq", board.flash_freq,
        "--flash-size", "detect",
        flash_addr, str(firmware_file)
    ]

    result = run_command(cmd)

    if result and result.returncode == 0:
        print(f"\n{color('[SUCCESS]', Colors.GREEN)} Flash completed successfully!")
        return True
    else:
        print(f"\n{color('[ERROR]', Colors.RED)} Flash failed!")
        print(f"\n{color('Troubleshooting:', Colors.YELLOW)}")
        print(f"  1. Make sure you entered download mode correctly")
        print(f"     - Hold {board.boot_button}, press {board.reset_button}, release {board.boot_button}")
        print("  2. Try a different USB port or cable")
        print("  3. Check if another program is using the port")
        print("  4. Ensure drivers are installed (CP2102/CH340)")
        return False


def open_monitor(board: BoardConfig, port: str, after_flash: bool = False):
    """Open serial monitor"""
    if not port:
        print(f"{color('[ERROR]', Colors.RED)} No port specified!")
        return

    if not check_pio_installed():
        print(f"{color('[ERROR]', Colors.RED)} PlatformIO not found!")
        return

    if after_flash:
        print_reset_instructions(board)
        wait_for_user(f"Press {board.reset_button} on the board, then press ENTER to start monitor...")

        # Handle port change on ESP32-S3
        port = find_new_port(board, port)
        if not port:
            print(f"{color('[ERROR]', Colors.RED)} Could not find device. Try running monitor separately.")
            return

    max_retries = 2
    for attempt in range(max_retries + 1):
        print(f"\n{color('=' * 60, Colors.CYAN)}")
        print(f"{color(' Serial Monitor', Colors.BOLD)}")
        print(f"{color('=' * 60, Colors.CYAN)}")
        print(f"  Port: {port}")
        print(f"  Baud: {board.monitor_baud}")
        print(f"  Exit: Ctrl+C")
        print(f"{color('=' * 60, Colors.CYAN)}\n")

        result = run_command(get_pio_cmd() + ["device", "monitor", "-b", str(board.monitor_baud), "-p", port])

        if result and result.returncode != 0 and attempt < max_retries:
            print(f"\n{color('[WARNING]', Colors.YELLOW)} Monitor failed - port may have changed.")
            new_port = find_new_port(board, port)
            if new_port and new_port != port:
                port = new_port
                continue
            elif not new_port:
                print(f"{color('[ERROR]', Colors.RED)} No device found.")
                return
        break


# ============================================================
# Interactive Menu
# ============================================================

def interactive_menu(board: BoardConfig):
    """Show interactive menu for a selected board"""
    while True:
        print(f"\n{color('Main Menu:', Colors.GREEN)} [{board.name}]")
        print("-" * 50)
        print(f"  {color('[1]', Colors.CYAN)} Build firmware")
        print(f"  {color('[2]', Colors.CYAN)} Flash firmware")
        print(f"  {color('[3]', Colors.CYAN)} Serial monitor")
        print(f"  {color('[4]', Colors.CYAN)} Build + Flash + Monitor (Full cycle)")
        print(f"  {color('[5]', Colors.CYAN)} Check firmware status")
        print(f"  {color('[6]', Colors.CYAN)} Clean build")
        print(f"  {color('[7]', Colors.CYAN)} Change board")
        print(f"  {color('[0]', Colors.CYAN)} Exit")
        print("-" * 50)

        choice = input(f"\n{color('[?]', Colors.CYAN)} Select option: ").strip()

        if choice == "1":
            build_firmware(board)

        elif choice == "2":
            port = select_port(board, for_flashing=True)
            if port:
                flash_firmware(board, port, interactive=True)

        elif choice == "3":
            port = select_port(board, for_flashing=False)
            if port:
                open_monitor(board, port, after_flash=False)

        elif choice == "4":
            if build_firmware(board):
                port = select_port(board, for_flashing=True)
                if port and flash_firmware(board, port, interactive=True):
                    open_monitor(board, port, after_flash=True)

        elif choice == "5":
            fw = check_firmware_exists(board)
            print(f"\n{color('Firmware Status:', Colors.GREEN)} [{board.env}]")
            print("-" * 50)
            if fw["factory_bin"]:
                size = fw["factory_bin"].stat().st_size
                print(f"  {color('[OK]', Colors.GREEN)} Factory: {fw['factory_bin'].name}")
                print(f"           Size: {size:,} bytes")
            else:
                print(f"  {color('[X]', Colors.RED)} Factory: Not found")

            if fw["build_firmware"]:
                size = fw["build_firmware"].stat().st_size
                print(f"  {color('[OK]', Colors.GREEN)} Build: {fw['build_firmware'].name}")
                print(f"         Size: {size:,} bytes")
            else:
                print(f"  {color('[X]', Colors.RED)} Build: Not found (run build first)")
            print("-" * 50)

        elif choice == "6":
            if check_pio_installed():
                run_command(get_pio_cmd() + ["run", "-e", board.env, "-t", "clean"], "Cleaning build...")
                print(f"{color('[SUCCESS]', Colors.GREEN)} Build cleaned!")

        elif choice == "7":
            return None  # Signal to select new board

        elif choice == "0":
            print(f"\n{color('Goodbye! Happy mining!', Colors.CYAN)}\n")
            sys.exit(0)

        else:
            print(f"{color('[ERROR]', Colors.RED)} Invalid option!")


def list_boards():
    """Print list of available boards"""
    print(f"\n{color('Available Boards:', Colors.GREEN)}")
    print("=" * 70)

    for group_name, board_keys in BOARD_GROUPS.items():
        print(f"\n  {color(group_name, Colors.CYAN)}")

        for key in board_keys:
            if key in BOARDS:
                board = BOARDS[key]
                print(f"    {color(key, Colors.GREEN):20} - {board.name}")
                print(f"    {' ' * 20}   {color(board.description, Colors.DIM)}")

    print("\n" + "=" * 70)
    print(f"\nUsage: python flash.py --board {color('<board-key>', Colors.CYAN)}")
    print(f"   Ex: python flash.py --board cyd-2usb")


# ============================================================
# Main Entry Point
# ============================================================

def main():
    """Main entry point"""
    # Enable ANSI colors on Windows
    if sys.platform == "win32":
        os.system("")

    parser = argparse.ArgumentParser(
        description="SparkMiner Universal Build & Flash Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python flash.py                      # Interactive mode
  python flash.py --list               # List available boards
  python flash.py --board cyd-2usb     # Select CYD 2-USB board
  python flash.py --board freenove-s3 --all  # Build, flash, monitor
  python flash.py --build              # Build only (interactive board select)
  python flash.py --flash COM5         # Flash to COM5
        """
    )

    parser.add_argument("--list", "-l", action="store_true", help="List available boards")
    parser.add_argument("--board", "-b", metavar="KEY", help="Select board by key (see --list)")
    parser.add_argument("--build", action="store_true", help="Build firmware")
    parser.add_argument("--flash", "-f", nargs="?", const="auto", metavar="PORT", help="Flash firmware")
    parser.add_argument("--monitor", "-m", nargs="?", const="auto", metavar="PORT", help="Open serial monitor")
    parser.add_argument("--all", "-a", nargs="?", const="auto", metavar="PORT", help="Build, flash, and monitor")
    parser.add_argument("--clean", "-c", action="store_true", help="Clean build directory")
    parser.add_argument("--no-interactive", "-y", action="store_true", help="Skip interactive prompts")

    args = parser.parse_args()

    # List boards
    if args.list:
        list_boards()
        return

    # Select or get board
    board = None
    if args.board:
        board = get_board_by_key(args.board)
        if not board:
            print(f"{color('[ERROR]', Colors.RED)} Unknown board: {args.board}")
            print(f"\nRun '{color('python flash.py --list', Colors.CYAN)}' to see available boards.")
            sys.exit(1)

    # Check PlatformIO
    print_banner(board)

    if not check_pio_installed():
        print(f"{color('[ERROR]', Colors.RED)} PlatformIO not found!")
        print("\nInstall with: pip install platformio")
        print("Or activate venv: .venv\\Scripts\\activate")
        sys.exit(1)

    # Select board if not specified
    if not board:
        board = select_board()
        if not board:
            print(f"\n{color('No board selected. Goodbye!', Colors.CYAN)}\n")
            return
        print_banner(board)

    interactive = not args.no_interactive

    # Handle CLI commands
    if args.clean:
        run_command(get_pio_cmd() + ["run", "-e", board.env, "-t", "clean"], "Cleaning build...")
        return

    if args.build or args.all:
        if not build_firmware(board):
            if args.all:
                sys.exit(1)
            return

    if args.flash or args.all:
        port_arg = args.flash if args.flash and args.flash != "auto" else (
            args.all if args.all and args.all != "auto" else None)
        port = port_arg or select_port(board, for_flashing=True)
        if port:
            if not flash_firmware(board, port, interactive=interactive):
                sys.exit(1)
            if args.all or args.monitor:
                open_monitor(board, port, after_flash=interactive)
        return

    if args.monitor:
        port = args.monitor if args.monitor != "auto" else select_port(board, for_flashing=False)
        if port:
            open_monitor(board, port, after_flash=False)
        return

    # Interactive mode
    while True:
        result = interactive_menu(board)
        if result is None:
            # User wants to change board
            board = select_board()
            if not board:
                print(f"\n{color('Goodbye!', Colors.CYAN)}\n")
                return
            print_banner(board)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{color('Cancelled. Goodbye!', Colors.CYAN)}\n")
        sys.exit(0)
