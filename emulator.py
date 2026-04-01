import serial
import time
from openpyxl import load_workbook, Workbook
from filelock import FileLock
import threading
import queue
from pynput import keyboard as pynput_keyboard
import hid
from serial.tools import list_ports
import argparse
import re

# --- CARD CONFIGURATION ---
NUM_CARDS = 1000000
START_VALUE = 0x040C06
STEP_SIZE   = 0x000002
KEY_TYPE = "EM4100/32"
UID_LENGTH = 10

# --- TIMING CONFIGURATION ---
EMULATION_DELAY = 0.5
QUEUE_CLEAR_DELAY = 0.2
POST_READ_DELAY = 0.2
STOP_EMULATION_DELAY = 0.2
DELAY_BETWEEN_CARDS = 0.1

MAX_EMULATION_RETRIES = 5
TOTAL_READER_TIMEOUT = 6.0
POLL_INTERVAL = 0.5
RFIDEAS_TIMEOUT = 1.0
RESET_INTERVAL = 30

# -- EXCEL CONFIGURATION ---
EXCEL_FILE = "emulator_log.xlsx"
LOCK_FILE = EXCEL_FILE + ".lock"

print("Starting emulator...")

# --- PORT DETECTION FUNCTIONS ---
def find_port_by_vid_pid(vid, pid):
    """Find serial port by VID and PID"""
    ports = list_ports.comports()
    for port in ports:
        if port.vid is not None and port.pid is not None:
            if port.vid == vid and port.pid == pid:
                return port.device
    return None

def check_flipper_device():
    """Check and initialize Flipper device"""
    flipper_port = find_port_by_vid_pid(0x0483, 0x5740)  # STMicroelectronics Flipper Zero
    if not flipper_port:
        print("✗ Flipper not found. Available ports:")
        for port in list_ports.comports():
            print(f"  {port.device}: {port.description} (VID: {port.vid:04X}, PID: {port.pid:04X})")
        flipper_port = input("Enter Flipper port manually: ") or 'COM17'
    else:
        print(f"✓ Flipper detected on {flipper_port}")
    
    try:
        flipper = serial.Serial(flipper_port, 230400, timeout=1)
        flipper.setDTR(True)
        flipper.setRTS(True)
        time.sleep(2)
        flipper.write(b"\r\n\r\n")  # wake up Flipper CLI
        time.sleep(0.5)
        print(f"✓ Flipper initialized on {flipper_port}")
        return flipper
    except Exception as e:
        print(f"✗ Error initializing Flipper: {e}")
        exit(1)

def check_reader_device():
    """Check and initialize helloID Reader device"""
    reader_port = find_port_by_vid_pid(0x1d6b, 0x4944)  # helloID Reader device
    if not reader_port:
        print("✗ Reader not found. Available ports:")
        for port in list_ports.comports():
            print(f"  {port.device}: {port.description} (VID: {port.vid:04X}, PID: {port.pid:04X})")
        reader_port = input("Enter Reader port manually: ") or 'COM18'
    else:
        print(f"✓ Reader detected on {reader_port}")
    
    try:
        reader = serial.Serial(reader_port, 9600, timeout=0)
        print(f"✓ Reader initialized on {reader_port}")
        return reader
    except Exception as e:
        print(f"✗ Error initializing Reader: {e}")
        exit(1)

def check_rfideas_device():
    """Check and initialize RFIDEAs HID device (vendor_id 0x0c27)"""
    try:
        devices = hid.enumerate()
        rfideas_devices = [d for d in devices if d.get('vendor_id') == 0x0c27]
        if rfideas_devices:
            device = rfideas_devices[0]
            print(f"✓ RFIDEAs device found: {device.get('product_string', 'Unknown')}")
            return device
        else:
            print("✗ RFIDEAs device not found. Please connect it.")
            return None
    except Exception as e:
        print(f"✗ Error checking for RFIDEAs device: {e}")
        return None

# --- SERIAL SETUP ---
flipper = check_flipper_device()
reader = check_reader_device()
rfideas = check_rfideas_device()

