#!/usr/bin/env python3
# -*- mode: python3; indent-tabs-mode: nil; tab-width: 4 -*-
"""
dll_test.py - Test program for reading a card and changing LEDs on pcProx using pcProxAPI.dll

Copyright 2024 - Based on original pcprox usbtest.py
"""

import time
import argparse
from pcprox_dll import PcProxDLL


def main(debug=False):
    try:
        pcprox = PcProxDLL()

        if debug:
            print("DLL loaded successfully")

        # Connect to device - try USB first, then COM
        connect_result = pcprox.connect_usb()
        if connect_result != 0:
            if debug:
                print(f"USB connection failed (error: {pcprox.get_last_error()}), trying COM...")
            connect_result = pcprox.connect_com()
            if connect_result != 0:
                print(f"Failed to connect to device via USB or COM, error: {pcprox.get_last_error()}")
                return

        if debug:
            print("Connected to device")

        # Test ping
        ping_result = pcprox.ping()
        if debug:
            print(f"Ping result: {ping_result}")

        # Show device info
        print(f"Device: {pcprox.get_device_name()}")
        print(f"Part: {pcprox.get_part_number()}")
        print(f"Firmware: {pcprox.get_firmware_version()}")
        print(f"Serial: {pcprox.get_serial_number()}")

        # Check keyboard send status
        if debug:
            halted = pcprox.get_keyboard_send_halted()
            print(f"Keyboard send initially halted: {halted}")

        # Halt keyboard sending for direct control
        pcprox.set_keyboard_send_halted(True)

        if debug:
            halted = pcprox.get_keyboard_send_halted()
            print(f"Keyboard send after setting halted: {halted}")

        # Turn off red LED, turn on green LED
        pcprox.set_led_states(False, True)

        # Wait half a second
        time.sleep(0.5)

        # Turn off green LED
        pcprox.set_led_states(False, False)

        found_card = False
        print('Waiting for a card... (red light should pulse)')

        for x in range(40):
            # Flash the red LED as "1-on 1-off 1-on 3-off"
            red_state = (x % 6) in (0, 2)
            pcprox.set_led_states(red_state, False)

            # Check for card
            card_id = pcprox.get_active_card_id()
            if debug and x % 5 == 0:
                print(f"Checking for card... (iteration {x})")
            
            if card_id is not None:
                # We got a card!
                pcprox.set_led_states(False, False)
                found_card = True

                # Print the tag ID
                print(f'Tag data: {" ".join([f"{b:02x}" for b in card_id])}')
                print(f'Bit length: {len(card_id) * 8}')
                break

            # No card in the field, sleep
            time.sleep(0.2)

        # We were successful, do a little light show
        if found_card:
            print('We got a card! (blinking lights)')
            for x in range(20):
                green_state = (x & 0x01) == 0
                red_state = (x & 0x02) > 0
                pcprox.set_led_states(red_state, green_state)
                time.sleep(0.1)
        else:
            print('No card found.')

        # Re-enable sending keystrokes
        pcprox.set_keyboard_send_halted(False)

        # Place the LEDs back under pcProx control
        pcprox.set_led_states(False, False)

        # Disconnect - try USB disconnect first, then COM
        try:
            pcprox.disconnect_usb()
        except AttributeError:
            try:
                pcprox.disconnect_com()
            except AttributeError:
                if debug:
                    print("No disconnect function available")

        if debug:
            print("Disconnected from device")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Test program for pcprox using pcProxAPI.dll which reads a card in the field')

    parser.add_argument('-d', '--debug', action='store_true',
                        help='Enable debug output')

    options = parser.parse_args()
    main(options.debug)