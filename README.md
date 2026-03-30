# Card Emulator (emulator.py)

A small utility to emulate HID/RFID cards using a Flipper Zero (via serial), read back with a HelloID reader (serial), and verify readings from an RFIDEAs HID keyboard device. Logs results to an Excel file (`emulator_log.xlsx`).

**Features**
- Emulate sequential 24-bit card IDs and send them to Flipper Zero.
- Read back card UIDs from a serial HelloID reader and convert them using the convert24 algorithm.
- Capture HID keyboard-like input from RFIDEAs devices via `pynput` and compare with converted UID.
- Append results to an Excel workbook with simple column auto-sizing.

**Requirements**
- Python 3.8+
- Windows (script tested on Windows)
- System libraries/drivers for HID access (may need libusb for some hid implementations)
- Python packages listed in `requirements.txt`  

Install dependencies:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**Files**
- Main script: [emulator.py](emulator.py)
- Output log: `emulator_log.xlsx`

**Quick Usage**

1. Connect devices:
   - Flipper Zero (USB serial)
   - HelloID reader (serial)
   - RFIDEAs HID device (USB keyboard-like)
2. Run the script:

```powershell
python emulator.py
```

The script will attempt to auto-detect Flipper and reader ports by VID/PID. If detection fails you'll be prompted to enter the COM port manually.

**Configuration**
At the top of `emulator.py` you can change constants to control behavior:
- `NUM_CARDS` — how many cards to emulate
- `START_VALUE`, `STEP_SIZE` — generation of 24-bit values
- `KEY_TYPE`, `UID_LENGTH` — emulation format
- Timing and retry constants: `EMULATION_DELAY`, `MAX_EMULATION_RETRIES`, `TOTAL_READER_TIMEOUT`, etc.
- `EXCEL_FILE` — log filename

**Stopping the script**
- Use Ctrl+C to interrupt. The script tries to gracefully stop the keyboard listener and close serial ports.

**Troubleshooting**
- "Flipper not found" / "Reader not found": verify USB connections and correct drivers; note VID/PID printed by the script and use manual COM input if necessary.
- HID input not captured: some HID backends require additional OS drivers (libusb). Ensure the `hid` library you installed supports your device.
- Permission errors writing `emulator_log.xlsx`: ensure the file isn't open in Excel or locked by another process.

**Notes**
- Excel writes are protected by a `FileLock` (`emulator_log.xlsx.lock`) to avoid concurrent writes.
- The script expects the HelloID reader to output hex UID strings; short/truncated reads are ignored.