# --- QUEUES ---
reader_queue = queue.Queue()
keyboard_queue = queue.Queue()
stop_event = threading.Event()
keyboard_listener = None  

# --- HELPER FUNCTIONS ---
def generate_24bit_numbers(start=START_VALUE, step=STEP_SIZE):
    """Generate 24-bit numbers sequentially with the given step size"""
    if step <= 0:
        raise ValueError("Step must be a positive integer")
    max_value = 0xFFFFFF
    for value in range(start, max_value + 1, step):
        yield value

def convert24(value: int) -> int:
    """Convert 24-bit value using the convert24 algorithm"""
    value &= 0xFFFFFF
    high = (value >> 16) & 0xFF
    folded_high = (high & 0x80) | (high & 0x07)
    out = (value & 0x00FFFF) | (folded_high << 16)
    
    if (folded_high & 0x07) >= 4:
        out = (out - 0x01042E) & 0xFFFFFF

    return out

def int24_to_hex6(value: int) -> str:
    """Convert 24-bit integer to 6-character uppercase hex string"""
    value &= 0xFFFFFF
    
    return f"{value:06X}"
    
def clean_reader_line(line):
    """Extract UID from reader line. Keep only the last part after ':'"""
    if ':' in line:
        return line.split(':')[-1].strip()
    return line.strip()

def is_valid_uid(uid):
    if not uid or uid == "NOT DETECTED":
        return False
    if uid == "0000000000000000":
        return False
    if len(uid) < 8:
        return False
    try:
        int(uid, 16)
        return True
    except ValueError:
        return False

def log_to_excel(nr, emulated, helloid, converted, rfideas, compare_result):
    """Log a single row to Excel with all columns."""
    with FileLock(LOCK_FILE):
        try:
            wb = load_workbook(EXCEL_FILE)
            ws = wb.active
        except Exception:
            wb = Workbook()
            ws = wb.active
            ws.append(["Nr", "Emulated UID", "HelloID", "Converted HelloID", "RFIDEAs", "Compare"])
        ws.append([nr, emulated, helloid, converted, rfideas, compare_result])
        
        # Auto-adjust column widths
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if cell.value:
                        max_length = max(max_length, len(str(cell.value)))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
        try:
            wb.save(EXCEL_FILE)
        except Exception as e:
            print(f"Error saving Excel file: {e}")

def send_flipper_command(key_data):
    key_type = KEY_TYPE
    cmd = f"rfid emulate {key_type} {key_data}"
    flipper.write((cmd + "\r\n").encode())
    time.sleep(EMULATION_DELAY)

def stop_flipper_emulation():
    """Send Ctrl+C to stop emulation"""
    flipper.write(b"\x03")  # ASCII: Ctrl+C
    time.sleep(STOP_EMULATION_DELAY)

def reset_flipper():
    """Reset the Flipper device by closing and reopening the connection"""
    global flipper
    try:
        flipper.close()
        time.sleep(1)
        # Re-detect Flipper port
        flipper_port = find_port_by_vid_pid(0x0483, 0x5740)  # STMicroelectronics Flipper Zero
        if not flipper_port:
            print("✗ Flipper not found after reset attempt")
            return
        flipper = serial.Serial(flipper_port, 230400, timeout=1)
        flipper.setDTR(True)
        flipper.setRTS(True)
        time.sleep(2)
        flipper.write(b"\r\n\r\n")  # Wake up Flipper CLI
        time.sleep(0.5)
        reader.reset_input_buffer()  # Clear reader input buffer during reset
        print(f"✓ Flipper reset")
    except Exception as e:
        print(f"✗ Error resetting Flipper: {e}")

# --- READER THREAD ---
def reader_thread():
    buffer = ""
    try:
        while True:
            bytes_waiting = reader.in_waiting
            if bytes_waiting > 0:
                data = reader.read(bytes_waiting).decode(errors='ignore')
                buffer += data
                if "\n" in buffer:
                    lines = buffer.split("\n")
                    for line in lines[:-1]:
                        line = line.strip()
                        if line:
                            uid = clean_reader_line(line)
                            
                            # Validate before queuing
                            if len(uid) >= 6:  # Minimum UID length
                                try:
                                    int(uid, 16)  # Check if valid hex
                                    reader_queue.put(uid)
                                except ValueError:
                                    pass  # Skip invalid hex
                            # else skip short/truncated reads like "000"
                    buffer = lines[-1]
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nExiting reader thread...")
        reader.close()

