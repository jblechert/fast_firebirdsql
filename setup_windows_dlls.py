#!/usr/bin/env python3
"""
Setup script to copy Windows DLLs to the correct location for fast_firebirdsql.

This script should be run after installing the fast_firebirdsql wheel on Windows
to ensure the required DLLs are in the correct location.
"""

import os
import sys
import shutil
import site
from pathlib import Path


def find_fast_firebirdsql_package():
    """Find the installed fast_firebirdsql package directory."""
    # Try to import fast_firebirdsql to get its location
    try:
        import fast_firebirdsql
        package_dir = Path(fast_firebirdsql.__file__).parent
        return package_dir
    except ImportError:
        pass

    # If import fails, search in site-packages
    for site_dir in site.getsitepackages():
        fast_firebirdsql_dir = Path(site_dir) / "fast_firebirdsql"
        if fast_firebirdsql_dir.exists():
            return fast_firebirdsql_dir

    return None


def setup_windows_dlls():
    """Copy Windows DLLs to the fast_firebirdsql package directory."""
    if sys.platform != "win32":
        print("This script is only needed on Windows.")
        return True

    package_dir = find_fast_firebirdsql_package()
    if not package_dir:
        print("ERROR: Could not find fast_firebirdsql package directory.")
        return False

    print(f"Found fast_firebirdsql package at: {package_dir}")
    
    # Look for windows-firebird directory in the wheel
    windows_firebird_dir = None
    
    # Check in the package directory first
    candidate = package_dir.parent / "windows-firebird"
    if candidate.exists():
        windows_firebird_dir = candidate
    else:
        # Check in site-packages root
        for site_dir in site.getsitepackages():
            candidate = Path(site_dir) / "windows-firebird"
            if candidate.exists():
                windows_firebird_dir = candidate
                break
    
    if not windows_firebird_dir:
        print("ERROR: Could not find windows-firebird directory with DLLs.")
        return False
    
    print(f"Found Windows DLLs at: {windows_firebird_dir}")
    
    # Copy DLLs to package directory (since the abi3 wheels, only
    # fbclient.dll is bundled; python3.dll comes with CPython itself)
    dlls_to_copy = ["fbclient.dll"]
    copied_dlls = []
    
    for dll_name in dlls_to_copy:
        src_dll = windows_firebird_dir / dll_name
        dst_dll = package_dir / dll_name
        
        if src_dll.exists():
            try:
                shutil.copy2(src_dll, dst_dll)
                copied_dlls.append(dll_name)
                print(f"Copied {dll_name} to package directory")
            except Exception as e:
                print(f"ERROR: Failed to copy {dll_name}: {e}")
                return False
        else:
            print(f"WARNING: {dll_name} not found in {windows_firebird_dir}")
    
    if copied_dlls:
        print(f"Successfully copied {len(copied_dlls)} DLL(s): {', '.join(copied_dlls)}")
        print("fast_firebirdsql should now work correctly on Windows.")
        return True
    else:
        print("ERROR: No DLLs were copied.")
        return False


if __name__ == "__main__":
    success = setup_windows_dlls()
    sys.exit(0 if success else 1)
