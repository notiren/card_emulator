#!/usr/bin/env python3
# -*- mode: python3; indent-tabs-mode: nil; tab-width: 4 -*-
"""
raw_card_reader.py - Capture raw RFID card data using HID interface

This script bypasses the DLL and communicates directly with the pcProx device
using the HID interface to capture raw card data.

Copyright 2024
"""

import hid
import time
import struct
from typing import Optional, Tuple

# pcProx USB IDs
PCPROX_VENDOR = 0x0c27
PCPROX_PRODUCT = 0x3bfa

class RawPcProxReader:
    def __init__(self, debug=False):
        self.debug = debug
        self.device = None

    def open_device(self) -> bool:
        """Open the pcProx HID device (appears as USB Keyboard)"""
        try:
            # Find RFIDeas device
            devices = hid.enumerate()
            rfideas_devices = [d for d in devices if d.get('vendor_id') == 0x0c27]

            if not rfideas_devices:
                print("No RFIDeas devices found")
                return False

            # Use the first one (should be the pcProx)
            device_info = rfideas_devices[0]

            if self.debug:
                print(f"Opening device: {device_info.get('product_string')}")

            self.device = hid.device()
            self.device.open_path(device_info['path'])

            # Set non-blocking mode
            self.device.set_nonblocking(1)

            if self.debug:
                print("Device opened successfully")
            return True

        except Exception as e:
            print(f"Failed to open device: {e}")
            return False

    def close_device(self):
        """Close the device"""
        if self.device:
            self.device.close()
            self.device = None

    def send_command(self, cmd: int) -> Optional[bytes]:
        """Send a command and read response"""
        if not self.device:
            return None

        try:
            # Send command (single byte)
            msg = bytes([cmd])
            self.device.write(b'\x00' + msg)  # HID report format

            if self.debug:
                print(f"HID TX: {msg.hex()}")

            # Read response
            time.sleep(0.01)  # Small delay
            response = self.device.read(8)

            if response:
                if self.debug:
                    print(f"HID RX: {response.hex()}")
                return bytes(response)
            else:
                return None

        except Exception as e:
            if self.debug:
                print(f"HID error: {e}")
            return None

    def get_raw_card_data(self) -> Optional[Tuple[bytes, int]]:
        """
        Read raw HID keyboard data from device.

        Returns (card_data, bit_length) or None if no card.
        """
        if not self.device:
            return None

        try:
            # Read HID report (8 bytes for keyboard)
            data = self.device.read(8)

            if data and len(data) >= 8:
                # HID keyboard report format:
                # byte 0: modifier keys
                # byte 1: reserved
                # bytes 2-7: key codes

                # Check if any keys are pressed (non-zero key codes)
                key_codes = data[2:8]
                if any(key_codes):  # At least one key pressed
                    if self.debug:
                        print(f"Raw HID data: {data.hex()}")

                    # Convert key codes to characters
                    card_text = ""
                    for key_code in key_codes:
                        if key_code != 0:
                            char = self._hid_key_to_char(key_code, data[0])  # modifier
                            if char:
                                card_text += char

                    if card_text:
                        # Parse facility:card format
                        if ':' in card_text:
                            try:
                                facility, card = card_text.split(':')
                                facility = int(facility)
                                card = int(card)

                                # Convert back to raw bytes (simulate HID Prox format)
                                # This is a simplified conversion
                                raw_bytes = struct.pack('<I', (facility << 17) | (card << 1))
                                return raw_bytes[:3], 26  # 26-bit HID Prox

                            except ValueError:
                                pass

                        # Return as ASCII bytes
                        return card_text.encode('ascii'), len(card_text) * 8

            return None

        except Exception as e:
            if self.debug:
                print(f"HID read error: {e}")
            return None

    def _hid_key_to_char(self, key_code: int, modifiers: int) -> Optional[str]:
        """Convert HID key code to character"""
        # Simplified key code mapping (numbers only for card data)
        key_map = {
            0x1E: '1', 0x1F: '2', 0x20: '3', 0x21: '4', 0x22: '5',
            0x23: '6', 0x24: '7', 0x25: '8', 0x26: '9', 0x27: '0',
            0x37: '.'  # Period (for facility:card separator)
        }

        if key_code in key_map:
            char = key_map[key_code]
            # Handle shift for colon (: is shift+.)
            if key_code == 0x37 and (modifiers & 0x02):  # Left shift
                return ':'
            return char

        return None

    def read_card_loop(self):
        """Main card reading loop"""
        print("Raw pcProx HID Card Reader")
        print("Captures raw HID keyboard data from pcProx device")
        print("Press Ctrl+C to stop")
        print("-" * 50)

        if not self.open_device():
            return

        try:
            card_buffer = ""
            last_key_time = time.time()

            while True:
                card_data = self.get_raw_card_data()

                if card_data:
                    raw_bytes, bit_length = card_data

                    # Convert bytes to string for display
                    if isinstance(raw_bytes, bytes):
                        try:
                            text_data = raw_bytes.decode('ascii', errors='ignore')
                            card_buffer += text_data
                            last_key_time = time.time()
                        except:
                            pass

                    # Check for complete card (facility:card format)
                    if ':' in card_buffer and time.time() - last_key_time > 0.5:
                        # We have a complete card
                        print(f"\nRaw card data captured: {card_buffer}")
                        print(f"Hex bytes: {card_buffer.encode('ascii').hex()}")

                        # Parse facility:card
                        if ':' in card_buffer:
                            parts = card_buffer.split(':')
                            if len(parts) == 2:
                                try:
                                    facility = int(parts[0])
                                    card_id = int(parts[1])
                                    print(f"Parsed - Facility: {facility}, Card: {card_id}")
                                    print(f"Formatted: {facility:05d}:{card_id:05d}")

                                    # Convert to EM4102-like format for Flipper
                                    # HID Prox 26-bit: facility (8-bit) + card (16-bit) + parity
                                    combined = (facility << 17) | (card_id << 1)
                                    em4102_hex = f"{combined:010X}"
                                    print(f"EM4102 equivalent: {em4102_hex}")

                                except ValueError:
                                    print("Could not parse facility:card format")

                        card_buffer = ""  # Reset for next card

                else:
                    # No data, show we're waiting
                    print(".", end="", flush=True)

                time.sleep(0.05)  # Poll every 50ms

        except KeyboardInterrupt:
            print("\nStopping...")

        finally:
            self.close_device()

def main():
    reader = RawPcProxReader(debug=False)
    reader.read_card_loop()

if __name__ == "__main__":
    main()