# --- KEYBOARD LISTENER THREAD (RFIDEAs HID) ---
def keyboard_listener_thread():
    """Listen for keyboard input from RFIDEAs device"""
    global keyboard_listener
    buffer = ""
    
    def on_press(key):
        nonlocal buffer

        if stop_event.is_set():
            return False
        
        try:
            if hasattr(key, 'char') and key.char is not None:
                char = key.char
                if char.isprintable():
                    buffer += char
            
            # Enter key signals end of scan
            if key == pynput_keyboard.Key.enter and buffer:
                keyboard_queue.put(buffer)
                buffer = ""
        except Exception:
            pass
    
    keyboard_listener = pynput_keyboard.Listener(on_press=on_press)
    keyboard_listener.start()
    keyboard_listener.join()

# --- GENERATE EMULATED CARDS ---
emulated_cards = []
for num in generate_24bit_numbers(step=STEP_SIZE):
    euid = f"00000012D6{num:06X}"
    emulated_cards.append(euid)
    if len(emulated_cards) >= NUM_CARDS:
        break

# --- MAIN LOOP ---
def load_keys_from_excel(path):
    """Load keys from the first column of an Excel file.
    Extracts the last 6 hex characters from each cell and
    formats them as emulated EUIDs using the existing prefix.
    """
    keys = []
    try:
        wb = load_workbook(path, data_only=True)
        ws = wb.active
        for row in ws.iter_rows(min_row=1, max_col=1, values_only=True):
            cell = row[0]
            if not cell:
                continue
            s = str(cell).strip()
            matches = re.findall(r"[0-9A-Fa-f]+", s)
            if not matches:
                continue
            token = matches[-1]
            if len(token) < 6:
                continue
            last6 = token[-6:]
            try:
                num = int(last6, 16)
                euid = f"00000012D6{num:06X}"
                keys.append(euid)
            except ValueError:
                continue
    except Exception as e:
        print(f"Error loading key list from Excel: {e}")
    return keys


