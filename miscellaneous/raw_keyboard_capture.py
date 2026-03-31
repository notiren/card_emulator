#!/usr/bin/env python3
# -*- mode: python3; indent-tabs-mode: nil; tab-width: 4 -*-
"""
raw_keyboard_capture.py - Capture raw keyboard input from pcProx device

This script captures raw keystrokes sent by the pcProx device and displays
the raw data for analysis.

Copyright 2024
"""

import msvcrt
import time

def capture_raw_keyboard():
    """Capture raw keyboard input and display data"""
    print("Raw Keyboard Capture for pcProx")
    print("Press keys on the pcProx device to see raw data")
    print("Press Ctrl+C to stop")
    print("-" * 40)

    buffer = ""
    last_key_time = time.time()

    try:
        while True:
            if msvcrt.kbhit():
                # Get the raw key
                key = msvcrt.getch()

                # Show raw byte value
                raw_byte = key[0] if isinstance(key, bytes) else ord(key)
                print(f"Raw byte: 0x{raw_byte:02X} ('{chr(raw_byte) if 32 <= raw_byte <= 126 else '?'}')")

                # Try to decode as character
                try:
                    char = key.decode('cp1252', errors='ignore')
                    if char:
                        buffer += char
                        last_key_time = time.time()
                except:
                    pass

                # Check for complete input (timeout after 1 second of no input)
                if buffer and time.time() - last_key_time > 1.0:
                    print(f"Buffer: '{buffer}'")
                    print(f"Raw bytes: {buffer.encode('latin1').hex()}")

                    # Check if it looks like card data
                    if ':' in buffer and buffer.replace(':', '').isdigit():
                        print("Detected card data format!")
                        try:
                            facility, card = buffer.split(':')
                            facility = int(facility)
                            card = int(card)
                            print(f"Facility: {facility}, Card: {card}")
                        except:
                            pass

                    print("-" * 20)
                    buffer = ""

            time.sleep(0.01)  # Small delay

    except KeyboardInterrupt:
        print("\nStopping...")

def main():
    capture_raw_keyboard()

if __name__ == "__main__":
    main()