#!/usr/bin/env python3
"""
check_setup.py - Check if your environment is ready for pcProxAPI.dll
"""

import platform
import os
import sys

def check_python_architecture():
    """Check Python architecture"""
    arch = platform.architecture()[0]
    print(f"Python architecture: {arch}")
    return arch

def check_dll_exists():
    """Check if DLL exists"""
    dll_path = os.path.join(os.getcwd(), 'pcProxAPI.dll')
    exists = os.path.exists(dll_path)
    print(f"pcProxAPI.dll found: {exists}")
    if exists:
        size = os.path.getsize(dll_path)
        print(f"DLL size: {size} bytes")
    return exists

def check_platform():
    """Check if running on Windows"""
    system = platform.system()
    print(f"Platform: {system}")
    return system == 'Windows'

def test_dll_load():
    """Test loading the DLL"""
    try:
        import ctypes
        dll_path = os.path.join(os.getcwd(), 'pcProxAPI.dll')
        dll = ctypes.WinDLL(dll_path)
        print("DLL loads successfully")
        return True
    except Exception as e:
        print(f"DLL load failed: {e}")
        return False

def main():
    print("=== pcProxAPI.dll Setup Check ===\n")

    # Check platform
    if not check_platform():
        print("ERROR: pcProxAPI.dll only works on Windows")
        return False

    print()

    # Check Python architecture
    arch = check_python_architecture()
    if arch != '32bit':
        print("WARNING: You have 64-bit Python but pcProxAPI.dll is 32-bit")
        print("   You need either:")
        print("   - 32-bit Python installation, or")
        print("   - 64-bit version of pcProxAPI.dll")
    else:
        print("OK: Python architecture is correct (32-bit)")

    print()

    # Check DLL exists
    if not check_dll_exists():
        print("ERROR: pcProxAPI.dll not found in current directory")
        print(f"   Current directory: {os.getcwd()}")
        return False

    print()

    # Test DLL loading
    if test_dll_load():
        print("SUCCESS: DLL loads successfully - you're ready to go!")
        print("\nTry running: python dll_test.py")
        return True
    else:
        print("ERROR: DLL failed to load")
        return False

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)

# Also run when imported
else:
    main()