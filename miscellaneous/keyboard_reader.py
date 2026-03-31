from pynput import keyboard as pynput_keyboard
import hid

# =========================
# RFID DEVICE DETECTION
# =========================

def find_rfid_device():
    """Find and return the first RFIDeas RFID device (vendor_id 0x0c27)"""
    try:
        devices = hid.enumerate()
        rfideas_devices = [d for d in devices if d.get('vendor_id') == 0x0c27]
        if rfideas_devices:
            return rfideas_devices[0]
        return None
    except Exception as e:
        print(f"Error scanning for RFID devices: {e}")
        return None

# =========================
# KEYBOARD LISTENER
# =========================

def read_keyboard_cards():
    print("Listening for card scans... (Press Ctrl+C to exit)\n")
    
    buffer = ""
    listener = None
    
    def on_press(key):
        nonlocal buffer
        
        try:
            if hasattr(key, 'char') and key.char is not None:
                char = key.char
                if char.isprintable():
                    buffer += char
            
            # Enter key signals end of scan
            if key == pynput_keyboard.Key.enter and buffer:
                print(buffer)
                buffer = ""
                
        except Exception:
            pass
    
    try:
        with pynput_keyboard.Listener(on_press=on_press) as listener:
            listener.join()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        if listener:
            listener.stop()

# =========================
# MAIN
# =========================

def main():
    device = find_rfid_device()
    
    if not device:
        print("No RFID device found. Still listening for keyboard input...\n")
    
    try:
        read_keyboard_cards()
    except KeyboardInterrupt:
        print("\nScript interrupted by user.")


if __name__ == "__main__":
    main()