def main(key_list_path=None):
    # Determine starting Nr from Excel
    try:
        wb = load_workbook(EXCEL_FILE)
        ws = wb.active
        last_row = ws.max_row
        if last_row > 1:  # Header is row 1
            last_nr = ws.cell(row=last_row, column=1).value
            start_nr = last_nr + 1 if isinstance(last_nr, int) else 1
        else:
            start_nr = 1
    except FileNotFoundError:
        start_nr = 1
    except Exception:
        start_nr = 1

    # Build emulated cards list (from Excel list if provided)
    emulated_cards = []
    if key_list_path:
        loaded = load_keys_from_excel(key_list_path)
        if loaded:
            emulated_cards = loaded
            print(f"✓ Loaded {len(emulated_cards)} keys from: {key_list_path}")
        else:
            print(f"✗ No valid keys found in {key_list_path}; falling back to generated cards.")

    # If no emulated cards yet, generate them as before
    if not emulated_cards:
        for num in generate_24bit_numbers(step=STEP_SIZE):
            euid = f"00000012D6{num:06X}"
            emulated_cards.append(euid)
            if len(emulated_cards) >= NUM_CARDS:
                break

    # Print headers
    print("\n")
    print(f"{'Nr':<7}{'Emulated UID':<20}{'HelloID':<20}{'Converted HelloID':<20}{'RFIDEAs':<20}{'Compare'}")
    print("-"*110)

    for i, euid in enumerate(emulated_cards, start_nr):
        # Reset Flipper at intervals to prevent device timeout
        if (i - start_nr) > 0 and (i - start_nr) % RESET_INTERVAL == 0:
            reset_flipper()
            time.sleep(1)
        
        # Clear old queue items BEFORE emulation
        while not reader_queue.empty():
            reader_queue.get()
        while not keyboard_queue.empty():
            keyboard_queue.get()
        time.sleep(QUEUE_CLEAR_DELAY)  # Wait for queues to fully clear

        reader_read = "NOT DETECTED"

        for attempt in range(MAX_EMULATION_RETRIES):
            while not reader_queue.empty():
                reader_queue.get()

            send_flipper_command(euid[-10:])
            
            start_time = time.time()

            while time.time() - start_time < TOTAL_READER_TIMEOUT:
                try:
                    candidate = reader_queue.get(timeout=POLL_INTERVAL)

                    if is_valid_uid(candidate):
                        reader_read = candidate
                        print(f"Reader OK in {time.time() - start_time:.2f}s (attempt {attempt+1})")
                        break
                    else:
                        print(f"Invalid read ignored: {candidate}")

                except queue.Empty:
                    continue
            
            stop_flipper_emulation()
            
            if reader_read != "NOT DETECTED":
                break

            print(f"Retrying... (attempt {attempt+1})")

        # Wait for keyboard/RFIDEAs input
        rfideas_read = ""
        try:
            rfideas_read = keyboard_queue.get(timeout=RFIDEAS_TIMEOUT)
        except queue.Empty:
            rfideas_read = "NOT DETECTED"

        # Convert the received UID from reader (last 6 hex chars = 3 bytes)
        converted_uid = "NOT DETECTED"
        if reader_read != "NOT DETECTED":
            try:
                # Extract last 6 characters, convert them, keep first 10 chars of device ID
                int_value = int(reader_read[-6:], 16)
                converted_int = convert24(int_value)
                hex_value = int24_to_hex6(converted_int)
                # reader_read is like "00000012D6000072" (16 chars: 10 prefix + 6 uid)
                # Replace only the last 6 chars with converted value
                converted_uid = reader_read[:10] + hex_value
            except (ValueError, IndexError):
                converted_uid = "ERROR"

        # Format all UIDs with 000000 prefix for display
        emulated_display = euid
        helloid_display = reader_read if reader_read != "NOT DETECTED" else "NOT DETECTED"
        converted_display = converted_uid if converted_uid not in ["NOT DETECTED", "ERROR"] else converted_uid
        rfideas_display = "000000" + rfideas_read if rfideas_read != "NOT DETECTED" else "NOT DETECTED"
        
        # Compare Converted HelloID with RFIDEAs
        if converted_display in ["NOT DETECTED", "ERROR"] or rfideas_display == "NOT DETECTED":
            compare_result = "ERROR"
        elif converted_display == rfideas_display:
            compare_result = "Matched"
        else:
            compare_result = "Not Matched"

        # Log and print: Nr | Emulated UID | HelloID | Converted HelloID | RFIDEAs | Compare
        print(f"{i:<7}{emulated_display:<20}{helloid_display:<20}{converted_display:<20}{rfideas_display:<20}{compare_result}")
        log_to_excel(i, emulated_display, helloid_display, converted_display, rfideas_display, compare_result)

        time.sleep(DELAY_BETWEEN_CARDS)

# --- MAIN ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Card emulator: optionally load keys from Excel list")
    parser.add_argument('-list', '--list', dest='excel_list_path', help='Path to Excel file containing keys')
    args = parser.parse_args()
    try:
        threading.Thread(target=reader_thread, daemon=True).start()
        threading.Thread(target=keyboard_listener_thread, daemon=True).start()
        time.sleep(1)
        main(args.excel_list_path)
        print("\nAll cards emulated and logged to:", EXCEL_FILE)
    
        # Send Ctrl+C to interrupt the keyboard listener
        try:
            controller = pynput_keyboard.Controller()
            controller.press(pynput_keyboard.Key.ctrl)
            controller.press('c')
            controller.release('c')
            controller.release(pynput_keyboard.Key.ctrl)
            time.sleep(0.1)
        except:
            pass
        
        # Signal listener to stop and try to stop it gracefully
        stop_event.set()
        if keyboard_listener:
            keyboard_listener.stop()
        time.sleep(0.1)
        exit(0)
        
    except KeyboardInterrupt:
        print("\nInterrupted by user (Ctrl+C)")   