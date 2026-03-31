# pcProxAPI.dll Python Wrapper

This is a standalone Python ctypes wrapper for the RFIDeas pcProxAPI.dll, providing direct access to pcProx USB RFID readers on Windows.

## Requirements

- **Windows only** (DLL is Windows-specific)
- **Python 3.6+** (32-bit or 64-bit)
- pcProxAPI.dll or pcProxAPI_64.dll in the same directory as your script

## Installation

1. Place pcProxAPI_3.dll in your project directory
2. Use the provided `pcprox_dll.py` module

**Note:** The wrapper automatically prefers pcProxAPI_64.dll if available, which works with both 32-bit and 64-bit Python. If not found, it falls back to pcProxAPI.dll (32-bit only).

## Usage

### Basic Example

```python
from pcprox_dll import PcProxDLL

# Create instance
pcprox = PcProxDLL()

# Connect to device
result = pcprox.connect_usb()
if result == 0:
    print("Connected successfully")

    # Get device info
    print(f"Device: {pcprox.get_device_name()}")
    print(f"Firmware: {pcprox.get_firmware_version()}")

    # Read cards
    card_id = pcprox.get_active_card_id()
    if card_id:
        print(f"Card detected: {card_id.hex()}")

    # Control LEDs
    pcprox.set_led_states(True, False)  # Red on, green off

    # Disconnect
    pcprox.disconnect_usb()
else:
    print(f"Connection failed: {pcprox.get_last_error()}")
```

### Test Script

Run the included test script:

```bash
python dll_test.py -d  # With debug output
```

### Card Reading via Keyboard Emulation

Since the DLL card reading functions don't work with this device, use keyboard capture instead:

```bash
python keyboard_reader.py
```

This script captures card data sent as keystrokes (like "154336:006562") and converts it to EM4102 format for Flipper Zero.

### Raw Data Capture

For the most direct raw data capture, use:

```bash
python raw_keyboard_capture.py
```

This captures every keystroke sent by the pcProx device and displays the raw byte values, allowing you to see exactly what data is being transmitted.

## Testing Results

✅ **Successfully tested with pcProxAPI_64.dll on 64-bit Python**
- DLL loads without architecture mismatch errors
- Device connects via COM port (not USB)
- LED control works perfectly
- Connection and basic device functions work
- **Card reading via DLL API returns no data** - device works in keyboard emulation mode

### Card Reading Behavior

The pcProx device reads cards successfully but sends data as **keyboard keystrokes** rather than through the DLL API. The "154336:006562" output you saw was the device sending card data as key presses.

**Current Status:**
- ✅ Device connection and LED control
- ✅ Device responds to commands  
- ❌ DLL card reading functions return no data
- ✅ Hardware card reading (via keyboard emulation)

### Recommended Usage

For reliable card reading, use the device's **keyboard emulation mode** and capture keystrokes rather than relying on the DLL API for card data.

## API Reference

### Connection
- `connect_usb()` - Connect via USB
- `disconnect_usb()` - Disconnect USB
- `connect_com(port=0)` - Connect via COM port
- `disconnect_com()` - Disconnect COM

### Device Info
- `get_device_name()` - Get device name string
- `get_part_number()` - Get part number
- `get_firmware_version()` - Returns (major, minor, build)
- `get_serial_number()` - Get serial number
- `ping()` - Test device connectivity

### Card Reading
- `get_active_card_id()` - Get currently active card as bytes
- `get_queued_card_id(clear=True)` - Get queued card ID
- `get_queued_card_id_index(index)` - Get card by queue index

### LED Control
- `get_led_states()` - Returns (red_state, green_state)
- `set_led_states(red, green)` - Set LED states

### Configuration
- `get_keyboard_send_halted()` - Check if keyboard sending is halted
- `set_keyboard_send_halted(halted)` - Halt/resume keyboard sending
- `get_active_config()` - Get current configuration
- `get_active_device()` - Get active device index

## Error Handling

All functions return status codes. Use `get_last_error()` to get detailed error information:

```python
result = pcprox.connect_usb()
if result != 0:
    error_code = pcprox.get_last_error()
    print(f"Connection failed with error: {error_code}")
```

## Architecture Notes

- pcProxAPI_64.dll works with both 32-bit and 64-bit Python
- pcProxAPI.dll is 32-bit only
- The wrapper automatically detects and uses the best available DLL
- All functions include runtime checks for availability (different DLL versions have different APIs)

## Troubleshooting

### "DLL architecture mismatch"
- Install 32-bit Python or find 64-bit pcProxAPI.dll

### "pcProxAPI.dll not found"
- Ensure the DLL is in the same directory as your script
- Or specify the path: `PcProxDLL(r"C:\path\to\pcProxAPI.dll")`

### Connection fails
- Check USB connection
- Ensure device is powered
- Try different USB port
- Check device manager for driver issues

### No cards detected
- Ensure reader is compatible (RDR-6081AKU/APU tested)
- Check card type/frequency (125kHz HID Prox)
- Verify card is in reader field

## Files

- `pcprox_dll.py` - Main ctypes wrapper
- `dll_test.py` - Test script for LED control
- `keyboard_reader.py` - Card reader via keyboard capture
- `raw_card_reader.py` - Raw HID interface card reader
- `raw_keyboard_capture.py` - Raw keyboard data capture
- `pcProxAPI_3.dll` - official RFIDeas utility DLL (recommended)

## License

Based on RFIDeas pcProxAPI.dll and original pcprox Python module.