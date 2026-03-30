import hid

print("Scanning for HID devices...")
devices = hid.enumerate()

rfideas_devices = [d for d in devices if d.get('vendor_id') == 0x0c27]
print(f"\nFound {len(rfideas_devices)} RFIDeas devices:")

for d in rfideas_devices:
    print(f"  Product: {d.get('product_string', 'Unknown')}")
    print(f"  Manufacturer: {d.get('manufacturer_string', 'Unknown')}")
    print(f"  Vendor ID: {d['vendor_id']:04x}")
    print(f"  Product ID: {d['product_id']:04x}")
    print(f"  Serial: {d.get('serial_number', 'N/A')}")
    print()

# Also show all HID devices
print(f"Total HID devices found: {len(devices)}")
if len(devices) <= 10:  # Only show if not too many
    for d in devices:
        print(f"  {d.get('manufacturer_string', 'Unknown')} {d.get('product_string', 'Unknown')} ({d['vendor_id']:04x}:{d['product_id']:04x})")